#!/usr/bin/env python3
"""
Simple MQTT Client Example using JWT Authentication
Demonstrates the complete flow: Login -> Get MQTT Creds -> Connect to MQTT
"""
import requests
import paho.mqtt.client as mqtt
import ssl
import sys
import time

# Configuration
API_URL = "http://127.0.0.1:8000"  # Change to your Django server URL
MOBILE = "9876543210"  # Change to your test mobile number
PASSWORD = "test123"    # Change to your test password

def main():
    print("=" * 60)
    print("MQTT JWT Authentication Client Example")
    print("=" * 60)
    
    # Step 1: Login and get JWT token
    print("\n[1/3] Logging in...")
    try:
        response = requests.post(f"{API_URL}/user_login_app/", {
            "mobile": MOBILE,
            "password": PASSWORD
        })
        
        if response.status_code != 200:
            print(f"✗ Login failed: {response.text}")
            sys.exit(1)
        
        jwt_token = response.json().get('token')
        if not jwt_token:
            print("✗ No token in response")
            sys.exit(1)
            
        print(f"✓ Login successful! Token: {jwt_token[:30]}...")
        
    except Exception as e:
        print(f"✗ Login error: {e}")
        sys.exit(1)
    
    # Step 2: Prepare MQTT credentials
    print("\n[2/3] Preparing MQTT credentials...")
    try:
        response = requests.post(f"{API_URL}/mqtt/prepare-auth-token/", 
            json={"jwt_token": jwt_token}
        )
        
        if response.status_code != 200:
            print(f"✗ Failed to prepare MQTT auth: {response.text}")
            sys.exit(1)
        
        mqtt_creds = response.json()
        if not mqtt_creds.get('success'):
            print(f"✗ Failed: {mqtt_creds.get('error')}")
            sys.exit(1)
        
        print(f"✓ MQTT credentials ready!")
        print(f"  Username: {mqtt_creds['mqtt_username']}")
        print(f"  Host: {mqtt_creds['mqtt_host']}:{mqtt_creds['mqtt_port']}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    
    # Step 3: Connect to MQTT broker
    print("\n[3/3] Connecting to MQTT broker...")
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✓ Connected to MQTT broker!")
            
            # Subscribe to user-specific topics
            topic = f"device/{mqtt_creds['user_id']}/#"
            client.subscribe(topic)
            print(f"✓ Subscribed to: {topic}")
            
            # Publish a test message
            client.publish(f"device/{mqtt_creds['user_id']}/status", "online")
            print(f"✓ Published status message")
            
        else:
            print(f"✗ Connection failed with code: {rc}")
            if rc == 4:
                print("  (Authentication failed - check credentials)")
    
    def on_message(client, userdata, msg):
        print(f"  📨 Message on {msg.topic}: {msg.payload.decode()}")
    
    def on_disconnect(client, userdata, rc):
        print(f"  Disconnected (rc={rc})")
    
    try:
        # Create MQTT client
        client = mqtt.Client(f"client_{mqtt_creds['user_id']}")
        
        # Set callbacks
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        
        # Set authentication
        client.username_pw_set(
            username=mqtt_creds['mqtt_username'],
            password=mqtt_creds['mqtt_password']
        )
        
        # Configure TLS
        if mqtt_creds.get('mqtt_use_tls'):
            try:
                client.tls_set(
                    ca_certs=mqtt_creds['mqtt_ca_cert'],
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS
                )
            except FileNotFoundError:
                print("  ⚠ CA certificate not found, using insecure connection")
                client.tls_set(cert_reqs=ssl.CERT_NONE)
                client.tls_insecure_set(True)
        
        # Connect
        client.connect(
            mqtt_creds['mqtt_host'],
            int(mqtt_creds['mqtt_port']),
            keepalive=60
        )
        
        # Start loop
        print("\n  Listening for messages (Press Ctrl+C to exit)...")
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n✓ Disconnecting...")
        client.disconnect()
        print("✓ Done!")
        
    except Exception as e:
        print(f"✗ MQTT error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
