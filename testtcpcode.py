import socket
import time
import random
import datetime
import math

# ========================
# CONFIGURABLE PARAMETERS
# ========================
SERVER_IP = "135.235.166.209"  # same as m_SrvADDR
PORT1 = 6000
PORT2 = 5001

IMEI = "861850060252422"
DEVICE_ID = "AS09AC4635"

# Base GPS location (latitude, longitude)
BASE_LAT = 24.880475
BASE_LON = 92.881256

# Random movement radius in meters
RANDOM_RADIUS_M = 5

# ========================
# FUNCTIONS
# ========================

def random_gps_nearby(base_lat, base_lon, radius_m=50):
    """Generate a random GPS coordinate within `radius_m` meters of base location."""
    # Convert meters to degrees roughly
    radius_deg = radius_m / 111320.0  # 1 deg ~ 111.32 km
    angle = random.uniform(0, 2 * math.pi)
    offset_lat = radius_deg * math.cos(angle)
    offset_lon = (radius_deg * math.sin(angle)) / math.cos(math.radians(base_lat))
    return round(base_lat + offset_lat, 6), round(base_lon + offset_lon, 6)

def get_current_gps_data():
    """Generate current UTC time/date and random GPS within 50m of BASE_LAT/LON."""
    now_utc = datetime.datetime.utcnow()
    date_str = now_utc.strftime("%d%m%Y")    # ddmmyyyy
    time_str = now_utc.strftime("%H%M%S")    # hhmmss
    lat, lon = random_gps_nearby(BASE_LAT, BASE_LON, RANDOM_RADIUS_M)
    heading = random.randint(0, 359)
    altitude = random.randint(50, 80)      # dummy altitude in meters
    satellites = random.randint(6, 12)
    fix_status = 1  # valid fix
    speed = random.randint(0, 40)  # speed in km/h
    return date_str, time_str, lat, lon, heading, altitude, satellites, fix_status, speed

def calculate_checksum(payload: str) -> str:
    """Calculate XOR checksum like NMEA."""
    checksum = 0
    for c in payload:
        checksum ^= ord(c)
    return f"{checksum:02X}"

def build_payloads():
    """Generate two payload strings using the SAME GPS data for both ports."""
    date_str, time_str, lat, lon, heading, altitude, sats, fix, speed = get_current_gps_data()
    
    # First payload (T frame)
    payload1 = f"$,T,ATKCT,2.2.2,EA,01,L,{IMEI},{DEVICE_ID},{fix},{date_str},{time_str},{lat},N,{lon},E,{speed},{heading},{sats},{altitude},1.9,0.9,airtel,1,1,12.2,4.0,0,O,27,405,56,0093,27A7,0,0,0,0,0,0,0,0,0,0,0,0,1110,00,000041,71.9,"
    checksum1 = calculate_checksum(payload1)
    payload1 = f"{payload1}{checksum1},*"

    # Second payload (EPB/EMR frame)
    payload2 = f"$,EPB,EMR,{IMEI},NM,{date_str},{time_str},A,{lat},N,{lon},E,0.0,0.0,236.8,G,{DEVICE_ID},0000000000,"
    checksum2 = calculate_checksum(payload2)
    payload2 = f"{payload2}{checksum2},*"
    
    return payload1, payload2

def send_to_tcp(ip, port, data):
    """Send data to a TCP server and close connection."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((ip, port))
            s.sendall(data.encode('ascii'))
            print(f"✅ Sent to {ip}:{port} -> {data}")
    except Exception as e:
        print(f"❌ Failed to send to {ip}:{port} -> {e}")

# ========================
# MAIN LOOP
# python3 testtcpcode.py
# ========================
if __name__ == "__main__":
    while True:
        # Create SAME GPS data for both ports
        payload1, payload2 = build_payloads()
        
        # Send to both ports
        send_to_tcp(SERVER_IP, PORT1, payload1)
        send_to_tcp(SERVER_IP, PORT2, payload2)

        time.sleep(12)
