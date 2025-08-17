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
    
    # Create the firmware file if it doesn't exist (for testing)
    firmware_file = os.path.join(firmware_dir, "1.1.1.pack")
    if not os.path.exists(firmware_file):
        with open(firmware_file, 'wb') as f:
            f.write(b"Dummy firmware content for testing")
        print(f"Created dummy firmware file: {firmware_file}")
    
    # Create authorizer and add user
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", ".", perm="elradfmwMT")
    
    # Create handler
    handler = FTPHandler
    handler.authorizer = authorizer
    
    # Optional: Set banner message
    handler.banner = "Firmware FTP Server Ready"
    
    # Create FTP server
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