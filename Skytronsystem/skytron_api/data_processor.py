"""
Common data processing module for GPS tracking and Emergency data
This module contains shared processing logic for TCP, MQTT, and EM servers
"""

import re
import json
import time
import string
import secrets
from datetime import datetime, timezone, timedelta
import pytz
from django.db import close_old_connections
from django.db.models import Max
from django.utils import timezone as django_timezone
from geopy.distance import geodesic

# Per-device cache for the most-recent route alert state.
# Avoids re-scanning the full AlertsLog table on every GPS update.
# Invalidated immediately when a new alert is written.
# No lock: dict get/set/pop are atomic under the GIL, and a race here only
# means a redundant recompute of an idempotent value, never corruption --
# a shared lock across all devices would otherwise serialize every
# concurrent cache-miss (e.g. a burst of many distinct devices reconnecting).
_route_alert_cache: dict = {}          # device_tag_id -> (expires_at, last_alert_map)
_ROUTE_ALERT_CACHE_TTL = 30           # seconds

# Per-IMEI cache for DeviceStock lookups (device registration rarely changes).
_device_cache: dict = {}               # imei_str -> (expires_at, DeviceStock|None)
_DEVICE_CACHE_TTL = 120               # seconds

# Per-device_id cache for DeviceTag lookups.
_device_tag_cache: dict = {}           # device.id -> (expires_at, DeviceTag|None)

# Per-device cache for the most-recent non-Route alert per type.
# Eliminates 15+ DB queries per packet caused by lastnormal_alerts.filter().last() calls.
# Invalidated whenever create_alert() writes a new row.
_normal_alert_cache: dict = {}         # device_tag_id -> (expires_at, {type: AlertsLog})
_NORMAL_ALERT_CACHE_TTL = 10          # seconds

from skytron_api.models import (
    GPSData, GPSDataLog, DeviceTag, DeviceStock, Route, AlertsLog,
    EMGPSLocation, GPSemDataLog, User, BleKey,
    gpsdata_populate_location_and_consecutive_time,
    pointofinterests,
)

# Timezone setup
gmt_timezone = pytz.timezone('GMT')
ist_timezone = pytz.timezone('Asia/Kolkata')


def _get_device_by_imei(imei):
    """Cached DeviceStock lookup by IMEI string. TTL = 120 s.

    Locking removed: dict get/set are atomic under the GIL, and this cache
    is idempotent (a race just means two threads redundantly compute the
    same DeviceStock lookup) -- the shared lock was serializing every
    concurrent cache-miss across ALL devices, which under a burst of many
    distinct devices (e.g. a mass reconnect) became the bottleneck itself.
    """
    now = time.monotonic()
    key = str(imei)
    entry = _device_cache.get(key)
    if entry and now < entry[0]:
        return entry[1]
    # Exact match first -- uses the unique index on imei (O(log n)).
    # Falls back to substring match only for legacy rows whose stored imei
    # doesn't exactly match what the device sends (varying lengths seen in
    # production data); that fallback can't use an index and is O(n), so
    # it should stay rare.
    device = DeviceStock.objects.filter(imei=key).first()
    if device is None:
        device = DeviceStock.objects.filter(imei__contains=key).last()
    _device_cache[key] = (now + _DEVICE_CACHE_TTL, device)
    return device


def _get_device_tag(device):
    """Cached DeviceTag lookup for a DeviceStock instance. TTL = 120 s."""
    if device is None:
        return None
    now = time.monotonic()
    key = device.id
    entry = _device_tag_cache.get(key)
    if entry and now < entry[0]:
        return entry[1]
    device_tag = DeviceTag.objects.filter(device=device, status='Owner_Final_OTP_Verified').last()
    _device_tag_cache[key] = (now + _DEVICE_CACHE_TTL, device_tag)
    return device_tag


def _get_normal_alert_map(device_tag):
    """Return {alert_type: AlertsLog} for the latest non-Route alert per type.
    Cached per device for _NORMAL_ALERT_CACHE_TTL seconds.
    Invalidated by create_alert() on every new alert write.
    """
    now = time.monotonic()
    key = device_tag.id
    entry = _normal_alert_cache.get(key)
    if entry and now < entry[0]:
        return entry[1]

    last_alerts = (
        AlertsLog.objects.filter(deviceTag=device_tag)
        .exclude(type="Route")
        .values('type')
        .annotate(latest_timestamp=Max('timestamp'))
    )
    alerts = list(AlertsLog.objects.filter(
        deviceTag=device_tag,
        type__in=[e['type'] for e in last_alerts],
        timestamp__in=[e['latest_timestamp'] for e in last_alerts],
    ))
    alert_map = {a.type: a for a in alerts}

    _normal_alert_cache[key] = (now + _NORMAL_ALERT_CACHE_TTL, alert_map)
    return alert_map


