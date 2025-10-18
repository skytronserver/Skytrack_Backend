#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import ssl
import sys
import time

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected successfully!")
        print(f"Connection result: {rc}")
        client.subscribe("test/topic")
    else:
        print(f"❌ Connection failed with result code {rc}")
        error_messages = {
            1: "Connection refused – incorrect protocol version",
            2: "Connection refused – invalid client identifier",
            3: "Connection refused – server unavailable",
            4: "Connection refused – bad username or password",
            5: "Connection refused – not authorised"
        }
        print(f"Error: {error_messages.get(rc, 'Unknown error')}")

def on_message(client, userdata, msg):
    print(f"📨 Received message: {msg.topic} - {msg.payload.decode()}")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"📺 Subscribed successfully with QoS: {granted_qos}")

def on_disconnect(client, userdata, rc):
    print(f"🔌 Disconnected with result code {rc}")

def test_mqtt_connection():
    # Configuration
    MQTT_HOST = "127.0.0.1"
    MQTT_PORT = 8883
    USERNAME = "9998887777"
    PASSWORD = "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h"
    CA_CERT = "/etc/mosquitto/certs/ca.crt"
    
    print("🔄 Testing MQTT connection...")
    print(f"Host: {MQTT_HOST}:{MQTT_PORT}")
    print(f"Username: {USERNAME}")
    print(f"CA Certificate: {CA_CERT}")
    print("-" * 50)
    
    # Create MQTT client
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    
    # Set up SSL/TLS
    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(CA_CERT)
        client.tls_set_context(context)
        print("✅ SSL context configured")
    except Exception as e:
        print(f"❌ SSL setup failed: {e}")
        return False
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    
    try:
        print("🔄 Connecting...")
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        
        # Start loop
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Test publish
        if client.is_connected():
            print("📤 Publishing test message...")
            client.publish("test/topic", "Hello from test script!")
            time.sleep(1)
        
        # Keep alive for a bit
        time.sleep(5)
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_mqtt_connection()
    sys.exit(0 if success else 1)