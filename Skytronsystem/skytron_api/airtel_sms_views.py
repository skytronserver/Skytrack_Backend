"""
Incoming SMS pushed by Airtel's SMS gateway.

    POST /api/airtel-sms/receive/    Airtel -> backend, one SMS or a list of SMS per call
    GET  /api/airtel-sms/list/       superadmin, filtered + paginated

The POST needs no login, but every call must prove it knows the key shared
with Airtel, in one of two ways:

    X-Api-Key:   <key>
  or
    X-Signature: hex( HMAC-SHA256( key, raw request body ) )

For now the SMS is only logged (AirtelSmsInLog) and acknowledged; nothing
acts on its text yet.

This path is exempt from the input guard (an SMS may hold any text) and from
the global per-IP rate limit (the gateway sends everything from a few
addresses) - see input_guard.py and rate_limit.py. The text is stored as-is,
so anything that shows it must render it as plain text.

Settings (env):
    AIRTEL_SMS_API_KEYS     comma-separated keys (several allowed for rotation);
                            empty = the POST endpoint is disabled
    AIRTEL_SMS_ALLOWED_IPS  comma-separated IPs / CIDR ranges the gateway calls
                            from; empty = any address
"""
import hashlib
import hmac
import ipaddress
import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db.models import F, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .ble_sos_app_log_views import _Invalid, _date_param, _err, _int_param
from .models import AirtelSmsInLog

logger = logging.getLogger(__name__)

API_KEYS = [k.strip().encode() for k in os.environ.get('AIRTEL_SMS_API_KEYS', '').split(',') if k.strip()]


def _networks(raw):
    networks = []
    for item in raw.split(','):
        if item.strip():
            try:
                networks.append(ipaddress.ip_network(item.strip(), strict=False))
            except ValueError:
                logger.error(f"AIRTEL_SMS_ALLOWED_IPS: ignoring invalid entry {item.strip()!r}")
    return networks


_ALLOWED_RAW = os.environ.get('AIRTEL_SMS_ALLOWED_IPS', '')
ALLOWED_NETWORKS = _networks(_ALLOWED_RAW)
# A list that is set but has no valid entry must not open the endpoint to everyone.
IP_CHECK = bool(_ALLOWED_RAW.strip())

MAX_BODY_BYTES = 256 * 1024
MAX_BATCH = 100
MAX_NO_LEN = 20
MAX_TEXT_LEN = 2000
IST = dt_timezone(timedelta(hours=5, minutes=30))
_TIME_FORMATS = ('%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y%m%d%H%M%S')

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
ORDERINGS = {'received_at', '-received_at', 'sms_timestamp', '-sms_timestamp'}


# --------------------------------------------------------------------------
# POST /api/airtel-sms/receive/
# --------------------------------------------------------------------------

