import paho.mqtt.client as mqtt
import ssl
import time

# MQTT broker settings
broker = "135.235.166.209"
port = 8883
username = "6026969588"   #  -P 'testpass123' 
password =  'isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h'#"testpass123"
topic = "test/topic"
message = "Hello from VS Code (secure)"

# Flag to check connection
connected = False

# Callback when client connects to broker
def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print("✅ Connected to MQTT broker successfully.")
        connected = True
    else:
        print(f"❌ Failed to connect, return code {rc}")

# Callback for publish result
def on_publish(client, userdata, mid):
    print("📤 Message published.")

# Create client
client = mqtt.Client()
client.username_pw_set(username, password)
client.tls_set(ca_certs="/etc/mosquitto/certs/ca.crt", tls_version=ssl.PROTOCOL_TLS)

# Attach callbacks
client.on_connect = on_connect
client.on_publish = on_publish

# Connect and wait for connection
try:
    client.connect(broker, port, 60)
    client.loop_start()

    # ⏳ Wait for on_connect to set the flag
    for _ in range(10):  # Try for ~10 seconds
        if connected:
            break
        
        
        time.sleep(1)

    if not connected:
        print("❌ Could not connect to MQTT broker.")
    else:
        result = client.publish(topic, message)
        result.wait_for_publish()
        time.sleep(1)  # Allow time for publish callback

    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"❌ Error: {e}")