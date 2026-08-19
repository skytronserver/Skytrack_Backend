#!/bin/bash

# Load environment variables from a configurable file.
# Priority: ENV_FILE, then .env, then .renv.
ENV_FILE="${ENV_FILE:-.env}"
if [ ! -f "$ENV_FILE" ] && [ -f ".renv" ]; then
  ENV_FILE=".renv"
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE"
  exit 1
fi

source "$ENV_FILE"
echo "Loaded environment from: $ENV_FILE"

if [ -z "$DB_HOST" ]; then
  echo "DB_HOST is not set in $ENV_FILE"
  exit 1
fi
echo "Using DB_HOST: $DB_HOST"

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

# Decide whether to use proxy for docker build based on DB_HOST
PROXY_ARGS=""
if [ "$DB_HOST" = "10.192.136.184" ]; then
  echo "Detected production DB_HOST ($DB_HOST): enabling proxy for Docker build"
  PROXY_ARGS="\
    --build-arg http_proxy=http://192.0.2.12:8080 \
    --build-arg https_proxy=http://192.0.2.12:8080 \
    --build-arg HTTP_PROXY=http://192.0.2.12:8080 \
    --build-arg HTTPS_PROXY=http://192.0.2.12:8080 \
    --build-arg ftp_proxy=http://192.0.2.12:8080 \
    --build-arg FTP_PROXY=http://192.0.2.12:8080"
else
  echo "Detected non-production DB_HOST ($DB_HOST): building without proxy"
fi

# Build the Docker image with build arguments
docker build -t skytron-backend-api -f Skytronsystem/dockerfile.api \
  $PROXY_ARGS \
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
  --build-arg GPS_REVERSE_GEOCODE_ENABLED="$GPS_REVERSE_GEOCODE_ENABLED" \
  --build-arg GPS_REVERSE_GEOCODE_TIMEOUT="$GPS_REVERSE_GEOCODE_TIMEOUT" \
  --build-arg GPS_REVERSE_GEOCODE_COOLDOWN="$GPS_REVERSE_GEOCODE_COOLDOWN" \
  --build-arg GPS_REVERSE_GEOCODE_ROOT="$GPS_REVERSE_GEOCODE_ROOT" \
  --build-arg MINIO_ENDPOINT="$MINIO_ENDPOINT" \
  --build-arg MINIO_ACCESS_KEY="$MINIO_ACCESS_KEY" \
  --build-arg MINIO_SECRET_KEY="$MINIO_SECRET_KEY" \
  --build-arg MINIO_BUCKET="$MINIO_BUCKET" \
  --build-arg MINIO_SECURE="$MINIO_SECURE" \
  --build-arg ALLOWALLDEVMQTT="$ALLOWALLDEVMQTT" \
  --build-arg LOAD_TEST_SECRET="$LOAD_TEST_SECRET" \
  --build-arg DISABLE_THROTTLE="$DISABLE_THROTTLE" \
  Skytronsystem/
 
# Stop any running container with the same name
docker stop skytron-backend-api-container || true
docker rm skytron-backend-api-container || true

# Run the container with the volume mount (environment variables are now baked into the image)
sudo docker run -d --restart=always \
  --network "$NETWORK_NAME" \
  -p 2000:2000 \
  -v $STORAGE_DIR:/host_storage \
  -v /home/azureuser/Skytrack_Backend/SKTN:/app/SKTN \
  --name skytron-backend-api-container \
  skytron-backend-api

echo "Docker container started with host storage mounted at /host_storage"
echo "Firmware files will be stored in /home/azureuser/Skytrack_Backend/SKTN on the host machine"
#@SET PORT1-6000*
#@GET DEBUG   @CLR SOSDIS-1*
#@GET LOC*

#@SETREGNO-DL333*
# @CLR SOSDIS-1*
#@SETREGNO-DL00000*
#@GETREGNO*
#   @GETLOC*        @SETPROF-2*

#source .venv/bin/activate
#cd Skytronsystem
#python manage.py migrate skytron_api
