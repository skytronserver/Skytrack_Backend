#!/bin/bash
# Quick Deployment Checklist for New Server
# Run this script on the NEW server after transferring files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Skytrack Backend Deployment Checklist${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

all_good=true

echo -e "${YELLOW}[Phase 1] System Requirements${NC}"
echo ""

# Check Docker
echo -n "  [1.1] Docker installed: "
if command_exists docker; then
    echo -e "${GREEN}✓${NC} ($(docker --version | cut -d' ' -f3))"
else
    echo -e "${RED}✗${NC}"
    echo "       Install: curl -fsSL https://get.docker.com | sudo sh"
    all_good=false
fi

# Check Mosquitto
echo -n "  [1.2] Mosquitto installed: "
if command_exists mosquitto; then
    echo -e "${GREEN}✓${NC} ($(mosquitto -h 2>&1 | grep version | cut -d' ' -f3))"
else
    echo -e "${RED}✗${NC}"
    echo "       Install: sudo apt install mosquitto mosquitto-clients"
    all_good=false
fi

# Check PostgreSQL client
echo -n "  [1.3] PostgreSQL client: "
if command_exists psql; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} (optional)"
    echo "       Install: sudo apt install postgresql-client"
fi

# Check OpenSSL
echo -n "  [1.4] OpenSSL: "
if command_exists openssl; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    all_good=false
fi

echo ""
echo -e "${YELLOW}[Phase 2] Project Files${NC}"
echo ""

# Check .env file
echo -n "  [2.1] .env file exists: "
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC}"
    
    # Check critical env vars
    echo "       Checking critical variables..."
    for var in DB_HOST DB_NAME DB_USER ALLOWED_HOSTS SECRET_KEY; do
        if grep -q "^$var=" .env 2>/dev/null; then
            echo -e "       - $var: ${GREEN}✓${NC}"
        else
            echo -e "       - $var: ${RED}✗ Missing${NC}"
            all_good=false
        fi
    done
else
    echo -e "${RED}✗${NC}"
    echo "       Copy and configure .env file"
    all_good=false
fi

# Check JWT keys
echo -n "  [2.2] JWT RSA keys: "
if [ -f "Skytronsystem/keys/jwt_private_key.pem" ] && [ -f "Skytronsystem/keys/jwt_public_key.pem" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "       Missing: Skytronsystem/keys/jwt_*.pem"
    all_good=false
fi

# Check certificates
echo -n "  [2.3] MQTT certificates: "
if [ -d "mqtt_certificates/root_ca" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} Need to generate"
    echo "       Run: sudo ./generate_trusted_certificates.sh"
fi

# Check root CA for Docker
echo -n "  [2.4] Root CA for Docker: "
if [ -f "Skytronsystem/root_ca.crt" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC}"
    echo "       Run: cp mqtt_certificates/root_ca/root_ca.crt Skytronsystem/"
fi

echo ""
echo -e "${YELLOW}[Phase 3] Network Configuration${NC}"
echo ""

# Check if port 2000 is available
echo -n "  [3.1] Port 2000 available: "
if ! sudo netstat -tulpn 2>/dev/null | grep -q ":2000 "; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC} (already in use)"
    echo "       Port 2000 is used by Django API"
fi

# Check if port 8883 is available
echo -n "  [3.2] Port 8883 available: "
if ! sudo netstat -tulpn 2>/dev/null | grep -q ":8883 "; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} (Mosquitto might be running)"
fi

echo ""
echo -e "${YELLOW}[Phase 4] Database Connection${NC}"
echo ""