def process_gps_data(data_str):
    """
    Process GPS tracking data from devices
    Supports both old 52-field format and new PVT format
    Used by TCP server and MQTT deviceTracking topic
    """
    try:
        groups = data_str.split(',')
        
        # New PVT format: $,PVT,HPSP,1.0.0,NR,01,L,860269065286924,DL01AB1234,1,24102025,053343,26.193022,N,91.752831,E,0.0,341.14,23,56.8,0.9,0.6,AIRTEL,1,1,11.6,4.2,1,C,16,405,56,1BDA,E62F,0000,0000,0,0000,0000,0,0000,0000,0,0000,0000,0,1111,10,000043,20,*
        if len(groups) >= 45 and groups[0] == '$' and groups[1] == 'PVT':
            try:
                # Parse datetime
                date_str = groups[10]  # 24102025
                time_str = groups[11]  # 053343
                
                # Convert to proper datetime format
                gmt_datetime_str = f'{date_str} {time_str}'
                gmt_datetime = datetime.strptime(gmt_datetime_str, '%d%m%Y %H%M%S')
                ist_datetime = gmt_timezone.localize(gmt_datetime).astimezone(ist_timezone)
                
                # Separate date and time components
                ist_date = ist_datetime.strftime('%d%m%Y')
                ist_time = ist_datetime.strftime('%H%M%S')

                # Validate GPS coordinates
                lat = float(groups[12])  # 26.193022
                lon = float(groups[14])  # 91.752831
                
                if lat < 5 or lon < 5:
                    return None
                if lat > 90 or lon > 180:  # Updated coordinate validation
                    return None
                if str(groups[13]) not in ["N", "S"] or str(groups[15]) not in ["E", "W"]:
                    return None

                gps_data = {
                    'packet_type': groups[4][:2],  # PVT -> PV (limit to 2 chars)
                    'alert_id': groups[5][:2],     # 01 (sequence number, used as alert_id)
                    'packet_status': groups[6][:1], # L (Live/History indicator, limit to 1 char)
                    'imei': groups[7],         # 860269065286924
                    'vehicle_registration_number': groups[8], # DL01AB1234
                    'gps_status': groups[9][:1],   # 1 (GPS fix status, limit to 1 char)
                    'packet_datetime': ist_datetime,
                    'date': ist_date,
                    'time': ist_time,
                    'latitude': lat,
                    'latitude_dir': groups[13][:1], # N (limit to 1 char)
                    'longitude': lon,
                    'longitude_dir': groups[15][:1], # E (limit to 1 char)
                    'speed': float(groups[16]),  # 341.14 (speed in km/h)
                    'heading': float(groups[17]), # 23 (course/heading)
                    'satellites': int(float(groups[18])), # 0.9 (satellites in use)
                    'altitude': int(float(groups[19])),   # 0.0 (altitude)
                    'pdop': float(groups[20]),   # 0.6 (GPS accuracy)
                    'hdop': float(groups[21]),   # 56.8 (HDOP)
                    'network_operator': groups[22][:20], # AIRTEL (limit length)
                    'ignition_status': groups[23][:1],  # 1 (ignition status, limit to 1 char)
                    'main_power_status': groups[24][:1], # 1 (GPRS status, using as main power)
                    'main_input_voltage': float(groups[25]), # 11.6 (main power voltage)
                    'internal_battery_voltage': float(groups[26]), # 4.2 (backup battery)
                    'emergency_status': groups[27][:1],     # Default, not in new format
                    'box_tamper_alert': groups[28][:1],     # Default Open, not in new format
                    'gsm_signal_strength': groups[29][:2], # 1 (GSM signal strength)
                    'mcc': groups[30][:10],           # 405 (Mobile Country Code)
                    'mnc': groups[31][:10],           # 56 (Mobile Network Code)
                    'lac': groups[32][:10],           # 1BDA (Location Area Code)
                    'cell_id': groups[33][:10],       # E62F (Cell ID)
                    'nbr1_cell_id': groups[34][:10],  # 0000 (Neighboring cell 1)
                    'nbr1_lac': groups[35][:10],      # 0000
                    'nbr1_signal_strength': groups[36][:10], # 0
                    'nbr2_cell_id': groups[37][:10],  # 0000 (Neighboring cell 2)
                    'nbr2_lac': groups[38][:10],      # 0000
                    'nbr2_signal_strength': groups[39][:10], # 0
                    'nbr3_cell_id': groups[40][:10],  # 0000 (Neighboring cell 3)
                    'nbr3_lac': groups[41][:10],      # 0000
                    'nbr3_signal_strength': groups[42][:10], # 0
                    'nbr4_cell_id': groups[43][:10],  # 0000 (Neighboring cell 4)
                    'nbr4_lac': groups[44][:10],      # 0000
                    'nbr4_signal_strength': groups[45][:10] if len(groups) > 45 else '0', # 0
                    'digital_input_status': groups[46][:10] if len(groups) > 46 else '1111', # 1111
                    'digital_output_status': groups[47][:3] if len(groups) > 47 else '00', # 1111 
                    'frame_number': int(groups[48]) if len(groups) > 48 and groups[48].isdigit() else 0, # 10 (odometer reading)
                    'odometer': float(groups[49]) if len(groups) > 49 and groups[49].replace('.', '').isdigit() else 0.0, # 000043
                }

                return gps_data
                
            except (ValueError, IndexError) as e:
                print(f"Error parsing PVT format: {e}", flush=True)
                return None
                
        # Legacy 52-field format: $,T,ATMV,1.1.4,BH,05,L,861850060252547,ABC00000012...
        elif len(groups) == 52 and groups[0] == '$' and groups[1] == 'T':
            try:
                # Combine date and time strings and convert to a datetime object
                gmt_datetime_str = f'{groups[10]} {groups[11]}'
                gmt_datetime = datetime.strptime(gmt_datetime_str, '%d%m%Y %H%M%S')
                ist_datetime = gmt_timezone.localize(gmt_datetime).astimezone(ist_timezone)
                
                # Separate date and time components
                ist_date = ist_datetime.strftime('%d%m%Y')
                ist_time = ist_datetime.strftime('%H%M%S')

                # Validate GPS coordinates
                lat = float(groups[12])
                lon = float(groups[14])
                
                if lat < 5 or lon < 5:
                    return None
                if lat > 180 or lon > 180:
                    return None
                if str(groups[13]) != "N" or str(groups[15]) != "E":
                    return None

                gps_data = {
                    'packet_type': groups[4],
                    'alert_id': groups[5],
                    'packet_status': groups[6],
                    'imei': groups[7],
                    'vehicle_registration_number': groups[8],
                    'gps_status': groups[9],
                    'packet_datetime': ist_datetime,
                    'date': ist_date,
                    'time': ist_time,
                    'latitude': lat,
                    'latitude_dir': groups[13],
                    'longitude': lon,
                    'longitude_dir': groups[15],
                    'speed': float(groups[16]),
                    'heading': float(groups[17]),
                    'satellites': int(groups[18]),
                    'altitude': int(float(groups[19])),
                    'pdop': float(groups[20]),
                    'hdop': float(groups[21]),
                    'network_operator': groups[22],
                    'ignition_status': groups[23],
                    'main_power_status': groups[24],
                    'main_input_voltage': float(groups[25]),
                    'internal_battery_voltage': float(groups[26]),
                    'emergency_status': groups[27],
                    'box_tamper_alert': groups[28],
                    'gsm_signal_strength': groups[29],
                    'mcc': groups[30],
                    'mnc': groups[31],
                    'lac': groups[32],
                    'cell_id': groups[33],
                    'nbr1_cell_id': groups[34],
                    'nbr1_lac': groups[35],
                    'nbr1_signal_strength': groups[36],
                    'nbr2_cell_id': groups[37],
                    'nbr2_lac': groups[38],
                    'nbr2_signal_strength': groups[39],
                    'nbr3_cell_id': groups[40],
                    'nbr3_lac': groups[41],
                    'nbr3_signal_strength': groups[42],
                    'nbr4_cell_id': groups[43],
                    'nbr4_lac': groups[44],
                    'nbr4_signal_strength': groups[45],
                    'digital_input_status': groups[46],
                    'digital_output_status': groups[47],
                    'frame_number': int(groups[48]),
                    'odometer': float(groups[49]),
                }

                return gps_data
            except (ValueError, IndexError) as e:
                print(f"Error parsing legacy format: {e}", flush=True)
                return None
        else:
            print(f"Unknown GPS data format. Length: {len(groups)}, First fields: {groups[:5] if len(groups) >= 5 else groups}", flush=True)
            return None
    except Exception as e:
        print("GPS data processing error:", e, flush=True)
        return None


