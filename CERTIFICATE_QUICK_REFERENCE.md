# MQTT Certificate Chain - Quick Reference

## Problem
❌ Security audit flags: Certificate validation disabled (`tls_insecure_set(True)`)  
❌ Self-signed certificates without proper chain of trust

## Solution
✅ Create proper CA hierarchy: Root CA → Intermediate CA → Server Certificate  
✅ Enable certificate validation in all MQTT clients  
✅ Security audit compliant

---

## Quick Start (4 Steps)

### 1. Generate Certificates (One-time)
```bash
cd /path/to/Skytrack_Backend
sudo ./generate_trusted_certificates.sh
```
Creates:
- Root CA (distribute to all clients)
- Intermediate CA (signs server certs)
- Server certificate (for MQTT broker)
- Client certificates (optional)

### 2. Deploy to Mosquitto
Automatically done by script, or manually:
```bash
sudo cp mqtt_certificates/server/server.crt /etc/mosquitto/certs/
sudo cp mqtt_certificates/server/server.key /etc/mosquitto/certs/
sudo cp mqtt_certificates/intermediate_ca/ca_chain.crt /etc/mosquitto/certs/
sudo systemctl restart mosquitto
```

### 3. Update Django Container
```bash
# Copy root CA for Docker build
cp mqtt_certificates/root_ca/root_ca.crt Skytronsystem/root_ca.crt

# Rebuild container
./run_with_host_storage.sh
```

### 4. Distribute Root CA to Clients
All MQTT clients need: `mqtt_certificates/root_ca/root_ca.crt`

---

## Updated Code Examples

### ❌ BEFORE (Insecure - Audit Fail)
```python
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.tls_set(ca_certs="ca.crt")
client.tls_insecure_set(True)  # ❌ Disables validation!
client.connect("mqtt.gromed.in", 8883)
```

### ✅ AFTER (Secure - Audit Pass)
```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()
client.tls_set(
    ca_certs="root_ca.crt",  # Root CA certificate
    cert_reqs=ssl.CERT_REQUIRED,  # ✅ Require validation
    tls_version=ssl.PROTOCOL_TLSv1_2
)
# No tls_insecure_set() - validation enabled!
client.connect("mqtt.gromed.in", 8883)
```

---

## Mosquitto Configuration

### Update /etc/mosquitto/conf.d/tls.conf:
```conf
listener 8883
cafile /etc/mosquitto/certs/ca_chain.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
tls_version tlsv1.2
require_certificate false
```

---

## Testing

### Test Connection (Security Compliant)
```bash
mosquitto_sub -h mqtt.gromed.in -p 8883 \
  --cafile mqtt_certificates/root_ca/root_ca.crt \
  -u "jwt" -P "YOUR_JWT_TOKEN" \
  -t "test/topic" -v
```

### Verify Certificate Chain
```bash
openssl verify -CAfile mqtt_certificates/intermediate_ca/ca_chain.crt \
  mqtt_certificates/server/server.crt
# Should output: OK
```

### Check Certificate Details
```bash
# View server certificate SANs (Subject Alternative Names)
openssl x509 -in mqtt_certificates/server/server.crt -text -noout | grep -A 10 "Subject Alternative Name"

# Check expiration
openssl x509 -in mqtt_certificates/server/server.crt -noout -enddate
```

---

## Certificate Validity

| Certificate | Validity | Purpose |
|------------|----------|---------|
| Root CA | 20 years | Self-signed, kept offline |
| Intermediate CA | 10 years | Signs server/client certs |
| Server Certificate | ~2 years | MQTT broker identity |
| Client Certificates | ~2 years | Optional mutual TLS |

---

## Distribution Checklist

