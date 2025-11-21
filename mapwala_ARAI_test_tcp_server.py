import socket
import threading
from datetime import datetime

def handle_client(conn, addr):
    print(f"\n--- New connection established ---")
    print(f"Client IP: {addr[0]}, Port: {addr[1]}\n")
    stop_event = threading.Event()
    
    # Check for initial authentication string
    REQUIRED_SUBSTRING = "42240"    #Hamre"84747"        # mapwala1"287104"  # You can change this to your required substring
    try:
        initial_data = conn.recv(1024)
        print(f"\033[47m\033[30m{initial_data}\033[0m")
        if not initial_data or REQUIRED_SUBSTRING not in initial_data.decode():
            print(f"\033[47m\033[30mInitial authentication failed. Required substring not found.\033[0m")
            conn.close()
            return
        print(f"\033[47m\033[30mAuthentication successful!\033[0m")
    except Exception as e:
        print(f"\033[47m\033[30mError during authentication: {e}\033[0m")
        conn.close()
        return

    def receive():
        while not stop_event.is_set():
            try:
                data = conn.recv(1024)
                if not data:
                    print("Connection closed by client.")
                    stop_event.set()
                    break
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                #print(f"\033[47m\033[30m\nFrom Device {addr[0]} {timestamp}: {data.decode()}\033[1m")
                decoded_data = data.decode()
                if True :#"1.0.0,OT,12,L" in decoded_data:
                    if "49.50.117.155" in decoded_data and "PIP" in decoded_data:
                        # Replace the old IP with the new IP
                        modified_data = decoded_data.replace("135.235.166.209", "49.50.117.155")
                        print(f"\033[47m\033[30m\n{modified_data}\033[1m") 
                    else:
                        print(f"\033[47m\033[30m\n{decoded_data}\033[1m")
                
                
            except Exception as e:
                print(f"\033[47m\033[30mReceive error: {e}\033[1m")
                stop_event.set()
                break

    recv_thread = threading.Thread(target=receive, daemon=True)
    recv_thread.start()

    try:
        while not stop_event.is_set():
            msg = input()
            if msg.strip() == "":
                continue
            if msg.lower() == "exit":
                print("Closing connection.")
                stop_event.set()
                break
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            # Only print the formatted outgoing message, not the raw input
            print(f"\033[47m\033[30mFrom Server to {addr[0]} {timestamp}: {msg}\033[1m")
            try:
                conn.sendall(msg.encode())
            except Exception as e:
                print(f"Send error: {e}")
                stop_event.set()
                break
    except Exception as e:
        print(f"Send error: {e}")
    finally:
        conn.close()

def set_terminal_color():
    # Set entire terminal background to white and text to black
    print('\033[47m\033[30m\033[2J\033[H', end='')

def start_server(host='0.0.0.0', port=6000):
    set_terminal_color()  # Set terminal colors when server starts
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Add this line
        s.bind((host, port))
        s.listen(1)
        print(f"TCP server listening on {host}:{port}")
        while True:
            conn, addr = s.accept()
            handle_client(conn, addr)
            
            
if __name__ == "__main__":
    start_server()
