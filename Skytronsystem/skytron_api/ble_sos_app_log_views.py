"""
SOS feedback log from the mobile app that talks to the BLE device.

    POST /api/ble-sos/app-log/          app -> backend, one call per SOS press
    GET  /api/ble-sos/app-log/list/     superadmin, filtered + paginated

The POST needs no login, but every call must be signed with a secret built
into the app, so web pages and scripts without the secret are refused:

    X-App-Timestamp: <unix seconds>
    X-App-Nonce:     <16-64 random chars [A-Za-z0-9_-], new for every call>
    X-App-Signature: hex( HMAC-SHA256( secret, "<timestamp>.<nonce>.<sha256 hex of raw body>" ) )

The timestamp must be within BLE_SOS_MAX_SKEW seconds of server time and a
nonce is accepted once, so a captured request cannot be replayed. Calls that
carry an Origin header (i.e. made by a browser) are refused outright, and the
X-App-* headers are not in CORS_ALLOW_HEADERS, so a browser preflight fails.

Settings (env):
    BLE_SOS_APP_SECRETS     comma-separated secrets (several allowed for rotation);
                            empty = the POST endpoint is disabled
    BLE_SOS_MAX_SKEW        allowed clock difference in seconds (default 300)
    BLE_SOS_PHONE_LIMIT     calls per phone per window (default 3)
    BLE_SOS_IP_LIMIT        calls per IP per window (default 60; carrier NAT)
    BLE_SOS_WINDOW_SECONDS  rate limit window (default 300)
"""
import hashlib
import hmac
import json
import logging
import math
import os
import re
import time
from datetime import datetime, time as dtime, timezone as dt_timezone

from django.core.cache import cache
from django.db.models import F, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .models import BleSosAppLog
from .rate_limit import _client_ip

logger = logging.getLogger(__name__)

APP_SECRETS = [s.strip().encode() for s in os.environ.get('BLE_SOS_APP_SECRETS', '').split(',') if s.strip()]
MAX_SKEW = int(os.environ.get('BLE_SOS_MAX_SKEW') or 300)
PHONE_LIMIT = int(os.environ.get('BLE_SOS_PHONE_LIMIT') or 3)
IP_LIMIT = int(os.environ.get('BLE_SOS_IP_LIMIT') or 60)
WINDOW_SECONDS = int(os.environ.get('BLE_SOS_WINDOW_SECONDS') or 300)

MAX_BODY_BYTES = 16 * 1024
MAX_CELLS = 10
MAX_CELL_KEYS = 15

_RE_MAC = re.compile(r'^[0-9A-F]{2}([:-]?)[0-9A-F]{2}(?:\1[0-9A-F]{2}){4}$')
_RE_REG_NO = re.compile(r'^[A-Z0-9]{4,15}$')
_RE_PHONE_ID = re.compile(r'^[A-Za-z0-9._:-]{4,128}$')
_RE_MOBILE = re.compile(r'^\d{10,15}$')
_RE_NONCE = re.compile(r'^[A-Za-z0-9_-]{16,64}$')
_RE_CELL_KEY = re.compile(r'^[A-Za-z_]{1,20}$')
_RE_VERSION = re.compile(r'^[A-Za-z0-9._+-]{1,30}$')

SOS_TYPES = {code for code, _ in BleSosAppLog.SOS_TYPE_CHOICES}

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
ORDERINGS = {'received_at', '-received_at', 'event_time', '-event_time'}


class _Invalid(Exception):
    pass


def _err(message, code, **extra):
    return Response({'status': 'error', 'message': message, **extra}, status=code)


# --------------------------------------------------------------------------
# POST /api/ble-sos/app-log/
# --------------------------------------------------------------------------

