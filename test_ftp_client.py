#!/usr/bin/env python3
"""
FTP Client Test Script for debugging Quectel FOTA issues
"""
import ftplib
import os
import sys

def test_ftp_connection(host='localhost', port=4000, username='test', password='test'):
    """Test FTP connection and operations"""
    try:
        print(f"Connecting to FTP server at {host}:{port}")
        
        # Create FTP connection
        ftp = ftplib.FTP()
        ftp.connect(host, port)
        print(f"✓ Connected successfully")
        
        # Login
        ftp.login(username, password)
        print(f"✓ Logged in as {username}")
        
        # Print welcome message
        print(f"Welcome message: {ftp.getwelcome()}")
        
        # List current directory
        print("\n--- Current directory listing ---")
        ftp.dir()
        
        # Change to firmware directory
        print("\n--- Changing to firmware directory ---")
        ftp.cwd('firmware')
        print("✓ Changed to firmware directory")
        
        # List firmware directory
        print("\n--- Firmware directory listing ---")
        ftp.dir()
        
        # Get file size
        print("\n--- Getting file information ---")
        files = ftp.nlst()
        for filename in files:
            try:
                size = ftp.size(filename)
                print(f"File: {filename}, Size: {size} bytes")
            except Exception as e:
                print(f"Could not get size for {filename}: {e}")
        
        # Test PASV mode
        print("\n--- Testing passive mode ---")
        ftp.set_pasv(True)
        print("✓ Passive mode enabled")
        
        # Try to download a small chunk to test data connection
        if '1.1.1.pack' in files:
            print("\n--- Testing data connection (first 100 bytes) ---")
            data = []
            def collect_data(chunk):
                data.append(chunk)
                if len(b''.join(data)) >= 100:  # Stop after 100 bytes
                    raise Exception("Stopping after 100 bytes")
            
            try:
                ftp.retrbinary('RETR 1.1.1.pack', collect_data)
            except Exception as e:
                if "Stopping after 100 bytes" in str(e):
                    print(f"✓ Data connection working, received {len(b''.join(data))} bytes")
                else:
                    print(f"✗ Data connection failed: {e}")
        
        print("\n--- Closing connection ---")
        ftp.quit()
        print("✓ Connection closed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    print("=== FTP Connection Test ===")
    success = test_ftp_connection(host)
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Tests failed!")