def _caller_ip(request):
    """
    Address that connected to our proxy. The proxy appends it to
    X-Forwarded-For, so it is the last entry; earlier entries come from the
    caller and can be forged.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    raw = forwarded.split(',')[-1].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def _ip_allowed(ip):
    if not IP_CHECK:
        return True
    return bool(ip) and any(ipaddress.ip_address(ip) in net for net in ALLOWED_NETWORKS)


def _authorised(request, body):
    api_key = request.META.get('HTTP_X_API_KEY', '').strip().encode()
    if api_key:
        return any(hmac.compare_digest(k, api_key) for k in API_KEYS)
    signature = request.META.get('HTTP_X_SIGNATURE', '').strip().lower()
    if signature.startswith('sha256='):
        signature = signature[7:]
    if signature:
        return any(hmac.compare_digest(hmac.new(k, body, hashlib.sha256).hexdigest(), signature)
                   for k in API_KEYS)
    return False


def _text(data, key, max_len, required=False):
    value = data.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)                 # a number sent unquoted
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise _Invalid(f'{key} must be text.')
    if required and not value.strip():
        raise _Invalid(f'{key} is required.')
    if len(value) > max_len:
        raise _Invalid(f'{key} must be at most {max_len} characters.')
    return value


def _parse_sms_time(value):
    """Best effort: an unreadable time must not lose the SMS (the raw value is kept)."""
    if isinstance(value, str) and value.strip().replace('.', '', 1).isdigit() and len(value.strip()) != 14:
        value = float(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 1e11 else value    # epoch ms or seconds
        try:
            return datetime.fromtimestamp(seconds, tz=dt_timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        parsed = parse_datetime(value)
    except ValueError:
        parsed = None
    for fmt in _TIME_FORMATS:
        if parsed:
            break
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            pass
    if parsed is None:
        return None
    # Airtel is an Indian gateway: a time without a zone is IST.
    return parsed if timezone.is_aware(parsed) else parsed.replace(tzinfo=IST)


def _clean_payload(data):
    if not isinstance(data, dict):
        raise _Invalid('Each SMS must be a JSON object.')
    if '\\u0000' in json.dumps(data):
        raise _Invalid('Body must not contain NUL characters.')

    sms_text = _text(data, 'sms_text', MAX_TEXT_LEN)
    char_length = data.get('char_length')
    if char_length in (None, ''):
        char_length = len(sms_text)
    else:
        try:
            char_length = int(str(char_length).strip())
        except ValueError:
            raise _Invalid('char_length must be a whole number.')
        if not 0 <= char_length <= 100000:
            raise _Invalid('char_length must be between 0 and 100000.')

    timestamp = data.get('sms_timestamp')
    return {
        'sender_no': _text(data, 'sender_no', MAX_NO_LEN, required=True).strip(),
        'receiver_no': _text(data, 'receiver_no', MAX_NO_LEN, required=True).strip(),
        'sms_text': sms_text,
        'char_length': char_length,
        'sms_timestamp': _parse_sms_time(timestamp),
        'sms_timestamp_raw': '' if timestamp is None else str(timestamp)[:64],
        'raw_payload': data,
    }


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def airtel_sms_receive(request):
    """POST /api/airtel-sms/receive/  (X-Api-Key or X-Signature; see module docstring)
    JSON or form-encoded:
    {
      "sms_timestamp": "2026-10-12 14:05:31", "sender_no": "919876543210",
      "receiver_no": "919000012345", "sms_text": "HELLO", "char_length": 5
    }
    or a JSON list of up to MAX_BATCH such objects. A list is saved as a
    whole or not at all: one invalid SMS rejects the call.
    """
    if not API_KEYS:
        return _err('Not available.', status.HTTP_503_SERVICE_UNAVAILABLE)

    ip = _caller_ip(request)
    body = request.body
    if len(body) > MAX_BODY_BYTES:
        return _err('Request too large.', status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if not _authorised(request, body):
        return _err('Invalid or missing key.', status.HTTP_401_UNAUTHORIZED)
    if not _ip_allowed(ip):
        logger.warning(f"Airtel SMS: valid key from address not in AIRTEL_SMS_ALLOWED_IPS: {ip}")
        return _err('Forbidden.', status.HTTP_403_FORBIDDEN)

    try:
        if 'json' in (request.content_type or '').lower():
            payload = json.loads(body.decode('utf-8'))
        else:
            payload = request.POST.dict()
    except (ValueError, UnicodeDecodeError):
        return _err('Body must be valid JSON.', status.HTTP_400_BAD_REQUEST)

    is_batch = isinstance(payload, list)
    items = payload if is_batch else [payload]
    if not 1 <= len(items) <= MAX_BATCH:
        return _err(f'A list must hold 1 to {MAX_BATCH} SMS.', status.HTTP_400_BAD_REQUEST)
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')[:255]
    logs = []
    for index, item in enumerate(items):
        try:
            data = _clean_payload(item)
        except _Invalid as e:
            if is_batch:
                return _err(f'SMS {index}: {e}', status.HTTP_400_BAD_REQUEST, index=index)
            return _err(str(e), status.HTTP_400_BAD_REQUEST)
        logs.append(AirtelSmsInLog(source_ip=ip, forwarded_for=forwarded_for, **data))

    logs = AirtelSmsInLog.objects.bulk_create(logs)
    if is_batch:
        return Response({'status': 'success', 'message': f'{len(logs)} SMS received.',
                         'count': len(logs), 'ids': [log.id for log in logs]})
    return Response({'status': 'success', 'message': 'SMS received.', 'id': logs[0].id})


# --------------------------------------------------------------------------
# GET /api/airtel-sms/list/
# --------------------------------------------------------------------------

def _row(log):
    return {
        'id': log.id,
        'sender_no': log.sender_no,
        'receiver_no': log.receiver_no,
        'sms_text': log.sms_text,
        'char_length': log.char_length,
        'sms_timestamp': log.sms_timestamp,
        'sms_timestamp_raw': log.sms_timestamp_raw,
        'source_ip': log.source_ip,
        'forwarded_for': log.forwarded_for,
        'received_at': log.received_at,
        'raw_payload': log.raw_payload,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def airtel_sms_list(request):
    """GET /api/airtel-sms/list/
        ?sender_no=98765 &receiver_no=919000012345 &source_ip=... &date_from=2026-10-01
        &date_to=2026-10-12 &search=... &ordering=-received_at &page=1 &page_size=50
    date_from/date_to filter on received_at; sender_no and receiver_no are partial matches.
    """
    if getattr(request.user, 'role', None) != 'superadmin':
        return _err('Only superadmin can access this.', status.HTTP_403_FORBIDDEN)

    p = request.GET
    try:
        page = _int_param(request, 'page', 1, 1, 100000)
        page_size = _int_param(request, 'page_size', DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
        date_from = _date_param(request, 'date_from')
        date_to = _date_param(request, 'date_to', end_of_day=True)
    except _Invalid as e:
        return _err(str(e), status.HTTP_400_BAD_REQUEST)

    ordering = p.get('ordering') or '-received_at'
    if ordering not in ORDERINGS:
        return _err(f"ordering must be one of: {', '.join(sorted(ORDERINGS))}.", status.HTTP_400_BAD_REQUEST)

    qs = AirtelSmsInLog.objects.all()
    sender = (p.get('sender_no') or '').strip().lstrip('+')
    if sender:
        qs = qs.filter(sender_no__icontains=sender)
    receiver = (p.get('receiver_no') or '').strip().lstrip('+')
    if receiver:
        qs = qs.filter(receiver_no__icontains=receiver)
    source_ip = (p.get('source_ip') or '').strip()
    if source_ip:
        try:
            qs = qs.filter(source_ip=str(ipaddress.ip_address(source_ip)))
        except ValueError:
            return _err('source_ip must be an IP address.', status.HTTP_400_BAD_REQUEST)
    if date_from:
        qs = qs.filter(received_at__gte=date_from)
    if date_to:
        qs = qs.filter(received_at__lte=date_to)
    search = (p.get('search') or '').strip()[:100]
    if search:
        qs = qs.filter(Q(sms_text__icontains=search) | Q(sender_no__icontains=search)
                       | Q(receiver_no__icontains=search))

    total = qs.count()
    field = F(ordering.lstrip('-'))
    qs = qs.order_by(field.desc(nulls_last=True) if ordering.startswith('-') else field.asc(nulls_last=True), '-id')
    start = (page - 1) * page_size
    rows = [_row(log) for log in qs[start:start + page_size]]

    return Response({
        'status': 'success',
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total else 0,
        },
        'data': rows,
    })
