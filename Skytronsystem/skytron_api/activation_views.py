from datetime import datetime
from typing import Optional

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ActivationCommandReply, DeviceStock, DeviceTag

_MIN_FIELDS = 12


def _digits_only(phone: str) -> str:
    return ''.join(c for c in phone if c.isdigit())


def _phone_matches(incoming: str, stored: Optional[str]) -> bool:
    if not stored:
        return False
    a, b = _digits_only(incoming), _digits_only(stored)
    return a == b or a.endswith(b) or b.endswith(a)


def _parse_raw_message(raw_message: str):
    """
    Handles two formats:

    New (From-header embedded):
        From : +919101033201()
        ACTVR,123321,MAPW,1.0.4,...

    Legacy (ACTVR line only):
        ACTVR,123321,MAPW,1.0.4,...

    Returns (actvr_line, incoming_from_no).
    - actvr_line       : the comma-separated ACTVR data string
    - incoming_from_no : cleaned phone number, or '0000000000' if absent
    """
    actvr_line = None
    incoming_from_no = '0000000000'

    for line in raw_message.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith('FROM'):
            # Extract everything after the first ':'
            phone_raw = line.split(':', 1)[1].strip() if ':' in line else line[4:].strip()
            # Remove +91 country-code prefix if present
            if phone_raw.startswith('+91'):
                phone_raw = phone_raw[3:]
            # Keep digits only (strips trailing "()" and any other chars)
            digits = _digits_only(phone_raw)
            if digits:
                incoming_from_no = digits

        elif line.startswith('ACTVR'):
            actvr_line = line

    return actvr_line, incoming_from_no


@api_view(['POST'])
@permission_classes([AllowAny])
def receive_activation_command_reply(request):
    """
    Public endpoint called by the SMS gateway when a device sends an ACTVR reply.

    Expected body:
        raw_message – full message from gateway, which may include a "From" header:

            From : +919101033201()
            ACTVR,123321,MAPW,1.0.4,866192076850302,...

        or just the bare ACTVR line (legacy):

            ACTVR,123321,MAPW,1.0.4,866192076850302,...

        incoming_from_no – (optional) overrides the phone number extracted from
                           the message. Defaults to '0000000000' if neither the
                           header nor this field provides a number.
    """
    raw_message = request.data.get('raw_message', '').strip()
    if not raw_message:
        return Response({'error': 'raw_message is required.'}, status=400)

    # Parse the From-header and ACTVR line out of the full message
    actvr_line, extracted_no = _parse_raw_message(raw_message)

    # Allow explicit override via request field; fall back to extracted, then default
    override_no = (request.data.get('incoming_from_no', '') or '').strip()
    incoming_from_no = _digits_only(override_no) if override_no else extracted_no

    if not actvr_line:
        return Response({'error': 'No ACTVR line found in message.'}, status=400)

    fields = [f.strip() for f in actvr_line.split(',')]

    if len(fields) < _MIN_FIELDS or fields[0] != 'ACTVR':
        return Response({'error': 'Invalid ACTVR message format.'}, status=400)

    code = fields[1]   # activation code echoed by device (stored in raw_message only)
    imei = fields[4]   # 15-digit IMEI

    # Parse timestamp – field[11] is "DDMMYYYY HHMMSS"
    try:
        ts_naive = datetime.strptime(fields[11], '%d%m%Y %H%M%S')
        ts = timezone.make_aware(ts_naive, timezone.utc)
    except (ValueError, IndexError):
        return Response({'error': 'Invalid or missing timestamp in message.'}, status=400)

    # 1. Match IMEI against DeviceStock
    try:
        device_stock = DeviceStock.objects.get(imei=imei)
    except DeviceStock.DoesNotExist:
        return Response(
            {'error': 'No device found matching the given IMEI.'},
            status=404,
        )

    # 2. Verify phone number against msisdn1 / msisdn2 (skip when no number was provided)
    if incoming_from_no != '0000000000' and not (
        _phone_matches(incoming_from_no, device_stock.msisdn1)
        or _phone_matches(incoming_from_no, device_stock.msisdn2)
    ):
        return Response(
            {'error': 'Incoming number does not match any MSISDN for this device.'},
            status=403,
        )

    # 3. Find the latest valid DeviceTag for this DeviceStock
    device_tag = (
        DeviceTag.objects.filter(device=device_stock)
        .exclude(status__in=['TagDeleted', 'untaged_after_failed_taging'])
        .order_by('-tagged')
        .first()
    )

    # 4. Store only the ACTVR data line (From-header stripped)
    entry = ActivationCommandReply.objects.create(
        imei=imei,
        device_tag=device_tag,
        raw_message=actvr_line,
        timestamp=ts,
        incoming_from_no=incoming_from_no,
    )

    # Build parsed fields for the response
    def _safe(idx, cast=str, default=None):
        try:
            return cast(fields[idx])
        except (IndexError, ValueError):
            return default

    lat_val = _safe(6, float)
    lat_dir = _safe(7)
    lon_val = _safe(8, float)
    lon_dir = _safe(9)
    latitude  = lat_val if lat_dir == 'N' else (-lat_val if lat_val else None)
    longitude = lon_val if lon_dir == 'E' else (-lon_val if lon_val else None)

    parsed = {
        'command':          _safe(0),
        'esn_code':         _safe(1),
        'server_id':        _safe(2),
        'firmware_version': _safe(3),
        'imei':             _safe(4),
        'gps_fix':          _safe(5, int),
        'latitude':         latitude,
        'longitude':        longitude,
        'flag':             _safe(10, int),
        'timestamp_raw':    _safe(11),
        'altitude_m':       _safe(12, float),
        'speed':            _safe(13, float),
        'satellites':       _safe(14, int),
        'mcc':              _safe(15, int),
        'mnc':              _safe(16, int),
        'cell_id_hex':      _safe(17),
        'field_18':         _safe(18),
        'field_19':         _safe(19),
        'battery_voltage':  _safe(20, float),
        'field_21':         _safe(21),
        'field_22':         _safe(22),
    }

    return Response(
        {
            'id':               entry.id,
            'imei':             entry.imei,
            'device_tag_id':    entry.device_tag_id,
            'timestamp':        entry.timestamp,
            'incoming_from_no': entry.incoming_from_no,
            'parsed_message':   parsed,
            'message':          'Activation reply recorded.',
        },
        status=201,
    )
