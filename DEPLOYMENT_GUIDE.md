# Skytrack Backend - New Server Deployment Guide

## Overview

This guide walks you through deploying the Skytrack Backend system to a new server with all components:
- Django API (Docker container)
- Mosquitto MQTT Broker with JWT authentication
- PostgreSQL Database connection
- SSL/TLS certificates with proper chain of trust

---

## Pre-Deployment Checklist

### Information You'll Need

- [ ] **New Server Details:**
  - IP Address: `___________________`
  - Hostname/Domain: `___________________`
  - OS: Ubuntu 20.04+ / Debian 11+
  - SSH Access: `___________________`

- [ ] **Database Details:**
  - Database Host: `___________________`
  - Database Port: `___________________`
  - Database Name: `___________________`
  - Database User: `___________________`
  - Database Password: `___________________`

- [ ] **Environment Configuration:**
  - Domain Name: `___________________`
  - Email Service Credentials: `___________________`
  - SMS Gateway Credentials: `___________________`

- [ ] **Files to Transfer:**
  - [ ] Entire `Skytrack_Backend` directory
  - [ ] `.env` file (update after transfer)
  - [ ] JWT RSA keys (`keys/jwt_private_key.pem`, `keys/jwt_public_key.pem`)
  - [ ] MQTT certificates (`mqtt_certificates/` directory)

---

## Deployment Steps

### Phase 1: Server Preparation

#### 1.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
```

#### 1.2 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
```

#### 1.3 Install Mosquitto MQTT Broker
```bash
# Install Mosquitto
sudo apt install -y mosquitto mosquitto-clients

# Stop it for now (we'll configure first)
sudo systemctl stop mosquitto
```

#### 1.4 Install Required Tools
```bash
sudo apt install -y \
    git \
    openssl \
    postgresql-client \
    python3-pip \
    unzip \
    build-essential \
    libssl-dev
```

---

### Phase 2: Transfer Files to New Server

#### 2.1 From Current Server - Create Archive
```bash
cd /home/azureuser
tar -czf skytrack_backup_$(date +%Y%m%d).tar.gz \
    --exclude='Skytrack_Backend/__pycache__' \
    --exclude='Skytrack_Backend/.git' \
    --exclude='Skytrack_Backend/logs/*' \
    Skytrack_Backend/
```

#### 2.2 Transfer to New Server
```bash
# Option A: Using SCP
scp skytrack_backup_*.tar.gz user@NEW_SERVER_IP:/home/user/

# Option B: Using rsync (recommended - more efficient)
rsync -avz --progress \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='logs/*' \
    /home/azureuser/Skytrack_Backend/ \
    user@NEW_SERVER_IP:/home/user/Skytrack_Backend/
```

#### 2.3 On New Server - Extract Archive (if using tar)
```bash
cd /home/user
tar -xzf skytrack_backup_*.tar.gz
cd Skytrack_Backend
```

---

### Phase 3: Configure Environment

#### 3.1 Update .env File
```bash
cd /path/to/Skytrack_Backend
nano .env
```

**Update these critical values:**
```bash
# Database Configuration
DB_HOST=YOUR_NEW_DATABASE_HOST
DB_PORT=5432
DB_NAME=YOUR_DATABASE_NAME
DB_USER=YOUR_DATABASE_USER
DB_PASSWORD=YOUR_DATABASE_PASSWORD

# Server Configuration
ALLOWED_HOSTS=YOUR_NEW_DOMAIN.com,YOUR_NEW_IP,127.0.0.1
DEBUG=False

# MQTT Configuration (update if IP changed)
MQTT_BROKER_HOST=YOUR_NEW_SERVER_IP_OR_DOMAIN

# Email Configuration
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password

# SMS Configuration (if applicable)
SMS_API_KEY=your_sms_api_key
SMS_SENDER_ID=your_sender_id

# Secret Key (generate new one for production)
SECRET_KEY=generate_new_secret_key_here
```

**Generate new SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

#### 3.2 Verify JWT Keys Exist
```bash
ls -la Skytronsystem/keys/jwt_*.pem
# Should show:
# jwt_private_key.pem
# jwt_public_key.pem
```

---

### Phase 4: Configure MQTT Certificates

#### 4.1 Update Certificate Generation Script (if server IP changed)

Edit `generate_trusted_certificates.sh`:
```bash
nano generate_trusted_certificates.sh
```

Update `SERVER_IPS` and `SERVER_DNS` arrays:
```bash
SERVER_IPS=(
    "127.0.0.1"
    "YOUR_NEW_SERVER_IP_1"
    "YOUR_NEW_SERVER_IP_2"
    # Add all IPs this server will use
)

SERVER_DNS=(
    "localhost"
    "YOUR_DOMAIN.com"
    "mqtt.YOUR_DOMAIN.com"
    "api.YOUR_DOMAIN.com"
)
```

#### 4.2 Regenerate Certificates (if IPs/domains changed)
```bash
# Only if server IPs or domains changed
sudo ./generate_trusted_certificates.sh
```

