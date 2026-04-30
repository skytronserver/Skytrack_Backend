#!/usr/bin/env python3
import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

# This matches your device DFOTA logic in fota_ftp_demo.c:
# Remote path requested by the module:  MAPW/<current_version>.pac
# Example: MAPW/1.0.1.pac  (contains delta to migrate 1.0.1 -> 1.0.2)

FTP_PORT = int(os.getenv("FTP_PORT", "5001"))
FTP_USER = os.getenv("FTP_USER", "test")
FTP_PASS = os.getenv("FTP_PASS", "test")
FOTA_DIR = os.getenv("FOTA_DIR", "MAPW")   # must match the folder used by the device code

# IMPORTANT for Internet-facing FTP:
# Passive mode uses a second TCP port for data transfers.
# If you only open FTP_PORT in your firewall/NSG, external clients will hang/fail on LIST/RETR.
# Use a small fixed range here and open it in the cloud firewall/NSG too.
PASSIVE_PORT_START = int(os.getenv("FTP_PASSIVE_PORT_START", "50000"))
PASSIVE_PORT_END = int(os.getenv("FTP_PASSIVE_PORT_END", "50020"))

# If the server is behind NAT (common on cloud VMs), set this to your PUBLIC IP so the
# server advertises the correct address in PASV/EPSV responses.
# Example: export FTP_PUBLIC_IP=xxx.xxx.xxx.xxx
FTP_PUBLIC_IP = os.getenv("FTP_PUBLIC_IP")

def main():
    # Ensure MAPW/ exists (FTP root is current directory ".")
    os.makedirs(FOTA_DIR, exist_ok=True)

    print(f"FTP root: {os.path.abspath('.')}")
    print(f"DFOTA directory: {os.path.abspath(FOTA_DIR)}")
    print(f"Listening on: 0.0.0.0:{FTP_PORT}")
    print(f"Username: {FTP_USER}")
    print(f"Password: {FTP_PASS}")
    print(f"Passive ports: {PASSIVE_PORT_START}-{PASSIVE_PORT_END}")
    if FTP_PUBLIC_IP:
        print(f"Public IP (masquerade): {FTP_PUBLIC_IP}")
    else:
        print("Public IP (masquerade): not set (OK for local/LAN; needed for some public/NAT setups)")
    print()
    print("Place DFOTA files like:")
    print("  MAPW/1.0.1.pac   (updates 1.0.1 -> 1.0.2)")
    print("  MAPW/1.0.2.pac   (updates 1.0.2 -> 1.0.3)")
    print()

    # List available pac files for quick sanity
    pac_files = [f for f in os.listdir(FOTA_DIR) if f.lower().endswith(".pac")]
    if not pac_files:
        print("WARNING: No .pac files found in MAPW/. Device will log 'No DFOTA package available' and skip.")
    else:
        print("Available DFOTA packages:")
        for f in sorted(pac_files):
            p = os.path.join(FOTA_DIR, f)
            try:
                print(f"  - {FOTA_DIR}/{f} ({os.path.getsize(p):,} bytes)")
            except OSError:
                print(f"  - {FOTA_DIR}/{f}")

    # FTP auth (root is ".", so MAPW/... paths work)
    authorizer = DummyAuthorizer()
    authorizer.add_user(FTP_USER, FTP_PASS, ".", perm="elradfmwMT")

    handler = FTPHandler
    handler.authorizer = authorizer
    handler.banner = "Mapwala DFOTA FTP Server Ready"
    handler.passive_ports = range(PASSIVE_PORT_START, PASSIVE_PORT_END + 1)
    if FTP_PUBLIC_IP:
        handler.masquerade_address = FTP_PUBLIC_IP

    server = FTPServer(("0.0.0.0", FTP_PORT), handler)

    print()
    print("Press Ctrl+C to stop the server")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down FTP server...")
        server.close_all()

if __name__ == "__main__":
    main()