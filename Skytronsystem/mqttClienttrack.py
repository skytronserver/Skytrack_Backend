import ssl
import paho.mqtt.client as mqtt
import json
import django
import os

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")
django.setup()

import  re 
from skytron_api.models import * #EMCallAssignment, EMCallBroadcast, EMCallMessages, EMGPSLocation, GPSData, GPSDataLog ,DeviceTag, DeviceStock

from skytron_api.serializers import * #EMCallBroadcastSerializer, EMCallMessagesSerializer
import threading

from django.utils import timezone
from skytron_api.models import EMUserLocation
from skytron_api.views import get_user_object
from django.contrib.auth.models import User

from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

# Import JWT authentication for proper token handling
from skytron_api.jwt_authentication import HybridAuthentication

# Import our common data processor
from skytron_api.data_processor import process_device_tracking_data, process_emergency_data, get_device_response_data

# MQTT Settings - using environment variables for deployment flexibility
BROKER_URL = os.getenv("MQTT_BROKER_HOST", "10.192.136.179")  # Default fallback
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "8883"))  # Use SSL/TLS port
TOPIC = "field_ex/location_update"

# MQTT Authentication - using environment variables
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "6026969588")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h")

# Paths to certificates - Docker container path
# Use root CA certificate for proper chain of trust validation
ROOT_CA = "/app/keys/ca.crt"  # Root CA for certificate chain validation
#CLIENT_CERT = "/app/mqttKeys/client.crt"  # Optional: for mutual TLS
#CLIENT_KEY = "/app/mqttKeys/client.key"    # Optional: for mutual TLS
#mosquitto_sub -h '135.235.166.209' -p 8883 -t '#' --cafile /app/ca.crt --cert /app/client.crt --key /app/client.key -d











"""
import paho.mqtt.client as mqtt
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("#")  # Subscribe to all topics
def on_message(client, userdata, msg):
    print(f"{msg.topic} {msg.payload.decode()}")
client = mqtt.Client()
client.tls_set(ca_certs="/home/azureuser/Skytrack_Backend/Skytronsystem/ca.crt",
               certfile="/home/azureuser/Skytrack_Backend/Skytronsystem/client.crt",
               keyfile="/home/azureuser/Skytrack_Backend/Skytronsystem/client.key")
client.on_connect = on_connect
client.on_message = on_message
client.connect("135.235.166.209", 8883)
client.loop_forever()

"""








authenticator = HybridAuthentication()
# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully") 
        client.subscribe("#") 
    else:
        print(f"Connection failed with code {rc}")

