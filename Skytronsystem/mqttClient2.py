import os
import ssl
import json
import django
import paho.mqtt.client as mqtt
from django.utils import timezone

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")
django.setup()


from skytron_api.models import EMUserLocation, EMCallAssignment, EMCallMessages
from skytron_api.views import get_user_object
from django.contrib.auth.models import User
from skytron_api.authentication import CustomTokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from skytron_api.serializers import EMCallMessagesSerializer

# MQTT Settings
BROKER_URL = "216.10.244.243"
BROKER_PORT = 8883  # Use SSL/TLS port
TOPIC = "field_ex/location_update"

# Paths to certificates
ROOT_CA = "/etc/mosquitto/ca_certificates/ca.crt"
CLIENT_CERT = "/etc/mosquitto/certs/client.crt"
CLIENT_KEY = "/etc/mosquitto/certs/client.key"

authenticator = CustomTokenAuthentication()

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
        data = json.loads(msg.payload.decode())
        token = data.get("token")

        # Authenticate the token using TokenAuthentication
        try:
            # We need a request-like object to pass into the authenticate method
            class FakeRequest:
                def __init__(self, token):
                    self.META = {'Authorization': f'{token}'}
            
            fake_request = FakeRequest(token)
            user_auth_tuple = authenticator.authenticate(fake_request)

            if user_auth_tuple is None:
                raise AuthenticationFailed("Invalid token.")

            user = user_auth_tuple[0]  # Extract the user from the authentication tuple
        except AuthenticationFailed as e:
            error_message = f"Authentication error: {str(e)}"
            print(error_message)
            client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))
            client.disconnect()
            return

        # Get user object and validate roles
        role = "sosexecutive"
        uo = get_user_object(user, role)

        if not uo:
            error_message = f"Request must be from {role}."
            print(error_message)
            client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))
            return

        # Check the type of action (location update or message send/receive)
        action = data.get("action")

        if action == "location_update":
            # Handle location update
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
                client.publish(TOPIC, json.dumps({"status": "success", "message": success_message}))
            else:
                error_message = "Location not updated. Value error."
                print(error_message)
                client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))

        elif action == "send_message":
            # Handle message sending
            assignment_id = data.get("assignment_id")
            message_text = data.get("message")

            assignment = EMCallAssignment.objects.filter(id=assignment_id, ex=uo).exclude(status__in=["rejected", "closed_false_allert", "closed"]).last()

            if not assignment:
                error_message = "Assignment not found or invalid."
                print(error_message)
                client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))
                #return

            call = assignment.call
            ob = EMCallMessages.objects.create(assignment=assignment, call=call, message=message_text)

            if ob:
                user.last_activity = timezone.now()
                user.login = True
                user.save()
                success_message = f"Message sent successfully: {ob.id}"
                print(success_message)
                client.publish(TOPIC, json.dumps({"status": "success", "message": success_message, "data": EMCallMessagesSerializer(ob, many=False).data}))
            else:
                error_message = "Unable to send message. Value error."
                print(error_message)
                client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))

        elif action == "retrieve_messages":
            # Handle message retrieval
            assignment_id = data.get("assignment_id")

            assignment = EMCallAssignment.objects.filter(id=assignment_id, ex=uo).exclude(status__in=["rejected", "closed_false_allert", "closed"]).last()

            if not assignment:
                error_message = "Assignment not found or invalid."
                print(error_message)
                client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))
                #return

            call = assignment.call
            messages = EMCallMessages.objects.filter(assignment=assignment, call=call).all()

            if messages:
                user.last_activity = timezone.now()
                user.login = True
                user.save()
                success_message = "Messages retrieved successfully."
                print(success_message)
                client.publish(TOPIC, json.dumps({"status": "success", "message": success_message, "data": EMCallMessagesSerializer(messages, many=True).data}))
            else:
                error_message = "No messages found for this call."
                print(error_message)
                client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))

    except Exception as e:
        error_message = f"Error processing message: {str(e)}"
        print(error_message)
        client.publish(TOPIC, json.dumps({"status": "error", "message": error_message}))


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
