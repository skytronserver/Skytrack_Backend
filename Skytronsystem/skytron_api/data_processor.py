"""
Common data processing module for GPS tracking and Emergency data
This module contains shared processing logic for TCP, MQTT, and EM servers
"""

import re
import json
import time
import string
import secrets
from datetime import datetime, timezone
import pytz
from django.db import close_old_connections
from django.db.models import Max
from django.utils import timezone as django_timezone
from geopy.distance import geodesic

from skytron_api.models import (
    GPSData, GPSDataLog, DeviceTag, DeviceStock, Route, AlertsLog,
    EMGPSLocation, GPSemDataLog, User, BleKey
)

# Timezone setup
gmt_timezone = pytz.timezone('GMT')
ist_timezone = pytz.timezone('Asia/Kolkata')


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
                    'ignition_status': groups[27][:1],  # 1 (ignition status, limit to 1 char)
                    'main_power_status': groups[24][:1], # 1 (GPRS status, using as main power)
                    'main_input_voltage': float(groups[25]), # 11.6 (main power voltage)
                    'internal_battery_voltage': float(groups[26]), # 4.2 (backup battery)
                    'emergency_status': '0',     # Default, not in new format
                    'box_tamper_alert': 'O',     # Default Open, not in new format
                    'gsm_signal_strength': groups[23][:10], # 1 (GSM signal strength)
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
                    'digital_output_status': '00',  # Default, not explicitly in new format
                    'frame_number': int(groups[47]) if len(groups) > 47 and groups[47].isdigit() else 0, # 10 (odometer reading)
                    'odometer': float(groups[48]) if len(groups) > 48 and groups[48].replace('.', '').isdigit() else 0.0, # 000043
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


def process_em_data(data_str):
    """
    Process Emergency (EM) data from devices
    Supports new EPB format: $,EPB,EMR,860269065287047,NM,24102025051128,A,26.193007,N,91.752815,E,90.6,0.0,0.000,G,DL01AB1234,9401633421,*,04
    Used by EM server and MQTT deviceEM topic
    """
    try:
        data_list = data_str.split(',')
        
        # New EPB format parsing
        if len(data_list) >= 17 and data_list[0] == '$' and data_list[1] == 'EPB':
            try:
                # Parse the timestamp (DDMMYYYYHHMMSS format)
                timestamp_str = data_list[5]  # 24102025062501
                print(f"[MQTT] Parsing timestamp: {timestamp_str}", flush=True)
                
                if len(timestamp_str) == 14:
                    # Extract components: DD MM YYYY HH MM SS
                    day = timestamp_str[0:2]      # 24
                    month = timestamp_str[2:4]    # 10
                    year = timestamp_str[4:8]     # 2025
                    hour = timestamp_str[8:10]    # 06
                    minute = timestamp_str[10:12] # 25
                    second = timestamp_str[12:14] # 01
                    
                    print(f"[MQTT] Extracted: {day}/{month}/{year} {hour}:{minute}:{second}", flush=True)
                    
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
                    print(f"[MQTT] Parsed datetime: {ist_datetime}", flush=True)
                    
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
                        device = DeviceStock.objects.filter(imei__contains=str(imei)).last()
                        print(f"#{imei}# -> Device: {device}", flush=True)
                        
                        device_tag = None
                        if device:
                            device_tag = DeviceTag.objects.filter(device=device).last()
                            print(f"Device tag found: {device_tag}", flush=True)
                        else:
                            print(f"No device found for IMEI: {imei}", flush=True)
                        
                        # Create EMGPSLocation directly
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
                            vehicle_reg_no=data_list[15],     # DL01AB1234
                            reply_mob_no=data_list[16] if len(data_list) > 16 else '9401633421', # phone
                            device_tag=device_tag             # DeviceTag or None
                        )
                        
                        print(f"[MQTT] EM location created successfully: {location}", flush=True)
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


