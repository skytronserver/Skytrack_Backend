#!/usr/bin/env bash
set -euo pipefail

CONF_DIR="/etc/mosquitto/conf.d"
TARGET="${CONF_DIR}/10-single-session-policy.conf"

if [[ ${EUID} -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

mkdir -p "${CONF_DIR}"

cat > "${TARGET}" <<'EOF'
# Managed by apply_mqtt_single_session_policy.sh
# Broker-side guardrails only; app-level IMEI lease logic enforces
# one tracking + one emergency session per IMEI.
allow_zero_length_clientid false
persistent_client_expiration 1d

# Production log levels (avoid log_type all noise)
log_type error
log_type warning
log_type notice
EOF

echo "[ok] Wrote ${TARGET}"

echo "[info] Checking mosquitto config syntax..."
mosquitto -c /etc/mosquitto/mosquitto.conf -p 0 -v >/tmp/mosq_config_check.log 2>&1 &
CHK_PID=$!
sleep 1
kill "${CHK_PID}" >/dev/null 2>&1 || true

if grep -qiE "error|invalid|unknown" /tmp/mosq_config_check.log; then
  echo "[warn] Potential config issue detected. Review /tmp/mosq_config_check.log"
  cat /tmp/mosq_config_check.log
  exit 1
fi

echo "[info] Restarting mosquitto..."
systemctl restart mosquitto
systemctl --no-pager --full status mosquitto | sed -n '1,30p'

echo "[info] Active policy file content:"
cat "${TARGET}"

echo "[done] Single-session policy applied."