def process_em_data(data_str, publish_callback=None):
    """
    Process Emergency (EM) data from devices
    Supports new EPB format: $,EPB,EMR,860269065287047,NM,24102025051128,A,26.193007,N,91.752815,E,90.6,0.0,0.000,G,DL01AB1234,9401633421,*,04
    Also supports optional extension before checksum:
    ...,*,{SOS_PUB_AS01PT0010},5C
    Used by EM server and MQTT deviceEM topic
    """
    _t_em_start = time.perf_counter()
    try:
        data_list = data_str.split(',')
        
        # New EPB format parsing
        if len(data_list) >= 17 and data_list[0] == '$' and data_list[1] == 'EPB':
            try:
                # Parse the timestamp (DDMMYYYYHHMMSS format)
                timestamp_str = data_list[5]  # 24102025062501
                #print(f"[MQTT] Parsing timestamp: {timestamp_str}", flush=True)
                
                if len(timestamp_str) == 14:
                    # Extract components: DD MM YYYY HH MM SS
                    day = timestamp_str[0:2]      # 24
                    month = timestamp_str[2:4]    # 10
                    year = timestamp_str[4:8]     # 2025
                    hour = timestamp_str[8:10]    # 06
                    minute = timestamp_str[10:12] # 25
                    second = timestamp_str[12:14] # 01
                    
                    #print(f"[MQTT] Extracted: {day}/{month}/{year} {hour}:{minute}:{second}", flush=True)
                    
                    # Create datetime object directly
                    gmt_datetime = datetime(
                        year=int(year),
                        month=int(month), 
                        day=int(day),
                        hour=int(hour),
                        minute=int(minute),
                        second=int(second)
                    )
                    
                    ist_datetime = gmt_timezone.localize(gmt_datetime).astimezone(ist_timezone)
                    #print(f"[MQTT] Parsed datetime: {ist_datetime}", flush=True)

                    extention_value = None
                    try:
                        star_index = next(
                            (idx for idx, token in enumerate(data_list) if (token or '').strip() == '*'),
                            None,
                        )
                        if star_index is not None and star_index + 1 < len(data_list):
                            maybe_extention = (data_list[star_index + 1] or '').strip()
                            if maybe_extention.startswith('{') and maybe_extention.endswith('}'):
                                extention_value = maybe_extention
                    except Exception:
                        extention_value = None
                    
                    # Create EM location data
                    em_data = {
                        'packet_type': data_list[1],      # EPB
                        'event_type': data_list[2],       # EMR
                        'imei': data_list[3],             # 860269065287047
                        'event_status': data_list[4],     # NM (Normal/Emergency)
                        'timestamp': ist_datetime,
                        'gps_validity': data_list[6],     # A (Valid/Invalid)
                        'latitude': float(data_list[7]),  # 26.193007
                        'latitude_dir': data_list[8],     # N
                        'longitude': float(data_list[9]), # 91.752815
                        'longitude_dir': data_list[10],   # E
                        'speed': float(data_list[11]),    # 90.6
                        'course': float(data_list[12]),   # 0.0
                        'altitude': float(data_list[13]), # 0.000
                        'gps_quality': data_list[14],     # G
                        'vehicle_reg': data_list[15],     # DL01AB1234
                        'contact_info': data_list[16] if len(data_list) > 16 else '', # 9401633421
                    }
                    
                    # You might want to create a specific EM data object here
                    # For now, we'll use the existing EMGPSLocation.create_from_string method
                    # but with the parsed data converted to the expected format
                    
                    # Convert to format expected by EMGPSLocation.create_from_string
                    # Looking at the original EM server, the expected format should be:
                    # [0] message_type (EMR)
                    # [1] device_imei  
                    # [2] packet_status (NM)
                    # [3] date (DDMMYYYY) 
                    # [4] time (HHMMSS)
                    # [5] gps_validity (A)
                    # [6] latitude
                    # [7] latitude_direction (N)
                    # [8] longitude  
                    # [9] longitude_direction (E)
                    # [10] speed
                    # [11] course/distance
                    # [12] altitude
                    # [13] provider (G)
                    # [14] vehicle_reg_no
                    # [15] reply_mob_no
                    
                    converted_data = [
                        data_list[2],  # EMR (message_type)
                        data_list[3],  # 860269065242240 (device_imei)
                        data_list[4],  # NM (packet_status)
                        f"{day}{month}{year}",     # 24102025 (date - DDMMYYYY format)
                        f"{hour}{minute}{second}", # 063007 (time - HHMMSS format)
                        data_list[6],  # A (gps_validity)
                        data_list[7],  # 24.880604 (latitude)
                        data_list[8],  # N (latitude_direction)
                        data_list[9],  # 92.881081 (longitude)
                        data_list[10], # E (longitude_direction)
                        data_list[11], # 18.6 (speed)
                        data_list[12], # 0.0 (course/distance)
                        data_list[13], # 0.000 (altitude)
                        data_list[14], # G (provider)
                        data_list[15], # DL01AB1234 (vehicle_reg_no)
                        data_list[16] if len(data_list) > 16 else '9401633421', # reply_mob_no
                    ]
                    
                    # Create EM data directly instead of using the problematic create_from_string method
                    try:
                        # Convert IST datetime to date and time fields
                        em_date = ist_datetime.date()
                        em_time = ist_datetime.time()
                        
                        # Find device by IMEI
                        imei = data_list[3]
                        _t_em0 = time.perf_counter()
                        device = DeviceStock.objects.filter(imei__contains=str(imei)).last()
                        _t_em1 = time.perf_counter()
                        #print(f"#{imei}# -> Device: {device}", flush=True)
                        print(f"[EM][Perf] device_lookup={(_t_em1-_t_em0)*1000:.1f}ms imei={imei}", flush=True)
                        
                        def _send_sos_stop(reason):
                            if publish_callback:
                                try:
                                    publish_callback(f"deviceResponse/{imei}", json.dumps({"keys": "@SETSOSDIS-1*"}), qos=1)
                                    print(f"[EM] SOS stop sent to device {imei} ({reason})", flush=True)
                                except Exception as _pe:
                                    print(f"[EM] Failed to send SOS stop to {imei}: {_pe}", flush=True)

                        device_tag = None
                        if device:
                            device_tag = DeviceTag.objects.filter(device=device,status = 'Owner_Final_OTP_Verified').last()
                            _t_em2 = time.perf_counter()
                            print(f"[EM][Perf] device_tag_lookup={(_t_em2-_t_em1)*1000:.1f}ms", flush=True)
                            if device_tag is None:
                                print(f"[EM] Device {imei} has no Owner_Final_OTP_Verified tag — rejecting EM packet", flush=True)
                                _send_sos_stop("no verified device tag")
                                return None
                        else:
                            print(f"[EM] Device {imei} not found in DeviceStock — rejecting EM packet", flush=True)
                            _send_sos_stop("unregistered device")
                            return None
                        
                        # Create EMGPSLocation directly
                        _t_em3 = time.perf_counter()
                        location = EMGPSLocation.objects.create(
                            message_type=data_list[2],        # EMR
                            device_imei=data_list[3],         # 860269065242240
                            packet_status=data_list[4],       # NM
                            date=em_date,                     # 2025-10-24
                            time=em_time,                     # 06:33:55
                            gps_validity=data_list[6],        # A
                            latitude=float(data_list[7]),     # 24.880587
                            latitude_direction=data_list[8],  # N
                            longitude=float(data_list[9]),    # 92.881050
                            longitude_direction=data_list[10], # E
                            speed=float(data_list[11]),       # 15.9
                            distance=float(data_list[12]),    # 0.0 (course)
                            altitude=float(data_list[13]),    # 0.000
                            provider=data_list[14],           # G
                            vehicle_reg_no= device_tag.vehicle_reg_no,  #  data_list[15],     # DL01AB1234
                            reply_mob_no=data_list[16] if len(data_list) > 16 else '9401633421', # phone
                            extention=extention_value,
                            device_tag=device_tag             # DeviceTag or None
                        )
                        
                        print(f"[MQTT] EM location created successfully: {location}", flush=True)
                        _t_em4 = time.perf_counter()
                        print(f"[EM][Perf] em_location_save={(_t_em4-_t_em3)*1000:.1f}ms  (includes post_save/create_emergency_call signal)", flush=True)
                        print(f"[EM][Perf] TOTAL process_em_data={(_t_em4-_t_em_start)*1000:.1f}ms", flush=True)
                        return location
                        
                    except Exception as create_error:
                        print(f"[MQTT] Direct EM creation error: {create_error}", flush=True)
                        return None
                    
            except (ValueError, IndexError) as e:
                print(f"Error parsing EPB format: {e}", flush=True)
                return None
                
        # Legacy format support (if needed)
        elif len(data_list) >= 18:
            # Remove the first element if it's just '$'
            if data_list[0] == '$':
                data_list = data_list[1:]
            
            # Process EM data according to the old format
            location = EMGPSLocation.create_from_string(data_list)
            return location
        else:
            print(f"Unknown EM data format. Length: {len(data_list)}, First fields: {data_list[:5] if len(data_list) >= 5 else data_list}", flush=True)
            return None
    except Exception as e:
        print("EM data processing error:", e, flush=True)
        return None


