#!/bin/bash
set -e

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
sudo rm -f /var/log/*-????????
sudo journalctl --vacuum-size=100M
sudo truncate -s 0 /var/log/mail.log
sudo truncate -s 0 /var/log/mail.info
sudo truncate -s 0 /var/log/mail.warn
sudo truncate -s 0 /var/log/mail.err
sudo truncate -s 0 /var/log/mail
sudo truncate -s 0 /var/log/syslog.1
sudo truncate -s 0 /var/log/warn
sudo truncate -s 0 /var/log/sudo.log
sudo truncate -s 0 /var/log/aide


sudo docker system prune -f
sudo ./run_with_host_storage.sh
sudo docker exec skytron-backend-api-container python manage.py migrate
sudo ./run_mqtt.sh

