#!/bin/bash
# Broker VM: install the MQTT device-IP reporter (systemd service).
#
#   sudo ./install_mqtt_ip_reporter.sh --key <MQTT_IP_REPORT_KEY from backend .env>
#   sudo ./install_mqtt_ip_reporter.sh --key <key> --url http://10.192.136.175:2000/api/mqtt/client-ip/report/
#
# Options:
#   --key KEY        required (or env MQTT_IP_REPORT_KEY, or prompted)
#   --url URL        default: built from auth_opt_http_* in the go-auth config,
#                    i.e. the same backend the broker already calls for auth
#   --log PATH       default: `log_dest file` from the mosquitto config
#   --check          validate config, log access and backend key, then stop
#                    (installs nothing)
#
# Needs only python3 and systemd. Never restarts or edits Mosquitto itself.
# Safe to re-run (updates files and restarts the reporter).
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
SRC_SCRIPT="mqtt_deployment/mqtt_ip_reporter.py"
SRC_UNIT="mqtt_deployment/mqtt-ip-reporter.service"
INSTALL_DIR="/opt/skytrack"
ENV_DIR="/etc/skytrack"
ENV_PATH="$ENV_DIR/mqtt-ip-reporter.env"
UNIT_PATH="/etc/systemd/system/mqtt-ip-reporter.service"
MOSQ_DIR="/etc/mosquitto"

KEY="${MQTT_IP_REPORT_KEY:-}"
URL=""
LOG_PATH=""
CHECK_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --key) KEY="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --log) LOG_PATH="$2"; shift 2 ;;
    --check) CHECK_ONLY=1; shift ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN:  $*" >&2; }

[ "$(id -u)" -eq 0 ] || die "run with sudo"
[ -f "$SRC_SCRIPT" ] && [ -f "$SRC_UNIT" ] || die "run from the repo checkout ($SRC_SCRIPT / $SRC_UNIT not found)"
command -v python3 >/dev/null || die "python3 not found (apt install python3)"
id mosquitto >/dev/null 2>&1 || die "user 'mosquitto' not found - is this the broker VM?"

# Last value of a mosquitto/go-auth option across all config files.
mosq_opt() {
  grep -rhE "^[[:space:]]*$1[[:space:]]+" "$MOSQ_DIR" --include='*.conf' 2>/dev/null \
    | tail -n1 | awk '{ $1=""; sub(/^ /, ""); print }' || true
}

# ---------------------------------------------------------------------------
# 1. Key
# ---------------------------------------------------------------------------
if [ -z "$KEY" ]; then
  read -r -s -p "MQTT_IP_REPORT_KEY (from backend .env): " KEY; echo
fi
[ -n "$KEY" ] || die "key is required"
[[ "$KEY" =~ ^[A-Za-z0-9._~+/=-]+$ ]] || die "key contains unexpected characters"

# ---------------------------------------------------------------------------
# 2. Backend URL (default: same backend go-auth uses)
# ---------------------------------------------------------------------------
if [ -z "$URL" ]; then
  host="$(mosq_opt auth_opt_http_host)"
  port="$(mosq_opt auth_opt_http_port)"
  tls="$(mosq_opt auth_opt_http_with_tls)"
  [ -n "$host" ] || die "could not find auth_opt_http_host under $MOSQ_DIR; pass --url"
  scheme="http"; [ "$tls" = "true" ] && scheme="https"
  URL="$scheme://$host${port:+:$port}/api/mqtt/client-ip/report/"
  echo "[1/6] Backend URL (from go-auth config): $URL"
else
  echo "[1/6] Backend URL: $URL"
fi

# ---------------------------------------------------------------------------
# 3. Broker log
# ---------------------------------------------------------------------------
if [ -z "$LOG_PATH" ]; then
  LOG_PATH="$(grep -rhE '^[[:space:]]*log_dest[[:space:]]+file[[:space:]]+' "$MOSQ_DIR" --include='*.conf' 2>/dev/null \
               | tail -n1 | awk '{print $3}' || true)"
  [ -n "$LOG_PATH" ] || die "mosquitto is not logging to a file. Add to mosquitto.conf:
    log_dest file /var/log/mosquitto/mosquitto.log
    log_type notice
then restart mosquitto in a maintenance window and re-run this script."
fi
echo "[2/6] Broker log: $LOG_PATH"

