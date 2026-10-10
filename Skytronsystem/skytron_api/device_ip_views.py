"""
Device source-IP lookups over the raw packet logs (GPSDataLog / GPSemDataLog).

Every log row now carries source_ip (from the TCP socket, or the MQTT broker's
connect log), the packet's IMEI and its network operator name. These APIs
answer three questions within a time window:

    GET /api/device-ip/unique/      which IPs have devices sent from?
    GET /api/device-ip/imeis/       which IMEIs sent from this IP?   (paginated)
    GET /api/device-ip/by-imei/     which IPs did this IMEI send from?

All three are superadmin only, and read only rows that have an IP (served by
the partial indexes from migration 0106).

    POST /api/mqtt/client-ip/report/   broker VM -> backend imei/IP feed

is called only by mqtt_deployment/mqtt_ip_reporter.py, authenticated with the
shared MQTT_IP_REPORT_KEY (disabled when that env var is empty).
"""
import hmac
import ipaddress
import math
import os
import re
from datetime import timedelta

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.cache import cache
from django.db.models import Count, Max, Min, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from . import mqtt_client_ip
from .models import GPSDataLog, GPSemDataLog

SOURCES = {'gps': GPSDataLog, 'em': GPSemDataLog}
DEFAULT_DAYS = 7
MAX_DAYS = 90
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
UNIQUE_IP_CACHE_SECONDS = 60


class _BadParam(Exception):
    pass


def _bad(message):
    return Response({'status': 'error', 'message': message}, status=status.HTTP_400_BAD_REQUEST)


