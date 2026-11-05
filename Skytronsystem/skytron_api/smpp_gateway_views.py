"""
SMS gateway API over our Airtel SMPP link, for our own servers (this dev VM
and NIC production). Served at https://dev-api.skytron.in, which exposes only
these two paths. The SMS is sent from our VMN by the smpp_worker container.

    POST /api/smpp/gateway/send/
        {"receiver_no": "5754206414333", "text": "@GETLOC*"}
        -> 201 {"status": "success", "txn_id": "...", "sms_status": "queued", ...}

    GET  /api/smpp/gateway/status/?txn_id=<id>[,<id>...]     (up to 50 ids)
        -> 200 {"status": "success", "data": [{"txn_id": ..., "sms_status": ..., ...}]}

Every call needs both:
    - header  X-Api-Key: <key>      a key from SMPP_API_KEYS
    - a caller address listed in SMPP_API_ALLOWED_IPS

A client sees only the transactions it created with its own key.

At most SMPP_API_DAILY_LIMIT SMS (default 1000) are accepted per calendar day
(IST), counted over all keys together; past that, send answers 429.

sms_status: queued -> sending -> submitted -> delivered | undelivered | failed

Settings (env):
    SMPP_API_KEYS          comma-separated name:key pairs, e.g. "dev:abc...,prod:def..."
                           (the name is stored with each SMS); empty = API disabled
    SMPP_API_ALLOWED_IPS   comma-separated IPs / CIDR ranges; empty = API disabled
    SMPP_API_DAILY_LIMIT   SMS per IST day over all keys (default 1000)

This path is exempt from the input guard (device commands may hold any
characters) - see input_guard.py.
"""
import hmac
import ipaddress
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db import connection, transaction
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .ble_sos_app_log_views import _err
from .models import SmppSmsOut
from .smpp_views import MAX_TEXT_LEN, SmppNumberError, normalise_number

logger = logging.getLogger(__name__)

IST = dt_timezone(timedelta(hours=5, minutes=30))
MAX_STATUS_IDS = 50
_TXN_RE = re.compile(r'[0-9a-f]{32}')
_QUOTA_LOCK_ID = 0x534D5050   # pg advisory lock key ("SMPP") serialising the daily count


def _load_keys(raw):
    keys = []
    for item in raw.split(','):
        name, sep, key = item.strip().partition(':')
        if not item.strip():
            continue
        if not sep or not name.strip() or len(key.strip()) < 24:
            logger.error("SMPP_API_KEYS: ignoring an entry that is not name:key with a key of 24+ characters")
            continue
        keys.append((name.strip()[:32], key.strip().encode()))
    return keys


def _load_networks(raw):
    networks = []
    for item in raw.split(','):
        if item.strip():
            try:
                networks.append(ipaddress.ip_network(item.strip(), strict=False))
            except ValueError:
                logger.error(f"SMPP_API_ALLOWED_IPS: ignoring invalid entry {item.strip()!r}")
    return networks


API_KEYS = _load_keys(os.environ.get('SMPP_API_KEYS', ''))
ALLOWED_NETWORKS = _load_networks(os.environ.get('SMPP_API_ALLOWED_IPS', ''))
try:
    DAILY_LIMIT = max(0, int(os.environ.get('SMPP_API_DAILY_LIMIT', '1000')))
except ValueError:
    DAILY_LIMIT = 1000