log_types="$(grep -rhE '^[[:space:]]*log_type[[:space:]]+' "$MOSQ_DIR" --include='*.conf' 2>/dev/null | awk '{print $2}' | sort -u | tr '\n' ' ' || true)"
if [ -n "$log_types" ] && ! echo " $log_types " | grep -qE ' (notice|information|all) '; then
  warn "log_type is only: $log_types- connect lines are logged at 'notice'."
  warn "Add 'log_type notice' to mosquitto.conf and restart mosquitto in a maintenance window."
fi

[ -f "$LOG_PATH" ] || warn "$LOG_PATH does not exist yet (the reporter will keep retrying)"
if [ -f "$LOG_PATH" ] && ! runuser -u mosquitto -- test -r "$LOG_PATH"; then
  die "user mosquitto cannot read $LOG_PATH"
fi

if [ -f "$LOG_PATH" ]; then
  sample="$(grep -h 'New client connected' "$LOG_PATH" 2>/dev/null | tail -n3 || true)"
  if [ -n "$sample" ]; then
    echo "      Recent connects (these IPs are what will be stored):"
    echo "$sample" | sed 's/^/        /'
  else
    warn "no 'New client connected' lines in $LOG_PATH yet"
  fi
fi

# ---------------------------------------------------------------------------
# 4. Backend reachability + key check (empty batch, writes nothing)
# ---------------------------------------------------------------------------
echo "[3/6] Testing backend endpoint"
check="$(MQTT_IP_REPORT_URL="$URL" MQTT_IP_REPORT_KEY="$KEY" python3 - <<'PY'
import json, os, urllib.request, urllib.error
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
req = urllib.request.Request(
    os.environ["MQTT_IP_REPORT_URL"], data=b'{"entries": []}', method="POST",
    headers={"Content-Type": "application/json", "X-MQTT-IP-Key": os.environ["MQTT_IP_REPORT_KEY"]})
try:
    with opener.open(req, timeout=10) as r:
        print(r.status, r.read()[:200].decode(errors="replace"))
except urllib.error.HTTPError as e:
    print(e.code, e.read()[:200].decode(errors="replace").replace("\n", " "))
except Exception as e:
    print(0, e)
PY
)"
code="${check%% *}"
case "$code" in
  200) echo "      OK: $check" ;;
  403) die "backend rejected the key (403). Use MQTT_IP_REPORT_KEY from the backend .env, and make sure the backend was deployed with deploy_device_ip_backend.sh." ;;
  400) die "backend returned 400: $check
Most likely the URL host is not in the backend's ALLOWED_HOSTS - use the host go-auth uses, or pass --url." ;;
  404) die "backend returned 404 - the backend is not running the new code yet (run deploy_device_ip_backend.sh there first)." ;;
  *)   die "cannot reach $URL: $check" ;;
esac

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "Check passed (--check: nothing installed)."
  exit 0
fi

# ---------------------------------------------------------------------------
# 5. Install
# ---------------------------------------------------------------------------
echo "[4/6] Installing $INSTALL_DIR/mqtt_ip_reporter.py and $UNIT_PATH"
install -d -m 755 "$INSTALL_DIR"
install -m 755 "$SRC_SCRIPT" "$INSTALL_DIR/mqtt_ip_reporter.py"
install -m 644 "$SRC_UNIT" "$UNIT_PATH"

echo "[5/6] Writing $ENV_PATH (root-only)"
install -d -m 755 "$ENV_DIR"
umask 077
cat > "$ENV_PATH" <<EOF
MQTT_IP_REPORT_URL=$URL
MQTT_IP_REPORT_KEY=$KEY
MQTT_BROKER_LOG_PATH=$LOG_PATH
EOF
chmod 600 "$ENV_PATH"

# ---------------------------------------------------------------------------
# 6. Start
# ---------------------------------------------------------------------------
echo "[6/6] Starting mqtt-ip-reporter"
systemctl daemon-reload
systemctl enable mqtt-ip-reporter >/dev/null 2>&1
systemctl restart mqtt-ip-reporter
sleep 4

if systemctl is-active --quiet mqtt-ip-reporter; then
  echo
  journalctl -u mqtt-ip-reporter -n 5 --no-pager | sed 's/^/  /'
  echo
  echo "=============================================================================="
  echo " Reporter running. Follow it with:  sudo journalctl -u mqtt-ip-reporter -f"
  echo " Expect: 'following $LOG_PATH; N devices queued' and no 'unreachable' lines."
  echo "=============================================================================="
else
  journalctl -u mqtt-ip-reporter -n 20 --no-pager >&2
  die "mqtt-ip-reporter failed to start (log above)"
fi
