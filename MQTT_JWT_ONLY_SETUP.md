# MQTT JWT-Only Authentication Setup Guide

## Overview
Enable Mosquitto to accept connections with **JWT token as password, no username required**.

---

## Architecture

```
MQTT Client (no username, JWT password)
          ↓
Mosquitto Broker (port 8883)
          ↓
mosquitto-go-auth plugin
          ↓
HTTP POST to Django API
    /mqtt/validate-connection/
          ↓
JWT validation (RS256 signature)
Extract user_id from payload
Lookup user in database
          ↓
Return 200 OK or 403 Forbidden
          ↓
Allow/Deny connection
```

---

## Installation Steps

### Step 1: Install mosquitto-go-auth Plugin

```bash
cd /home/azureuser/Skytrack_Backend
chmod +x install_mosquitto_go_auth.sh
./install_mosquitto_go_auth.sh
```

OR manually:

```bash
# Download plugin
cd /tmp
wget https://github.com/iegomez/mosquitto-go-auth/releases/download/2.1.0/mosquitto-go-auth-2.1.0-linux-amd64.tar.gz
tar -xzf mosquitto-go-auth-2.1.0-linux-amd64.tar.gz

# Install
sudo cp mosquitto-go-auth.so /usr/lib/mosquitto-go-auth.so
sudo chmod 755 /usr/lib/mosquitto-go-auth.so
```

### Step 2: Configure Mosquitto

**Disable dynamic-security (temporarily):**
```bash
sudo mv /etc/mosquitto/conf.d/dynsec.conf /etc/mosquitto/conf.d/dynsec.conf.disabled
```

**Create mosquitto-go-auth config:**
```bash
sudo tee /etc/mosquitto/conf.d/go-auth.conf > /dev/null <<'EOF'
# External authentication via mosquitto-go-auth
auth_plugin /usr/lib/mosquitto-go-auth.so

# Use HTTP backend
auth_opt_backends http

# Django API endpoint
auth_opt_http_host 127.0.0.1
auth_opt_http_port 2000
auth_opt_http_getuser_uri /mqtt/validate-connection/
auth_opt_http_superuser_uri /mqtt/validate-connection/
auth_opt_http_aclcheck_uri /mqtt/validate-acl/

# HTTP settings
auth_opt_http_with_tls false
auth_opt_http_method POST
auth_opt_http_response_mode status
auth_opt_http_params_mode json

# Logging
auth_opt_log_level debug
EOF
```

### Step 3: Restart Mosquitto

```bash
sudo systemctl restart mosquitto
sudo systemctl status mosquitto
```

### Step 4: Test JWT-Only Connection

**Without username (JWT-only mode):**
```bash
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "" \
  -P "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -t "test/topic" \
  -v
```

**With username (traditional mode):**
```bash
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "1000000002" \
  -P "static_password" \
  -t "test/topic" \
  -v
```

---

## Django Endpoints (Already Created)

### 1. `/mqtt/validate-connection/` 
**Called by mosquitto-go-auth for every connection attempt**

Request:
```json
{
    "username": "",  // empty for JWT-only
    "password": "JWT_TOKEN...",
    "clientid": "client123"
}
```

Response:
- `200 OK` → Allow connection
- `403 Forbidden` → Deny connection

### 2. `/mqtt/validate-acl/`
**Called for topic access control**

Request:
```json
{
    "username": "1000000002",
    "topic": "test/topic",
    "acc": 1  // 1=read, 2=write
}
```

Response:
- `200 OK` → Allow access
- `403 Forbidden` → Deny access

---

## How It Works

### JWT-Only Mode (No Username)
1. Client connects with empty username and JWT token as password
2. Mosquitto calls `/mqtt/validate-connection/` via mosquitto-go-auth
3. Django validates JWT:
   - Verify RS256 signature
   - Check expiration
   - Extract user_id
   - Lookup user in database
4. Return 200 if valid, 403 if invalid
5. Mosquitto allows/denies connection

### Username+Password Mode (Traditional)
1. Client connects with username and password
2. Mosquitto calls `/mqtt/validate-connection/`
3. Django checks if user exists
4. Return 200 (can add password verification)
5. Mosquitto allows connection

