import socket,re
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from skytron_api.models import GPSData, GPSDataLog ,DeviceTag, DeviceStock,Route,AlertsLog
from skytron_api.models import gpsdata_populate_location_and_consecutive_time
from geopy.distance import geodesic
import json
import threading
from datetime import datetime, timezone
import pytz

# Import common data processor (same as MQTT) - handles both PVT and legacy formats
from skytron_api.data_processor import process_gps_data, extract_log_meta
from skytron_api import connection_registry

# Timezone setup
gmt_timezone = pytz.timezone('GMT')
ist_timezone = pytz.timezone('Asia/Kolkata')

# Live socket registry: imei -> connected socket, so the command dispatcher
# thread (running in this same process) can find a live connection to
# sendall() a queued command onto.
LIVE_SOCKETS = {}
LIVE_SOCKETS_LOCK = threading.Lock()

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
    # Close old database connections before processing alerts
    close_old_connections()
    
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
        
    print("rouutes found",len(routes),flush=True)
    for route in routes:
        print("rouutes found")
        r = route.route  # This is the route string containing coordinates
        points = json.loads(r)  # Convert route string into a list of points
        status = "out"  # Default status

        # Check if any point in the route is within 100 meters of the given lat/lon
        for point in points[0:-1]:
            route_lon,route_lat,  _ = point
            print(point)
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
    seen_imeis = set()

    def _on_imei_seen(seen_imei):
        with LIVE_SOCKETS_LOCK:
            LIVE_SOCKETS[seen_imei] = conn
        seen_imeis.add(seen_imei)
        connection_registry.record_tcp_connect(seen_imei, client_address[0], client_address[1], "tcp")

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
                # Close old database connections to prevent leaks
                close_old_connections()
                
                data_str = data.decode('utf-8')

                try:
                    log_imei, log_network = extract_log_meta(data_str)
                    GPSDataLog.objects.create(raw_data=data_str, source_ip=client_address[0],
                                              imei=log_imei, network_name=log_network)
                except Exception as e:
                    print("Data processing error log:", e, flush=True)

                
                data_l = data_str.split('$')
                for dat in data_l:
                    try:
                        # Process GPS data using common processor
                        # Supports both formats:
                        # - New PVT: $,PVT,HPSP,1.0.0,NR,01,L,860269065286924,DL01AB1234,...
                        # - Legacy: $,T,ATMV,1.1.4,BH,05,L,861850060252547,ABC00000012,...
                        dat = '$' + dat
                        if len(dat) > 4:
                            gps_data = process_gps_data(dat)
                            
                            if gps_data:

                                reg=gps_data['imei']
                                _on_imei_seen(reg)
                                dev=DeviceStock.objects.filter(imei__contains=str(reg)).last()
                                print("#"+reg+"#",dev)
                                if dev: 
                                    device_tag=DeviceTag.objects.filter(device=dev).last()#,status='Device_Active'
                                     

                                    if device_tag:
                                        gps_data['device_tag']=device_tag
                                        gps_data.pop('imei', None)
                                        gps_data.pop('vehicle_registration_number', None)
                                        gps_data['source_ip']=client_address[0]

                                        g=GPSData.objects.create(**gps_data)
                                        g.save()
                                        try:
                                            gpsdata_populate_location_and_consecutive_time(
                                                sender=GPSData,
                                                instance=g,
                                                created=True,
                                            )
                                            g.refresh_from_db(fields=[
                                                'state', 'district', 'city', 'road', 'road_type',
                                                'time_in_same_state', 'time_in_same_district', 'time_in_same_city'
                                            ])
                                        except Exception as enrich_error:
                                            print(f"GPS enrichment error: {enrich_error}", flush=True)
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
        with LIVE_SOCKETS_LOCK:
            for seen_imei in seen_imeis:
                if LIVE_SOCKETS.get(seen_imei) is conn:
                    del LIVE_SOCKETS[seen_imei]
        for seen_imei in seen_imeis:
            connection_registry.record_tcp_disconnect(seen_imei, "tcp")
        # Close any remaining database connections
        close_old_connections()
        conn.close()
        print(f"Connection from {client_address} closed.", flush=True)



def _tcp_command_dispatcher():
    """Background loop (runs in this process, alongside the accept loop):
    pop queued commands for the GPS TCP transport and sendall() them onto
    whichever live socket in LIVE_SOCKETS matches the target IMEI."""
    while True:
        item = connection_registry.pop_command_for_dispatch("tcp", timeout=1)
        if not item:
            continue

        request_id = item.get("request_id")
        imei = item.get("imei")

        if connection_registry.is_command_stale(item):
            connection_registry.push_command_ack(
                request_id, "error", error="Command was stale (issued too long ago)"
            )
            continue

        with LIVE_SOCKETS_LOCK:
            sock = LIVE_SOCKETS.get(imei)

        if not sock:
            connection_registry.push_command_ack(
                request_id, "error", error=f"No live socket for IMEI {imei}"
            )
            continue

        try:
            payload = item.get("payload", "")
            encoded = payload.encode(item.get("encoding") or "utf-8") if isinstance(payload, str) else payload
            sock.sendall(encoded)
            connection_registry.push_command_ack(request_id, "sent", bytes_sent=len(encoded))
        except Exception as e:
            connection_registry.push_command_ack(request_id, "error", error=str(e))


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        host = '0.0.0.0'
        port = 6000

        dispatcher_thread = threading.Thread(target=_tcp_command_dispatcher, daemon=True)
        dispatcher_thread.start()

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
    
