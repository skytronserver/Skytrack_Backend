#!/bin/bash

# Run the host storage setup script first
bash setup_host_storage.sh

# Path to host storage directory
STORAGE_DIR="/var/skytrack_storage"

# Build the Docker image
docker build -t skytron-backend-api -f Skytronsystem/dockerfile.api Skytronsystem/
 
# Stop any running container with the same name
docker stop skytron-backend-api-container || true
docker rm skytron-backend-api-container || true

# Run the container with the volume mount
 
sudo docker run -d  --restart=always -p 2000:2000  -v $STORAGE_DIR:/host_storage  -e  MAIL_ID=noreply@skytron.in  -e  MAIL_PW=Developer@18062025  --name skytron-backend-api-container skytron-backend-api 

echo "Docker container started with host storage mounted at /host_storage"
echo "Files saved through the API will be stored in $STORAGE_DIR on the host machine"
