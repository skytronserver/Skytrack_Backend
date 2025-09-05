import socket
import threading
from datetime import datetime

def handle_client(conn, addr):
    print(f"\n--- New connection established ---")
    print(f"Client IP: {addr[0]}, Port: {addr[1]}\n")
    stop_event = threading.Event()

    def receive():
        while not stop_event.is_set():
            try:
                data = conn.recv(1024)
                if not data:
                    print("Connection closed by client.")
                    stop_event.set()
                    break
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"\033[93m\nFrom Device {addr[0]} {timestamp}: {data.decode()}\033[0m")
            except Exception as e:
                print(f"Receive error: {e}")
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
            print(f"\033[92mFrom Server to {addr[0]} {timestamp}: {msg}\033[0m")
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

def start_server(host='0.0.0.0', port=6000):
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
