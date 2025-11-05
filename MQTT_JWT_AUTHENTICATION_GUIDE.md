# MQTT JWT Authentication Configuration Guide

## Overview
This configuration enables your MQTT broker to accept **both** traditional username/password authentication **and** JWT token-based authentication.

## Architecture

### Authentication Flow

#### Method 1: JWT Token Authentication (New)
1. Client obtains JWT token from Django API (`/user_login/` or `/user_login_app/`)
2. Client calls `/mqtt/prepare-auth-token/` endpoint with JWT token
3. Django validates JWT token and extracts user_id
4. Django creates/updates MQTT user in Mosquitto dynamic security with deterministic password
5. Endpoint returns MQTT credentials (username, password, host, port)
6. Client connects to MQTT broker using returned credentials

#### Method 2: Username/Password Authentication (Existing)
1. Client uses mobile number as username and password
2. MQTT broker validates via dynamic security
3. Connection established

## API Endpoints

### 1. Prepare MQTT Auth (Authenticated)
**Endpoint:** `POST /mqtt/prepare-auth/`

**Authentication:** Required (Bearer token or Django session)

**Request:**
```json
{
  "jwt_token": "optional_jwt_token_string"
}
```

**Response:**
```json
{
  "success": true,
  "mqtt_username": "9876543210",
  "mqtt_password": "generated_password_hash",
  "mqtt_host": "127.0.0.1",
  "mqtt_port": 8883,
  "mqtt_use_tls": true,
  "mqtt_ca_cert": "/etc/mosquitto/certs/ca.crt",
  "message": "MQTT credentials prepared. Use these to connect to MQTT broker."
}
```

### 2. Prepare MQTT Auth with Token (Public)
**Endpoint:** `POST /mqtt/prepare-auth-token/`

**Authentication:** None (validates JWT token)

**Request:**
```json
{
  "jwt_token": "your_jwt_token_here"
}
```

**Response:**
```json
{
  "success": true,
  "mqtt_username": "9876543210",
  "mqtt_password": "generated_password_hash",
  "mqtt_host": "127.0.0.1",
  "mqtt_port": 8883,
  "mqtt_use_tls": true,
  "mqtt_ca_cert": "/etc/mosquitto/certs/ca.crt",
  "user_id": 123,
  "mobile": "9876543210",
  "message": "MQTT credentials prepared. Connect using these credentials."
}
```

## Client Implementation Examples

### Python Client Example
```python
import requests
import paho.mqtt.client as mqtt
import ssl

# Step 1: Login and get JWT token
login_response = requests.post('https://your-domain.com/user_login_app/', {
    'mobile': '9876543210',
    'password': 'your_password'
})
jwt_token = login_response.json()['token']

# Step 2: Prepare MQTT credentials
auth_response = requests.post('https://your-domain.com/mqtt/prepare-auth-token/', {
    'jwt_token': jwt_token
})
auth_data = auth_response.json()

if auth_data['success']:
    # Step 3: Connect to MQTT broker
    client = mqtt.Client()
    client.username_pw_set(
        username=auth_data['mqtt_username'],
        password=auth_data['mqtt_password']
    )
    
    # Configure TLS
    client.tls_set(
        ca_certs=auth_data['mqtt_ca_cert'],
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS
    )
    
    # Connect
    client.connect(
        host=auth_data['mqtt_host'],
        port=auth_data['mqtt_port'],
        keepalive=60
    )
    
    # Subscribe to topics
    client.subscribe(f"device/{auth_data['user_id']}/#")
    
    # Start loop
    client.loop_forever()
```