def create_alert(alert_type, status, loc_id, device_tag, poi_ref=None):
    """Create an alert entry"""
    try:
        AlertsLog.objects.create(
            type=alert_type,
            status=status,
            timestamp=datetime.now(),
            gps_ref_id=loc_id,
            deviceTag=device_tag,
            state=device_tag.device.dealer.manufacturer.state,
            poi_ref=poi_ref,
            alert_details='',
        )
        # Invalidate per-device alert cache so next packet sees the new row.
        _normal_alert_cache.pop(device_tag.id, None)
    except Exception as e:
        print(f"Error creating alert: {e}", flush=True)


def process_alerts(gps_data, loc_id):
    """
    Process alerts based on GPS data
    This handles all alert types: Emergency, Engine, OverSpeed, Battery, etc.
    """
    try:
        # Close old database connections before processing alerts
        close_old_connections()
        
        device_tag = gps_data['device_tag']
        packet_type = gps_data['packet_type']
        alert_id = gps_data['alert_id']
        lat = gps_data['latitude']
        lon = gps_data['longitude']

        # Load latest alert per type from cache (avoids 15+ DB queries per packet).
        normal_alert_map = _get_normal_alert_map(device_tag)

        # Emergency Alert
        if packet_type == "EA":
            alert_type = "Em"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)

        # Engine/Ignition Alerts
        if gps_data["ignition_status"] == "1":
            alert_type = "Eng"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)

            # Close any open UnauthorizedParking when engine starts
            try:
                up_last = normal_alert_map.get('UnauthorizedParking')
                if up_last and (up_last.status or '') == 'in':
                    create_alert('UnauthorizedParking', 'out', loc_id, device_tag)
            except Exception as _e:
                print(f"UnauthorizedParking close error: {_e}", flush=True)

            # Overtime: trigger along with Eng 'in' when outside working hours
            try:
                cat = getattr(device_tag, "category", None)
                wh_start = getattr(cat, "working_hour_start_time", None) if cat else None
                wh_end = getattr(cat, "working_hour_end_time", None) if cat else None

                if wh_start and wh_end:
                    now_ist_time = django_timezone.localtime(django_timezone.now(), ist_timezone).time()

                    def _in_working_hours(t, start, end):
                        return (start <= t <= end) if (start <= end) else (t >= start or t <= end)

                    in_hours = _in_working_hours(now_ist_time, wh_start, wh_end)
                    if not in_hours:
                        ot_last = normal_alert_map.get("Overtime")
                        if not ot_last or (ot_last.status or "") != "in":
                            create_alert("Overtime", "in", loc_id, device_tag)
                # If no working hours configured, skip Overtime
            except Exception as _e:
                print(f"Overtime check error: {_e}", flush=True)
        elif gps_data["ignition_status"] == "0":
            alert_type = "Eng"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

            # Close Overtime on engine off
            try:
                ot_last = normal_alert_map.get("Overtime")
                if ot_last and (ot_last.status or "") == "in":
                    create_alert("Overtime", "out", loc_id, device_tag)
            except Exception as _e:
                print(f"Overtime close error: {_e}", flush=True)

            # UnauthorizedParking: fire when ignition off within 50m of a NoParking POI
            try:
                noparking_pois = pointofinterests.objects.filter(
                    use_type='NoParking',
                    status='Active',
                    lat__isnull=False,
                    lon__isnull=False,
                    lat__range=(lat - 0.001, lat + 0.001),
                    lon__range=(lon - 0.001, lon + 0.001),
                )
                for _poi in noparking_pois:
                    if geodesic((lat, lon), (_poi.lat, _poi.lon)).meters <= 50:
                        create_alert('UnauthorizedParking', 'in', loc_id, device_tag, poi_ref=_poi)
                        break
            except Exception as _e:
                print(f"UnauthorizedParking check error: {_e}", flush=True)

        # Speed Alerts
        if gps_data["speed"] > 80:
            alert_type = "OverSpeed"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["speed"] <= 80:
            alert_type = "OverSpeed"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # Internal Battery Alerts
        if gps_data["internal_battery_voltage"] < 3:
            alert_type = "LowIntBat"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["internal_battery_voltage"] >= 3:
            alert_type = "LowIntBat"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # External Battery Alerts
        if gps_data["main_input_voltage"] < 8:
            alert_type = "LowExtBat"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["main_input_voltage"] > 9:
            alert_type = "LowExtBat"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # Battery Disconnect Alerts
        if gps_data["main_input_voltage"] < 2:
            alert_type = "ExtBatDiscnt"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["main_input_voltage"] >= 2:
            alert_type = "ExtBatDiscnt"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # Box Tamper Alerts
        if gps_data["box_tamper_alert"] == "C":
            alert_type = "BoxTemp"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["box_tamper_alert"] == "O":
            alert_type = "BoxTemp"
            al = normal_alert_map.get(alert_type)
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # GPS Loss Alerts
        try:
            gps_fix_ok = str(gps_data.get("gps_status", "")).strip() == "1"
        except Exception:
            gps_fix_ok = False
        alert_type = "GPSLoss"
        desired_status = "out" if gps_fix_ok else "in"
        al = normal_alert_map.get(alert_type)
        if not al or (al.status or "") != desired_status:
            create_alert(alert_type, desired_status, loc_id, device_tag)

        # Network Loss Alerts (based on GSM signal strength < 15)
        signal_raw = gps_data.get("gsm_signal_strength", 0)
        try:
            signal_val = float(signal_raw)
        except Exception:
            # If unparsable, treat as very low signal
            signal_val = 0.0
        alert_type = "NetworkLoss"
        desired_status = "in" if signal_val < 15 else "out"
        al = normal_alert_map.get(alert_type)
        if not al or (al.status or "") != desired_status:
            create_alert(alert_type, desired_status, loc_id, device_tag)

        # Alert ID based alerts
        alert_mappings = {
            "10": ('Em', "in"), 
            "20": ('EmPublicApp', "in"), 
            "21": ('EmRegisteredApp', "in"), 
            "22": ('EmMonitorTripInvalidPw', "in"), 
            "23": ('EmMonitorTripBLEDisconnect', "in"), 
            "24": ('EmMonitorTripDeviated', "in"), 
            "09": ("EmTemp", "in"), 
            "17": ("Tilt", "in"), 
            "13": ("HarshBreak", "in"), 
            "15": ("HarshTurn", "in"), 
            "14": ("HarshAcceleration", "in"), 
        }
        
  

        # Event-based alert IDs always create a new record on each occurrence
        # (transient events, not stateful on/off conditions)
        ALWAYS_CREATE_ALERT_IDS = {"10", "20", "21", "22", "23", "24", "09", "13", "14", "15", "17"}

        if alert_id in alert_mappings:
            alert_type, status = alert_mappings[alert_id]
            al = normal_alert_map.get(alert_type)
            if not al or al.status != status or alert_id in ALWAYS_CREATE_ALERT_IDS:
                create_alert(alert_type, status, loc_id, device_tag)

        # Border-cross alerts (state/district/city) on actual administrative change
        try:
            current_loc = (
                GPSData.objects
                .filter(id=loc_id, device_tag=device_tag)
                .only('id', 'state', 'district', 'city', 'device_tag_id', 'entry_time')
                .first()
            )
            if current_loc is not None:
                prev_loc = (
                    GPSData.objects
                    .filter(device_tag=device_tag)
                    .exclude(id=current_loc.id)
                    .order_by('-entry_time', '-id')
                    .only('id', 'state', 'district', 'city')
                    .first()
                )

                def _norm_admin(value):
                    text = (value or '').strip()
                    return text.casefold() if text else None

                if prev_loc is not None:
                    prev_state = _norm_admin(prev_loc.state)
                    cur_state = _norm_admin(current_loc.state)
                    if prev_state and cur_state and prev_state != cur_state:
                        create_alert('state_border_cross', 'in', loc_id, device_tag)

                    prev_district = _norm_admin(prev_loc.district)
                    cur_district = _norm_admin(current_loc.district)
                    if prev_district and cur_district and prev_district != cur_district:
                        create_alert('district_border_cross', 'in', loc_id, device_tag)

                    prev_city = _norm_admin(prev_loc.city)
                    cur_city = _norm_admin(current_loc.city)
                    if prev_city and cur_city and prev_city != cur_city:
                        create_alert('city_border_cross', 'in', loc_id, device_tag)
        except Exception as _e:
            print(f"Border-cross alert error: {_e}", flush=True)

        # Prohibited_Area: alert when vehicle is within 100m of a Prohibited_Area POI
        try:
            prohibited_pois = pointofinterests.objects.filter(
                use_type='Prohibited_Area',
                status='Active',
                lat__isnull=False,
                lon__isnull=False,
                lat__range=(lat - 0.002, lat + 0.002),
                lon__range=(lon - 0.002, lon + 0.002),
            )
            _prohibited_in_range = None
            for _poi in prohibited_pois:
                if geodesic((lat, lon), (_poi.lat, _poi.lon)).meters <= 100:
                    _prohibited_in_range = _poi
                    break
            _pa_last = normal_alert_map.get('Prohibited_Area')
            if _prohibited_in_range is not None:
                if not _pa_last or (_pa_last.status or '') == 'out':
                    create_alert('Prohibited_Area', 'in', loc_id, device_tag, poi_ref=_prohibited_in_range)
            else:
                if _pa_last and (_pa_last.status or '') == 'in':
                    create_alert('Prohibited_Area', 'out', loc_id, device_tag)
        except Exception as _e:
            print(f"Prohibited_Area check error: {_e}", flush=True)

        # Permit_3day: alert when vehicle has been outside its home district for 3+ days
        try:
            _home_district_obj = getattr(device_tag, 'district', None)
            if _home_district_obj is not None:
                _home_district_name = (_home_district_obj.district or '').strip().casefold()
                if _home_district_name:
                    _three_days_ago = django_timezone.now() - timedelta(days=3)
                    # Skip if a Permit_3day alert was already fired within the last 3 days
                    _recent_permit = AlertsLog.objects.filter(
                        deviceTag=device_tag,
                        type='Permit_3day',
                        timestamp__gte=_three_days_ago,
                    ).exists()
                    if not _recent_permit:
                        # Check if any GPS record in the last 3 days shows the home district
                        _gps_in_home = GPSData.objects.filter(
                            device_tag=device_tag,
                            entry_time__gte=_three_days_ago,
                            district__iexact=_home_district_name,
                        ).exists()
                        # Only fire if there is actually GPS data in the period (device is sending)
                        _gps_any = GPSData.objects.filter(
                            device_tag=device_tag,
                            entry_time__gte=_three_days_ago,
                            district__isnull=False,
                        ).exclude(district='').exists()
                        if _gps_any and not _gps_in_home:
                            create_alert('Permit_3day', 'in', loc_id, device_tag)
        except Exception as _e:
            print(f"Permit_3day check error: {_e}", flush=True)

        # Route Alerts
        process_route_alerts(gps_data, loc_id, device_tag, lat, lon)

    except Exception as e:
        print(f"Error processing alerts: {e}", flush=True)


