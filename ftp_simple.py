#!/usr/bin/env python3
"""
Simple FTP Server for Quectel FOTA - files in root directory
"""
import os
import logging
import shutil
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

class SimpleFTPHandler(FTPHandler):
    def on_connect(self):
        print(f"[CONNECT] {self.remote_ip}:{self.remote_port} connected")
    
    def on_disconnect(self):
        print(f"[DISCONNECT] {self.remote_ip}:{self.remote_port} disconnected")
    
    def on_login(self, username):
        print(f"[LOGIN] User '{username}' logged in from {self.remote_ip}")
    
    def on_logout(self, username):
        print(f"[LOGOUT] User '{username}' logged out")
    
    def ftp_LIST(self, path):
        print(f"[LIST] Client requesting directory listing for: {path}")
        return super().ftp_LIST(path)
    
    def ftp_SIZE(self, path):
        print(f"[SIZE] Client requesting size for file: {path}")
        try:
            result = super().ftp_SIZE(path)
            print(f"[SIZE] Returned size for {path}: SUCCESS")
            return result
        except Exception as e:
            print(f"[SIZE] Error getting size for {path}: {e}")
            raise
    
    def ftp_RETR(self, path):
        print(f"[RETR] Client requesting download of file: {path}")
        try:
            result = super().ftp_RETR(path)
            print(f"[RETR] Started download of {path}")
            return result
        except Exception as e:
            print(f"[RETR] Error downloading {path}: {e}")
            raise
    
    def ftp_CWD(self, path):
        print(f"[CWD] Client changing directory to: {path}")
        result = super().ftp_CWD(path)
        print(f"[CWD] Current working directory is now: {self.fs.cwd}")
        return result

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create a temporary directory for firmware files
    ftp_root = "ftp_root"
    if not os.path.exists(ftp_root):
        os.makedirs(ftp_root)
    
    # Create firmware subdirectory to match Quectel expectations
    firmware_dir = os.path.join(ftp_root, "firmware")
    if not os.path.exists(firmware_dir):
        os.makedirs(firmware_dir)
    
    # Copy firmware files to both root and firmware subdirectory
    firmware_files = ["firmware/1.1.1.pack", "firmware/1.1.11.pack"]
    for firmware_file in firmware_files:
        if os.path.exists(firmware_file):
            # Copy to root directory
            root_dest = os.path.join(ftp_root, os.path.basename(firmware_file))
            shutil.copy2(firmware_file, root_dest)
            print(f"Copied {firmware_file} to {root_dest}")
            
            # Copy to firmware subdirectory (this is what Quectel expects)
            firmware_dest = os.path.join(firmware_dir, os.path.basename(firmware_file))
            shutil.copy2(firmware_file, firmware_dest)
            print(f"Copied {firmware_file} to {firmware_dest}")
            print(f"File size: {os.path.getsize(firmware_dest)} bytes")
    
    # Create authorizer and add user
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", ftp_root, perm="elr")  # Only read permissions
    
    # Create handler with custom logging
    handler = SimpleFTPHandler
    handler.authorizer = authorizer
    
    # Configure passive mode ports (important for NAT/firewall environments)
    handler.passive_ports = range(60000, 60100)
    
    # Set banner message
    handler.banner = "Quectel FOTA FTP Server Ready"
    
    # Enable debugging
    handler.permit_foreign_addresses = True
    
    # Create FTP server
    server = FTPServer(("0.0.0.0", 4000), handler)
    
    print("Starting Quectel FOTA FTP server on port 4000...")
    print("Username: test")
    print("Password: test")
    print(f"FTP root directory: {os.path.abspath(ftp_root)}")
    print("Available firmware files:")
    
    # List files in root directory
    for file in os.listdir(ftp_root):
        file_path = os.path.join(ftp_root, file)
        if os.path.isfile(file_path):
            print(f"  Root: {file} ({os.path.getsize(file_path)} bytes)")
    
    # List files in firmware subdirectory
    firmware_subdir = os.path.join(ftp_root, "firmware")
    if os.path.exists(firmware_subdir):
        for file in os.listdir(firmware_subdir):
            file_path = os.path.join(firmware_subdir, file)
            if os.path.isfile(file_path):
                print(f"  /firmware/{file} ({os.path.getsize(file_path)} bytes)")
    
    print("Passive ports: 60000-60099")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down FTP server...")
        server.close_all()

if __name__ == "__main__":
    main()