def create_alert(alert_type, status, loc_id, device_tag):
    """Create an alert entry"""
    try:
        AlertsLog.objects.create(
            type=alert_type,
            status=status,
            timestamp=datetime.now(),
            gps_ref_id=loc_id,
            deviceTag=device_tag,
            state=device_tag.device.dealer.manufacturer.state
        )
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

        # Fetch last alerts for non-route alerts
        last_alerts = (
            AlertsLog.objects.filter(deviceTag=device_tag)
            .exclude(type="Route")
            .values('type')
            .annotate(latest_timestamp=Max('timestamp'))
        )

        lastnormal_alerts = AlertsLog.objects.filter(
            deviceTag=device_tag,
            type__in=[entry['type'] for entry in last_alerts],
            timestamp__in=[entry['latest_timestamp'] for entry in last_alerts]
        )

        # Emergency Alert
        if packet_type == "EA":
            alert_type = "Em"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)

        # Engine/Ignition Alerts
        if gps_data["ignition_status"] == "1":
            alert_type = "Eng"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)

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
                        ot_last = lastnormal_alerts.filter(type="Overtime").last()
                        if not ot_last or (ot_last.status or "") != "in":
                            create_alert("Overtime", "in", loc_id, device_tag)
                # If no working hours configured, skip Overtime
            except Exception as _e:
                print(f"Overtime check error: {_e}", flush=True)
        elif gps_data["ignition_status"] == "0":
            alert_type = "Eng"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

            # Close Overtime on engine off
            try:
                ot_last = lastnormal_alerts.filter(type="Overtime").last()
                if ot_last and (ot_last.status or "") == "in":
                    create_alert("Overtime", "out", loc_id, device_tag)
            except Exception as _e:
                print(f"Overtime close error: {_e}", flush=True)

        # Speed Alerts
        if gps_data["speed"] > 80:
            alert_type = "OverSpeed"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["speed"] <= 80:
            alert_type = "OverSpeed"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # Internal Battery Alerts
        if gps_data["internal_battery_voltage"] < 3:
            alert_type = "LowIntBat"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["internal_battery_voltage"] >= 3:
            alert_type = "LowIntBat"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # External Battery Alerts
        if gps_data["main_input_voltage"] < 8:
            alert_type = "LowExtBat"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["main_input_voltage"] > 9:
            alert_type = "LowExtBat"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # Battery Disconnect Alerts
        if gps_data["main_input_voltage"] < 2:
            alert_type = "ExtBatDiscnt"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["main_input_voltage"] >= 2:
            alert_type = "ExtBatDiscnt"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # Box Tamper Alerts
        if gps_data["box_tamper_alert"] == "C":
            alert_type = "BoxTemp"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "out":
                create_alert(alert_type, "in", loc_id, device_tag)
        elif gps_data["box_tamper_alert"] == "O":
            alert_type = "BoxTemp"
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status == "in":
                create_alert(alert_type, "out", loc_id, device_tag)

        # GPS Loss Alerts
        try:
            gps_fix_ok = str(gps_data.get("gps_status", "")).strip() == "1"
        except Exception:
            gps_fix_ok = False
        alert_type = "GPSLoss"
        desired_status = "out" if gps_fix_ok else "in"
        al = lastnormal_alerts.filter(type=alert_type).last()
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
        al = lastnormal_alerts.filter(type=alert_type).last()
        if not al or (al.status or "") != desired_status:
            create_alert(alert_type, desired_status, loc_id, device_tag)

        # Alert ID based alerts
        alert_mappings = {
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
        
  

        if alert_id in alert_mappings:
            alert_type, status = alert_mappings[alert_id]
            al = lastnormal_alerts.filter(type=alert_type).last()
            if not al or al.status != status:
                create_alert(alert_type, status, loc_id, device_tag)

        # Route Alerts
        process_route_alerts(gps_data, loc_id, device_tag, lat, lon)

    except Exception as e:
        print(f"Error processing alerts: {e}", flush=True)


def process_route_alerts(gps_data, loc_id, device_tag, lat, lon):
    """Process route-based alerts"""
    try:
        # Fetch active routes associated with the device
        routes = Route.objects.filter(status='Active', device=device_tag.device)
        
        # Fetch last route alerts
        last_alerts = AlertsLog.objects.filter(
            deviceTag=device_tag, 
            type="Route"
        ).order_by('type', 'route_ref', '-timestamp')

        # Create a dictionary to store the last alert for each route
        last_alert_map = {}
        for alert in last_alerts:
            key = (alert.type, alert.route_ref.id if alert.route_ref else None)
            if key not in last_alert_map:
                last_alert_map[key] = alert

        print(f"Routes found: {len(routes)}", flush=True)
        
        for route in routes:
            r = route.route  # Route string containing coordinates
            points = json.loads(r)  # Convert route string into a list of points
            status = "out"  # Default status

            # Check if any point in the route is within 100 meters
            for point in points[0:-1]:
                route_lon, route_lat, _ = point
                distance = geodesic((lat, lon), (route_lat, route_lon)).meters
                if distance <= 100:
                    status = "in"
                    break

            # Determine if a new alert needs to be created
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

    except Exception as e:
        print(f"Error processing route alerts: {e}", flush=True)


def process_device_tracking_data(data_str, source="unknown"):
    """
    Main function to process device tracking data
    Used by both TCP server and MQTT deviceTracking topic
    """
    try:
        # Close old database connections to prevent leaks
        close_old_connections()
        
        # Log raw data
        try:
            GPSDataLog.objects.create(raw_data=data_str)
        except Exception as e:
            print(f"Data logging error ({source}):", e, flush=True)

        # Split data by $ delimiter
        data_parts = data_str.split('$')
        
        for part in data_parts:
            try:
                if len(part) <= 4:
                    continue
                    
                # Add $ prefix back
                formatted_data = '$' + part
                
                # Process GPS data
                gps_data = process_gps_data(formatted_data)
                
                if gps_data:
                    imei = gps_data['imei']
                    
                    # Find device by IMEI
                    device = DeviceStock.objects.filter(imei__contains=str(imei)).last()
                    print(f"#{imei}# -> Device: {device}", flush=True)
                    
                    if device:
                        device_tag = DeviceTag.objects.filter(device=device).last()
                        
                        if device_tag:
                            # Add device tag and remove IMEI/vehicle info
                            gps_data['device_tag'] = device_tag
                            gps_data.pop('imei', None)
                            gps_data.pop('vehicle_registration_number', None)
                            
                            # Save GPS data
                            gps_record = GPSData.objects.create(**gps_data)
                            gps_record.save()
                            
                            # Process alerts
                            process_alerts(gps_data, gps_record.id)
                            
                            print(f"[{source}] GPS data processed:", formatted_data, flush=True)
                            print(f"[{source}] GPS record created:", gps_data, flush=True)
                        else:
                            print(f"[{source}] No device tag found for device: {device}", flush=True)
                    else:
                        print(f"[{source}] No device found for IMEI: {imei}", flush=True)
                else:
                    print(f"[{source}] Invalid GPS data format:", formatted_data, flush=True)
                    
            except Exception as e:
                print(f"[{source}] Data processing error:", e, flush=True)
                
    except Exception as e:
        print(f"[{source}] Main processing error:", e, flush=True)
    finally:
        # Close any remaining database connections
        close_old_connections()


def process_emergency_data(data_str, source="unknown"):
    """
    Main function to process emergency data
    Used by both EM server and MQTT deviceEM topic
    """
    try:
        # Close old database connections to prevent leaks
        close_old_connections()
        
        # Log raw data
        try:
            GPSemDataLog.objects.create(raw_data=data_str)
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
                    
                    print(f"[{source}] EM data list:", data_list, flush=True)
                    
                    # Use the new EM data processor instead of create_from_string
                    location = process_em_data(formatted_data)
                    
                    if location is not None:
                        # location is already saved in process_em_data
                        print(f"[{source}] EM location processed successfully:", location, flush=True)
                        
                        # You can add EM-specific alert processing here if needed
                        # process_em_alerts(location)
                        
                    else:
                        print(f"[{source}] Failed to create EM location from data", flush=True)
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
        
        # Generate 30 new keys (15-char Base32 alphabet)
        keys = []
        for i in range(30):
            key_value = generate_random_ble_key(15)
            
            # Ensure uniqueness
            while BleKey.objects.filter(key=key_value).exists():
                key_value = generate_random_ble_key(15)
            
            # Create the BLE key
            ble_key = BleKey.objects.create(
                key=key_value,
                imei=imei,
                active=True
            )
            keys.append(key_value)
            
        print(f"Generated {len(keys)} BLE keys for device {imei}", flush=True)
        return keys
        
    except Exception as e:
        print(f"Error generating BLE keys for {imei}: {e}", flush=True)
        return []


def get_device_response_data(imei):
    """
    Get device response data with SOS status and BLE keys
    """
    try:
        # Check if we have active BLE keys for this device
        active_keys = BleKey.objects.filter(imei=imei, active=True).order_by('entry_time')

        # Helper: validate key is 15-char using Base32 alphabet
        def _is_valid_b32_15(s: str) -> bool:
            if not s or len(s) != 15:
                return False
            alphabet = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
            return all(c in alphabet for c in s.upper())

        count = active_keys.count()
        need_regen = count != 30
        keys_list = []
        if not need_regen:
            # Validate each key for new format
            for k in active_keys:
                val = (k.key or '').strip().upper()
                if not _is_valid_b32_15(val):
                    need_regen = True
                    break
                keys_list.append(val)

        if need_regen:
            print(f"Device {imei} needs new BLE keys (current: {count}); regenerating 15-char Base32 keys", flush=True)
            keys = generate_ble_keys_for_device(imei)
        else:
            keys = keys_list
            print(f"Using existing 15-char Base32 BLE keys for device {imei}", flush=True)
        
        # Create response data
        response_data = {
            "sos": 0,  # Default SOS status
            "keys": keys
        }
        
        return response_data
        
    except Exception as e:
        print(f"Error getting device response data for {imei}: {e}", flush=True)
        return {
            "sos": 0,
            "keys": []
        }