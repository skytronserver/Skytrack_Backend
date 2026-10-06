"""
Vehicle OBD + GPS status: for a given IMEI, scan the raw GPSDataLog for the
latest PVT tracking packets, pull the OBD data block appended after the
packet's '*' terminator (RPM, Speed, ...), and derive an at-a-glance device
status (connectivity / speed-limit / VLTD) from the last N such packets.

Each status uses its own rule over the scanned window:
  - connectivity_status: "online" if at least CONNECTIVITY_MIN_PACKETS of
    the scanned packets carry both RPM and SPD, else "offline".
  - speed_limit_status: classifies the single most recent packet's speed.
  - vltd_status: "Active" only if every one of the latest VLTD_LATEST_N
    packets has a structurally valid GPS fix, else "offline".
"""
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
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
SCAN_WINDOW_MINUTES = 5

# Bounds the raw-log row scan within the SCAN_WINDOW_MINUTES cutoff (raw_data
# has no IMEI index, so a row cap keeps a high-frequency device cheap too).
ROW_SCAN_LIMIT = 500

# connectivity_status is "online" once at least this many of the (up to
# PACKET_WINDOW) scanned packets carry both RPM and SPD -- a single
# corroborating packet isn't enough, but the device doesn't need every
# packet in the window to have it either.
CONNECTIVITY_MIN_PACKETS = 5

# vltd_status is "Active" only if every one of the latest this-many packets
# has a structurally valid GPS fix.
VLTD_LATEST_N = 5

# Speed-limit thresholds (km/h), per the OBD "SPD" field. Evaluated against
# the single most recent packet only.
SPEED_FUNCTIONAL_BELOW = 20
SPEED_OVERSPEED_ABOVE = 20

# device_data.gps_valid ("is the vehicle's location trustworthy right now")
# additionally requires the latest packet to have arrived within this many
# seconds of the request -- a structurally valid fix from a few minutes ago
# is stale, not current. Measured against the server's own receipt time
# (GPSDataLog.timestamp), not the packet's self-reported date/time, since
# the device's own clock can be garbage when it doesn't have a GPS lock.
GPS_FRESHNESS_SECONDS = 20

# connectivity_status and vltd_status additionally require the latest
# packet to have arrived within this many seconds of the request, on top
# of each status's own rule (CONNECTIVITY_MIN_PACKETS / VLTD_LATEST_N) --
# if nothing has come in this recently, both go "offline" regardless of
# how the last batch of packets looked. Measured against the server's own
# receipt time, same reasoning as GPS_FRESHNESS_SECONDS above.
STATUS_FRESHNESS_SECONDS = 15

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


