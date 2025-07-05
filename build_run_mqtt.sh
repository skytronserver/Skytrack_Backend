#!/bin/bash
cd Skytronsystem
# Move to the project root directory
cd /home/azureuser/Skytrack_Backend

# Build the Docker image
echo "Building Docker image..."
docker build -t skytrack-mqtt -f Skytronsystem/dockerfile.mqtt .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Docker image built successfully!"
    
    # Check if container already exists and remove it
    echo "Checking for existing MQTT client container..."
    if docker ps -a | grep -q skytrack-mqtt-client; then
        echo "Found existing container, stopping and removing it..."
        docker stop skytrack-mqtt-client > /dev/null 2>&1
        docker rm skytrack-mqtt-client > /dev/null 2>&1
    fi
    
    # Run the container with restart policy
    echo "Starting the MQTT client container with auto-restart..."
    docker run -d --name skytrack-mqtt-client --restart unless-stopped skytrack-mqtt
    
    # Check if container started successfully
    if [ $? -eq 0 ]; then
        echo "Container status:"
        docker ps | grep skytrack-mqtt-client
        echo "To view logs, run: docker logs skytrack-mqtt-client"
    else
        echo "Failed to start container. Check docker logs for details."
        exit 1
    fi
else
    echo "Docker build failed. Please check the errors above."
fi