### JavaScript/Node.js Client Example
```javascript
const mqtt = require('mqtt');
const axios = require('axios');
const fs = require('fs');

async function connectMQTT() {
  // Step 1: Login and get JWT token
  const loginResponse = await axios.post('https://your-domain.com/user_login_app/', {
    mobile: '9876543210',
    password: 'your_password'
  });
  const jwtToken = loginResponse.data.token;
  
  // Step 2: Prepare MQTT credentials
  const authResponse = await axios.post('https://your-domain.com/mqtt/prepare-auth-token/', {
    jwt_token: jwtToken
  });
  const authData = authResponse.data;
  
  if (authData.success) {
    // Step 3: Connect to MQTT broker
    const client = mqtt.connect(`mqtts://${authData.mqtt_host}:${authData.mqtt_port}`, {
      username: authData.mqtt_username,
      password: authData.mqtt_password,
      ca: fs.readFileSync(authData.mqtt_ca_cert),
      rejectUnauthorized: true
    });
    
    client.on('connect', () => {
      console.log('Connected to MQTT broker');
      client.subscribe(`device/${authData.user_id}/#`);
    });
    
    client.on('message', (topic, message) => {
      console.log(`Received message on ${topic}: ${message.toString()}`);
    });
  }
}

connectMQTT();
```

### Android (Java/Kotlin) Example
```kotlin
import org.eclipse.paho.android.service.MqttAndroidClient
import org.eclipse.paho.client.mqttv3.*
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class MQTTManager {
    fun connectWithJWT(jwtToken: String) {
        // Step 1: Prepare MQTT credentials
        val request = PrepareAuthRequest(jwtToken)
        apiService.prepareMqttAuth(request).enqueue(object : Callback<MqttAuthResponse> {
            override fun onResponse(call: Call<MqttAuthResponse>, response: Response<MqttAuthResponse>) {
                val authData = response.body()
                if (authData?.success == true) {
                    // Step 2: Connect to MQTT
                    val mqttClient = MqttAndroidClient(
                        context,
                        "ssl://${authData.mqttHost}:${authData.mqttPort}",
                        authData.mqttUsername
                    )
                    
                    val options = MqttConnectOptions()
                    options.userName = authData.mqttUsername
                    options.password = authData.mqttPassword.toCharArray()
                    options.isCleanSession = true
                    
                    // Configure SSL
                    val socketFactory = getSSLSocketFactory(authData.mqttCaCert)
                    options.socketFactory = socketFactory
                    
                    mqttClient.connect(options, null, object : IMqttActionListener {
                        override fun onSuccess(asyncActionToken: IMqttToken?) {
                            Log.d("MQTT", "Connected successfully")
                            mqttClient.subscribe("device/${authData.userId}/#", 0)
                        }
                        
                        override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                            Log.e("MQTT", "Connection failed", exception)
                        }
                    })
                }
            }
            
            override fun onFailure(call: Call<MqttAuthResponse>, t: Throwable) {
                Log.e("API", "Failed to prepare MQTT auth", t)
            }
        })
    }
}
```

## Configuration Files

### Django Settings (`settings.py`)
```python
# MQTT Broker Configuration
MQTT_HOST = os.environ.get('MQTT_HOST', '127.0.0.1')
MQTT_PORT = os.environ.get('MQTT_PORT', '8883')
MQTT_ADMIN_USER = os.environ.get('MQTT_ADMIN_USER', 'admin')
MQTT_ADMIN_PASS = os.environ.get('MQTT_ADMIN_PASS', 'adminpass')
MQTT_CA_FILE = os.environ.get('MQTT_CA_FILE', '/etc/mosquitto/certs/ca.crt')
```

### Environment Variables (`.env`)
```bash
MQTT_HOST=127.0.0.1
MQTT_PORT=8883
MQTT_ADMIN_USER=admin
MQTT_ADMIN_PASS=adminpass
MQTT_CA_FILE=/etc/mosquitto/certs/ca.crt
```

## Security Features

1. **JWT Token Validation**: All JWT tokens are validated before MQTT user creation
2. **User Verification**: User must exist in Django database and be active
3. **Deterministic Passwords**: Passwords are generated from JWT token hash (same token = same password)
4. **TLS Encryption**: All MQTT connections use TLS 1.2+
5. **Certificate Validation**: Clients must trust the CA certificate
6. **Automatic User Management**: MQTT users are created/updated automatically

## Backward Compatibility

The system maintains full backward compatibility:
- **Existing username/password authentication continues to work**
- **Dynamic security user database is preserved**
- **No changes required for existing MQTT clients**
- **New clients can choose either authentication method**

## Testing

### Test JWT Authentication
```bash
# 1. Get JWT token
curl -X POST https://your-domain.com/user_login_app/ \
  -H "Content-Type: application/json" \
  -d '{"mobile": "9876543210", "password": "your_password"}'

