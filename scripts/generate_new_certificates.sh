#!/bin/bash

# Generate New MQTT SSL Certificates with Multiple IPs
# This script creates a new CA and server certificate for all required IPs

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}MQTT SSL Certificate Generator${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Define IP addresses
IP1="135.235.166.209"
IP2="103.195.217.127"
IP3="10.192.136.179"

echo -e "${YELLOW}[INFO]${NC} Generating certificates for IPs:"
echo -e "  • ${IP1}"
echo -e "  • ${IP2}"
echo -e "  • ${IP3}"
echo ""

# Create temporary directory for certificate generation
CERT_DIR="/tmp/mqtt_new_certs"
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

echo -e "${YELLOW}[INFO]${NC} Working in directory: $CERT_DIR"

# 1. Generate CA Private Key
echo -e "${YELLOW}[INFO]${NC} Generating CA private key..."
openssl genrsa -out ca.key 4096
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} CA private key generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate CA private key"
    exit 1
fi

# 2. Generate CA Certificate
echo -e "${YELLOW}[INFO]${NC} Generating CA certificate..."
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/C=IN/ST=Assam/L=Guwahati/O=SKYTRON/OU=MQTT/CN=SKYTRON_MQTT_CA"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} CA certificate generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate CA certificate"
    exit 1
fi

# 3. Generate Server Private Key
echo -e "${YELLOW}[INFO]${NC} Generating server private key..."
openssl genrsa -out server.key 2048
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} Server private key generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate server private key"
    exit 1
fi

# 4. Create Server Certificate Extension File with Multiple IPs
echo -e "${YELLOW}[INFO]${NC} Creating certificate extension file..."
cat > server_ext.cnf << EOF
[req]
default_bits = 2048
prompt = no
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]
C = IN
ST = Assam
L = Guwahati
O = SKYTRON
OU = MQTT
CN = skytron_mqtt_server

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
IP.1 = ${IP1}
IP.2 = ${IP2}
IP.3 = ${IP3}
DNS.1 = localhost
DNS.2 = skytron_mqtt_server
EOF

echo -e "${GREEN}[✓]${NC} Certificate extension file created"

# 5. Generate Server Certificate Signing Request
echo -e "${YELLOW}[INFO]${NC} Generating server certificate signing request..."
openssl req -new -key server.key -out server.csr -config server_ext.cnf
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} Server CSR generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate server CSR"
    exit 1
fi

# 6. Generate Server Certificate signed by CA
echo -e "${YELLOW}[INFO]${NC} Generating server certificate signed by CA..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -extensions v3_req -extfile server_ext.cnf
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} Server certificate generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate server certificate"
    exit 1
fi

# 7. Generate Client Private Key
echo -e "${YELLOW}[INFO]${NC} Generating client private key..."
openssl genrsa -out client.key 2048
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} Client private key generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate client private key"
    exit 1
fi

# 8. Generate Client Certificate Signing Request
echo -e "${YELLOW}[INFO]${NC} Generating client certificate signing request..."
openssl req -new -key client.key -out client.csr -subj "/C=IN/ST=Assam/L=Guwahati/O=SKYTRON/OU=MQTT/CN=skytron_mqtt_client"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} Client CSR generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate client CSR"
    exit 1
fi

# 9. Generate Client Certificate signed by CA
echo -e "${YELLOW}[INFO]${NC} Generating client certificate signed by CA..."
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 365
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[✓]${NC} Client certificate generated"
else
    echo -e "${RED}[✗]${NC} Failed to generate client certificate"
    exit 1
fi

# 10. Set proper permissions
echo -e "${YELLOW}[INFO]${NC} Setting certificate permissions..."
chmod 644 *.crt
chmod 600 *.key
echo -e "${GREEN}[✓]${NC} Permissions set"

# 11. Verify the server certificate
echo -e "${YELLOW}[INFO]${NC} Verifying server certificate..."
echo ""
echo -e "${BLUE}Certificate Details:${NC}"
openssl x509 -in server.crt -text -noout | grep -A 10 "Subject Alternative Name"
echo ""

# 12. Copy certificates to mosquitto directory
echo -e "${YELLOW}[INFO]${NC} Installing certificates to mosquitto directory..."

