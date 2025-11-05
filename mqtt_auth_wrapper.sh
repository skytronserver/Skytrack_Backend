#!/bin/bash
# MQTT Authentication Script for Mosquitto
# This script is called by Mosquitto for authentication
# It supports both JWT tokens and username/password authentication
#
# Usage: Called automatically by Mosquitto with environment variables:
#   $1 = username
#   $2 = password (or JWT token)
#
# Exit codes:
#   0 = Authentication successful
#   1 = Authentication failed

USERNAME="$1"
PASSWORD="$2"

LOG_FILE="/var/log/mqtt_auth_wrapper.log"

# Log function
log_auth() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_auth "Auth attempt - Username: '$USERNAME', Password length: ${#PASSWORD}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call the Python authentication script using relative path
/usr/bin/python3 "$SCRIPT_DIR/mqtt_unified_auth.py" "$USERNAME" "$PASSWORD"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_auth "Authentication SUCCESS for: $USERNAME"
else
    log_auth "Authentication FAILED for: $USERNAME"
fi

exit $EXIT_CODE