def _get_route_alert_map(device_tag):
    """
    Return {('Route', route_id): alert} using DISTINCT ON to fetch only
    the most-recent alert per route.  Results are cached per device for
    _ROUTE_ALERT_CACHE_TTL seconds so the expensive query doesn't run on
    every GPS update.  The cache is invalidated when a new alert is written.
    """
    now = time.monotonic()
    dtid = device_tag.id
    entry = _route_alert_cache.get(dtid)
    if entry and now < entry[0]:
        return entry[1]

    # DISTINCT ON (route_ref_id) → one row per route, most-recent first.
    # Falls back to dedup-in-Python for DBs that don't support DISTINCT ON.
    try:
        alerts = list(
            AlertsLog.objects.filter(deviceTag=device_tag, type="Route")
            .order_by('route_ref_id', '-id')
            .distinct('route_ref_id')
        )
    except Exception:
        # Fallback: order + deduplicate in Python (original behaviour)
        alerts_qs = (
            AlertsLog.objects.filter(deviceTag=device_tag, type="Route")
            .order_by('route_ref_id', '-id')
        )
        seen: set = set()
        alerts = []
        for a in alerts_qs:
            if a.route_ref_id not in seen:
                seen.add(a.route_ref_id)
                alerts.append(a)

    alert_map = {('Route', a.route_ref_id): a for a in alerts if a.route_ref_id}
    _route_alert_cache[dtid] = (now + _ROUTE_ALERT_CACHE_TTL, alert_map)
    return alert_map


