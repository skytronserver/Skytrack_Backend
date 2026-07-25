# gps_socket_server.py
import os
import socket
import django
#python3 manage.py tcp_server --traceback >logtcp.log &
#sudo python3 gps_socket_server.py > tcplog.log &
# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")
django.setup()

from skytron_api.models import User,EMGPSLocation,GPSemDataLog
from django.core.management import call_command
import socket
import threading
from django.db.models import Q
from skytron_api import connection_registry

# Live socket registry: imei -> connected socket, so the command dispatcher
# thread (running in this same process) can find a live connection to
# sendall() a queued command onto.
LIVE_SOCKETS = {}
LIVE_SOCKETS_LOCK = threading.Lock()

# Define the host and port you want to listen on
host = '0.0.0.0'  # Listen on all available network interfaces
port = 5001      # Use a port number of your choicecd ..

# Create a TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Bind the socket to the host and port
server_socket.bind((host, port))
# Start listening for incoming connections
server_socket.listen(1000)  # Listen for up to 5 incoming connections

print(f"Listening on {host}:{port}...")
def handle_gps_data(data_string):
    # Create GPSLocation object from the string data
    location = EMGPSLocation.create_from_string(data_string)
    location.save()

def processEM(str_data, on_imei_seen=None):
        try:
            GPSemDataLog.objects.create(raw_data=str_data)
        except Exception as e:
            print("Data processing error log:", e, flush=True)
        print("EM Data processing :", str_data, flush=True)
        print("EM Data processing :", str_data)

        data_l = str_data.split('$')
        for dat in data_l:
            dat='$'+dat
            if len(dat)>4:
                print("Data processing 32323 :", dat, flush=True)
                try:
                    data_list = dat.split(',')
                    if len(data_list)>10:
                        data_list=data_list[2:]
                        print(data_list)
                        if on_imei_seen is not None:
                            try:
                                on_imei_seen(data_list[1])
                            except Exception as e:
                                print(f"on_imei_seen callback error: {e}", flush=True)
                        location = EMGPSLocation.create_from_string(data_list)
                        if location is not None:
                            location.save() 
                        else:
                            print(f"Warning: No device tag found for IMEI {data_list[1]}, skipping save")
                except Exception as e :
                    print("error1 ",e)
                    #raise e
                
def start_socket_server():
    host = '0.0.0.0'
    port = 6000#5001  # Change to your desired port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        #server_socket.bind((host, port))
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1000)
        

        print(f"Socket server listening on {host}:{port}")

        while True:
            conn, addr = server_socket.accept()
            with conn:
                print(f"Connected by {addr}")

                data = conn.recv(1024)
                if not data:
                    break

                data_string = data.decode('utf-8')
                print(f"Received data: {data_string}")

                # Handle the received GPS data
                #handle_gps_data(data_string)
# Function to handle client connections
def handle_client(client_socket, client_address):
    print(f"Accepted connection from {client_address}")
    seen_imeis = set()

    def _on_imei_seen(seen_imei):
        with LIVE_SOCKETS_LOCK:
            LIVE_SOCKETS[seen_imei] = client_socket
        seen_imeis.add(seen_imei)
        connection_registry.record_tcp_connect(seen_imei, client_address[0], client_address[1], "tcpem")

    inp="$,EPB,EMR,868960065504918,NM,29092024,142315,A,26.134428,N,91.803711,E,61.1,0.0,143.8,G,GEM1205-04-00,0000000000,49,*"
    # $EPB,SEM,861850060252315,NM,30092024132916,A,28.456324,N,77.032673,E,220,0,G,00,ABC00000006,9655543732,2A,*::::
    try:
        while True:
            data = client_socket.recv(1024)  # Receive up to 1024 bytes of data
            if not data:
                break  # No more data to receive, exit the loop
            str_data=data.decode('utf-8')
            print(f"Received data from {client_address}: {str_data}:::: ")
            RegNo=""
            processEM(str_data, on_imei_seen=_on_imei_seen)
            """if len(RegNo)>2:

                existing_emergency_call = EmergencyCall.objects.filter(Q(vehicle_no=RegNo)).order_by('-start_time').last()
                if existing_emergency_call:
                    if existing_emergency_call.status=='Closed':
                        data = {'vehicle_no': existing_emergency_call.vehicle_no,'device_imei': existing_emergency_call.device_imei,'call_id': existing_emergency_call.call_id,}
                        d="CloseEM"+existing_emergency_call.vehicle_no
                        client_socket.sendall(d.encode('utf-8'))"""
    finally:
        with LIVE_SOCKETS_LOCK:
            for seen_imei in seen_imeis:
                if LIVE_SOCKETS.get(seen_imei) is client_socket:
                    del LIVE_SOCKETS[seen_imei]
        for seen_imei in seen_imeis:
            connection_registry.record_tcp_disconnect(seen_imei, "tcpem")
        client_socket.close()
        print(f"Connection with {client_address} closed")
def _em_command_dispatcher():
    """Background loop (runs in this process, alongside the accept loop):
    pop queued commands for the EM TCP transport and sendall() them onto
    whichever live socket in LIVE_SOCKETS matches the target IMEI."""
    while True:
        item = connection_registry.pop_command_for_dispatch("tcpem", timeout=1)
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


if __name__ == "__main__":
    # Run Django setup to make models available
    #call_command('runserver', '0.0.0.0:5001')
    #start_socket_server()
    dispatcher_thread = threading.Thread(target=_em_command_dispatcher, daemon=True)
    dispatcher_thread.start()

    while True:
        client_socket, client_address = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()
 