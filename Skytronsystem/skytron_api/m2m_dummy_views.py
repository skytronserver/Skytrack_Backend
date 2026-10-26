"""
Dummy M2M / eSIM provider API, hosted inside this backend.

    POST /api/m2m-dummy/sim-details/     body: {"k1": <token>, "k2": <iccid>}

Same request and response shape as the real provider API (Mapwala format)
that views.py calls from the M2M config test, tagging step 2 and eSIM
renewal, so _normalise_m2m_result accepts it unchanged. It exists because
production has no outbound URL whitelisted yet: an eSimProvider saves

    api_url = http://localhost:2000/api/m2m-dummy/sim-details/

as their M2M config and the backend then calls itself.

Every SIM it returns is fabricated: status Active, activated 30 days ago,
valid DUMMY_VALIDITY_YEARS from today. Primary/fallback TSP come from the
TSP combination picked in the latest tagging entry for that ICCID, so the
step 2 combination check passes; otherwise DEFAULT_TSPS.

Only direct calls from this host are served: loopback REMOTE_ADDR and no
proxy header, so nothing coming in through nginx can reach it.

Settings (env):
    M2M_DUMMY_API_ENABLED   'false' disables the endpoint (default: enabled)
    M2M_DUMMY_API_TOKEN     if set, k1 must equal it or the call gets 401;
                            empty = any non-empty k1 is accepted
"""
import hashlib
import ipaddress
import logging
import os
import re
from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import DeviceStockMaster

logger = logging.getLogger(__name__)

ENABLED = os.environ.get('M2M_DUMMY_API_ENABLED', 'true').strip().lower() != 'false'
API_TOKEN = os.environ.get('M2M_DUMMY_API_TOKEN', '').strip()

DUMMY_VALIDITY_YEARS = 5
DUMMY_ACTIVATED_DAYS_AGO = 30
DEFAULT_TSPS = ('AIRTEL', 'BSNL')
DATE_FORMAT = '%d-%m-%Y'


def _is_local_call(request):
    """A direct call from this host, not one relayed by nginx."""
    if request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('HTTP_X_REAL_IP'):
        return False
    try:
        return ipaddress.ip_address(request.META.get('REMOTE_ADDR', '')).is_loopback
    except ValueError:
        return False


def _error(code, message, http_status):
    return Response({"apiResponseCode": code, "apiResponseMsg": message, "resultObj": []}, status=http_status)


def _tsps_for(iccid):
    """(primary, fallback) matching the combination chosen while tagging this ICCID."""
    record = (DeviceStockMaster.objects.filter(iccid=iccid)
              .exclude(provider_combination=[]).order_by('-id').first())
    combination = [str(t).strip().upper() for t in (record.provider_combination if record else []) if str(t).strip()]
    if len(combination) >= 2:
        return combination[0], combination[1]
    return DEFAULT_TSPS


def _msisdn(iccid, salt):
    """Stable 13-digit M2M number per ICCID, so repeat calls agree."""
    digits = re.sub(r'\D', '', hashlib.sha256(f'{salt}:{iccid}'.encode()).hexdigest())
    return '5' + (digits + '0' * 12)[:12]


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def m2m_dummy_sim_details(request):
    if not ENABLED or not _is_local_call(request):
        return Response({"error": "Not found."}, status=404)

    data = request.data if isinstance(request.data, dict) else {}
    token = str(data.get('k1') or '').strip()
    iccid = str(data.get('k2') or '').strip()

    if not token or (API_TOKEN and token != API_TOKEN):
        return _error("LCM_401", "Invalid or expired token.", 401)
    if not re.fullmatch(r'\d{18,22}', iccid):
        return _error("LCM_002", "Invalid ICCID.", 200)

    today = timezone.localdate()
    primary_tsp, fallback_tsp = _tsps_for(iccid)
    logger.info(f"M2M dummy API served ICCID {iccid} ({primary_tsp}/{fallback_tsp})")

    return Response({
        "apiResponseCode": "LCM_001",
        "apiResponseMsg": "Success (dummy data)",
        "resultObj": [{
            "iccid": iccid,
            "cardStatus": "Active",
            "cardState": "Commercial",
            "activateOn": (today - timedelta(days=DUMMY_ACTIVATED_DAYS_AGO)).strftime(DATE_FORMAT),
            "expiredOn": (today + timedelta(days=365 * DUMMY_VALIDITY_YEARS)).strftime(DATE_FORMAT),
            "primaryTSP": primary_tsp,
            "primaryMSISDN": _msisdn(iccid, 'primary'),
            "primaryStatus": "Active",
            "fallbackTSP": fallback_tsp,
            "fallbackMSISDN": _msisdn(iccid, 'fallback'),
            "fallbackStatus": "Active",
            "dataUsage": "0.00 MB",
            "dataUsageDate": today.strftime(DATE_FORMAT),
        }],
    })
