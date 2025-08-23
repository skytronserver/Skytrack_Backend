#!/usr/bin/env python3
import os
import logging
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

class CustomFTPHandler(FTPHandler):
    def on_connect(self):
        print(f"[CONNECT] {self.remote_ip}:{self.remote_port} connected")
    
    def on_disconnect(self):
        print(f"[DISCONNECT] {self.remote_ip}:{self.remote_port} disconnected")
    
    def on_login(self, username):
        print(f"[LOGIN] User '{username}' logged in from {self.remote_ip}")
    
    def on_logout(self, username):
        print(f"[LOGOUT] User '{username}' logged out")
    
    def on_file_sent(self, file):
        print(f"[DOWNLOAD] File '{file}' sent to {self.remote_ip}")
    
    def on_file_received(self, file):
        print(f"[UPLOAD] File '{file}' received from {self.remote_ip}")
    
    def on_incomplete_file_sent(self, file):
        print(f"[PARTIAL] Incomplete transfer of '{file}' to {self.remote_ip}")
    
    def on_incomplete_file_received(self, file):
        print(f"[PARTIAL] Incomplete receive of '{file}' from {self.remote_ip}")
    
    def ftp_LIST(self, path):
        print(f"[LIST] Client requesting directory listing for: {path}")
        return super().ftp_LIST(path)
    
    def ftp_SIZE(self, path):
        print(f"[SIZE] Client requesting size for file: {path}")
        print(f"[SIZE] Current working directory: {self.fs.cwd}")
        print(f"[SIZE] Resolved file path: {self.fs.realpath(path)}")
        
        # Try different path variations to find the file
        possible_paths = [
            path,  # Original path
            os.path.basename(path),  # Just filename
            path.replace('/home/azureuser/Skytrack_Backend/', ''),  # Relative path
        ]
        
        for try_path in possible_paths:
            try:
                print(f"[SIZE] Trying path: {try_path}")
                result = super().ftp_SIZE(try_path)
                if result:
                    print(f"[SIZE] SUCCESS - Found file at {try_path}, size: {result}")
                    return result
                else:
                    print(f"[SIZE] No result for path: {try_path}")
            except Exception as e:
                print(f"[SIZE] Exception for path {try_path}: {e}")
                continue
        
        # If we get here, the file wasn't found
        print(f"[SIZE] FAILED - Could not find file using any path variation")
        
        # Let's check what files actually exist in the current directory
        try:
            cwd_files = os.listdir(self.fs.realpath('.'))
            print(f"[SIZE] Files in current directory: {cwd_files}")
            
            # Also check the firmware subdirectory specifically
            firmware_path = os.path.join(self.fs.realpath('.'), 'firmware')
            if os.path.exists(firmware_path):
                firmware_files = os.listdir(firmware_path)
                print(f"[SIZE] Files in firmware subdirectory: {firmware_files}")
        except Exception as e:
            print(f"[SIZE] Could not list directories: {e}")
        
        # Return None to indicate file not found
        return None
    
    def ftp_RETR(self, path):
        print(f"[RETR] Client requesting download of file: {path}")
        return super().ftp_RETR(path)
    
    def ftp_CWD(self, path):
        print(f"[CWD] Client changing directory to: {path}")
        result = super().ftp_CWD(path)
        print(f"[CWD] Current working directory is now: {self.fs.cwd}")
        return result

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create the directory structure if it doesn't exist
    firmware_dir = "firmware"
    if not os.path.exists(firmware_dir):
        os.makedirs(firmware_dir)
    
    # Create the firmware file if it doesn't exist (for testing)
    firmware_file = os.path.join(firmware_dir, "1.1.1.pack")
    if not os.path.exists(firmware_file):
        with open(firmware_file, 'wb') as f:
            f.write(b"Dummy firmware content for testing")
        print(f"Created dummy firmware file: {firmware_file}")
    
    # Create authorizer and add user
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", ".", perm="elradfmwMT")
    
    # Create handler with custom logging
    handler = CustomFTPHandler
    handler.authorizer = authorizer
    
    # Configure passive mode ports (important for NAT/firewall environments)
    # Use a range of ports for passive mode
    handler.passive_ports = range(60000, 60100)
    
    # Optional: Set banner message
    handler.banner = "Firmware FTP Server Ready"
    
    # Enable debugging
    handler.permit_foreign_addresses = True
    
    # Create FTP server
    server = FTPServer(("0.0.0.0", 4000), handler)
    
    print("Starting FTP server on port 4000...")
    print("Username: test")
    print("Password: test")
    print(f"Firmware file available at: firmware/1.1.1.pack")
    print("Passive ports: 60000-60099")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down FTP server...")
        server.close_all()

if __name__ == "__main__":
    main()