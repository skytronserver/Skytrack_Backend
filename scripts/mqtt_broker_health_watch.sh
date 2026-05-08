#!/usr/bin/env bash
set -euo pipefail

UNIT="${1:-mosquitto}"

echo "[info] Watching mosquitto health events only (Ctrl+C to stop)"
echo "[info] unit=${UNIT}"

sudo journalctl -u "${UNIT}" -f -o short-iso --no-pager \
  | grep --line-buffered -E "already connected, closing old connection|unexpected eof while reading|denied|not authorised|Socket error on client|Client .* disconnected|Client .* connected"
