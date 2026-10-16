#!/bin/bash
#   ./NIC_deploy.sh                  backend VM: API, MQTT client, migrations
#                                    (+ IP reporter if Mosquitto runs on this VM too)
#   ./NIC_deploy.sh mqtt-reporter    broker VM: only the MQTT IP reporter container.
#                                    First time: ./NIC_deploy.sh mqtt-reporter --key <MQTT_IP_REPORT_KEY>
#                                    (extra args go to run_mqtt_reporter.sh)
set -e

ROLE="${1:-backend}"
[ $# -gt 0 ] && shift

# Proxy settings — applied to this script and all child processes
export http_proxy="http://192.0.2.12:8080"
export https_proxy="http://192.0.2.12:8080"
export HTTP_PROXY="http://192.0.2.12:8080"
export HTTPS_PROXY="http://192.0.2.12:8080"
export ftp_proxy="http://192.0.2.12:8080"
export FTP_PROXY="http://192.0.2.12:8080"

git pull

# Run with sudo — scripts have their own env/Docker setup

sudo rm -f /var/log/*.gz
sudo find /var/log -maxdepth 1 -type f -name '*-????????' -delete
sudo journalctl --vacuum-size=100M
# Only truncate regular files — some servers have these as directories or not at all
for f in mail.log mail.info mail.warn mail.err mail syslog.1 warn sudo.log aide; do
    if sudo test -f "/var/log/$f"; then sudo truncate -s 0 "/var/log/$f"; fi
done


sudo docker system prune -f

case "$ROLE" in
  backend)
    sudo ./run_with_host_storage.sh
    sudo docker exec skytron-backend-api-container python manage.py migrate
    sudo ./run_mqtt.sh
    # Co-located broker (dev): keep the reporter on the current code too.
    if pgrep -x mosquitto >/dev/null; then
        sudo ./run_mqtt_reporter.sh "$@" || echo "WARN: MQTT IP reporter not deployed (see above)"
    fi
    ;;
  mqtt-reporter)
    sudo ./run_mqtt_reporter.sh "$@"
    ;;
  *)
    echo "Unknown role: $ROLE (use: backend | mqtt-reporter)" >&2
    exit 1
    ;;
esac