#### 4.3 Copy Root CA for Docker Build
```bash
cp mqtt_certificates/root_ca/root_ca.crt Skytronsystem/root_ca.crt
```

---

### Phase 5: Install Mosquitto JWT Authentication

#### 5.1 Run Setup Script
```bash
sudo ./setup_mosquitto_jwt_auth.sh
```

This will:
- Download and install mosquitto-go-auth plugin
- Configure HTTP backend pointing to Django API
- Enable Redis cache
- Restart Mosquitto

#### 5.2 Verify Mosquitto Status
```bash
sudo systemctl status mosquitto
sudo journalctl -u mosquitto -n 50
```

---

### Phase 6: Database Setup

#### 6.1 Test Database Connection
```bash
# Install PostgreSQL client if not already installed
sudo apt install -y postgresql-client

# Test connection
psql -h YOUR_DB_HOST -p YOUR_DB_PORT -U YOUR_DB_USER -d YOUR_DB_NAME
# Enter password when prompted
# Type \q to exit
```

#### 6.2 Verify Database Schema
The database should already exist with all tables. If this is a fresh database:
```bash
# You'll need to run migrations after Docker container is running
# See Phase 7.5
```

---

### Phase 7: Deploy Django Container

#### 7.1 Make Scripts Executable
```bash
chmod +x run_with_host_storage.sh
chmod +x build_run_mqtt.sh
chmod +x run_mqtt.sh
chmod +x run_tcp.sh
```

#### 7.2 Build and Run Django Container
```bash
./run_with_host_storage.sh
```

This will:
- Build Docker image with all dependencies
- Copy certificates and keys
- Start container on port 2000
- Configure with environment variables

#### 7.3 Verify Container is Running
```bash
docker ps | grep skytron
# Should show: skytron-backend-api-container
```

#### 7.4 Check Container Logs
```bash
docker logs -f skytron-backend-api-container
# Press Ctrl+C to exit
```

#### 7.5 Run Migrations (if needed)
```bash
# Only if this is a fresh database or migrations are pending
docker exec -it skytron-backend-api-container bash -c "cd /app && python3 manage.py migrate"
```

#### 7.6 Create Superuser (if needed)
```bash
docker exec -it skytron-backend-api-container bash -c "cd /app && python3 manage.py createsuperuser"
```

---

### Phase 8: Verify Deployment

#### 8.1 Check Django API
```bash
curl http://localhost:2000/api/
# Should return API response (not error)
```

#### 8.2 Check MQTT Connection with JWT
```bash
# First, get a JWT token from API (or use existing one)
# Then test MQTT connection:

mosquitto_sub -h localhost -p 8883 \
  --cafile mqtt_certificates/root_ca/root_ca.crt \
  -u "jwt" \
  -P "YOUR_JWT_TOKEN" \
  -t "test/topic" -v
```

#### 8.3 Check MQTT Authentication Endpoint
```bash
curl -X POST http://localhost:2000/api/mqtt/validate-connection/ \
  -H "Content-Type: application/json" \
  -d '{"username":"jwt","password":"YOUR_JWT_TOKEN"}'

# Should return: {"ok":true,"user_id":...}
```

#### 8.4 Run Deployment Checklist
```bash
./check_certificate_deployment.sh
# Should show all green checkmarks
```

---

### Phase 9: Configure Firewall

#### 9.1 Set Up UFW (Ubuntu Firewall)
```bash
# Enable firewall
sudo ufw enable

# Allow SSH (CRITICAL - do this first!)
sudo ufw allow 22/tcp

# Allow Django API port
sudo ufw allow 2000/tcp

# Allow MQTT port
sudo ufw allow 8883/tcp

# Allow HTTP/HTTPS (if using reverse proxy)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

#### 9.2 Cloud Provider Firewall
If using AWS/Azure/GCP, also configure security groups:
- Allow inbound TCP 2000 (Django API)
- Allow inbound TCP 8883 (MQTT TLS)
- Allow inbound TCP 22 (SSH)
- Allow inbound TCP 80/443 (if using web server)

---

### Phase 10: Set Up Reverse Proxy (Optional but Recommended)

#### 10.1 Install Nginx
```bash
sudo apt install -y nginx
```

#### 10.2 Configure Nginx for Django API
```bash
sudo nano /etc/nginx/sites-available/skytrack
```

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN.com;

    location / {
        proxy_pass http://127.0.0.1:2000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/user/Skytrack_Backend/Skytronsystem/staticfiles/;
    }
}
```

#### 10.3 Enable Site and Restart Nginx
```bash
sudo ln -s /etc/nginx/sites-available/skytrack /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 10.4 Set Up SSL with Let's Encrypt (Recommended)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN.com
```

---

### Phase 11: Set Up Systemd Services (Auto-start on Boot)

#### 11.1 Docker Container Auto-start
```bash
# Update docker run command in run_with_host_storage.sh
# Add --restart unless-stopped flag

# Or create systemd service:
sudo nano /etc/systemd/system/skytrack-api.service
```

