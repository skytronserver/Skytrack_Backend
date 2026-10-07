#!/bin/bash
# Backend VM: deploy the device source-IP feature.
#
#   sudo ./deploy_device_ip_backend.sh
#
# 1. Ensures MQTT_IP_REPORT_KEY is in .env (generates one if missing).
# 2. Rebuilds the API container, runs migrations (0106 adds imei/network_name
#    + concurrent indexes on the log tables), rebuilds the MQTT client and the
#    TCP GPS/EM servers.
# 3. Verifies, then prints the key to use for install_mqtt_ip_reporter.sh on
#    the broker VM.
#
# Run `git pull` first; this script deploys whatever is checked out.
# Set ENV_FILE to use a file other than .env (same as run_with_host_storage.sh).
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
ENV_FILE="${ENV_FILE:-.env}"
API_CONTAINER="skytron-backend-api-container"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. Shared key for the broker VM reporter
# ---------------------------------------------------------------------------
existing_key="$(grep -E '^(export[[:space:]]+)?MQTT_IP_REPORT_KEY=' "$ENV_FILE" | tail -n1 | sed -E 's/^(export[[:space:]]+)?MQTT_IP_REPORT_KEY=//; s/^["'\'']//; s/["'\'']$//' || true)"
if [ -n "$existing_key" ]; then
  echo "[1/5] MQTT_IP_REPORT_KEY already set in $ENV_FILE - keeping it"
else
  if command -v openssl >/dev/null 2>&1; then
    new_key="$(openssl rand -hex 32)"
  else
    new_key="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  fi
  cp -p "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
  # Match the file's style: NIC .env lines use `export`.
  if grep -qE '^export[[:space:]]' "$ENV_FILE"; then
    printf '\nexport MQTT_IP_REPORT_KEY=%s\n' "$new_key" >> "$ENV_FILE"
  else
    printf '\nMQTT_IP_REPORT_KEY=%s\n' "$new_key" >> "$ENV_FILE"
  fi
  echo "[1/5] Generated MQTT_IP_REPORT_KEY and appended it to $ENV_FILE (backup saved)"
fi

# ---------------------------------------------------------------------------
# 2. API container + migrations
# ---------------------------------------------------------------------------
echo "[2/5] Rebuilding API container"
ENV_FILE="$ENV_FILE" ./run_with_host_storage.sh

echo "      Waiting for $API_CONTAINER"
for i in $(seq 1 30); do
  if docker exec "$API_CONTAINER" true >/dev/null 2>&1; then break; fi
  sleep 2
done

echo "      Running migrations (0106 builds indexes CONCURRENTLY - can take a few minutes on large tables)"
docker exec "$API_CONTAINER" python manage.py migrate

# ---------------------------------------------------------------------------
# 3. MQTT client + TCP servers
# ---------------------------------------------------------------------------
echo "[3/5] Rebuilding MQTT client container"
ENV_FILE="$ENV_FILE" ./run_mqtt.sh

echo "[4/5] Rebuilding TCP GPS (6000) and EM (5001) server containers"
./run_tcp.sh

# ---------------------------------------------------------------------------
# 4. Verify
# ---------------------------------------------------------------------------
echo "[5/5] Verifying"
fail=0

if docker exec "$API_CONTAINER" python manage.py showmigrations skytron_api 2>/dev/null \
     | grep -q '\[X\] 0106_datalog_imei_network_name'; then
  echo "  OK   migration 0106 applied"
else
  echo "  FAIL migration 0106 not applied"; fail=1
fi

if docker exec "$API_CONTAINER" sh -c '[ -n "$MQTT_IP_REPORT_KEY" ]'; then
  echo "  OK   API container has MQTT_IP_REPORT_KEY"
else
  echo "  FAIL API container has no MQTT_IP_REPORT_KEY (report endpoint will return 403)"; fail=1
fi

for c in skytrack-mqtt-client-container skytron-backend-gps-container skytron-backend-em-container; do
  if [ "$(docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null)" = "true" ]; then
    echo "  OK   $c running"
  else
    echo "  FAIL $c not running"; fail=1
  fi
done

final_key="$(grep -E '^(export[[:space:]]+)?MQTT_IP_REPORT_KEY=' "$ENV_FILE" | tail -n1 | sed -E 's/^(export[[:space:]]+)?MQTT_IP_REPORT_KEY=//; s/^["'\'']//; s/["'\'']$//')"

echo
echo "=============================================================================="
echo " Backend deployed. Now on the BROKER VM run:"
echo
echo "   sudo ./install_mqtt_ip_reporter.sh --key $final_key"
echo
echo " (add --url http://<this-backend>:2000/api/mqtt/client-ip/report/ if the"
echo "  broker's go-auth.conf does not point at this backend)"
echo "=============================================================================="

exit $fail
