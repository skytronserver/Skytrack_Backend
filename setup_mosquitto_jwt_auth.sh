#!/bin/bash
#
# Setup mosquitto-go-auth plugin for JWT-based MQTT authentication
# This script should be run on the host machine (not in Docker) where Mosquitto is installed
#
# Usage: sudo bash setup_mosquitto_jwt_auth.sh
#

set -e

echo "======================================"
echo "Mosquitto JWT Authentication Setup"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Check if mosquitto is installed
if ! command -v mosquitto &> /dev/null; then
    echo "ERROR: Mosquitto is not installed. Please install it first."
    exit 1
fi

echo ""
echo "Step 1: Installing mosquitto-go-auth plugin..."
echo "----------------------------------------------"

# Check if plugin already exists
if [ -f "/usr/lib/x86_64-linux-gnu/go-auth.so" ]; then
    echo "✓ Plugin already installed at /usr/lib/x86_64-linux-gnu/go-auth.so"
else
    echo "Downloading mosquitto-go-auth v3.0.0..."
    
    # Install unzip if not present
    if ! command -v unzip &> /dev/null; then
        echo "Installing unzip..."
        apt-get update && apt-get install -y unzip
    fi
    
    # Download and extract
    cd /tmp
    wget -q https://github.com/iegomez/mosquitto-go-auth/releases/download/3.0.0/linux-amd64.zip
    unzip -o linux-amd64.zip
    
    # Install plugin
    cp linux-amd64/go-auth.so /usr/lib/x86_64-linux-gnu/
    cp linux-amd64/pw /usr/local/bin/
    
    # Cleanup
    rm linux-amd64.zip
    rm -rf linux-amd64
    
    echo "✓ Plugin installed successfully"
fi

echo ""
echo "Step 2: Configuring mosquitto-go-auth..."
echo "----------------------------------------------"

# Copy go-auth configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/go-auth.conf" ]; then
    cp "$SCRIPT_DIR/go-auth.conf" /etc/mosquitto/conf.d/
    echo "✓ Configuration copied to /etc/mosquitto/conf.d/go-auth.conf"
else
    echo "WARNING: go-auth.conf not found in $SCRIPT_DIR"
    echo "Creating default configuration..."
    
    cat > /etc/mosquitto/conf.d/go-auth.conf <<'EOF'
# Mosquitto Go Auth Plugin Configuration
# JWT-based authentication via HTTP backend

# Load the plugin
auth_plugin /usr/lib/x86_64-linux-gnu/go-auth.so

# Log level (debug, info, warn, error)
auth_opt_log_level info

# Backends to use (http for API validation)
auth_opt_backends http

# Cache settings (optional, improves performance)
auth_opt_cache true
auth_opt_cache_type redis
auth_opt_cache_reset true
auth_opt_cache_refresh true
auth_opt_auth_cache_seconds 30
auth_opt_acl_cache_seconds 30

# HTTP Backend Configuration
auth_opt_http_host 127.0.0.1
auth_opt_http_port 2000
auth_opt_http_getuser_uri /api/mqtt/validate-connection/
auth_opt_http_aclcheck_uri /api/mqtt/validate-acl/
auth_opt_http_superuser_uri /api/mqtt/validate-connection/

# HTTP request settings
auth_opt_http_with_tls false
auth_opt_http_verify_peer false
auth_opt_http_timeout 5

# Request format
auth_opt_http_method POST
auth_opt_http_params_mode json

# Response mode (200 = success)
auth_opt_http_response_mode status
EOF
    
    echo "✓ Default configuration created"
fi

echo ""
echo "Step 3: Disabling dynamic-security plugin..."
echo "----------------------------------------------"

# Disable dynamic security (conflicts with go-auth)
if [ -f "/etc/mosquitto/conf.d/dynsec.conf" ]; then
    mv /etc/mosquitto/conf.d/dynsec.conf /etc/mosquitto/conf.d/dynsec.conf.disabled
    echo "✓ Dynamic security disabled (renamed to dynsec.conf.disabled)"
else
    echo "✓ Dynamic security already disabled"
fi

echo ""
echo "Step 4: Restarting Mosquitto..."
echo "----------------------------------------------"

systemctl restart mosquitto
sleep 2

if systemctl is-active --quiet mosquitto; then
    echo "✓ Mosquitto restarted successfully"
else
    echo "ERROR: Mosquitto failed to start. Check logs with: journalctl -u mosquitto -n 50"
    exit 1
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "MQTT JWT Authentication is now configured."
echo ""
echo "Usage:"
echo "  mosquitto_sub -h 127.0.0.1 -p 8883 \\"
echo "    --cafile /etc/mosquitto/certs/ca.crt \\"
echo "    -u \"jwt\" \\"
echo "    -P \"YOUR_JWT_TOKEN\" \\"
echo "    -t \"test/topic\" -v"
echo ""
echo "Note:"
echo "  - Use any non-empty username (e.g., 'jwt')"
echo "  - Put the RS256 JWT token in the password field"
echo "  - Tokens are validated via Django API at http://127.0.0.1:2000/api/mqtt/validate-connection/"
echo ""
echo "To re-enable dynamic-security:"
echo "  sudo mv /etc/mosquitto/conf.d/dynsec.conf.disabled /etc/mosquitto/conf.d/dynsec.conf"
echo "  sudo mv /etc/mosquitto/conf.d/go-auth.conf /etc/mosquitto/conf.d/go-auth.conf.disabled"
echo "  sudo systemctl restart mosquitto"
echo ""