- [ ] Generate certificates: `sudo ./generate_trusted_certificates.sh`
- [ ] Deploy to Mosquitto: Auto-deployed by script
- [ ] Update Mosquitto config: `/etc/mosquitto/conf.d/tls.conf`
- [ ] Restart Mosquitto: `sudo systemctl restart mosquitto`
- [ ] Copy root CA for Docker: `cp mqtt_certificates/root_ca/root_ca.crt Skytronsystem/`
- [ ] Rebuild Django container: `./run_with_host_storage.sh`
- [ ] Distribute root CA to all clients
- [ ] Update client code (remove `tls_insecure_set()`)
- [ ] Test connections with validation enabled

---

## Troubleshooting

### Error: "certificate verify failed"
**Fix:** Ensure client has correct root CA file
```bash
# Check client has root_ca.crt, not old ca.crt
ls -la mqtt_certificates/root_ca/root_ca.crt
```

### Error: "Hostname mismatch"
**Fix:** Connect using hostname, not IP
```python
# ❌ Wrong
client.connect("135.235.166.209", 8883)

# ✅ Correct
client.connect("mqtt.gromed.in", 8883)
```

### Error: "unable to get local issuer certificate"
**Fix:** Use ca_chain.crt (includes intermediate + root)
```conf
cafile /etc/mosquitto/certs/ca_chain.crt  # Not just root_ca.crt
```

---

## Certificate Renewal (Every ~2 Years)

Server certificates expire in 2 years. To renew:

```bash
# Navigate to certificate directory
cd mqtt_certificates/server

# Generate new server certificate (reuses existing CA)
openssl genrsa -out server_new.key 2048
openssl req -new -key server_new.key -out server_new.csr -config server.conf

# Sign with Intermediate CA (not root!)
openssl x509 -req -in server_new.csr \
  -CA ../intermediate_ca/intermediate_ca.crt \
  -CAkey ../intermediate_ca/intermediate_ca.key \
  -CAcreateserial -out server_new.crt \
  -days 825 -sha256 -extensions v3_req -extfile server.conf

# Deploy
sudo cp server_new.crt /etc/mosquitto/certs/server.crt
sudo cp server_new.key /etc/mosquitto/certs/server.key
sudo systemctl restart mosquitto
```

**Note:** Clients don't need updates - they still use same root CA!

---

## Files Created

```
Skytrack_Backend/
├── generate_trusted_certificates.sh       # Generate certificate chain
├── check_certificate_deployment.sh        # Verify deployment
├── CERTIFICATE_CHAIN_SECURITY.md          # Full documentation
├── CERTIFICATE_QUICK_REFERENCE.md         # This file
└── mqtt_certificates/
    ├── root_ca/
    │   └── root_ca.crt                    # Distribute to ALL clients
    ├── intermediate_ca/
    │   ├── intermediate_ca.crt
    │   └── ca_chain.crt                   # For Mosquitto config
    ├── server/
    │   ├── server.crt                     # MQTT broker certificate
    │   ├── server.key                     # MQTT broker private key
    │   └── server_chain.crt               # Full chain
    └── client/
        ├── client.crt                     # Optional: for mutual TLS
        └── client.key
```

---

## Security Compliance

✅ **Certificate Chain of Trust**
- Proper CA hierarchy (Root → Intermediate → Server)
- Root CA can be kept offline and secure
- Intermediate CA signs operational certificates

✅ **Certificate Validation Enabled**
- `CERT_REQUIRED` in Python
- No `tls_insecure_set(True)`
- No `rejectUnauthorized: false` in Node.js
- Proper hostname verification

✅ **Industry Standards**
- TLS 1.2 or higher
- Server certs valid ≤825 days (~2 years)
- Strong encryption (RSA 2048-bit minimum)
- Subject Alternative Names (SANs) configured

✅ **Key Management**
- Private keys with restricted permissions (600)
- Root CA key kept offline
- Separate keys for server and clients

---

## Support

For detailed information, see:
- **Full Guide:** `CERTIFICATE_CHAIN_SECURITY.md`
- **Deployment:** Run `./check_certificate_deployment.sh`
- **Testing:** See "Testing" section above

---

**Last Updated:** $(date +"%Y-%m-%d")
**Security Status:** ✅ Audit Compliant
