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

# MQTT Settings
BROKER_URL ="216.10.244.243"
BROKER_PORT = 8883  # Use SSL/TLS port
TOPIC = "field_ex/location_update"

# Paths to certificates
ROOT_CA = "/etc/mosquitto/ca_certificates/ca.crt"
CLIENT_CERT = "/etc/mosquitto/certs/client.crt"
CLIENT_KEY = "/etc/mosquitto/certs/client.key"



from datetime import datetime
import pytz
gmt_timezone = pytz.timezone('GMT')
ist_timezone = pytz.timezone('Asia/Kolkata')
def process_gps_data(data_str):    
    # Save the raw data to GPSDataLog model     
    try:
        # Define a regular expression pattern to match the format of the incoming string
        #pattern = re.compile(r'\$,T,(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),\*')
        groups=data_str.split(',') 
        #print(groups)
        print("length of data",len(groups))

        if len(groups)==52:
            if groups[0]=='$' and groups[1]=='T' and groups[-1]=='*' : 
                # Combine date and time strings and convert to a datetime object
                gmt_datetime_str = f'{groups[10]} {groups[11]}'
                gmt_datetime = datetime.strptime(gmt_datetime_str, '%d%m%Y %H%M%S')
                ist_datetime = gmt_timezone.localize(gmt_datetime).astimezone(ist_timezone)
                # Separate date and time components
                ist_date = ist_datetime.strftime('%d%m%Y')
                ist_time = ist_datetime.strftime('%H%M%S')

 
                #if groups[8]!='GEM1205-04-00':#868960065504918, 
                #    return None
                try:
                    if float(groups[12])<5 or float(groups[14])<5 :
                        return None
                    if float(groups[12])>180 or float(groups[14])>180 :
                        return None
                    if str(groups[13])!="N" or str(groups[15])!="E" :
                        return None
                except:
                    return None
                gps_data = {
                    #'start_character': groups[0],
                    #'header': groups[1],
                    #'vendor_id': groups[2],
                    #'firmware_version': groups[3],
                    'packet_type': groups[4],
                    'alert_id': groups[5],
                    'packet_status': groups[6],
                    'imei': groups[7],
                    'vehicle_registration_number': groups[8],
                    'gps_status': groups[9],
                    'date': ist_date,
                    'time': ist_time,
                    'latitude': float(groups[12]),
                    'latitude_dir': groups[13],
                    'longitude': float(groups[14]),
                    'longitude_dir': groups[15],
                    'speed': float(groups[16]),
                    'heading': float(groups[17]),
                    'satellites': int(groups[18]),
                    'altitude': int(float(groups[19])),
                    'pdop': float(groups[20]),
                    'hdop': float(groups[21]),
                    'network_operator': groups[22],
                    'ignition_status': groups[23],
                    'main_power_status': groups[24],
                    'main_input_voltage': float(groups[25]),
                    'internal_battery_voltage': float(groups[26]),
                    'emergency_status': groups[27],
                    'box_tamper_alert': groups[28],
                    'gsm_signal_strength': groups[29],
                    'mcc': groups[30],
                    'mnc': groups[31],
                    'lac': groups[32],
                    'cell_id': groups[33],
                    'nbr1_cell_id': groups[34],
                    'nbr1_lac': groups[35],
                    'nbr1_signal_strength': groups[36],
                    'nbr2_cell_id': groups[37],
                    'nbr2_lac': groups[38],
                    'nbr2_signal_strength': groups[39],
                    'nbr3_cell_id': groups[40],
                    'nbr3_lac': groups[41],
                    'nbr3_signal_strength': groups[42],
                    'nbr4_cell_id': groups[43],
                    'nbr4_lac': groups[44],
                    'nbr4_signal_strength': groups[45],
                    'digital_input_status': groups[46],
                    'digital_output_status': groups[47],
                    'frame_number': int(groups[48]),
                    'odometer': float(groups[49]),
                    #'checksum': groups[50],
                    #'end_char': groups[51],
                }
                #print(data_str)
                #print(gps_data)

                return gps_data
            else:
                return None
        else:
            return None
    except Exception as e:
        print("data processign error function ",e, flush=True)
        return None
    