# Try to extract DB details from .env
if [ -f ".env" ]; then
    DB_HOST=$(grep "^DB_HOST=" .env 2>/dev/null | cut -d'=' -f2)
    DB_PORT=$(grep "^DB_PORT=" .env 2>/dev/null | cut -d'=' -f2)
    DB_NAME=$(grep "^DB_NAME=" .env 2>/dev/null | cut -d'=' -f2)
    DB_USER=$(grep "^DB_USER=" .env 2>/dev/null | cut -d'=' -f2)
    
    if [ -n "$DB_HOST" ] && [ -n "$DB_NAME" ] && command_exists psql; then
        echo -n "  [4.1] Database connection: "
        if timeout 5 bash -c "PGPASSWORD=\$(grep '^DB_PASSWORD=' .env | cut -d'=' -f2) psql -h $DB_HOST -p ${DB_PORT:-5432} -U $DB_USER -d $DB_NAME -c 'SELECT 1' >/dev/null 2>&1"; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
            echo "       Cannot connect to database"
            echo "       Check credentials and network access"
            all_good=false
        fi
    else
        echo "  [4.1] Database connection: ${YELLOW}Skipped${NC} (install psql to test)"
    fi
fi

echo ""
echo -e "${YELLOW}[Phase 5] Mosquitto Configuration${NC}"
echo ""

# Check mosquitto-go-auth
echo -n "  [5.1] mosquitto-go-auth plugin: "
if [ -f "/usr/lib/x86_64-linux-gnu/go-auth.so" ] || [ -f "/usr/lib/aarch64-linux-gnu/go-auth.so" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} Not installed"
    echo "       Run: sudo ./setup_mosquitto_jwt_auth.sh"
fi

# Check go-auth.conf
echo -n "  [5.2] go-auth.conf: "
if [ -f "/etc/mosquitto/conf.d/go-auth.conf" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC}"
fi

# Check TLS config
echo -n "  [5.3] TLS configuration: "
if [ -f "/etc/mosquitto/conf.d/tls.conf" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    all_good=false
fi

# Check Mosquitto service
echo -n "  [5.4] Mosquitto service: "
if sudo systemctl is-active --quiet mosquitto; then
    echo -e "${GREEN}✓${NC} (running)"
else
    echo -e "${YELLOW}⚠${NC} (not running)"
    echo "       Start: sudo systemctl start mosquitto"
fi

echo ""
echo -e "${YELLOW}[Phase 6] Docker Container${NC}"
echo ""

# Check if container is running
echo -n "  [6.1] Container running: "
if docker ps | grep -q "skytron-backend-api-container"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠${NC} Not running"
    echo "       Run: ./run_with_host_storage.sh"
fi

echo ""
echo -e "${YELLOW}[Phase 7] Firewall${NC}"
echo ""

# Check UFW
echo -n "  [7.1] UFW status: "
if command_exists ufw; then
    if sudo ufw status | grep -q "Status: active"; then
        echo -e "${GREEN}✓${NC} (active)"
        
        # Check required ports
        echo "       Checking required ports..."
        for port in 22 2000 8883; do
            if sudo ufw status | grep -q "$port"; then
                echo -e "       - Port $port: ${GREEN}✓${NC}"
            else
                echo -e "       - Port $port: ${YELLOW}⚠ Not configured${NC}"
            fi
        done
    else
        echo -e "${YELLOW}⚠${NC} (inactive)"
    fi
else
    echo -e "${YELLOW}N/A${NC} (not installed)"
fi

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

if [ "$all_good" = true ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Generate certificates (if needed): sudo ./generate_trusted_certificates.sh"
    echo "2. Install MQTT auth plugin: sudo ./setup_mosquitto_jwt_auth.sh"
    echo "3. Deploy container: ./run_with_host_storage.sh"
    echo "4. Test deployment: ./check_certificate_deployment.sh"
else
    echo -e "${YELLOW}⚠ Some items need attention (see above)${NC}"
    echo ""
    echo "Review the checklist and resolve issues marked with ✗"
fi

echo ""
echo "Documentation:"
echo "  - Full guide: DEPLOYMENT_GUIDE.md"
echo "  - Quick ref: cat DEPLOYMENT_GUIDE.md | grep '###'"
echo ""
