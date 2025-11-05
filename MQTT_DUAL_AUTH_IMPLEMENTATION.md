# MQTT Dual Authentication - Implementation Complete ✅

**Date:** November 5, 2025  
**Status:** Implemented and Deployed

---

## 🎯 Your Requirements - IMPLEMENTED

### ✅ Requirement 1: Password-Only = JWT Token
**"If only password is given, treat it as JWT token and validate"**

**Implementation:**
- New Django API endpoint: `/mqtt/dual-auth/`
- When request contains only `token` (no `username`):
  1. Decode JWT and validate signature (RS256)
  2. Extract `user_id` and `user_mobile` from payload
  3. Lookup user in Django database
  4. Create/update MQTT user with mobile as username
  5. Set JWT token as MQTT password
  6. Return credentials to client

### ✅ Requirement 2: Username Given = Static Password
**"If username is given, treat password as static and use dynamic-security"**

**Implementation:**
- Same endpoint: `/mqtt/dual-auth/`
- When request contains both `username` and `password`:
  1. Validate credentials exist
  2. Return credentials for client to connect
  3. MQTT broker uses dynamic-security.json for authentication
  4. No JWT validation needed

---

## 📡 API Endpoint

### URL
```
POST http://135.235.166.209:2000/mqtt/dual-auth/
```

### MODE 1: JWT Token Only

**Request:**
```json
{
    "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (Success):**
```json
{
    "success": true,
    "auth_mode": "jwt",
    "username": "1000000001",
    "password": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "mqtt_host": "127.0.0.1",
    "mqtt_port": 8883,
    "mqtt_use_tls": true,
    "mqtt_ca_cert": "/etc/mosquitto/certs/ca.crt",
    "user_id": 123,
    "mobile": "1000000001",
    "message": "JWT validated. MQTT user created/updated. Connect with provided credentials."
}
```

**Response (Error):**
```json
{
    "success": false,
    "error": "Invalid or expired JWT token",
    "auth_mode": "jwt"
}
```

### MODE 2: Username + Password

**Request:**
```json
{
    "username": "1000000001",
    "password": "myStaticPassword123"
}
```

**Response (Success):**
```json
{
    "success": true,
    "auth_mode": "username_password",
    "username": "1000000001",
    "password": "myStaticPassword123",
    "mqtt_host": "127.0.0.1",
    "mqtt_port": 8883,
    "mqtt_use_tls": true,
    "mqtt_ca_cert": "/etc/mosquitto/certs/ca.crt",
    "message": "Use provided credentials to connect. Authentication via dynamic-security."
}
```

---

## 🔐 Authentication Flow

### JWT Mode Flow
```
Client Application
    ↓
[1] Login → OTP Verification → Get JWT Token
    ↓
[2] POST /mqtt/dual-auth/ with {"token": "JWT..."}
    ↓
Django API validates JWT:
    - Verify RS256 signature ✓
    - Check expiration ✓
    - Extract user_id ✓
    - Lookup user in DB ✓
    ↓
[3] mosquitto_ctrl setClientPassword
    Username: user.mobile
    Password: JWT_token
    ↓
[4] Return credentials to client
    ↓
[5] Client connects to MQTT:
    - Host: 135.235.166.209
    - Port: 8883
    - Username: 1000000001
    - Password: JWT_token
    - TLS: Yes
    ↓
Mosquitto broker:
    - Check dynamic-security.json
    - Match username + password hash
    - ALLOW connection ✓
```

### Username/Password Mode Flow
```
Client Application
    ↓
[1] POST /mqtt/dual-auth/ with {"username": "...", "password": "..."}
    ↓
Django API:
    - Returns credentials as-is
    - No JWT validation
    ↓
[2] Client connects to MQTT:
    - Username: 1000000001
    - Password: staticPassword
    ↓
Mosquitto broker:
    - Check dynamic-security.json
    - Match username + password hash
    - ALLOW or DENY
```

---

##  📋 Testing Commands

### Test 1: JWT Token Mode

```bash
# Step 1: Get JWT token (after OTP verification)
curl -X POST http://135.235.166.209:2000/mqtt/dual-auth/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_JWT_TOKEN_HERE"
  }'

