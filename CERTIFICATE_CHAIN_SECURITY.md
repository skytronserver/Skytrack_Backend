# MQTT Certificate Chain of Trust - Security Compliance Guide

## Problem Statement

**Issue:** MQTT clients currently disable certificate validation (`tls_insecure_set(True)`) which is flagged in security audits.

**Root Cause:** Self-signed certificates without a proper chain of trust.

**Solution:** Create a proper Certificate Authority (CA) hierarchy with a chain of trust.

## Certificate Chain Structure

```
Root CA (Self-signed, 20 years)
    ├── Intermediate CA (Signed by Root, 10 years)
        ├── Server Certificate (Signed by Intermediate, 2 years)
        └── Client Certificates (Signed by Intermediate, 2 years)
```

**Benefits:**
- ✅ Root CA can be kept offline and secure
- ✅ Intermediate CA signs operational certificates
- ✅ Server certs can be renewed without changing root trust
- ✅ Clients validate against root CA (proper chain of trust)
- ✅ Security audit compliant (no certificate validation bypass)

## Step 1: Generate Certificates

```bash
cd /path/to/Skytrack_Backend
sudo ./generate_trusted_certificates.sh
```

This creates:
- **Root CA**: `mqtt_certificates/root_ca/root_ca.crt` (distribute to all clients)
- **Intermediate CA**: `mqtt_certificates/intermediate_ca/intermediate_ca.crt`
- **CA Chain**: `mqtt_certificates/intermediate_ca/ca_chain.crt` (root + intermediate)
- **Server Certificate**: `mqtt_certificates/server/server.crt`
- **Server Key**: `mqtt_certificates/server/server.key`
- **Server Chain**: `mqtt_certificates/server/server_chain.crt` (full chain)

## Step 2: Update Mosquitto Configuration

Edit `/etc/mosquitto/conf.d/tls.conf`:

```conf
# TLS Configuration with Certificate Chain
listener 8883
protocol mqtt

# Use CA chain for client verification
cafile /etc/mosquitto/certs/ca_chain.crt

# Server certificate with full chain
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key

# TLS settings
tls_version tlsv1.2
require_certificate false
use_identity_as_username false

# Disable insecure connections
allow_anonymous false
```

**Restart Mosquitto:**
```bash
sudo systemctl restart mosquitto
sudo systemctl status mosquitto
```

## Step 3: Distribute Root CA to Clients

All MQTT clients need the root CA certificate to validate the server.

### Option A: System Trust Store (Recommended for Production)

**Linux (Ubuntu/Debian):**
```bash
# Copy root CA to system trust store
sudo cp mqtt_certificates/root_ca/root_ca.crt /usr/local/share/ca-certificates/skytron_root_ca.crt
sudo update-ca-certificates
```

**Linux (RHEL/CentOS):**
```bash
sudo cp mqtt_certificates/root_ca/root_ca.crt /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

**Windows:**
```powershell
# Import to Trusted Root Certification Authorities
certutil -addstore "Root" skytron_root_ca.crt
```

### Option B: Application-Level (For Testing/Development)

Provide the root CA file path to your MQTT client library.

## Step 4: Update Client Code

### Python (Paho MQTT)

**Before (INSECURE - Security Audit Fail):**
```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()

