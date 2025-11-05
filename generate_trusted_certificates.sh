#!/bin/bash
# Generate Proper Certificate Chain for MQTT Broker
# Creates: Root CA → Intermediate CA → Server Certificate
# This creates a proper chain of trust for security compliance

set -e  # Exit on any error

# Get script directory for portable paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$SCRIPT_DIR/mqtt_certificates"

# Configuration
COUNTRY="IN"
STATE="Assam"
CITY="Guwahati"
ORGANIZATION="SKYTRON"
ROOT_CN="SKYTRON Root CA"
INTERMEDIATE_CN="SKYTRON Intermediate CA"
SERVER_CN="mqtt.gromed.in"

# IP addresses and DNS names for the server
SERVER_IPS=(
    "127.0.0.1"
    "10.192.136.179"
    "135.235.166.209"
    "103.195.217.127"
)

SERVER_DNS=(
    "localhost"
    "mqtt.gromed.in"
    "api.gromed.in"
    "*.skytron.in"
)

# Certificate validity periods
ROOT_CA_DAYS=7300      # 20 years
INTERMEDIATE_DAYS=3650 # 10 years
SERVER_DAYS=825        # ~2 years (industry standard)

echo "==============================================="
echo "MQTT Certificate Chain Generator"
echo "==============================================="
echo "This will create a proper certificate chain:"
echo "  Root CA → Intermediate CA → Server Certificate"
echo ""

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$CERT_DIR"/{root_ca,intermediate_ca,server,client}
cd "$CERT_DIR"

# =====================================================
# STEP 1: Create Root CA (Self-signed)
# =====================================================
echo ""
echo "[1/6] Generating Root CA..."

cat > root_ca/root_ca.conf <<EOF
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_ca

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORGANIZATION
OU=Certificate Authority
CN=$ROOT_CN