def _point_within_100m(lat, lon, points) -> bool:
    """
    Return True if any route point is within 100 m of (lat, lon).
    Uses a cheap bounding-box pre-filter (~0.0015 ° ≈ 165 m) to skip
    the expensive geodesic call for points that are clearly out of range.
    """
    LAT_MARGIN = 0.0015   # ~165 m latitude
    LON_MARGIN = 0.0015   # ~165 m longitude (conservative; varies by latitude)
    for point in points[:-1]:
        route_lon, route_lat, *_ = point
        if abs(route_lat - lat) > LAT_MARGIN or abs(route_lon - lon) > LON_MARGIN:
            continue
        if geodesic((lat, lon), (route_lat, route_lon)).meters <= 100:
            return True
    return False


def process_route_alerts(gps_data, loc_id, device_tag, lat, lon):
    """Process route-based alerts"""
    _t_route_start = time.perf_counter()
    try:
        routes = Route.objects.filter(status='Active', device=device_tag.device)
        _t_routes_fetched = time.perf_counter()

        last_alert_map = _get_route_alert_map(device_tag)

        route_count = len(routes)
        print(f"Routes found: {route_count}", flush=True)
        _t_last_alerts_fetched = time.perf_counter()
        print(f"[Tracking][Perf] route_fetch={(_t_routes_fetched-_t_route_start)*1000:.1f}ms  last_alerts_fetch={(_t_last_alerts_fetched-_t_routes_fetched)*1000:.1f}ms  routes={route_count}", flush=True)

        alert_written = False
        for i, route in enumerate(routes):
            _t_ri = time.perf_counter()
            points = json.loads(route.route)
            status = "in" if _point_within_100m(lat, lon, points) else "out"

            alert_key = ('Route', route.id)
            last_alert = last_alert_map.get(alert_key)

            if not last_alert or not last_alert.status or last_alert.status != status:
                AlertsLog.objects.create(
                    type='Route',
                    status=status,
                    timestamp=datetime.now(),
                    gps_ref_id=loc_id,
                    route_ref=route,
                    deviceTag=device_tag,
                    state=device_tag.device.dealer.manufacturer.state
                )
                alert_written = True
            print(f"[Tracking][Perf]   route[{i}] id={route.id} pts={len(points)} status={status} took={(time.perf_counter()-_t_ri)*1000:.1f}ms", flush=True)

        # Invalidate cache so the next call reflects newly written alerts
        if alert_written:
            _route_alert_cache.pop(device_tag.id, None)

        print(f"[Tracking][Perf] process_route_alerts TOTAL={(time.perf_counter()-_t_route_start)*1000:.1f}ms", flush=True)

    except Exception as e:
        print(f"Error processing route alerts: {e}", flush=True)