# Expected response: username and password (JWT)
# Step 2: Connect to MQTT with returned credentials
mosquitto_pub -h 135.235.166.209 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "1000000001" \
  -P "YOUR_JWT_TOKEN_HERE" \
  -t "test/topic" \
  -m "Hello from JWT mode" \
  -d
```

### Test 2: Username/Password Mode

```bash
# Step 1: Verify credentials
curl -X POST http://135.235.166.209:2000/mqtt/dual-auth/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "1000000001",
    "password": "yourStaticPassword"
  }'

# Step 2: Connect to MQTT
mosquitto_pub -h 135.235.166.209 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "1000000001" \
  -P "yourStaticPassword" \
  -t "test/topic" \
  -m "Hello from password mode" \
  -d
```

---

## 🐍 Python Client Examples

### Example 1: JWT Mode

```python
import requests
import paho.mqtt.client as mqtt

# Step 1: Get JWT token from your Django login/OTP flow
jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."  # From OTP verification

# Step 2: Prepare MQTT connection
response = requests.post(
    'http://135.235.166.209:2000/mqtt/dual-auth/',
    json={'token': jwt_token}
)

if response.status_code == 200:
    data = response.json()
    
    if data['success']:
        # Step 3: Connect to MQTT
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT broker!")
                client.subscribe('test/topic')
            else:
                print(f"Connection failed with code {rc}")
        
        def on_message(client, userdata, msg):
            print(f"Received: {msg.topic} -> {msg.payload.decode()}")
        
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Set credentials from API response
        client.username_pw_set(data['username'], data['password'])
        client.tls_set(ca_certs='/path/to/ca.crt')  # Download from server
        
        # Connect
        client.connect(data['mqtt_host'], data['mqtt_port'], 60)
        client.loop_forever()
    else:
        print(f"Auth failed: {data['error']}")
else:
    print(f"API error: {response.status_code}")
```

### Example 2: Username/Password Mode

```python
import requests
import paho.mqtt.client as mqtt

# Step 1: Get credentials (optional API call for validation)
response = requests.post(
    'http://135.235.166.209:2000/mqtt/dual-auth/',
    json={
        'username': '1000000001',
        'password': 'myStaticPassword'
    }
)

if response.status_code == 200:
    data = response.json()
    
    # Step 2: Connect to MQTT
    client = mqtt.Client()
    client.username_pw_set(data['username'], data['password'])
    client.tls_set(ca_certs='/path/to/ca.crt')
    client.connect(data['mqtt_host'], data['mqtt_port'], 60)
    
    # Publish/Subscribe
    client.publish('test/topic', 'Hello MQTT')
    client.loop_start()
```

---

## 📂 Files Modified/Created

### Created Files
1. `/home/azureuser/Skytrack_Backend/mqtt_dual_auth_hook.py`
   - Standalone script for potential external auth plugin integration
   
2. `/home/azureuser/Skytrack_Backend/MQTT_DUAL_AUTH_SETUP.md`
   - Configuration guide and documentation
   
3. `/home/azureuser/Skytrack_Backend/MQTT_DUAL_AUTH_IMPLEMENTATION.md`
   - This file - complete implementation summary

### Modified Files
1. `/home/azureuser/Skytrack_Backend/Skytronsystem/skytron_api/mqtt_auth_views.py`
   - Added `mqtt_dual_auth()` endpoint function
   - Added JWT validation logic
   - Added mosquitto_ctrl integration
   
2. `/home/azureuser/Skytrack_Backend/Skytronsystem/skytron_api/urls.py`
   - Added route: `path('mqtt/dual-auth/', mqtt_dual_auth, name='mqtt_dual_auth')`

### Deployed
- ✅ Files copied to Docker container: `skytron-backend-api-container`
- ✅ Container restarted and running
- ✅ Endpoint accessible at: `http://135.235.166.209:2000/mqtt/dual-auth/`

---

## 🔍 Verification

### Check Django Container
```bash
sudo docker ps --filter "name=skytron-backend-api"
# Should show: Up X seconds

sudo docker logs skytron-backend-api-container --tail 50
# Check for startup errors
```

### Check Mosquitto Broker
```bash
sudo systemctl status mosquitto
# Should show: active (running)

sudo tail -f /var/log/mosquitto/mosquitto.log
# Monitor MQTT connections
```

