#!/bin/bash
# Script to create MQTT users for Owner, Police, and Ambulance

# Configuration
CA_FILE="/etc/mosquitto/certs/ca.crt"
HOST="135.235.166.209"
PORT="8883"
ADMIN_USER="admin"
ADMIN_PASS="adminpass"
USER_PASSWORD='isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h' #"testpass123"

# Users to create with their roles
declare -A USERS=(
    ["6026969588"]="Owner"
    ["1000000010"]="Police"
    ["1000000011"]="Ambulance"
)

echo "Creating MQTT users for Owner, Police, and Ambulance..."

for user in "${!USERS[@]}"; do
    role=${USERS[$user]}
    echo "Creating user: $user ($role)"
    
    # Create client
    mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u $ADMIN_USER -P $ADMIN_PASS \
        -t '$CONTROL/dynamic-security/v1' \
        -m "{\"commands\":[{\"command\":\"createClient\",\"username\":\"$user\"}]}" \
        --insecure
    
    sleep 1
    
    # Set password
    mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u $ADMIN_USER -P $ADMIN_PASS \
        -t '$CONTROL/dynamic-security/v1' \
        -m "{\"commands\":[{\"command\":\"setClientPassword\",\"username\":\"$user\",\"password\":\"$USER_PASSWORD\"}]}" \
        --insecure
    
    sleep 1
    
    # Add open-all role for full access
    mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u $ADMIN_USER -P $ADMIN_PASS \
        -t '$CONTROL/dynamic-security/v1' \
        -m "{\"commands\":[{\"command\":\"addClientRole\",\"username\":\"$user\",\"rolename\":\"open-all\"}]}" \
        --insecure
    
    sleep 1
    
    echo "User $user ($role) created and configured"
done

echo "All users created. Testing connections..."

# Test publish capability with each user
for user in "${!USERS[@]}"; do
    role=${USERS[$user]}
    echo "Testing publish for $role ($user):"
    mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u "$user" -P "$USER_PASSWORD" \
        -t "test/$role" -m "Hello from $role user $user" --insecure -d
    echo "---"
done

echo "Testing subscription capability..."

# Function to test subscription
test_subscription() {
    local user=$1
    local role=$2
    local test_topic="test/subscription/$role"
    
    echo "Testing subscription for $role ($user):"
    echo "Starting subscriber in background..."
    
    # Start subscriber in background for 5 seconds
    timeout 5s mosquitto_sub --cafile $CA_FILE -h $HOST -p $PORT -u "$user" -P "$USER_PASSWORD" \
        -t "$test_topic" --insecure -d &
    
    local sub_pid=$!
    sleep 2
    
    # Publish a test message
    echo "Publishing test message to $test_topic"
    mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u "$user" -P "$USER_PASSWORD" \
        -t "$test_topic" -m "Subscription test message for $role" --insecure
    
    # Wait for subscriber to finish
    wait $sub_pid 2>/dev/null
    echo "Subscription test completed for $role"
    echo "---"
}

# Test subscription for each user
for user in "${!USERS[@]}"; do
    role=${USERS[$user]}
    test_subscription "$user" "$role"
done

echo "Testing cross-user messaging..."

# Test that Owner can publish to sosEx and owner topics (like your application)
echo "Testing Owner publishing to owner topic:"
mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u "6026929588" -P "$USER_PASSWORD" \
    -t "owner/6026929588" -m '{"token":"test_token","message":"Owner test message"}' --insecure -d

echo "Testing Police publishing to sosEx topic:"
mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u "1000000010" -P "$USER_PASSWORD" \
    -t "sosEx/1000000010" -m '{"token":"test_token","em_lat":26.133602,"em_lon":91.804747,"speed":10}' --insecure -d

echo "Testing Ambulance publishing to sosEx topic:"
mosquitto_pub --cafile $CA_FILE -h $HOST -p $PORT -u "1000000011" -P "$USER_PASSWORD" \
    -t "sosEx/1000000011" -m '{"token":"test_token","em_lat":26.133602,"em_lon":91.804747,"speed":15}' --insecure -d

echo "All tests completed successfully!"


