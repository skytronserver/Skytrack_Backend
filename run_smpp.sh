#!/bin/bash
# Airtel SMPP worker (SMS to devices from our VMN): python manage.py smpp_worker
# in its own container, from the API image (so run it after run_with_host_storage.sh,
# which NIC_deploy.sh backend does). Dev VM only - not part of the NIC rollout.
#
#   sudo ./run_smpp.sh            (re)start the worker with the SMPP_* settings in .env
#   sudo ./run_smpp.sh --stop     stop and remove it
#
# Settings (.env): SMPP_SYSTEM_ID and SMPP_PASSWORD are required; the rest are
# optional, see the docstring of Skytronsystem/skytron_api/management/commands/smpp_worker.py.
# They are passed at run time, not baked into the image.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

ENV_FILE="${ENV_FILE:-.env}"
[ -f "$ENV_FILE" ] || { echo "Environment file not found: $ENV_FILE" >&2; exit 1; }
set -a; source "$ENV_FILE"; set +a

IMAGE=skytron-backend-api
CONTAINER=skytron-smpp-worker-container
NETWORK_NAME="skytron-net"

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
if [ "${1:-}" = "--stop" ]; then
  echo "SMPP worker stopped"
  exit 0
fi

[ -n "${SMPP_SYSTEM_ID:-}" ] && [ -n "${SMPP_PASSWORD:-}" ] \
  || { echo "SMPP_SYSTEM_ID / SMPP_PASSWORD not set in $ENV_FILE - SMPP worker not started" >&2; exit 1; }
docker image inspect "$IMAGE" >/dev/null 2>&1 \
  || { echo "image $IMAGE missing - run ./run_with_host_storage.sh first" >&2; exit 1; }

# Same Redis as the API: the worker's heartbeat is read by GET /api/smpp/status/.
if [ -n "${REDIS_HOST:-}" ]; then
  REDIS_URL="redis://${REDIS_PASSWORD:+:$REDIS_PASSWORD@}$REDIS_HOST:${REDIS_PORT:-6379}/1"
else
  REDIS_URL="redis://skytron-redis:6379/1"
fi

ENV_ARGS=()
for v in SMPP_SYSTEM_ID SMPP_PASSWORD SMPP_HOSTS SMPP_PORT SMPP_TLS SMPP_SYSTEM_TYPE \
         SMPP_SOURCE_ADDR SMPP_SOURCE_TON SMPP_SOURCE_NPI SMPP_DEST_TON SMPP_DEST_NPI \
         SMPP_DATA_CODING SMPP_TPS SMPP_WINDOW SMPP_MAX_ATTEMPTS SMPP_ENQUIRE_INTERVAL; do
  [ -n "${!v:-}" ] && ENV_ARGS+=(-e "$v")
done

docker run -d --restart=always \
  --network "$NETWORK_NAME" \
  --stop-timeout 20 \
  -e REDIS_URL="$REDIS_URL" \
  "${ENV_ARGS[@]}" \
  --log-opt max-size=20m --log-opt max-file=5 \
  --name "$CONTAINER" \
  "$IMAGE" python manage.py smpp_worker >/dev/null

sleep 5
if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" != "true" ]; then
  echo "SMPP worker did not stay up:" >&2
  docker logs --tail 30 "$CONTAINER" >&2 || true
  exit 1
fi
echo "SMPP worker running ($CONTAINER):"
docker logs --tail 5 "$CONTAINER" 2>&1 | grep -v 'JWT .* key loaded' || true
