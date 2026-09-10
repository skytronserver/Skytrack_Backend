"""
Dummy/mock API: devices with an IP violation (the IP a device's session
connected from doesn't match its configured/valid IP range).

Every field returned here is fabricated -- there is no real IMEI, ICCID,
owner, or manufacturer behind any row. This exists purely as a stand-in
response shape for frontend/integration work ahead of the real IP-violation
detection feature, which does not exist yet.
"""
import random
from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .throttles import IPViolationDummyRateThrottle

DEFAULT_COUNT = 10
MAX_COUNT = 100

_MANUFACTURERS = [
    ("MapleTech Telematics Pvt Ltd", "Plot 14, Industrial Estate, Guwahati, Assam", "9435012345"),
    ("Northline Devices Pvt Ltd", "Sector 62, Noida, Uttar Pradesh", "9811023456"),
    ("Aranya Electronics Ltd", "MIDC Bhosari, Pune, Maharashtra", "9822034567"),
    ("Skyline IoT Solutions", "Peenya Industrial Area, Bengaluru, Karnataka", "9880045678"),
]

_MODELS = ["SKT-GT200", "SKT-GT310", "SKT-AX50", "SKT-VLT7"]

_OWNER_NAMES = [
    "Ramesh Kalita", "Ankita Sharma", "Bipul Das", "Farhan Ahmed",
    "Meera Nair", "Suresh Reddy", "Priya Verma", "Rahul Deka",
]

_OWNER_ADDRESSES = [
    "House 12, Zoo Road, Guwahati, Assam",
    "Flat 4B, Sector 21, Noida, Uttar Pradesh",
    "23 MG Road, Pune, Maharashtra",
    "56 Indiranagar, Bengaluru, Karnataka",
    "9 Park Street, Kolkata, West Bengal",
]

_REG_STATE_PREFIXES = ["AS01", "DL01", "MH12", "KA05", "WB06"]
_REG_SERIES = ["AA", "AB", "BC", "CD", "PT"]

_VALID_IP_RANGES = ["103.195.217.0/24", "10.192.136.0/24", "182.75.20.0/24", "45.113.0.0/16"]


def _random_ip():
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def _random_imei():
    return ''.join(str(random.randint(0, 9)) for _ in range(15))


def _random_iccid():
    return '89' + ''.join(str(random.randint(0, 9)) for _ in range(18))


def _dummy_record():
    manufacturer_name, manufacturer_address, manufacturer_mobile = random.choice(_MANUFACTURERS)
    session_start = timezone.now() - timedelta(hours=random.randint(1, 72), minutes=random.randint(0, 59))
    session_end = session_start + timedelta(minutes=random.randint(5, 240))

    return {
        "IMEI": _random_imei(),
        "Manufacturer Name": manufacturer_name,
        "Manufacturer Address": manufacturer_address,
        "Manufacturer Mobile No": manufacturer_mobile,
        "Model": random.choice(_MODELS),
        "ICCID ID": _random_iccid(),
        "Owner Name": random.choice(_OWNER_NAMES),
        "Owner No": f"9{random.randint(100000000, 999999999)}",
        "Owner Address": random.choice(_OWNER_ADDRESSES),
        "Vehicle Reg No": (
            f"{random.choice(_REG_STATE_PREFIXES)}{random.choice(_REG_SERIES)}{random.randint(1000, 9999)}"
        ),
        "Valid IP Range": random.choice(_VALID_IP_RANGES),
        "Received IP": _random_ip(),
        "Session Start Time": session_start.isoformat(),
        "Session End Time": session_end.isoformat(),
    }


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([IPViolationDummyRateThrottle])
def ip_violation_dummy_list(request):
    """
    GET /api/ip-violations/dummy/?count=<n>&seed=<optional>

    Returns `count` (default 10, max 100) fabricated device records shaped
    like an IP-violation report. Pass `seed` to get a reproducible set of
    rows across calls (same seed + count -> same output); omit it for a
    fresh random set each call.
    """
    try:
        count = int(request.GET.get('count', DEFAULT_COUNT))
    except (TypeError, ValueError):
        count = DEFAULT_COUNT
    count = max(1, min(count, MAX_COUNT))

    seed = request.GET.get('seed')
    rng_state = random.getstate()
    try:
        if seed is not None:
            random.seed(seed)
        records = [_dummy_record() for _ in range(count)]
    finally:
        random.setstate(rng_state)

    return Response({
        'status': 'success',
        'is_dummy_data': True,
        'note': 'All fields in this response are fabricated placeholder data.',
        'count': len(records),
        'devices': records,
    })
