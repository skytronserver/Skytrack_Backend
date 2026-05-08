#!/usr/bin/env bash
set -euo pipefail

SINCE="${1:-2 hours ago}"
UNIT="${2:-mosquitto}"

echo "[info] Duplicate MQTT client_id report"
echo "[info] unit=${UNIT} since=${SINCE}"

echo
echo "=== Top duplicate client_id disconnects (already connected) ==="
sudo journalctl -u "${UNIT}" --since "${SINCE}" --no-pager \
  | grep -F "already connected, closing old connection" \
  | sed -E "s/.*Client ([^ ]+) already connected.*/\1/" \
  | sort | uniq -c | sort -nr | head -n 30 || true

echo
echo "=== TLS unexpected EOF count by minute ==="
sudo journalctl -u "${UNIT}" --since "${SINCE}" --no-pager \
  | grep -F "unexpected eof while reading" \
  | awk '{print $1, $2, substr($3,1,5)}' \
  | sort | uniq -c | sort -nr || true

echo
echo "=== Auth throttle / no-credential events from backend (last ${SINCE}) ==="
if sudo docker ps --format '{{.Names}}' | grep -qx 'skytron-backend-api-container'; then
  sudo docker logs --since "${SINCE}" skytron-backend-api-container 2>&1 \
    | grep -E "currently blocked \(throttle\)|No credentials provided|blocked after [0-9]+ failures" \
    | sed -E "s/.*clientid '([^']+)'.*/\1/" \
    | sort | uniq -c | sort -nr | head -n 30 || true
else
  echo "[warn] skytron-backend-api-container not running"
fi
