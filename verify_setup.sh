#!/bin/bash
# Quick verification script for MQTT JWT Authentication setup

echo "=========================================="
echo "MQTT JWT Authentication - Setup Verification"
echo "=========================================="
echo ""

# Check if Django container is running
echo "✓ Checking Django container..."
if sudo docker ps | grep -q "skytron-backend-api-container"; then
    echo "  ✓ Django container is running"
else
    echo "  ✗ Django container is NOT running"
    echo "  Run: sudo docker start skytron-backend-api-container"
    exit 1
fi

# Check if Mosquitto is running
echo "✓ Checking MQTT broker..."
if sudo systemctl is-active --quiet mosquitto; then
    echo "  ✓ Mosquitto is running"
else
    echo "  ✗ Mosquitto is NOT running"
    echo "  Run: sudo systemctl start mosquitto"
    exit 1
fi

# Check if new files exist
echo "✓ Checking new files..."
FILES=(
    "/home/azureuser/Skytrack_Backend/Skytronsystem/skytron_api/mqtt_auth_views.py"
    "/home/azureuser/Skytrack_Backend/mqtt_unified_auth.py"
    "/home/azureuser/Skytrack_Backend/test_mqtt_jwt_auth.py"
    "/home/azureuser/Skytrack_Backend/mqtt_client_example.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $(basename $file)"
    else
        echo "  ✗ $(basename $file) NOT FOUND"
    fi
done

# Check if JWT keys exist
echo "✓ Checking JWT keys..."
if [ -f "/home/azureuser/Skytrack_Backend/Skytronsystem/keys/jwt_private_key.pem" ]; then
    echo "  ✓ JWT private key exists"
else
    echo "  ✗ JWT private key NOT FOUND"
fi

if [ -f "/home/azureuser/Skytrack_Backend/Skytronsystem/keys/jwt_public_key.pem" ]; then
    echo "  ✓ JWT public key exists"
else
    echo "  ✗ JWT public key NOT FOUND"
fi

# Check MQTT certificates
echo "✓ Checking MQTT certificates..."
if [ -f "/etc/mosquitto/certs/ca.crt" ]; then
    echo "  ✓ MQTT CA certificate exists"
else
    echo "  ✗ MQTT CA certificate NOT FOUND"
fi

# Test Django API endpoints
echo "✓ Testing API endpoints..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:2000/mqtt/prepare-auth-token/ \
    -X POST -H "Content-Type: application/json" -d '{"jwt_token":"test"}' 2>/dev/null)

if [ "$RESPONSE" == "400" ] || [ "$RESPONSE" == "401" ]; then
    echo "  ✓ /mqtt/prepare-auth-token/ endpoint is accessible (returned $RESPONSE as expected)"
elif [ "$RESPONSE" == "000" ]; then
    echo "  ✗ Cannot reach Django API on port 2000"
    echo "  Check if container is running and port is open"
else
    echo "  ⚠ Endpoint returned unexpected status: $RESPONSE"
fi

echo ""
echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Test with: python3 test_mqtt_jwt_auth.py"
echo "2. Review: QUICK_REFERENCE.md"
echo "3. Full docs: MQTT_JWT_AUTHENTICATION_GUIDE.md"
echo ""
