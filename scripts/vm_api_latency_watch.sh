#!/usr/bin/env bash
set -euo pipefail

DURATION_MIN="${1:-15}"
INTERVAL_SEC="${2:-15}"
API_URL="${3:-https://api.gromed.in/api/gps-data-log-table/?search=67340}"

if ! [[ "${DURATION_MIN}" =~ ^[0-9]+$ ]] || ! [[ "${INTERVAL_SEC}" =~ ^[0-9]+$ ]]; then
  echo "Usage: $0 [duration_min] [interval_sec] [api_url]" >&2
  exit 1
fi

OUT_DIR="/tmp/vm_api_watch_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${OUT_DIR}"

END_EPOCH=$(( $(date +%s) + DURATION_MIN * 60 ))

echo "[info] Writing logs to ${OUT_DIR}"
echo "[info] duration=${DURATION_MIN}m interval=${INTERVAL_SEC}s api=${API_URL}"

while [[ $(date +%s) -lt ${END_EPOCH} ]]; do
  TS="$(date -Is)"

  {
    echo "=== ${TS} vmstat ==="
    vmstat 1 2
    echo
    echo "=== ${TS} pressure ==="
    cat /proc/pressure/cpu
    cat /proc/pressure/io
    cat /proc/pressure/memory
    echo
    echo "=== ${TS} docker stats ==="
    sudo docker stats --no-stream
    echo
    echo "=== ${TS} api latency ==="
    curl -sS -o /dev/null -w "http=%{http_code} total=%{time_total}s connect=%{time_connect}s starttransfer=%{time_starttransfer}s\n" "${API_URL}" || true
    echo
  } | tee -a "${OUT_DIR}/watch.log"

  sleep "${INTERVAL_SEC}"
done

echo "[info] completed. summary:"
grep -E "^http=|avg10=|load average|cpu" "${OUT_DIR}/watch.log" | tail -n 60 || true