def _caller_ip(request):
    """
    Address that connected to nginx. nginx appends it to X-Forwarded-For, so it
    is the last entry; earlier entries come from the caller and can be forged.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    raw = forwarded.split(',')[-1].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def _client_name(request):
    """Name of the matching API key, or None."""
    given = request.META.get('HTTP_X_API_KEY', '').strip().encode()
    if not given:
        return None
    match = None
    for name, key in API_KEYS:          # compare against every key: constant time per call
        if hmac.compare_digest(key, given):
            match = name
    return match


def _check_caller(request):
    """(client_name, ip, None) when allowed, else (None, ip, error response)."""
    ip = _caller_ip(request)
    if not API_KEYS or not ALLOWED_NETWORKS:
        return None, ip, _err('SMS gateway API is not configured.', status.HTTP_503_SERVICE_UNAVAILABLE)
    if not ip or not any(ipaddress.ip_address(ip) in net for net in ALLOWED_NETWORKS):
        logger.warning(f"SMPP gateway: refused caller address {ip}")
        return None, ip, _err('Caller address not allowed.', status.HTTP_403_FORBIDDEN)
    client = _client_name(request)
    if not client:
        logger.warning(f"SMPP gateway: missing or wrong API key from {ip}")
        return None, ip, _err('Missing or invalid X-Api-Key.', status.HTTP_401_UNAUTHORIZED)
    return client, ip, None


def _day_start_utc(now=None):
    now_ist = (now or datetime.now(dt_timezone.utc)).astimezone(IST)
    return now_ist.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt_timezone.utc)


def _used_today():
    return SmppSmsOut.objects.filter(created_at__gte=_day_start_utc()).exclude(api_client='').count()


def _row(sms):
    parts = sorted(sms.parts.all(), key=lambda part: part.part_no)
    return {
        'txn_id': sms.txn_id,
        'receiver_no': sms.dest_no,
        'sms_status': sms.status,
        'error': sms.error,
        'parts_total': sms.parts_total,
        'created_at': sms.created_at,
        'submitted_at': sms.submitted_at,
        'final_at': sms.final_at,
        'parts': [{
            'part_no': p.part_no,
            'message_id': p.message_id,
            'dlr_stat': p.dlr_stat,
            'dlr_err': p.dlr_err,
            'submitted_at': p.submitted_at,
            'dlr_at': p.dlr_at,
        } for p in parts],
    }


# --------------------------------------------------------------------------
# POST /api/smpp/gateway/send/
# --------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def smpp_gateway_send(request):
    client, ip, denied = _check_caller(request)
    if denied:
        return denied
    if not isinstance(request.data, dict):
        return _err('Body must be a JSON object.', status.HTTP_400_BAD_REQUEST)

    text = request.data.get('text')
    if not isinstance(text, str) or not text:
        return _err('text is required.', status.HTTP_400_BAD_REQUEST)
    if len(text) > MAX_TEXT_LEN:
        return _err(f'text must be at most {MAX_TEXT_LEN} characters.', status.HTTP_400_BAD_REQUEST)
    receiver = request.data.get('receiver_no')
    if not isinstance(receiver, (str, int)) or not str(receiver).strip():
        return _err('receiver_no is required.', status.HTTP_400_BAD_REQUEST)
    try:
        dest_no = normalise_number(receiver)
    except SmppNumberError as e:
        return _err(f'receiver_no: {e}', status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        # One sender at a time past this point, so the count and the insert agree.
        with connection.cursor() as cur:
            cur.execute('SELECT pg_advisory_xact_lock(%s)', [_QUOTA_LOCK_ID])
        used = _used_today()
        if used >= DAILY_LIMIT:
            logger.warning(f"SMPP gateway: daily limit {DAILY_LIMIT} reached, refused {client}@{ip}")
            return _err(f'Daily limit of {DAILY_LIMIT} SMS reached; resets at 00:00 IST.',
                        status.HTTP_429_TOO_MANY_REQUESTS, daily_limit=DAILY_LIMIT, used_today=used)
        sms = SmppSmsOut.objects.create(dest_no=dest_no, text=text, txn_id=secrets.token_hex(16),
                                        api_client=client, client_ip=ip)

    return Response({
        'status': 'success',
        'message': 'SMS queued.',
        'txn_id': sms.txn_id,
        'receiver_no': sms.dest_no,
        'sms_status': sms.status,
        'created_at': sms.created_at,
        'daily_limit': DAILY_LIMIT,
        'remaining_today': DAILY_LIMIT - used - 1,
    }, status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------
# GET /api/smpp/gateway/status/?txn_id=...
# --------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def smpp_gateway_status(request):
    client, ip, denied = _check_caller(request)
    if denied:
        return denied

    ids = [t.strip().lower() for t in (request.GET.get('txn_id') or '').split(',') if t.strip()]
    if not ids:
        return _err('txn_id is required.', status.HTTP_400_BAD_REQUEST)
    if len(ids) > MAX_STATUS_IDS:
        return _err(f'At most {MAX_STATUS_IDS} txn_id values per call.', status.HTTP_400_BAD_REQUEST)
    bad = [t for t in ids if not _TXN_RE.fullmatch(t)]
    if bad:
        return _err('txn_id must be 32 hex characters.', status.HTTP_400_BAD_REQUEST, invalid=bad[:5])

    found = {sms.txn_id: sms for sms in
             SmppSmsOut.objects.filter(txn_id__in=ids, api_client=client).prefetch_related('parts')}
    if len(ids) == 1 and ids[0] not in found:
        return _err('Transaction not found.', status.HTTP_404_NOT_FOUND)
    return Response({
        'status': 'success',
        'data': [_row(found[t]) for t in ids if t in found],
        'not_found': [t for t in ids if t not in found],
    })
