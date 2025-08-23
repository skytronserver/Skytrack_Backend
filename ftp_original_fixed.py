#!/usr/bin/env python3
import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def main():
    # Create the directory structure if it doesn't exist
    firmware_dir = "firmware"
    if not os.path.exists(firmware_dir):
        os.makedirs(firmware_dir)
    
    # Ensure the correct firmware file exists (your code expects .pack)
    expected_file = os.path.join(firmware_dir, "1.1.1.pack")
    source_files = ["firmware/1.1.1.pac", "firmware/1.1.1.pack"]
    
    for source_file in source_files:
        if os.path.exists(source_file) and not os.path.exists(expected_file):
            import shutil
            shutil.copy2(source_file, expected_file)
            print(f"Copied {source_file} to {expected_file}")
            break
    
    if not os.path.exists(expected_file):
        print(f"WARNING: Expected file {expected_file} not found!")
        print("Available files in firmware directory:")
        for f in os.listdir(firmware_dir):
            print(f"  - {f}")
    else:
        file_size = os.path.getsize(expected_file)
        print(f"✓ Firmware file ready: firmware/1.1.1.pack ({file_size:,} bytes)")
    
    # Create authorizer and add user - EXACTLY like original
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", ".", perm="elradfmwMT")
    
    # Create handler - use basic handler like original
    handler = FTPHandler
    handler.authorizer = authorizer
    
    # Optional: Set banner message
    handler.banner = "Firmware FTP Server Ready"
    
    # Create FTP server - EXACTLY like original
    server = FTPServer(("0.0.0.0", 4000), handler)
    
    print("Starting FTP server on port 4000...")
    print("Username: test")
    print("Password: test")
    print(f"Firmware file available at: firmware/1.1.1.pack")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down FTP server...")
        server.close_all()

if __name__ == "__main__":
    main()
