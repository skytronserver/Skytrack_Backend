import socket,re
from django.core.management.base import BaseCommand
from skytron_api.models import GPSData, GPSDataLog ,DeviceTag

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
                        dat = '$' + dat
                        if len(dat) > 4:
                            gps_data = process_gps_data(dat)
                            #print(gps_data)
                            if gps_data:
                                reg=gps_data['vehicle_registration_number']
                                device_tag=DeviceTag.objects.filter(vehicle_reg_no=reg,status='Device_Active').last()
                                if device_tag:
                                    gps_data['device_tag']=device_tag.id 
                                gps_data.pop('imei', None)
                                gps_data.pop('vehicle_registration_number', None)
                                g=GPSData.objects.create(**gps_data)
                                g.save()
                                #print(gps_data)
                            else:
                                print("Data format errot error:", dat, flush=True)
                    except Exception as e:
                        print("Data processing error main:", e, flush=True)
                        #raise e

    except socket.timeout:
        print(f"Client {client_address} timed out. Closing the connection.", flush=True)
    except Exception as e:
        print(f"Error handling client {client_address}: {e}", flush=True)
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

 

                gps_data = {
                    #'start_character': groups[0],
                    #'header': groups[1],
                    #'vendor_id': groups[2],
                    #'firmware_version': groups[3],
                    #'packet_type': groups[4],
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

                return gps_data
            else:
                return None
        else:
            return None
    except Exception as e:
        print("data processign error function ",e, flush=True)
        return None
    
