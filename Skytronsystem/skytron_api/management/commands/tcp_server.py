import socket,re
from django.core.management.base import BaseCommand
from skytron_api.models import GPSData, GPSDataLog ,DeviceTag, DeviceStock,Route,AlertsLog
from geopy.distance import geodesic
import json
import threading
'''
def handle_client(conn, client_address):
    print(f"Accepted connection from {client_address}", flush=True)
    try:
        with conn:
            conn.settimeout(180)
            while True:
                # Set timeout for 3 minutes (180 seconds)
                

                data = conn.recv(1024)
                 
                if data:
                    data_str = data.decode('utf-8')
                    try:
                        GPSDataLog.objects.create(raw_data=data_str)
                    except Exception as e:
                        print("data processign error log: ",e, flush=True)
                    data_l = data_str.split('$')
                    for dat in data_l:
                        try:
                            dat='$'+dat
                            if len(dat)>4:
                                gps_data = process_gps_data(dat)
                                GPSData.objects.create(**gps_data)
                        except Exception as e:
                            print("data processign error main: ",e, flush=True) 
                            
                            
                    conn.settimeout(None)
                    conn.settimeout(180)

    except socket.timeout:
        print(f"Client {client_address} timed out. Closing the connection.", flush=True)
        conn.close()
    except Exception as e:
        print(f"Error handling client {client_address}: {e}", flush=True)
        conn.close()
    finally:
        conn.close()
        print(f"Connection closed  ", flush=True)
 
with conn:
        while True:
            try:
                data = conn.recv(1024)
                
                    #print(data_str, flush=True)
            except Exception as e:
                print(e, flush=True)
                break
    try:
        conn.close()
        print(f"Connection with {client_address} closed", flush=True)
    except Exception as e:
                print(e, flush=True)
 
    
class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        host = '0.0.0.0'
        port = 6000

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((host, port))
            server_socket.listen(1000)

            print(f"TCP Socket Server listening on {host}:{port}", flush=True)

            while True:
                try:
                    conn, addr = server_socket.accept()
                    client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                    client_thread.start()
                    
                except Exception as e:
                    print("ErroStart1:",e, flush=True)
'''


from django.db.models import Max
def createAleart(t,s,locid,devicetag):
            AlertsLog.objects.create(
                type=t,
                status=s,
                timestamp=datetime.now(),
                gps_ref_id=locid, 
                deviceTag=devicetag,
                #district=devicetag.device.dealer.district,
                state=devicetag.device.dealer.manufacturer.state
            )