# ❌ INSECURE: Disables certificate validation
client.tls_set(
    ca_certs="/path/to/ca.crt",
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.tls_insecure_set(True)  # ❌ Security audit flag!

client.connect("mqtt.gromed.in", 8883)
```

**After (SECURE - Security Audit Pass):**
```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()

# ✅ SECURE: Proper certificate validation
client.tls_set(
    ca_certs="/path/to/root_ca.crt",  # Root CA certificate
    certfile=None,  # Optional: client certificate
    keyfile=None,   # Optional: client key
    tls_version=ssl.PROTOCOL_TLSv1_2,
    cert_reqs=ssl.CERT_REQUIRED,  # ✅ Require valid certificate
    ciphers=None
)
# ✅ NO tls_insecure_set() call - validation is enabled!

# Connect using hostname that matches certificate CN/SAN
client.connect("mqtt.gromed.in", 8883)
```

### Python (Using System CA Store)

```python
import paho.mqtt.client as mqtt
import ssl
import certifi  # pip install certifi

client = mqtt.Client()

# Use system CA store (if root CA installed system-wide)
context = ssl.create_default_context(cafile=certifi.where())
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED

client.tls_set_context(context)
client.connect("mqtt.gromed.in", 8883)
```

### Java (Eclipse Paho)

```java
import org.eclipse.paho.client.mqttv3.*;
import javax.net.ssl.*;
import java.io.FileInputStream;
import java.security.KeyStore;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;

public class SecureMqttClient {
    public static void main(String[] args) throws Exception {
        String broker = "ssl://mqtt.gromed.in:8883";
        String clientId = "JavaClient";
        
        // Load root CA certificate
        CertificateFactory cf = CertificateFactory.getInstance("X.509");
        FileInputStream caInput = new FileInputStream("/path/to/root_ca.crt");
        X509Certificate ca = (X509Certificate) cf.generateCertificate(caInput);
        caInput.close();
        
        // Create keystore with root CA
        KeyStore keyStore = KeyStore.getInstance(KeyStore.getDefaultType());
        keyStore.load(null, null);
        keyStore.setCertificateEntry("ca", ca);
        
        // Create TrustManager with root CA
        TrustManagerFactory tmf = TrustManagerFactory.getInstance(
            TrustManagerFactory.getDefaultAlgorithm()
        );
        tmf.init(keyStore);
        
        // Create SSL context
        SSLContext sslContext = SSLContext.getInstance("TLSv1.2");
        sslContext.init(null, tmf.getTrustManagers(), null);
        
        // Create MQTT client with proper SSL
        MqttClient client = new MqttClient(broker, clientId);
        MqttConnectOptions options = new MqttConnectOptions();
        options.setSocketFactory(sslContext.getSocketFactory());
        
        // ✅ Certificate validation is enabled by default
        client.connect(options);
    }
}
```

### Node.js (MQTT.js)

```javascript
const mqtt = require('mqtt');
const fs = require('fs');

// Load root CA certificate
const ca = fs.readFileSync('/path/to/root_ca.crt');

const client = mqtt.connect('mqtts://mqtt.gromed.in:8883', {
    ca: ca,
    rejectUnauthorized: true,  // ✅ Enable certificate validation
    protocol: 'mqtts',
    port: 8883
});

client.on('connect', () => {
    console.log('Connected securely with certificate validation');
});
```

### Android (Java/Kotlin)

```kotlin
import org.eclipse.paho.android.service.MqttAndroidClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import java.io.InputStream
import java.security.KeyStore
import java.security.cert.CertificateFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManagerFactory

class SecureMqttClient(context: Context) {
    private val serverUri = "ssl://mqtt.gromed.in:8883"
    private val clientId = "AndroidClient"
    
    fun connect() {
        val client = MqttAndroidClient(context, serverUri, clientId)
        
        // Load root CA from assets
        val cf = CertificateFactory.getInstance("X.509")
        val caInputStream: InputStream = context.assets.open("root_ca.crt")
        val ca = cf.generateCertificate(caInputStream)
        caInputStream.close()
        
        // Create keystore with root CA
        val keyStore = KeyStore.getInstance(KeyStore.getDefaultType())
        keyStore.load(null, null)
        keyStore.setCertificateEntry("ca", ca)
        
        // Create SSL context
        val tmf = TrustManagerFactory.getInstance(
            TrustManagerFactory.getDefaultAlgorithm()
        )
        tmf.init(keyStore)
        val sslContext = SSLContext.getInstance("TLS")
        sslContext.init(null, tmf.trustManagers, null)
        
        // Connect with SSL
        val options = MqttConnectOptions()
        options.socketFactory = sslContext.socketFactory
        
        client.connect(options)
    }
}
```

### iOS (Swift - CocoaMQTT)

```swift
import CocoaMQTT

class SecureMqttClient {
    func connect() {
        let clientID = "iOSClient"
        let mqtt = CocoaMQTT(clientID: clientID, host: "mqtt.gromed.in", port: 8883)
        
        // Enable SSL with root CA
        mqtt.enableSSL = true
        
        // Load root CA certificate
        if let caPath = Bundle.main.path(forResource: "root_ca", ofType: "crt"),
           let caData = try? Data(contentsOf: URL(fileURLWithPath: caPath)) {
            
            let certificates = [SecCertificateCreateWithData(nil, caData as CFData)!]
            
            mqtt.allowUntrustCertificate = false  // ✅ Validate certificate
            mqtt.sslSettings = [
                kCFStreamSSLCertificates as String: certificates,
                kCFStreamSSLValidatesCertificateChain as String: true
            ]
        }
        
        mqtt.connect()
    }
}
```

## Step 5: Update Django Container MQTT Client

For the MQTT client inside Django container (`mqttClienttrack.py`):

```python
import paho.mqtt.client as mqtt
import ssl
import os

# Get certificate path (inside container)
CERT_DIR = "/app/Skytronsystem"
ROOT_CA = os.path.join(CERT_DIR, "root_ca.crt")

def create_mqtt_client():
    client = mqtt.Client()
    
    # ✅ SECURE: Enable certificate validation
    if os.path.exists(ROOT_CA):
        client.tls_set(
            ca_certs=ROOT_CA,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            cert_reqs=ssl.CERT_REQUIRED
        )
    else:
        raise FileError(f"Root CA not found: {ROOT_CA}")
    
    # Set credentials (JWT token authentication)
    client.username_pw_set(username="jwt", password=get_jwt_token())
    
    return client
```

**Update Dockerfile to include root CA:**
```dockerfile
# Copy root CA into container
COPY mqtt_certificates/root_ca/root_ca.crt /app/Skytronsystem/root_ca.crt
RUN chmod 644 /app/Skytronsystem/root_ca.crt
```

## Step 6: Verify Certificate Chain

Test that the certificate chain is valid:

```bash
# Verify server certificate against CA chain
openssl verify -CAfile mqtt_certificates/intermediate_ca/ca_chain.crt \
    mqtt_certificates/server/server.crt

# Should output: mqtt_certificates/server/server.crt: OK
```

Check certificate details:

```bash
# View server certificate
openssl x509 -in mqtt_certificates/server/server.crt -text -noout

# Check SANs (Subject Alternative Names)
openssl x509 -in mqtt_certificates/server/server.crt -text -noout | grep -A 10 "Subject Alternative Name"
```

## Step 7: Test Secure Connection

Test with mosquitto_sub (with validation enabled):

```bash
# ✅ With certificate validation (secure)
mosquitto_sub -h mqtt.gromed.in -p 8883 \
  --cafile mqtt_certificates/root_ca/root_ca.crt \
  -u "jwt" \
  -P "YOUR_JWT_TOKEN" \
  -t "test/topic" -v

# Should connect successfully without tls_insecure flag
```

Test from Python:

```python
import paho.mqtt.client as mqtt
import ssl

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if rc == 0:
        print("✅ Secure connection with certificate validation!")
    else:
        print(f"❌ Connection failed: {rc}")

client = mqtt.Client()
client.on_connect = on_connect

# Enable certificate validation
client.tls_set(
    ca_certs="mqtt_certificates/root_ca/root_ca.crt",
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.username_pw_set("jwt", "YOUR_JWT_TOKEN")
client.connect("mqtt.gromed.in", 8883, 60)
client.loop_forever()
```

## Security Audit Compliance Checklist

✅ **Proper CA Hierarchy**
- Root CA → Intermediate CA → Server Certificate
- Root CA kept secure and offline
- Intermediate CA signs operational certificates

✅ **Certificate Validation Enabled**
- No `tls_insecure_set(True)` in Python
- No `rejectUnauthorized: false` in Node.js
- No custom TrustManager that accepts all certificates in Java
- Proper hostname verification

✅ **Industry Standards**
- Server certificates valid for ≤825 days (~2 years)
- Strong encryption (RSA 2048-bit minimum)
- TLS 1.2 or higher
- Subject Alternative Names (SANs) configured

✅ **Key Management**
- Private keys have restricted permissions (600)
- Root CA key kept offline
- Separate keys for server and clients

✅ **Certificate Distribution**
- Root CA distributed to all clients
- Clients verify server certificate against root CA
- No certificate validation bypass

## Troubleshooting

### Error: "certificate verify failed"

**Cause:** Client cannot validate server certificate

**Solutions:**
1. Ensure client has correct root CA file
2. Check server hostname matches certificate CN/SAN
3. Verify certificate chain is complete

```bash
# Check what hostname client is using
openssl s_client -connect mqtt.gromed.in:8883 -showcerts

# Must match one of the SANs in certificate
```

### Error: "Hostname mismatch"

**Cause:** Connecting to IP address but certificate has DNS name

**Solution:** Connect using hostname that matches certificate:
```python
# ❌ Wrong: Using IP
client.connect("135.235.166.209", 8883)

# ✅ Correct: Using hostname from certificate
client.connect("mqtt.gromed.in", 8883)
```

Or regenerate certificate with IP in SAN.

### Error: "unable to get local issuer certificate"

**Cause:** Certificate chain incomplete

**Solution:** Use ca_chain.crt (includes intermediate + root):
```bash
# In mosquitto config
cafile /etc/mosquitto/certs/ca_chain.crt
```

## Certificate Renewal

Server certificates expire in ~2 years. To renew:

```bash
# 1. Generate new server certificate (reuses existing CA)
cd mqtt_certificates/server
openssl genrsa -out server_new.key 2048
openssl req -new -key server_new.key -out server_new.csr -config server.conf

# 2. Sign with Intermediate CA
openssl x509 -req -in server_new.csr \
    -CA ../intermediate_ca/intermediate_ca.crt \
    -CAkey ../intermediate_ca/intermediate_ca.key \
    -CAcreateserial -out server_new.crt \
    -days 825 -sha256 -extensions v3_req -extfile server.conf

# 3. Deploy to Mosquitto
sudo cp server_new.crt /etc/mosquitto/certs/server.crt
sudo cp server_new.key /etc/mosquitto/certs/server.key
sudo systemctl restart mosquitto
```

**Note:** Clients don't need updates - they still use same root CA!

## Summary

✅ **Security Compliance Achieved:**
- Proper certificate chain of trust
- No certificate validation bypass
- Industry-standard certificate lifetimes
- Secure key management

✅ **Audit Requirements Met:**
- Certificate validation enabled on all clients
- Strong encryption (TLS 1.2+)
- Proper hostname verification
- No security warnings

✅ **Operational Benefits:**
- Easy certificate renewal (server only)
- Root CA remains trusted
- Clients don't need updates for server cert renewal
- Proper separation of concerns (Root → Intermediate → Operational)
