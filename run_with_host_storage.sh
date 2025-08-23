#!/bin/bash

# Load environment variables from .env file
source .env

# Run the host storage setup script first
bash setup_host_storage.sh

# Path to host storage directory
STORAGE_DIR="/var/skytrack_storage"

# Ensure a dedicated Docker network exists so containers can resolve each other by name
NETWORK_NAME="skytron-net"
docker network create "$NETWORK_NAME" >/dev/null 2>&1 || true

# Refresh Redis container to match Django CACHES LOCATION: redis://skytron-redis:6379/1
echo "Stopping and removing any existing Redis container (skytron-redis) ..."
docker stop skytron-redis >/dev/null 2>&1 || true
docker rm skytron-redis >/dev/null 2>&1 || true

echo "Starting Redis container (skytron-redis) on network $NETWORK_NAME ..."
docker run -d \
  --name skytron-redis \
  --restart unless-stopped \
  --network "$NETWORK_NAME" \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes
echo "Redis is running and reachable at redis://skytron-redis:6379"

# Build the Docker image with build arguments
docker build -t skytron-backend-api -f Skytronsystem/dockerfile.api \
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
docker stop skytron-backend-api-container || true
docker rm skytron-backend-api-container || true

# Run the container with the volume mount (environment variables are now baked into the image)
sudo docker run -d --restart=always \
  --network "$NETWORK_NAME" \
  -p 2000:2000 \
  -v $STORAGE_DIR:/host_storage \
  --name skytron-backend-api-container \
  skytron-backend-api 

echo "Docker container started with host storage mounted at /host_storage"
echo "Files saved through the API will be stored in $STORAGE_DIR on the host machine"
