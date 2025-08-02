#!/bin/bash

# Load environment variables from .env file
source .env

# Run the host storage setup script first
bash setup_host_storage.sh

# Path to host storage directory
STORAGE_DIR="/var/skytrack_storage"

# Build the Docker image with build arguments
docker build -t skytrack-mqtt-client -f Skytronsystem/dockerfile.mqtt \
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
  Skytronsystem/
 
# Stop any running container with the same name
docker stop skytrack-mqtt-client-container || true
docker rm skytrack-mqtt-client-container || true

# Run the container with the volume mount (environment variables are now baked into the image)
sudo docker run -d --restart=always  -v $STORAGE_DIR:/host_storage --name skytrack-mqtt-client-container skytrack-mqtt-client



 