def Process_sosEx_Data(msg,topic_parts): 
    try:
        # Print raw message for debugging
        raw_message = msg.payload.decode()
        print(f"Raw message received: {raw_message}")
        
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError as je:
            print(f"JSON Decode Error: {je}")
            print(f"Raw message that failed: '{raw_message}'")
            client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status": "error", "message": f"Invalid JSON format: {str(je)}"}))
            return
            
        print("Parsed data:", data)
        token=data.get("token")
        if token:
            # Use Token token format for JWT tokens
            auth_header = f"Bearer {token}"
            client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status": "update", "message": "user authentication in progress"}))

            # Authenticate the token using HybridAuthentication
            try:
                # We need a request-like object to pass into the authenticate method
                class FakeRequest:
                    def __init__(self, auth_header):
                        self.META = {'HTTP_AUTHORIZATION': auth_header}
                        self.data = {}  # Add empty data dict for compatibility
                        self.GET = {}   # Add empty GET dict for compatibility
                        print(f"Authorization Header: {auth_header}")
                
                fake_request = FakeRequest(auth_header)
                user_auth_tuple = authenticator.authenticate(fake_request)

                if user_auth_tuple is None:
                    #client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps3#({"status": "error1", "message": "Invalid token."}))
 
               
                    raise AuthenticationFailed("Invalid token.")
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status":"update", "message": "user found"}))
                user = user_auth_tuple[0]  # Extract the user from the authentication tuple
            except AuthenticationFailed as e:
                error_message = f"Authentication error: {str(e)}"
                print(error_message)
                #client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status": "error", "message": error_message}))
                #client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": error_message}))
                return

            # Get user object and validate roles
            role = "sosexecutive"
            uo = get_user_object(user, role)
            

            if not uo:
                error_message = f"Request must be from {role}"
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status": "error", "message": error_message}))
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
                try:
                    assignment_id =data.get("assignment_id")  
                    print(assignment_id)

                    assignment =EMCallAssignment.objects.filter(id=assignment_id,ex=uo,status__in=["accepted"]).last()
                    if not assignment and assignment_id!=None:
                        client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": "Invalid assignment id"}))
                        return 0
                    else:
                        deviceloc=list(EMGPSLocation.objects.filter(device_tag= assignment.call.device).order_by('-id')[:100].values())
        
                        ee=EMCallBroadcast.objects.filter( type=uo.user_type,call=assignment.call,status="accepted").last
             
                        msg=EMCallMessages.objects.filter(call=assignment.call).all()
        
                        client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "success", "locationHistory":deviceloc,"broadcast":EMCallBroadcastSerializer(ee,many=False).data,"groupMSG":EMCallMessagesSerializer(msg,many=True).data,"message": success_message}))
                        return 0
                except Exception as e:
                    client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message":"  "+str(e)}))
                     



        

                # Check for active broadcasts for this user type
                ee = EMCallBroadcast.objects.filter(type=uo.user_type, status="pending")
                print(f"Found {ee.count()} pending broadcasts for user type: {uo.user_type}")
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status": "update", "message": f"Found {ee.count()} pending broadcasts for user type: {uo.user_type}"}))
                if ee.exists():
                    dat = {"status": "success", "broadcast": EMCallBroadcastSerializer(ee, many=True).data, "message": success_message}
                    print(f"Sending broadcast response: {dat}")
                else:
                    # If no pending broadcasts, send success without broadcast data
                    dat = {"status": "success", "broadcast": [], "message": success_message}
                    print("No pending broadcasts found, sending empty broadcast array")
                
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps(dat))
            else:
                error_message = "Location not updated. Value error."
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status": "error", "message": error_message}))
        
        else:
 
            print("Invalid token in message payload")
            #client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error2", "message": "Invalid token."}))

               
    except Exception as e:
            client.publish(topic_parts[0]+"/"+topic_parts[1]+"", json.dumps({"status": "error", "message": "Something went wrong."}))
               
            raise e
            print("data processign error function ",e, flush=True)


def Process_owner_Data(msg,topic_parts): 
    try:
        data = json.loads(msg.payload.decode())
        print(data)
        token=data.get("token")
        
        if token:
            # Use Token token format for JWT tokens
            auth_header = f"Bearer {token}"
 
            try: 
                class FakeRequest:
                    def __init__(self, auth_header):
                        self.META = {'HTTP_AUTHORIZATION': auth_header}
                        self.data = {}  # Add empty data dict for compatibility
                        self.GET = {}   # Add empty GET dict for compatibility
                        print(f"Authorization Header: {auth_header}")
                
                fake_request = FakeRequest(auth_header)
                user_auth_tuple = authenticator.authenticate(fake_request)

                if user_auth_tuple is None:
                    raise AuthenticationFailed("Invalid token.")

                user = user_auth_tuple[0]  # Extract the user from the authentication tuple
            except AuthenticationFailed as e:
                error_message = f"Authentication error: {str(e)}"
                print(error_message)
                #client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": error_message}))
                return


            role = "owner"
            uo = get_user_object(user, role)

            if not uo:
                error_message = f"Request must be from {role}"
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": error_message}))
                return
            

            user.last_activity = timezone.now()
            user.login = True
            user.save() 
            print(user)
            try:
                alerts = AlertsLog.objects.filter(deviceTag__vehicle_owner=uo).order_by('-id')[:10]
                if alerts:
                    serializer = AlertsLogSerializer(alerts, many=True)
     
                    client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "success", "alertHistory":serializer.data}))
                    print("data sent")
                    return 0
            except Exception as e :
                    print(e)
            return 0



         
           
           
    except Exception as e:
            raise e
            print("data processign error function ",e, flush=True)

