#!/bin/bash
# Syncs MQTT_LOADTEST_WHITELIST_IPS from .env into the fail2ban "mosquitto"
# jail's ignoreip line, then reloads the jail. Run this after changing
# MQTT_LOADTEST_WHITELIST_IPS in .env (e.g. the load-test machine's IP changed).
set -euo pipefail

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env"
JAIL_FILE="/etc/fail2ban/jail.d/mosquitto.conf"
BASE_IPS="127.0.0.1/8 ::1"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (sudo), needed to edit $JAIL_FILE and reload fail2ban." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [ -z "${MQTT_LOADTEST_WHITELIST_IPS:-}" ]; then
  echo "MQTT_LOADTEST_WHITELIST_IPS is empty in $ENV_FILE — nothing to sync." >&2
  exit 1
fi

sed -i -E "s|^ignoreip( +)=.*|ignoreip = ${BASE_IPS} ${MQTT_LOADTEST_WHITELIST_IPS}|" "$JAIL_FILE"

echo "Updated $JAIL_FILE:"
grep "^ignoreip" "$JAIL_FILE"

fail2ban-client reload mosquitto
echo "Reloaded fail2ban jail 'mosquitto'."