# 2. Prepare MQTT credentials
curl -X POST https://your-domain.com/mqtt/prepare-auth-token/ \
  -H "Content-Type: application/json" \
  -d '{"jwt_token": "YOUR_JWT_TOKEN"}'

# 3. Connect to MQTT (use returned credentials)
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u RETURNED_USERNAME \
  -P RETURNED_PASSWORD \
  -t "test/#"
```

### Test Username/Password Authentication (Existing)
```bash
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile /etc/mosquitto/certs/ca.crt \
  -u 9876543210 \
  -P your_password \
  -t "test/#"
```

## Troubleshooting

### Check Logs
```bash
# Django application logs
tail -f /path/to/django/logs/app.log

# MQTT authentication logs
sudo tail -f /var/log/mqtt_unified_auth.log

# Mosquitto broker logs
sudo tail -f /var/log/mosquitto/mosquitto.log
```

### Common Issues

1. **JWT Token Expired**
   - Error: "Invalid or expired JWT token"
   - Solution: Request new JWT token from login endpoint

2. **User Not Found**
   - Error: "User not found or inactive"
   - Solution: Verify user exists and is_active=True in Django database

3. **MQTT Connection Failed**
   - Check network connectivity to MQTT broker
   - Verify TLS certificate is valid and trusted
   - Confirm MQTT broker is running: `sudo systemctl status mosquitto`

4. **Permission Denied**
   - Ensure mosquitto_ctrl has permissions to modify dynamic security
   - Check admin username/password in settings

## Migration Guide

### For Existing Deployments

1. **Backup Current Configuration**
   ```bash
   sudo cp /etc/mosquitto/mosquitto.conf /etc/mosquitto/mosquitto.conf.backup
   sudo cp /var/lib/mosquitto/dynamic-security.json /var/lib/mosquitto/dynamic-security.json.backup
   ```

2. **Deploy New Code**
   ```bash
   cd /home/azureuser/Skytrack_Backend
   git pull
   cd Skytronsystem
   python manage.py migrate
   ```

3. **Update Django Settings**
   - Add MQTT configuration to settings.py
   - Add environment variables to .env file

4. **Restart Services**
   ```bash
   sudo systemctl restart mosquitto
   sudo systemctl restart your-django-app
   ```

5. **Test Both Authentication Methods**
   - Test existing username/password clients
   - Test new JWT token authentication
   - Monitor logs for any issues

## Support

For issues or questions:
1. Check logs in `/var/log/mqtt_unified_auth.log`
2. Review Django application logs
3. Check Mosquitto broker logs
4. Verify JWT token is valid using `/verify-jwt-token/` endpoint (if available)

## Files Modified/Created

1. **Django Application**:
   - `/home/azureuser/Skytrack_Backend/Skytronsystem/skytron_api/mqtt_auth_views.py` (new)
   - `/home/azureuser/Skytrack_Backend/Skytronsystem/skytron_api/urls.py` (modified)
   - `/home/azureuser/Skytrack_Backend/Skytronsystem/Skytronsystem/settings.py` (modified)

2. **MQTT Scripts**:
   - `/home/azureuser/Skytrack_Backend/mqtt_unified_auth.py` (new)
   - `/home/azureuser/Skytrack_Backend/mqtt_auth_wrapper.sh` (new)
   - `/home/azureuser/Skytrack_Backend/mqtt_jwt_preauth_service.py` (new)
   - `/home/azureuser/Skytrack_Backend/mqtt_acl_check.py` (new)

3. **Configuration**:
   - `/home/azureuser/Skytrack_Backend/mqtt_deployment/config/mosquitto_unified_auth.conf` (new)
