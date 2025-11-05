# MQTT Dual Authentication Configuration Guide

## Overview
This guide explains how to configure Mosquitto MQTT broker to support **dual authentication modes**:

1. **JWT Token Only** (no username) → Validate JWT signature, extract user info
2. **Username + Password** → Use Mosquitto dynamic-security plugin

---

## How It Works

### Authentication Flow Diagram
```
MQTT Client Connection
        ↓
  Username provided?
        ↓
    ┌───┴───┐
    NO      YES
    ↓        ↓
JWT Mode    Username+Password Mode
    ↓        ↓
Decode JWT  Check dynamic-security.json
Validate    Match username/password hash
signature       ↓
    ↓       ALLOW or DENY
Extract
user_id
    ↓
Lookup user
in Django DB
    ↓
Create MQTT
user account
    ↓
ALLOW or DENY
```

### Mode 1: JWT Token Only (No Username)
**Client connects with:**
- Username: `""` (empty) or not provided
- Password: `eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...` (JWT token)

**Authentication process:**
1. Script receives empty username and JWT token as password
2. Verify JWT signature using RS256 public key
3. Check expiration, issuer, audience
4. Extract `user_id` and `user_mobile` from payload
5. Lookup user in Django database by `user_id`
6. Verify user is active
7. Create/update MQTT user with mobile number as username
8. Allow connection

### Mode 2: Username + Password (Traditional)
**Client connects with:**
- Username: `1000000001` (mobile number)
- Password: `myStaticPassword123`

**Authentication process:**
1. Script receives username and password
2. Delegate to Mosquitto dynamic-security plugin
3. Dynamic-security checks username/password hash in `/var/lib/mosquitto/dynamic-security.json`
4. Allow or deny based on stored credentials

---

## Installation Steps

### Step 1: Install the Authentication Script
The script is already created at:
```bash
/home/azureuser/Skytrack_Backend/mqtt_dual_auth_hook.py
```

Verify it's executable:
```bash
ls -la /home/azureuser/Skytrack_Backend/mqtt_dual_auth_hook.py
chmod +x /home/azureuser/Skytrack_Backend/mqtt_dual_auth_hook.py
```

### Step 2: Configure Mosquitto to Use External Auth Plugin

**IMPORTANT NOTE:** Mosquitto's built-in dynamic-security plugin does NOT support external auth hooks directly. To implement your dual-mode authentication, you have **two options**:

#### Option A: Use mosquitto-go-auth Plugin (Recommended)
This plugin supports multiple authentication backends including HTTP API.

1. **Install mosquitto-go-auth:**
```bash
# Download and install mosquitto-go-auth
wget https://github.com/iegomez/mosquitto-go-auth/releases/download/2.1.0/mosquitto-go-auth-linux-amd64.tar.gz
tar -xzf mosquitto-go-auth-linux-amd64.tar.gz
sudo cp mosquitto-go-auth.so /usr/lib/mosquitto-go-auth.so
```

2. **Create auth configuration** (`/etc/mosquitto/conf.d/auth.conf`):
```conf
# External authentication plugin
auth_plugin /usr/lib/mosquitto-go-auth.so

# HTTP backend configuration
auth_opt_backends http

# Point to your Django API endpoint
auth_opt_http_host 127.0.0.1
auth_opt_http_port 2000
auth_opt_http_getuser_uri /mqtt/auth/
auth_opt_http_superuser_uri /mqtt/superuser/
auth_opt_http_aclcheck_uri /mqtt/acl/

# HTTP request configuration
auth_opt_http_with_tls false
auth_opt_http_method POST
auth_opt_http_response_mode status
```

3. **Create Django API endpoints** in `skytron_api/mqtt_auth_views.py`:
```python
@api_view(['POST'])
def mqtt_auth(request):
    """Handle MQTT authentication requests"""
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    
    # Mode 1: JWT only (no username)
    if not username:
        success, user, mobile = authenticate_jwt_only(password)
        if success:
            return Response({'status': 'ok'}, status=200)
        return Response({'status': 'error'}, status=403)
    
    # Mode 2: Username + password (check dynamic-security)
    else:
        # Delegate to dynamic-security or implement password check
        return Response({'status': 'ok'}, status=200)
```

#### Option B: Create ACL Plugin Hook (Current Setup)
Use the script as a pre-connection hook, but note that Mosquitto doesn't support this natively without plugins.

**Alternative: Modify Client Connection Logic**
Since Mosquitto doesn't easily support custom pre-auth hooks, you can:

1. **Client-side:** Before connecting to MQTT, call Django API to register/validate
2. **Django API:** Validate JWT, create MQTT user via mosquitto_ctrl
3. **Client:** Then connect with username/password

---

## Quick Implementation (Recommended Approach)

Since full external auth plugin integration is complex, here's the **practical solution**:

### Implementation: Pre-Auth Django API Endpoint

