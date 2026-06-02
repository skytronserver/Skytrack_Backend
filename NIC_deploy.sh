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
sudo ./run_with_host_storage.sh
sudo ./run_mqtt.sh
