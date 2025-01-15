import socket
import signal
import sys
def compute_simple_checksum(data):
    return sum(data) % 256
def start_server(ip_address="0.0.0.0", port=2121):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Set SO_REUSEADDR to reuse the port immediately after the program terminates
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((ip_address, port))
    server_socket.listen(5)
    print(f"Server started at {ip_address}:{port}")
    # Handle graceful shutdown
    def handle_exit(sig, frame):
        print("\nShutting down server...")
        server_socket.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)  # Handle Ctrl+C
    signal.signal(signal.SIGTERM, handle_exit)  # Handle termination signals
    while True:
        try:
            client_socket, client_address = server_socket.accept()
            print(f"Connection received from {client_address}")
            # Process the client's request
            request = client_socket.recv(1024).decode()

            if request.strip() == "getfile":
                print("Received 'getfile' request, sending file...")

                total_bytes = 0
                loop_count = 0
                with open("/var/www/html/skytron_backend/Skytronsystem/FOTAFiles/oldnew.pack", "rb") as file:
                    while (chunk := file.read(128)):
                        client_socket.sendall(chunk)
                        loop_count += 1
                        bytes_received = len(chunk)
                        total_bytes += bytes_received
                        checksum = compute_simple_checksum(chunk)
                        print(f"[Download Loop {loop_count}] Bytes Received: {bytes_received}, Total Bytes: {total_bytes}, Buffer Checksum: 0x{checksum:02X}")
                print("File sent successfully.")
            else:
                print(f"Unexpected request: {request}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()

# Run the server
if __name__ == "__main__":
    start_server(port=2121)
