# MQTT JWT Authentication - Quick Reference

## 🎯 What Was Done

Your MQTT broker now accepts **BOTH**:
1. ✅ **JWT Token Authentication** (NEW)
2. ✅ **Username/Password Authentication** (EXISTING - unchanged)

## 🚀 Quick Start

### For Clients Using JWT Tokens

**Step 1: Get JWT Token**
```bash
POST /user_login_app/
Body: {"mobile": "9876543210", "password": "your_password"}
Response: {"token": "eyJhbGciOi..."}
```

**Step 2: Get MQTT Credentials**
```bash
POST /mqtt/prepare-auth-token/
Body: {"jwt_token": "eyJhbGciOi..."}
Response: {
  "mqtt_username": "9876543210",
  "mqtt_password": "abc123...",
  "mqtt_host": "127.0.0.1",
  "mqtt_port": 8883
}
```

**Step 3: Connect to MQTT**
Use the returned username and password to connect to MQTT broker.

### For Clients Using Username/Password

**No changes needed!** Connect directly to MQTT broker:
```python
client.username_pw_set("your_username", "your_password")
client.connect("127.0.0.1", 8883)
```

## 📡 API Endpoints

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|---------------|---------|
| `/mqtt/prepare-auth/` | GET/POST | ✅ Yes | Get MQTT creds for authenticated user |
| `/mqtt/prepare-auth-token/` | POST | ❌ No | Get MQTT creds with JWT token |

## 🔧 Configuration

**Django Settings** (`settings.py`):
```python
MQTT_HOST = '127.0.0.1'
MQTT_PORT = '8883'
MQTT_ADMIN_USER = 'admin'
MQTT_ADMIN_PASS = 'adminpass'
MQTT_CA_FILE = '/etc/mosquitto/certs/ca.crt'
```

## 📝 Example Code

**Python**:
```python
import requests, paho.mqtt.client as mqtt

# Get JWT token
token = requests.post('http://127.0.0.1:2000/user_login_app/', 
    {'mobile': '9876543210', 'password': 'pwd'}).json()['token']

# Get MQTT credentials
creds = requests.post('http://127.0.0.1:2000/mqtt/prepare-auth-token/',
    json={'jwt_token': token}).json()

# Connect to MQTT
client = mqtt.Client()
client.username_pw_set(creds['mqtt_username'], creds['mqtt_password'])
client.tls_set(ca_certs=creds['mqtt_ca_cert'])
client.connect(creds['mqtt_host'], int(creds['mqtt_port']))
```

## 🧪 Testing

**Quick Test**:
```bash
cd /home/azureuser/Skytrack_Backend
python3 test_mqtt_jwt_auth.py
```

**Example Client**:
```bash
python3 mqtt_client_example.py
```

## 📂 Important Files

**New Files**:
- `Skytronsystem/skytron_api/mqtt_auth_views.py` - Auth endpoints
- `mqtt_unified_auth.py` - Unified auth script
- `test_mqtt_jwt_auth.py` - Test suite
- `mqtt_client_example.py` - Example client
- `MQTT_JWT_AUTHENTICATION_GUIDE.md` - Full documentation

**Modified Files**:
- `Skytronsystem/skytron_api/urls.py` - Added routes
- `Skytronsystem/Skytronsystem/settings.py` - Added MQTT config

## ✅ What Works

- ✅ JWT token authentication
- ✅ Username/password authentication (unchanged)
- ✅ Automatic MQTT user creation from JWT tokens
- ✅ TLS/SSL encrypted connections
- ✅ User validation from Django database
- ✅ Backward compatibility maintained

## 🔍 Troubleshooting

**Check logs**:
```bash
sudo docker logs skytron-backend-api-container  # Django
sudo tail -f /var/log/mosquitto/mosquitto.log   # MQTT
```

**Common fixes**:
- JWT expired → Request new token
- User not found → Check user is active in Django
- Connection refused → Check mosquitto is running

## 🛠️ Next Steps

1. Test with your actual mobile/credentials
2. Update client apps to use new JWT flow
3. Monitor logs during testing
4. Deploy to production

## 📚 Documentation

- **Full Guide**: `MQTT_JWT_AUTHENTICATION_GUIDE.md`
- **Summary**: `IMPLEMENTATION_SUMMARY.md`
- **This File**: Quick reference

---

**Need Help?** Check the logs or review the full documentation.
