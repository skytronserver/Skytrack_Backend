#!/usr/bin/env python3
"""
Quectel FOTA FTP Server - Optimized for embedded devices
"""
import os
import logging
import shutil
import time
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

class QuectelFTPHandler(FTPHandler):
    # Increase timeout for slow embedded devices
    timeout = 300  # 5 minutes
    
    def on_connect(self):
        print(f"[CONNECT] {self.remote_ip}:{self.remote_port} connected")
        print(f"[INFO] Set timeout to {self.timeout} seconds for embedded device")
    
    def on_disconnect(self):
        print(f"[DISCONNECT] {self.remote_ip}:{self.remote_port} disconnected")
    
    def on_login(self, username):
        print(f"[LOGIN] User '{username}' logged in from {self.remote_ip}")
        print(f"[INFO] Current directory: {self.fs.cwd}")
    
    def on_logout(self, username):
        print(f"[LOGOUT] User '{username}' logged out")
    
    def ftp_LIST(self, line):
        print(f"[LIST] Client requesting directory listing for: {line}")
        path = line or '.'
        print(f"[LIST] Resolved path: {self.fs.fs2ftp(self.fs.realpath(path))}")
        return super().ftp_LIST(line)
    
    def ftp_SIZE(self, line):
        print(f"[SIZE] Client requesting size for file: {line}")
        print(f"[SIZE] Current directory: {self.fs.cwd}")
        try:
            # Add small delay for embedded devices
            time.sleep(0.1)
            result = super().ftp_SIZE(line)
            print(f"[SIZE] SUCCESS - File {line} size returned")
            return result
        except Exception as e:
            print(f"[SIZE] ERROR - Could not get size for {line}: {e}")
            # Try to list directory to see what's available
            try:
                files = self.fs.listdir(self.fs.cwd)
                print(f"[SIZE] Available files in current directory: {files}")
            except:
                pass
            raise
    
    def ftp_RETR(self, line):
        print(f"[RETR] Client requesting download of file: {line}")
        print(f"[RETR] Current directory: {self.fs.cwd}")
        try:
            result = super().ftp_RETR(line)
            print(f"[RETR] SUCCESS - Started download of {line}")
            return result
        except Exception as e:
            print(f"[RETR] ERROR - Could not download {line}: {e}")
            raise
    
    def ftp_CWD(self, line):
        print(f"[CWD] Client changing directory to: {line}")
        try:
            result = super().ftp_CWD(line)
            print(f"[CWD] SUCCESS - Current working directory is now: {self.fs.cwd}")
            # List contents of new directory
            try:
                files = self.fs.listdir(self.fs.cwd)
                print(f"[CWD] Files in new directory: {files}")
            except:
                pass
            return result
        except Exception as e:
            print(f"[CWD] ERROR - Could not change to directory {line}: {e}")
            raise
    
    def ftp_PWD(self, line):
        print(f"[PWD] Client requesting current directory")
        result = super().ftp_PWD(line)
        print(f"[PWD] Current directory: {self.fs.cwd}")
        return result

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create FTP root structure
    ftp_root = "quectel_ftp"
    firmware_dir = os.path.join(ftp_root, "firmware")
    
    # Create directories if they don't exist (but don't delete existing files)
    if not os.path.exists(ftp_root):
        os.makedirs(ftp_root)
    if not os.path.exists(firmware_dir):
        os.makedirs(firmware_dir)
    
    # Copy firmware files to firmware subdirectory
    source_firmware_files = ["firmware/1.1.1.pack", "firmware/1.1.11.pack", "firmware/1.1.1.pac"]
    copied_files = []
    
    for source_file in source_firmware_files:
        if os.path.exists(source_file):
            dest_file = os.path.join(firmware_dir, os.path.basename(source_file))
            shutil.copy2(source_file, dest_file)
            file_size = os.path.getsize(dest_file)
            copied_files.append((os.path.basename(source_file), file_size))
            print(f"Copied {source_file} to {dest_file} ({file_size} bytes)")
    
    # List all files that are actually in the firmware directory
    print("\nScanning firmware directory for all files...")
    all_firmware_files = []
    if os.path.exists(firmware_dir):
        for filename in os.listdir(firmware_dir):
            file_path = os.path.join(firmware_dir, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                all_firmware_files.append((filename, file_size))
                print(f"Found: {filename} ({file_size} bytes)")
    
    # Create authorizer with permissive settings
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", ftp_root, perm="elr")  # read permissions only
    
    # Create handler optimized for Quectel
    handler = QuectelFTPHandler
    handler.authorizer = authorizer
    
    # Optimize for embedded devices
    handler.dtp_handler.timeout = 300  # 5 minutes for data connections
    handler.passive_ports = range(60000, 60020)  # Smaller range for better compatibility
    handler.banner = "Quectel FOTA Server Ready"
    handler.permit_foreign_addresses = True
    
    # Create FTP server
    server = FTPServer(("0.0.0.0", 4000), handler)
    
    print("=" * 50)
    print("QUECTEL FOTA FTP SERVER")
    print("=" * 50)
    print(f"Server: 0.0.0.0:4000")
    print(f"Username: test")
    print(f"Password: test")
    print(f"Root directory: {os.path.abspath(ftp_root)}")
    print(f"Firmware directory: {os.path.abspath(firmware_dir)}")
    print("\nAvailable firmware files:")
    for filename, size in all_firmware_files:
        print(f"  /firmware/{filename} ({size:,} bytes)")
    print(f"\nPassive ports: 60000-60019")
    print(f"Timeout: 300 seconds")
    print("\nServer ready for Quectel FOTA download")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down FOTA server...")
        server.close_all()

if __name__ == "__main__":
    main()
