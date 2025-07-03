#!/bin/bash

# Move to the project root directory
cd /home/azureuser/Skytrack_Backend

# Build the Docker image
echo "Building Docker image..."
docker build -t skytrack-mqtt -f Skytronsystem/dockerfile.mqtt .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "Docker image built successfully!"
    
    # Run the container
    echo "Starting the MQTT client container..."
    docker run -d --name skytrack-mqtt-client skytrack-mqtt
    
    # Check container status
    echo "Container status:"
    docker ps | grep skytrack-mqtt-client
    
    echo "To view logs, run: docker logs skytrack-mqtt-client"
else
    echo "Docker build failed. Please check the errors above."
fi