authenticator = TokenAuthentication()
# Callback when the client connects to the broker
# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully") 
        client.subscribe("#") 
    else:
        print(f"Connection failed with code {rc}")

def Process_sosEx_Data(msg,topic_parts): 
    try:
        data = json.loads(msg.payload.decode())
        print(data)
        token=data.get("token")
        if token:
            token = "Token "+token

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
                client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": error_message}))
                return

            # Get user object and validate roles
            role = "sosexecutive"
            uo = get_user_object(user, role)

            if not uo:
                error_message = f"Request must be from {role}"
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": error_message}))
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
                except:
                    pass



        

                ee=EMCallBroadcast.objects.filter( type=uo.user_type,status="pending")
                dat={"status": "success", "broadcast":EMCallBroadcastSerializer(ee,many=True).data,"message": success_message}
                 
                
                client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps(dat))
            else:
                error_message = "Location not updated. Value error."
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": error_message}))
        
    except Exception as e:
            raise e
            print("data processign error function ",e, flush=True)


def Process_owner_Data(msg,topic_parts): 
    try:
        data = json.loads(msg.payload.decode())
        print(data)
        token=data.get("token")
        if token:
            token = "Token "+token
 
            try: 
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
                client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "error", "message": error_message}))
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
            try:
                alerts = AlertsLog.objects.filter(deviceTag__vvehicle_owner=uo)
                if alerts:
                    serializer = AlertsLogSerializer(alerts, many=True)
     
                    client.publish(topic_parts[0]+"/"+topic_parts[1], json.dumps({"status": "success", "alertHistory":serializer.data}))
                    return 0
            except:
                    pass



         
           
           
    except Exception as e:
            raise e
            print("data processign error function ",e, flush=True)

def Process_Device_Data(msg):
    print(msg.payload.decode())
    data_str=str(msg.payload.decode())
    try:
        try:
            GPSDataLog.objects.create(raw_data=data_str)
        except Exception as e:
            print("Data processing error log:", e, flush=True)
                
        data_l = data_str.split('$')
        for dat in data_l:
            try:
                #dat=",T,ATMV,1.1.4,BH,05,L,861850060252547,ABC00000012,0,25102024,023547,26.133602,N,91.804747,E,3,269,00,78,24.4,24.4,airtel,0,1,8.1,4.0,0,O,18,405,56,0092,F0A1,E364,0092,14,0F17,0092,18,0F17,0092,18,0,0,0,1100,00,000781,1162.0,E9,*"
                dat = '$' + dat
                if len(dat) > 4:
                    gps_data = process_gps_data(dat)
                            
                    if gps_data:
                        reg=gps_data['imei']
                        dev=DeviceStock.objects.filter(imei__contains=str(reg)).last()
                        if dev:
                            print("hhhh",reg)
                            device_tag=DeviceTag.objects.filter(device=dev).last()#,status='Device_Active'
                            if device_tag:
                                gps_data['device_tag']=device_tag
                                gps_data.pop('imei', None)
                                gps_data.pop('vehicle_registration_number', None)
                                g=GPSData.objects.create(**gps_data)
                                g.save()
            except Exception as e:
                        print("Data processing error main:", e, flush=True)
    except Exception as e:
            print("data processign error function ",e, flush=True)

def on_message(client, userdata, msg):
    try:
        # Split the topic to extract the user ID
        topic_parts = msg.topic.split('/')
        print(f"Message Topic: {topic_parts}")
        if len(topic_parts) == 2 and topic_parts[0] == 'gpsTracking':
            user_id = topic_parts[1]
            print(f"Message received for user ID: {user_id}")
            ###Process_Device_Data(msg)
        elif len(topic_parts) == 2 and topic_parts[0] == 'sosEx':
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
        raise e
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