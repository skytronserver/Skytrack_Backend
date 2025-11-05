# NEW SERVER DEPLOYMENT - QUICK REFERENCE

## 📋 Before You Start

**What You Need:**
- [ ] New server with Ubuntu/Debian
- [ ] SSH access to new server
- [ ] Database credentials
- [ ] Current Skytrack_Backend directory

---

## 🚀 Quick Deployment (5 Steps)

### 1️⃣ Prepare New Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Mosquitto
sudo apt install -y mosquitto mosquitto-clients

# Install tools
sudo apt install -y openssl postgresql-client python3-pip unzip build-essential
```

### 2️⃣ Transfer Files
```bash
# From OLD server - create archive
cd /home/azureuser
tar -czf skytrack_backup.tar.gz Skytrack_Backend/

# Transfer to NEW server
scp skytrack_backup.tar.gz user@NEW_IP:/home/user/

# On NEW server - extract
cd /home/user
tar -xzf skytrack_backup.tar.gz
cd Skytrack_Backend
```

### 3️⃣ Configure Environment
```bash
# Edit .env file
nano .env

# Update these:
DB_HOST=your_db_host
ALLOWED_HOSTS=your_domain,your_ip,127.0.0.1
SECRET_KEY=generate_new_one
MQTT_BROKER_HOST=your_new_ip

# Generate new secret key:
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4️⃣ Setup MQTT & Certificates
```bash
# If server IP/domain changed, update certificate script:
nano generate_trusted_certificates.sh
# Update SERVER_IPS and SERVER_DNS arrays

# Generate certificates
sudo ./generate_trusted_certificates.sh

# Copy root CA for Docker
cp mqtt_certificates/root_ca/root_ca.crt Skytronsystem/

# Install MQTT authentication
sudo ./setup_mosquitto_jwt_auth.sh
```

### 5️⃣ Deploy Container
```bash
# Build and run
./run_with_host_storage.sh

# Verify
docker ps
docker logs skytron-backend-api-container
```

---

## ✅ Verification Commands

```bash
# Check all requirements
./deployment_checklist.sh

# Verify certificates
./check_certificate_deployment.sh

# Test Django API
curl http://localhost:2000/api/

# Test MQTT
mosquitto_sub -h localhost -p 8883 \
  --cafile mqtt_certificates/root_ca/root_ca.crt \
  -u "jwt" -P "TOKEN" -t "test" -v

# Check logs
docker logs -f skytron-backend-api-container
sudo journalctl -u mosquitto -f
```

---

## 🔧 Common Issues & Fixes

### Issue: Database Connection Failed
```bash
# Test connection
psql -h DB_HOST -p 5432 -U DB_USER -d DB_NAME

# Fix: Check .env credentials
# Fix: Verify DB allows connections from new IP
```

### Issue: Container Won't Start
```bash
# Check logs
docker logs skytron-backend-api-container

# Fix: Verify .env file
# Fix: Check port 2000 is free
sudo netstat -tulpn | grep 2000
```

### Issue: MQTT Connection Failed
```bash
# Check Mosquitto
sudo systemctl status mosquitto
sudo journalctl -u mosquitto -n 50

# Fix: Restart Mosquitto
sudo systemctl restart mosquitto

# Fix: Check certificates deployed
ls -la /etc/mosquitto/certs/
```

### Issue: Certificate Errors
```bash
# Regenerate if IPs changed
sudo ./generate_trusted_certificates.sh

# Verify chain
openssl verify -CAfile mqtt_certificates/intermediate_ca/ca_chain.crt \
  mqtt_certificates/server/server.crt
```

---

## 🔒 Security Checklist

- [ ] Change SECRET_KEY in .env
- [ ] Update ALLOWED_HOSTS
- [ ] Set DEBUG=False
- [ ] Configure firewall (ports 22, 2000, 8883)
- [ ] Strong database passwords
- [ ] SSL/TLS certificates installed
- [ ] Distribute new root CA to clients

---

## 📦 What Gets Transferred

**Essential Files:**
```
Skytrack_Backend/
├── .env                          # ⚠️ Update after transfer
├── Skytronsystem/                # Django project
│   ├── keys/
│   │   ├── jwt_private_key.pem  # JWT signing
│   │   └── jwt_public_key.pem   # JWT verification
│   └── root_ca.crt              # MQTT certificate validation
├── mqtt_certificates/            # Certificate chain
│   ├── root_ca/root_ca.crt      # Distribute to clients
│   ├── intermediate_ca/
│   └── server/
├── run_with_host_storage.sh     # Deploy container
├── generate_trusted_certificates.sh
├── setup_mosquitto_jwt_auth.sh
└── *.md                          # Documentation
```

---

## 🌐 Network Ports

| Port | Service | Required |
|------|---------|----------|
| 22   | SSH     | Yes      |
| 2000 | Django API | Yes   |
| 8883 | MQTT TLS | Yes    |
| 80   | HTTP (optional) | No |
| 443  | HTTPS (optional) | No |

Configure firewall:
```bash
sudo ufw allow 22/tcp
sudo ufw allow 2000/tcp
sudo ufw allow 8883/tcp
sudo ufw enable
```

---

## 📊 Post-Deployment

### Update DNS Records
```
A Record: yourdomain.com → NEW_SERVER_IP
A Record: api.yourdomain.com → NEW_SERVER_IP
A Record: mqtt.yourdomain.com → NEW_SERVER_IP
```

### Distribute Root CA
Send to all MQTT clients:
```
mqtt_certificates/root_ca/root_ca.crt
```

### Set Up Auto-start
```bash
# Docker containers restart automatically
# Verify:
docker inspect skytron-backend-api-container | grep RestartPolicy

# Mosquitto enabled on boot:
sudo systemctl enable mosquitto
```

### Set Up Backups
```bash
# Daily backup at 2 AM
crontab -e
# Add:
0 2 * * * tar -czf ~/backup_$(date +\%Y\%m\%d).tar.gz ~/Skytrack_Backend
```

---

## 🆘 Emergency Commands

```bash
# Restart everything
sudo systemctl restart mosquitto
docker restart skytron-backend-api-container

# View all logs
docker logs -f skytron-backend-api-container
sudo journalctl -u mosquitto -f

# Check status
docker ps
sudo systemctl status mosquitto
sudo systemctl status docker

# Rebuild from scratch
docker stop skytron-backend-api-container
docker rm skytron-backend-api-container
./run_with_host_storage.sh
```

---

## 📖 Documentation

- **Full Guide:** `DEPLOYMENT_GUIDE.md`
- **Certificates:** `CERTIFICATE_CHAIN_SECURITY.md`
- **Portability:** `DEPLOYMENT_PORTABILITY.md`
- **MQTT Auth:** `MQTT_JWT_AUTH_SETUP.md`

---

## ⏱️ Estimated Time

| Phase | Time |
|-------|------|
| Server setup | 10-15 min |
| File transfer | 5-10 min |
| Configuration | 10-15 min |
| Certificate generation | 5 min |
| Container deployment | 5-10 min |
| Verification | 5 min |
| **Total** | **40-60 min** |

---

## 🎯 Success Criteria

✅ Docker container running  
✅ Mosquitto accepting connections  
✅ Django API responding  
✅ MQTT JWT authentication working  
✅ Certificate validation enabled  
✅ All deployment checks passing  

Run: `./deployment_checklist.sh` to verify!

---

**Need Help?** Check `DEPLOYMENT_GUIDE.md` for detailed instructions.