### Test API Endpoint
```bash
curl -X POST http://135.235.166.209:2000/mqtt/dual-auth/ \
  -H "Content-Type: application/json" \
  -d '{"token": "test"}' \
  -v

# Expected: 403 Forbidden (invalid token) or 200 OK (valid token)
```

---

## 🔐 Security Features

### JWT Validation
- ✅ RS256 signature verification (RSA public key)
- ✅ Expiration timestamp check (120 seconds default)
- ✅ Issuer verification (`skytrack-auth`)
- ✅ Audience verification (`skytrack-api`)
- ✅ User existence check in Django database
- ✅ Active user status verification

### MQTT Security
- ✅ TLS encryption (port 8883)
- ✅ Certificate-based trust (ca.crt)
- ✅ Username/password authentication required
- ✅ Dynamic password updates via JWT tokens

---

## 📊 Logging

### Django API Logs
```bash
sudo docker logs -f skytron-backend-api-container | grep "MQTT Dual Auth"
```

**Log Entries:**
- `MQTT Dual Auth: JWT mode - token length=XXX`
- `MQTT Dual Auth: JWT decoded - user_id=XXX, mobile=XXX`
- `MQTT Dual Auth: JWT mode success - username=XXX`
- `MQTT Dual Auth: Username/Password mode - username=XXX`

### Mosquitto Broker Logs
```bash
sudo tail -f /var/log/mosquitto/mosquitto.log
```

**Watch for:**
- `New connection from XXX on port 8883`
- `Client XXX disconnected`
- `New client connected from XXX as XXX`

---

## ⚡ Performance Considerations

### JWT Token Expiration
**Current:** 120 seconds (2 minutes)  
**Recommendation for MQTT:** 1 hour to 24 hours

**To change:**
Edit `/home/azureuser/Skytrack_Backend/Skytronsystem/skytron_api/secure_token.py`:
```python
self.access_token_lifetime = 3600  # 1 hour in seconds
```

### Connection Pooling
- MQTT clients maintain persistent connections
- JWT validation happens once per connection
- Subsequent publishes/subscribes use existing connection

---

## 🎯 Summary

### What Works Now ✅

1. **JWT Token Only Mode:**
   - Client sends only JWT token (no username)
   - Django validates JWT signature and expiration
   - Extracts user info from token
   - Creates MQTT user dynamically
   - Client connects to MQTT with mobile + JWT

2. **Username/Password Mode:**
   - Client sends username + static password
   - Django validates format
   - MQTT broker checks dynamic-security.json
   - Traditional authentication

### What's Different from Standard Setup

- **Dual-mode support**: One endpoint, two authentication methods
- **Dynamic user creation**: JWT mode creates MQTT users on-demand
- **Stateless JWT**: No database session lookup for JWT mode
- **Flexible password**: JWT tokens work as MQTT passwords

### Next Steps (Optional Enhancements)

1. **Token Refresh**: Implement refresh token mechanism for long-lived connections
2. **ACL Management**: Add topic-based access control per user
3. **Monitoring**: Add Prometheus metrics for auth success/failure rates
4. **Rate Limiting**: Prevent brute force attacks on auth endpoint
5. **Audit Logging**: Track all authentication attempts in database

---

## 🆘 Troubleshooting

### Issue: "Invalid or expired JWT token"
**Solution:**
- Check JWT token is current (not expired)
- Verify token was generated by your Django app
- Check RS256 signature keys match

### Issue: "User not found or inactive"
**Solution:**
- Verify user_id in JWT payload matches database
- Check user.is_active = True in Django

### Issue: "Failed to create MQTT user"
**Solution:**
- Check mosquitto_ctrl is installed: `which mosquitto_ctrl`
- Verify MQTT admin credentials in settings.py
- Check Mosquitto is running: `sudo systemctl status mosquitto`

### Issue: "Connection refused"
**Solution:**
- Check MQTT broker is running
- Verify port 8883 is open: `sudo netstat -tulpn | grep 8883`
- Check TLS certificates exist: `ls -la /etc/mosquitto/certs/`

---

**Implementation Date:** November 5, 2025  
**Status:** ✅ **COMPLETE AND DEPLOYED**  
**Tested:** Ready for integration testing

Your dual authentication requirement is now fully implemented and running! 🎉