def process_device_tracking_data(data_str, source="unknown"):
    """
    Main function to process device tracking data
    Used by both TCP server and MQTT deviceTracking topic
    """
    _t_total_start = time.perf_counter()
    # Close old database connections to prevent leaks
    close_old_connections()

    # For logging only: if we find a device_tag, replace the incoming default
    # registration string with the mapped vehicle_reg_no in the raw data_str.
    data_str_for_log = data_str

    # Special-case logging format sometimes received like:
    # $DL01AB1234,$866192070567266,$1.0.0,$1.0.1,$26.134123N91.803780E
    # Here the second field is IMEI; replace ONLY the first token based on IMEI.
    try:
        def _swap_reg_by_imei(match):
            imei_val = match.group(1)
            device = _get_device_by_imei(imei_val)
            if not device:
                return match.group(0)
            device_tag = _get_device_tag(device)
            reg_no = (getattr(device_tag, "vehicle_reg_no", None) or "").strip() if device_tag else ""
            if not reg_no:
                return match.group(0)
            return f"${reg_no},${imei_val}"

        data_str_for_log = re.sub(r"\$DL01AB1234,\$(\d{14,17})", _swap_reg_by_imei, data_str_for_log)
    except Exception:
        pass
    try:
        # Split data by $ delimiter
        data_parts = data_str.split('$')

        for part in data_parts:
            try:
                if part == "":
                    continue

                # Add $ prefix back
                formatted_data = '$' + part

                # Skip very small fragments but preserve them for logging
                if len(part) <= 4:
                    continue

                # Process GPS data
                gps_data = process_gps_data(formatted_data)

                if gps_data:
                    imei = gps_data['imei']

                    # Find device by IMEI (cached, TTL=120s)
                    _t0 = time.perf_counter()
                    device = _get_device_by_imei(imei)
                    _t1 = time.perf_counter()
                    print(f"#{imei}# -> Device: {device}", flush=True)
                    print(f"[Tracking][Perf] device_lookup={(_t1-_t0)*1000:.1f}ms", flush=True)

                    if device:
                        device_tag = _get_device_tag(device)
                        _t2 = time.perf_counter()
                        print(f"[Tracking][Perf] device_tag_lookup={(_t2-_t1)*1000:.1f}ms", flush=True)

                        if device_tag:
                            reg_no = (getattr(device_tag, "vehicle_reg_no", None) or "").strip()

                            

                            # Add device tag and remove IMEI/vehicle info
                            gps_data['device_tag'] = device_tag
                            gps_data.pop('imei', None)
                            gps_data.pop('vehicle_registration_number', None)

                            # Save GPS data.
                            # Note: GPSData post_save signal already performs enrichment.
                            _t3 = time.perf_counter()
                            gps_record = GPSData.objects.create(**gps_data)
                            _t4 = time.perf_counter()
                            print(f"[Tracking][Perf] gps_save={(_t4-_t3)*1000:.1f}ms  (includes post_save signal/geocoding)", flush=True)

                            # Process alerts
                            process_alerts(gps_data, gps_record.id)
                            _t5 = time.perf_counter()
                            print(f"[Tracking][Perf] process_alerts={(_t5-_t4)*1000:.1f}ms", flush=True)
                        else:
                            print(f"[{source}] No device tag found for device: {device}", flush=True)
                    else:
                        print(f"[{source}] No device found for IMEI: {imei}", flush=True)
                else:
                    print(f"[{source}] Invalid GPS data format:", formatted_data, flush=True)

            except Exception as e:
                print(f"[{source}] Data processing error:", e, flush=True)

    except Exception as e:
        print(f"[{source}] Data splitting error:", e, flush=True)

    # Log raw data (with DL01AB1234 replaced when device_tag is present)
    try:
        GPSDataLog.objects.create(raw_data=data_str_for_log)
    except Exception as e:
        print(f"Data logging error ({source}):", e, flush=True)
    finally:
        # Close any remaining database connections
        close_old_connections()
    print(f"[Tracking][Perf] TOTAL process_device_tracking_data={( time.perf_counter()-_t_total_start)*1000:.1f}ms source={source}", flush=True)