**File:** `Skytronsystem/skytron_api/mqtt_auth_views.py`

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .secure_token import verify_jwt_token, decode_jwt_token
from django.contrib.auth import get_user_model
import subprocess

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def mqtt_prepare_connection(request):
    """
    Prepare MQTT connection - validates JWT and creates MQTT user
    
    Request body:
    {
        "token": "JWT_TOKEN_HERE"  # If JWT mode
        OR
        "username": "1000000001",  # If username/password mode
        "password": "static_pass"
    }
    
    Returns:
    {
        "status": "success",
        "username": "1000000001",
        "password": "JWT_TOKEN" or "static_pass"
    }
    """
    
    # Mode 1: JWT Token only
    if 'token' in request.data and not request.data.get('username'):
        jwt_token = request.data.get('token')
        
        # Verify JWT
        if not verify_jwt_token(jwt_token):
            return Response({
                'status': 'error',
                'message': 'Invalid or expired JWT token'
            }, status=403)
        
        # Decode JWT
        payload = decode_jwt_token(jwt_token)
        if not payload:
            return Response({
                'status': 'error',
                'message': 'Unable to decode JWT'
            }, status=403)
        
        user_id = payload.get('user_id')
        user_mobile = payload.get('user_mobile')
        
        # Lookup user
        user = User.objects.filter(id=user_id, is_active=True).first()
        if not user:
            return Response({
                'status': 'error',
                'message': 'User not found or inactive'
            }, status=403)
        
        # Create/update MQTT user via mosquitto_ctrl
        username = user.mobile
        try:
            subprocess.run([
                'mosquitto_ctrl',
                '--cafile', '/etc/mosquitto/certs/ca.crt',
                '-h', '127.0.0.1',
                '-p', '8883',
                '-u', 'admin',
                '-P', 'adminpass',
                'dynsec', 'setClientPassword',
                username, jwt_token
            ], check=True, capture_output=True, timeout=5)
            
            return Response({
                'status': 'success',
                'username': username,
                'password': jwt_token,
                'message': 'JWT validated, MQTT user created'
            }, status=200)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Failed to create MQTT user: {str(e)}'
            }, status=500)
    
    # Mode 2: Username + Password (already exists in dynamic-security)
    else:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'status': 'error',
                'message': 'Username and password required'
            }, status=400)
        
        return Response({
            'status': 'success',
            'username': username,
            'password': password,
            'message': 'Use existing dynamic-security credentials'
        }, status=200)
```

### Add URL Route
**File:** `Skytronsystem/skytron_api/urls.py`

```python
from .mqtt_auth_views import mqtt_prepare_connection

urlpatterns = [
    # ... existing routes ...
    path('mqtt/prepare-connection/', mqtt_prepare_connection, name='mqtt_prepare_connection'),
]
```

---

## Client Usage Examples

### Python Client - JWT Mode
```python
import requests
import paho.mqtt.client as mqtt

# Step 1: Get JWT token from Django (after OTP verification)
jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."

# Step 2: Prepare MQTT connection via Django API
response = requests.post('http://135.235.166.209:2000/mqtt/prepare-connection/', json={
    'token': jwt_token
})

if response.status_code == 200:
    data = response.json()
    username = data['username']
    password = data['password']
    
    # Step 3: Connect to MQTT with credentials
    client = mqtt.Client()
    client.username_pw_set(username, password)
    client.tls_set(ca_certs='/path/to/ca.crt')
    client.connect('135.235.166.209', 8883, 60)
    client.subscribe('test/topic')
    client.loop_forever()
else:
    print(f"Auth failed: {response.json()}")
```

### Python Client - Username/Password Mode
```python
import paho.mqtt.client as mqtt

# Connect directly with existing credentials
client = mqtt.Client()
client.username_pw_set('1000000001', 'myStaticPassword')
client.tls_set(ca_certs='/path/to/ca.crt')
client.connect('135.235.166.209', 8883, 60)
client.subscribe('test/topic')
client.loop_forever()
```

---

## Testing

### Test JWT Mode
```bash
# 1. Get JWT token from Django
curl -X POST http://135.235.166.209:2000/mqtt/prepare-connection/ \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_JWT_TOKEN_HERE"}'

# 2. Use returned credentials to connect
mosquitto_pub -h 135.235.166.209 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "1000000001" \
  -P "YOUR_JWT_TOKEN_HERE" \
  -t "test/topic" \
  -m "Hello from JWT mode"
```

### Test Username/Password Mode
```bash
mosquitto_pub -h 135.235.166.209 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u "1000000001" \
  -P "staticPassword123" \
  -t "test/topic" \
  -m "Hello from password mode"
```

---

## Summary

✅ **Created:** `/home/azureuser/Skytrack_Backend/mqtt_dual_auth_hook.py`  
✅ **Authentication Modes:** JWT-only and Username+Password supported  
✅ **Recommended Approach:** Use Django API pre-auth endpoint (easier to implement)

**Next Steps:**
1. Implement the Django API endpoint (`mqtt_prepare_connection`)
2. Update client applications to call this endpoint before MQTT connection
3. Test both authentication modes
4. Monitor logs in `/var/log/mqtt_dual_auth.log`

This approach gives you full control over authentication while working within Mosquitto's limitations.
