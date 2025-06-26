import ssl
import paho.mqtt.client as mqtt
import json
import django
import os
# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")
django.setup()

from django.utils import timezone
from skytron_api.models import EMUserLocation
from skytron_api.views import get_user_object
from django.contrib.auth.models import User

from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

# MQTT Settings
BROKER_URL ="216.10.244.243"
BROKER_PORT = 8883  # Use SSL/TLS port
TOPIC = "field_ex/location_update"

# Paths to certificates
ROOT_CA = "/etc/mosquitto/ca_certificates/ca.crt"
CLIENT_CERT = "/etc/mosquitto/certs/client.crt"
CLIENT_KEY = "/etc/mosquitto/certs/client.key"

authenticator = TokenAuthentication()
# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully")
        # Subscribe to the topic after connection
        client.subscribe(TOPIC)
        print(f"Subscribed to topic: {TOPIC}")
    else:
        print(f"Connection failed with code {rc}")
def on_message(client, userdata, msg):
    try:
        # Parse incoming message
        print(msg)
        data = json.loads(msg.payload.decode())
        print(data)
        token = "Token "+data.get("token")

        # Authenticate the token using TokenAuthentication
        try:
            # We need a request-like object to pass into the authenticate method
            class FakeRequest:
                def __init__(self, token):
                    self.META = {'HTTP_AUTHORIZATION': f'{token}'}
                    print(f"Authorization Header: Token {token}")
            
            fake_request = FakeRequest(token)
            user_auth_tuple = authenticator.authenticate(fake_request)

            if user_auth_tuple is None:
                raise AuthenticationFailed("Invalid token.")

            user = user_auth_tuple[0]  # Extract the user from the authentication tuple
        except AuthenticationFailed as e:
            error_message = f"Authentication error: {str(e)}"
            print(error_message)
            client.publish("field_ex/location_update_response", json.dumps({"status": "error", "message": error_message}))
            return

        # Get user object and validate roles
        role = "sosexecutive"
        uo = get_user_object(user, role)

        if not uo:
            error_message = f"Request must be from {role}"
            print(error_message)
            client.publish("field_ex/location_update_response", json.dumps({"status": "error", "message": error_message}))
            return
        
        # Optional role validation for specific user types
        # Uncomment if needed
        # if not (uo.user_type == 'police_ex' or uo.user_type == 'ambulance_ex'):
        #     error_message = "Request must be from police_ex or ambulance_ex."
        #     print(error_message)
        #     client.publish("field_ex/location_update_response", json.dumps({"status": "error", "message": error_message}))
        #     return

        # Create EMUserLocation object
        em_lat = float(data.get("em_lat"))
        em_lon = float(data.get("em_lon"))
        speed = float(data.get("speed"))

        ob = EMUserLocation.objects.create(field_ex=uo, em_lat=em_lat, em_lon=em_lon, speed=speed)
        if ob:
            user.last_activity = timezone.now()
            user.login = True
            user.save()
            success_message = f"Location updated successfully: {ob.id}"
            print(success_message)
            client.publish("field_ex/location_update_response", json.dumps({"status": "success", "message": success_message}))
        else:
            error_message = "Location not updated. Value error."
            print(error_message)
            client.publish("field_ex/location_update_response", json.dumps({"status": "error", "message": error_message}))

    except Exception as e:
        error_message = f"Error processing message: {str(e)}"
        print(error_message)
        client.publish("field_ex/location_update_response", json.dumps({"status": "error", "message": error_message}))


client = mqtt.Client()

# Set up callbacks
client.on_connect = on_connect
client.on_message = on_message

# Create SSL context
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.check_hostname = False
context.load_verify_locations(cafile=ROOT_CA)
context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)

# Set the SSL context
client.tls_set_context(context)

# Connect to the broker
client.connect(BROKER_URL, BROKER_PORT, 60)

# Blocking loop to keep listening to messages
client.loop_forever()