```ini
[Unit]
Description=Skytrack Backend API Container
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/Skytrack_Backend
ExecStart=/home/user/Skytrack_Backend/run_with_host_storage.sh
ExecStop=/usr/bin/docker stop skytron-backend-api-container
User=user

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable skytrack-api
sudo systemctl start skytrack-api
```

#### 11.2 Verify Services
```bash
sudo systemctl status mosquitto
sudo systemctl status docker
sudo systemctl status skytrack-api
```

---

## Post-Deployment Tasks

### 1. Update DNS Records
Point your domain to the new server IP:
```
A Record: YOUR_DOMAIN.com → NEW_SERVER_IP
A Record: api.YOUR_DOMAIN.com → NEW_SERVER_IP
A Record: mqtt.YOUR_DOMAIN.com → NEW_SERVER_IP
```

### 2. Distribute New Root CA Certificate
Send `mqtt_certificates/root_ca/root_ca.crt` to all MQTT clients.

### 3. Update Client Applications
Update client apps with:
- New server IP/domain
- New root CA certificate
- Ensure certificate validation is enabled

### 4. Set Up Monitoring
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Check logs regularly
docker logs -f skytron-backend-api-container
sudo journalctl -u mosquitto -f
```

### 5. Set Up Backups
```bash
# Create backup script
nano ~/backup_skytrack.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/user/backups"
mkdir -p $BACKUP_DIR

# Backup code
tar -czf $BACKUP_DIR/skytrack_code_$DATE.tar.gz /home/user/Skytrack_Backend/

# Backup database (adjust credentials)
pg_dump -h DB_HOST -U DB_USER DB_NAME | gzip > $BACKUP_DIR/skytrack_db_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "skytrack_*" -mtime +7 -delete
```

```bash
chmod +x ~/backup_skytrack.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/user/backup_skytrack.sh
```

---

## Troubleshooting Guide

### Issue: Docker Container Won't Start
```bash
# Check logs
docker logs skytron-backend-api-container

# Common fixes:
# 1. Check .env file
# 2. Verify database connection
# 3. Check port 2000 is available
sudo netstat -tulpn | grep 2000
```

### Issue: MQTT Connection Failed
```bash
# Check Mosquitto logs
sudo journalctl -u mosquitto -n 100

# Test basic connection
mosquitto_sub -h localhost -p 8883 --insecure -t test

# Check certificates
ls -la /etc/mosquitto/certs/

# Verify Django API is responding
curl http://localhost:2000/api/mqtt/validate-connection/
```

### Issue: Database Connection Error
```bash
# Test connection
psql -h DB_HOST -p DB_PORT -U DB_USER -d DB_NAME

# Check firewall on database server
# Check .env file has correct credentials
# Verify database accepts connections from new server IP
```

### Issue: Certificate Validation Errors
```bash
# Verify certificate chain
openssl verify -CAfile mqtt_certificates/intermediate_ca/ca_chain.crt \
  mqtt_certificates/server/server.crt

# Check certificate SANs match hostname
openssl x509 -in mqtt_certificates/server/server.crt -text -noout | grep -A 10 "Subject Alternative Name"

# Regenerate if IPs/domains don't match
sudo ./generate_trusted_certificates.sh
```

---

## Security Checklist

- [ ] Changed default SECRET_KEY in .env
- [ ] Updated ALLOWED_HOSTS in .env
- [ ] DEBUG=False in production
- [ ] Firewall configured (UFW + cloud security groups)
- [ ] SSL/TLS certificates installed
- [ ] Strong database passwords
- [ ] SSH key-based authentication (disable password auth)
- [ ] Regular backups configured
- [ ] Monitoring and alerting set up
- [ ] JWT keys have proper permissions (600 for private)
- [ ] Root CA certificate distributed securely

---

## Quick Reference Commands

```bash
# Restart everything
sudo systemctl restart mosquitto
docker restart skytron-backend-api-container

# View logs
docker logs -f skytron-backend-api-container
sudo journalctl -u mosquitto -f

# Check status
docker ps
sudo systemctl status mosquitto
./check_certificate_deployment.sh

# Rebuild container
cd /path/to/Skytrack_Backend
./run_with_host_storage.sh

# Test MQTT
mosquitto_sub -h localhost -p 8883 \
  --cafile mqtt_certificates/root_ca/root_ca.crt \
  -u "jwt" -P "TOKEN" -t "test" -v
```

---

## Support Files

All scripts are portable and use dynamic paths:
- `run_with_host_storage.sh` - Deploy Django container
- `generate_trusted_certificates.sh` - Generate certificates
- `setup_mosquitto_jwt_auth.sh` - Install MQTT auth plugin
- `check_certificate_deployment.sh` - Verify deployment

See also:
- `DEPLOYMENT_PORTABILITY.md` - Portable deployment guide
- `CERTIFICATE_CHAIN_SECURITY.md` - Security compliance guide
- `MQTT_JWT_AUTH_SETUP.md` - MQTT authentication details

---

**Deployment Complete!** 🚀

Your Skytrack Backend is now running on the new server with:
✅ Django API
✅ MQTT Broker with JWT authentication
✅ Proper certificate chain of trust
✅ Security audit compliant
✅ Auto-start on boot