def _int_param(request, name, default, lo, hi):
    raw = request.GET.get(name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise _BadParam(f'{name} must be a number.')
    if not lo <= value <= hi:
        raise _BadParam(f'{name} must be between {lo} and {hi}.')
    return value


def _common_params(request):
    source = (request.GET.get('source') or 'all').strip().lower()
    if source not in ('gps', 'em', 'all'):
        raise _BadParam("source must be one of: gps, em, all.")
    days = _int_param(request, 'days', DEFAULT_DAYS, 1, MAX_DAYS)
    page = _int_param(request, 'page', 1, 1, 100000)
    page_size = _int_param(request, 'page_size', DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    sources = ['gps', 'em'] if source == 'all' else [source]
    return sources, days, page, page_size


def _grouped(sources, since, group_field, filters, count_imeis=False):
    """Group IP-bearing log rows by group_field across the selected tables,
    then merge the per-table groups into one dict keyed by group value."""
    merged = {}
    for label in sources:
        annotations = {
            'packet_count': Count('id'),
            'first_seen': Min('timestamp'),
            'last_seen': Max('timestamp'),
            'network_names': ArrayAgg('network_name', distinct=True,
                                      filter=Q(network_name__isnull=False), default=[]),
        }
        if count_imeis:
            annotations['imeis'] = ArrayAgg('imei', distinct=True,
                                            filter=Q(imei__isnull=False), default=[])
        rows = (SOURCES[label].objects
                .filter(source_ip__isnull=False, timestamp__gte=since, **filters)
                .values(group_field)
                .annotate(**annotations))
        for row in rows:
            key = str(row[group_field])
            entry = merged.setdefault(key, {
                group_field: key,
                'packet_count': 0,
                'first_seen': row['first_seen'],
                'last_seen': row['last_seen'],
                'network_names': set(),
                'imeis': set(),
                'seen_in': [],
            })
            entry['packet_count'] += row['packet_count']
            entry['first_seen'] = min(entry['first_seen'], row['first_seen'])
            entry['last_seen'] = max(entry['last_seen'], row['last_seen'])
            entry['network_names'].update(row['network_names'])
            entry['imeis'].update(row.get('imeis') or [])
            entry['seen_in'].append(label)

    out = []
    for entry in merged.values():
        imeis = entry.pop('imeis')
        if count_imeis:
            entry['imei_count'] = len(imeis)
        entry['network_names'] = sorted(entry['network_names'])
        out.append(entry)
    out.sort(key=lambda e: e['last_seen'], reverse=True)
    return out


def _paginate(rows, page, page_size):
    total = len(rows)
    start = (page - 1) * page_size
    return rows[start:start + page_size], {
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': math.ceil(total / page_size) if total else 0,
    }


def _superadmin_or_403(request):
    if getattr(request.user, 'role', None) != 'superadmin':
        return Response({'status': 'error', 'message': 'Only superadmin can access this.'},
                        status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def device_ip_unique(request):
    """GET /api/device-ip/unique/?source=all&days=7&search=106.222&page=1&page_size=50"""
    denied = _superadmin_or_403(request)
    if denied:
        return denied
    try:
        sources, days, page, page_size = _common_params(request)
    except _BadParam as e:
        return _bad(str(e))

    search = (request.GET.get('search') or '').strip()
    if search and not all(c in '0123456789abcdefABCDEF.:' for c in search):
        return _bad('search may contain only IP characters (digits, a-f, "." and ":").')

    # This aggregates every IP-bearing log row in the window, so the merged
    # result is kept briefly: paging and searching through it then cost
    # nothing instead of repeating the full aggregation per click.
    cache_key = f"device_ip:unique:{'+'.join(sources)}:{days}"
    rows = cache.get(cache_key)
    if rows is None:
        since = timezone.now() - timedelta(days=days)
        rows = _grouped(sources, since, 'source_ip', {}, count_imeis=True)
        cache.set(cache_key, rows, UNIQUE_IP_CACHE_SECONDS)
    if search:
        rows = [r for r in rows if r['source_ip'].startswith(search)]
    page_rows, pagination = _paginate(rows, page, page_size)

    return Response({
        'status': 'success',
        'source': '+'.join(sources),
        'days': days,
        'pagination': pagination,
        'data': page_rows,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def device_ip_imeis(request):
    """GET /api/device-ip/imeis/?ip=106.222.247.168&source=all&days=7&page=1&page_size=50"""
    denied = _superadmin_or_403(request)
    if denied:
        return denied
    try:
        sources, days, page, page_size = _common_params(request)
    except _BadParam as e:
        return _bad(str(e))
    try:
        ip = str(ipaddress.ip_address((request.GET.get('ip') or '').strip()))
    except ValueError:
        return _bad('ip is required and must be a valid IPv4/IPv6 address.')

    since = timezone.now() - timedelta(days=days)
    rows = _grouped(sources, since, 'imei', {'source_ip': ip, 'imei__isnull': False})
    page_rows, pagination = _paginate(rows, page, page_size)

    return Response({
        'status': 'success',
        'ip': ip,
        'source': '+'.join(sources),
        'days': days,
        'pagination': pagination,
        'data': page_rows,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def device_ip_by_imei(request):
    """GET /api/device-ip/by-imei/?imei=866192070567555&source=all&days=7&page=1&page_size=50"""
    denied = _superadmin_or_403(request)
    if denied:
        return denied
    try:
        sources, days, page, page_size = _common_params(request)
    except _BadParam as e:
        return _bad(str(e))
    imei = (request.GET.get('imei') or '').strip()
    if not (imei.isdigit() and 14 <= len(imei) <= 17):
        return _bad('imei is required and must be 14-17 digits.')

    since = timezone.now() - timedelta(days=days)
    rows = _grouped(sources, since, 'source_ip', {'imei': imei})
    page_rows, pagination = _paginate(rows, page, page_size)

    return Response({
        'status': 'success',
        'imei': imei,
        'source': '+'.join(sources),
        'days': days,
        'pagination': pagination,
        'data': page_rows,
    })


MQTT_IP_REPORT_KEY = os.environ.get('MQTT_IP_REPORT_KEY', '')
MAX_REPORT_ENTRIES = 2000
_RE_IMEI = re.compile(r'^\d{14,17}$')


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([])
def mqtt_client_ip_report(request):
    """POST /api/mqtt/client-ip/report/
    Header  X-MQTT-IP-Key: <MQTT_IP_REPORT_KEY>
    Body    {"entries": [{"imei": "866192070567555", "ip": "106.222.247.168", "ts": 1791346448}, ...]}
    """
    supplied = request.headers.get('X-MQTT-IP-Key', '')
    if not MQTT_IP_REPORT_KEY or not hmac.compare_digest(supplied, MQTT_IP_REPORT_KEY):
        return Response({'status': 'error', 'message': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)

    entries = request.data.get('entries') if isinstance(request.data, dict) else None
    if not isinstance(entries, list) or len(entries) > MAX_REPORT_ENTRIES:
        return _bad(f'entries must be a list of at most {MAX_REPORT_ENTRIES} items.')

    clean, rejected = [], 0
    for e in entries:
        try:
            imei = str(e['imei']).strip()
            ip = str(ipaddress.ip_address(str(e['ip']).strip()))
            ts = int(e['ts'])
            if not _RE_IMEI.match(imei):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            rejected += 1
            continue
        clean.append((imei, ip, ts))

    try:
        written = mqtt_client_ip.record_many(clean)
    except Exception as exc:
        return Response({'status': 'error', 'message': f'store failed: {exc}'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({'status': 'success', 'accepted': len(clean), 'written': written, 'rejected': rejected})
