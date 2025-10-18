#!/usr/bin/env python3
"""
Test script for SOS Executive MQTT message
Usage: python3 test_sos_mqtt.py <token>
"""

import paho.mqtt.client as mqtt
import ssl
import json
import sys
import time

# MQTT Configuration
BROKER = "135.235.166.209"
PORT = 8883
CA_CERT = "/etc/mosquitto/certs/ca.crt"

# MQTT Users (you can change which user to use for testing)
MQTT_USERS = {
    "admin": "adminpass",
    "6026929588": "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h",
    "1000000010": "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h",
    "1000000011": "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h"
}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker")
        # Subscribe to response topic
        client.subscribe("sosEx/response")
        print("📺 Subscribed to sosEx/response")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    print(f"📨 Response received on {msg.topic}:")
    try:
        response = json.loads(msg.payload.decode())
        print(json.dumps(response, indent=2))
    except:
        print(msg.payload.decode())

def on_publish(client, userdata, mid):
    print("📤 Message published successfully")

def send_sos_message(token, username="admin", password="adminpass"):
    # Test message payload
    test_message = {
        "token": token,
        "em_lat": 26.133602,
        "em_lon": 91.804747,
        "speed": 45.5,
        "assignment_id": None  # Set to specific ID if you have an active assignment
    }
    
    print(f"🔄 Testing SOS Executive message...")
    print(f"User: {username}")
    print(f"Topic: sosEx/123456")
    print(f"Message: {json.dumps(test_message, indent=2)}")
    print("-" * 50)
    
    # Create MQTT client
    client = mqtt.Client()
    client.username_pw_set(username, password)
    client.tls_set(ca_certs=CA_CERT, tls_version=ssl.PROTOCOL_TLS)
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    
    try:
        # Connect and wait for connection
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        # Publish test message
        topic = "sosEx/123456"  # Replace 123456 with actual user ID if needed
        message_json = json.dumps(test_message)
        
        result = client.publish(topic, message_json)
        result.wait_for_publish()
        
        print("⏳ Waiting for response...")
        time.sleep(5)  # Wait for response
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 test_sos_mqtt.py <token>")
        print("Example: python3 test_sos_mqtt.py abc123xyz")
        sys.exit(1)
    
    token = sys.argv[1]
    
    # You can change which user to test with
    username = "admin"
    password = MQTT_USERS[username]
    
    send_sos_message(token, username, password)