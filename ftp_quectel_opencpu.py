#!/usr/bin/env python3
"""
Quectel OpenCPU FOTA FTP Server - Specifically designed for ql_ftp_client
"""
import os
import shutil
import logging
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

class QuectelOpenCPUHandler(FTPHandler):
    # Quectel devices expect longer timeouts
    timeout = 600  # 10 minutes
    
    def __init__(self, conn, server, ioloop=None):
        super().__init__(conn, server, ioloop)
        # Optimize for Quectel OpenCPU FTP client
        self.use_sendfile = False  # Disable sendfile for better compatibility
    
    def on_connect(self):
        print(f"[QUECTEL] Device connected from {self.remote_ip}:{self.remote_port}")
    
    def on_disconnect(self):
        print(f"[QUECTEL] Device disconnected from {self.remote_ip}:{self.remote_port}")
    
    def on_login(self, username):
        print(f"[QUECTEL] Device '{username}' logged in from {self.remote_ip}")
    
    def on_logout(self, username):
        print(f"[QUECTEL] Device '{username}' logged out")
    
    def on_file_sent(self, file):
        print(f"[QUECTEL] FOTA file '{file}' sent successfully to {self.remote_ip}")
    
    def on_incomplete_file_sent(self, file):
        print(f"[QUECTEL] FOTA file '{file}' partially sent to {self.remote_ip}")

def setup_fota_files():
    """Setup FOTA files in the expected directory structure"""
    ftp_root = "quectel_opencpu_ftp"
    firmware_dir = os.path.join(ftp_root, "firmware")
    
    # Create directories
    if not os.path.exists(ftp_root):
        os.makedirs(ftp_root)
    if not os.path.exists(firmware_dir):
        os.makedirs(firmware_dir)
    
    # Copy and ensure correct filenames
    source_files = [
        ("firmware/1.1.1.pack", "1.1.1.pack"),
        ("firmware/1.1.11.pack", "1.1.11.pack"),
        ("firmware/1.1.1.pac", "1.1.1.pack"),  # Copy .pac as .pack for compatibility
    ]
    
    available_files = []
    
    for source_file, dest_filename in source_files:
        if os.path.exists(source_file):
            dest_path = os.path.join(firmware_dir, dest_filename)
            if not os.path.exists(dest_path):
                shutil.copy2(source_file, dest_path)
                print(f"Copied {source_file} -> firmware/{dest_filename}")
            
            file_size = os.path.getsize(dest_path)
            available_files.append((dest_filename, file_size))
    
    # Verify the expected file exists
    expected_file = os.path.join(firmware_dir, "1.1.1.pack")
    if os.path.exists(expected_file):
        print(f"✓ Quectel expected file 'firmware/1.1.1.pack' is ready")
        print(f"  File size: {os.path.getsize(expected_file):,} bytes")
    else:
        print("✗ WARNING: Expected file 'firmware/1.1.1.pack' not found!")
    
    return ftp_root, available_files

def main():
    # Disable extensive logging that might interfere
    logging.basicConfig(level=logging.WARNING)  # Only show warnings and errors
    
    print("=" * 60)
    print("QUECTEL OPENCPU FOTA FTP SERVER")
    print("=" * 60)
    
    # Setup FOTA files
    ftp_root, available_files = setup_fota_files()
    
    # Create authorizer - match your code exactly
    authorizer = DummyAuthorizer()
    authorizer.add_user("test", "test", ftp_root, perm="elr")  # Read permissions only
    
    # Create handler optimized for Quectel OpenCPU
    handler = QuectelOpenCPUHandler
    handler.authorizer = authorizer
    
    # Quectel-specific optimizations
    handler.banner = "Quectel FOTA Ready"
    handler.permit_foreign_addresses = True
    handler.tcp_no_delay = True  # Reduce latency
    
    # Don't restrict passive ports - let system choose
    # Quectel devices work better with default port allocation
    
    # Create FTP server
    server = FTPServer(("0.0.0.0", 4000), handler)
    server.max_cons = 10  # Allow multiple connections
    server.max_cons_per_ip = 5  # Multiple connections per IP
    
    print(f"Server: 0.0.0.0:4000")
    print(f"Username: test")
    print(f"Password: test")
    print(f"FTP Root: {os.path.abspath(ftp_root)}")
    print(f"Expected path in your code: firmware/1.1.1.pack")
    print()
    print("Available FOTA files:")
    for filename, size in available_files:
        print(f"  firmware/{filename} ({size:,} bytes)")
    print()
    print("Quectel OpenCPU optimizations:")
    print("  ✓ Extended timeout (10 minutes)")
    print("  ✓ Disabled sendfile for compatibility")
    print("  ✓ TCP_NODELAY enabled")
    print("  ✓ Multiple connections allowed")
    print("  ✓ Standard passive port allocation")
    print()
    print("Your Quectel code configuration:")
    print(f"  hostname: {server.address[0]}:{server.address[1]}")
    print("  username: test")
    print("  password: test")
    print("  file_full_path: firmware/1.1.1.pack")
    print()
    print("Server ready for Quectel OpenCPU FOTA download")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Quectel FOTA server...")
        server.close_all()

if __name__ == "__main__":
    main()
