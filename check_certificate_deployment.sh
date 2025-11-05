#!/bin/bash
# MQTT Certificate Chain Deployment Checklist
# Run this script to prepare for secure MQTT deployment with proper certificate validation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "MQTT Certificate Chain Deployment Checklist"
echo "=============================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Track completion
all_good=true

echo "Checking prerequisites..."
echo ""

# Check 1: Certificate generation script exists
echo -n "[1/7] Checking certificate generation script... "
if [ -f "./generate_trusted_certificates.sh" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "  Missing: generate_trusted_certificates.sh"
    all_good=false
fi

# Check 2: Certificates generated
echo -n "[2/7] Checking if certificates are generated... "
if [ -d "./mqtt_certificates/root_ca" ] && [ -f "./mqtt_certificates/root_ca/root_ca.crt" ]; then
    echo -e "${GREEN}✓${NC}"
    echo "  Root CA: mqtt_certificates/root_ca/root_ca.crt"
    echo "  Valid until: $(openssl x509 -in mqtt_certificates/root_ca/root_ca.crt -noout -enddate | cut -d= -f2)"
else
    echo -e "${YELLOW}⚠${NC}"
    echo "  Certificates not generated yet."
    echo "  Run: sudo ./generate_trusted_certificates.sh"
    all_good=false
fi

# Check 3: Root CA copied for Docker build
echo -n "[3/7] Checking root CA in Skytronsystem directory... "
if [ -f "./Skytronsystem/root_ca.crt" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC}"
    if [ -f "./mqtt_certificates/root_ca/root_ca.crt" ]; then
        echo "  Copying root CA for Docker build..."
        cp mqtt_certificates/root_ca/root_ca.crt Skytronsystem/root_ca.crt
        echo -e "  ${GREEN}✓${NC} Copied"
    else
        echo "  Run: sudo ./generate_trusted_certificates.sh first"
        all_good=false
    fi
fi

# Check 4: Mosquitto certificates deployed
echo -n "[4/7] Checking Mosquitto certificates... "
if [ -f "/etc/mosquitto/certs/server.crt" ] && [ -f "/etc/mosquitto/certs/ca_chain.crt" ]; then
    echo -e "${GREEN}✓${NC}"
    echo "  Server cert: /etc/mosquitto/certs/server.crt"
    echo "  CA chain: /etc/mosquitto/certs/ca_chain.crt"
else
    echo -e "${YELLOW}⚠${NC}"
    echo "  Mosquitto certificates not deployed"
    echo "  Run: sudo ./generate_trusted_certificates.sh (it will deploy automatically)"
    all_good=false
fi

# Check 5: Mosquitto TLS configuration
echo -n "[5/7] Checking Mosquitto TLS configuration... "
if [ -f "/etc/mosquitto/conf.d/tls.conf" ]; then
    if grep -q "ca_chain.crt" /etc/mosquitto/conf.d/tls.conf; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC}"
        echo "  TLS config exists but may not use ca_chain.crt"
        echo "  Update cafile to: /etc/mosquitto/certs/ca_chain.crt"
    fi
else
    echo -e "${RED}✗${NC}"
    echo "  Missing: /etc/mosquitto/conf.d/tls.conf"
    all_good=false
fi

# Check 6: Python MQTT client configuration
echo -n "[6/7] Checking Python MQTT client configuration... "
if grep -q "CERT_REQUIRED" Skytronsystem/mqttClienttrack.py; then
    echo -e "${GREEN}✓${NC}"
    echo "  Certificate validation enabled (security audit compliant)"
else
    echo -e "${YELLOW}⚠${NC}"
    echo "  May need to update mqttClienttrack.py"
    echo "  Should use: cert_reqs=ssl.CERT_REQUIRED"
fi

# Check 7: Dockerfile includes root CA
echo -n "[7/7] Checking Dockerfile includes root CA... "
if grep -q "root_ca.crt" Skytronsystem/dockerfile.api; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC}"
    echo "  Dockerfile may not copy root CA certificate"
    all_good=false
fi

echo ""
echo "=============================================="
echo "Summary"
echo "=============================================="
echo ""

if [ "$all_good" = true ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Restart Mosquitto: sudo systemctl restart mosquitto"
    echo "2. Rebuild Django container: ./run_with_host_storage.sh"
    echo "3. Test connection with certificate validation"
    echo ""
else
    echo -e "${YELLOW}⚠ Some items need attention (see above)${NC}"
    echo ""
    echo "Recommended actions:"
    echo ""
    
    if [ ! -d "./mqtt_certificates/root_ca" ]; then
        echo "1. Generate certificates:"
        echo "   sudo ./generate_trusted_certificates.sh"
        echo ""
    fi
    
    if [ ! -f "./Skytronsystem/root_ca.crt" ] && [ -f "./mqtt_certificates/root_ca/root_ca.crt" ]; then
        echo "2. Copy root CA for Docker build:"
        echo "   cp mqtt_certificates/root_ca/root_ca.crt Skytronsystem/root_ca.crt"
        echo ""
    fi
    
    echo "3. Update Mosquitto TLS config (/etc/mosquitto/conf.d/tls.conf):"
    echo "   cafile /etc/mosquitto/certs/ca_chain.crt"
    echo "   certfile /etc/mosquitto/certs/server.crt"
    echo "   keyfile /etc/mosquitto/certs/server.key"
    echo ""
    
    echo "4. Restart Mosquitto:"
    echo "   sudo systemctl restart mosquitto"
    echo ""
    
    echo "5. Rebuild Django container:"
    echo "   ./run_with_host_storage.sh"
    echo ""
fi

echo "=============================================="
echo ""
echo "Testing commands:"
echo ""
echo "# Test MQTT connection with certificate validation"
echo "mosquitto_sub -h mqtt.gromed.in -p 8883 \\"
echo "  --cafile mqtt_certificates/root_ca/root_ca.crt \\"
echo "  -u \"jwt\" -P \"YOUR_JWT_TOKEN\" \\"
echo "  -t \"test/topic\" -v"
echo ""
echo "# Verify certificate chain"
echo "openssl verify -CAfile mqtt_certificates/intermediate_ca/ca_chain.crt \\"
echo "  mqtt_certificates/server/server.crt"
echo ""
echo "# Check Mosquitto is using correct certificates"
echo "sudo journalctl -u mosquitto -n 50"
echo ""
echo "=============================================="
echo ""
echo "Documentation:"
echo "  - Certificate generation: generate_trusted_certificates.sh"
echo "  - Security guide: CERTIFICATE_CHAIN_SECURITY.md"
echo "  - Deployment guide: DEPLOYMENT_PORTABILITY.md"
echo ""