def _parse_obd_tail(raw):
    """
    Pull RPM/SPD out of the OBD block appended after the packet's '*'
    terminator.

    Two formats have been seen in production:
      - "key:value" pairs, comma-separated, e.g. "RPM:0,SPD:0,CLT:0,..."
        (current format). The block can be incomplete/truncated -- fields
        can be missing or cut off mid-token -- so RPM/SPD are located by
        key rather than by position, and anything else is ignored.
      - a plain positional CSV list in header order (RPM,SPD,CLT,...), or
        the literal sentinel "OBD-NULL" when the device has no OBD
        connection at all (legacy format, kept for backward compatibility).

    Returns (obd_present, obd_null, obd_rpm, obd_speed).
    """
    star_pos = raw.rfind('*')
    if star_pos == -1:
        return False, False, None, None

    tail = raw[star_pos + 1:].strip()
    if tail.startswith(','):
        tail = tail[1:]
    tail = tail.strip()
    if not tail:
        return False, False, None, None

    tokens = [t.strip() for t in tail.split(',') if t.strip() != '']
    if not tokens:
        return False, False, None, None

    if len(tokens) == 1 and tokens[0].upper() == OBD_NULL_SENTINEL:
        return True, True, None, None

    if any(':' in t for t in tokens):
        values = {}
        for t in tokens:
            if ':' not in t:
                continue
            key, _, val = t.partition(':')
            values[key.strip().upper()] = val.strip()
        return True, False, _numeric(values.get('RPM')), _numeric(values.get('SPD'))

    # Legacy positional CSV -- RPM is index 0, SPD is index 1.
    rpm = tokens[0] if len(tokens) > 0 else None
    speed = tokens[1] if len(tokens) > 1 else None
    return True, False, _numeric(rpm), _numeric(speed)


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
    obd_present, _obd_null, obd_rpm, obd_speed = _parse_obd_tail(raw)
    # "online" specifically means BOTH RPM and SPD telemetry came through --
    # the rest of the OBD block can be incomplete/truncated/missing, that's
    # fine, but these two are what this endpoint reports on.
    obd_online = obd_rpm is not None and obd_speed is not None

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
        'obd_rpm': obd_rpm,
        'obd_speed': obd_speed,
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([VehicleOBDStatusRateThrottle])
def vehicle_obd_status_lookup(request):
    """
    GET /api/vehicle-obd-status/lookup/?imei=<imei>

    Scans PVT packets received in the last SCAN_WINDOW_MINUTES (5) minutes
    only -- anything older is ignored -- taking up to the latest
    PACKET_WINDOW (20) of them for the given IMEI, and returns:
      - device_data: fields extracted from the single most recent packet
        (IMEI, tagged vehicle reg no / type / category / owner, whether an
        OBD data block was present, OBD RPM/Speed, GPS validity, timestamp).
      - status: connectivity_status ("online" if >= CONNECTIVITY_MIN_PACKETS
        of the scanned packets have both RPM and SPD), speed_limit_status
        (classifies the latest packet's speed only), and vltd_status
        ("Active" only if the latest VLTD_LATEST_N packets are all
        GPS-valid, else "offline").
    """
    # H-3: superadmin only for now
    if getattr(request.user, 'role', None) != 'superadmin':
        return Response(
            {'status': 'error', 'message': 'You do not have access to this.'},
            status=status.HTTP_403_FORBIDDEN,
        )

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
                'device_reported_timestamp': None,
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
    latest_age_seconds = (timezone.now() - latest['log_timestamp']).total_seconds()
    gps_valid_now = latest['gps_valid'] and latest_age_seconds <= GPS_FRESHNESS_SECONDS
    # connectivity_status, speed_limit_status, and vltd_status all require
    # the latest packet to still be fresh -- if nothing has arrived in the
    # last STATUS_FRESHNESS_SECONDS, all three reflect that regardless of
    # how the rest of the window looked.
    data_fresh = latest_age_seconds <= STATUS_FRESHNESS_SECONDS

    device_data = {
        **base_device_data,
        'vehicle_reg_no': device_tag.vehicle_reg_no or latest['vehicle_reg_no'],
        'obd_data_received': latest['obd_present'],
        'obd_online': latest['obd_online'],
        'obd_rpm': latest['obd_rpm'],
        'obd_speed': latest['obd_speed'],
        'gps_valid': gps_valid_now,
        'latitude': latest['latitude'],
        'longitude': latest['longitude'],
        # Server receipt time -- authoritative. The device's own
        # self-reported date/time (see device_reported_timestamp) can be
        # garbage (seen: 2080, 2020) when it doesn't have a GPS lock, so it
        # is never used as the primary timestamp.
        'last_data_timestamp': latest['log_timestamp'],
        'device_reported_timestamp': latest['packet_datetime'],
    }

    # speed_limit_status: the latest packet's speed only -- stale data
    # (nothing within STATUS_FRESHNESS_SECONDS) is always an anomaly, no
    # matter what speed value the last-received packet happened to carry.
    if data_fresh:
        speed_state_latest = _speed_state(latest)
        speed_limit_status = {
            'functional': 'Functional',
            'overspeed': 'Overspeed detected',
        }.get(speed_state_latest, 'Speed limit anomaly detected')
    else:
        speed_limit_status = 'Speed limit anomaly detected'

    # connectivity_status: at least CONNECTIVITY_MIN_PACKETS of the scanned
    # packets (not necessarily consecutive) must carry both RPM and SPD.
    obd_full_count = sum(1 for p in packets if p['obd_online'])
    connectivity_status = 'online' if obd_full_count >= CONNECTIVITY_MIN_PACKETS and data_fresh else 'offline'

    # vltd_status: every one of the latest VLTD_LATEST_N packets must be
    # GPS-valid -- fewer packets than that in the window is also "offline"
    # (not enough recent data to call it Active).
    latest_n = packets[:VLTD_LATEST_N]
    vltd_status = (
        'Active'
        if len(latest_n) >= VLTD_LATEST_N and all(p['gps_valid'] for p in latest_n) and data_fresh
        else 'offline'
    )

    packet_history = [
        {
            'timestamp': p['log_timestamp'],
            'device_reported_timestamp': p['packet_datetime'],
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
