"""
Vehicle OBD + GPS status: for a given IMEI, scan the raw GPSDataLog for the
latest PVT tracking packets, pull the OBD data block appended after the
packet's '*' terminator (RPM, Speed, ...), and derive an at-a-glance device
status (connectivity / speed-limit / VLTD) from the last N such packets.

A status is only reported "OK" when every one of the last N packets agrees
-- a single bad packet in the window is enough to flip it to the "not OK"
message.
"""
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .alert_stats_views import _scope_device_tags
from .data_processor import gmt_timezone, ist_timezone
from .device_data_health_views import _split_packets
from .device_inspector_views import _find_device_tag
from .models import DeviceTag, GPSDataLog
from .throttles import VehicleOBDStatusRateThrottle
from .views import _packet_fields, _is_pvt_packet, _extract_pvt_lat_lon

# Sample IMEI from the ARAI PVT packet format used to develop this endpoint --
# used as the default when the caller doesn't pass ?imei=.
DEFAULT_EXAMPLE_IMEI = '866192070567134'

# How many of the most recent PVT packets to evaluate the status over.
PACKET_WINDOW = 20

# Only packets received within this many minutes of "now" are scanned --
# anything older is not looked at, regardless of PACKET_WINDOW.
SCAN_WINDOW_MINUTES = 10

# Bounds the raw-log row scan within the SCAN_WINDOW_MINUTES cutoff (raw_data
# has no IMEI index, so a row cap keeps a high-frequency device cheap too).
ROW_SCAN_LIMIT = 500

# Speed-limit thresholds (km/h), per the OBD "SPD" field.
SPEED_FUNCTIONAL_BELOW = 30
SPEED_OVERSPEED_ABOVE = 30

# Literal value the device sends in place of real OBD telemetry when it has
# no OBD connection -- a packet carrying this is NOT a sign the OBD link is
# online, even though the '*' terminator does have data after it.
OBD_NULL_SENTINEL = 'OBD-NULL'


def _numeric(value):
    """Best-effort str -> int/float, else the original string, else None."""
    if value is None or value == '':
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    return int(f) if f.is_integer() else f


def _parse_pvt_packet(raw, imei):
    """
    Pull device/vehicle/OBD fields out of one PVT packet fragment.

    Returns None if the fragment isn't a PVT tracking packet for this exact
    IMEI. Otherwise returns a dict describing the packet.
    """
    if not _is_pvt_packet(raw):
        return None

    parts = _packet_fields(raw)
    try:
        idx = next(i for i, p in enumerate(parts) if p.upper() == 'PVT')
    except StopIteration:
        return None

    def _field(offset):
        pos = idx + offset
        return parts[pos] if 0 <= pos < len(parts) else None

    imei_field = _field(6)
    if not imei_field or imei_field != imei:
        return None

    gps_fix = _field(8)
    date_field = _field(9)
    time_field = _field(10)

    lat, lon = _extract_pvt_lat_lon(raw)
    gps_valid = lat is not None and lon is not None and gps_fix == '1'

    # The OBD block (RPM,SPD,CLT,...) is appended, comma-separated, after
    # the packet's own '*' terminator -- not part of the standard PVT field
    # layout, so it's pulled from the raw text rather than `parts`.
    obd_values = []
    star_pos = raw.rfind('*')
    if star_pos != -1:
        tail = raw[star_pos + 1:].strip()
        if tail.startswith(','):
            tail = tail[1:]
        tail = tail.strip()
        if tail:
            obd_values = [v.strip() for v in tail.split(',')]
    obd_present = len(obd_values) > 0
    obd_null = obd_present and obd_values[0].strip().upper() == OBD_NULL_SENTINEL
    # "online" means real OBD telemetry is coming through -- data present
    # after '*' AND it isn't the device's own "no OBD connection" sentinel.
    obd_online = obd_present and not obd_null

    packet_datetime = None
    try:
        if date_field and time_field and len(date_field) == 8 and len(time_field) == 6:
            gmt_dt = datetime.strptime(f'{date_field} {time_field}', '%d%m%Y %H%M%S')
            packet_datetime = gmt_timezone.localize(gmt_dt).astimezone(ist_timezone)
    except (ValueError, OverflowError):
        packet_datetime = None

    return {
        'vehicle_reg_no': _field(7),
        'latitude': float(lat) if lat is not None else None,
        'longitude': float(lon) if lon is not None else None,
        'gps_valid': gps_valid,
        'packet_datetime': packet_datetime,
        'obd_present': obd_present,
        'obd_online': obd_online,
        'obd_rpm': _numeric(obd_values[0]) if len(obd_values) > 0 else None,
        'obd_speed': _numeric(obd_values[1]) if len(obd_values) > 1 else None,
    }


def _speed_state(packet):
    if not packet['obd_present'] or packet['obd_speed'] is None:
        return 'anomaly'
    try:
        speed = float(packet['obd_speed'])
    except (TypeError, ValueError):
        return 'anomaly'
    if speed < SPEED_FUNCTIONAL_BELOW:
        return 'functional'
    if speed > SPEED_OVERSPEED_ABOVE:
        return 'overspeed'
    return 'anomaly'


def _vltd_state(packet):
    return 'active' if packet['gps_valid'] else 'gps_loss'