def process_emergency_data(data_str, source="unknown", publish_callback=None):
    """
    Main function to process emergency data
    Used by both EM server and MQTT deviceEM topic
    """
    try:
        # Close old database connections to prevent leaks
        close_old_connections()

        # For logging only: if we can resolve a device_tag from the EM payload,
        # replace the incoming default registration string in the raw data_str.
        data_str_for_log = data_str
        try:
            # Most common format: $,EPB,EMR,<imei>,...,DL01AB1234,...
            parts = data_str.split('$')
            for part in parts:
                if not part:
                    continue
                formatted_data = '$' + part
                fields = formatted_data.split(',')
                if len(fields) >= 4 and fields[0] == '$' and fields[1] == 'EPB':
                    imei = fields[3]
                    device = DeviceStock.objects.filter(imei__contains=str(imei)).last()
                    if device:
                        device_tag = DeviceTag.objects.filter(device=device,status = 'Owner_Final_OTP_Verified').last()
                        reg_no = (getattr(device_tag, "vehicle_reg_no", None) or "").strip() if device_tag else ""
                        if reg_no:
                            data_str_for_log = data_str.replace("DL01AB1234", reg_no)
                            break
        except Exception:
            # Never block EM processing due to log formatting
            data_str_for_log = data_str

        # Log raw data
        try:
            GPSemDataLog.objects.create(raw_data=data_str_for_log)
        except Exception as e:
            print(f"EM data logging error ({source}):", e, flush=True)
        
        # Split data by $ delimiter
        data_parts = data_str.split('$')
        
        for part in data_parts:
            try:
                if len(part) <= 4:
                    continue
                    
                # Add $ prefix back
                formatted_data = '$' + part
                
                print(f"[{source}] Processing EM data:", formatted_data, flush=True)
                
                # Process EM data
                data_list = formatted_data.split(',')
                
                if len(data_list) >= 18:
                    # Remove the first element if it's just '$'
                    if data_list[0] == '$':
                        data_list = data_list[1:]
                    
                    #print(f"[{source}] EM data list:", data_list, flush=True)
                    
                    # Use the new EM data processor instead of create_from_string
                    location = process_em_data(formatted_data, publish_callback=publish_callback)
                    
                    if location is not None:
                        # location is already saved in process_em_data
                        #print(f"[{source}] EM location processed successfully:", location, flush=True)
                        pass
                        
                        # You can add EM-specific alert processing here if needed
                        # process_em_alerts(location)
                        
                    else:
                        #print(f"[{source}] Failed to create EM location from data", flush=True)
                        pass
                else:
                    print(f"[{source}] Invalid EM data format (insufficient fields):", formatted_data, flush=True)
                    
            except Exception as e:
                print(f"[{source}] EM data processing error:", e, flush=True)
                
    except Exception as e:
        print(f"[{source}] Main EM processing error:", e, flush=True)
    finally:
        # Close any remaining database connections
        close_old_connections()


def generate_random_ble_key(length=15):
    """Generate a random BLE key using Base32 alphabet (no padding).

    Keys are 15 characters long and use the character set
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567".

    Args:
        length (int): Length of the key. Default 15.

    Returns:
        str: A random uppercase Base32-like string of length `length`.
    """
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_ble_keys_for_device(imei):
    """
    Generate 30 BLE keys for a device IMEI
    Returns list of key strings
    """
    try:
        # First, deactivate any existing keys for this IMEI
        BleKey.objects.filter(imei=imei).update(active=False)
        
        # Generate 30 new keys (15-char Base32 alphabet).
        # Keyspace is 32^15 (~3.8e22), so collisions against the existing table
        # or within this batch are astronomically unlikely — the `key` column's
        # unique constraint is the real backstop, not a per-key existence check.
        # bulk_create replaces what used to be up to 61 sequential queries
        # (1 exists + 1 create per key) with 2.
        keys = set()
        while len(keys) < 30:
            keys.add(generate_random_ble_key(15))
        keys = list(keys)

        BleKey.objects.bulk_create([
            BleKey(key=k, imei=imei, active=True) for k in keys
        ])

        print(f"Generated {len(keys)} BLE keys for device {imei}", flush=True)
        return keys
        
    except Exception as e:
        print(f"Error generating BLE keys for {imei}: {e}", flush=True)
        return []


def get_device_response_data(imei):
    """
    Get device response data with SOS status.

    BLE key issuance is disabled here for now (each device needing keys was
    costing 60+ sequential DB round-trips per tracking message). BleKey model
    and generate_ble_keys_for_device() are untouched, so this can call them
    again to re-enable BLE keys later.
    """
    return {
        "sos": 0,  # Default SOS status
        "keys": [],
    }