
import hashlib
import zlib
import binascii

def calculate_checksum_simple(data_string):
    """
    Simple checksum: Sum of ASCII values modulo 256
    """
    return sum(ord(c) for c in data_string) % 256

def calculate_checksum_xor(data_string):
    """
    XOR checksum: XOR all bytes together
    """
    checksum = 0
    for char in data_string:
        checksum ^= ord(char)
    return checksum

def calculate_crc8(data_string):
    """
    CRC8 checksum using zlib
    """
    return zlib.crc32(data_string.encode()) & 0xFF

def calculate_md5_short(data_string):
    """
    MD5 hash (first 8 characters)
    """
    return hashlib.md5(data_string.encode()).hexdigest()[:8]

def calculate_nmea_checksum(data_string):
    """
    NMEA-style checksum (XOR between $ and *)
    Commonly used in GPS protocols
    """
    # Remove $ at start and * at end if present
    if data_string.startswith('$'):
        data_string = data_string[1:]
    if data_string.endswith('*'):
        data_string = data_string[:-1]
    
    checksum = 0
    for char in data_string:
        checksum ^= ord(char)
    return f"{checksum:02X}"  # Return as 2-digit hex

def add_hash_to_gps_packet(packet_without_hash, hash_type="simple"):
    """
    Add hash to a GPS packet string before the asterisk
    
    Args:
        packet_without_hash: GPS packet without hash (e.g., "$,PVT,HPSP,1.0.0,NR,01,L,data1,data2,000051,*")
        hash_type: Type of hash to generate ("simple", "xor", "crc8", "md5", "nmea")
    
    Returns:
        GPS packet with hash added
    """
    # Remove trailing asterisk if present
    if packet_without_hash.endswith('*'):
        base_packet = packet_without_hash[:-1]
    else:
        base_packet = packet_without_hash
    
    # Calculate hash based on the data portion (excluding serial number)
    # For GPS packets, usually hash is calculated on everything before serial
    parts = base_packet.split(',')
    if len(parts) >= 2:
        # Data to hash (everything except the last part which is serial)
        data_to_hash = ','.join(parts[:-1])
    else:
        data_to_hash = base_packet
    
    # Generate hash based on type
    if hash_type == "simple":
        hash_value = calculate_checksum_simple(data_to_hash)
    elif hash_type == "xor":
        hash_value = calculate_checksum_xor(data_to_hash)
    elif hash_type == "crc8":
        hash_value = calculate_crc8(data_to_hash)
    elif hash_type == "md5":
        hash_value = calculate_md5_short(data_to_hash)
    elif hash_type == "nmea":
        hash_value = calculate_nmea_checksum(data_to_hash)
    else:
        hash_value = calculate_checksum_simple(data_to_hash)  # default
    
    # Add hash before asterisk
    return f"{base_packet},{hash_value},*"

def main():
    """
    Example usage of hash generation for GPS packets
    """
    print("GPS Packet Hash Generation Examples")
    print("=" * 50)
    
    # Example GPS packets without hash
    test_packets = [
      "$,PVT,DTPL,1.0.0,OT,12,L,860269065286973,DL02AB1111,1,14102025,073223,18.524075,N,73.816109,E,1.0,328.10,17,704.2,1.1,0.8,AIRTEL,0,1,23.3,4.1,0,C,31,404,90,17F6,5A65,0000,0000,0,0000,0000,0,0000,0000,0,0000,0000,0,0100,10,000352,",
        "$,PVT,HPSP,1.0.0,NR,02,H,hist1,hist2,000025",
        "$,PVT,HPSP,1.0.0,NR,01,L,live,packet,000100"
    ]
    
    hash_types = ["simple", "xor", "crc8", "md5", "nmea"]
    
    for i, packet in enumerate(test_packets, 1):
        print(f"\nExample {i}: {packet}")
        print("-" * 60)
        
        for hash_type in hash_types:
            hashed_packet = add_hash_to_gps_packet(packet, hash_type)
            print(f"{hash_type:>6}: {hashed_packet}")
    
    print("\n" + "=" * 50)
    print("Manual Hash Calculation Examples:")
    print("=" * 50)
    
    test_string = "$,PVT,HPSP,1.0.0,NR,01,L,data1,data2"
    print(f"Input string: {test_string}")
    print(f"Simple checksum: {calculate_checksum_simple(test_string)}")
    print(f"XOR checksum: {calculate_checksum_xor(test_string)}")
    print(f"CRC8: {calculate_crc8(test_string)}")
    print(f"MD5 (short): {calculate_md5_short(test_string)}")
    print(f"NMEA checksum: {calculate_nmea_checksum(test_string)}")

if __name__ == "__main__":
    main()