def _connectivity_state(packet):
    # OBD-NULL means the device has no OBD connection, not that it's online.
    return 'online' if packet['obd_online'] else 'offline'


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([VehicleOBDStatusRateThrottle])
def vehicle_obd_status_lookup(request):
    """
    GET /api/vehicle-obd-status/lookup/?imei=<imei>

    Scans PVT packets received in the last SCAN_WINDOW_MINUTES (10) minutes
    only -- anything older is ignored -- taking up to the latest
    PACKET_WINDOW (20) of them for the given IMEI, and returns:
      - device_data: fields extracted from the single most recent packet
        (IMEI, tagged vehicle reg no / type / category / owner, whether an
        OBD data block was present, OBD RPM/Speed, GPS validity, timestamp).
      - status: connectivity / speed-limit / VLTD status, each "OK" only if
        every packet found in that 10-minute window was OK for that check.
    """
    imei = (request.GET.get('imei') or DEFAULT_EXAMPLE_IMEI).strip()
    if not imei:
        return Response({'status': 'error', 'message': 'imei is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Public endpoint: RBAC-scope the device-tag search only for an
    # authenticated caller (matches their role's visibility); an anonymous
    # caller searches across all device tags.
    if request.user and request.user.is_authenticated:
        device_tags_qs, err = _scope_device_tags(request.user)
        if err:
            return err
    else:
        device_tags_qs = DeviceTag.objects.all()

    device_tag = _find_device_tag(device_tags_qs, imei)
    if not device_tag:
        return Response(
            {'status': 'error', 'message': f'No device found for IMEI {imei} in your scope'},
            status=status.HTTP_404_NOT_FOUND,
        )

    real_imei = device_tag.device.imei if device_tag.device else imei

    cutoff = timezone.now() - timedelta(minutes=SCAN_WINDOW_MINUTES)
    rows = (
        GPSDataLog.objects
        .filter(raw_data__contains=real_imei, timestamp__gte=cutoff)
        .order_by('-timestamp')
        .values_list('timestamp', 'raw_data')[:ROW_SCAN_LIMIT]
    )

    packets = []
    for log_timestamp, raw_data in rows:
        for frag in reversed(_split_packets(raw_data)):
            parsed = _parse_pvt_packet(frag, real_imei)
            if parsed is None:
                continue
            parsed['log_timestamp'] = log_timestamp
            packets.append(parsed)
            if len(packets) >= PACKET_WINDOW:
                break
        if len(packets) >= PACKET_WINDOW:
            break

    vehicle_type = device_tag.category.category if device_tag.category else None
    vehicle_category_code = device_tag.category_code.category_code if device_tag.category_code else None
    vehicle_owner_name = device_tag.vehicle_owner.company_name if device_tag.vehicle_owner else None

    base_device_data = {
        'device_imei': real_imei,
        'vehicle_reg_no': device_tag.vehicle_reg_no,
        'vehicle_type': vehicle_type,
        'vehicle_category_code': vehicle_category_code,
        'vehicle_owner_name': vehicle_owner_name,
    }

    if not packets:
        return Response({
            'status': 'success',
            'imei': real_imei,
            'packets_scanned': 0,
            'packets_window': PACKET_WINDOW,
            'scan_window_minutes': SCAN_WINDOW_MINUTES,
            'device_data': {
                **base_device_data,
                'obd_data_received': False,
                'obd_online': False,
                'obd_rpm': None,
                'obd_speed': None,
                'gps_valid': False,
                'latitude': None,
                'longitude': None,
                'last_data_timestamp': None,
            },
            'status_summary': {
                'connectivity_status': 'offline',
                'speed_limit_status': 'Speed limit anomaly detected',
                'vltd_status': 'offline',
            },
            'message': (
                f'No PVT packets found for IMEI {real_imei} within the last '
                f'{SCAN_WINDOW_MINUTES} minute(s).'
            ),
        })

    latest = packets[0]

    device_data = {
        **base_device_data,
        'vehicle_reg_no': device_tag.vehicle_reg_no or latest['vehicle_reg_no'],
        'obd_data_received': latest['obd_present'],
        'obd_online': latest['obd_online'],
        'obd_rpm': latest['obd_rpm'],
        'obd_speed': latest['obd_speed'],
        'gps_valid': latest['gps_valid'],
        'latitude': latest['latitude'],
        'longitude': latest['longitude'],
        'last_data_timestamp': latest['packet_datetime'] or latest['log_timestamp'],
    }

    speed_states = [_speed_state(p) for p in packets]
    vltd_states = [_vltd_state(p) for p in packets]
    connectivity_states = [_connectivity_state(p) for p in packets]

    if all(s == 'functional' for s in speed_states):
        speed_limit_status = 'Functional'
    elif all(s == 'overspeed' for s in speed_states):
        speed_limit_status = 'Overspeed detected'
    else:
        speed_limit_status = 'Speed limit anomaly detected'

    vltd_status = 'Active' if all(s == 'active' for s in vltd_states) else 'GPS Loss'
    connectivity_status = 'online' if all(s == 'online' for s in connectivity_states) else 'offline'

    packet_history = [
        {
            'timestamp': p['packet_datetime'] or p['log_timestamp'],
            'gps_valid': p['gps_valid'],
            'obd_data_received': p['obd_present'],
            'obd_online': p['obd_online'],
            'obd_rpm': p['obd_rpm'],
            'obd_speed': p['obd_speed'],
        }
        for p in packets
    ]

    return Response({
        'status': 'success',
        'imei': real_imei,
        'packets_scanned': len(packets),
        'packets_window': PACKET_WINDOW,
        'scan_window_minutes': SCAN_WINDOW_MINUTES,
        'device_data': device_data,
        'status_summary': {
            'connectivity_status': connectivity_status,
            'speed_limit_status': speed_limit_status,
            'vltd_status': vltd_status,
        },
        'packet_history': packet_history,
    })
