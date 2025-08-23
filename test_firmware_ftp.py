#!/usr/bin/env python3
"""
Test script to verify FTP server accessibility for firmware files
"""
import ftplib
import sys

def test_firmware_access(host='localhost', port=4000):
    """Test specific firmware file access"""
    try:
        print(f"Testing FTP server at {host}:{port}")
        
        # Connect and login
        ftp = ftplib.FTP()
        ftp.connect(host, port)
        ftp.login('test', 'test')
        print("✓ Connected and logged in")
        
        # List files in root directory
        print("\n--- Files in root directory ---")
        files = []
        ftp.retrlines('LIST', files.append)
        for file_info in files:
            print(file_info)
        
        # Test specific firmware files
        firmware_files = ['1.1.1.pack', '1.1.11.pack']
        for filename in firmware_files:
            print(f"\n--- Testing {filename} ---")
            try:
                # Test SIZE command
                size = ftp.size(filename)
                print(f"✓ File {filename} exists, size: {size} bytes")
                
                # Test download first 10 bytes
                data = b''
                def collect_chunk(chunk):
                    nonlocal data
                    data += chunk
                    if len(data) >= 10:
                        raise Exception("Got 10 bytes")
                
                try:
                    ftp.retrbinary(f'RETR {filename}', collect_chunk)
                except Exception as e:
                    if "Got 10 bytes" in str(e):
                        print(f"✓ Successfully downloaded first 10 bytes: {data[:10]}")
                    else:
                        print(f"✗ Download test failed: {e}")
                        
            except Exception as e:
                print(f"✗ Error accessing {filename}: {e}")
        
        ftp.quit()
        print("\n✓ Test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    test_firmware_access(host)
