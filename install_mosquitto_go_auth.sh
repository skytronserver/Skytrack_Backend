#!/bin/bash
# Install mosquitto-go-auth plugin for JWT authentication

set -e

echo "Installing mosquitto-go-auth plugin..."

# Download mosquitto-go-auth
cd /tmp
wget https://github.com/iegomez/mosquitto-go-auth/releases/download/2.1.0/mosquitto-go-auth-2.1.0-linux-amd64.tar.gz
tar -xzf mosquitto-go-auth-2.1.0-linux-amd64.tar.gz

# Install plugin
sudo cp mosquitto-go-auth.so /usr/lib/mosquitto-go-auth.so
sudo chmod 755 /usr/lib/mosquitto-go-auth.so

# Backup current config
sudo cp /etc/mosquitto/conf.d/dynsec.conf /etc/mosquitto/conf.d/dynsec.conf.backup

# Create new auth config
sudo tee /etc/mosquitto/conf.d/go-auth.conf > /dev/null <<'EOF'
# External authentication via mosquitto-go-auth
auth_plugin /usr/lib/mosquitto-go-auth.so

# Use HTTP backend for authentication
auth_opt_backends http

# Django API endpoint for authentication
auth_opt_http_host 127.0.0.1
auth_opt_http_port 2000
auth_opt_http_getuser_uri /mqtt/validate-connection/
auth_opt_http_superuser_uri /mqtt/validate-connection/
auth_opt_http_aclcheck_uri /mqtt/validate-acl/

# HTTP request settings
auth_opt_http_with_tls false
auth_opt_http_method POST
auth_opt_http_response_mode status

# Enable username extraction from token
auth_opt_http_params_mode json

# Log level
auth_opt_log_level debug
EOF

echo "mosquitto-go-auth installed successfully!"
echo "Next steps:"
echo "1. Create Django endpoints: /mqtt/validate-connection/ and /mqtt/validate-acl/"
echo "2. Restart Mosquitto: sudo systemctl restart mosquitto"
echo "3. Test connection without username"
