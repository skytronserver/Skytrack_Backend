#!/usr/bin/env python3
"""
MQTT JWT Authentication Test Script
Tests both JWT token and username/password authentication
"""
import sys
import os
import requests
import time
import ssl
import json

# Add Django path for testing
sys.path.append('/home/azureuser/Skytrack_Backend/Skytronsystem')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Skytronsystem.settings')

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("WARNING: paho-mqtt not installed. Install with: pip install paho-mqtt")

# Configuration
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000')
TEST_MOBILE = os.environ.get('TEST_MOBILE', '9876543210')
TEST_PASSWORD = os.environ.get('TEST_PASSWORD', 'test123')

def test_login():
    """Test user login and JWT token generation"""
    print("\n=== Test 1: User Login ===")
    try:
        response = requests.post(f'{API_BASE_URL}/user_login_app/', {
            'mobile': TEST_MOBILE,
            'password': TEST_PASSWORD
        })
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'token' in data:
                print(f"✓ Login successful")
                print(f"  JWT Token: {data['token'][:50]}...")
                return data['token']
            else:
                print(f"✗ Login failed: No token in response")
                print(f"  Response: {data}")
                return None
        else:
            print(f"✗ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Login error: {e}")
        return None

def test_prepare_mqtt_auth_with_token(jwt_token):
    """Test MQTT auth preparation with JWT token"""
    print("\n=== Test 2: Prepare MQTT Auth with JWT Token ===")
    try:
        response = requests.post(f'{API_BASE_URL}/mqtt/prepare-auth-token/', 
            json={'jwt_token': jwt_token}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✓ MQTT credentials prepared successfully")
                print(f"  MQTT Username: {data['mqtt_username']}")
                print(f"  MQTT Password: {data['mqtt_password'][:20]}...")
                print(f"  MQTT Host: {data['mqtt_host']}")
                print(f"  MQTT Port: {data['mqtt_port']}")
                print(f"  User ID: {data.get('user_id')}")
                print(f"  Mobile: {data.get('mobile')}")
                return data
            else:
                print(f"✗ Failed: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"✗ Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_prepare_mqtt_auth_authenticated(jwt_token):
    """Test MQTT auth preparation with authenticated endpoint"""
    print("\n=== Test 3: Prepare MQTT Auth (Authenticated) ===")
    try:
        headers = {'Authorization': f'Token {jwt_token}'}
        response = requests.get(f'{API_BASE_URL}/mqtt/prepare-auth/', 
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✓ MQTT credentials prepared successfully")
                print(f"  MQTT Username: {data['mqtt_username']}")
                print(f"  MQTT Password: {data['mqtt_password'][:20]}...")
                return data
            else:
                print(f"✗ Failed: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"✗ Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_mqtt_connection(mqtt_creds):
    """Test actual MQTT connection"""
    if not MQTT_AVAILABLE:
        print("\n=== Test 4: MQTT Connection ===")
        print("✗ Skipped: paho-mqtt not installed")
        return False
    
    print("\n=== Test 4: MQTT Connection ===")
    try:
        # Create MQTT client
        client = mqtt.Client()
        
        # Set username and password
        client.username_pw_set(
            username=mqtt_creds['mqtt_username'],
            password=mqtt_creds['mqtt_password']
        )
        
        # Configure TLS if using secure connection
        if mqtt_creds['mqtt_use_tls']:
            try:
                client.tls_set(
                    ca_certs=mqtt_creds['mqtt_ca_cert'],
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS
                )
                print("  TLS configured")
            except Exception as e:
                print(f"  Warning: TLS configuration failed: {e}")
                print("  Attempting connection without TLS verification...")
                client.tls_set(cert_reqs=ssl.CERT_NONE)
                client.tls_insecure_set(True)
        
        # Connection callbacks
        connected = [False]
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"✓ Successfully connected to MQTT broker")
                connected[0] = True
            else:
                print(f"✗ Connection failed with code {rc}")
                if rc == 1:
                    print("  Error: Connection refused - incorrect protocol version")
                elif rc == 2:
                    print("  Error: Connection refused - invalid client identifier")
                elif rc == 3:
                    print("  Error: Connection refused - server unavailable")
                elif rc == 4:
                    print("  Error: Connection refused - bad username or password")
                elif rc == 5:
                    print("  Error: Connection refused - not authorized")
        
        def on_disconnect(client, userdata, rc):
            print(f"  Disconnected from MQTT broker (rc={rc})")
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        
        # Connect
        print(f"  Connecting to {mqtt_creds['mqtt_host']}:{mqtt_creds['mqtt_port']}...")
        client.connect(
            host=mqtt_creds['mqtt_host'],
            port=int(mqtt_creds['mqtt_port']),
            keepalive=60
        )
        
        # Start loop and wait for connection
        client.loop_start()
        time.sleep(3)
        
        # Check if connected
        if connected[0]:
            # Try to subscribe
            topic = f"test/{mqtt_creds['mqtt_username']}/#"
            result = client.subscribe(topic)
            print(f"  Subscribed to topic: {topic}")
            
            # Publish test message
            client.publish(f"test/{mqtt_creds['mqtt_username']}/hello", "Test message")
            print(f"  Published test message")
            
            time.sleep(1)
        
        # Disconnect
        client.loop_stop()
        client.disconnect()
        
        return connected[0]
        
    except Exception as e:
        print(f"✗ MQTT connection error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_user_verification():
    """Verify MQTT user was created in dynamic security"""
    print("\n=== Test 5: Verify MQTT User in Dynamic Security ===")
    try:
        import subprocess
        result = subprocess.run(
            ['mosquitto_ctrl', '--cafile', '/etc/mosquitto/certs/ca.crt',
             '-h', '127.0.0.1', '-p', '8883',
             '-u', 'admin', '-P', 'adminpass',
             'dynsec', 'listClients'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✓ Successfully queried dynamic security")
            # Print first few clients
            try:
                clients = json.loads(result.stdout)
                print(f"  Total clients: {len(clients.get('clients', []))}")
                for client in clients.get('clients', [])[:5]:
                    print(f"    - {client.get('username')}")
            except:
                print(f"  Response: {result.stdout[:200]}")
        else:
            print(f"✗ Failed to query dynamic security: {result.stderr}")
            
    except FileNotFoundError:
        print("✗ mosquitto_ctrl not found. Install mosquitto-clients package.")
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("MQTT JWT Authentication Test Suite")
    print("=" * 60)
    
    # Test 1: Login
    jwt_token = test_login()
    if not jwt_token:
        print("\n✗ Cannot proceed without valid JWT token")
        sys.exit(1)
    
    # Test 2: Prepare MQTT auth with token
    mqtt_creds = test_prepare_mqtt_auth_with_token(jwt_token)
    if not mqtt_creds:
        print("\n✗ Cannot proceed without MQTT credentials")
        sys.exit(1)
    
    # Test 3: Prepare MQTT auth with authenticated endpoint
    test_prepare_mqtt_auth_authenticated(jwt_token)
    
    # Test 4: Actual MQTT connection
    test_mqtt_connection(mqtt_creds)
    
    # Test 5: Verify user in dynamic security
    test_manual_user_verification()
    
    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