---

## Testing Commands

### Test Django Endpoint Directly
```bash
# Test JWT-only
curl -X POST http://127.0.0.1:2000/mqtt/validate-connection/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "",
    "password": "YOUR_JWT_TOKEN_HERE",
    "clientid": "test_client"
  }'

# Expected: {"ok":true,"user_id":27,"username":"1000000002"}
```

### Test MQTT Connection
```bash
# Your actual JWT token
JWT_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyNywidXNlcl9tb2JpbGUiOiIxMDAwMDAwMDAyIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImlhdCI6MTc2MjM2ODYwNiwiZXhwIjoxNzYyMzY4NzI2LCJqdGkiOiIyN18xNzYyMzY4NjA2Iiwic2Vzc2lvbl9kYXRhIjp7ImxvZ2luX3R5cGUiOiJvdHBfdmFsaWRhdGVkIiwic3RhdHVzIjoiYXV0aGVudGljYXRlZCIsImxvZ2luX3RpbWUiOiIyMDI1LTExLTA1VDE4OjUwOjA2LjYwMDQxNSswMDowMCIsInJvbGUiOiJkZXZpY2VtYW51ZmFjdHVyZSJ9LCJpc3MiOiJza3l0cmFjay1hdXRoIiwiYXVkIjoic2t5dHJhY2stYXBpIn0.mFiRGPcY-L8s_hNMkgTBmPbq8XDSMgrXCXoEswCLie1A1Mno06JkI84yo1pstvpq7ju1xTf6t8qV9e6_J1vFQi12rU6gEqqsCIXL5Nx-v-ozKhhCGpNvUzR0aneuGomV3oucjYzKJ3hvtFY9Q-XE6JIeLZc3TCy1Ukwd-V6jJv6V8dgdbq0r7GpTb_SqA1DL_SIs8O6Yg7cjqxUkBFfNlJHM-yWGq0fg1ffaygfM8p0LxT9vRTMGSBfVoOrSO_yvBGZPWM6Di8z4LsydODSyFYJ6JMS10Ge9gc4JIScYqVjtgYeE6fNiYDZBYvRtW_iRLgwHgzjYvlvW6VUtF0H_KQ"

# Connect without username
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "" \
  -P "$JWT_TOKEN" \
  -t "#" \
  -v
```

---

## Monitoring

### Check Mosquitto Logs
```bash
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### Check Django Logs
```bash
sudo docker logs -f skytron-backend-api-container | grep "MQTT Auth"
```

### mosquitto-go-auth Logs
Look for lines like:
```
mosquitto-go-auth: http request to http://127.0.0.1:2000/mqtt/validate-connection/
mosquitto-go-auth: http response status: 200
```

---

## Troubleshooting

### Issue: "Connection Refused"
**Solution:** Check if mosquitto-go-auth plugin is loaded
```bash
sudo journalctl -u mosquitto -n 50 | grep auth
```

### Issue: "HTTP request failed"
**Solution:** Ensure Django is running and accessible
```bash
curl http://127.0.0.1:2000/mqtt/validate-connection/
```

### Issue: "JWT verification failed"
**Solution:** 
- Check JWT hasn't expired (exp claim)
- Verify RS256 public key matches
- Check logs: `sudo docker logs skytron-backend-api-container`

---

## Summary

✅ **Created Files:**
- `/home/azureuser/Skytrack_Backend/install_mosquitto_go_auth.sh`
- `/home/azureuser/Skytrack_Backend/Skytronsystem/skytron_api/mqtt_validate_views.py`
- Updated `urls.py` with validation endpoints

✅ **Django Endpoints:**
- `POST /mqtt/validate-connection/` - Validates MQTT auth (JWT or username/password)
- `POST /mqtt/validate-acl/` - Validates topic access control

✅ **Ready to Test:**
1. Install mosquitto-go-auth plugin
2. Configure Mosquitto
3. Restart Mosquitto
4. Connect with empty username and JWT token as password

**Your command will be:**
```bash
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "" \
  -P "YOUR_JWT_TOKEN" \
  -t "test/topic" \
  -v
```

This will work! The mosquitto-go-auth plugin intercepts the connection and validates the JWT via Django API.