[v3_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical,CA:TRUE
keyUsage = critical,digitalSignature,cRLSign,keyCertSign
EOF

# Generate Root CA private key
openssl genrsa -out root_ca/root_ca.key 4096

# Generate Root CA certificate (self-signed)
openssl req -x509 -new -nodes \
    -key root_ca/root_ca.key \
    -sha256 \
    -days $ROOT_CA_DAYS \
    -out root_ca/root_ca.crt \
    -config root_ca/root_ca.conf

chmod 600 root_ca/root_ca.key
chmod 644 root_ca/root_ca.crt

echo "✓ Root CA created (valid for $ROOT_CA_DAYS days)"

# =====================================================
# STEP 2: Create Intermediate CA
# =====================================================
echo ""
echo "[2/6] Generating Intermediate CA..."

cat > intermediate_ca/intermediate_ca.conf <<EOF
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORGANIZATION
OU=Certificate Authority
CN=$INTERMEDIATE_CN

[v3_intermediate_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical,CA:TRUE,pathlen:0
keyUsage = critical,digitalSignature,cRLSign,keyCertSign
EOF

# Generate Intermediate CA private key
openssl genrsa -out intermediate_ca/intermediate_ca.key 4096

# Generate Intermediate CA certificate signing request (without extensions in CSR)
openssl req -new \
    -key intermediate_ca/intermediate_ca.key \
    -out intermediate_ca/intermediate_ca.csr \
    -config intermediate_ca/intermediate_ca.conf

# Sign Intermediate CA with Root CA (add extensions during signing)
openssl x509 -req \
    -in intermediate_ca/intermediate_ca.csr \
    -CA root_ca/root_ca.crt \
    -CAkey root_ca/root_ca.key \
    -CAcreateserial \
    -out intermediate_ca/intermediate_ca.crt \
    -days $INTERMEDIATE_DAYS \
    -sha256 \
    -extensions v3_intermediate_ca \
    -extfile intermediate_ca/intermediate_ca.conf

chmod 600 intermediate_ca/intermediate_ca.key
chmod 644 intermediate_ca/intermediate_ca.crt

echo "✓ Intermediate CA created (valid for $INTERMEDIATE_DAYS days)"

# =====================================================
# STEP 3: Create Certificate Chain File
# =====================================================
echo ""
echo "[3/6] Creating certificate chain..."

# Create chain: Server cert will reference this
cat intermediate_ca/intermediate_ca.crt root_ca/root_ca.crt > intermediate_ca/ca_chain.crt

echo "✓ Certificate chain created"

# =====================================================
# STEP 4: Generate Server Certificate
# =====================================================
echo ""
echo "[4/6] Generating Server Certificate..."

# Build SAN (Subject Alternative Names) configuration
SAN_CONFIG="[alt_names]"$'\n'
dns_count=1
for dns in "${SERVER_DNS[@]}"; do
    SAN_CONFIG+="DNS.$dns_count = $dns"$'\n'
    ((dns_count++))
done

ip_count=1
for ip in "${SERVER_IPS[@]}"; do
    SAN_CONFIG+="IP.$ip_count = $ip"$'\n'
    ((ip_count++))
done

cat > server/server.conf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORGANIZATION
OU=MQTT Server
CN=$SERVER_CN

[v3_req]
basicConstraints = CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

$SAN_CONFIG
EOF

# Generate server private key
openssl genrsa -out server/server.key 2048

# Generate server certificate signing request
openssl req -new \
    -key server/server.key \
    -out server/server.csr \
    -config server/server.conf

# Sign server certificate with Intermediate CA
openssl x509 -req \
    -in server/server.csr \
    -CA intermediate_ca/intermediate_ca.crt \
    -CAkey intermediate_ca/intermediate_ca.key \
    -CAcreateserial \
    -out server/server.crt \
    -days $SERVER_DAYS \
    -sha256 \
    -extensions v3_req \
    -extfile server/server.conf

chmod 600 server/server.key
chmod 644 server/server.crt

# Create server certificate chain (server + intermediate + root)
cat server/server.crt intermediate_ca/intermediate_ca.crt root_ca/root_ca.crt > server/server_chain.crt

echo "✓ Server certificate created (valid for $SERVER_DAYS days)"

# =====================================================
# STEP 5: Generate Client Certificate (Optional)
# =====================================================
echo ""
echo "[5/6] Generating Client Certificate..."

cat > client/client.conf <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORGANIZATION
OU=MQTT Client
CN=mqtt.client

[v3_req]
basicConstraints = CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = clientAuth
EOF

# Generate client private key
openssl genrsa -out client/client.key 2048

# Generate client certificate signing request
openssl req -new \
    -key client/client.key \
    -out client/client.csr \
    -config client/client.conf

# Sign client certificate with Intermediate CA
openssl x509 -req \
    -in client/client.csr \
    -CA intermediate_ca/intermediate_ca.crt \
    -CAkey intermediate_ca/intermediate_ca.key \
    -CAcreateserial \
    -out client/client.crt \
    -days $SERVER_DAYS \
    -sha256 \
    -extensions v3_req \
    -extfile client/client.conf

chmod 600 client/client.key
chmod 644 client/client.crt

echo "✓ Client certificate created"

# =====================================================
# STEP 6: Deploy to Mosquitto
# =====================================================
echo ""
echo "[6/6] Deploying certificates to Mosquitto..."

MOSQUITTO_CERT_DIR="/etc/mosquitto/certs"

if [ -d "$MOSQUITTO_CERT_DIR" ]; then
    # Backup existing certificates
    if [ -f "$MOSQUITTO_CERT_DIR/ca.crt" ]; then
        echo "  Backing up existing certificates..."
        sudo cp -r "$MOSQUITTO_CERT_DIR" "${MOSQUITTO_CERT_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Copy new certificates
    echo "  Copying certificates to $MOSQUITTO_CERT_DIR..."
    sudo cp root_ca/root_ca.crt "$MOSQUITTO_CERT_DIR/ca.crt"
    sudo cp intermediate_ca/ca_chain.crt "$MOSQUITTO_CERT_DIR/ca_chain.crt"
    sudo cp server/server.crt "$MOSQUITTO_CERT_DIR/server.crt"
    sudo cp server/server.key "$MOSQUITTO_CERT_DIR/server.key"
    sudo cp server/server_chain.crt "$MOSQUITTO_CERT_DIR/server_chain.crt"
    
    # Set proper permissions
    sudo chown mosquitto:mosquitto "$MOSQUITTO_CERT_DIR"/*.{crt,key} 2>/dev/null || true
    sudo chmod 644 "$MOSQUITTO_CERT_DIR"/*.crt
    sudo chmod 600 "$MOSQUITTO_CERT_DIR"/*.key
    
    echo "✓ Certificates deployed to Mosquitto"
else
    echo "  WARNING: $MOSQUITTO_CERT_DIR not found. Skipping deployment."
    echo "  You'll need to manually copy certificates."
fi

# =====================================================
# Summary and Instructions
# =====================================================
echo ""
echo "==============================================="
echo "Certificate Generation Complete!"
echo "==============================================="
echo ""
echo "Generated Certificates:"
echo "  Root CA:         $CERT_DIR/root_ca/root_ca.crt"
echo "  Intermediate CA: $CERT_DIR/intermediate_ca/intermediate_ca.crt"
echo "  CA Chain:        $CERT_DIR/intermediate_ca/ca_chain.crt"
echo "  Server Cert:     $CERT_DIR/server/server.crt"
echo "  Server Key:      $CERT_DIR/server/server.key"
echo "  Server Chain:    $CERT_DIR/server/server_chain.crt"
echo "  Client Cert:     $CERT_DIR/client/client.crt"
echo "  Client Key:      $CERT_DIR/client/client.key"
echo ""
echo "Certificate Validity:"
echo "  Root CA:         $ROOT_CA_DAYS days (~20 years)"
echo "  Intermediate CA: $INTERMEDIATE_DAYS days (~10 years)"
echo "  Server & Client: $SERVER_DAYS days (~2 years)"
echo ""
echo "Next Steps:"
echo ""
echo "1. Update Mosquitto TLS Configuration:"
echo "   Edit: /etc/mosquitto/conf.d/tls.conf"
echo ""
echo "   listener 8883"
echo "   cafile /etc/mosquitto/certs/ca_chain.crt"
echo "   certfile /etc/mosquitto/certs/server.crt"
echo "   keyfile /etc/mosquitto/certs/server.key"
echo "   require_certificate false"
echo "   use_identity_as_username false"
echo ""
echo "2. Restart Mosquitto:"
echo "   sudo systemctl restart mosquitto"
echo ""
echo "3. Distribute Root CA to Clients:"
echo "   File: $CERT_DIR/root_ca/root_ca.crt"
echo "   Clients must use this CA certificate for validation"
echo ""
echo "4. Test Connection (with validation enabled):"
echo "   mosquitto_sub -h mqtt.gromed.in -p 8883 \\"
echo "     --cafile $CERT_DIR/root_ca/root_ca.crt \\"
echo "     -u \"jwt\" -P \"YOUR_JWT_TOKEN\" \\"
echo "     -t \"test/topic\" -v"
echo ""
echo "5. Verify Certificate Chain:"
echo "   openssl verify -CAfile $CERT_DIR/intermediate_ca/ca_chain.crt \\"
echo "     $CERT_DIR/server/server.crt"
echo ""
echo "Security Notes:"
echo "  ✓ Root CA key is secure (keep it safe and offline)"
echo "  ✓ Intermediate CA signs server certificates"
echo "  ✓ Proper certificate chain established"
echo "  ✓ Industry-standard validity periods"
echo "  ✓ Multiple SANs configured for flexibility"
echo ""
echo "For Python/Java clients, install root CA in system trust store"
echo "or provide ca.crt file path in SSL context."
echo ""
echo "==============================================="
