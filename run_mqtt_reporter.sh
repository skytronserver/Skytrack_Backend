#!/bin/bash
# Broker VM: run the MQTT device-IP reporter as a Docker container
# (replaces the systemd/python3 install from install_mqtt_ip_reporter.sh on VMs
# where Python must not run on the host). Only bash, grep and docker are used on the host.
#
#   sudo ./run_mqtt_reporter.sh                       # re-deploy, reuses saved settings
#   sudo ./run_mqtt_reporter.sh --key <MQTT_IP_REPORT_KEY from backend .env>
#   sudo ./run_mqtt_reporter.sh --key <key> --url http://10.192.136.175:2000/api/mqtt/client-ip/report/
#
# Options:
#   --key KEY        default: env MQTT_IP_REPORT_KEY, then the saved env file,
#                    then ./.env (co-located dev VM), else prompted
#   --url URL        default: saved env file, else built from auth_opt_http_* in the
#                    go-auth config, i.e. the same backend the broker already calls for auth
#   --log PATH       default: saved env file, else `log_dest file` from the mosquitto config
#   --load TAR       docker load the base image from TAR first (VMs without registry access;
#                    make it elsewhere with: docker save python:3.9-slim-bullseye -o base.tar)
#   --check          build the image and validate config, log access and backend key,
#                    then stop (starts nothing)
#
# Settings are saved to /etc/skytrack/mqtt-ip-reporter.env (root-only), so later runs
# (e.g. from NIC_deploy.sh mqtt-reporter) need no arguments. Never restarts or edits
# Mosquitto. Stops and disables the old systemd mqtt-ip-reporter service if present.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
SRC_SCRIPT="mqtt_deployment/mqtt_ip_reporter.py"
SRC_DOCKERFILE="mqtt_deployment/Dockerfile.ip_reporter"
IMAGE="skytrack-mqtt-ip-reporter"
CONTAINER="skytrack-mqtt-ip-reporter-container"
ENV_DIR="/etc/skytrack"
ENV_PATH="$ENV_DIR/mqtt-ip-reporter.env"
MOSQ_DIR="/etc/mosquitto"

KEY="${MQTT_IP_REPORT_KEY:-}"
URL=""
LOG_PATH=""
LOAD_TAR=""
CHECK_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --key) KEY="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --log) LOG_PATH="$2"; shift 2 ;;
    --load) LOAD_TAR="$2"; shift 2 ;;
    --check) CHECK_ONLY=1; shift ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN:  $*" >&2; }

[ "$(id -u)" -eq 0 ] || die "run with sudo"
[ -f "$SRC_SCRIPT" ] && [ -f "$SRC_DOCKERFILE" ] || die "run from the repo checkout ($SRC_SCRIPT / $SRC_DOCKERFILE not found)"
command -v docker >/dev/null || die "docker not found"
docker info >/dev/null 2>&1 || die "docker daemon not reachable"

# Value of KEY=... from an env file, without sourcing it.
env_val() { [ -f "$2" ] && grep -E "^$1=" "$2" | tail -n1 | cut -d= -f2- | tr -d '"'"'"'\r' || true; }

# Last value of a mosquitto/go-auth option across all config files.
mosq_opt() {
  grep -rhE "^[[:space:]]*$1[[:space:]]+" "$MOSQ_DIR" --include='*.conf' 2>/dev/null \
    | tail -n1 | awk '{ $1=""; sub(/^ /, ""); print }' || true
}

# ---------------------------------------------------------------------------
# 1. Key
# ---------------------------------------------------------------------------
[ -n "$KEY" ] || KEY="$(env_val MQTT_IP_REPORT_KEY "$ENV_PATH")"
[ -n "$KEY" ] || KEY="$(env_val MQTT_IP_REPORT_KEY .env)"
if [ -z "$KEY" ]; then
  [ -t 0 ] || die "no key saved yet; pass --key <MQTT_IP_REPORT_KEY from backend .env>"
  read -r -s -p "MQTT_IP_REPORT_KEY (from backend .env): " KEY; echo
