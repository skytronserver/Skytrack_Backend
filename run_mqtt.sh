#!/bin/bash

# Load environment variables from .env file
source .env

# Run the host storage setup script first
bash setup_host_storage.sh

# Path to host storage directory
STORAGE_DIR="/var/skytrack_storage"

# Build the Docker image with build arguments
docker build -t skytrack-mqtt-client -f Skytronsystem/dockerfile.mqtt \
  --build-arg http_proxy=http://192.0.2.12:8080 \
  --build-arg https_proxy=http://192.0.2.12:8080 \
  --build-arg HTTP_PROXY=http://192.0.2.12:8080 \
  --build-arg HTTPS_PROXY=http://192.0.2.12:8080 \
  --build-arg ftp_proxy=http://192.0.2.12:8080 \
  --build-arg FTP_PROXY=http://192.0.2.12:8080 \
  --build-arg MAIL_ID="$MAIL_ID" \
  --build-arg MAIL_PW="$MAIL_PW" \
  --build-arg DEBUG="$DEBUG" \
  --build-arg SECRET_KEY="$SECRET_KEY" \
  --build-arg EMAIL_HOST_USER="$EMAIL_HOST_USER" \
  --build-arg EMAIL_HOST_PASSWORD="$EMAIL_HOST_PASSWORD" \
  --build-arg ALLOWED_HOSTS="$ALLOWED_HOSTS" \
  --build-arg DB_NAME="$DB_NAME" \
  --build-arg DB_USER="$DB_USER" \
  --build-arg DB_PASSWORD="$DB_PASSWORD" \
  --build-arg DB_HOST="$DB_HOST" \
  --build-arg DB_PORT="$DB_PORT" \
  --build-arg SMS_URL="$SMS_URL" \
  --build-arg SMS_USERID="$SMS_USERID" \
  --build-arg SMS_PASSWORD="$SMS_PASSWORD" \
  --build-arg SMS_SENDER="$SMS_SENDER" \
  --build-arg SMS_PEID="$SMS_PEID" \
  --build-arg MQTT_BROKER_HOST="$MQTT_BROKER_HOST" \
  --build-arg MQTT_BROKER_PORT="$MQTT_BROKER_PORT" \
  --build-arg MQTT_ADMIN_USER="$MQTT_ADMIN_USER" \
  --build-arg MQTT_ADMIN_PASS="$MQTT_ADMIN_PASS" \
  --build-arg MQTT_USERNAME="$MQTT_USERNAME" \
  --build-arg MQTT_PASSWORD="$MQTT_PASSWORD" \
  --build-arg ROOT_URL="$ROOT_URL" \
  --build-arg JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  --build-arg JWT_ALGORITHM="$JWT_ALGORITHM" \
  --build-arg JWT_ACCESS_TOKEN_LIFETIME="$JWT_ACCESS_TOKEN_LIFETIME" \
  --build-arg JWT_REFRESH_TOKEN_LIFETIME="$JWT_REFRESH_TOKEN_LIFETIME" \
  Skytronsystem/
 
# Stop any running container with the same name
docker stop skytrack-mqtt-client-container || true
docker rm skytrack-mqtt-client-container || true

# Run migrations first in a temporary container
echo "Running database migrations..."
docker run --rm --name skytrack-mqtt-migration skytrack-mqtt-client python manage.py makemigrations skytron_api
docker run --rm --name skytrack-mqtt-migration skytrack-mqtt-client python manage.py migrate --run-syncdb

# Run the container with the volume mount (environment variables are now baked into the image)
sudo docker run -d --restart=always  -v $STORAGE_DIR:/host_storage --name skytrack-mqtt-client-container skytrack-mqtt-client



 
