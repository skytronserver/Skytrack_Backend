#!/usr/bin/env python3
"""
Ultra-simple FTP Server for Quectel FOTA - minimal implementation
"""
import os
import shutil
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def main():
    # Create FTP root structure
    ftp_root = "simple_ftp"
    firmware_dir = os.path.join(ftp_root, "firmware")
    
    # Create directories
    if not os.path.exists(ftp_root):
        os.makedirs(ftp_root)
    if not os.path.exists(firmware_dir):
        os.makedirs(firmware_dir)
    
    # Copy all firmware files
    source_files = ["firmware/1.1.1.pack", "firmware/1.1.11.pack", "firmware/1.1.1.pac"]
    for source_file in source_files:
        if os.path.exists(source_file):
            dest_file = os.path.join(firmware_dir, os.path.basename(source_file))
            if not os.path.exists(dest_file):
                shutil.copy2(source_file, dest_file)
                print(f"Copied: {os.path.basename(source_file)}")
    
    # List available files
    print("\nFirmware files available:")
    for filename in os.listdir(firmware_dir):
        file_path = os.path.join(firmware_dir, filename)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            print(f"  /firmware/{filename} ({size:,} bytes)")
    
    # Create simple authorizer
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", ftp_root, perm="elr")
    
    # Use basic FTP handler (no custom logging)
    handler = FTPHandler
    handler.authorizer = authorizer
    handler.banner = "Simple FOTA Server"
    
    # Create FTP server
    server = FTPServer(("0.0.0.0", 4000), handler)
    
    print(f"\nSimple FTP Server running on port 4000")
    print(f"Username: test, Password: test")
    print(f"Try your Quectel device now...")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.close_all()

if __name__ == "__main__":
    main()