fi
[ -n "$KEY" ] || die "key is required"
[[ "$KEY" =~ ^[A-Za-z0-9._~+/=-]+$ ]] || die "key contains unexpected characters"

# ---------------------------------------------------------------------------
# 2. Backend URL (default: saved, else the same backend go-auth uses)
# ---------------------------------------------------------------------------
[ -n "$URL" ] || URL="$(env_val MQTT_IP_REPORT_URL "$ENV_PATH")"
if [ -z "$URL" ]; then
  host="$(mosq_opt auth_opt_http_host)"
  port="$(mosq_opt auth_opt_http_port)"
  tls="$(mosq_opt auth_opt_http_with_tls)"
  [ -n "$host" ] || die "could not find auth_opt_http_host under $MOSQ_DIR; pass --url"
  scheme="http"; [ "$tls" = "true" ] && scheme="https"
  URL="$scheme://$host${port:+:$port}/api/mqtt/client-ip/report/"
fi
echo "[1/6] Backend URL: $URL"

# ---------------------------------------------------------------------------
# 3. Broker log
# ---------------------------------------------------------------------------
[ -n "$LOG_PATH" ] || LOG_PATH="$(env_val MQTT_BROKER_LOG_PATH "$ENV_PATH")"
if [ -z "$LOG_PATH" ]; then
  LOG_PATH="$(grep -rhE '^[[:space:]]*log_dest[[:space:]]+file[[:space:]]+' "$MOSQ_DIR" --include='*.conf' 2>/dev/null \
               | tail -n1 | awk '{print $3}' || true)"
  [ -n "$LOG_PATH" ] || die "mosquitto is not logging to a file. Add to mosquitto.conf:
    log_dest file /var/log/mosquitto/mosquitto.log
    log_type notice