def _check_signature(request, body):
    """Return an error Response, or None when the call is signed by the app."""
    ts_raw = request.META.get('HTTP_X_APP_TIMESTAMP', '')
    nonce = request.META.get('HTTP_X_APP_NONCE', '')
    signature = request.META.get('HTTP_X_APP_SIGNATURE', '').strip().lower()
    if not (ts_raw.isdigit() and _RE_NONCE.match(nonce) and signature):
        return _err('Forbidden.', status.HTTP_403_FORBIDDEN)

    now = int(time.time())
    if abs(now - int(ts_raw)) > MAX_SKEW:
        # server_time lets the app correct for a wrong phone clock and retry.
        return _err('Request timestamp out of range.', status.HTTP_401_UNAUTHORIZED, server_time=now)

    message = f"{ts_raw}.{nonce}.{hashlib.sha256(body).hexdigest()}".encode()
    if not any(hmac.compare_digest(hmac.new(s, message, hashlib.sha256).hexdigest(), signature)
               for s in APP_SECRETS):
        return _err('Forbidden.', status.HTTP_403_FORBIDDEN)

    try:
        fresh = cache.add(f"blesos_nonce:{nonce}", 1, 2 * MAX_SKEW + 60)
    except Exception as e:
        # Fail open: an SOS report must not be lost to a cache outage.
        logger.error(f"BLE SOS nonce cache error: {e}")
        fresh = True
    if not fresh:
        return _err('Duplicate request.', status.HTTP_409_CONFLICT)
    return None


def _over_limit(key, limit):
    """Count one call against key; return seconds to wait if over limit, else 0."""
    try:
        cache.add(key, 0, WINDOW_SECONDS)
        count = cache.incr(key)
    except Exception as e:
        logger.error(f"BLE SOS rate limit cache error: {e}")
        return 0
    if count <= limit:
        return 0
    try:
        return max(1, int(cache.ttl(key) or WINDOW_SECONDS))
    except Exception:
        return WINDOW_SECONDS


def _opt_str(data, key, max_len):
    value = data.get(key)
    if value in (None, ''):
        return ''
    if not isinstance(value, str) or len(value.strip()) > max_len:
        raise _Invalid(f'{key} must be text of at most {max_len} characters.')
    return value.strip()


def _opt_number(data, key, lo, hi, integer=False):
    value = data.get(key)
    if value in (None, ''):
        return None
    if isinstance(value, bool):
        raise _Invalid(f'{key} must be a number.')
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise _Invalid(f'{key} must be a number.')
    if math.isnan(value) or not lo <= value <= hi:
        raise _Invalid(f'{key} must be between {lo} and {hi}.')
    return int(round(value)) if integer else value


def _parse_event_time(value):
    if value in (None, ''):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 1e11 else value    # epoch ms or seconds
        try:
            return datetime.fromtimestamp(seconds, tz=dt_timezone.utc)
        except (OverflowError, OSError, ValueError):
            raise _Invalid('event_time is not a valid timestamp.')
    if isinstance(value, str):
        parsed = parse_datetime(value.strip())
        if parsed:
            return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
    raise _Invalid('event_time must be epoch seconds/milliseconds or an ISO-8601 datetime.')


def _clean_cells(value):
    if value in (None, ''):
        return []
    if not isinstance(value, list) or len(value) > MAX_CELLS:
        raise _Invalid(f'cell_ids must be a list of at most {MAX_CELLS} items.')
    cells = []
    for cell in value:
        if isinstance(cell, (int, str)) and not isinstance(cell, bool) and len(str(cell)) <= 32:
            cells.append(cell)
            continue
        if not isinstance(cell, dict) or len(cell) > MAX_CELL_KEYS:
            raise _Invalid('each cell_ids item must be an id or an object of cell fields.')
        for k, v in cell.items():
            if not _RE_CELL_KEY.match(str(k)):
                raise _Invalid('cell_ids field names may contain only letters and "_".')
            if v is not None and not isinstance(v, (int, float, bool)) and not (isinstance(v, str) and len(v) <= 32):
                raise _Invalid(f'cell_ids.{k} must be a number or short text.')
        cells.append(cell)
    return cells


