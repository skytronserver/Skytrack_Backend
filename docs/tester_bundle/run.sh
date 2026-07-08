#!/usr/bin/env bash
set -euo pipefail

# Tester bundle runner: sets variables and runs all user simulators
# This script will create a local Python venv and install dependencies.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
CERTS_DIR="$ROOT_DIR/certs"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="python3"

# Ensure Python is available
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Python3 not found"; exit 1; }

# Create venv if not present and install deps
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet paho-mqtt

# Common MQTT/TLS settings (from your provided details)
export MQTT_HOST="135.235.166.209"
export MQTT_PORT="8883"
export MQTT_CAFILE="$CERTS_DIR/ca.crt"
export MQTT_INSECURE="0"   # set to 1 to disable cert verification
export MQTT_TIMEOUT="20"    # seconds

###############################################################################
# sosEx user (police executive) — using your provided variables
###############################################################################
export USER_ID="6026117160"
export JWT_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjY5LCJ1c2VyX21vYmlsZSI6IjYwMjYxMTcxNjAiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzY3MDcyNjE3LCJleHAiOjE3NjcyNDU0MTcsImp0aSI6IjEyNjlfMTc2NzA3MjYxNyIsInNlc3Npb25fZGF0YSI6eyJsb2dpbl90eXBlIjoib3RwX3ZhbGlkYXRlZCIsInN0YXR1cyI6ImF1dGhlbnRpY2F0ZWQiLCJsb2dpbl90aW1lIjoiMjAyNS0xMi0zMFQwNTozMDoxNy45NDE2OTUrMDA6MDAiLCJyb2xlIjoic29zZXhlY3V0aXZlIn0sImlzcyI6InNreXRyYWNrLWF1dGgiLCJhdWQiOiJza3l0cmFjay1hcGkifQ.dApVpZ-_VDmMMhiKfOI04NGeLpax0ijyWoo9_tWH6cecv-efcZiWNRJx6wm35dMTRbekp6m1cNyNVt8mk-CjNCGykB3GAICJG2ZBYAvst-uyKeuw-GQDCOgIgalGz7bOKOiulGss7VXWTipccip3INn-VbSy1ZdlD4VglpWS3S2NqsVGfkZQ4PSefjk0CF_FPS_QCbBO9GkOIx81k-54MUoG-77ZKBTyF-vKZRaCHTyu3Yc5q_o3Q_6lGvr-Iyu640vUYTZJ7Q-dRmsAAPqa9-htJJyo96q6yj6R5eyscJgtqUNihsOLJF48VbYvNaPJvFPoCiMVubkW5TMZ0d_Ttw"

echo "=== Running sosEx simulator ==="
"$VENV_DIR/bin/python" "$SCRIPTS_DIR/sim_sosEx.py"

###############################################################################
# owner user — defaults channel to token. Fill values if you want to run.
###############################################################################




###############################################################################
# sosEx user (police executive) — updated police account credentials
###############################################################################
export USER_ID="6026969588"
export JWT_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjcxLCJ1c2VyX21vYmlsZSI6IjYwMjY5Njk1ODgiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzY3MDY5MjQyLCJleHAiOjE3NjcyNDIwNDIsImp0aSI6IjEyNzFfMTc2NzA2OTI0MiIsInNlc3Npb25fZGF0YSI6eyJsb2dpbl90eXBlIjoib3RwX3ZhbGlkYXRlZCIsInN0YXR1cyI6ImF1dGhlbnRpY2F0ZWQiLCJsb2dpbl90aW1lIjoiMjAyNS0xMi0zMFQwNDozNDowMi41NjE3MzkrMDA6MDAiLCJyb2xlIjoiZHRvcnRvIn0sImlzcyI6InNreXRyYWNrLWF1dGgiLCJhdWQiOiJza3l0cmFjay1hcGkifQ.sMdtYfqqUTXeZbjdHkYU1Q3QUE17V_z3yCjwm6UwYxxfzPFDs5gTg9r7kh_0wXkHAD2gU61UkifduuVunEKO9VDzAoQJNgLge2QqAnCzf_eDwLKuaGmKGcC7DzaAbaDgwIKK3p3558_LOBhRrCXhQVRVgRvC0Q6sHSUsfFD8CPxujhRuWHR2Ua-kcy1yTlMOlbUha5Qa5nDjUuCA-7yrI8RvpCPzKi-xx5aD1Ku9RW4xvkQyQWWY8lx62VSUznLQ_D4oScY7k7NtSMoAXfZc3jQjyB499p_bqwV04QQt1DDrAp4Q1u2lLPFjnRcVtyFK0vUkpUohZZ1V1l247w4oRg"
 
export CHANNEL="${OWNER_CHANNEL:-$JWT_TOKEN}"

if [[ -n "${JWT_TOKEN}" ]]; then
  echo "=== Running owner simulator ==="
  "$VENV_DIR/bin/python" "$SCRIPTS_DIR/sim_owner.py"
else
  echo "(owner) JWT_TOKEN not set; skipping run"
fi

###############################################################################
# dtorto user — defaults channel to token. Fill values if you want to run.
###############################################################################
export USER_ID="${DTORTO_USER_ID:-}"
export JWT_TOKEN="${DTORTO_JWT_TOKEN:-}"
export CHANNEL="${DTORTO_CHANNEL:-$JWT_TOKEN}"

if [[ -n "${JWT_TOKEN}" ]]; then
  echo "=== Running dtorto simulator ==="
  "$VENV_DIR/bin/python" "$SCRIPTS_DIR/sim_dtorto.py"
else
  echo "(dtorto) JWT_TOKEN not set; skipping run"
fi

echo "All done."