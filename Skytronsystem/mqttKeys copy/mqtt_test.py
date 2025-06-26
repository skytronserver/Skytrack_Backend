import ssl
import paho.mqtt.client as mqtt

# Define the endpoint (IP/URL and port)
BROKER_URL = "216.10.244.243"
BROKER_PORT = 8883

# Define the paths to the certificates
ROOT_CA = "/etc/mosquitto/ca_certificates/ca.crt"
CLIENT_CERT = "/etc/mosquitto/certs/client.crt"
CLIENT_KEY = "/etc/mosquitto/certs/client.key"

# Create a new MQTT client instance
client = mqtt.Client()

# Create SSL context with disabled hostname verification
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.check_hostname = False
context.load_verify_locations(cafile=ROOT_CA)
context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)

# Set the SSL context
client.tls_set_context(context)

# Connect to the broker
client.connect(BROKER_URL, BROKER_PORT, 60)

# Blocking call that processes network traffic, dispatches callbacks, and handles reconnecting.
client.loop_forever()