def process_alert(gps_data, locid):
    devicetag = gps_data['device_tag']
    packet_type = gps_data['packet_type']
    alert_id = gps_data['alert_id']
    lat = gps_data['latitude']
    lon = gps_data['longitude']

    # Fetch active routes associated with the device
    routes = Route.objects.filter(status='Active', device=devicetag.device)
    route_status = []

    last_alerts = (
        AlertsLog.objects.filter(deviceTag=devicetag)
        .exclude(type="Route")
        .values('type')  # Group by type
        .annotate(latest_timestamp=Max('timestamp'))  # Get the latest timestamp for each type
    )

    # Fetch the full objects corresponding to the latest alerts
    lastnormal_alerts = AlertsLog.objects.filter(
        deviceTag=devicetag,
        type__in=[entry['type'] for entry in last_alerts],
        timestamp__in=[entry['latest_timestamp'] for entry in last_alerts]
    )


    if gps_data["packet_type"]=="EA":#('Em', 'Em'),
        t= "Em"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        if al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if gps_data["ignition_status"]=="1":
        t="Eng"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)
    if gps_data["ignition_status"]=="0":
        t="Eng"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)


    if gps_data["speed"]>80:
        t="OverSpeed"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if gps_data["speed"]<80:
        t="OverSpeed"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)
    
    if gps_data["internal_battery_voltage"]<3:
        t="LowIntBat"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if gps_data["internal_battery_voltage"]>3:
        t="LowIntBat"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)

    if gps_data["main_input_voltage"]<8:
        t="LowExtBat"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)

    
    if gps_data["main_input_voltage"]>9:
        t="LowExtBat"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)

        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)

    if gps_data["internal_battery_voltage"]<2:
        t="ExtBatDiscnt"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if gps_data["internal_battery_voltage"]>2:
        t="ExtBatDiscnt"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)



    if gps_data["box_tamper_alert"]=="C":
        t="BoxTemp"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if gps_data["box_tamper_alert"]=="O":
        t="BoxTemp"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)
 


    if alert_id=="15":
        t="EmTemp"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if alert_id=="16":
        t="EmTemp"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)
 

    if alert_id=="17":
        t="Tilt"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if alert_id=="18":
        t="Tilt"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)

    if alert_id=="19":
        t="HarshBreak"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if alert_id=="20":
        t="HarshBreak"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)

    if alert_id=="21":
        t="HarshTurn"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if alert_id=="22":
        t="HarshTurn"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)

    if alert_id=="23":
        t="HarshAccileration"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"in",locid,devicetag)
        elif al.status=="out":
            createAleart(t,"in",locid,devicetag)


    if alert_id=="24":
        t="HarshAccileration"
        al=lastnormal_alerts.filter(type=t).last()
        if not al:
            createAleart(t,"out",locid,devicetag)
        elif al.status=="in":
    
            createAleart(t,"out",locid,devicetag)


 

    

    # Fetch last alerts for the given device tag, grouped by unique (type, route_ref)
    last_alerts = AlertsLog.objects.filter(deviceTag=devicetag,type="Route").order_by('type', 'route_ref', '-timestamp')

    # Create a dictionary to store the last alert for each (type, route_ref) combination
    last_alert_map = {}
    for alert in last_alerts:
        key = (alert.type, alert.route_ref.id if alert.route_ref else None)
        if key not in last_alert_map:
            last_alert_map[key] = alert
        

    for route in routes:
        r = route.route  # This is the route string containing coordinates
        points = json.loads(r)  # Convert route string into a list of points
        status = "out"  # Default status

        # Check if any point in the route is within 100 meters of the given lat/lon
        for point in points:
            route_lat, route_lon, _ = point
            distance = geodesic((lat, lon), (route_lat, route_lon)).meters
            if distance <= 100:
                status = "in"
                break  # No need to check further if one point is within range

        # Prepare the route status
        rs = {"rid": route.id, "status": status, "gpsid": locid}
        route_status.append(rs)

        # Determine if a new alert needs to be created
        alert_key = ('Route', route.id)
        last_alert = last_alert_map.get(alert_key)

        if not last_alert or not last_alert.status:  # Case 1: No previous alert or status is null/blank
            AlertsLog.objects.create(
                type='Route',
                status=status,
                timestamp=datetime.now(),
                gps_ref_id=locid,
                route_ref=route,
                deviceTag=devicetag,
                #district=devicetag.device.dealer.district,
                state=devicetag.device.dealer.manufacturer.state
            )
        elif last_alert.status != status:  # Case 2: Status has changed
            AlertsLog.objects.create(
                type='Route',
                status=status,
                timestamp=datetime.now(),
                gps_ref_id=locid,
                route_ref=route,
                deviceTag=devicetag, 
                #district=devicetag.device.dealer.district,
                state=devicetag.device.dealer.manufacturer.state
            )






import time
def handle_client(conn, client_address):
    print(f"Accepted connection from {client_address}", flush=True)
    try:
        conn.settimeout(180)
        last_data_time=time.time()
        while True:
            data = conn.recv(1024)
            if not data:
                if time.time() - last_data_time > 600:
                        print(f"No data received from {client_address} for more than 10 minutes. Closing the connection.", flush=True)
                        break 

            

            if  data: 
                data_str = data.decode('utf-8')

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
                                print("#"+reg+"#",dev)
                                if dev: 
                                    device_tag=DeviceTag.objects.filter(device=dev).last()#,status='Device_Active'
                                     

                                    if device_tag:
                                        gps_data['device_tag']=device_tag
                                        gps_data.pop('imei', None)
                                        gps_data.pop('vehicle_registration_number', None)

                                        g=GPSData.objects.create(**gps_data)
                                        g.save()
                                        process_alert(gps_data,g.id)

                                        print("########################",flush=True)
                                        print(dat)
                                        print(gps_data)
                                #print(gps_data)
                            else:
                                print("Data format errot error:", dat, flush=True)
                    except Exception as e:
                        print("Data processing error main:", e, flush=True)
                        raise e

    except socket.timeout:
        print(f"Client {client_address} timed out. Closing the connection.", flush=True)
    except Exception as e:
        print(f"Error handling client {client_address}: {e}", flush=True)
        raise e
    finally:
        conn.close()
        print(f"Connection from {client_address} closed.", flush=True)



class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        host = '0.0.0.0'
        port = 6000

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(1000)

            print(f"TCP Socket Server listening on {host}:{port}", flush=True)

            while True:
                try:
                    conn, addr = server_socket.accept()
                    client_thread = threading.Thread(target=handle_client, args=(conn, addr))

                    client_thread.start()
                except Exception as e:
                    print("Error starting thread:", e, flush=True)
                    try:
                        conn.close()  # Close the connection if it's open
                    except:
                        pass


from datetime import datetime, timezone
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
        #print(len(groups))

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
    