def Process_Device_Data(msg):
    """Process device tracking data using common processor and send response"""
    try:
        data_str = str(msg.payload.decode())
        print(f"[MQTT] Processing device tracking data: {data_str}", flush=True)
        
        # Process the GPS data
        process_device_tracking_data(data_str, source="MQTT")
        
        # Extract IMEI from the data for response
        imei = None
        try:
            # Parse the data to extract IMEI
            data_parts = data_str.split(',')
            if len(data_parts) > 7:
                # For PVT format: $,PVT,HPSP,1.0.0,NR,01,L,860269065242240,...
                imei = data_parts[7]  # IMEI is at index 7
                print(f"[MQTT] Extracted IMEI for response: {imei}", flush=True)
        except Exception as e:
            print(f"[MQTT] Error extracting IMEI: {e}", flush=True)
        
        # Send device response if IMEI was found
        if imei:
            try:
                # Get _
                response_data = get_device_response_data(imei)
                
                # Publish response to deviceResponse/<IMEI>
                response_topic = f"deviceResponse/{imei}"
                response_json = json.dumps(response_data)
                
                client.publish(response_topic, response_json)
                print(f"[MQTT] Sent response to {response_topic}: {response_json}", flush=True)
                
            except Exception as e:
                print(f"[MQTT] Error sending device response: {e}", flush=True)
                
    except Exception as e:
        print(f"[MQTT] Device data processing error: {e}", flush=True)


def Process_EM_Data(msg):
    """Process emergency data using common processor"""
    data_str = str(msg.payload.decode())
    print(f"[MQTT] Processing emergency data: {data_str}", flush=True)
    process_emergency_data(data_str, source="MQTT")

def on_message(client, userdata, msg):
    try:
        # Split the topic to extract the user ID
        topic_parts = msg.topic.split('/')
        print(f"Message Topic: {topic_parts}")
        if len(topic_parts) == 2 and topic_parts[0] == 'deviceTracking':
            user_id = topic_parts[1]
            print(f"Message received for user ID: {user_id}")
            print(f"Message received topic: {topic_parts[0]} {topic_parts[1]}")
            print(f"Message received payload: {msg.payload.decode()}")
            Process_Device_Data(msg)
        elif len(topic_parts) == 2 and topic_parts[0] == 'deviceEM':
            user_id = topic_parts[1]
            print(f"Message received for user ID: {user_id}")
            print(f"Message received topic: {topic_parts[0]} {topic_parts[1]}")
            print(f"Message received payload: {msg.payload.decode()}")
            Process_EM_Data(msg)
        elif len(topic_parts) == 2 and topic_parts[0] == 'sosEx':
            #print("message payload decode" ,msg.payload.decode())
            Process_sosEx_Data(msg,topic_parts)
        elif len(topic_parts) == 2 and topic_parts[0] == 'owner':
            Process_owner_Data(msg,topic_parts)

            
        else:
            print("Invalid topic format")
            print(topic_parts)
            return
        return

 
        data = json.loads(msg.payload.decode())
        print(data)
        token = "Bearer "+data.get("token")

                    # Authenticate the token using HybridAuthentication
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
        raise e
        error_message = f"Error processing message: {str(e)}"
        print(error_message)
        client.publish("field_ex/location_update_response", json.dumps({"status": "error", "message": error_message}))


client = mqtt.Client()

# Set username and password for authentication
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# ✅ SECURE: Set up SSL/TLS with proper certificate validation (security audit compliant)
# - Uses root CA for certificate chain validation
# - Requires valid server certificate (CERT_REQUIRED)
# - Enables hostname verification
# - No certificate validation bypass
client.tls_set(
    ca_certs=ROOT_CA,
    certfile=None,  # Client cert not required for this connection
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,  # ✅ Require valid certificate
    tls_version=ssl.PROTOCOL_TLSv1_2,  # Use TLS 1.2 or higher
    ciphers=None  # Use default secure ciphers
)

# Set up callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to the broker using hostname (must match certificate CN/SAN)
client.connect(BROKER_URL, BROKER_PORT, 60)
# Blocking loop to keep listening to messages
client.loop_forever()