then restart mosquitto in a maintenance window and re-run this script."
fi
[[ "$LOG_PATH" = /* ]] || die "log path must be absolute: $LOG_PATH"
LOG_DIR="$(dirname "$LOG_PATH")"
echo "[2/6] Broker log: $LOG_PATH"

log_types="$(grep -rhE '^[[:space:]]*log_type[[:space:]]+' "$MOSQ_DIR" --include='*.conf' 2>/dev/null | awk '{print $2}' | sort -u | tr '\n' ' ' || true)"
if [ -n "$log_types" ] && ! echo " $log_types " | grep -qE ' (notice|information|all) '; then
  warn "log_type is only: $log_types- connect lines are logged at 'notice'."
  warn "Add 'log_type notice' to mosquitto.conf and restart mosquitto in a maintenance window."
fi

# The container runs as the host's mosquitto user, which owns the log directory.
if id mosquitto >/dev/null 2>&1; then
  RUN_USER="$(id -u mosquitto):$(id -g mosquitto)"
else
  RUN_USER="$(stat -c '%u:%g' "$LOG_DIR" 2>/dev/null || true)"
  [ -n "$RUN_USER" ] || die "no 'mosquitto' user and $LOG_DIR missing - is this the broker VM?"
  warn "no 'mosquitto' user; running as owner of $LOG_DIR ($RUN_USER)"
fi
[ -d "$LOG_DIR" ] || die "$LOG_DIR does not exist"
[ -f "$LOG_PATH" ] || warn "$LOG_PATH does not exist yet (the reporter will keep retrying)"

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
# 4. Image (no RUN steps: only the base image is ever pulled)
# ---------------------------------------------------------------------------
echo "[3/6] Building image $IMAGE"
if [ -n "$LOAD_TAR" ]; then
  [ -f "$LOAD_TAR" ] || die "$LOAD_TAR not found"
  docker load -i "$LOAD_TAR"
fi
ctx="$(mktemp -d)"
trap 'rm -rf "$ctx"' EXIT
cp "$SRC_SCRIPT" "$SRC_DOCKERFILE" "$ctx/"
docker build -q -t "$IMAGE" -f "$ctx/$(basename "$SRC_DOCKERFILE")" "$ctx" >/dev/null \
  || die "image build failed. If this VM cannot pull python:3.9-slim-bullseye, run on a VM that can:
    docker save python:3.9-slim-bullseye -o base.tar
copy base.tar here and re-run with --load base.tar"

# Saved settings double as the container's --env-file.
umask 077
install -d -m 755 "$ENV_DIR"
tmp_env="$(mktemp "$ENV_DIR/.mqtt-ip-reporter.env.XXXXXX")"
cat > "$tmp_env" <<EOF
MQTT_IP_REPORT_URL=$URL
MQTT_IP_REPORT_KEY=$KEY
MQTT_BROKER_LOG_PATH=$LOG_PATH
EOF

# Read access exactly as the reporter will have it.
if [ -f "$LOG_PATH" ] && ! docker run --rm --user "$RUN_USER" -v "$LOG_DIR:$LOG_DIR:ro" \
     --entrypoint test "$IMAGE" -r "$LOG_PATH"; then
  rm -f "$tmp_env"
  die "container user $RUN_USER cannot read $LOG_PATH"
fi

# ---------------------------------------------------------------------------
# 5. Backend reachability + key check (empty batch, writes nothing)
# ---------------------------------------------------------------------------
echo "[4/6] Testing backend endpoint"
check="$(docker run --rm --network host --env-file "$tmp_env" "$IMAGE" --check)"
code="${check%% *}"
case "$code" in
  200) echo "      OK: $check" ;;
  403) rm -f "$tmp_env"; die "backend rejected the key (403). Use MQTT_IP_REPORT_KEY from the backend .env." ;;
  400) rm -f "$tmp_env"; die "backend returned 400: $check
Most likely the URL host is not in the backend's ALLOWED_HOSTS - use the host go-auth uses, or pass --url." ;;
  404) rm -f "$tmp_env"; die "backend returned 404 - the backend is not running the device-IP code yet." ;;
  *)   rm -f "$tmp_env"; die "cannot reach $URL: $check" ;;
esac

if [ "$CHECK_ONLY" -eq 1 ]; then
  rm -f "$tmp_env"
  echo "Check passed (--check: nothing started, settings not saved)."
  exit 0
fi

echo "[5/6] Saving settings to $ENV_PATH (root-only)"
mv -f "$tmp_env" "$ENV_PATH"
chmod 600 "$ENV_PATH"

# ---------------------------------------------------------------------------
# 6. Start (and retire the old host-python service so IPs aren't sent twice)
# ---------------------------------------------------------------------------
echo "[6/6] Starting $CONTAINER"
if command -v systemctl >/dev/null && systemctl cat mqtt-ip-reporter >/dev/null 2>&1; then
  echo "      Stopping and disabling old systemd service mqtt-ip-reporter"
  systemctl disable --now mqtt-ip-reporter >/dev/null 2>&1 || true
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
# --network host: reach the backend exactly as the host does (and 127.0.0.1 on a
# co-located VM). Log dir is mounted read-only at the same path so rotation works.
docker run -d --restart=always \
  --name "$CONTAINER" \
  --network host \
  --user "$RUN_USER" \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --memory 128m \
  --log-opt max-size=10m --log-opt max-file=3 \
  --env-file "$ENV_PATH" \
  -v "$LOG_DIR:$LOG_DIR:ro" \
  "$IMAGE" >/dev/null

sleep 4
if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" = "true" ]; then
  echo
  docker logs --tail 5 "$CONTAINER" 2>&1 | sed 's/^/  /'
  echo
  echo "=============================================================================="
  echo " Reporter running. Follow it with:  sudo docker logs -f $CONTAINER"
  echo " Expect: 'following $LOG_PATH; N devices queued' and no 'unreachable' lines."
  echo "=============================================================================="
else
  docker logs --tail 20 "$CONTAINER" >&2 || true
  die "$CONTAINER failed to start (log above)"
fi