def _clean_payload(data):
    if not isinstance(data, dict):
        raise _Invalid('Body must be a JSON object.')

    mac = str(data.get('ble_mac') or '').strip().upper()
    if not _RE_MAC.match(mac):
        raise _Invalid('ble_mac is required and must be a MAC address, e.g. AA:BB:CC:DD:EE:FF.')
    mac = ':'.join(re.findall(r'[0-9A-F]{2}', mac))

    reg_no = re.sub(r'[\s-]', '', str(data.get('registration_no') or '')).upper()
    if not _RE_REG_NO.match(reg_no):
        raise _Invalid('registration_no is required (4-15 letters/digits).')

    phone_id = str(data.get('phone_device_id') or '').strip()
    if not _RE_PHONE_ID.match(phone_id):
        raise _Invalid('phone_device_id is required (4-128 characters: letters, digits, . _ : -).')

    mobile = re.sub(r'[\s+-]', '', str(data.get('user_mobile') or ''))
    if mobile and not _RE_MOBILE.match(mobile):
        raise _Invalid('user_mobile must be 10-15 digits, or blank.')

    sos_type = str(data.get('sos_type') or '').strip()
    if sos_type not in SOS_TYPES:
        raise _Invalid(f"sos_type must be one of: {', '.join(sorted(SOS_TYPES))}.")

    lat = _opt_number(data, 'latitude', -90, 90)
    lon = _opt_number(data, 'longitude', -180, 180)
    if (lat is None) != (lon is None):
        raise _Invalid('latitude and longitude must be sent together.')

    app_version = _opt_str(data, 'app_version', 30)
    if app_version and not _RE_VERSION.match(app_version):
        raise _Invalid('app_version may contain only letters, digits and . _ + -')

    return {
        'ble_mac': mac,
        'ble_device_name': _opt_str(data, 'ble_device_name', 100),
        'registration_no': reg_no,
        'phone_device_id': phone_id,
        'user_mobile': mobile,
        'sos_type': sos_type,
        'latitude': lat,
        'longitude': lon,
        'phone_battery': _opt_number(data, 'phone_battery', 0, 100, integer=True),
        'signal_strength_dbm': _opt_number(data, 'signal_strength_dbm', -200, 0, integer=True),
        'cell_ids': _clean_cells(data.get('cell_ids')),
        'event_time': _parse_event_time(data.get('event_time')),
        'app_version': app_version,
    }


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def ble_sos_app_log_create(request):
    """POST /api/ble-sos/app-log/  (signed by the app; see module docstring)
    {
      "ble_mac": "AA:BB:CC:DD:EE:FF", "ble_device_name": "SKY-BLE-01",
      "registration_no": "AS01AB1234", "phone_device_id": "a1b2c3d4e5f60718",
      "user_mobile": "", "sos_type": "BLE_Public",
      "latitude": 26.1445, "longitude": 91.7362,
      "phone_battery": 54, "signal_strength_dbm": -87,
      "cell_ids": [{"type": "LTE", "mcc": 404, "mnc": 56, "tac": 1234, "cid": 56789012, "rsrp": -95}],
      "event_time": 1791346448, "app_version": "2.4.1"
    }
    """
    if not APP_SECRETS:
        return _err('Not available.', status.HTTP_503_SERVICE_UNAVAILABLE)
    # Native app HTTP clients send no Origin; browsers always do on a POST.
    if request.META.get('HTTP_ORIGIN'):
        return _err('Forbidden.', status.HTTP_403_FORBIDDEN)

    body = request.body
    if len(body) > MAX_BODY_BYTES:
        return _err('Request too large.', status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    denied = _check_signature(request, body)
    if denied:
        return denied

    try:
        data = _clean_payload(json.loads(body.decode('utf-8')))
    except (ValueError, UnicodeDecodeError):
        return _err('Body must be valid JSON.', status.HTTP_400_BAD_REQUEST)
    except _Invalid as e:
        return _err(str(e), status.HTTP_400_BAD_REQUEST)

    ip = _client_ip(request) or None
    phone_key = hashlib.sha256(data['phone_device_id'].encode()).hexdigest()[:32]
    wait = (_over_limit(f"blesos_rl:phone:{phone_key}", PHONE_LIMIT)
            or (ip and _over_limit(f"blesos_rl:ip:{ip}", IP_LIMIT)))
    if wait:
        response = _err(f'Limit reached: at most {PHONE_LIMIT} SOS reports per '
                        f'{WINDOW_SECONDS // 60} minutes.', status.HTTP_429_TOO_MANY_REQUESTS,
                        retry_after=wait)
        response['Retry-After'] = str(wait)
        return response

    log = BleSosAppLog.objects.create(source_ip=ip, **data)
    return Response({'status': 'success', 'id': log.id}, status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------
# GET /api/ble-sos/app-log/list/
# --------------------------------------------------------------------------

def _int_param(request, name, default, lo, hi):
    raw = request.GET.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise _Invalid(f'{name} must be a number.')
    if not lo <= value <= hi:
        raise _Invalid(f'{name} must be between {lo} and {hi}.')
    return value


def _date_param(request, name, end_of_day=False):
    raw = (request.GET.get(name) or '').strip()
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is None:
        day = parse_date(raw)
        if day is None:
            raise _Invalid(f'{name} must be YYYY-MM-DD or an ISO-8601 datetime.')
        parsed = datetime.combine(day, dtime.max if end_of_day else dtime.min)
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)


def _row(log):
    return {
        'id': log.id,
        'ble_mac': log.ble_mac,
        'ble_device_name': log.ble_device_name,
        'registration_no': log.registration_no,
        'phone_device_id': log.phone_device_id,
        'user_mobile': log.user_mobile,
        'sos_type': log.sos_type,
        'latitude': log.latitude,
        'longitude': log.longitude,
        'phone_battery': log.phone_battery,
        'signal_strength_dbm': log.signal_strength_dbm,
        'cell_ids': log.cell_ids,
        'event_time': log.event_time,
        'app_version': log.app_version,
        'source_ip': log.source_ip,
        'received_at': log.received_at,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def ble_sos_app_log_list(request):
    """GET /api/ble-sos/app-log/list/
        ?ble_mac=AA:BB:CC:DD:EE:FF &registration_no=AS01 &phone_device_id=... &user_mobile=...
        &sos_type=BLE_Public &date_from=2026-10-01 &date_to=2026-10-07 &search=...
        &ordering=-received_at &page=1 &page_size=50
    date_from/date_to filter on received_at; registration_no is a partial match.
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
    sos_type = (p.get('sos_type') or '').strip()
    if sos_type and sos_type not in SOS_TYPES:
        return _err(f"sos_type must be one of: {', '.join(sorted(SOS_TYPES))}.", status.HTTP_400_BAD_REQUEST)

    qs = BleSosAppLog.objects.all()
    mac = (p.get('ble_mac') or '').strip().upper()
    if mac:
        qs = qs.filter(ble_mac=':'.join(re.findall(r'[0-9A-F]{2}', mac)) if _RE_MAC.match(mac) else mac)
    reg_no = re.sub(r'[\s-]', '', p.get('registration_no') or '').upper()
    if reg_no:
        qs = qs.filter(registration_no__icontains=reg_no)
    if p.get('phone_device_id'):
        qs = qs.filter(phone_device_id=p['phone_device_id'].strip())
    if p.get('user_mobile'):
        qs = qs.filter(user_mobile=re.sub(r'[\s+-]', '', p['user_mobile']))
    if sos_type:
        qs = qs.filter(sos_type=sos_type)
    if date_from:
        qs = qs.filter(received_at__gte=date_from)
    if date_to:
        qs = qs.filter(received_at__lte=date_to)
    search = (p.get('search') or '').strip()[:100]
    if search:
        qs = qs.filter(Q(ble_mac__icontains=search) | Q(ble_device_name__icontains=search)
                       | Q(registration_no__icontains=search) | Q(phone_device_id__icontains=search)
                       | Q(user_mobile__icontains=search))

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