# Backup existing certificates
if [ -d "/etc/mosquitto/certs" ]; then
    sudo cp -r /etc/mosquitto/certs /etc/mosquitto/certs.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}[✓]${NC} Existing certificates backed up"
fi

# Create certs directory if it doesn't exist
sudo mkdir -p /etc/mosquitto/certs/

# Copy new certificates
sudo cp ca.crt /etc/mosquitto/certs/
sudo cp server.crt /etc/mosquitto/certs/
sudo cp server.key /etc/mosquitto/certs/
sudo cp client.crt /etc/mosquitto/certs/
sudo cp client.key /etc/mosquitto/certs/

# Set ownership and permissions
sudo chown -R mosquitto:mosquitto /etc/mosquitto/certs/
sudo chmod 644 /etc/mosquitto/certs/*.crt
sudo chmod 600 /etc/mosquitto/certs/*.key

echo -e "${GREEN}[✓]${NC} Certificates installed to /etc/mosquitto/certs/"

# 13. Copy certificates to deployment package
echo -e "${YELLOW}[INFO]${NC} Updating deployment package..."
DEPLOY_CERT_DIR="/home/azureuser/Skytrack_Backend/mqtt_deployment/certs"
sudo cp ca.crt "$DEPLOY_CERT_DIR/"
sudo cp server.crt "$DEPLOY_CERT_DIR/"
sudo cp server.key "$DEPLOY_CERT_DIR/"
sudo cp client.crt "$DEPLOY_CERT_DIR/"
sudo cp client.key "$DEPLOY_CERT_DIR/"

sudo chown -R azureuser:azureuser "$DEPLOY_CERT_DIR/"
sudo chmod 644 "$DEPLOY_CERT_DIR/"*.crt
sudo chmod 600 "$DEPLOY_CERT_DIR/"*.key

echo -e "${GREEN}[✓]${NC} Deployment package updated"

# 14. Copy certificates to application directories
echo -e "${YELLOW}[INFO]${NC} Updating application certificates..."

# Copy to Skytronsystem directory
APP_CERT_DIR="/home/azureuser/Skytrack_Backend/Skytronsystem"
sudo cp ca.crt "$APP_CERT_DIR/"
sudo cp client.crt "$APP_CERT_DIR/"
sudo cp client.key "$APP_CERT_DIR/"

# Copy to keys directory for Docker
KEYS_DIR="/home/azureuser/Skytrack_Backend/Skytronsystem/keys"
sudo mkdir -p "$KEYS_DIR"
sudo cp ca.crt "$KEYS_DIR/"
sudo cp client.crt "$KEYS_DIR/"
sudo cp client.key "$KEYS_DIR/"

sudo chown -R azureuser:azureuser "$APP_CERT_DIR/"
sudo chown -R azureuser:azureuser "$KEYS_DIR/"

echo -e "${GREEN}[✓]${NC} Application certificates updated"

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Certificate Generation Complete!${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${YELLOW}Generated certificates for IPs:${NC}"
echo -e "  • ${IP1}"
echo -e "  • ${IP2}"
echo -e "  • ${IP3}"
echo ""
echo -e "${YELLOW}Certificate locations:${NC}"
echo -e "  • Mosquitto: /etc/mosquitto/certs/"
echo -e "  • Deployment: /home/azureuser/Skytrack_Backend/mqtt_deployment/certs/"
echo -e "  • Application: /home/azureuser/Skytrack_Backend/Skytronsystem/"
echo -e "  • Docker Keys: /home/azureuser/Skytrack_Backend/Skytronsystem/keys/"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Restart mosquitto: ${BLUE}sudo systemctl restart mosquitto${NC}"
echo -e "  2. Test connection: ${BLUE}mosquitto_pub -h ${IP3} -p 8883 --cafile ca.crt -u admin -P adminpass -t test -m hello${NC}"
echo -e "  3. Update your applications to use the new certificates"
echo ""
echo -e "${YELLOW}Temporary files in:${NC} $CERT_DIR"
echo -e "${YELLOW}You can remove them after verification:${NC} rm -rf $CERT_DIR"
echo ""