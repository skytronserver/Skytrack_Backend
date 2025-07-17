#!/bin/bash

# Load environment variables from .env file
source .env

# Run the host storage setup script first
bash setup_host_storage.sh

# Path to host storage directory
STORAGE_DIR="/var/skytrack_storage"

# Build the Docker image with build arguments
docker build -t skytron-backend-gps -f Skytronsystem/dockerfile.gps \
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
docker stop skytron-backend-gps-container || true
docker rm skytron-backend-gps-container || true

# Run the container with the volume mount (environment variables are now baked into the image)
sudo docker run -d --restart=always -p 6000:6000 -v $STORAGE_DIR:/host_storage --name skytron-backend-gps-container skytron-backend-gps







# Build the Docker image with build arguments
docker build -t skytron-backend-em -f Skytronsystem/dockerfile.em \
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
docker stop skytron-backend-em-container || true
docker rm skytron-backend-em-container || true

# Run the container with the volume mount (environment variables are now baked into the image)
sudo docker run -d --restart=always -p 5001:5001 -v $STORAGE_DIR:/host_storage --name skytron-backend-em-container skytron-backend-em



