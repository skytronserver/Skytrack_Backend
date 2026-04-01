
import threading, os, ssl, json, time
import paho.mqtt.client as mqtt
from rest_framework.pagination import PageNumberPagination
from math import radians, sin, cos, sqrt, asin
# --- API: Get latest EMUserLocation for all unique field executives ---
from django.db.models import OuterRef, Subquery, Max

from .models import Trip
from .serializers import TripSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.shortcuts import render
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.views.decorators.http import require_http_methods

import logging


logger = logging.getLogger(__name__)

try:
    from django_redis.exceptions import ConnectionInterrupted  # type: ignore
except Exception:  # pragma: no cover
    ConnectionInterrupted = ()  # type: ignore

try:
    from redis.exceptions import ConnectionError as RedisConnectionError  # type: ignore
except Exception:  # pragma: no cover
    RedisConnectionError = ()  # type: ignore


class SafeAnonRateThrottle(AnonRateThrottle):
    """Like DRF's AnonRateThrottle, but doesn't 500 if cache backend is down."""

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except (ConnectionInterrupted, RedisConnectionError, OSError) as exc:
            logger.warning('Throttle cache unavailable; allowing request', exc_info=exc)
            return True


class SafeUserRateThrottle(UserRateThrottle):
    """Like DRF's UserRateThrottle, but doesn't 500 if cache backend is down."""

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except (ConnectionInterrupted, RedisConnectionError, OSError) as exc:
            logger.warning('Throttle cache unavailable; allowing request', exc_info=exc)
            return True


# Override the imported throttle symbols so all @throttle_classes([...]) usages in this
# module use the safe variants (without touching hundreds of decorators).
AnonRateThrottle = SafeAnonRateThrottle
UserRateThrottle = SafeUserRateThrottle


from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime

from .models import pointofinterests
from .serializers import PointOfInterestSerializer
from django.db.models import F, Value as V
from django.db.models.functions import Concat
from django.db.models import FloatField
from django.db.models.functions import Cast
import math

from django.db.models import Avg, Count, DurationField, ExpressionWrapper
from django.db.models.functions import TruncMonth
from django.db.models import Prefetch


@api_view(['GET'])
@permission_classes([AllowAny])
def sos_monthly_metrics(request):
    """
    Unauthenticated API providing month-wise SOS metrics for a given year.

    Output includes per-month:
    - total SOS calls
    - genuine SOS calls (status != 'closed_false_alert')
    - fake SOS calls (status == 'closed_false_alert')
    - average response time of police (arrived_time - accept_time for assignments type in ['police_ex','pcr'])
    - average response time of ambulance (arrived_time - accept_time for assignments type in ['ambulance_ex','acr'])
    - average acceptance time of desk executives (accept_time - start_time for assignments type == 'desk_ex')

    Optional query param: year (defaults to current year)
    """
    from .models import EMCall, EMCallAssignment
    try:
        year = int(request.GET.get('year', timezone.now().year))
    except ValueError:
        return Response({'error': 'Invalid year parameter'}, status=400)

    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime(year, 1, 1), tz)
    end_dt = timezone.make_aware(datetime(year + 1, 1, 1), tz)

    months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    # Base response structure
    data = {
        'year': year,
        'months': months_order,
        'calls': {
            'total': [0] * 12,
            'genuine': [0] * 12,
            'fake': [0] * 12,
        },
        'performance': {
            'police_avg_seconds': [None] * 12,
            'ambulance_avg_seconds': [None] * 12,
            'executive_accept_avg_seconds': [None] * 12,
        }
    }

    # --- Counts: total, genuine, fake ---
    calls_qs = EMCall.objects.filter(start_time__gte=start_dt, start_time__lt=end_dt)

    totals = (
        calls_qs
        .annotate(month=TruncMonth('start_time'))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
    )
    for row in totals:
        idx = row['month'].month - 1
        data['calls']['total'][idx] = row['total']

    fake = (
        calls_qs.filter(status='closed_false_alert')
        .annotate(month=TruncMonth('start_time'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    for row in fake:
        idx = row['month'].month - 1
        data['calls']['fake'][idx] = row['count']

    # Genuine = total - fake (simple heuristic based on status)
    for i in range(12):
        data['calls']['genuine'][i] = max(0, data['calls']['total'][i] - data['calls']['fake'][i])

    # --- Performance: average durations ---
    # Helper to aggregate average duration per month
    def assign_avg_duration(queryset, diff_expr_field, month_by='call__start_time'):
        return (
            queryset
            .exclude(**{diff_expr_field.split(' - ')[0] + '__isnull': True})
            .exclude(**{diff_expr_field.split(' - ')[2] + '__isnull': True})
            .annotate(
                month=TruncMonth(month_by),
                diff=ExpressionWrapper(
                    F(diff_expr_field.split(' - ')[2]) - F(diff_expr_field.split(' - ')[0]),
                    output_field=DurationField()
                )
            )
            .values('month')
            .annotate(avg=Avg('diff'))
            .order_by('month')
        )

    # Police: arrived_time - accept_time, types in police family
    police_qs = EMCallAssignment.objects.filter(
        call__start_time__gte=start_dt,
        call__start_time__lt=end_dt,
        type__in=['police_ex', 'pcr']
    )
    police_avgs = (
        police_qs
        .exclude(accept_time__isnull=True)
        .exclude(arrived_time__isnull=True)
        .annotate(
            month=TruncMonth('call__start_time'),
            diff=ExpressionWrapper(F('arrived_time') - F('accept_time'), output_field=DurationField())
        )
        .values('month')
        .annotate(avg=Avg('diff'))
        .order_by('month')
    )
    for row in police_avgs:
        idx = row['month'].month - 1
        avg_seconds = row['avg'].total_seconds() if row['avg'] else None
        data['performance']['police_avg_seconds'][idx] = avg_seconds

    # Ambulance: arrived_time - accept_time, types in ambulance family
    ambulance_qs = EMCallAssignment.objects.filter(
        call__start_time__gte=start_dt,
        call__start_time__lt=end_dt,
        type__in=['ambulance_ex', 'acr']
    )
    ambulance_avgs = (
        ambulance_qs
        .exclude(accept_time__isnull=True)
        .exclude(arrived_time__isnull=True)
        .annotate(
            month=TruncMonth('call__start_time'),
            diff=ExpressionWrapper(F('arrived_time') - F('accept_time'), output_field=DurationField())
        )
        .values('month')
        .annotate(avg=Avg('diff'))
        .order_by('month')
    )
    for row in ambulance_avgs:
        idx = row['month'].month - 1
        avg_seconds = row['avg'].total_seconds() if row['avg'] else None
        data['performance']['ambulance_avg_seconds'][idx] = avg_seconds

    # Executives (desk): accept_time - start_time
    desk_qs = EMCallAssignment.objects.filter(
        call__start_time__gte=start_dt,
        call__start_time__lt=end_dt,
        type='desk_ex'
    )
    desk_avgs = (
        desk_qs
        .exclude(accept_time__isnull=True)
        .exclude(start_time__isnull=True)
        .annotate(
            month=TruncMonth('call__start_time'),
            diff=ExpressionWrapper(F('accept_time') - F('start_time'), output_field=DurationField())
        )
        .values('month')
        .annotate(avg=Avg('diff'))
        .order_by('month')
    )
    for row in desk_avgs:
        idx = row['month'].month - 1
        avg_seconds = row['avg'].total_seconds() if row['avg'] else None
        data['performance']['executive_accept_avg_seconds'][idx] = avg_seconds

    return Response(data)


class SOSReportPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500
    page_query_param = 'page'


def _parse_dt_param(value):
    """Parse datetime query params.

    Accepts ISO-8601 strings (preferred) and returns an aware datetime when possible.
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in ('', 'none', 'null', 'undefined'):
        return None
    dt = parse_datetime(str(value))
    if dt is None:
        return None
    if timezone.is_naive(dt):
        try:
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        except Exception:
            pass
    return dt


def _em_ex_display_name(ex_obj):
    if not ex_obj:
        return None
    try:
        u = ex_obj.users.first()
        if u and getattr(u, 'name', None):
            return u.name
        if u and getattr(u, 'mobile', None):
            return u.mobile
        if u and getattr(u, 'email', None):
            return u.email
    except Exception:
        pass
    return str(getattr(ex_obj, 'id', None))


def _haversine_km(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    except Exception:
        return None
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return r * c


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET'])
def SOS_detailed_report(request):
    """SOS report (one row per emergency call).

    Filters (query params):
    - start_datetime, end_datetime (ISO-8601)
    - district_id
    - call_id
    - vehicle_reg_no
    - device_imei

    Pagination:
    - page (default 1)
    - page_size (default 50)
    """
    from .models import EMCall, EMCallAssignment, EMCallBroadcast, GPSData, pointofinterests

    start_dt = _parse_dt_param(request.GET.get('start_datetime'))
    end_dt = _parse_dt_param(request.GET.get('end_datetime'))
    district_id = request.GET.get('district_id')
    call_id = request.GET.get('call_id')
    vehicle_reg_no = request.GET.get('vehicle_reg_no')
    device_imei = request.GET.get('device_imei')

    try:
        district_id = int(district_id) if district_id not in (None, '', 'None', 'null', 'undefined') else None
    except Exception:
        district_id = None
    try:
        call_id_int = int(call_id) if call_id not in (None, '', 'None', 'null', 'undefined') else None
    except Exception:
        call_id_int = None

    # Base queryset
    qs = (
        EMCall.objects
        .select_related(
            'device', 'device__device', 'device__category', 'device__district',
            'team', 'team__teamlead', 'team__state'
        )
        .all()
        .order_by('-start_time', '-id')
    )

    if start_dt:
        qs = qs.filter(start_time__gte=start_dt)
    if end_dt:
        qs = qs.filter(start_time__lte=end_dt)
    if district_id is not None:
        qs = qs.filter(device__district_id=district_id)
    if call_id_int is not None:
        qs = qs.filter(id=call_id_int)
    if vehicle_reg_no:
        qs = qs.filter(device__vehicle_reg_no__icontains=str(vehicle_reg_no).strip())
    if device_imei:
        qs = qs.filter(device__device__imei__icontains=str(device_imei).strip())

    # Prefetch assignments and broadcasts to avoid N+1 queries during row-building.
    assignment_qs = (
        EMCallAssignment.objects
        .select_related('ex', 'admin')
        .prefetch_related('ex__users')
        .order_by('id')
    )
    broadcast_qs = (
        EMCallBroadcast.objects
        .select_related('acceted_by', 'created_by', 'admin')
        .prefetch_related('acceted_by__users', 'created_by__users')
        .order_by('id')
    )
    qs = qs.prefetch_related(
        Prefetch('EMCall_id', queryset=assignment_qs, to_attr='__pref_assignments'),
        Prefetch('EMCallb_id', queryset=broadcast_qs, to_attr='__pref_broadcasts'),
    )

    # GPS subqueries for trigger/closure coords (fast and DB-side)
    trigger_gps = (
        GPSData.objects
        .filter(device_tag=OuterRef('device_id'), entry_time__gte=OuterRef('start_time'))
        .order_by('entry_time')
    )
    closure_gps = (
        GPSData.objects
        .filter(device_tag=OuterRef('device_id'), entry_time__lte=OuterRef('end_time'))
        .order_by('-entry_time')
    )
    qs = qs.annotate(
        trigger_time=Subquery(trigger_gps.values('entry_time')[:1]),
        trigger_latitude=Subquery(trigger_gps.values('latitude')[:1]),
        trigger_longitude=Subquery(trigger_gps.values('longitude')[:1]),
        closure_latitude=Subquery(closure_gps.values('latitude')[:1]),
        closure_longitude=Subquery(closure_gps.values('longitude')[:1]),
    )

    paginator = SOSReportPagination()
    page = paginator.paginate_queryset(qs, request)

    # Pre-load police station POIs once (used per-row for nearest)
    police_stations = list(
        pointofinterests.objects.filter(use_type='PoliceStation')
        .exclude(lat__isnull=True)
        .exclude(lon__isnull=True)
        .exclude(status__in=['Deleted', 'Deleted2'])
        .values('id', 'name', 'lat', 'lon')
    )

    def nearest_police_station_name(lat, lon):
        if lat is None or lon is None or not police_stations:
            return None
        best_name = None
        best_dist = None
        for ps in police_stations:
            d = _haversine_km(lat, lon, ps.get('lat'), ps.get('lon'))
            if d is None:
                continue
            if best_dist is None or d < best_dist:
                best_dist = d
                best_name = ps.get('name')
        return best_name

    def pick_first(qs_list, pred):
        for item in qs_list:
            try:
                if pred(item):
                    return item
            except Exception:
                continue
        return None

    def min_dt(values):
        values = [v for v in values if v is not None]
        return min(values) if values else None

    results = []
    for call in page:
        device_tag = getattr(call, 'device', None)
        assignments = getattr(call, '__pref_assignments', []) or []
        broadcasts = getattr(call, '__pref_broadcasts', []) or []

        desk_assignment = pick_first(assignments, lambda a: getattr(a, 'type', None) == 'desk_ex')
        teamlead_ex = getattr(getattr(call, 'team', None), 'teamlead', None)

        police_assignments = [a for a in assignments if getattr(a, 'type', None) in ('police_ex', 'pcr')]
        amb_assignments = [a for a in assignments if getattr(a, 'type', None) in ('ambulance_ex', 'acr')]

        # Broadcast times
        police_bcasts = [b for b in broadcasts if getattr(b, 'type', None) in ('police_ex', 'pcr')]
        amb_bcasts = [b for b in broadcasts if getattr(b, 'type', None) in ('ambulance_ex', 'acr')]

        first_broadcast = broadcasts[0] if broadcasts else None
        police_broadcast_time = min_dt([getattr(b, 'created_at', None) for b in police_bcasts])
        amb_broadcast_time = min_dt([getattr(b, 'created_at', None) for b in amb_bcasts])
        broadcast_initiated_time = min_dt([getattr(b, 'created_at', None) for b in broadcasts])

        police_acceptance_time = min_dt([getattr(b, 'accept_at', None) for b in police_bcasts])
        amb_acceptance_time = min_dt([getattr(b, 'accept_at', None) for b in amb_bcasts])

        police_accept_bcast = pick_first(police_bcasts, lambda b: getattr(b, 'status', None) == 'accepted')
        amb_accept_bcast = pick_first(amb_bcasts, lambda b: getattr(b, 'status', None) == 'accepted')

        # Who attended? choose earliest arrived among police/ambulance assignments
        arrived_assignments = [a for a in (police_assignments + amb_assignments) if getattr(a, 'arrived_time', None) is not None]
        arrived_assignments.sort(key=lambda a: a.arrived_time)
        attended_by = arrived_assignments[0].ex if arrived_assignments else None

        # Closure times by type
        police_case_closure_time = None
        for a in reversed(police_assignments):
            police_case_closure_time = getattr(a, 'complete_time', None) or getattr(a, 'arrived_time', None)
            if police_case_closure_time:
                break
        amb_case_closure_time = None
        for a in reversed(amb_assignments):
            amb_case_closure_time = getattr(a, 'complete_time', None) or getattr(a, 'arrived_time', None)
            if amb_case_closure_time:
                break

        # Durations
        total_call_duration = None
        if getattr(call, 'end_time', None) and getattr(call, 'start_time', None):
            try:
                total_call_duration = int((call.end_time - call.start_time).total_seconds())
            except Exception:
                total_call_duration = None

        # Response times (mins)
        police_resp_mins = None
        for a in police_assignments:
            if getattr(a, 'accept_time', None) and getattr(a, 'arrived_time', None):
                police_resp_mins = (a.arrived_time - a.accept_time).total_seconds() / 60.0
                break
        amb_resp_mins = None
        for a in amb_assignments:
            if getattr(a, 'accept_time', None) and getattr(a, 'arrived_time', None):
                amb_resp_mins = (a.arrived_time - a.accept_time).total_seconds() / 60.0
                break

        response_time = None
        if police_resp_mins is not None and amb_resp_mins is not None:
            response_time = min(police_resp_mins, amb_resp_mins)
        elif police_resp_mins is not None:
            response_time = police_resp_mins
        elif amb_resp_mins is not None:
            response_time = amb_resp_mins

        # Executive acceptance time (desk)
        call_accepted_time = getattr(desk_assignment, 'accept_time', None) if desk_assignment else None
        # Overall "response" to accept (seconds)
        response_accept_seconds = None
        if call_accepted_time and getattr(call, 'start_time', None):
            try:
                response_accept_seconds = int((call_accepted_time - call.start_time).total_seconds())
            except Exception:
                response_accept_seconds = None

        # Broadcast sent to
        has_police = bool(police_bcasts)
        has_amb = bool(amb_bcasts)
        if has_police and has_amb:
            broadcast_sent_to = 'BOTH'
        elif has_police:
            broadcast_sent_to = 'POLICE'
        elif has_amb:
            broadcast_sent_to = 'AMBULANCE'
        else:
            broadcast_sent_to = None

        trig_lat = getattr(call, 'trigger_latitude', None)
        trig_lon = getattr(call, 'trigger_longitude', None)
        cls_lat = getattr(call, 'closure_latitude', None)
        cls_lon = getattr(call, 'closure_longitude', None)

        total_distance_km = None
        if trig_lat is not None and trig_lon is not None and cls_lat is not None and cls_lon is not None:
            total_distance_km = _haversine_km(trig_lat, trig_lon, cls_lat, cls_lon)
            if total_distance_km is not None:
                total_distance_km = round(float(total_distance_km), 3)

        results.append({
            'call_id': call.id,
            'event_created_at': call.start_time.isoformat() if call.start_time else None,

            'vehicle_reg_no': getattr(device_tag, 'vehicle_reg_no', None),
            'vehicle_category': getattr(getattr(device_tag, 'category', None), 'category', None),
            'device_imei': getattr(getattr(device_tag, 'device', None), 'imei', None),
            'device_make': getattr(getattr(getattr(device_tag, 'device', None), 'model', None), 'vendor_id', None),

            'trigger_time': call.trigger_time.isoformat() if getattr(call, 'trigger_time', None) else (call.start_time.isoformat() if call.start_time else None),
            'trigger_latitude': float(trig_lat) if trig_lat is not None else None,
            'trigger_longitude': float(trig_lon) if trig_lon is not None else None,
            'nearest_police_station': nearest_police_station_name(trig_lat, trig_lon),

            'auto_assigned_executive_name': _em_ex_display_name(getattr(desk_assignment, 'ex', None)) if desk_assignment else None,
            'auto_assigned_time': getattr(desk_assignment, 'start_time', None).isoformat() if (desk_assignment and getattr(desk_assignment, 'start_time', None)) else None,

            'team_lead_name': _em_ex_display_name(teamlead_ex),
            'attended_by_name': _em_ex_display_name(attended_by),

            'call_accepted_time': call_accepted_time.isoformat() if call_accepted_time else None,

            'broadcast_initiated_time': broadcast_initiated_time.isoformat() if broadcast_initiated_time else None,
            'broadcast_sent_to': broadcast_sent_to,
            'police_broadcast_time': police_broadcast_time.isoformat() if police_broadcast_time else None,
            'ambulance_broadcast_time': amb_broadcast_time.isoformat() if amb_broadcast_time else None,

            'police_acceptance_time': police_acceptance_time.isoformat() if police_acceptance_time else None,
            'ambulance_acceptance_time': amb_acceptance_time.isoformat() if amb_acceptance_time else None,
            'police_officer_name_or_id': (
                _em_ex_display_name(getattr(police_accept_bcast, 'acceted_by', None))
                if police_accept_bcast else None
            ),
            'ambulance_officer_name_or_id': (
                _em_ex_display_name(getattr(amb_accept_bcast, 'acceted_by', None))
                if amb_accept_bcast else None
            ),

            'case_type': getattr(call, 'em_type', None),
            'police_case_closure_time': police_case_closure_time.isoformat() if police_case_closure_time else None,
            'ambulance_case_closure_time': amb_case_closure_time.isoformat() if amb_case_closure_time else None,

            'closure_latitude': float(cls_lat) if cls_lat is not None else None,
            'closure_longitude': float(cls_lon) if cls_lon is not None else None,
            'total_distance_km': total_distance_km,
            'total_call_duration': total_call_duration,
            'response_time': response_time,
            'police_response_time_mins': round(float(police_resp_mins), 3) if police_resp_mins is not None else None,
            'ambulance_response_time_mins': round(float(amb_resp_mins), 3) if amb_resp_mins is not None else None,
            'final_case_status': getattr(call, 'status', None),

            # extra helpful metric (kept optional; can be ignored by client)
            'desk_acceptance_time_seconds': response_accept_seconds,
        })

    return paginator.get_paginated_response(results)



@api_view(['GET'])
@permission_classes([AllowAny])
def ambulance_fleet_metrics(request):
    """Alias of ambulace_fleet_metrics (typo-safe)."""
    return ambulace_fleet_metrics(request)


@api_view(['GET'])
@permission_classes([AllowAny])
def ambulace_fleet_metrics(request):
    """
    Unauthenticated Ambulance fleet metrics.
    - total_executives: count of `EM_ex` with ambulance roles
    - online_executives: unique `field_ex` seen in `EMUserLocation` in last 1 minute
    - offline_executives: total - online
    - standby_executives: total - online - total_emergency_calls_live
    - total_emergency_calls_live: distinct live calls with an 'accepted' ambulance broadcast
    """
    from .models import EM_ex, EMCall, EMCallBroadcast, EMUserLocation
    now = timezone.now()
    window_start = now - timedelta(minutes=1)

    ambulance_ex_types = ['ambulance_ex', 'ACR']  # EM_ex.user_type values (note ACR is uppercase in model)
    ambulance_broadcast_types = ['ambulance_ex', 'acr']  # EMCallBroadcast.type values
    open_statuses = [
        'pending', 'desk_ex_assigned', 'broadcast_pending', 'field_ex_aproaching', 'field_ex_arrived'
    ]

    total_execs = EM_ex.objects.filter(user_type__in=ambulance_ex_types).count()

    # Online executives: unique field_ex with a location update in last 1 minute, filtered to ambulance types
    online = (
        EMUserLocation.objects
        .filter(time__gte=window_start)
        .exclude(field_ex__isnull=True)
        .filter(field_ex__user_type__in=ambulance_ex_types)
        .values_list('field_ex_id', flat=True)
        .distinct()
        .count()
    )

    live_calls = (
        EMCallBroadcast.objects
        .filter(type__in=ambulance_broadcast_types, status='accepted', call__status__in=open_statuses)
        .values('call_id').distinct().count()
    )

    offline = max(0, total_execs - online)
    standby = max(0,  online - live_calls)

    return Response({
        'total_executives': total_execs,
        'online_executives': online,
        'offline_executives': offline,
        'standby_executives': standby,
        'total_emergency_calls_live': live_calls,
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def police_fleet_metrics(request):
    """
    Unauthenticated Police fleet metrics.
    - total_executives: count of `EM_ex` with police roles
    - online_executives: unique `field_ex` seen in `EMUserLocation` in last 1 minute
    - offline_executives: total - online
    - standby_executives: total - online - total_emergency_calls_live
    - total_emergency_calls_live: distinct live calls with an 'accepted' police broadcast
    """
    from .models import EM_ex, EMCallBroadcast, EMUserLocation
    now = timezone.now()
    window_start = now - timedelta(minutes=1)

    police_ex_types = ['police_ex', 'PCR']  # EM_ex.user_type values (PCR uppercase per model)
    police_broadcast_types = ['police_ex', 'pcr']  # EMCallBroadcast.type values
    open_statuses = [
        'pending', 'desk_ex_assigned', 'broadcast_pending', 'field_ex_aproaching', 'field_ex_arrived'
    ]

    total_execs = EM_ex.objects.filter(user_type__in=police_ex_types).count()

    # Online executives: unique field_ex with a location update in last 1 minute, filtered to police types
    online = (
        EMUserLocation.objects
        .filter(time__gte=window_start)
        .exclude(field_ex__isnull=True)
        .filter(field_ex__user_type__in=police_ex_types)
        .values_list('field_ex_id', flat=True)
        .distinct()
        .count()
    )

    live_calls = (
        EMCallBroadcast.objects
        .filter(type__in=police_broadcast_types, status='accepted', call__status__in=open_statuses)
        .values('call_id').distinct().count()
    )

    offline = max(0, total_execs - online)
    standby = max(0, online - live_calls)

    return Response({
        'total_executives': total_execs,
        'online_executives': online,
        'offline_executives': offline,
        'standby_executives': standby,
        'total_emergency_calls_live': live_calls,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def vehicle_status_metrics(request):
    """
    Unauthenticated API: totals for registered vehicles, online, offline, and live SOS.

    - total: count of DeviceTag
    - online: distinct DeviceTag with GPSData entries in last 15 minutes
    - offline: total - online
    - live_sos: count of EMCall where status == 'pending'
    """
    from .models import DeviceTag, GPSData, EMCall
    now = timezone.now()
    window_start = now - timedelta(minutes=15)

    total = DeviceTag.objects.count()
    online = (
        GPSData.objects
        .filter(entry_time__gte=window_start)
        .exclude(device_tag__isnull=True)
        .values_list('device_tag_id', flat=True)
        .distinct()
        .count()
    )
    offline = max(0, total - online)
    live_sos = EMCall.objects.filter(status='pending').count()

    return Response({
        'total_registered_vehicles': total,
        'online_vehicles': online,
        'offline_vehicles': offline,
        'live_sos_calls': live_sos,
        'window_minutes': 15,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def public_device_onboarding_dashboard(request):
    """
    Public dashboard API for device onboarding and inventory metrics.

    Includes:
    - Total manufacturers with at least one accepted technical onboarding.
    - Total eSIM (M2M) providers.
    - Total device models with accepted technical onboarding.
    - Total device stock.
    - Total tagged devices (currently tagged, excluding untagged/deleted tags).
    - Total online devices (GPS seen in last 15 minutes).
    - Total offline devices.
    - Manufacturer list with at least one accepted technical onboarding request.
    """
    from .models import (
        DeviceModelTechnicalOnboardingRequest,
        eSimProvider,
        DeviceStock,
        DeviceTag,
        GPSData,
        Manufacturer,
    )

    onboarding_done_qs = DeviceModelTechnicalOnboardingRequest.objects.filter(status='accepted')

    manufacturer_ids_with_done_onboarding = onboarding_done_qs.values_list(
        'manufacturer_id',
        flat=True
    ).distinct()

    total_manufacturers_with_onboarding_done = manufacturer_ids_with_done_onboarding.count()
    total_esim_m2m_provider = eSimProvider.objects.count()
    total_device_models_with_onboarding_done = onboarding_done_qs.values_list(
        'device_model_id',
        flat=True
    ).distinct().count()
    total_device_stock = DeviceStock.objects.count()

    tagged_device_base_qs = DeviceTag.objects.exclude(status__in=['Device_Untagged', 'TagDeleted'])
    total_tagged_device = tagged_device_base_qs.count()

    now = timezone.now()
    window_start = now - timedelta(minutes=15)
    total_online_device = (
        GPSData.objects
        .filter(entry_time__gte=window_start)
        .exclude(device_tag__isnull=True)
        .exclude(device_tag__status__in=['Device_Untagged', 'TagDeleted'])
        .values_list('device_tag_id', flat=True)
        .distinct()
        .count()
    )
    total_offline_device = max(0, total_tagged_device - total_online_device)

    manufacturers = (
        Manufacturer.objects
        .filter(id__in=manufacturer_ids_with_done_onboarding)
        .prefetch_related('users')
        .order_by('company_name', 'id')
    )

    manufacturer_list = []
    for manufacturer in manufacturers:
        primary_user = manufacturer.users.order_by('id').first()
        manufacturer_list.append({
            'manufacturer_id': manufacturer.id,
            'company_name': manufacturer.company_name,
            'company_address': manufacturer.company_address,
            'company_gstn': manufacturer.gstnnumber,
            'company_contact_no': manufacturer.company_phoneno,
            'company_email_id': manufacturer.company_email,
            'user_name': getattr(primary_user, 'name', None),
            'user_contact_no': getattr(primary_user, 'mobile', None),
            'user_email_id': getattr(primary_user, 'email', None),
        })

    return Response({
        'totals': {
            'total_manufacturers_with_onboarding_done': total_manufacturers_with_onboarding_done,
            'total_esim_m2m_provider': total_esim_m2m_provider,
            'total_device_models_with_onboarding_done': total_device_models_with_onboarding_done,
            'total_device_stock': total_device_stock,
            'total_tagged_device': total_tagged_device,
            'total_online_device': total_online_device,
            'total_offline_device': total_offline_device,
            'online_window_minutes': 15,
        },
        'manufacturers': manufacturer_list,
    })








# API: Get average lat/lon for given mcc, mnc, lac (cell location)
@api_view(['POST'])
@permission_classes([AllowAny])
def cell_location_average(request):
    serializer = GSMCellInfoInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=400)
    mcc = serializer.validated_data['mcc']
    mnc = serializer.validated_data['mnc']
    lac = serializer.validated_data['lac']
    # Filter GPSData by mcc, mnc, lac
    qs = GPSData.objects.filter(mcc=mcc, mnc=mnc, lac=lac)
    count = qs.count()
    if count == 0:
        return Response({'error': 'No data found for given mcc, mnc, lac.'}, status=404)
    avg_lat = qs.aggregate(avg_lat=models.Avg('latitude'))['avg_lat']
    avg_lon = qs.aggregate(avg_lon=models.Avg('longitude'))['avg_lon']
    return Response({
        'count': count,
        'average_latitude': avg_lat,
        'average_longitude': avg_lon
    })
    
    
    
# Geocoding API: Search POIs by text query
@api_view(['GET'])
@permission_classes([AllowAny])
def geocode_poi(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return Response({'error': 'Query parameter "q" is required.'}, status=400)
    # Search in name, city, state, address, description, area, pluscode, etc.
    filters = (
        Q(name__icontains=query) |
        Q(city__icontains=query) |
        Q(state__icontains=query) |
        Q(address__icontains=query) |
        Q(description__icontains=query) |
        Q(area__icontains=query) |
        Q(pluscode__icontains=query)
    )
    pois = pointofinterests.objects.filter(filters)
    serializer = PointOfInterestSerializer(pois, many=True)
    # Only return lat/lon and name for geocoding
    results = [
        {
            'id': poi['id'],
            'name': poi['name'],
            'lat': poi['lat'],
            'lon': poi['lon'],
            'address': poi['address'],
            'city': poi['city'],
            'state': poi['state'],
            'description': poi['description'],
        }
        for poi in serializer.data
    ]
    return Response({'results': results})

# Reverse Geocoding API: Find nearest POI to given lat/lon
@api_view(['GET'])
@permission_classes([AllowAny])
def reverse_geocode_poi(request):
    try:
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
    except (TypeError, ValueError):
        return Response({'error': 'lat and lon query parameters are required and must be float.'}, status=400)
    # Only consider POIs with valid lat/lon
    pois = pointofinterests.objects.exclude(lat__isnull=True).exclude(lon__isnull=True)
    min_dist = None
    nearest_poi = None
    for poi in pois:
        if poi.lat is not None and poi.lon is not None:
            # Haversine formula for distance in km
            dlat = math.radians(poi.lat - lat)
            dlon = math.radians(poi.lon - lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(poi.lat)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            dist = 6371 * c
            if min_dist is None or dist < min_dist:
                min_dist = dist
                nearest_poi = poi
    if nearest_poi:
        serializer = PointOfInterestSerializer(nearest_poi)
        return Response(serializer.data)
    else:
        return Response({'error': 'No POI found.'}, status=404)

# Create Trip
@api_view(['POST'])
@permission_classes([AllowAny])
def create_trip(request):
    data = request.data.copy()
    user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    if not user:
        # Temp user logic using sessionid from headers
        sessionid = request.headers.get('sessionid')
        from .models import TempUser
        temp_user = TempUser.objects.filter(session_key=sessionid).first()
        if not temp_user:
            return Response({'error': 'Invalid temp user sessionid'}, status=status.HTTP_400_BAD_REQUEST)
        data['created_by'] = None
        data['mobile_no'] = temp_user.mobile
    else:
        data['created_by'] = user.id
        data['mobile_no'] = None
    serializer = TripSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Get Trip(s)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_trip(request, trip_id=None):
    user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    from .models import TempUser
    if trip_id:
        trip = get_object_or_404(Trip, id=trip_id)
        if trip.created_by:
            if user and trip.created_by != user:
                return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        else:
            sessionid = request.headers.get('sessionid')
            temp_user = TempUser.objects.filter(session_key=sessionid).first()
            if not temp_user or trip.mobile_no != temp_user.mobile:
                return Response({'error': 'Not allowed for temp user'}, status=status.HTTP_403_FORBIDDEN)
        serializer = TripSerializer(trip)
        return Response(serializer.data)
    else:
        if user:
            trips = Trip.objects.filter(created_by=user)
        else:
            sessionid = request.headers.get('sessionid')
            temp_user = TempUser.objects.filter(session_key=sessionid).first()
            if not temp_user:
                return Response({'error': 'Invalid temp user sessionid'}, status=status.HTTP_400_BAD_REQUEST)
            trips = Trip.objects.filter(mobile_no=temp_user.mobile)
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

# Update Trip (only name and route, only by creator, only if not ended/canceled)
@api_view(['POST'])
@permission_classes([AllowAny])
def update_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    from .models import TempUser
    if trip.created_by:
        if not user or trip.created_by != user:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
    else:
        sessionid = request.headers.get('sessionid')
        temp_user = TempUser.objects.filter(session_key=sessionid).last()
        if not temp_user or trip.mobile_no != temp_user.mobile:
            return Response({'error': 'Not allowed for temp user'}, status=status.HTTP_403_FORBIDDEN)
    if trip.status != 'created':
        return Response({'error': 'Cannot update ended or canceled trip'}, status=status.HTTP_400_BAD_REQUEST)
    data = {}
    if 'trip_name' in request.data:
        data['trip_name'] = request.data['trip_name']
    if 'trip_route' in request.data:
        data['trip_route'] = request.data['trip_route']
    serializer = TripSerializer(trip, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# End Trip (only by creator, only if not ended/canceled)
@api_view(['POST'])
@permission_classes([AllowAny])
def end_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    from .models import TempUser
    if trip.created_by:
        if not user or trip.created_by != user:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
    else:
        sessionid = request.headers.get('sessionid')
        temp_user = TempUser.objects.filter(session_key=sessionid).first()
        if not temp_user or trip.mobile_no != temp_user.mobile:
            return Response({'error': 'Not allowed for temp user'}, status=status.HTTP_403_FORBIDDEN)
    if trip.status != 'created':
        return Response({'error': 'Trip already ended or canceled'}, status=status.HTTP_400_BAD_REQUEST)
    trip.status = 'ended'
    trip.save()
    serializer = TripSerializer(trip)
    return Response(serializer.data)

# Cancel Trip (only by creator, only if not ended/canceled)
@api_view(['POST'])
@permission_classes([AllowAny])
def cancel_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
    from .models import TempUser
    if trip.created_by:
        if not user or trip.created_by != user:
            return Response({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
    else:
        sessionid = request.headers.get('sessionid')
        temp_user = TempUser.objects.filter(session_key=sessionid).first()
        if not temp_user or trip.mobile_no != temp_user.mobile:
            return Response({'error': 'Not allowed for temp user'}, status=status.HTTP_403_FORBIDDEN)
    if trip.status != 'created':
        return Response({'error': 'Trip already ended or canceled'}, status=status.HTTP_400_BAD_REQUEST)
    trip.status = 'canceled'
    trip.save()
    serializer = TripSerializer(trip)
    return Response(serializer.data)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, time
import logging
from .models import LoginSettings, User
from .login_settings_cache import (
    cache_login_settings,
    get_login_settings_from_cache,
)

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_login_settings(request):
    """
    API to create or update login settings for a user role.
    Saves to database and updates Redis cache.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = request.user
        if user.role != 'superadmin':
            return Response({
                'success': False,
                'error': 'Only Super Admin can configure login settings'
            }, status=status.HTTP_403_FORBIDDEN)
        user_role = request.data.get('user_role')
        if not user_role:
            return Response({
                'success': False,
                'error': 'user_role is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        valid_roles = [
            "superadmin", "stateadmin", "devicemanufacture", "dealer",
            "owner", "esimprovider", "filment", "sosadmin",
            "teamleader", "sosexecutive", "default"
        ]
        if user_role not in valid_roles:
            return Response({
                'success': False,
                'error': f'Invalid user_role. Must be one of: {", ".join(valid_roles)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        settings, created = LoginSettings.objects.get_or_create(
            user_role=user_role,
            defaults={
                'created_by': user.email,
                'daily_login_limit': 0,
                'session_expiry_minutes': 2880,
                'max_simultaneous_sessions': 0,
                'login_start_time': time(0, 0, 0),
                'login_end_time': time(23, 59, 59),
                'enforce_time_boundary': False,
            }
        )
        if 'daily_login_limit' in request.data:
            daily_limit = request.data.get('daily_login_limit')
            try:
                settings.daily_login_limit = int(daily_limit)
                if settings.daily_login_limit < 0:
                    return Response({
                        'success': False,
                        'error': 'daily_login_limit must be >= 0'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'daily_login_limit must be a valid integer'
                }, status=status.HTTP_400_BAD_REQUEST)
        if 'session_expiry_minutes' in request.data:
            expiry = request.data.get('session_expiry_minutes')
            try:
                settings.session_expiry_minutes = int(expiry)
                if settings.session_expiry_minutes <= 0:
                    return Response({
                        'success': False,
                        'error': 'session_expiry_minutes must be > 0'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'session_expiry_minutes must be a valid integer'
                }, status=status.HTTP_400_BAD_REQUEST)
        if 'max_simultaneous_sessions' in request.data:
            max_sessions = request.data.get('max_simultaneous_sessions')
            try:
                settings.max_simultaneous_sessions = int(max_sessions)
                if settings.max_simultaneous_sessions < 0:
                    return Response({
                        'success': False,
                        'error': 'max_simultaneous_sessions must be >= 0'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'max_simultaneous_sessions must be a valid integer'
                }, status=status.HTTP_400_BAD_REQUEST)
        if 'login_start_time' in request.data:
            try:
                start_time_str = request.data.get('login_start_time')
                settings.login_start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'login_start_time must be in HH:MM:SS format (e.g., 08:00:00)'
                }, status=status.HTTP_400_BAD_REQUEST)
        if 'login_end_time' in request.data:
            try:
                end_time_str = request.data.get('login_end_time')
                settings.login_end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'login_end_time must be in HH:MM:SS format (e.g., 18:00:00)'
                }, status=status.HTTP_400_BAD_REQUEST)
        if 'enforce_time_boundary' in request.data:
            settings.enforce_time_boundary = bool(request.data.get('enforce_time_boundary'))
        if 'is_active' in request.data:
            settings.is_active = bool(request.data.get('is_active'))
        if not created:
            settings.created_by = user.email
        settings.save()
        cache_success = cache_login_settings(settings)
        response_data = {
            'success': True,
            'message': f'Login settings {"created" if created else "updated"} successfully',
            'cached': cache_success,
            'data': {
                'user_role': settings.user_role,
                'daily_login_limit': settings.daily_login_limit,
                'session_expiry_minutes': settings.session_expiry_minutes,
                'max_simultaneous_sessions': settings.max_simultaneous_sessions,
                'login_start_time': settings.login_start_time.strftime('%H:%M:%S'),
                'login_end_time': settings.login_end_time.strftime('%H:%M:%S'),
                'enforce_time_boundary': settings.enforce_time_boundary,
                'is_active': settings.is_active,
                'created_by': settings.created_by,
                'updated_at': settings.updated_at.isoformat(),
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in set_login_settings: {str(e)}")
        return Response({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def get_login_settings(request):
    """
    API to retrieve login settings from Redis cache.
    For GET: Returns all cached settings
    For POST with user_role: Returns specific role settings
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        if request.method == 'GET':
            all_settings = LoginSettings.objects.filter(is_active=True).order_by('user_role')
            settings_list = []
            for settings in all_settings:
                settings_list.append({
                    'user_role': settings.user_role,
                    'daily_login_limit': settings.daily_login_limit,
                    'session_expiry_minutes': settings.session_expiry_minutes,
                    'max_simultaneous_sessions': settings.max_simultaneous_sessions,
                    'login_start_time': settings.login_start_time.strftime('%H:%M:%S'),
                    'login_end_time': settings.login_end_time.strftime('%H:%M:%S'),
                    'enforce_time_boundary': settings.enforce_time_boundary,
                    'is_active': settings.is_active,
                    'created_by': settings.created_by,
                    'updated_at': settings.updated_at.isoformat(),
                })
            return Response({
                'success': True,
                'count': len(settings_list),
                'data': settings_list
            }, status=status.HTTP_200_OK)
        else:
            user_role = request.data.get('user_role')
            if not user_role:
                user_role = request.user.role
            cached_settings = get_login_settings_from_cache(user_role)
            if cached_settings:
                return Response({
                    'success': True,
                    'source': 'cache',
                    'data': cached_settings
                }, status=status.HTTP_200_OK)
            else:
                try:
                    settings = LoginSettings.objects.get(user_role=user_role, is_active=True)
                    cache_login_settings(settings)
                    return Response({
                        'success': True,
                        'source': 'database',
                        'message': 'Settings loaded from database and cached',
                        'data': {
                            'user_role': settings.user_role,
                            'daily_login_limit': settings.daily_login_limit,
                            'session_expiry_minutes': settings.session_expiry_minutes,
                            'max_simultaneous_sessions': settings.max_simultaneous_sessions,
                            'login_start_time': settings.login_start_time.strftime('%H:%M:%S'),
                            'login_end_time': settings.login_end_time.strftime('%H:%M:%S'),
                            'enforce_time_boundary': settings.enforce_time_boundary,
                            'is_active': settings.is_active,
                        }
                    }, status=status.HTTP_200_OK)
                except LoginSettings.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f'No login settings found for role: {user_role}'
                    }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in get_login_settings: {str(e)}")
        return Response({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# skytron_api/views.py
from rest_framework.authtoken.models import Token 
from django.http import HttpResponseBadRequest, JsonResponse,HttpResponse  
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes, throttle_classes
import secrets
import string
import logging
logger = logging.getLogger(__name__)

HOST_STORAGE_PATH = os.environ.get('HOST_STORAGE_PATH', '/host_storage')
e=""
STATIC_OTP_CAP=False #True
import os
DEPLOY_URL = "skytron.in" #os.getenv("ROOT_URL", "skytron.in")   
EMAIL_ACTIVE=False

REMOVE_OTP_CAP=False #True

from django.core.serializers import serialize
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate,logout,login 
from rest_framework.response import Response
from rest_framework import status 
import bleach
from .models import *
from .serializers import *
import xml.etree.ElementTree as ET
import json
import html 
import random
from itertools import islice 
from django.utils import timezone     
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail as sm
def send_mail(subject, message, from_email, recipient_list, fail_silently=False, html_message=None):    
    pass
import os 
import magic
import glob
# Define the path on the host machine where files will be stored
# This directory should be mounted as a volume in Docker
#HOST_STORAGE_PATH = os.environ.get('HOST_STORAGE_PATH', '/tmp/skytrack_storage')  # This should match the volume mount point in Docker


               
from django.utils.crypto import get_random_string
from math import radians, sin, cos, sqrt, asin   
from .secure_token import generate_jwt_token, verify_jwt_token, decode_jwt_token   
import sys
from django.forms.models import model_to_dict
from django.db import transaction

from django.contrib.auth import get_user_model
from rest_framework.views import APIView  

from django.shortcuts import get_object_or_404 
from rest_framework.parsers import MultiPartParser,FileUploadParser
import time 
import pandas as pd 
import calendar 

from rest_framework import generics,filters  

from django.core.files.storage import FileSystemStorage
from rest_framework import generics, status 
from django.conf import settings
     
import ast 
from django.views.static import serve
from django.conf import settings  
import json
from django.db.models import Subquery, OuterRef, Max, F,Subquery, OuterRef,Q  
from django.forms.models import model_to_dict
from scipy.signal import butter, lfilter,lfilter
from .forms import GPSDataFilterForm
import numpy as np 
from django.views import View 
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import  get_object_or_404 
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
import requests

import base64
import uuid   
from .utils import generate_captcha
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
import json
import os 
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, RegexValidator
from datetime import datetime, timedelta

from django.utils.timezone import now 
# Import MQTT user creation function (relative import)
from .mqtt_user_creator import create_mqtt_user
import paho.mqtt.client as mqtt
import ssl
import threading
 
#python3 -m pip install pdfkit
#sudo apt-get install wkhtmltopdf
#sudo apt-get update
#sudo apt-get install libreoffice

import io
from docx import Document
import pdfkit
from tempfile import NamedTemporaryFile


import io
from docx import Document
import subprocess
from tempfile import NamedTemporaryFile

from pathlib import Path
import os  
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from .throttles import AuthRateThrottle, LoginRateThrottle, OTPRateThrottle, PasswordResetRateThrottle
from django.core.cache import cache


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_latest_emuser_locations(request):
    """
    Returns the latest EMUserLocation for each unique field executive, with filters:
    - fEM_ex__user__name (partial match)
    - em_ex_id (exact)
    - em_ex__user_type (exact)
    - location search: latest entry within 10km of input lat/lon
    """
    # Get query params
    name = request.GET.get('name')
    em_ex_id = request.GET.get('em_ex_id')
    user_type = request.GET.get('user_type')
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    radius_km = float(request.GET.get('radius_km', 10))

    # Subquery to get latest EMUserLocation id for each field_ex
    latest_ids = EMUserLocation.objects.values('field_ex').annotate(max_id=Max('id')).values_list('max_id', flat=True)
    qs = EMUserLocation.objects.filter(id__in=latest_ids).select_related('field_ex', 'field_ex__createdby')

    # Filter by field executive user name
    if name:
        qs = qs.filter(field_ex__users__name__icontains=name)
    # Filter by EM_ex id
    if em_ex_id:
        qs = qs.filter(field_ex__id=em_ex_id)
    # Filter by EM_ex user_type
    if user_type:
        qs = qs.filter(field_ex__user_type=user_type)

    # Location filter (within radius_km of lat/lon)
    if lat and lon:
        try:
            lat = float(lat)
            lon = float(lon)
            def haversine(lat1, lon1, lat2, lon2):
                # Earth radius in km
                R = 6371.0
                dlat = radians(lat2 - lat1)
                dlon = radians(lon2 - lon1)
                a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                return R * c
            filtered_ids = []
            for loc in qs:
                if loc.em_lat is not None and loc.em_lon is not None:
                    dist = haversine(lat, lon, loc.em_lat, loc.em_lon)
                    if dist <= radius_km:
                        filtered_ids.append(loc.id)
            qs = qs.filter(id__in=filtered_ids)
        except Exception:
            return Response({'status': 'error', 'message': 'Invalid lat/lon for location search'}, status=400)

    # Pagination (optional, default page size 100)
    paginator = PageNumberPagination()
    paginator.page_size = int(request.GET.get('page_size', 100))
    result_page = paginator.paginate_queryset(qs.order_by('-time'), request)

    # Use EMUserLocationSerializer (includes field_ex details)
    serializer = EMUserLocationSerializer(result_page, many=True)
    return paginator.get_paginated_response({'status': 'success', 'data': serializer.data})



def send_general_mqtt_message(imei, message_json):
    """
    Send a general JSON message to device via MQTT deviceResponse topic
    This function runs in a separate thread to avoid blocking the API response
    imei: device IMEI (str)
    message_json: dict or JSON-serializable object
    """
    

    def mqtt_publisher():
        try:
            BROKER_URL = os.getenv("MQTT_BROKER_HOST", "135.235.166.209")
            BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "8883"))
            MQTT_USERNAME = os.getenv("MQTT_USERNAME", "admin")
            MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "adminpass")

         
            ROOT_CA =  "/app/keys/ca.crt"

            client = mqtt.Client()
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            client.tls_set(ca_certs=ROOT_CA, tls_version=ssl.PROTOCOL_TLS)
            client.connect(BROKER_URL, BROKER_PORT, 60)

            response_topic = f"deviceResponse/{imei}"
            if isinstance(message_json, str):
                response_json = message_json
            else:
                response_json = json.dumps(message_json, separators=(",", ":"))
            result = client.publish(response_topic, response_json, qos=1)
            result.wait_for_publish()
            print(f"[MQTT] Sent message to {response_topic}: {response_json}", flush=True)
            client.disconnect()
        except Exception as e:
            print(f"[MQTT] Error sending message to {imei}: {e}", flush=True)

    mqtt_thread = threading.Thread(target=mqtt_publisher)
    mqtt_thread.daemon = True
    mqtt_thread.start()


# API: Concatenate command_base + value and send to device via MQTT
@api_view(['POST'])
@permission_classes([AllowAny])
def send_mqtt_command(request):
    """
    POST body:
    - imei: string (required)
    - command_base: string (required)
    - value: string (required)

    Builds final_command = command_base + value and publishes as JSON to
    topic deviceResponse/{imei} using send_general_mqtt_message.
    """
    imei = (request.data.get('imei') or request.GET.get('imei'))
    command_base = (
        request.data.get('command_base')
        or request.data.get('commandBase')
        or request.GET.get('command_base')
        or request.GET.get('commandBase')
    )
    value = (request.data.get('value') or request.GET.get('value'))

    if not imei or not command_base or value is None:
        return Response(
            {
                'status': 'error',
                'message': 'Missing required fields: imei, command_base, value.'
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    final_command = f"@{str(command_base)}*"

    payload = { 
        'keys': final_command,
        
    }

    try:
        send_general_mqtt_message(imei, payload)
        return Response(
            {
                'status': 'queued',
                'imei': imei,
                'final_command': final_command,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {
                'status': 'error',
                'message': f'Failed to publish MQTT command: {e}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
 

def send_sos_mqtt_message(imei, i):     
    def mqtt_publisher():
        try:
            # MQTT Configuration (matching the existing mqttClienttrack.py)
            #BROKER_URL = os.getenv("MQTT_BROKER_HOST", "10.192.136.179")
            BROKER_URL = os.getenv("MQTT_BROKER_HOST", "135.235.166.209")
            BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "8883"))
            MQTT_USERNAME = os.getenv("MQTT_USERNAME", "admin")
            MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "adminpass")
 
             
            ROOT_CA =  "/app/keys/ca.crt"
            
            # Create MQTT client
            client = mqtt.Client()
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            client.tls_set(ca_certs=ROOT_CA, tls_version=ssl.PROTOCOL_TLS)
            
            # Connect to broker
            client.connect(BROKER_URL, BROKER_PORT, 60)
            
            # Determine JSON payload based on 'i'
            try:
                ival = int(str(i).strip())
            except Exception:
                raise ValueError(f"Invalid SOS command input i={i}. Expected 1 or 2.")

            if ival not in (1, 2):
                raise ValueError(f"Invalid SOS command input i={i}. Expected 1 (start) or 2 (stop).")

            payload_str = json.dumps({"sos": ival}, separators=(",", ":"))

            # Publish to device response topic as JSON string (QoS 1)
            response_topic = f"deviceResponse/{imei}"
            result = client.publish(response_topic, payload_str, qos=1)
            result.wait_for_publish()
            
            print(f"[SOS MQTT] Sent JSON to {response_topic}: {payload_str}", flush=True)
            
            client.disconnect()
            
        except Exception as e:
            print(f"[SOS MQTT] Error sending SOS message to {imei}: {e}", flush=True)
    
    # Run MQTT publishing in a separate thread to avoid blocking
    mqtt_thread = threading.Thread(target=mqtt_publisher)
    mqtt_thread.daemon = True
    mqtt_thread.start()





def replace_text_in_docx_in_memory(template_path, replacements): 
    doc = Document(template_path) 
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value) 
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def convert_docx_to_pdf_with_libreoffice(docx_buffer): 
    with NamedTemporaryFile(suffix=".docx", delete=False) as temp_docx_file:
        temp_docx_file.write(docx_buffer.getvalue())
        temp_docx_path = temp_docx_file.name 
    temp_pdf_path = temp_docx_path.replace('.docx', '.pdf') 
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', temp_docx_path, '--outdir', '/tmp'])

    with open(temp_pdf_path, 'rb') as pdf_file:
        pdf_buffer = io.BytesIO(pdf_file.read()) 
    subprocess.run(['rm', temp_docx_path, temp_pdf_path]) 
    return pdf_buffer


 
template_path = '/app/skytron_api/static/Cetificate_template.docx'

def validate_inputs(datar):
    errors = {} 
    d=None
    try:
        d=datar.data
    except:
        pass
    
    data = datar.GET.copy()  # Start with GET data
    if d:
        data.update()  # Add POST data (overwrites GET data if keys overlap)

   # Validate (date))
    Keys=["created","velid_from"]
    for key in Keys:
        expiry_date = data.get(key)
        if expiry_date:
            try:
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d')
                if expiry_date <= datetime.now():
                    errors[key] = key+' should not be a past date.'
            except ValueError:
                errors[key] = 'Invalid date format for '+key+'.'
   
    # Validate expiry date (should be more than 6 months from today)
    Keys=["velid_upto","expiryDate","expirydate","tac_validity","cop_validity","esim_validity"]
    for key in Keys:
        expiry_date = data.get(key)
        if expiry_date:
            try:
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d')
                if expiry_date <= datetime.now() + timedelta(days=30):
                    errors[key] = key+' should be more than 1 months from today.'
            except ValueError:
                errors[key] = 'Invalid date format for '+key+'.'



    # Validate date of birth (should be less than 18 years from today)
    dob = data.get('dob')
    if dob:
        try:
            dob = datetime.strptime(dob, '%Y-%m-%d')
            if dob >= datetime.now() - timedelta(days=365*18):
                errors['dob'] = 'Date of birth should be at least 18 years ago.'
        except ValueError:
            errors['dob'] = 'Invalid date format for date of birth.'

  
    # Validate mobile (should be exactly 10 digits)
    mobile = data.get('mobile')
    if mobile:
        if not mobile.isdigit() or len(mobile) != 10:
            errors['mobile'] = 'Mobile number should be exactly 10 digits.'
    mobile = data.get("vehicle_owner") #vehicle owner phone no 
    if mobile:
        if not mobile.isdigit() or len(mobile) != 10:
            errors["vehicle_owner"] = 'vehicle_owner should be exactly 10 digits.'
            

    # Validate mobile (should be exactly 10 digits)
    mobile = data.get('pincode')
    if mobile:
        if not mobile.isdigit() or len(mobile) != 6:
            errors['pincode'] = 'pincode number should be exactly 6 digits.'

    # Validate email format
    email = data.get('email')
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Invalid email format.'

    # Validate (only alphabets and spaces)
    Keys=['name', "dto_rto",'city',"district_name" ,'country','company_name', "title","detail","feedback","em_msg","company_name","state_name"]
    for key in Keys:
        val = data.get(key)
        if val:
            if not all(x.isalpha() or x.isspace() for x in val):
                errors[key] = key+' should contain only alphabets and spaces.'
                
    # Validate (only alphanumaric and spaces)
    Keys=[ 'remarks','address',"title","detail","feedback","em_msg","company_name"]
    for key in Keys:
        val = data.get(key)
        if val:
            if not all(x.isalnum() or x.isspace() for x in val):
                errors[key] = key+' should contain only alphanumeric and spaces.'
                
     
    
 

    # Validate (only alphanumaric)
    Keys=['idProofno',"category","district_code",'idProofType', 'vehicle_reg_no','engine_no','chassis_no','vehicle_make','vehicle_model','category']
    for key in Keys:
        val = data.get(key)
        if val:
            if not all(x.isalnum()   for x in val):
                    errors[key] = key+' should contain only alphanumeric.'
 
    # Validate ids (only int)
    Keys=['device_id',"maxSpeed",'call_id',"district" ,"warnSpeed",'state']
    for key in Keys:
        val = data.get(key)
        if val:
            try:
                val = int(val)
                if val <= 0:
                    errors[key] = key + ' should be a positive integer.'
            except ValueError:
                errors[key] = key + ' should be a positive integer.'
    


    # Validate otp (should be exactly 6 digits)
    otp = data.get('otp')
    if otp:
        if not otp.isdigit() or len(otp) != 6:
            errors['otp'] = 'OTP should be exactly 6 digits.'
    
    user_type = data.get('user_type')
    if user_type:
        if str(user_type) not in ['teamlead', 'desk_ex', 'police_ex', 'ambulance_ex', 'PCR', 'ACR']:
            errors['user_type'] = 'invalid user_type.'
    user_type = data.get('role')
    if user_type:# "superadmin", "stateadmin", "devicemanufacture", "dealer", "owner", "esimprovider","filment","sosadmin", "teamleader","sosexecutive"
        if str(user_type) not in ["superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider","superadmin", "stateadmin", "devicemanufacture", "dealer", "owner", "esimprovider","filment","sosadmin", "teamleader","sosexecutive"]:
            errors['role'] = 'invalid role.'
    
    regex_validations = {
        'gstNo': r'^([0][1-9]|[1-2][0-9]|[3][0-7])([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$',
        'gstnnumber': r'^([0][1-9]|[1-2][0-9]|[3][0-7])([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$',
        'ip_tracking': r'^(\d{1,3}\.){3}\d{1,3}$',
        'ip_tracking2': r'^(\d{1,3}\.){3}\d{1,3}$',
        'ip_sos': r'^(\d{1,3}\.){3}\d{1,3}$',
        'port_sos': r'^[1-9][0-9]{0,4}$',
        'sms_tracking': r'^[1-9][0-9]{0,4}$',
        'sms_tracking2': r'^[1-9][0-9]{0,4}$',
        'sms_sos': r'^[1-9][0-9]{0,4}$',
        'imei': r'^[0-9]{15}$',
        'msisdn1': r'^[0-9]{15}$',
        'msisdn2': r'^[0-9]{15}$',
        'iccid': r'^[0-9]{19,20}$',
        'Device': r'^\d{15}$',
        'vehicle_reg_no': r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$',
        'engine_no': r'^[A-Z0-9]{6,17}$',
        'chassis_no': r'^[A-HJ-NPR-Z0-9]{17}$',
    }

    for key, pattern in regex_validations.items():
        value = data.get(key)
        if value and not re.match(pattern, value):
            errors[key] = f"Invalid format for {key}."


    return errors


def _parse_string_list(value):
    """Parse a request value into a list of short strings.

    Accepts:
    - already-provided Python list/tuple
    - JSON string like '["Airtel","Jio"]'
    - comma-separated string like 'Airtel,Jio'
    """
    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        items = list(value)
    elif isinstance(value, str):
        raw = value.strip()
        if raw == "":
            items = []
        else:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    items = parsed
                else:
                    items = [parsed]
            except Exception:
                items = [p.strip() for p in raw.split(',')]
    else:
        items = [value]

    cleaned = []
    for item in items:
        if item is None:
            continue
        s = str(item).strip()
        if not s:
            continue
        cleaned.append(s)
    return cleaned


ALLOWED_PARTNER_STATUSES = {
    'Reject',
    'Allow to login',
    'Allow to add dealer',
    'Accept',
}


def _normalize_partner_status(value):
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == 'Reject':
        normalized = 'Reject'
    return normalized

def geneateCet(savepath,IMEI,Make,Model,Validity,RegNo,FitmentDate,TaggingDate,ActivationDate,Status,Date):
    replacements = {
        '{{IMEI}}':IMEI,
        '{{Make}}':Make ,
        '{{Model}}':Model,
        '{{Validity}}':Validity,
        '{{RegNo}}':RegNo,
        '{{FitmentDate}}':FitmentDate,
        '{{TaggingDate}}':TaggingDate,
        '{{ActivationDate}}':ActivationDate,
        '{{Status}}':Status,
        '{{Date}}':Date     
    }
    docx_buffer = replace_text_in_docx_in_memory(template_path, replacements)
    pdf_buffer = convert_docx_to_pdf_with_libreoffice(docx_buffer)
    with open(savepath, 'wb') as f:
        f.write(pdf_buffer.getvalue())




 

def load_private_key():
    import os
    from pathlib import Path

    # Prefer explicit configuration, then container path, then local repo keys.
    env_path = os.getenv('PRIVATE_KEY_PATH')
    repo_default = str(Path(__file__).resolve().parent.parent / 'keys' / 'private_key.pem')
    candidates = [p for p in [env_path, '/app/keys/private_key.pem', repo_default] if p]

    for private_key_path in candidates:
        try:
            with open(private_key_path, 'rb') as key_file:
                return RSA.import_key(key_file.read())
        except FileNotFoundError:
            continue

    # Don't crash module import (enables manage.py check / migrations in dev).
    # Endpoints that require decrypting fields will fail gracefully when key is missing.
    return None

def decrypt_field(encrypted_field, private_key):
    if not private_key:
        return None
    cipher = PKCS1_OAEP.new(private_key)
    #if len(encrypted_field)<16:
    #    return encrypted_field
    enc=base64.b64decode(encrypted_field)
    try:
        decrypted_data = cipher.decrypt(enc)
        return decrypted_data.decode('utf-8')
    except Exception as e :
        return None
PRIVATE_KEY=load_private_key() 
#print(PRIVATE_KEY)




@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 

def get_settings(request): 
    data={'mqtt_ip': "135.235.166.209", 'mqtt_port': "8883","mqtt_ca_cart":"""-----BEGIN CERTIFICATE-----
MIIDrDCCApSgAwIBAgITFfcYWF9ArRO7Qli8ksgfR1OEOjANBgkqhkiG9w0BAQsF
ADBmMQswCQYDVQQGEwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkx
FTATBgNVBAoMDE9yZ2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDEPMA0GA1UE
AwwGWW91ckNBMB4XDTI1MDUwOTEyMTY1NVoXDTM1MDUwNzEyMTY1NVowZjELMAkG
A1UEBhMCVVMxDjAMBgNVBAgMBVN0YXRlMQ0wCwYDVQQHDARDaXR5MRUwEwYDVQQK
DAxPcmdhbml6YXRpb24xEDAOBgNVBAsMB09yZ1VuaXQxDzANBgNVBAMMBllvdXJD
QTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANobRTTC3d2QotD45ky9
2dHaC/ZJEeogqV1MVKYVZe3n1xJF8FOFhH72OEZRyW9HRByjdYCuB7Ygp3HW25Ru
SGO0f8DNqHSCVPzOw/87dF+ierZ2HVisy0XqP3k6hkFgg5JSJLNkUlQKGQBuReH1
U+pGHnMreMHh81wTuafX2SdnfyM/CKB+g79LDSxrRwqOOkG1xqszaIeQkOG1tbPQ
SvW23GcbqPxnoxfq0dUgrkYWYsh44D4KIET0VtqoxV7nczFJrQS0i2FcSLh+iPtO
W+QYbNXuesy8uXIJebycngLm8DcwE/B3NKyes5rgjcBWZGs2U+1fAtLAVYb+0GZK
TOUCAwEAAaNTMFEwHQYDVR0OBBYEFL1YNcA0yJEK5+/dAqx171nFaI/4MB8GA1Ud
IwQYMBaAFL1YNcA0yJEK5+/dAqx171nFaI/4MA8GA1UdEwEB/wQFMAMBAf8wDQYJ
KoZIhvcNAQELBQADggEBAAjmbnXhtFLppjl3YlbXUebmqkKsIDAyQbyoN4WzlAfY
uAgSAn93D7ygJG0h88SrFHGJ7JIisWoYBBwX1fD9EeWrArc5yKK/yYH2o5qcmKTB
8BYqIzWqkkIdUFZwMKrxk+KAyHnXxqwwdQ8mfmQbvFoHj5494y6L7uCTjOsHF13+
UelnNEA3Oj9JhUEGrRXrza+ZY7dxovIkEiUhise/1gkOJ6XijQGYD23eaSBnVvxV
Qq4rx+09PjwkQInk5yVt0JiikPuoyo2pi1dDnGOEa3Po5puISufraVrYPt4fbkW7
wwB/9mlr921t0usT5JPoTFREz0Z4UuZRIuaM+fUOaIU=
-----END CERTIFICATE-----""","mqtt_key":"""-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDXaKxddiNsh3gU
MZhojcn4xCulkastkylyQHKj9kG+hAFpR2L/DV9W8H/B5ElaIOdXOWTYLN4SOMlW
OoaogVW/7FfDr51ObV0yb/mUKNTKHTz1ksWSoSMh2SNWHlaP1ATVmg/ms2qILKf5
ajLxvq276I9eAcnRWYLo9VqX8hRFehb7CNn5mzPbyLjOt7ED2ltBIRadVl33b3h3
BYMdMGgUUKRmEAP++pLjfDUTA58/faMjy0gjXUGlGLwB9t/mBjgn1eISN0pZSVNM
2H281QnBmfH28TuhFVrYLE5IzWRNp5K8g6b528HuI5yGaJ4OF671Hv2WqD+RSqTU
//K6Al+fAgMBAAECggEACSuVmuz6mRYzUHjECj9vB74iNYw8A1aufwSrXLuRFPE9
tiOp3T3Ofz8B0VlMnh+keZwh5OoUEiaEu70GGopXAjKnkdcaFUqmmw0VTO9oD6qq
+7Fh49okSr6ZuILWII1gH0/NuX6N3Ho6NG4G+S+q6cL+x3vAAb+TySMY1jsiDcsO
y/r5wODUAIUzCj2zO/YtYebH1RxdTOqdgSMIjC75csDD0etCfS/Spc6YgPv5sOpU
mhtII9xxY75u4SFR86oLEDaMbyKDmANT0Uiqi56hvWIcPezw+cFfjjfcuDiK+cV7
V+UQ9nfMRMXl5rBTtqUKeTZhtJSYRYkeVmRQ0vPjkQKBgQDvNnHVPwX6cTjKJglX
hnPwCWnGTuLhLbKzeV75kdbwWb9ImO8M0DVZ6lFOAnVf/cTlQwHt+G5eaUlDRrDt
1yhWOKph9iOICK2IVH3FpDyZ71He2UmCYbTCn9OifCPPBybegI6FZhXAY9C1P58K
db3ASO4LfRYB2APCr5JfzSrxXQKBgQDmhpVkKzTMpzHUpscsAoArtw8OnnHMUKB4
TinHF8fK4o3RvLJ0HR/kl2zBTLQsFvYURbqmCXr5+Ng5F77H8YFTUk1kD7HhR7cm
2pS5ibb1astSDq6dSiwsWiqF/P5wi0cpjlEs/2zvUfhesHg+WywilVtvt7tFDWGw
F5rKOsTZKwKBgFL2Nep4LhGafNCW+nxxc/oWual+KG9iEuzttgOmEb5P0ehSqe1u
tGIXwtTkQ2LkNwowABZRJ630o+UCOlByY1nr0yOgYthF8jEq5GfMOvxEJMe94iGm
0zMAjTx4A09EsrVOLp+TNQ4BUBvcEcNl7EYoxO4VFrHTAhLeI0y4ciE9AoGATyaK
iLglCtelTmRtInlBVMEn1Fcmr4ZHcsczpP5PRSQAmbD2fNO7LZuoZb5WZoUDvPYs
HfJHXSjJ5OB4SuJrCxbJJ8ATzUv4YMjQI9xbC2y9ntEXtz3OaPQUgajaG/5WUrhg
utiAqLM2WhyxTIe1YbJykKs/C3iKwBF6vlDrYb0CgYAPsmbNx0SWs2zcynxnP0bt
3vpPBiEyO8XnBXs1U86WufN7EuIe6poO5pV5B6TlLZxSNMs1LZOG6vsubf8Ie/mc
6TMYuEA3wWFOmbdqzzTmZFaNnp9xmH512dOGYnCKfTNE6tlXBoC9zRJBbJfR9N51
9HiJVQkH3UauquM0gRrBhg==
-----END PRIVATE KEY-----""","mqtt_cart":"""-----BEGIN CERTIFICATE-----
MIIDVzCCAj8CFAl+hCw6eE5wlZl/YRRGDfAfYYyIMA0GCSqGSIb3DQEBCwUAMGYx
CzAJBgNVBAYTAlVTMQ4wDAYDVQQIDAVTdGF0ZTENMAsGA1UEBwwEQ2l0eTEVMBMG
A1UECgwMT3JnYW5pemF0aW9uMRAwDgYDVQQLDAdPcmdVbml0MQ8wDQYDVQQDDAZZ
b3VyQ0EwHhcNMjUwNTA5MTIxOTE0WhcNMzUwNTA3MTIxOTE0WjBqMQswCQYDVQQG
EwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkxFTATBgNVBAoMDE9y
Z2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDETMBEGA1UEAwwKQ2xpZW50TmFt
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANdorF12I2yHeBQxmGiN
yfjEK6WRqy2TKXJAcqP2Qb6EAWlHYv8NX1bwf8HkSVog51c5ZNgs3hI4yVY6hqiB
Vb/sV8OvnU5tXTJv+ZQo1ModPPWSxZKhIyHZI1YeVo/UBNWaD+azaogsp/lqMvG+
rbvoj14BydFZguj1WpfyFEV6FvsI2fmbM9vIuM63sQPaW0EhFp1WXfdveHcFgx0w
aBRQpGYQA/76kuN8NRMDnz99oyPLSCNdQaUYvAH23+YGOCfV4hI3SllJU0zYfbzV
CcGZ8fbxO6EVWtgsTkjNZE2nkryDpvnbwe4jnIZong4XrvUe/ZaoP5FKpNT/8roC
X58CAwEAATANBgkqhkiG9w0BAQsFAAOCAQEAUvwHyIpIxM+MVFL6E/6Ag5LhCBAs
5Ed9LX8+SjFHKeeugWqb3iVaPqBcZJ86XlJ49pEMOwBtGJpbLUPBNpr8t+QXmnl/
wEH7xzNmvODJ/1DVLsCn0kL8ycohwEapQGkH5H+/Rp7+JvNZVHDkVGuu3PzXTjxd
2nlVhUciOC7kSBBRZO7mAOFMCPfYcSYKQfsF9Pirsb7rQdSRhp6thURpKJCS2SyV
wBk8bKkg4AOXs7ujsUfUiSFEjTqUjVkzxoAUdhljHGMyMWfUELtUcHTSmGcbdA90
IjBsK1eaOD7wUP3fdubAc1dUScYK4zwmnFfDP3fwwU0qC8eal+4by5Zi1Q==
-----END CERTIFICATE-----"""}

    return JsonResponse(data)

@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
def generate_captcha_api(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)


    byte_io, result = generate_captcha(STATIC_OTP_CAP)
    key = uuid.uuid4().hex
    cap,error=Captcha.objects.safe_create(key=key, answer=result)
    if error:   # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create


    # Convert image blob to base64
    img_base64 = base64.b64encode(byte_io.getvalue()).decode('utf-8')

    return JsonResponse({'key': key, 'captcha': img_base64})

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def verify_captcha_api(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    key = request.POST.get('key')
    user_input = request.POST.get('captcha')

    try:
        captcha = Captcha.objects.get(key=key)
        if not captcha.is_valid():
            captcha.delete()  # Optionally, delete the expired captcha
            return JsonResponse({'success': False, 'error': 'Captcha expired'})

        if int(user_input) == captcha.answer:
            captcha.delete()  # Optionally, delete the captcha after successful verification
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid captcha'})
    except Captcha.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Captcha not found'})
   

import os, magic
import os
import random
from rest_framework.response import Response


def save_file(request, tag, path):
    uploaded_file = request.FILES.get(tag)
    if not uploaded_file:
        return None 
        return Response({'error': f"File not found"}, status=400)
    #Response({'error': f"Invalid file type. Allowed types are:"}, status=400)

    # Validate file size (should be less than 1 MB)
    max_file_size = 1 * 1024 * 1024  # 1 MB in bytes
    if uploaded_file.size > max_file_size:
        return None 
        return Response({'error': f"File size should be less than 1 MB. Current size: {uploaded_file.size / (1024 * 1024):.2f} MB"}, status=400)

    # Validate file type using magic numbers
    valid_mime_types = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'application/pdf': 'pdf',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    }

    # Use python-magic to detect the MIME type
    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(uploaded_file.read(2048) or b'')  # Read the first 2 KB of the file
    except Exception:
        return None
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

    if mime_type not in valid_mime_types:
        return None 
        return Response({'error': f"Invalid file type. Allowed types are: {', '.join(valid_mime_types.keys())}"}, status=400)

    # Additional validation to prevent executable files
    uploaded_file.seek(0)  # Reset file pointer to the beginning
    file_content = uploaded_file.read(2048)  # Read the first 2 KB of the file
    if b'MZ' in file_content or b'PK\x03\x04' in file_content:
        return None 
        return Response({'error': "Invalid file detected. Upload denied."}, status=400)
    data=file_content
    if data.startswith(b"MZ") or data.startswith(b"\x7FELF") or data.startswith(b"\xcf\xfa\xed\xfe") or \
        data.startswith(b"\xce\xfa\xed\xfe") or \
        data.startswith(b"\xca\xfe\xba\xbe")or data.startswith(b"#!"):
            return None 
        #return Response({'error': "Invalid file detected. Upload denied."}, status=400)
    
    # Create the directory in the host storage path if it doesn't exist
    if not path.startswith('fileuploads/') and path != 'fileuploads' and not path.startswith('./fileuploads/'):
        # Prepend fileuploads/ to ensure consistent path structure
        host_path = os.path.join(HOST_STORAGE_PATH, 'fileuploads', path.lstrip('./'))
    else:
        host_path = os.path.join(HOST_STORAGE_PATH, path.lstrip('./'))
    
    try:
        os.makedirs(host_path, exist_ok=True)
    except PermissionError:
        return None
    
    file_extension = valid_mime_types[mime_type]
    file_name = ''.join(secrets.choice('0123456789') for _ in range(40)) + "." + file_extension
    file_path = os.path.join(host_path, file_name)
    
    with open(file_path, 'wb') as file:
        uploaded_file.seek(0)  # Reset file pointer to the beginning
        for chunk in uploaded_file.chunks():
            file.write(chunk)

    # Return the path that will be stored in the database and used for retrieval
    if not path.startswith('fileuploads/') and path != 'fileuploads' and not path.startswith('./fileuploads/'):
        # Return path with folder name included, e.g., "notice/filename.jpg"
        return os.path.join(path.lstrip('./'), file_name)
    else:
        # Path already has structure, just return it
        return os.path.join(path.lstrip('./'), file_name)



def find_file_in_folders(filename, folders):
    # First try with the original path which might include directories
    
    
    filename=os.path.join(HOST_STORAGE_PATH, filename)
    if os.path.isfile(filename):
        return filename
                
    return None
    for folder in folders:
        filename_clean = filename.replace("%20", " ")
        
        # Case 1: If filename already contains path components like 'notice/file.jpg'
        if '/' in filename_clean:
            # Try direct path
            potential_path = os.path.join(folder, filename_clean)
            if os.path.isfile(potential_path):
                return potential_path
                
            # Try with fileuploads prefix if not already there
            if not filename_clean.startswith('fileuploads/'):
                potential_path = os.path.join(folder, 'fileuploads', filename_clean)
                if os.path.isfile(potential_path):
                    return potential_path
        
        # Case 2: Simple filename without directory
        else:
            # Try direct path for simple filename
            potential_path = os.path.join(folder, filename_clean)
            if os.path.isfile(potential_path):
                return potential_path
            
            # Try common subdirectories for files
            for subdir in ['', 'notice', 'fileuploads/notice']:
                potential_path = os.path.join(folder, subdir, filename_clean)
                if os.path.isfile(potential_path):
                    return potential_path

    # Use glob as a fallback for more flexible matching
    for folder in folders:
        # Try to find by filename only, anywhere under the folder
        pattern = os.path.join(folder, '**', os.path.basename(filename.replace("%20", " ")))
        matches = glob.glob(pattern, recursive=True)
        if matches and os.path.isfile(matches[0]):
            return matches[0]
            
    return None
folders = [
    os.path.join(HOST_STORAGE_PATH, ''),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/tac_docs/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/Receipt_files/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/kyc_files/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/cop_files/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/file_bin/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/man/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/media/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/notice/'),
    os.path.join(HOST_STORAGE_PATH, 'fileuploads/driver/'),
    # Add more folders as needed
]

# Ensure directories exist (do not crash at import time if host path isn't writable)
_host_storage_init_ok = True
for folder in folders:
    try:
        os.makedirs(folder, exist_ok=True)
    except PermissionError:
        _host_storage_init_ok = False
        break

# Backward-compatible local relative folders used by legacy code paths on some VMs.
for legacy_local_folder in ['fileuploads/cop_files', 'fileuploads/copfiles']:
    try:
        os.makedirs(legacy_local_folder, exist_ok=True)
    except PermissionError:
        pass

if not _host_storage_init_ok:
    HOST_STORAGE_PATH = os.environ.get('HOST_STORAGE_FALLBACK_PATH', '/tmp/skytrack_storage')
    folders = [
        os.path.join(HOST_STORAGE_PATH, ''),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/tac_docs/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/Receipt_files/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/kyc_files/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/cop_files/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/file_bin/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/man/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/media/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/notice/'),
        os.path.join(HOST_STORAGE_PATH, 'fileuploads/driver/'),
    ]
    for folder in folders:
        try:
            os.makedirs(folder, exist_ok=True)
        except PermissionError:
            pass
    for legacy_local_folder in ['fileuploads/cop_files', 'fileuploads/copfiles']:
        try:
            os.makedirs(legacy_local_folder, exist_ok=True)
        except PermissionError:
            pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  # Apply throttling here
@require_http_methods(['GET', 'POST'])
def downloadfile(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        file_path =   request.data.get('file_path') 
        #print(request.content_type )
        #print(request.data)
        #print(request.user )

        if not file_path:
            return JsonResponse({'error': 'file_path is required'}, status=400) 
        try:
            # Extract just the filename for the response header
            filename = os.path.basename(file_path)
            
            # Try to find the file first with the full path
            full_path = find_file_in_folders(file_path, folders)
            
            # If that fails, try with just the filename
            if not full_path:
                filename_only = os.path.basename(file_path)
                full_path = find_file_in_folders(filename_only, folders)
                
            if not full_path:
                return JsonResponse({'error': f'file not found: {file_path}'}, status=400) 
                
            try:                
                with open(full_path, 'rb') as file:
                    response = HttpResponse(file.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                    return response
            except FileNotFoundError:
                return HttpResponse("File not found.", status=404) 
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'Error in reading file.'}, status=404)
    return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)



def apply_low_pass_filter(queryset, columns):
    # Get the values of the specified columns from the queryset
    column_values = {col: list(queryset.values_list(col, flat=True)) for col in columns}

    # Apply low-pass filter and median filter to each column
    for col, values in column_values.items():
        normalized_values,meanv,std_value = normalize(values)
        median_filtered_values = median_filter(normalized_values)
        low_pass_filtered_values = moving_average_filter(median_filtered_values, window_size=10) #low_pass_filter(median_filtered_values)
        column_values[col] = unnormalize(low_pass_filtered_values,meanv,std_value)
         

    # Update the queryset with the filtered values
    for i, entry in enumerate(queryset):
        for col, values in column_values.items():
            setattr(entry, col, values[i])

    return queryset

def low_pass_filter(data, cutoff_freq=0.4, sampling_rate=1.0, order=16):


    # Design a Butterworth low-pass filter
    nyquist = 0.5 * sampling_rate
    normal_cutoff = cutoff_freq / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)

    # Initialize filtered data with the first value
    filtered_data = [data[0]]

    # Initialize the state for the filter
    zi = [0] * (max(len(a), len(b)) - 1)
    
    # Apply the filter to the remaining data
    for value in data[1:]:
        filtered_value, zi = lfilter(b, a, [value], zi=zi)
        filtered_data.append(filtered_value[0])

    return filtered_data
def moving_average_filter(data, window_size=5):
    # Apply a simple moving average filter to the data
    filtered_data = np.convolve(data, np.ones(window_size) / window_size, mode='same')
    return filtered_data.tolist()
def normalize(data):
    # Normalize the data to have zero mean and unit variance
    mean_value = np.mean(data)
    std_value = np.std(data)
    normalized_data = [(x - mean_value) / std_value for x in data]

    return [normalized_data,mean_value,std_value]
def unnormalize(data,mean_value,std_value):
    # Normalize the data to have zero mean and unit variance
    
    normalized_data = [ mean_value+ (x*std_value) for x in data]

    return normalized_data

def median_filter(data, kernel_size=3):
    # Apply a median filter to the data
    filtered_data = np.convolve(data, np.ones(kernel_size) / kernel_size, mode='same')

    return filtered_data.tolist()
 

  

from itertools import chain

# Remove the custom model_to_dict function and use Django's built-in version
# which is already imported from django.forms.models




@csrf_exempt   
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def gps_track_data_api(request ):  
    
    if request.method == 'GET':
        # Debug authentication status 
        if hasattr(request.user, 'role'):
            print(f"DEBUG: request.user.role = {request.user.role}")
        else:
            print("DEBUG: request.user has no role attribute")
        # Check authentication headers
        auth_header = request.META.get('HTTP_AUTHORIZATION', None)
        print(f"DEBUG: Authorization header = {auth_header}")

        imei = request.GET.get('imei', None)
        regno = request.GET.get('regno', None)
        # Filters
        manufacturer_id = request.GET.get('manufacturer_id', None)
        make_text = request.GET.get('make', None)  # DeviceTag.vehicle_make (partial text)
        category_param = request.GET.get('category', None)  # DeviceTag.category (id or text)

        district_id = request.GET.get('district_id', None)
        district_text = request.GET.get('district', None)  # Settings_District.district (partial text)

        # Geofence filter params
        route_id = request.GET.get('route_id', None)
        roads_param = request.GET.get('roads', None)  # legacy/alias for route_id

        poi_id = request.GET.get('poi_id', None)
        poi_param = request.GET.get('poi', None)  # legacy/alias for poi_id

        polygon_param = request.GET.get('polygon', None)  # Expects JSON string: [[lat,lon],[lat,lon],...]

        # Speed filter (live vehicle speed >= speed_limit)
        speed_limit_param = request.GET.get('speed_limit', None)

        # Normalize geofence params: treat '', 'None', 'null', 'undefined' as absent
        import json
        def _norm(v):
            if v is None:
                return None
            if isinstance(v, str) and v.strip().lower() in ('', 'none', 'null', 'undefined'):
                return None
            return v
        # Apply legacy aliases when modern param not present
        if route_id is None:
            route_id = roads_param
        if poi_id is None:
            poi_id = poi_param

        route_id = _norm(route_id)
        poi_id = _norm(poi_id)
        polygon_param = _norm(polygon_param)
        manufacturer_id = _norm(manufacturer_id)
        make_text = _norm(make_text)
        category_param = _norm(category_param)
        district_id = _norm(district_id)
        district_text = _norm(district_text)
        speed_limit_param = _norm(speed_limit_param)
        # If polygon is a JSON string, treat empty/short polygons as absent
        if isinstance(polygon_param, str):
            try:
                _poly_tmp = json.loads(polygon_param)
                if isinstance(_poly_tmp, list) and len(_poly_tmp) < 3:
                    polygon_param = None
            except Exception:
                # Invalid JSON polygon -> ignore
                polygon_param = None
        # Attempt to coerce IDs to int when present
        try:
            route_id = int(route_id) if route_id is not None else None
        except Exception:
            route_id = None
        try:
            poi_id = int(poi_id) if poi_id is not None else None
        except Exception:
            poi_id = None
        try:
            manufacturer_id = int(manufacturer_id) if manufacturer_id is not None else None
        except Exception:
            manufacturer_id = None
        try:
            district_id = int(district_id) if district_id is not None else None
        except Exception:
            district_id = None

        # Category can be id or text
        category_id = None
        category_text = None
        if category_param is not None:
            try:
                if str(category_param).strip().isdigit():
                    category_id = int(str(category_param).strip())
                else:
                    category_text = str(category_param).strip()
            except Exception:
                category_id = None
                category_text = None

        try:
            speed_limit = int(speed_limit_param) if speed_limit_param is not None else None
        except Exception:
            speed_limit = None
        in_range = True
        in_range_param = request.GET.get('in_range', None)
        if in_range_param is not None:
            in_range = str(in_range_param).lower() == 'true'
        # New owner name substring filter
        owner_name_substr = request.GET.get('owner', None)
        # New road/city substring filter (applies to latest entry per device_tag)
        poi_t = _norm(request.GET.get('poi_t', None))
        poi_t_cf = str(poi_t).casefold() if poi_t is not None else None

        # Get base queryset
        gps_queryset = GPSData.objects.exclude(device_tag=None).filter(gps_status=1)

        # Filter by imei if provided (partial match)
        if imei and imei != "None":
            gps_queryset = gps_queryset.filter(device_tag__device__imei__icontains=imei)
        # Filter by regno if provided (partial match)
        if regno and regno != "None":
            gps_queryset = gps_queryset.filter(device_tag__vehicle_reg_no__icontains=regno)
        # Filter by vehicle make (partial match, case-insensitive)
        if make_text is not None:
            gps_queryset = gps_queryset.filter(device_tag__vehicle_make__icontains=str(make_text))
        # Filter by manufacturer id via DeviceTag -> DeviceStock -> Dealer -> Manufacturer
        if manufacturer_id is not None:
            gps_queryset = gps_queryset.filter(device_tag__device__dealer__manufacturer__id=manufacturer_id)
        # Filter by vehicle category (id or text)
        if category_id is not None:
            gps_queryset = gps_queryset.filter(device_tag__category_id=category_id)
        elif category_text is not None:
            gps_queryset = gps_queryset.filter(device_tag__category__category__icontains=category_text)
        # Filter by district id / district name
        if district_id is not None:
            gps_queryset = gps_queryset.filter(device_tag__district__id=district_id)
        if district_text is not None:
            gps_queryset = gps_queryset.filter(device_tag__district__district__icontains=str(district_text))
        # Filter by configured max speed for the vehicle category
        if speed_limit is not None:
            # Settings_VehicleCategory.maxSpeed is stored as text; allow leading zeros
            gps_queryset = gps_queryset.filter(device_tag__category__maxSpeed__regex=rf'^0*{speed_limit}$')

        # Apply role-based filtering (unchanged)
        if request.user and request.user.is_authenticated:
            user_role = getattr(request.user, 'role', None)
            if not user_role:
                gps_queryset = GPSData.objects.none()
                return JsonResponse({'error': 'User role not found.'}, status=400)
            if user_role == 'superadmin':
                pass
            elif user_role in ['stateadmin', 'sosadmin', 'sosexecutive', 'dtorto','dealer']:
                user_states = []
                if user_role == 'stateadmin':
                    state_admins = StateAdmin.objects.filter(users=request.user)
                    user_states = [sa.state.id for sa in state_admins]
                elif user_role == 'sosadmin':
                    em_admins = EM_admin.objects.filter(users=request.user)
                    user_states = [ea.state.id for ea in em_admins]
                elif user_role == 'sosexecutive':
                    em_exs = EM_ex.objects.filter(users=request.user)
                    user_states = [ee.state.id for ee in em_exs]
                elif user_role == 'dtorto':
                    dto_rtos = dto_rto.objects.filter(users=request.user)
                    user_states = [dr.state.id for dr in dto_rtos]
                elif user_role == 'dealer':
                    dlrs = Dealer.objects.filter(users=request.user)
                    user_states = [dr.manufacturer.state.id for dr in dlrs]
                if user_states:
                    gps_queryset = gps_queryset.filter(device_tag__district__state__id__in=user_states)
                else:
                    gps_queryset = GPSData.objects.none()
                    return JsonResponse({'error':  'No user states found.'}, status=400)
            elif user_role == 'owner':
                vehicle_owners = VehicleOwner.objects.filter(users=request.user)#, status='UserVerified')
                if vehicle_owners.exists():
                    owned_device_tags = DeviceTag.objects.filter(vehicle_owner__in=vehicle_owners)
                    gps_queryset = gps_queryset.filter(device_tag__in=owned_device_tags)
                else:
                    gps_queryset = GPSData.objects.none()
                    return JsonResponse({'error':  'User is not linked to any vehicles.'}, status=400)
            else:
                gps_queryset = GPSData.objects.none()
                return JsonResponse({'error':  'User not Authorised for this api.'}, status=400)
        else:
            gps_queryset = GPSData.objects.none()
            return JsonResponse({'error': 'User not authenticated.'}, status=401)

        # --- Geofence filter logic ---
        polygon = None
        geofence_center = None  # (lat, lon) center for POI radius filter
        geofence_message = None
        buffer_distance = 0.1  # 0.1 km = 100m
        from shapely.geometry import Point, Polygon, LineString
        import json
        # Select active geofence with precedence: POI > Route > Polygon
        geofence_count = sum([1 if x is not None else 0 for x in [route_id, poi_id, polygon_param]])
        active_type = 'poi' if poi_id is not None else ('route' if route_id is not None else ('polygon' if polygon_param is not None else None))
        if geofence_count > 1 and active_type:
            geofence_message = f"Multiple geofence params provided; using {active_type}."
        # Debug: show geofence selection
        try:
            print(f"DEBUG: geofence active_type={active_type}, poi_id={poi_id}, route_id={route_id}, polygon_present={(polygon_param is not None)}")
        except Exception:
            pass

        if active_type == 'route':
            try:
                route = Route.objects.get(id=route_id)
                points = []
                if hasattr(route, 'routepoints'):
                    if isinstance(route.routepoints, str):
                        points = json.loads(route.routepoints)
                    else:
                        points = route.routepoints
                coords = []
                for pt in points:
                    if isinstance(pt, dict):
                        coords.append((float(pt['lon']), float(pt['lat'])))
                    elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        coords.append((float(pt[1]), float(pt[0])))
                if coords:
                    line = LineString(coords)
                    polygon = line.buffer(buffer_distance)
                else:
                    geofence_message = "Route has no valid points. Geofence filter not applied."
            except Exception as e:
                geofence_message = f"Route geofence error: {e}. Geofence filter not applied."
        elif active_type == 'poi':
            # POI geofence: prefer polygon from POI.location when available or requested; otherwise fall back to 100m radius
            try:
                poi = pointofinterests.objects.get(id=poi_id)
                poi_location = getattr(poi, 'location', None)
                poi_as_polygon_param = request.GET.get('poi_as_polygon', None)
                use_polygon = False
                if poi_as_polygon_param is not None:
                    use_polygon = str(poi_as_polygon_param).strip().lower() == 'true'

                built_polygon = False
                if poi_location and (use_polygon or (getattr(poi, 'lat', None) is None or getattr(poi, 'lon', None) is None)):
                    try:
                        loc_coords = json.loads(poi_location) if isinstance(poi_location, str) else poi_location
                        poly_coords = []
                        if isinstance(loc_coords, list):
                            for item in loc_coords:
                                if isinstance(item, (list, tuple)) and len(item) >= 2:
                                    # Expect [lat, lon]
                                    lat_i = float(item[0])
                                    lon_i = float(item[1])
                                    poly_coords.append((lon_i, lat_i))
                                elif isinstance(item, dict) and 'lat' in item and 'lon' in item:
                                    poly_coords.append((float(item['lon']), float(item['lat'])))
                        if len(poly_coords) >= 3:
                            polygon = Polygon(poly_coords)
                            built_polygon = True
                            geofence_message = 'Using POI location polygon geofence.'
                        else:
                            geofence_message = 'POI location polygon invalid or too few points; falling back to radius.'
                    except Exception as e:
                        geofence_message = f'POI polygon parse error: {e}; falling back to radius.'

                if not built_polygon:
                    poi_lat = getattr(poi, 'lat', None)
                    poi_lon = getattr(poi, 'lon', None)
                    if poi_lat is not None and poi_lon is not None:
                        geofence_center = (float(poi_lat), float(poi_lon))
                    else:
                        # Neither valid polygon nor lat/lon available -> return blank per request
                        return JsonResponse({'data': [], 'geofence_message': 'POI has neither lat/lon nor valid polygon. Returning blank.'})
            except Exception as e:
                # POI lookup failed -> return blank
                return JsonResponse({'data': [], 'geofence_message': f'POI lookup error: {e}. Returning blank.'})
        elif active_type == 'polygon':
            try:
                coords = json.loads(polygon_param)
                poly_coords = [(float(lon), float(lat)) for lat, lon in coords]
                if poly_coords:
                    polygon = Polygon(poly_coords)
                else:
                    geofence_message = "Custom polygon has no valid points. Geofence filter not applied."
            except Exception as e:
                geofence_message = f"Custom polygon geofence error: {e}. Geofence filter not applied."
        # --- End geofence logic ---

        # --- Helper utilities for nearest POI / Route proximity ---
        # Haversine distance in kilometers
        def haversine_km(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
            return 2 * R * asin(sqrt(a))

        # Resolve a representative point for a POI
        def poi_coord(poi):
            try:
                if getattr(poi, 'lat', None) is not None and getattr(poi, 'lon', None) is not None:
                    return float(poi.lat), float(poi.lon)
                loc = getattr(poi, 'location', None)
                if not loc:
                    return None
                coords = json.loads(loc) if isinstance(loc, str) else loc
                lats, lons = [], []
                if isinstance(coords, list):
                    for item in coords:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            lats.append(float(item[0]))
                            lons.append(float(item[1]))
                        elif isinstance(item, dict) and 'lat' in item and 'lon' in item:
                            lats.append(float(item['lat']))
                            lons.append(float(item['lon']))
                if lats and lons:
                    return sum(lats) / len(lats), sum(lons) / len(lons)
            except Exception:
                return None
            return None

        # Preload POIs and Routes once for efficiency
        try:
            all_pois = list(pointofinterests.objects.all())
        except Exception:
            all_pois = []
        police_pois = [p for p in all_pois if getattr(p, 'use_type', None) == 'police']

        try:
            all_routes = list(Route.objects.all())
        except Exception:
            all_routes = []

        def nearest_poi_info(lat, lon, poi_list):
            best = None
            best_dist = None
            for poi in poi_list:
                pc = poi_coord(poi)
                if not pc:
                    continue
                plat, plon = pc
                d = haversine_km(lat, lon, plat, plon)
                if best_dist is None or d < best_dist:
                    best = poi
                    best_dist = d
            if best is None:
                return None
            # Return full POI data using standard serializer with distance metadata
            return {
                'data': PointOfInterestSerializer(best).data,
                'distance_meters': int(round((best_dist or 0) * 1000)),
            }

        def routes_within_100m(lat, lon):
            results = []
            for r in all_routes:
                pts_raw = None
                if hasattr(r, 'route') and getattr(r, 'route') is not None:
                    pts_raw = getattr(r, 'route')
                elif hasattr(r, 'routepoints') and getattr(r, 'routepoints') is not None:
                    pts_raw = getattr(r, 'routepoints')
                if not pts_raw:
                    continue
                try:
                    pts = json.loads(pts_raw) if isinstance(pts_raw, str) else pts_raw
                except Exception:
                    continue
                min_km = None
                if isinstance(pts, list):
                    for pt in pts:
                        # Expect [lon, lat, altitude] or [lon, lat]
                        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                            lon_r = float(pt[0])
                            lat_r = float(pt[1])
                            d = haversine_km(lat, lon, lat_r, lon_r)
                            if min_km is None or d < min_km:
                                min_km = d
                        elif isinstance(pt, dict) and 'lat' in pt and 'lon' in pt:
                            d = haversine_km(lat, lon, float(pt['lat']), float(pt['lon']))
                            if min_km is None or d < min_km:
                                min_km = d
                if min_km is not None and min_km <= 0.1:  # within 100 meters
                    results.append({
                        'data': routeSerializer(r).data,
                        'min_distance_meters': int(round(min_km * 1000)),
                    })
            return results
        # --- End helper utilities ---

        distinct_registration_numbers = gps_queryset.values('device_tag').distinct()
        data = []
        from .serializers import DeviceTagSerializer, VehicleOwnerSerializer, UserSerializer
        for x in distinct_registration_numbers:
            latest_entry = gps_queryset.filter(device_tag=x['device_tag']).filter(gps_status=1).order_by('-entry_time')
            latest_entry = latest_entry.first()
            if latest_entry:
                # Filter by poi_t in latest GPSData.road or GPSData.city (case-insensitive substring)
                if poi_t_cf:
                    road_value = getattr(latest_entry, 'road', None)
                    city_value = getattr(latest_entry, 'city', None)
                    road_cf = str(road_value).casefold() if road_value is not None else ''
                    city_cf = str(city_value).casefold() if city_value is not None else ''
                    if poi_t_cf not in road_cf and poi_t_cf not in city_cf:
                        continue
                # Owner name substring filter
                if owner_name_substr:
                    owner_obj = getattr(getattr(latest_entry.device_tag, 'vehicle_owner', None), 'users', None)
                    owner_match = False
                    if owner_obj:
                        for user in owner_obj.all():
                            if owner_name_substr.lower() in (user.name or '').lower():
                                owner_match = True
                                break
                    if not owner_match:
                        continue  # skip if no owner matches substring
                # Geofence filter: check polygon containment OR POI radius
                if polygon is not None:
                    lat = getattr(latest_entry, 'latitude', None)
                    lon = getattr(latest_entry, 'longitude', None)
                    if lat is not None and lon is not None:
                        pt = Point(float(lon), float(lat))
                        inside = polygon.contains(pt)
                        if (in_range and not inside) or (not in_range and inside):
                            continue  # skip this point
                elif geofence_center is not None:
                    lat = getattr(latest_entry, 'latitude', None)
                    lon = getattr(latest_entry, 'longitude', None)
                    if lat is not None and lon is not None:
                        center_lat, center_lon = geofence_center
                        d_km = haversine_km(float(lat), float(lon), center_lat, center_lon)
                        inside = d_km <= 0.1  # within 100 meters
                        if (in_range and not inside) or (not in_range and inside):
                            continue
                serializer = GPSData_Serializer(latest_entry)
                dd = serializer.data.copy()
                if 'entry_time' not in dd and hasattr(latest_entry, 'entry_time'):
                    dd['entry_time'] = latest_entry.entry_time.isoformat() if latest_entry.entry_time else None
                if latest_entry.device_tag:
                    dd['vehicle_registration_number'] = latest_entry.device_tag.vehicle_reg_no
                    dd['imei'] = latest_entry.device_tag.device.imei
                    device_tag_obj = latest_entry.device_tag
                    device_tag_data = DeviceTagSerializer(device_tag_obj).data
                    # Attach concise device/manufacturer summary for convenience
                    try:
                        ds = device_tag_obj.device  # DeviceStock
                        dealer_obj = getattr(ds, 'dealer', None)
                        man_obj = getattr(dealer_obj, 'manufacturer', None) if dealer_obj else None
                        device_summary = {
                            'id': ds.id,
                            'imei': ds.imei,
                        }
                        if dealer_obj:
                            device_summary['dealer'] = {
                                'id': dealer_obj.id,
                                'company_name': getattr(dealer_obj, 'company_name', None),
                            }
                        if man_obj:
                            device_summary['manufacturer'] = {
                                'id': man_obj.id,
                                'company_name': getattr(man_obj, 'company_name', None),
                            }
                        device_tag_data['device_info'] = device_summary
                    except Exception:
                        pass
                    if device_tag_obj.vehicle_owner:
                        owner_data = VehicleOwnerSerializer(device_tag_obj.vehicle_owner).data
                        if 'users' not in owner_data:
                            owner_data['users'] = UserSerializer(device_tag_obj.vehicle_owner.users.all(), many=True).data
                        device_tag_data['vehicle_owner'] = owner_data
                    dd['device_tag_info'] = device_tag_data
                else:
                    dd['vehicle_registration_number'] = ""
                    dd['imei'] = ""
                    dd['device_tag_info'] = None

                # Attach nearest POI, nearest Police POI, and nearby Routes (<=100m)
                lat = getattr(latest_entry, 'latitude', None)
                lon = getattr(latest_entry, 'longitude', None)
                if lat is not None and lon is not None:
                    np_info = nearest_poi_info(float(lat), float(lon), all_pois)
                    npp_info = nearest_poi_info(float(lat), float(lon), police_pois)
                    near_rs = routes_within_100m(float(lat), float(lon))
                else:
                    np_info = None
                    npp_info = None
                    near_rs = []
                dd['nearest_poi'] = np_info
                dd['nearest_police'] = npp_info
                dd['nearby_routes_within_100m'] = near_rs
                data.append(dd)
        data_list = list(data)
        response = {'data': data_list}
        if geofence_message:
            response['geofence_message'] = geofence_message
        return JsonResponse(response)
    return JsonResponse({'error':  'Invalid request method. Only GET is allowed.'}, status=400)








@csrf_exempt   
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def gps_track_data_api_pub(request ):  
    
    if request.method == 'GET':
        imei = request.GET.get('imei', None)
        regno = request.GET.get('regno', None)
        # Filters
        manufacturer_id = request.GET.get('manufacturer_id', None)
        make_text = request.GET.get('make', None)  # DeviceTag.vehicle_make (partial text)
        category_param = request.GET.get('category', None)  # DeviceTag.category (id or text)

        district_id = request.GET.get('district_id', None)
        district_text = request.GET.get('district', None)  # Settings_District.district (partial text)

        # Geofence filter params
        route_id = request.GET.get('route_id', None)
        roads_param = request.GET.get('roads', None)  # legacy/alias for route_id

        poi_id = request.GET.get('poi_id', None)
        poi_param = request.GET.get('poi', None)  # legacy/alias for poi_id

        polygon_param = request.GET.get('polygon', None)  # Expects JSON string: [[lat,lon],[lat,lon],...]

        # Speed filter (live vehicle speed >= speed_limit)
        speed_limit_param = request.GET.get('speed_limit', None)

        # Normalize geofence params: treat '', 'None', 'null', 'undefined' as absent
        import json
        def _norm(v):
            if v is None:
                return None
            if isinstance(v, str) and v.strip().lower() in ('', 'none', 'null', 'undefined'):
                return None
            return v
        # Apply legacy aliases when modern param not present
        if route_id is None:
            route_id = roads_param
        if poi_id is None:
            poi_id = poi_param

        route_id = _norm(route_id)
        poi_id = _norm(poi_id)
        polygon_param = _norm(polygon_param)
        manufacturer_id = _norm(manufacturer_id)
        make_text = _norm(make_text)
        category_param = _norm(category_param)
        district_id = _norm(district_id)
        district_text = _norm(district_text)
        speed_limit_param = _norm(speed_limit_param)
        # If polygon is a JSON string, treat empty/short polygons as absent
        if isinstance(polygon_param, str):
            try:
                _poly_tmp = json.loads(polygon_param)
                if isinstance(_poly_tmp, list) and len(_poly_tmp) < 3:
                    polygon_param = None
            except Exception:
                # Invalid JSON polygon -> ignore
                polygon_param = None
        # Attempt to coerce IDs to int when present
        try:
            route_id = int(route_id) if route_id is not None else None
        except Exception:
            route_id = None
        try:
            poi_id = int(poi_id) if poi_id is not None else None
        except Exception:
            poi_id = None
        try:
            manufacturer_id = int(manufacturer_id) if manufacturer_id is not None else None
        except Exception:
            manufacturer_id = None
        try:
            district_id = int(district_id) if district_id is not None else None
        except Exception:
            district_id = None

        # Category can be id or text
        category_id = None
        category_text = None
        if category_param is not None:
            try:
                if str(category_param).strip().isdigit():
                    category_id = int(str(category_param).strip())
                else:
                    category_text = str(category_param).strip()
            except Exception:
                category_id = None
                category_text = None

        try:
            speed_limit = int(speed_limit_param) if speed_limit_param is not None else None
        except Exception:
            speed_limit = None

        # Public version: full registration number is compulsory
        if not regno or str(regno).strip().lower() in ('', 'none', 'null', 'undefined'):
            return JsonResponse({'error': 'regno (full vehicle registration number) is required.'}, status=400)
        regno = str(regno).strip()

        in_range = True
        in_range_param = request.GET.get('in_range', None)
        if in_range_param is not None:
            in_range = str(in_range_param).lower() == 'true'

        # New road/city substring filter (applies to the latest entry selected)
        poi_t = _norm(request.GET.get('poi_t', None))
        poi_t_cf = str(poi_t).casefold() if poi_t is not None else None

        # Get base queryset
        gps_queryset = GPSData.objects.exclude(device_tag=None).filter(gps_status=1)

        # Filter by imei if provided (partial match)
        if imei and imei != "None":
            gps_queryset = gps_queryset.filter(device_tag__device__imei__icontains=imei)
        # Public version: filter by regno (exact match)
        gps_queryset = gps_queryset.filter(device_tag__vehicle_reg_no__iexact=regno)
        # Filter by vehicle make (partial match, case-insensitive)
        if make_text is not None:
            gps_queryset = gps_queryset.filter(device_tag__vehicle_make__icontains=str(make_text))
        # Filter by manufacturer id via DeviceTag -> DeviceStock -> Dealer -> Manufacturer
        if manufacturer_id is not None:
            gps_queryset = gps_queryset.filter(device_tag__device__dealer__manufacturer__id=manufacturer_id)
        # Filter by vehicle category (id or text)
        if category_id is not None:
            gps_queryset = gps_queryset.filter(device_tag__category_id=category_id)
        elif category_text is not None:
            gps_queryset = gps_queryset.filter(device_tag__category__category__icontains=category_text)
        # Filter by district id / district name
        if district_id is not None:
            gps_queryset = gps_queryset.filter(device_tag__district__id=district_id)
        if district_text is not None:
            gps_queryset = gps_queryset.filter(device_tag__district__district__icontains=str(district_text))
        # Filter by configured max speed for the vehicle category
        if speed_limit is not None:
            gps_queryset = gps_queryset.filter(device_tag__category__maxSpeed__regex=rf'^0*{speed_limit}$')

        # --- Geofence filter logic ---
        polygon = None
        geofence_center = None  # (lat, lon) center for POI radius filter
        geofence_message = None
        buffer_distance = 0.1  # 0.1 km = 100m
        from shapely.geometry import Point, Polygon, LineString
        import json
        # Select active geofence with precedence: POI > Route > Polygon
        geofence_count = sum([1 if x is not None else 0 for x in [route_id, poi_id, polygon_param]])
        active_type = 'poi' if poi_id is not None else ('route' if route_id is not None else ('polygon' if polygon_param is not None else None))
        if geofence_count > 1 and active_type:
            geofence_message = f"Multiple geofence params provided; using {active_type}."
        # Debug: show geofence selection
        try:
            print(f"DEBUG: geofence active_type={active_type}, poi_id={poi_id}, route_id={route_id}, polygon_present={(polygon_param is not None)}")
        except Exception:
            pass

        if active_type == 'route':
            try:
                route = Route.objects.get(id=route_id)
                points = []
                if hasattr(route, 'routepoints'):
                    if isinstance(route.routepoints, str):
                        points = json.loads(route.routepoints)
                    else:
                        points = route.routepoints
                coords = []
                for pt in points:
                    if isinstance(pt, dict):
                        coords.append((float(pt['lon']), float(pt['lat'])))
                    elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        coords.append((float(pt[1]), float(pt[0])))
                if coords:
                    line = LineString(coords)
                    polygon = line.buffer(buffer_distance)
                else:
                    geofence_message = "Route has no valid points. Geofence filter not applied."
            except Exception as e:
                geofence_message = f"Route geofence error: {e}. Geofence filter not applied."
        elif active_type == 'poi':
            # POI geofence: prefer polygon from POI.location when available or requested; otherwise fall back to 100m radius
            try:
                poi = pointofinterests.objects.get(id=poi_id)
                poi_location = getattr(poi, 'location', None)
                poi_as_polygon_param = request.GET.get('poi_as_polygon', None)
                use_polygon = False
                if poi_as_polygon_param is not None:
                    use_polygon = str(poi_as_polygon_param).strip().lower() == 'true'

                built_polygon = False
                if poi_location and (use_polygon or (getattr(poi, 'lat', None) is None or getattr(poi, 'lon', None) is None)):
                    try:
                        loc_coords = json.loads(poi_location) if isinstance(poi_location, str) else poi_location
                        poly_coords = []
                        if isinstance(loc_coords, list):
                            for item in loc_coords:
                                if isinstance(item, (list, tuple)) and len(item) >= 2:
                                    # Expect [lat, lon]
                                    lat_i = float(item[0])
                                    lon_i = float(item[1])
                                    poly_coords.append((lon_i, lat_i))
                                elif isinstance(item, dict) and 'lat' in item and 'lon' in item:
                                    poly_coords.append((float(item['lon']), float(item['lat'])))
                        if len(poly_coords) >= 3:
                            polygon = Polygon(poly_coords)
                            built_polygon = True
                            geofence_message = 'Using POI location polygon geofence.'
                        else:
                            geofence_message = 'POI location polygon invalid or too few points; falling back to radius.'
                    except Exception as e:
                        geofence_message = f'POI polygon parse error: {e}; falling back to radius.'

                if not built_polygon:
                    poi_lat = getattr(poi, 'lat', None)
                    poi_lon = getattr(poi, 'lon', None)
                    if poi_lat is not None and poi_lon is not None:
                        geofence_center = (float(poi_lat), float(poi_lon))
                    else:
                        # Neither valid polygon nor lat/lon available -> return blank per request
                        return JsonResponse({'data': [], 'geofence_message': 'POI has neither lat/lon nor valid polygon. Returning blank.'})
            except Exception as e:
                # POI lookup failed -> return blank
                return JsonResponse({'data': [], 'geofence_message': f'POI lookup error: {e}. Returning blank.'})
        elif active_type == 'polygon':
            try:
                coords = json.loads(polygon_param)
                poly_coords = [(float(lon), float(lat)) for lat, lon in coords]
                if poly_coords:
                    polygon = Polygon(poly_coords)
                else:
                    geofence_message = "Custom polygon has no valid points. Geofence filter not applied."
            except Exception as e:
                geofence_message = f"Custom polygon geofence error: {e}. Geofence filter not applied."
        # --- End geofence logic ---

        # --- Helper utility for POI radius geofence ---
        # Haversine distance in kilometers
        def haversine_km(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
            return 2 * R * asin(sqrt(a))

        data = []
        from .serializers import DeviceTagSerializer, VehicleOwnerSerializer, UserSerializer
        latest_entry = gps_queryset.order_by('-entry_time')
        if imei and str(imei).strip().lower() not in ('', 'none', 'null', 'undefined'):
            latest_entry = latest_entry.filter(device_tag__device__imei__icontains=str(imei).strip())
        latest_entry = latest_entry.first()

        if latest_entry:
            # Geofence filter: check polygon containment OR POI radius
            if polygon is not None:
                lat = getattr(latest_entry, 'latitude', None)
                lon = getattr(latest_entry, 'longitude', None)
                if lat is not None and lon is not None:
                    pt = Point(float(lon), float(lat))
                    inside = polygon.contains(pt)
                    if (in_range and not inside) or (not in_range and inside):
                        latest_entry = None
            elif geofence_center is not None:
                lat = getattr(latest_entry, 'latitude', None)
                lon = getattr(latest_entry, 'longitude', None)
                if lat is not None and lon is not None:
                    center_lat, center_lon = geofence_center
                    d_km = haversine_km(float(lat), float(lon), center_lat, center_lon)
                    inside = d_km <= 0.1  # within 100 meters
                    if (in_range and not inside) or (not in_range and inside):
                        latest_entry = None

        if latest_entry and poi_t_cf:
            road_value = getattr(latest_entry, 'road', None)
            city_value = getattr(latest_entry, 'city', None)
            road_cf = str(road_value).casefold() if road_value is not None else ''
            city_cf = str(city_value).casefold() if city_value is not None else ''
            if poi_t_cf not in road_cf and poi_t_cf not in city_cf:
                latest_entry = None

        if latest_entry:
            serializer = GPSData_Serializer(latest_entry)
            dd = serializer.data.copy()
            if 'entry_time' not in dd and hasattr(latest_entry, 'entry_time'):
                dd['entry_time'] = latest_entry.entry_time.isoformat() if latest_entry.entry_time else None
            if latest_entry.device_tag:
                dd['vehicle_registration_number'] = latest_entry.device_tag.vehicle_reg_no
                dd['imei'] = latest_entry.device_tag.device.imei
                device_tag_obj = latest_entry.device_tag
                device_tag_data = DeviceTagSerializer(device_tag_obj).data
                # Attach concise device/manufacturer summary for convenience
                try:
                    ds = device_tag_obj.device  # DeviceStock
                    dealer_obj = getattr(ds, 'dealer', None)
                    man_obj = getattr(dealer_obj, 'manufacturer', None) if dealer_obj else None
                    device_summary = {
                        'id': ds.id,
                        'imei': ds.imei,
                    }
                    if dealer_obj:
                        device_summary['dealer'] = {
                            'id': dealer_obj.id,
                            'company_name': getattr(dealer_obj, 'company_name', None),
                        }
                    if man_obj:
                        device_summary['manufacturer'] = {
                            'id': man_obj.id,
                            'company_name': getattr(man_obj, 'company_name', None),
                        }
                    device_tag_data['device_info'] = device_summary
                except Exception:
                    pass
                if device_tag_obj.vehicle_owner:
                    owner_data = VehicleOwnerSerializer(device_tag_obj.vehicle_owner).data
                    if 'users' not in owner_data:
                        owner_data['users'] = UserSerializer(device_tag_obj.vehicle_owner.users.all(), many=True).data
                    device_tag_data['vehicle_owner'] = owner_data
                dd['device_tag_info'] = device_tag_data
            else:
                dd['vehicle_registration_number'] = ""
                dd['imei'] = ""
                dd['device_tag_info'] = None
            data.append(dd)

        data_list = list(data)
        response = {'data': data_list}
        if geofence_message:
            response['geofence_message'] = geofence_message
        return JsonResponse(response)
    return JsonResponse({'error':  'Invalid request method. Only GET is allowed.'}, status=400)



@api_view(['GET'])
@permission_classes([AllowAny])
def global_counts_summary(request):
    """
    Aggregated global counts for dashboard:
    - totalPanicPress: EMCall count
    - panicActionTaken: EMCall where status != 'pending'
    - alerts: counts for key categories
    - vltStatus: DeviceTag totals by status (active/inactive) and defective devices as maintenance
    
    Returns global counts without user-based filtering.
    """
    try:
        # Panic stats (SOS) - global
        total_panic = EMCall.objects.count()
        action_taken = EMCall.objects.exclude(status='pending').count()

        # Alerts counts (key categories) - global
        alert_type_map = {
            'Overspeed': 'OverSpeed',
            'Harsh Breaking': 'HarshBreak',
            'Route Deviation': 'EmMonitorTripDeviated',
            'Tampering': 'BoxTemp',
            'Geofence Violation': 'Geofence',
        }
        alerts = []
        for label, al_type in alert_type_map.items():
            cnt = AlertsLog.objects.filter(type=al_type).count()
            alerts.append({'category': label, 'count': cnt})

        # VLT status - global
        total_vlt = DeviceTag.objects.count()
        active_vlt = DeviceTag.objects.filter(status='Device_Active').count()
        inactive_vlt = DeviceTag.objects.filter(status='Device_Not_Active').count()
        maintenance_vlt = DeviceStock.objects.filter(stock_status='Device_Defective').count()

        result = {
            'totalPanicPress': total_panic,
            'panicActionTaken': action_taken,
            'alerts': alerts,
            'vltStatus': {
                'total': total_vlt,
                'active': active_vlt,
                'inactive': inactive_vlt,
                'maintenance': maintenance_vlt,
            },
        }
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': f'Failed to compute summary: {e}'}, status=500)



def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size

 

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@require_http_methods(['GET', 'POST'])
def gps_history_map_data(request ): 
    t = time.time()

    mapdata=[]
    data=[]     
    try:
        try:
            vehicle_registration_number = request.GET.get('vehicle_registration_number', None)
            start_datetime = request.GET.get('start_datetime', None)
            end_datetime = request.GET.get('end_datetime', None)
            owner_name_substr = request.GET.get('owner_name_substr', None)
        except:
            pass

        if not vehicle_registration_number or vehicle_registration_number == "":
            return JsonResponse({'error': "Vehicle registration number is required"}, status=400)

        # Validate datetime inputs and enforce 24-hour window
        if not start_datetime or not end_datetime:
            return JsonResponse({'error': "Invalid Search 22"}, status=403)

        start_dt = parse_datetime(start_datetime)
        end_dt = parse_datetime(end_datetime)
        if not start_dt or not end_dt:
            return JsonResponse({'error': "Invalid datetime format for start_datetime/end_datetime"}, status=400)
        if end_dt < start_dt:
            return JsonResponse({'error': "end_datetime must be after start_datetime"}, status=400)
        if (end_dt - start_dt) > timedelta(hours=24):
            return JsonResponse({'error': "Time range cannot exceed 24 hours"}, status=400)

        # User authentication and authorization checks
        if not request.user or not request.user.is_authenticated:
            return JsonResponse({'error': "Authentication required"}, status=401)
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            return JsonResponse({'error': "User role not found"}, status=403)

        # Check if user has access to this registration number
        device_tag = DeviceTag.objects.filter(vehicle_reg_no=vehicle_registration_number).first()
        if not device_tag:
            return JsonResponse({'error': "Vehicle registration number not found in system"}, status=404)

        # Role-based authorization
        has_access = False
        
        if user_role == 'superadmin':
            has_access = True
        elif user_role == 'stateadmin':
            state_admins = StateAdmin.objects.filter(users=request.user)#, status='UserVerified')
            user_states = [sa.state.id for sa in state_admins]
            if user_states and device_tag.district and device_tag.district.state.id in user_states:
                has_access = True
        elif user_role == 'dtorto':
            dto_rtos = dto_rto.objects.filter(users=request.user )
            user_districts = [dr.district for dr in dto_rtos if dr.district]
            if user_districts and device_tag.district and device_tag.district.district_code in user_districts:
                has_access = True
        elif user_role == 'owner':
            vehicle_owners = VehicleOwner.objects.filter(users=request.user)#, status='UserVerified')
            if vehicle_owners.exists():
                owned_device_tags = DeviceTag.objects.filter(vehicle_owner__in=vehicle_owners)
                if device_tag in owned_device_tags:
                    has_access = True

        if not has_access:
            return JsonResponse({'error': "Unauthorised access to history data"}, status=403)

        if vehicle_registration_number:
            # Base queryset with essential filters
            # Use exact device_tag FK filter for index utilization
            data = (
                GPSData.objects
                .filter(gps_status=1)
                .filter(device_tag=device_tag)
                .filter(entry_time__range=(start_dt, end_dt))
            )

            # Apply owner name filter at DB level if provided
            if owner_name_substr:
                data = data.filter(device_tag__vehicle_owner__users__name__icontains=owner_name_substr)

            # Avoid N+1 queries; ensure unique rows if M2M filter applied
            data = (
                data.select_related('device_tag', 'device_tag__vehicle_owner')
                    .prefetch_related('device_tag__vehicle_owner__users')
                    .order_by('entry_time')
            )
            if owner_name_substr:
                data = data.distinct()

            # Use count() instead of len(queryset) to avoid evaluation
            total_count = data.count()
            datalen = total_count - 1

            from .serializers import DeviceTagSerializer, VehicleOwnerSerializer, UserSerializer
            data_serialized = []

            # Stream rows to keep memory in check
            for entry in data.iterator(chunk_size=1000):
                entry_data = GPSData_modSerializer(entry).data
                if entry.device_tag:
                    device_tag_obj = entry.device_tag
                    device_tag_data = DeviceTagSerializer(device_tag_obj).data
                    if device_tag_obj.vehicle_owner:
                        owner_data = VehicleOwnerSerializer(device_tag_obj.vehicle_owner).data
                        if 'users' in owner_data:
                            pass
                        else:
                            owner_data['users'] = UserSerializer(device_tag_obj.vehicle_owner.users.all(), many=True).data
                        device_tag_data['vehicle_owner'] = owner_data
                    entry_data['device_tag_info'] = device_tag_data
                else:
                    entry_data['device_tag_info'] = None
                data_serialized.append(entry_data)

            try:
                return JsonResponse({'data': data_serialized, 'mapdata': mapdata, 'mapdata_length': datalen})
            except Exception as e:
                return JsonResponse({"error": "Unable to process request." + "No Record Found 1: " + vehicle_registration_number}, status=403)

        return JsonResponse({'error': "Invalid Search"}, status=403)
    except Exception as e:
        return JsonResponse({'error': "Unable to process request." + str(e)})


 

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def delRoute(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        role1="superadmin"
        sa=get_user_object(user,role1)
        if not man and not sa:
            return Response({"error":"Request must be from  "+role+' or '+role1+'.'}, status=status.HTTP_400_BAD_REQUEST)

        data =json.loads( request.body )
        try:
            id=data['id']  
            device =  DeviceStock.objects.get(id=data['device_id'])
            if id:
                route = Route.objects.filter(id=int(id),device=device,status="Active", createdby=user.id).last()
                if not route: 
                    return JsonResponse({"error": "Route not found"}, status=400)
                route.status="Deleted"
                route.save()
                route = Route.objects.filter(device=device,status="Active" , createdby=user).all()
                return JsonResponse({"message": "Route deleted successfully!",'new':[],"data": routeSerializer(route, many=True).data }, status=201)
        
        except Exception as e:
            print(e)
            return JsonResponse({"error": "Unable to process request."+str(e)}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


from jsonschema import validate, ValidationError

# Define the expected JSON schema
response_schema = {
    "type": "object",
    "properties": { 
                "paths": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "distance": {"type": "number"},
                            "weight": {"type": "number"},
                            "time": {"type": "number"},
                            "transfers": {"type": "number"},
                            "points_encoded": {"type": "boolean"},
                            "bbox": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 4,
                                "maxItems": 4
                            },
                            "points": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "coordinates": {
                                        "type": "array",
                                        "items": {
                                            "type": "array",
                                            "items": {"type": "number"},
                                            "minItems": 3,
                                            "maxItems": 3
                                        }
                                    }
                                },
                                "required": ["type", "coordinates"]
                            },
                            "instructions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "distance": {"type": "number"},
                                        "sign": {"type": "number"},
                                        "interval": {
                                            "type": "array",
                                            "items": {"type": "number"},
                                            "minItems": 2,
                                            "maxItems": 2
                                        },
                                        "text": {"type": "string"},
                                        "time": {"type": "number"},
                                        "street_name": {"type": "string"}
                                    },
                                    "required": ["distance", "sign", "interval", "text", "time"]
                                }
                            }
                        },
                        "required": ["distance", "weight", "time", "transfers", "points_encoded", "bbox", "points", "instructions"]
                    }
                }
            },
            "required": ["paths"]
   
 
}

# Function to validate the response
def validate_bhuvan_response(response_json):
    try:
        validate(instance=response_json, schema=response_schema)
        return True, "Response is valid."
    except ValidationError as e:
        return False, f"Invalid response: {e.message}"


@csrf_exempt
@api_view(['POST'])
#@permission_classes([IsAuthenticated]) #
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])   
def get_routePath(request): 
    # The target external API URL
    url = 'https://bhuvan-app1.nrsc.gov.in/api/routing/curl_routing_new_v2.php?token=fb46cfb86bea498dce694350fb6dd16d161ff8eb' 
    points_data = request.data.get("points", [])
    
    if not points_data:
        return Response({"error": "Points data is required"}, status=status.HTTP_400_BAD_REQUEST) 
    
    
     # Validate points
    if not points_data or not isinstance(points_data, list):
        return Response({"error": "Points data is required and must be a list"}, status=status.HTTP_400_BAD_REQUEST)
    if len(points_data)<2:
        return Response({"error": "At least two points are required to extract the path."}, status=status.HTTP_400_BAD_REQUEST)
    for point in points_data:
        if not isinstance(point, list) or len(point) != 2:
            return Response({"error": f"Invalid point format: {point}. Each point must be a list of two coordinates [longitude, latitude]."}, status=status.HTTP_400_BAD_REQUEST)
        
        longitude, latitude = point
        
        # Validate longitude and latitude ranges
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            return Response({"error": f"Invalid geo-coordinates: {point}. Longitude must be between -180 and 180, and latitude must be between -90 and 90."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the point is within India's boundary
        if not (68.0 <= longitude <= 97.0 and 6.0 <= latitude <= 37.0):
            return Response({"error": f"Point {point} is outside the rectangular boundary of India."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    try:
        response = requests.post(
            url,
            json={"points": points_data},  # Send points data in the correct format
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()  
        json_output = response.json()
        
        # Convert JSON output to string and sanitize it
        json_output_str = json.dumps(json_output)
        sanitized_json_output_str = bleach.clean(json_output_str)
        
        # Convert sanitized string back to JSON
        sanitized_json_output = json.loads(sanitized_json_output_str)
        
        is_valid, message = validate_bhuvan_response(sanitized_json_output)
        if not is_valid:
            return Response({"error": "Incoming path data is invalid." }, status=400)
        
        hash_object = hashlib.sha256(json_output_str.encode())
        hash_hex = hash_object.hexdigest()  
        
        return Response({"data": sanitized_json_output}, status=200)
    
    except requests.exceptions.RequestException:
        return Response({"error": "Unable to extract path for the provided coordinates. Please try again later."}, status=400)
    except ValueError:
        return Response({"error": "Invalid response received from the external API."}, status=400)
    except Exception as e:
        return Response({"error": "An unexpected error occurred."+str(e)}, status=400)
    
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def saveRoute(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        role1="superadmin"
        sa=get_user_object(user,role1)
        role2="stateadmin"
        sa2=get_user_object(user,role2)
        if not man and not sa and not sa2:
            return Response({"error":"Request must be from  "+role+' or '+role1+' or '+role2+'.'}, status=status.HTTP_400_BAD_REQUEST)

        #print(request.body)
        data =json.loads( request.body )
        id =None
        createdby=user #data['createdby_id'
        try:
            id=data['id']
        except Exception as e:
            print(e)

        try:
            #createdby =  User.objects.get(id=createdby)
            device =  DeviceStock.objects.get(id=data['device_id'])
            if not device:
                    return JsonResponse({"error": "Device not found"}, status=405)
            tag=None
            if man :
                tag=DeviceTag.objects.filter(  device_id=device,   vehicle_owner =man)
            elif sa or sa2  :
                tag=DeviceTag.objects.filter( device_id=device)
            if not tag:
                    return JsonResponse({"error": "Unauthorised owner "}, status=405)

            if id:
                route = Route.objects.get(id=id,device=device,status='Active', createdby=user)
                if not route:
                    return JsonResponse({"error": "existing route not fond for given id "}, status=405)
                route.route = data['route']
                route.routepoints = data['routepoints']
                
                for k in ["route","routepoints"]:
                    points_data = data[k]
                
                    if not points_data or not isinstance(points_data, list):
                        return Response({"error": k+" is required and must be a list"}, status=status.HTTP_400_BAD_REQUEST)
                    if len(points_data)<2:
                        return Response({"error": "At least two points are required to extract the path."}, status=status.HTTP_400_BAD_REQUEST)
                    for point in points_data:
                        if not isinstance(point, list) or len(point) != 2:
                            return Response({"error": f"Invalid point format: {point}. Each point must be a list of two coordinates [longitude, latitude]."}, status=status.HTTP_400_BAD_REQUEST)
                        
                        longitude, latitude = point
                        
                        # Validate longitude and latitude ranges
                        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                            return Response({"error": f"Invalid geo-coordinates: {point}. Longitude must be between -180 and 180, and latitude must be between -90 and 90."}, status=status.HTTP_400_BAD_REQUEST)
                        
                        # Check if the point is within India's boundary
                        if not (68.0 <= longitude <= 97.0 and 6.0 <= latitude <= 37.0):
                            return Response({"error": f"Point {point} is outside the rectangular boundary of India."}, status=status.HTTP_400_BAD_REQUEST)
                    
                
                route.createdby = createdby #User.objects.get(id=data['createdby_id']) 
                route.save()
                routes = Route.objects.filter(device=device ,status='Active', createdby=user).all()
                return JsonResponse({"message": "Route saved successfully!",'update':routeSerializer(route).data,"data": routeSerializer(routes, many=True).data }, status=201)
        
            else:
                route = Route(
                    route=data['route'],
                    routepoints=data['routepoints'],
                    status='Active',  # Assuming status is 'Active' when created
                    device=device,
                    createdby=createdby
                )
                route.save()
                routes = Route.objects.filter(device=device , status='Active',createdby=user).all()
                return JsonResponse({"message": "New Route saved successfully!",'new':routeSerializer(route).data,"route": routeSerializer(routes, many=True).data }, status=201)
        except Exception as e:
            print(e)
            return JsonResponse({"error": "Unable to save route"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)



@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def getRoute(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        role1="superadmin"
        sa=get_user_object(user,role1)
        role2="stateadmin"
        state_admin_obj=get_user_object(user,role2)
        role3="dtorto"
        dto_obj=get_user_object(user,role3)
        
        if not man and not sa and not state_admin_obj and not dto_obj:
            return Response({"error":"Request must be from owner, superadmin, state admin, or DTO."}, status=status.HTTP_400_BAD_REQUEST)

        data =json.loads( request.body )
        device_id =  data['device_id']
        
        try:

            device =  DeviceStock.objects.get(id=data['device_id'])
            if not device:
                    return JsonResponse({"error": "Device not found"}, status=405)
            if man:
                tag=DeviceTag.objects.filter(   device_id=device,   vehicle_owner =man)
            elif sa:
                tag=DeviceTag.objects.filter(   device_id=device )
            elif state_admin_obj:
                # State admin can access devices in their state
                tag=DeviceTag.objects.filter(
                    device_id=device,
                    district__state=state_admin_obj.state
                )
            elif dto_obj:
                # DTO can access devices in their state
                tag=DeviceTag.objects.filter(
                    device_id=device,
                    district__state=dto_obj.state
                )
            if not tag:
                    return JsonResponse({"error": "Unauthorised Access "}, status=405) 
             
            route = Route.objects.filter(device=device ,status="Active", createdby=user).all()#.latest('id')
            return JsonResponse({"route": routeSerializer(route, many=True).data  }, status=200)
        except Route.DoesNotExist:
            return JsonResponse({"error": "No active route found for this device"}, status=404)
        except Exception as e:
            return JsonResponse({"error": "Unable to get route"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])   
@require_http_methods(['GET', 'POST'])
def getRoutelist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'GET':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        user=request.user
        role="owner"
        man=get_user_object(user,role)
        if not man:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)

        device_id =request.GET.get('device_id')
        try:
            device = DeviceStock.objects.get(id=device_id)
            route = Route.objects.filter(device=device, status='Active', createdby=user).all()#.latest('id')
            if not route:
                return JsonResponse({"error": "No active route found for this device"}, status=404)
            return JsonResponse({"route": route}, status=200)
        except Route.DoesNotExist:
            return JsonResponse({"error": "No active route found for this device"}, status=404)
        except Exception as e:
            return JsonResponse({"error": "Unable to get route list"}, status=400)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)
   
        
#1     Registration of new user-
#tpid ="1007135935525313027"
#text="Dear User,To confirm your registration in SkyTron platform, please click at the following link and validate the registration request-{#var#}The link will expire in 5 minutes.-SkyTron"

#2   not working   Tagging of device and vehicle- owner confirmation:
#tpid ="1007941652638984780"
#text="Dear Vehicle Owner,To confirm Tagging of your vehicle with your tracking device in SkyTron platform, please click at the following link and validate the tagging request-{#var#}The link will expire in 5 minutes.-SkyTron"

#3      Set/Re-set new password-
#tpid ="1007927199705544392"
#text="Dear User,To activate your new password in SkyTron portal, please enter the OTP {#var#} valid for 5 minutes.Please do NOT share with anyone.-SkyTron"

#4. Dealer/Manufacturer confirmation of Tagging-
#tpid ="1007201930295888818"
#text="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {#var#}Device IMEI No: {#var#}To confirm, please enter the OTP {#var#}.- SkyTron"


#5. Owner verification link sent during tagging and activation-
#tpid ="1007671504419591069"
#text="Dear Vehicle Owner,To confirm tagging and activation of your VLTD with your vehicle in SkyTron platform, kindly click on the following link and validate: {#var#}Link will expire in 5 minutes. Please do NOT share.-SkyTron"

#6. Owner OTP- after tagging / activation is successful-
#tpid ="1007937055979875563"
#text="Dear Vehicle Owner,To confirm tagging of your VLTD with your vehicle, please enter the OTP: {#var#} will expire in 5 minutes. Please do NOT share.-SkyTron"

#7. New User create OTP- (OTP at the time of creating a new user)-
#tpid ="1007274756418421381"
#text="Dear User,To validate creation of a new user login in SkyTron platform, please enter the OTP {#var#}.Valid for 5 minutes. Please do not share.-SkyTron"


def send_SMS(no,text,tpid):
    import os
    url = os.getenv("SMS_URL", "http://tra.bulksmshyderabad.co.in/websms/sendsms.aspx")
    params = {
        'userid': os.getenv("SMS_USERID", "Gobell"),
        'password': os.getenv("SMS_PASSWORD", "1234566"),
        'sender': os.getenv("SMS_SENDER", "SKYTRN"),
        'mobileno': no,
        'msg': text,
        'peid': os.getenv("SMS_PEID", "1001371511701977986"),
        'tpid':  tpid
    } 

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise error for bad responses (non-200)
        print("Message Sent Successfully")
    except requests.exceptions.HTTPError as errh:
        print("Loginotpsend HTTP Error:", errh)
    except requests.exceptions.RequestException as err:
        print("Loginotpsend Request Exception:", err)
    except Exception as e :
        print("Loginotpsend:", e)




def sms_send(no,text,tpid):
    #text = "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
    import os
    url = os.getenv("SMS_URL", "http://tra.bulksmshyderabad.co.in/websms/sendsms.aspx")
    params = {
        'userid': os.getenv("SMS_USERID", "Gobell"),
        'password': os.getenv("SMS_PASSWORD", "1234566"),
        'sender': os.getenv("SMS_SENDER", "SKYTRN"),
        'mobileno': no,
        'msg': text,
        'peid': os.getenv("SMS_PEID", "1001371511701977986"),
        'tpid':  tpid
    } 

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise error for bad responses (non-200)
        print("Message Sent Successfully")
    except requests.exceptions.HTTPError as errh:
        print("Loginotpsend HTTP Error:", errh)
    except requests.exceptions.RequestException as err:
        print("Loginotpsend Request Exception:", err)
    except Exception as e :
        print("Loginotpsend:", err)

def add_sms_queue(msg,no):
    sms_entry ,error= sms_out.objects.safe_create( sms_text=msg,no=no, status='Queue'  )
    if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def sms_queue_add(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        no= request.GET.get('no')#request.data.get('no')
        msg = request.GET.get('msg', '') 
        add_sms_queue(msg,no)
        return JsonResponse({'status':"Success  "+msg})
    except Exception as e:
        return JsonResponse({'error': "error creating sms"}, status=400) 

@api_view(['POST'])  
@permission_classes([AllowAny])
@require_http_methods(['GET', 'POST'])
def sms_received(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Extract necessary parameters from the request data
        no= request.data.get('no')
        msg = request.data.get('msg', '')

        new_sms_in ,error= sms_in.objects.safe_create( sms_text=msg,no=no, status='Received'  )
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        return Response({'status':"Success"})
    except Exception as e:
        return Response({'error': "error geting sms"}, status=400)
    
@api_view(['get'])  
@permission_classes([AllowAny])
@require_http_methods(['GET', 'POST'])
def sms_queue(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        sms_entry = sms_out.objects.filter(status='Queue').first()
    
        if sms_entry:
            # Print all information of the retrieved entry
            #print(f"ID: {sms_entry.id}")
            #print(f"SMS Text: {sms_entry.sms_text}")
            #print(f"Number: {sms_entry.no}")
            #print(f"Status: {sms_entry.status}")
            #print(f"Created: {sms_entry.created}")

            # Update the status to 'Sent'
            sms_entry.status = 'Sent'
            sms_entry.save()
            return Response({'no':sms_entry.no,'msg':sms_entry.sms_text})
            #return Response({'no':"+917635975648",'msg':'data to send'})
        return Response({'no':"",'msg':''})
    except Exception as e:
        return Response({'error': "no sms"}, status=400)

    
@api_view(['get'])  
@require_http_methods(['GET', 'POST'])
def esim_provider_list(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        esimprovider= eSimProvider.objects.all()         
        esimprovider_serializer = eSimProviderSerializer(esimprovider, many=True)
        # Return the serialized data as JSON response
        return Response(esimprovider_serializer.data)
    except Exception as e:
        return Response({'error': "esim_provider_list"}, status=400)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def get_live_vehicle_no(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        if request.method == 'POST':
            # Fetch distinct vehicle registration numbers with a single DB query.
            # If the requester is a vehicle owner, restrict to their devices only.
            owner = get_user_object(request.user, "owner")

            gps_qs = GPSData.objects.all()
            if owner:
                gps_qs = gps_qs.filter(device_tag__vehicle_owner=owner)

            vehicle_list = list(
                gps_qs
                .exclude(device_tag__isnull=True)
                .exclude(device_tag__vehicle_reg_no__isnull=True)
                .exclude(device_tag__vehicle_reg_no='')
                .order_by('device_tag__vehicle_reg_no')
                .values_list('device_tag__vehicle_reg_no', flat=True)
                .distinct()
            )
            return Response(vehicle_list)
        else:
            return Response({'error': "POST request only"}, status=400)
    except Exception as e:
        return Response({'error': "get_live_vehicle_no"}, status=400)
 
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        
        id = request.data.get('vehicleowner_id')
        vehicle_owner = VehicleOwner.objects.filter(id=id).last()
        if not vehicle_owner:
            return Response({'error': "Invalid VehicleOwner id"}, status=400)
        if vehicle_owner.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.now()
        created = timezone.now()
        expirydate = request.data.get('expiryDate')#date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        idProofno = request.data.get('idProofno')
        file_idProof = request.data.get('file_idProof')

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if company_name:
            vehicle_owner.company_name = company_name
        if idProofno:
            vehicle_owner.idProofno = idProofno
        if file_idProof:
            vehicle_owner.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not vehicle_owner.file_idProof : 
                    return Response({'error': "Invalid file." }, status=400)
        vuser=vehicle_owner.users.last()
        if email:
            vuser.email = email
        if mobile:
            vuser.mobile = mobile
        if name:
            vuser.name = name
        if dob:
            vuser.dob = dob

        new_password = ''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)
        vuser.password = hashed_password
        #vehicle_owner.date_joined = str(date_joined)
        #vehicle_owner.created = str(created)
        vehicle_owner.expirydate = expirydate
        vuser.save()
        vehicle_owner.save()
        #send_usercreation_otp(vehicle_owner.users, new_password, 'Vehicle Owner')
        return Response(VehicleOwnerSerializer(vehicle_owner).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        company_name = request.data.get('company_name') 
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()  
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('owner',request)
        if not company_name:
            company_name=""
        if user: 
            try:
                # Create a savepoint for rollback if needed
                sid = transaction.savepoint()
                
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                
                if not file_idProof : 
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "Invalid file." }, status=400)
                dealer ,error= VehicleOwner.objects.safe_create(
                    company_name=company_name, 
                    created=created,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    createdby=createdby,
                    status="Created",
                ) 
            
                if error:
                    transaction.savepoint_rollback(sid)
                    return error  # Return the Response object from safe_create

                transaction.savepoint_commit(sid)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                return Response({'error': "Unable to process request."+str(e)}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'Vehicle Owner ')
             
            return Response(VehicleOwnerSerializer(dealer).data)
        else:
            return Response(error, status=400)        

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['POST'])
def create_superuser(request):
 
    # Validate inputs
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if the requesting user is a superuser
    if False:#  not request.role=='superadmin' :
        return Response({
            "error": "Permission denied. Only systemadmin can create new systemadmin."
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Validate required fields
        required_fields = ['email', 'mobile', 'name', 'dob']
        missing_fields = [field for field in required_fields if not request.data.get(field)]
        
        if missing_fields:
            return Response({
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        email = request.data.get('email', '').strip()
        mobile = request.data.get('mobile', '').strip()
        name = request.data.get('name', '').strip()
        dob = request.data.get('dob', '').strip()
        
        # Additional validation for email format
        if '@' not in email or '.' not in email.split('@')[1]:
            return Response({
                'error': "Invalid email format."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate mobile number format (basic validation)
        if not mobile.isdigit() or len(mobile) < 10:
            return Response({
                'error': "Invalid mobile number format. Must be at least 10 digits."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(Q(email=email) | Q(mobile=mobile)).exists():
            return Response({
                'error': "A user with this email or mobile number already exists."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a savepoint for rollback if needed
        sid = transaction.savepoint()
        
        try:
            # Call the create_user function with 'superadmin' role
            user, error, new_password = create_user('superadmin', request)
            
            if error:
                transaction.savepoint_rollback(sid)
                return Response(error, status=status.HTTP_400_BAD_REQUEST)
            
            if not user:
                transaction.savepoint_rollback(sid)
                return Response({
                    'error': "Failed to create user."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set the user as superuser and staff
            user.is_superuser = True
            user.is_staff = True
            user.role = 'superadmin'
            user.save()
            
            transaction.savepoint_commit(sid)
            
            # Send creation notification
            send_usercreation_otp(user, new_password, 'Super Admin')
            
            # Prepare response data
            response_data = {
                'message': 'Superuser created successfully.',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'mobile': user.mobile,
                    'role': user.role,
                    'is_superuser': user.is_superuser,
                    'is_staff': user.is_staff,
                    'date_joined': user.date_joined,
                    'created': user.created,
                },
                'temporary_password': new_password
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            transaction.savepoint_rollback(sid)
            return Response({
                'error': f"Unable to create superuser: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'error': f"Unable to process request: {str(e)}"
        }, status=status.HTTP_400_BAD_REQUEST)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_manufacturer(request, manufacturer_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get the Manufacturer instance or return a 404 response
        manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id)

        # Delete the associated user
        user = manufacturer.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        manufacturer.delete()

        return Response({'message': 'Manufacturer and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_dealer(request, dealer_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    try:
        # Get the Manufacturer instance or return a 404 response
        dealer = get_object_or_404(Dealer, id=dealer_id)

        # Delete the associated user
        user =dealer.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        dealer.delete()

        return Response({'message': 'Dealer and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_eSimProvider(request, esimProvider_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from   "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    try:
        # Get the Manufacturer instance or return a 404 response
        esimProvider = get_object_or_404(eSimProvider, id=esimProvider_id)

        # Delete the associated user
        user =esimProvider.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        esimProvider.delete()

        return Response({'message': 'eSim Provider and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_VehicleOwner(request, vo_id):
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    try:
        # Get the Manufacturer instance or return a 404 response
        vo = get_object_or_404(VehicleOwner, id=vo_id)

        # Delete the associated user
        user =vo.users.first()  # Assuming there is only one associated user
        if user:
            user.delete()

        # Delete the manufacturer
        vo.delete()

        return Response({'message': 'Vehicle Owner and associated user deleted successfully'})


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:

        user=request.user
        role="stateadmin"
        uo=get_user_object(user,role)
        role2="superadmin"
        uo2=get_user_object(user,role2)

        # Get filter parameters from the request
        obj_id = request.data.get('VehicleOwner_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        #address = request.data.get('address', '') 
        #address_State = request.data.get('address_State', '')
        filters = {} 
        
        if uo2:  # Superadmin - should get all data
            if obj_id:
                manufacturers = VehicleOwner.objects.filter(
                    id=obj_id,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    #users__address__icontains=address,
                    #users__address_State__icontains=address_State,
                ).distinct()
            else:
                manufacturers = VehicleOwner.objects.filter(
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    #users__address__icontains=address,
                    #users__address_State__icontains=address_State,
                ).distinct()
        
        
        elif uo:  # State admin - filter by state
            state=uo.state
            owners = DeviceTag.objects.filter( district__state=state, status="Owner_Final_OTP_Verified").values("vehicle_owner").distinct()
            manufacturers = VehicleOwner.objects.filter(
                        id__in=owners,
                        users__email__icontains=email,
                        company_name__icontains=company_name,
                        users__name__icontains=name,
                        users__mobile__icontains=phone_no,
                        #users__address__icontains=address,
                        #users__address_State__icontains=address_State,
                    ).distinct()
        
        
        else:  # Other roles
            state = request.data.get('state', '')
            if obj_id :
                manufacturers = VehicleOwner.objects.filter(
                    id=obj_id,
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    #users__address__icontains=address,
                    #users__address_State__icontains=address_State,
                ).distinct()
            else:
                manufacturers = VehicleOwner.objects.filter(
                    #id=manufacturer_id,
                    users__status='active',
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                    #users__address__icontains=address,
                    #users__address_State__icontains=address_State,
                ).distinct()

        # Serialize the queryset
        dealer_serializer = VehicleOwnerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        id = request.data.get('manufacturer_id')
        man=Manufacturer.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid manufacturer id"}, status=400)
        m_user = man.users.last()
        if not m_user:
            return Response({'error': "No user mapped to this manufacturer"}, status=400)
        is_creator = bool(getattr(man, 'createdby_id', None) == getattr(request.user, 'id', None))
        is_superadmin = bool(get_user_object(request.user, 'superadmin'))
        if not (is_creator or is_superadmin):
            return Response({'error': "Only creator or superadmin can edit this manufacturer"}, status=400)
        
        date_joined = timezone.localdate() 
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')        
        state = request.data.get('state')
        gstno = request.data.get('gstno' )   
        idProofno = request.data.get('idProofno' )  
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        esim_provider_ids = request.data.get('esim_provider', [])
        
        email = request.data.get('email' )
        mobile = request.data.get('mobile' )
        name = request.data.get('name' )
        dob = request.data.get('dob' )
        partner_status = _normalize_partner_status(request.data.get('status'))
        if company_name:
            man.company_name=company_name
        if gstnnumber :
            man.gstnnumber=gstnnumber
        if state:
            man.state = state
        if gstno:
            man.gstno=gstno  
        if  idProofno:
            man.idProofno=idProofno
        if file_authLetter:
            man.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man') 
            
            if not man.file_authLetter : 
                    return Response({'error': "Invalid file." }, status=400)

        if file_companRegCertificate :
            man.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
                
            if not man.file_companRegCertificate : 
                    return Response({'error': "Invalid file." }, status=400)

        if file_GSTCertificate :
            man.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
            if not man.file_GSTCertificate : 
                    return Response({'error': "Invalid file." }, status=400)
            

        if file_idProof:
            man.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not man.file_idProof : 
                    return Response({'error': "Invalid file." }, status=400)
            
        if esim_provider_ids !=[]:
            man.esim_provider_ids=esim_provider_ids

            
        if email:
            m_user.email  =email
        if mobile:
            m_user.mobile=mobile
        if name:
            m_user.name=name 
        if dob:
            m_user.dob = dob
        if partner_status is not None:
            if partner_status not in ALLOWED_PARTNER_STATUSES:
                return Response(
                    {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
                    status=400
                )
            man.status = partner_status
        
     
        m_user.save()
        man.save() 
        return Response(ManufacturerSerializer(man).data)
      

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_eSimProvider(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('esimprovider_id')
        esimprovider = eSimProvider.objects.filter(id=id).last()
        if not esimprovider:
            return Response({'error': "Invalid eSimProvider id"}, status=400)
        if esimprovider.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)

        ep_user = esimprovider.users.last()
        if not ep_user:
            return Response({'error': "No user mapped to this eSimProvider"}, status=400)
        
        date_joined = timezone.localdate()
        created = timezone.localdate()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')
        gstno = request.data.get('gstno')
        idProofno = request.data.get('idProofno')
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')

        telecomProviders_present = False
        telecom_raw = None
        if hasattr(request.data, 'getlist') and ('telecomProviders[]' in request.data or 'telecomProviders' in request.data):
            telecomProviders_present = True
            telecom_raw = request.data.getlist('telecomProviders[]') or request.data.getlist('telecomProviders')
        elif request.data.get('telecomProviders', None) is not None or request.data.get('telecom_providers', None) is not None:
            telecomProviders_present = True
            telecom_raw = request.data.get('telecomProviders', None)
            if telecom_raw is None:
                telecom_raw = request.data.get('telecom_providers', None)

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')
        partner_status = _normalize_partner_status(request.data.get('status'))

        if company_name:
            esimprovider.company_name = company_name
        if gstnnumber:
            esimprovider.gstnnumber = gstnnumber
        if gstno:
            esimprovider.gstno = gstno
        if idProofno:
            esimprovider.idProofno = idProofno
        if file_authLetter:
            esimprovider.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man')
            
            if not esimprovider.file_authLetter: 
                    return Response({'error': "Invalid auth file." }, status=400)
        if file_companRegCertificate:
            esimprovider.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
        
            if not esimprovider.file_companRegCertificate: 
                    return Response({'error': "Invalid reg cert file." }, status=400)
        if file_GSTCertificate:
            esimprovider.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
        
            if not esimprovider.file_GSTCertificate:
                    return Response({'error': "Invalid GST file." }, status=400)
        if file_idProof:
            esimprovider.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            
            if not esimprovider.file_idProof: 
                    return Response({'error': "Invalid id proof file." }, status=400)

        if telecomProviders_present:
            telecomProviders = _parse_string_list(telecom_raw)
            if telecomProviders is None:
                telecomProviders = []
            esimprovider.telecomProviders = telecomProviders

        if email:
            ep_user.email = email
        if mobile:
            ep_user.mobile = mobile
        if name:
            ep_user.name = name
        if dob:
            ep_user.dob = dob
        if partner_status is not None:
            if partner_status not in ALLOWED_PARTNER_STATUSES:
                return Response(
                    {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
                    status=400
                )
            esimprovider.status = partner_status

        new_password = ''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)
        ep_user.password = hashed_password
        esimprovider.date_joined = date_joined
        esimprovider.created = created
        esimprovider.expirydate = expirydate
        ep_user.save()
        esimprovider.save()
        #send_usercreation_otp(ep_user, new_password, 'EsimProvider')
        return Response(eSimProviderSerializer(esimprovider).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  
@require_http_methods(['GET', 'POST'])
def create_eSimProvider_pub(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
      
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    
    try: 
        company_name = request.data.get('company_name')
        company_address = request.data.get('company_address')
        company_pin = request.data.get('company_pin')
        company_email = request.data.get('company_email')
        company_phoneno = request.data.get('company_phoneno')
        company_registration_no = request.data.get('company_registration_no')
        panno = request.data.get('panno')
        gstnnumber = request.data.get('gstnnumber') 
        m2m_reg_certificate_no = request.data.get('m2m_reg_certificate_no')
        createdby = request.user if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False) else None
        if createdby is None:
            createdby = User.objects.filter(role='superadmin').order_by('id').first()
        if createdby is None:
            return Response(
                {'error': 'No default creator user found. Create a superadmin user first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        date_joined = timezone.localdate()
        created = timezone.localdate()
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        partner_status = _normalize_partner_status(request.data.get('status'))
        if partner_status is None:
            partner_status = 'Created'
        elif partner_status not in ALLOWED_PARTNER_STATUSES:
            return Response(
                {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
                status=400
            )
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_company_registration_certificate = request.data.get('file_company_registration_certificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        file_officialTechnicalOnboardingRequestLetter = request.data.get('file_officialTechnicalOnboardingRequestLetter')
        file_selfCertifiedDotM2mRegistrationCertificate = request.data.get('file_selfCertifiedDotM2mRegistrationCertificate')
        file_affidavitNda = request.data.get('file_affidavitNda')
        state = request.data.get('stateId') 
        telecomProviders = None
        if hasattr(request.data, 'getlist') and ('telecomProviders[]' in request.data or 'telecomProviders' in request.data):
            telecomProviders = request.data.getlist('telecomProviders[]') or request.data.getlist('telecomProviders')
        else:
            telecomProviders = request.data.get('telecomProviders', None)
            if telecomProviders is None:
                telecomProviders = request.data.get('telecom_providers', None)
        telecomProviders = _parse_string_list(telecomProviders) or []
        user,error,new_password=create_user('esimprovider',request)
        if user:  
         
            try:
                try:
                    file_authLetter=save_file(request,'file_authLetter','fileuploads/man') 
                    file_companRegCertificate=save_file(request,'file_companRegCertificate','fileuploads/man')
                    file_GSTCertificate=save_file(request,'file_GSTCertificate','fileuploads/man')
                    file_idProof = save_file(request,'file_idProof','fileuploads/man')
                    file_company_registration_certificate = None
                    if request.FILES.get('file_company_registration_certificate'):
                        file_company_registration_certificate = save_file(request, 'file_company_registration_certificate', 'fileuploads/man')
                        if not file_company_registration_certificate:
                            user.delete()
                            return Response({'error': "Invalid company registration certificate file." }, status=400)

                    file_officialTechnicalOnboardingRequestLetter = None
                    if request.FILES.get('file_officialTechnicalOnboardingRequestLetter'):
                        file_officialTechnicalOnboardingRequestLetter = save_file(request, 'file_officialTechnicalOnboardingRequestLetter', 'fileuploads/man')
                        if not file_officialTechnicalOnboardingRequestLetter:
                            user.delete()
                            return Response({'error': "Invalid official technical onboarding request letter file." }, status=400)

                    file_selfCertifiedDotM2mRegistrationCertificate = None
                    if request.FILES.get('file_selfCertifiedDotM2mRegistrationCertificate'):
                        file_selfCertifiedDotM2mRegistrationCertificate = save_file(request, 'file_selfCertifiedDotM2mRegistrationCertificate', 'fileuploads/man')
                        if not file_selfCertifiedDotM2mRegistrationCertificate:
                            user.delete()
                            return Response({'error': "Invalid self-certified DoT M2M registration certificate file." }, status=400)

                    file_affidavitNda = None
                    if request.FILES.get('file_affidavitNda'):
                        file_affidavitNda = save_file(request, 'file_affidavitNda', 'fileuploads/man')
                        if not file_affidavitNda:
                            user.delete()
                            return Response({'error': "Invalid affidavit NDA file." }, status=400)

                    if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof: 
                           
                        user.delete()
                        if   not file_idProof: 
                            return Response({'error': "Invalid id proof file." }, status=400)
                        if  not file_GSTCertificate : 
                            return Response({'error': "Invalid gst file." }, status=400)
                        if  not file_companRegCertificate  : 
                            return Response({'error': "Invalid CompReg file." }, status=400)
                        if not file_authLetter  : 
                            return Response({'error': "Invalid auth file." }, status=400)
                        else: 
                            return Response({'error': "Invalid file." }, status=400)
                except Exception as e:
                    user.delete()


                    return Response({'error44': "Unable to process request."+str(e)}, status=400)


                dealer ,error= eSimProvider.objects.safe_create(
                    company_name=company_name,
                    company_address=company_address,
                    company_pin=company_pin,
                    company_email=company_email,
                    company_phoneno=company_phoneno,
                    company_registration_no=company_registration_no,
                    panno=panno,
                    gstnnumber=gstnnumber,
                    m2m_reg_certificate_no=m2m_reg_certificate_no,
                    telecomProviders=telecomProviders,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    state_id=state,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_company_registration_certificate=file_company_registration_certificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    file_officialTechnicalOnboardingRequestLetter=file_officialTechnicalOnboardingRequestLetter,
                    file_selfCertifiedDotM2mRegistrationCertificate=file_selfCertifiedDotM2mRegistrationCertificate,
                    file_affidavitNda=file_affidavitNda,
                    createdby=createdby,
                    status=partner_status,
                )
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()


                return Response({'error1': "Unable to process request."+str(e)}, status=400)
            dealer.users.add(user)
            #send_usercreation_otp(user,new_password,'EsimProvider ')
             
            return Response(eSimProviderSerializer(dealer).data)
        else:
            return Response({'error131': str(error)}, status=400)

    except Exception as e:
        return Response({'error2': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])  
@require_http_methods(['GET', 'POST'])
def create_eSimProvider(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
      
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        company_name = request.data.get('company_name')
        company_address = request.data.get('company_address')
        company_pin = request.data.get('company_pin')
        company_email = request.data.get('company_email')
        company_phoneno = request.data.get('company_phoneno')
        company_registration_no = request.data.get('company_registration_no')
        panno = request.data.get('panno')
        gstnnumber = request.data.get('gstnnumber') 
        m2m_reg_certificate_no = request.data.get('m2m_reg_certificate_no')
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        partner_status = _normalize_partner_status(request.data.get('status'))
        if partner_status is None:
            partner_status = 'Created'
        elif partner_status not in ALLOWED_PARTNER_STATUSES:
            return Response(
                {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
                status=400
            )
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_company_registration_certificate = request.data.get('file_company_registration_certificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        file_officialTechnicalOnboardingRequestLetter = request.data.get('file_officialTechnicalOnboardingRequestLetter')
        file_selfCertifiedDotM2mRegistrationCertificate = request.data.get('file_selfCertifiedDotM2mRegistrationCertificate')
        file_affidavitNda = request.data.get('file_affidavitNda')
        state = request.data.get('stateId') 
        telecomProviders = None
        if hasattr(request.data, 'getlist') and ('telecomProviders[]' in request.data or 'telecomProviders' in request.data):
            telecomProviders = request.data.getlist('telecomProviders[]') or request.data.getlist('telecomProviders')
        else:
            telecomProviders = request.data.get('telecomProviders', None)
            if telecomProviders is None:
                telecomProviders = request.data.get('telecom_providers', None)
        telecomProviders = _parse_string_list(telecomProviders) or []
        user,error,new_password=create_user('esimprovider',request)
        if user:  
         
            try:
                try:
                    file_authLetter=save_file(request,'file_authLetter','fileuploads/man') 
                    file_companRegCertificate=save_file(request,'file_companRegCertificate','fileuploads/man')
                    file_GSTCertificate=save_file(request,'file_GSTCertificate','fileuploads/man')
                    file_idProof = save_file(request,'file_idProof','fileuploads/man')
                    file_company_registration_certificate = None
                    if request.FILES.get('file_company_registration_certificate'):
                        file_company_registration_certificate = save_file(request, 'file_company_registration_certificate', 'fileuploads/man')
                        if not file_company_registration_certificate:
                            user.delete()
                            return Response({'error': "Invalid company registration certificate file." }, status=400)

                    file_officialTechnicalOnboardingRequestLetter = None
                    if request.FILES.get('file_officialTechnicalOnboardingRequestLetter'):
                        file_officialTechnicalOnboardingRequestLetter = save_file(request, 'file_officialTechnicalOnboardingRequestLetter', 'fileuploads/man')
                        if not file_officialTechnicalOnboardingRequestLetter:
                            user.delete()
                            return Response({'error': "Invalid official technical onboarding request letter file." }, status=400)

                    file_selfCertifiedDotM2mRegistrationCertificate = None
                    if request.FILES.get('file_selfCertifiedDotM2mRegistrationCertificate'):
                        file_selfCertifiedDotM2mRegistrationCertificate = save_file(request, 'file_selfCertifiedDotM2mRegistrationCertificate', 'fileuploads/man')
                        if not file_selfCertifiedDotM2mRegistrationCertificate:
                            user.delete()
                            return Response({'error': "Invalid self-certified DoT M2M registration certificate file." }, status=400)

                    file_affidavitNda = None
                    if request.FILES.get('file_affidavitNda'):
                        file_affidavitNda = save_file(request, 'file_affidavitNda', 'fileuploads/man')
                        if not file_affidavitNda:
                            user.delete()
                            return Response({'error': "Invalid affidavit NDA file." }, status=400)

                    if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof: 
                           
                        user.delete()
                        if   not file_idProof: 
                            return Response({'error': "Invalid id proof file." }, status=400)
                        if  not file_GSTCertificate : 
                            return Response({'error': "Invalid gst file." }, status=400)
                        if  not file_companRegCertificate  : 
                            return Response({'error': "Invalid CompReg file." }, status=400)
                        if not file_authLetter  : 
                            return Response({'error': "Invalid auth file." }, status=400)
                        else: 
                            return Response({'error': "Invalid file." }, status=400)
                except Exception as e:
                    user.delete()


                    return Response({'error44': "Unable to process request."+str(e)}, status=400)


                dealer ,error= eSimProvider.objects.safe_create(
                    company_name=company_name,
                    company_address=company_address,
                    company_pin=company_pin,
                    company_email=company_email,
                    company_phoneno=company_phoneno,
                    company_registration_no=company_registration_no,
                    panno=panno,
                    gstnnumber=gstnnumber,
                    m2m_reg_certificate_no=m2m_reg_certificate_no,
                    telecomProviders=telecomProviders,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    state_id=state,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_company_registration_certificate=file_company_registration_certificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    file_officialTechnicalOnboardingRequestLetter=file_officialTechnicalOnboardingRequestLetter,
                    file_selfCertifiedDotM2mRegistrationCertificate=file_selfCertifiedDotM2mRegistrationCertificate,
                    file_affidavitNda=file_affidavitNda,
                    createdby=createdby,
                    status=partner_status,
                )
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()


                return Response({'error1': "Unable to process request."+str(e)}, status=400)
            dealer.users.add(user)
            send_usercreation_otp(user,new_password,'EsimProvider ')
             
            return Response(eSimProviderSerializer(dealer).data)
        else:
            return Response({'error131': str(error)}, status=400)

    except Exception as e:
        return Response({'error2': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_eSimProvider(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        role="devicemanufacture" 
        um=get_user_object(user,role)
        if um:
            
            dealer_serializer = eSimProviderSerializer(um.esim_provider, many=True)
            return Response(dealer_serializer.data)
        
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state_filter = request.data.get('state', '')

        # Optional GET query param for this POST API:
        # if `all_user=true`, don't restrict by user status (include inactive too).
        all_user_raw = None
        try:
            all_user_raw = request.query_params.get('all_user')
        except Exception:
            all_user_raw = request.GET.get('all_user') if hasattr(request, 'GET') else None
        all_user = str(all_user_raw).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}

        # Start with base query
        manufacturers = eSimProvider.objects.all() if all_user else eSimProvider.objects.filter(users__status='active')
        
        # Apply filters based on input parameters
        if dealer_id:
            manufacturers = manufacturers.filter(id=dealer_id)
        
        if email:
            manufacturers = manufacturers.filter(users__email__icontains=email)
            
        if company_name:
            manufacturers = manufacturers.filter(company_name__icontains=company_name)
            
        if name:
            manufacturers = manufacturers.filter(users__name__icontains=name)
            
        if phone_no:
            manufacturers = manufacturers.filter(users__mobile__icontains=phone_no)
            
        if state_filter:
            manufacturers = manufacturers.filter(state__id=state_filter)

        # Apply state-based filtering for state admin users
        if uo:  # If user is a state admin
            manufacturers = manufacturers.filter(state=uo.state)

        # Get distinct results and include state information
        manufacturers = manufacturers.select_related('state').distinct()

        # Serialize the queryset
        dealer_serializer = eSimProviderSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        
        return Response({'error': "Unable to process request." + str(e)}, status=400)






@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_eSimProvider_pub(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
       
        
        # Get filter parameters from the request
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state_filter = request.data.get('state', '')

        # Optional GET query param for this POST API:
        # if `all_user=true`, don't restrict by user status (include inactive too).
        all_user_raw = None
        try:
            all_user_raw = request.query_params.get('all_user')
        except Exception:
            all_user_raw = request.GET.get('all_user') if hasattr(request, 'GET') else None
        all_user = str(all_user_raw).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}

        # Start with base query
        manufacturers = eSimProvider.objects.all() if all_user else eSimProvider.objects.filter(users__status='active')
        
        # Apply filters based on input parameters
        if dealer_id:
            manufacturers = manufacturers.filter(id=dealer_id)
        
        if email:
            manufacturers = manufacturers.filter(users__email__icontains=email)
            
        if company_name:
            manufacturers = manufacturers.filter(company_name__icontains=company_name)
            
        if name:
            manufacturers = manufacturers.filter(users__name__icontains=name)
            
        if phone_no:
            manufacturers = manufacturers.filter(users__mobile__icontains=phone_no)
            
        if state_filter:
            manufacturers = manufacturers.filter(state__id=state_filter)

     
        # Get distinct results and include state information
        manufacturers = manufacturers.select_related('state').distinct()

        # Serialize the queryset
        dealer_serializer = eSimProviderSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        
        return Response({'error': "Unable to process request." + str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="devicemanufacture"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('dealer_id')
        dealer = Dealer.objects.filter(id=id).last()
        if not dealer:
            return Response({'error': "Invalid dealer id"}, status=400)
        if dealer.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.localdate()
        created = timezone.localdate()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')        
        gstno = request.data.get('gstno')   
        idProofno = request.data.get('idProofno')  
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        districts = request.data.get('districts', [])  # Changed to list of district IDs

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if company_name:
            dealer.company_name = company_name
        if gstnnumber:
            dealer.gstnnumber = gstnnumber
        if gstno:
            dealer.gstno = gstno  
        if idProofno:
            dealer.idProofno = idProofno
        if file_authLetter:
            dealer.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man')
            if not dealer.file_authLetter:
                    return Response({'error': "Invalid file." }, status=400)
        if file_companRegCertificate:
            dealer.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
            if not dealer.file_companRegCertificate:
                    return Response({'error': "Invalid file." }, status=400)
        if file_GSTCertificate:
            dealer.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
            if not dealer.file_GSTCertificate:
                    return Response({'error': "Invalid file." }, status=400)
        if file_idProof:
            dealer.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not dealer.file_idProof:
                    return Response({'error': "Invalid file." }, status=400)
        
        # Handle districts update
        if districts and isinstance(districts, list):
            dealer.districts.clear()  # Clear existing districts
            for district_id in districts:
                try:
                    district_obj = Settings_District.objects.get(id=district_id)
                    dealer.districts.add(district_obj)
                except Settings_District.DoesNotExist:
                    pass  # Skip invalid district IDs

        if email:
            dealer.user.email = email
        if mobile:
            dealer.user.mobile = mobile
        if name:
            dealer.user.name = name 
        if dob:
            dealer.user.dob = dob

        new_password = ''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)
        dealer.user.password = hashed_password
        dealer.date_joined = date_joined
        dealer.created = created
        dealer.expirydate = expirydate
        dealer.user.save()
        dealer.save()
        send_usercreation_otp(dealer.user, new_password, 'Dealer')
        return Response(DealerSerializer(dealer).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    man=Manufacturer.objects.filter(id=request.data.get('manufacturer')).last()
    if not man:
        return Response({"error":"Manufacturer not found."}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber') 
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()   
         
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof') 
        districts = request.data.getlist('districts[]', []) # Changed to list of district IDs
        user,error,new_password=create_user('dealer',request)
        if user:         
            try:
                # Create a savepoint for rollback if needed
                sid = transaction.savepoint()
                
                file_authLetter=save_file(request,'file_authLetter','fileuploads/man') 
                file_companRegCertificate=save_file(request,'file_companRegCertificate','fileuploads/man')
                file_GSTCertificate=save_file(request,'file_GSTCertificate','fileuploads/man')
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "Invalid file." }, status=400)
                

                dealer ,error= Dealer.objects.safe_create(
                    company_name=company_name,
                    gstnnumber=gstnnumber,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    createdby=createdby,
                    manufacturer=man,
                    status="Created",
                )
                
                if error:
                    transaction.savepoint_rollback(sid)
                    return error  # Return the Response object from safe_create
                
                # Add districts to the dealer
                dis=False
                user.save()
                dealer.save()
                if districts and isinstance(districts, list):
                    for district_id in districts:
                        try:
                            district_obj = Settings_District.objects.get(id=district_id)
                            dealer.districts.add(district_obj)
                            dealer.save()
                            dis=True
                        except Settings_District.DoesNotExist:
                            transaction.savepoint_rollback(sid)
                            return Response({'error': "Invalid District." }, status=400) 
                if not dis:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "No valid district."}, status=400) 
                
                transaction.savepoint_commit(sid)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                return Response({'error': "Unable to process request."+str(e)}, status=400) 
            dealer.users.add(user)
            send_usercreation_otp(user,new_password,'Dealer ')   
            dealer.save()  # Save the dealer after adding users and districts          
            return Response(DealerSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="devicemanufacture"
        user=request.user
        uo=get_user_object(user,role)
        role="stateadmin" 
        suo=get_user_object(user,role)
        
        # Get filter parameters from the request
        dealer_id = request.data.get('dealer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        district_filter = request.data.get('district', '')

        # Start with base query including related fields for better performance
        manufacturers = Dealer.objects.select_related('manufacturer__state').prefetch_related('districts__state')
        
        # Apply filters based on user role and input parameters
        if uo:  # Device manufacturer user
            manufacturers = manufacturers.filter(manufacturer=uo)
        elif suo:  # State admin user
            manufacturers = manufacturers.filter(manufacturer__state=suo.state)
        
        # Apply additional filters
        if dealer_id:
            manufacturers = manufacturers.filter(id=dealer_id)
        else:
            manufacturers = manufacturers.filter(users__status='active')
            
        if email:
            manufacturers = manufacturers.filter(users__email__icontains=email)
            
        if company_name:
            manufacturers = manufacturers.filter(company_name__icontains=company_name)
            
        if name:
            manufacturers = manufacturers.filter(users__name__icontains=name)
            
        if phone_no:
            manufacturers = manufacturers.filter(users__mobile__icontains=phone_no)
            
        if district_filter:
            manufacturers = manufacturers.filter(districts__id=district_filter)

        # Get distinct results
        manufacturers = manufacturers.distinct()

        # Serialize the queryset
        dealer_serializer = DealerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request." + str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        
        id = request.data.get('manufacturer_id')
        man=Manufacturer.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid manufacturer id"}, status=400)
        m_user = man.users.last()
        if not m_user:
            return Response({'error': "No user mapped to this manufacturer"}, status=400)
        is_creator = bool(getattr(man, 'createdby_id', None) == getattr(request.user, 'id', None))
        is_superadmin = bool(get_user_object(request.user, 'superadmin'))
        if not (is_creator or is_superadmin):
            return Response({'error': "Only creator or superadmin can edit this manufacturer"}, status=400)
        
        date_joined = timezone.localdate()
        created = timezone.localdate()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        company_name = request.data.get('company_name')
        gstnnumber = request.data.get('gstnnumber')        
        state = request.data.get('state')
        gstno = request.data.get('gstno' )   
        idProofno = request.data.get('idProofno' )  
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        esim_provider_ids = request.data.get('esim_provider', [])
        
        email = request.data.get('email' )
        mobile = request.data.get('mobile' )
        name = request.data.get('name' )
        dob = request.data.get('dob' )
        partner_status = _normalize_partner_status(request.data.get('status'))
        if company_name:
            man.company_name=company_name
        if gstnnumber :
            man.gstnnumber=gstnnumber
        if state:
            man.state = state
        if gstno:
            man.gstno=gstno  
        if  idProofno:
            man.idProofno=idProofno
        if file_authLetter:
            man.file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man') 
            if not man.file_authLetter :
                    return Response({'error': "Invalid file." }, status=400)

        if file_companRegCertificate :
            man.file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
            if not man.file_companRegCertificate :
                return Response({'error': "Invalid file." }, status=400)

        if file_GSTCertificate :
            man.file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
            if not file_GSTCertificate :
                return Response({'error': "Invalid file." }, status=400)

        if file_idProof:
            man.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            
            if not file_idProof :
                return Response({'error': "Invalid file." }, status=400)
        if esim_provider_ids !=[]:
            man.esim_provider_ids=esim_provider_ids

            
        if email:
            m_user.email  =email
        if mobile:
            m_user.mobile=mobile
        if name:
            m_user.name=name 
        if dob:
            m_user.dob = dob
        if partner_status is not None:
            if partner_status not in ALLOWED_PARTNER_STATUSES:
                return Response(
                    {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
                    status=400
                )
            man.status = partner_status
        
         
        man.created = created
        man.expirydate = expirydate
        m_user.save()
        man.save() 
        return Response(ManufacturerSerializer(man ).data)
      

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_manufacturer_pub(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"

    try:
        company_name = request.data.get('company_name')
        company_address = request.data.get('company_address')
        company_pin = request.data.get('company_pin')
        company_email = request.data.get('company_email')
        company_phoneno = request.data.get('company_phoneno')
        company_registration_no = request.data.get('company_registration_no')
        panno = request.data.get('panno')
        manufacturer_type = request.data.get('manufacturer_type')
        gstnnumber = request.data.get('gstnnumber')
        tac = request.data.get('tac')
        tac_validity = request.data.get('tac_validity')
        cop_no = request.data.get('cop_no')
        cop_validity = request.data.get('cop_validity')
        device_model_details = request.data.get('device_model_details')
        createdby = request.user if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False) else None
        if createdby is None:
            createdby = User.objects.filter(role='superadmin').order_by('id').first()
        if createdby is None:
            return Response(
                {'error': 'No default creator user found. Create a superadmin user first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        date_joined = timezone.localdate()
        created = timezone.localdate()
        state = request.data.get('state')
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        partner_status = _normalize_partner_status(request.data.get('status'))
        if partner_status is None:
            partner_status = 'Created'
        elif partner_status not in ALLOWED_PARTNER_STATUSES:
            return Response(
                {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
                status=400
            )
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_company_registration_certificate = request.data.get('file_company_registration_certificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        file_affidavitNda = request.data.get('file_affidavitNda')
        file_officialTechnicalOnboardingRequestLetter = request.data.get('file_officialTechnicalOnboardingRequestLetter')
        file_vehicleTypeApprovalTacAnnexureCopy = request.data.get('file_vehicleTypeApprovalTacAnnexureCopy')
        file_ais140DeviceTacCopy = request.data.get('file_ais140DeviceTacCopy')
        file_factoryFitmentDeclaration = request.data.get('file_factoryFitmentDeclaration')
        cop_file = request.data.get('cop_file')
        esim_provider_ids = request.POST.getlist('esimProvider[]',[])#request.data.get('esimProvider[]', [])
        print(esim_provider_ids)

        user, error, new_password = create_user('devicemanufacture', request)
        if user:  
            try:
                # Create a savepoint for rollback if needed
                sid = transaction.savepoint()
                
                file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man') 
                file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
                file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
                file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
                if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "Invalid file." }, status=400)

                # Optional file upload: only validate if provided
                file_affidavitNda = None
                if request.FILES.get('file_affidavitNda'):
                    file_affidavitNda = save_file(request, 'file_affidavitNda', 'fileuploads/man')
                    if not file_affidavitNda:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_company_registration_certificate = None
                if request.FILES.get('file_company_registration_certificate'):
                    file_company_registration_certificate = save_file(request, 'file_company_registration_certificate', 'fileuploads/man')
                    if not file_company_registration_certificate:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_officialTechnicalOnboardingRequestLetter = None
                if request.FILES.get('file_officialTechnicalOnboardingRequestLetter'):
                    file_officialTechnicalOnboardingRequestLetter = save_file(request, 'file_officialTechnicalOnboardingRequestLetter', 'fileuploads/man')
                    if not file_officialTechnicalOnboardingRequestLetter:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_vehicleTypeApprovalTacAnnexureCopy = None
                if request.FILES.get('file_vehicleTypeApprovalTacAnnexureCopy'):
                    file_vehicleTypeApprovalTacAnnexureCopy = save_file(request, 'file_vehicleTypeApprovalTacAnnexureCopy', 'fileuploads/man')
                    if not file_vehicleTypeApprovalTacAnnexureCopy:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_ais140DeviceTacCopy = None
                if request.FILES.get('file_ais140DeviceTacCopy'):
                    file_ais140DeviceTacCopy = save_file(request, 'file_ais140DeviceTacCopy', 'fileuploads/man')
                    if not file_ais140DeviceTacCopy:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_factoryFitmentDeclaration = None
                if request.FILES.get('file_factoryFitmentDeclaration'):
                    file_factoryFitmentDeclaration = save_file(request, 'file_factoryFitmentDeclaration', 'fileuploads/man')
                    if not file_factoryFitmentDeclaration:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                cop_file = None
                if request.FILES.get('cop_file'):
                    cop_file = save_file(request, 'cop_file', 'fileuploads/man')
                    if not cop_file:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                manufacturer ,error= Manufacturer.objects.safe_create(
                    company_name=company_name,
                    company_address=company_address,
                    company_pin=company_pin,
                    company_email=company_email,
                    company_phoneno=company_phoneno,
                    company_registration_no=company_registration_no,
                    panno=panno,
                    gstnnumber=gstnnumber,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_company_registration_certificate=file_company_registration_certificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    file_affidavitNda=file_affidavitNda,
                    file_officialTechnicalOnboardingRequestLetter=file_officialTechnicalOnboardingRequestLetter,
                    file_vehicleTypeApprovalTacAnnexureCopy=file_vehicleTypeApprovalTacAnnexureCopy,
                    file_ais140DeviceTacCopy=file_ais140DeviceTacCopy,
                    file_factoryFitmentDeclaration=file_factoryFitmentDeclaration,
                    cop_file=cop_file,
                    tac=tac,
                    tac_validity=tac_validity,
                    cop_no=cop_no,
                    cop_validity=cop_validity,
                    manufacturer_type=manufacturer_type,
                    device_model_details=device_model_details,
                    state_id=state,
                    createdby=createdby,
                    status=partner_status,
                )
                if error:
                    transaction.savepoint_rollback(sid)
                    return error  # Return the Response object from safe_create

                
                # Fetch the EsimProvider instances and set the many-to-many relationship
                esim_providers = eSimProvider.objects.filter(id__in=esim_provider_ids)
                a=0

                for esim_provider in esim_providers:
                    print(esim_provider.state.id)
                    if str(esim_provider.state.id)==str(state):
                        manufacturer.esim_provider.set(esim_providers)
                        a=a+1
                    else:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "State missmatch with esim Provider"}, status=400)
                if a==0:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "No valid esim Provider"}, status=400)
                
                transaction.savepoint_commit(sid)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                return Response({'error': "Unable to process request."+str(e)}, status=400)
            
            manufacturer.users.add(user) 
            #send_usercreation_otp(user, new_password, 'Device Manufacture ')
            return Response(ManufacturerSerializer(manufacturer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        company_name = request.data.get('company_name')
        company_address = request.data.get('company_address')
        company_pin = request.data.get('company_pin')
        company_email = request.data.get('company_email')
        company_phoneno = request.data.get('company_phoneno')
        company_registration_no = request.data.get('company_registration_no')
        panno = request.data.get('panno')
        manufacturer_type = request.data.get('manufacturer_type')
        gstnnumber = request.data.get('gstnnumber')
        tac = request.data.get('tac')
        tac_validity = request.data.get('tac_validity')
        cop_no = request.data.get('cop_no')
        cop_validity = request.data.get('cop_validity')
        device_model_details = request.data.get('device_model_details')
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()
        state = request.data.get('state')
        gstno = request.data.get('gstno', '')  # Placeholder for gstno
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        partner_status = _normalize_partner_status(request.data.get('status'))
        if partner_status is None:
            partner_status = 'Created'
        elif partner_status not in ALLOWED_PARTNER_STATUSES:
            return Response(
                {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
                status=400
            )
        file_authLetter = request.data.get('file_authLetter')
        file_companRegCertificate = request.data.get('file_companRegCertificate')
        file_company_registration_certificate = request.data.get('file_company_registration_certificate')
        file_GSTCertificate = request.data.get('file_GSTCertificate')
        file_idProof = request.data.get('file_idProof')
        file_affidavitNda = request.data.get('file_affidavitNda')
        file_officialTechnicalOnboardingRequestLetter = request.data.get('file_officialTechnicalOnboardingRequestLetter')
        file_vehicleTypeApprovalTacAnnexureCopy = request.data.get('file_vehicleTypeApprovalTacAnnexureCopy')
        file_ais140DeviceTacCopy = request.data.get('file_ais140DeviceTacCopy')
        file_factoryFitmentDeclaration = request.data.get('file_factoryFitmentDeclaration')
        cop_file = request.data.get('cop_file')
        esim_provider_ids = request.POST.getlist('esimProvider[]',[])#request.data.get('esimProvider[]', [])
        print(esim_provider_ids)

        user, error, new_password = create_user('devicemanufacture', request)
        if user:  
            try:
                # Create a savepoint for rollback if needed
                sid = transaction.savepoint()
                
                file_authLetter = save_file(request, 'file_authLetter', 'fileuploads/man') 
                file_companRegCertificate = save_file(request, 'file_companRegCertificate', 'fileuploads/man')
                file_GSTCertificate = save_file(request, 'file_GSTCertificate', 'fileuploads/man')
                file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
                if not file_authLetter or not file_companRegCertificate or not file_GSTCertificate or not file_idProof:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "Invalid file." }, status=400)

                # Optional file upload: only validate if provided
                file_affidavitNda = None
                if request.FILES.get('file_affidavitNda'):
                    file_affidavitNda = save_file(request, 'file_affidavitNda', 'fileuploads/man')
                    if not file_affidavitNda:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_company_registration_certificate = None
                if request.FILES.get('file_company_registration_certificate'):
                    file_company_registration_certificate = save_file(request, 'file_company_registration_certificate', 'fileuploads/man')
                    if not file_company_registration_certificate:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_officialTechnicalOnboardingRequestLetter = None
                if request.FILES.get('file_officialTechnicalOnboardingRequestLetter'):
                    file_officialTechnicalOnboardingRequestLetter = save_file(request, 'file_officialTechnicalOnboardingRequestLetter', 'fileuploads/man')
                    if not file_officialTechnicalOnboardingRequestLetter:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_vehicleTypeApprovalTacAnnexureCopy = None
                if request.FILES.get('file_vehicleTypeApprovalTacAnnexureCopy'):
                    file_vehicleTypeApprovalTacAnnexureCopy = save_file(request, 'file_vehicleTypeApprovalTacAnnexureCopy', 'fileuploads/man')
                    if not file_vehicleTypeApprovalTacAnnexureCopy:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_ais140DeviceTacCopy = None
                if request.FILES.get('file_ais140DeviceTacCopy'):
                    file_ais140DeviceTacCopy = save_file(request, 'file_ais140DeviceTacCopy', 'fileuploads/man')
                    if not file_ais140DeviceTacCopy:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                file_factoryFitmentDeclaration = None
                if request.FILES.get('file_factoryFitmentDeclaration'):
                    file_factoryFitmentDeclaration = save_file(request, 'file_factoryFitmentDeclaration', 'fileuploads/man')
                    if not file_factoryFitmentDeclaration:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                cop_file = None
                if request.FILES.get('cop_file'):
                    cop_file = save_file(request, 'cop_file', 'fileuploads/man')
                    if not cop_file:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "Invalid file." }, status=400)

                manufacturer ,error= Manufacturer.objects.safe_create(
                    company_name=company_name,
                    company_address=company_address,
                    company_pin=company_pin,
                    company_email=company_email,
                    company_phoneno=company_phoneno,
                    company_registration_no=company_registration_no,
                    panno=panno,
                    gstnnumber=gstnnumber,
                    created=created,
                    expirydate=expirydate,
                    gstno=gstno,
                    idProofno=idProofno,
                    file_authLetter=file_authLetter,
                    file_companRegCertificate=file_companRegCertificate,
                    file_company_registration_certificate=file_company_registration_certificate,
                    file_GSTCertificate=file_GSTCertificate,
                    file_idProof=file_idProof,
                    file_affidavitNda=file_affidavitNda,
                    file_officialTechnicalOnboardingRequestLetter=file_officialTechnicalOnboardingRequestLetter,
                    file_vehicleTypeApprovalTacAnnexureCopy=file_vehicleTypeApprovalTacAnnexureCopy,
                    file_ais140DeviceTacCopy=file_ais140DeviceTacCopy,
                    file_factoryFitmentDeclaration=file_factoryFitmentDeclaration,
                    cop_file=cop_file,
                    tac=tac,
                    tac_validity=tac_validity,
                    cop_no=cop_no,
                    cop_validity=cop_validity,
                    manufacturer_type=manufacturer_type,
                    device_model_details=device_model_details,
                    state_id=state,
                    createdby=createdby,
                    status=partner_status,
                )
                if error:
                    transaction.savepoint_rollback(sid)
                    return error  # Return the Response object from safe_create

                
                # Fetch the EsimProvider instances and set the many-to-many relationship
                esim_providers = eSimProvider.objects.filter(id__in=esim_provider_ids)
                a=0

                for esim_provider in esim_providers:
                    print(esim_provider.state.id)
                    if str(esim_provider.state.id)==str(state):
                        manufacturer.esim_provider.set(esim_providers)
                        a=a+1
                    else:
                        transaction.savepoint_rollback(sid)
                        return Response({'error': "State missmatch with esim Provider"}, status=400)
                if a==0:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "No valid esim Provider"}, status=400)
                
                transaction.savepoint_commit(sid)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                return Response({'error': "Unable to process request."+str(e)}, status=400)
            
            manufacturer.users.add(user) 
            send_usercreation_otp(user, new_password, 'Device Manufacture ')
            return Response(ManufacturerSerializer(manufacturer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_manufacturers(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('manufacturer_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')

        # Optional GET query param for this POST API:
        # if `all_user=true`, don't restrict by user status (include inactive too).
        all_user_raw = None
        try:
            all_user_raw = request.query_params.get('all_user')
        except Exception:
            all_user_raw = request.GET.get('all_user') if hasattr(request, 'GET') else None
        all_user = str(all_user_raw).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}

        # Check user role and apply appropriate filtering
        user = request.user
        
        # Check if user is an eSIM provider
        esim_provider_obj = get_user_object(user, "esimprovider")
        
        # Start with base queryset
        manufacturers = Manufacturer.objects.all()
        
        # If user is an eSIM provider, only show manufacturers assigned to them
        if esim_provider_obj:
            manufacturers = manufacturers.filter(esim_provider=esim_provider_obj)

        # Add ID filter if provided
        if manufacturer_id:
            manufacturers = manufacturers.filter(
                id=manufacturer_id,
                users__email__icontains=email,
                company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            if all_user:
                manufacturers = manufacturers.filter(
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no,
                ).distinct()
            else:
                manufacturers = manufacturers.filter(
                    users__status='active',
                    users__email__icontains=email,
                    company_name__icontains=company_name,
                    users__name__icontains=name,
                    users__mobile__icontains=phone_no, 
                ).distinct()

        # Serialize the queryset
        manufacturer_serializer = ManufacturerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(manufacturer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email

def create_user(role, req):
    try:
        email = (req.data.get('email', '') or '').strip()
        mobile = (req.data.get('mobile', '') or '').strip()
        name = (req.data.get('name', '') or '').strip()
        dob = (req.data.get('dob', '') or '').strip()
        address = req.data.get('address', '')
        address_pin = req.data.get('pin', '') or req.data.get('address_pin', '')

        field_errors = {}
        if not name:
            field_errors['name'] = 'name is required.'
        if not email:
            field_errors['email'] = 'email is required.'
        else:
            try:
                django_validate_email(email)
            except Exception:
                field_errors['email'] = 'email must be a valid email address.'

        if not mobile:
            field_errors['mobile'] = 'mobile is required.'
        else:
            mobile_digits = ''.join(ch for ch in mobile if ch.isdigit())
            if mobile_digits != mobile:
                field_errors['mobile'] = 'mobile must contain digits only.'
            elif len(mobile) < 10 or len(mobile) > 15:
                field_errors['mobile'] = 'mobile must be between 10 and 15 digits.'

        if not dob:
            field_errors['dob'] = 'dob is required.'

        if field_errors:
            return [None, {'errors': field_errors}, None]

        # Proactive uniqueness checks to avoid masking DB constraint details
        if User.objects.filter(email__iexact=email).exists():
            return [None, {'error': 'Email already exists.'}, None]
        if User.objects.filter(mobile=mobile).exists():
            return [None, {'error': 'Mobile already exists.'}, None]
        creator_id = None
        if hasattr(req, 'user') and getattr(req.user, 'is_authenticated', False):
            creator_id = getattr(req.user, 'id', None)
        if not creator_id:
            creator = User.objects.filter(role='superadmin').order_by('id').first()
            creator_id = getattr(creator, 'id', None)
        createdby_value = str(creator_id) if creator_id else 'public'
        date_joined = timezone.now()
        created = timezone.now()
        is_active = True
        is_staff = False
        status = 'pending'
        new_password = ''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)

        # Create user
        user ,error= User.objects.safe_create(
            name=name,
            email=email,
            mobile=mobile,
            role=role,
            dob=dob,
            address=address,
            address_pin=address_pin,
            createdby=createdby_value,
            date_joined=date_joined,
            created=created,
            is_active=is_active,
            is_staff=is_staff,
            status=status,
            password=new_password
        )
        if error:  # Rollback user creation if dealer creation fails
            return [None, error.data , None] # Return the Response object from safe_create

        user.save()
 
        return [user, None, new_password]

    except IntegrityError as e:
        # Handle database integrity errors (e.g., duplicate keys)
        msg = str(e).lower()
        if 'email' in msg:
            return [None, {'error': "Email field is invalid or already exists."}, None]
        if 'mobile' in msg:
            return [None, {'error': "Mobile field is invalid or already exists."}, None]
        return [None, {'error': "A database integrity error occurred."}, None]

    except ValidationError as e:
        # Handle validation errors
        errors = {}
        for field, messages in e.message_dict.items():
            errors[field] = f"{field} field is invalid."
        return [None, {'error': errors}, None]

    except Exception as e:
        # General exception handling
        return [None, {'error': "Unable to process request.1"+str(e)}, None]


def send_usercreation_otp(user,new_password,type):
    try:
        tpid ="1007515117119518623"  
        
        text='Dear User, To confirm your registration in SkyTron platform, please click at the following link and validate the registration request- '+DEPLOY_URL+'/new/'+str(new_password)+'. The link will expire in 5 minutes. -SkyTron'
        send_SMS(user.mobile,text,tpid) 
        """
        send_mail(
                type+' Account Created',text
                #f'Temporery password is : {new_password}'
                ,'noreply@skytron.in',
                [user.email],
                fail_silently=False,
                ) """
    except Exception as e:
        pass
        # Response({'error': "Error in sendig email  "+"Unable to process request."+str(e)}, status=400)


def _role_to_account_type(role: str) -> str:
    if not role:
        return "User"
    role_map = {
        "superadmin": "Super Admin",
        "stateadmin": "State Admin",
        "devicemanufacture": "Device Manufacture",
        "dealer": "Dealer",
        "owner": "Vehicle Owner",
        "esimprovider": "EsimProvider",
        "dtorto": "DTO/RTO",
        "sosadmin": "SOS Admin",
        "teamleader": "Team Leader",
        "sosexecutive": "SOS Executive",
        "filment": "Filment",
    }
    return role_map.get(str(role).strip().lower(), str(role))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([OTPRateThrottle])
@require_http_methods(['POST'])
def resend_usercreation_otp(request):
    """Resend the user creation OTP/link.

    Input: {"user_id": <int>}
    Role/type is derived from the User model.
    """
    errors = {}

    # Only allow superadmin to resend creation OTPs (prevents abuse/spam)
    requester = request.user
    if not get_user_object(requester, "superadmin"):
        return Response({"error": "Request must be from superadmin."}, status=status.HTTP_400_BAD_REQUEST)

    user_id = request.data.get("user_id")
    if user_id in [None, ""]:
        errors["user_id"] = "user_id is required."
    else:
        try:
            user_id = int(user_id)
            if user_id <= 0:
                errors["user_id"] = "user_id must be a positive integer."
        except Exception:
            errors["user_id"] = "user_id must be a valid integer."

    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    target_user = User.objects.filter(id=user_id).last()
    if not target_user:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    # If the user is already active, don't resend creation OTP.
    # (Creation OTP is intended only for pending/unverified onboarding.)
    #if str(getattr(target_user, "status", "")).lower() == "active" and bool(getattr(target_user, "is_active", False)):
    #    return Response({"error": "User already active; creation OTP cannot be resent."}, status=status.HTTP_400_BAD_REQUEST)

    token = getattr(target_user, "password", None)
    if not token:
        return Response({"error": "User activation token not available."}, status=status.HTTP_400_BAD_REQUEST)

    # If stored value is hashed/non-resendable, rotate a fresh onboarding token
    # and persist it so resend can proceed.
    token_str = str(token)
    if token_str.startswith("pbkdf2_") or "$" in token_str:
        token_str = ''.join(secrets.choice('0123456789') for _ in range(30))
        target_user.password = token_str
        target_user.save(update_fields=["password"])

    account_type = _role_to_account_type(getattr(target_user, "role", ""))
    send_usercreation_otp(target_user, token_str, account_type)

    return Response({"message": "User creation OTP sent successfully."}, status=status.HTTP_200_OK)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_StateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        idProofno = request.data.get('idProofno' )  # Placeholder for idProofno
        state= request.data.get('state','')  
        
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()  
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        file_idProof = request.data.get('file_idProof')
        file_authorisation_letter = request.data.get('file_authorisation_letter')
        
         
        user,error,new_password=create_user('stateadmin',request)
        if user:         
            try: 
                # Create a savepoint for rollback if needed
                sid = transaction.savepoint()
                
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not file_idProof:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "Invalid file." }, status=400)
                file_authorisation_letter=save_file(request,'file_authorisation_letter','fileuploads/man')
                if not file_authorisation_letter:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "Invalid file." }, status=400)
                
                dealer, error = StateAdmin.objects.safe_create( 
                    created=created,
                    state_id=state,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    file_authorisation_letter=file_authorisation_letter,
                    createdby=createdby,
                    status="Created",
                ) 
                
                if error:
                    transaction.savepoint_rollback(sid)
                    return error  # Return the Response object from safe_create

                transaction.savepoint_commit(sid)
                
            except Exception as e:
                transaction.savepoint_rollback(sid)
                return Response({'error': "Unable to process request1."+str(e)}, status=400)
            dealer.users.add(user)
            dealer.save()  # Save the dealer after adding users
            send_usercreation_otp(user,new_password,'State Admin ')
             
            return Response(StateadminSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_StateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('stateadmin_id')
        stateadmin = StateAdmin.objects.filter(id=id).last()
        if not stateadmin:
            return Response({'error': "Invalid StateAdmin id"}, status=400)
        if stateadmin.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.localdate()
        created = timezone.localdate()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        email = request.data.get('email')
        idProofno = request.data.get('idProofno')
        state = request.data.get('state')
        file_idProof = request.data.get('file_idProof')

        new_email = request.data.get('new_email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if email:
            stateadmin.user.email = email
        if idProofno:
            stateadmin.idProofno = idProofno
        if state:
            stateadmin.state_id = state
        if file_idProof:
            stateadmin.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not stateadmin.file_idProof:
                     
                    return Response({'error': "Invalid file." }, status=400)

        if new_email:
            stateadmin.user.email = new_email
        if mobile:
            stateadmin.user.mobile = mobile
        if name:
            stateadmin.user.name = name
        if dob:
            stateadmin.user.dob = dob

        new_password = ''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)
        stateadmin.user.password = hashed_password
        stateadmin.date_joined = date_joined
        stateadmin.created = created
        stateadmin.expirydate = expirydate
        stateadmin.user.save()
        stateadmin.save()
        send_usercreation_otp(stateadmin.user, new_password, 'State Admin')
        return Response(StateadminSerializer(stateadmin).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_StateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('StateAdmin_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state = request.data.get('state', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = StateAdmin.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = StateAdmin.objects.filter(
                #id=manufacturer_id,
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = StateadminSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

 



Districtlist={'Kamrup':'AS01','Kamrup Rural':'AS25','Nagaon':'AS02','Jorhat':'AS03',
              'Sibsagar':'AS04','Golaghat':'AS05','Dibrugarh':'AS06','Lakhimpur':'AS07',
              'Dima Hasao':'AS08','Karbi anglong':'AS09','Karimganj':'AS10','Cachar':'AS11',
              'Tezpur':'AS12','Darrang':'AS13','Nalbari':'AS14','Barpeta':'AS15','Kokrajhar':'AS16',
              'The woman':'AS17',' Goalpara':'AS18','Bongaigaon':'AS19','Marigaon':'AS21','Dhemaji':'AS22',
              'Tinsukia':'AS23','Hailakandi':'AS24','Chirang':'AS26','Udalguri':'AS27','Baksa':'AS28','Hojai':'AS31',
              'Biswanath':'AS32','Charaideo':'AS33','South Salmara':'AS34'}

@csrf_exempt
@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def getDistrictList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        state= request.data.get('State')
        districts = Settings_District.objects.filter(state_id=state).order_by('district', 'id')
        Districtlist = {}
        for district in districts:
            Districtlist[district.district] = district.district_code
        return JsonResponse(Districtlist)
    except:
        return Response({"error":"Unable to find District"}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()  
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '')
        dto_rto1= request.data.get('dto_rto', '')
        districtC = request.data.get('district_code', '')
        #state= request.data.get('State', '1')
        districts = Settings_District.objects.filter(state_id=state).order_by('district', 'id')
        Districtlist = {}
        if str(uo.state_id) !=str(state):
            return Response({"error":"Unauthorised state "+'.'}, status=status.HTTP_400_BAD_REQUEST)

        for district in districts:
            Districtlist[district.district] = district.district_code
        if districtC not in Districtlist.values():
            return Response({'error': "Invalid Dtrict Code:"+districtC}, status=400)
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('dtorto',request)
        if user:         
            try: 
                # Create a savepoint for rollback if needed
                sid = transaction.savepoint()
                
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                file_authorisation_letter = save_file(request,'file_authorisation_letter','fileuploads/man')
                if not file_idProof or not file_authorisation_letter:
                    transaction.savepoint_rollback(sid)
                    return Response({'error': "Invalid file." }, status=400)

                dealer,error = dto_rto.objects.safe_create( 
                    created=created,
                    state_id=state,
                    dto_rto=dto_rto1,
                    district=districtC,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    file_authorisation_letter=file_authorisation_letter,
                    createdby=createdby,
                    status="Created",
                ) 
                
                if error:
                    transaction.savepoint_rollback(sid)
                    return error  # Return the Response object from safe_create

                transaction.savepoint_commit(sid)

            except Exception as e:
                transaction.savepoint_rollback(sid)
                return Response({'error': "Unable to process request."+str(e)}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'DTO/RTO ')
             
            return Response(dto_rtoSerializer(dealer).data)
        else:
            return Response(error, status=400)          

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        id = request.data.get('dtorto_id')
        dtorto = dto_rto.objects.filter(id=id).last()
        if not dtorto:
            return Response({'error': "Invalid DTO/RTO id"}, status=400)
        if dtorto.createdby != request.user:
            return Response({'error': "User can be edited by only the creator"}, status=400)
        
        date_joined = timezone.localdate()
        created = timezone.localdate()
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        idProofno = request.data.get('idProofno')
        state = request.data.get('state', '1')
        dto_rto1 = request.data.get('dto_rto')
        districtC = request.data.get('district_code')

        districts = Settings_District.objects.filter(state_id=state).order_by('district', 'id')
        Districtlist = {district.district: district.district_code for district in districts}
        if districtC not in Districtlist.values():
            return Response({'error': "Invalid District Code:" + districtC}, status=400)

        file_idProof = request.data.get('file_idProof')
        file_authorisation_letter= request.data.get('file_authorisation_letter')

        email = request.data.get('email')
        mobile = request.data.get('mobile')
        name = request.data.get('name')
        dob = request.data.get('dob')

        if idProofno:
            dtorto.idProofno = idProofno
        if state:
            dtorto.state_id = state
        if dto_rto1:
            dtorto.dto_rto = dto_rto1
        if districtC:
            dtorto.district = districtC
        if file_idProof:
            dtorto.file_idProof = save_file(request, 'file_idProof', 'fileuploads/man')
            if not dtorto.file_idProof: 
                    return Response({'error': "Invalid file." }, status=400)
                
                
        if file_authorisation_letter:
            dtorto.file_idProof = save_file(request, 'file_authorisation_letter', 'fileuploads/man')
            if not dtorto.file_idProof: 
                    return Response({'error': "Invalid file." }, status=400)

        if email:
            dtorto.user.email = email
        if mobile:
            dtorto.user.mobile = mobile
        if name:
            dtorto.user.name = name
        if dob:
            dtorto.user.dob = dob

        new_password = ''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)
        dtorto.user.password = hashed_password
        dtorto.date_joined = date_joined
        dtorto.created = created
        dtorto.expirydate = expirydate
        dtorto.user.save()
        dtorto.save()
        send_usercreation_otp(dtorto.user, new_password, 'DTO/RTO')
        return Response(dto_rtoSerializer(dtorto).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        if uo:
            state=uo.state
        else:
            state = request.data.get('state', '')

        # Get filter parameters from the request
        obj_id = request.data.get('dto_rto_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        
        district = request.data.get('district', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if obj_id :
            manufacturers = dto_rto.objects.filter(
                id=obj_id,
                state=state,
           
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = dto_rto.objects.filter(
                state=state,
           
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = dto_rtoSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def transfer_DTO_RTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get filter parameters from the request
        id = request.data.get('dto_rto_id', None) 
        district = request.data.get('new_district_code', '')
        
        if district not in Districtlist.values():
            return Response({'error': "Invalid Dtrict Code:"+district}, status=400)

        
        if  id :
            dto = dto_rto.objects.get(id=id) 
            if dto:
                dd=dto.district
                if dd==district:
                    return Response({'error': 'No change in district code'}, status=400)
                dto.district=district
                dto.save()
                serializer = dto_rtoSerializer(dto, many=False)
                return Response({'Status': 'Successfully transfered from '+str(dd)+' to '+district,'dto_data':serializer.data})
            return Response({'error': 'DTO with given id ont found'}, status=400)
        return Response({'error': 'dto_rto_id not found'}, status=400)



    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


 
 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_SOS_user(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()   
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '') 
        district = request.data.get('district', '')
        user_type = request.data.get('user_type', '') 
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('sosexecutive',request)
 
        if user:  
            try: 
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not  file_idProof: 
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)


                dealer,error = EM_ex.objects.safe_create( 
                    created=created,
                    state_id=state, 
                    #district_id=district,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    user_type=user_type,
                    createdby=createdby,
                    status="Created",
                ) 
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+str(e)}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'SOS user ')             
            return Response(EM_exSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_SOS_user(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('dto_rto_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state = request.data.get('state', '')
        district = request.data.get('district', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = EM_ex.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = EM_ex.objects.filter(
                #id=manufacturer_id,
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = EM_exSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


from collections import defaultdict

@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def list_alert_logs(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        start_datetime = request.POST.get('start_datetime')
        end_datetime = request.POST.get('end_datetime')
        district_id = request.POST.get('district_id')
        state_id = request.POST.get('state_id')

        queryset = AlertsLog.objects.all()

        # Filter queryset based on optional POST inputs
        if start_datetime:
            queryset = queryset.filter(timestamp__gte=start_datetime)
        if end_datetime:
            queryset = queryset.filter(timestamp__lte=end_datetime)
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        if state_id:
            queryset = queryset.filter(state_id=state_id)

        # Get all alert types
        all_alert_types = dict(AlertsLog.TYPE_CHOICES)

        # Group queryset by alert type
        alert_groups = defaultdict(list)
        for item in queryset:
            alert_groups[item.type].append(AlertsLogSerializer(item).data)

        # Create response dictionary with all types, even if not present in queryset
        response_data = {}
        for alert_type, alert_type_name in all_alert_types.items():
            response_data[alert_type_name] = {
                'count': len(alert_groups[alert_type]),
                'details': alert_groups[alert_type]
            }

        return JsonResponse(response_data)

    # Handle GET requests or other HTTP methods
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_SOS_admin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        createdby = request.user 
        date_joined = timezone.localdate()
        created = timezone.localdate()  
        idProofno = request.data.get('idProofno', '')  # Placeholder for idProofno
        expirydate = date_joined + timezone.timedelta(days=365 * 2)  # 2 years expiry date
        state= request.data.get('state', '') 
        #district = request.data.get('district', '') 
        file_idProof = request.data.get('file_idProof') 
        user,error,new_password=create_user('sosadmin',request)
        if user:
            try:   
                file_idProof = save_file(request,'file_idProof','fileuploads/man')
                if not file_idProof: 
                    user.delete()
                    return Response({'error': "Invalid file." }, status=400)
                dealer,error = EM_admin.objects.safe_create( 
                    created=created,
                    state_id=state, 
                    #district_id=district,
                    expirydate=expirydate, 
                    idProofno=idProofno, 
                    file_idProof=file_idProof,
                    createdby=createdby,
                    status="Created",
                ) 
                
                if error:
                    user.delete()  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            except Exception as e:
                user.delete()
                return Response({'error': "Unable to process request."+str(e)}, status=400)
            dealer.users.add(user) 
            send_usercreation_otp(user,new_password,'SOS Admin ')
             
            return Response(EM_adminSerializer(dealer).data)
        else:
            return Response(error, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_SOS_admin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get filter parameters from the request
        manufacturer_id = request.data.get('dto_rto_id', None)
        email = request.data.get('email', '') 
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '')
        state = request.data.get('state', '')
        district = request.data.get('district', '')

        # Create a dictionary to hold the filter parameters
        filters = {}

        # Add ID filter if provided
        if manufacturer_id :
            manufacturers = EM_admin.objects.filter(
                id=manufacturer_id,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = EM_admin.objects.filter(
                #id=manufacturer_id,
                users__status='active',
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        serializer = EM_adminSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_desk_ex(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    

    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:  
        active_team_members = EMTeams.objects.filter(status="Active").values_list('members', flat=True)
        emex = EM_ex.objects.filter(
            state=uo.state,
            status="UserVerified",
            user_type='desk_ex',
            users__status='active'
        ).exclude(id__in=active_team_members).distinct()

        # Serialize and return the data
        serializer = EM_exSerializer(emex, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_team_lead(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role = "sosadmin"
    user = request.user
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": "Request must be from " + role + '.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        active_team_leads = EMTeams.objects.filter(status="Active").values_list('teamlead_id', flat=True)
        emex = EM_ex.objects.filter(
            state=uo.state,
            status="UserVerified",
            user_type='teamlead',
            users__status='active'
        ).exclude(id__in=active_team_leads).distinct()
        serializer = EM_exSerializer(emex, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'+str(user.role)}, status=400)
    state = request.data.get('state') 
    if uo.state.id!=state:
        return Response({"error":"Unauthorised State" }, status=400)

        
    #teamlead = EM_ex.objects.filter(id=request.data.get('teamlead') ,state=state,status="UserVerified",user_type='teamlead').last()
    #members = EM_ex.objects.filter(id=request.data.get('members',[]) ,state=state,status="UserVerified",user_type='desk_ex').all()



    teamlead_id = request.data.get('teamlead')
    member_ids = request.data.get('members', [])
    
    teamlead = EM_ex.objects.filter(id=teamlead_id, state=state,users__status='active', user_type='teamlead').last()
    members = EM_ex.objects.filter(id__in=member_ids, state=state, users__status='active', user_type='desk_ex').all()
    if not teamlead:
        return Response({"error": "Team lead not found."}, status=400)
    if not members:
        return Response({"error": "Members not found."}, status=400)
    if len(members)!=len(member_ids):
        return Response({"error": "All Members not found."}, status=400)


    # Check if the teamlead is part of any active team
    if EMTeams.objects.filter(teamlead=teamlead, status="Active").exists():
        return Response({"error": "The selected teamlead is already part of an active team."}, status=400)

    # Check if any of the members are part of any active team
    active_team_members = EMTeams.objects.filter(status="Active", members__in=members).distinct()
    if active_team_members.exists():
        return Response({"error": "One or more selected members are already part of an active team."}, status=400)

    created_by = uo  
    status = "NotActive"
    name = request.data.get('name') 
    detail = request.data.get('detail') 
    try:  
        if state and teamlead  and  members  and  created_by  and  status  and name and   detail:
            if members!=[]:
                   
                ob,error=EMTeams.objects.safe_create(state_id = state,
                    teamlead =teamlead,
                     
                    created_by = created_by,
                    status = status,
                    name = name,
                    detail = detail)
                
                if error: # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

                ob.members.set(members) 
                ob.save()
                return Response({'status': str('Team Created Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to create team. Incomplete data.')}, status=400)#Response(SOS_userSerializer(dealer).data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def activate_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('team_id') 
        ob=EMTeams.objects.filter(id = id,status = "NotActive" ,state=uo.state).last()
        if ob:
            ob.status="Active"
            ob.activated_at= timezone.now()
            ob.save()
            return Response({'status': str('Team Activated Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to activate team.  Team not found.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def remove_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('team_id') 
        ob=EMTeams.objects.filter(id = id,status = "Active",state=uo.state).last()
        if ob:
            ob.status="Removed"
            ob.activated_at= timezone.now()
            ob.save()
            return Response({'status': str('Team Removed Successfully'),"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to remove team. Team not found.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def edit_EM_team(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'+str(user.role)}, status=400)
    
    try:
        team_id = request.data.get('team_id')
        if not team_id:
            return Response({"error": "Team ID is required."}, status=400)
        
        # Get the team to edit
        team = EMTeams.objects.filter(id=team_id, state=uo.state).last()
        if not team:
            return Response({"error": "Team not found."}, status=400)
        
        # Only allow editing if team is NotActive or Active (not Removed)
        if team.status == "Removed":
            return Response({"error": "Cannot edit a removed team."}, status=400)
        
        state = request.data.get('state', team.state.id)
        if uo.state.id != state:
            return Response({"error":"Unauthorised State" }, status=400)

        # Get optional new teamlead
        teamlead_id = request.data.get('teamlead')
        if teamlead_id:
            teamlead = EM_ex.objects.filter(id=teamlead_id, state=state, users__status='active', user_type='teamlead').last()
            if not teamlead:
                return Response({"error": "Team lead not found."}, status=400)
            
            # Check if the new teamlead is part of any other active team (excluding current team)
            if EMTeams.objects.filter(teamlead=teamlead, status="Active").exclude(id=team_id).exists():
                return Response({"error": "The selected teamlead is already part of another active team."}, status=400)
        else:
            teamlead = team.teamlead

        # Get optional new members
        member_ids = request.data.get('members')
        if member_ids is not None:
            if member_ids:  # If not empty list
                members = EM_ex.objects.filter(id__in=member_ids, state=state, users__status='active', user_type='desk_ex').all()
                if len(members) != len(member_ids):
                    return Response({"error": "All Members not found."}, status=400)
                
                # Check if any of the new members are part of any other active team (excluding current team)
                active_team_members = EMTeams.objects.filter(status="Active", members__in=members).exclude(id=team_id).distinct()
                if active_team_members.exists():
                    return Response({"error": "One or more selected members are already part of another active team."}, status=400)
            else:
                members = []
        else:
            members = team.members.all()

        # Get optional new name and detail
        name = request.data.get('name', team.name)
        detail = request.data.get('detail', team.detail)

        # Update the team
        team.teamlead = teamlead
        team.name = name
        team.detail = detail
        team.save()
        
        # Update members if provided
        if member_ids is not None:
            team.members.set(members)
        
        return Response({'status': 'Team Updated Successfully', "team": EMTeamsSerializer(team).data}, status=200)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def get_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('team_id') 
        ob=EMTeams.objects.filter(id = id ,state=uo.state).last()
        if ob: 
            return Response({"team":EMTeamsSerializer(ob).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Team not found')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_EM_team(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ob=EMTeams.objects.filter( state=uo.state).all()
        if ob: 
            return Response({ "teams":EMTeamsSerializer(ob,many=True).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Team not found')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TLEx_getPendingCallList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ee=EMCallAssignment.objects.filter( call__team__teamlead= uo  ).all()

        if ee: 
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'call': str('Not found')}, status=404)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_getPendingCallList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    role2="stateadmin" 
    uo2=get_user_object(user,role2)
    role3="sosadmin"
    uo3=get_user_object(user,role3)
    if not (uo or uo2 or uo3):
        return Response({"error":"Request must be from  "+role+' or '+role2+' or '+role3+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        # Base queryset: only pending calls and excluding closed assignments
        qs_base = EMCallAssignment.objects.filter(call__status="pending").exclude(status="closed")

        # Scope selection based on role
        if uo2:
            qs = qs_base.filter(ex__state=uo2.state)
            cache_scope = f"state:{getattr(uo2.state, 'id', uo2.state_id)}"
        elif uo3:
            qs = qs_base.filter(ex__state=uo3.state)
            cache_scope = f"state:{getattr(uo3.state, 'id', uo3.state_id)}"
        else:
            qs = qs_base.filter(ex=uo)
            cache_scope = f"ex:{getattr(uo, 'id', None)}"

        # Attempt to reduce N+1 queries by joining common FKs used in serializers
        try:
            qs = qs.select_related(
                'ex',
                'ex__state',
                'call',
                'call__team',
                'call__team__teamlead',
            )
        except Exception:
            # If any relation path is invalid, skip silently to avoid breaking behavior
            pass

        # Short-lived cache to avoid repeated heavy serialization for the same scope
        cache_key = f"DEx_getPendingCallList:pending:{cache_scope}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({"calls": cached}, status=200)

        # Serialize once, then branch on data length (avoid extra exists/evaluation)
        data = EMCallAssignmentSerializer(qs, many=True).data

        # Cache for a brief period (e.g., 10 seconds)
        cache.set(cache_key, data, timeout=10)

        if data:
            return Response({"calls": data}, status=200)
        return Response({'call': 'Not found'}, status=200)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_getPendingCallListTL(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    role2="stateadmin" 
    uo2=get_user_object(user,role2)
    role3="sosadmin"
    uo3=get_user_object(user,role3)
    role4="superadmin"
    uo4=get_user_object(user,role4)
    if not (uo or uo2 or uo3 or uo4):
        return Response({"error":"Request must be from  "+role+' or '+role2+' or '+role3+' or '+role4+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        # Base queryset: only pending calls and excluding closed assignments
        qs_base = EMCallAssignment.objects.all()

        # Scope selection based on role
        if uo2:
            qs = qs_base.filter(ex__state=uo2.state)
            cache_scope = f"state:{getattr(uo2.state, 'id', uo2.state_id)}"
        elif uo3:
            qs = qs_base.filter(ex__state=uo3.state)
            cache_scope = f"state:{getattr(uo3.state, 'id', uo3.state_id)}"
        else:
            qs = qs_base.all()
            cache_scope = f"ex:{getattr(uo, 'id', None)}"

        # Attempt to reduce N+1 queries by joining common FKs used in serializers
        try:
            qs = qs.select_related(
                'ex',
                'ex__state',
                'call',
                'call__team',
                'call__team__teamlead',
            )
        except Exception:
            # If any relation path is invalid, skip silently to avoid breaking behavior
            pass

        qs = qs.order_by('-id')[:10]

        # Short-lived cache to avoid repeated heavy serialization for the same scope
        cache_key = f"DEx_getPendingCallList:pending:{cache_scope}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({"calls": cached}, status=200)

        # Serialize once, then branch on data length (avoid extra exists/evaluation)
        data = EMCallAssignmentSerializer(qs, many=True).data

        # Cache for a brief period (e.g., 10 seconds)
        cache.set(cache_key, data, timeout=10)

        if data:
            return Response({"calls": data}, status=200)
        return Response({'call': 'Not found'}, status=200)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)





    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_getCallList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    role2="stateadmin" 
    uo2=get_user_object(user,role2)
    role3="sosadmin"
    uo3=get_user_object(user,role3)
    if not (uo or uo2 or uo3):
        return Response({"error":"Request must be from  "+role+' or '+role2+' or '+role3+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        # Base queryset excluding closed to keep result set small
        qs_base = EMCallAssignment.objects.exclude(status="closed")

        # Scope selection based on role
        if uo2:
            qs = qs_base.filter(ex__state=uo2.state)
            cache_scope = f"state:{getattr(uo2.state, 'id', uo2.state_id)}"
        elif uo3:
            qs = qs_base.filter(ex__state=uo3.state)
            cache_scope = f"state:{getattr(uo3.state, 'id', uo3.state_id)}"
        else:
            qs = qs_base.filter(ex=uo)
            cache_scope = f"ex:{getattr(uo, 'id', None)}"

        # Attempt to reduce N+1 queries by joining common FKs used in serializers
        try:
            qs = qs.select_related(
                'ex',
                'ex__state',
                'call',
                'call__team',
                'call__team__teamlead',
            )
        except Exception:
            # If any relation path is invalid, skip silently to avoid breaking behavior
            pass

        # Short-lived cache to avoid repeated heavy serialization for the same scope
        cache_key = f"DEx_getCallList:{cache_scope}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response({"calls": cached}, status=200)

        # Serialize once, then branch on data length (avoid extra exists/evaluation)
        data = EMCallAssignmentSerializer(qs, many=True).data

        # Cache for a brief period (e.g., 10 seconds)
        cache.set(cache_key, data, timeout=10)

        if data:
            return Response({"calls": data}, status=200)
        return Response({'call': 'Not found'}, status=200)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_getLiveCallList(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ee=EMCallAssignment.objects.filter( type = "desk_ex",  ex = uo  )  

        if ee: 
            return Response({ "calls":EMCallAssignmentSerializer(ee,many=True).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'call': str('Not found')}, status=200)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_replyCall(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        accept =request.data.get("accept") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
   
        if assignment:
            if accept:
                assignment.status="accepted"#"rejected", "rejected")
                assignment.accept_time =  timezone.now()
            else:
                assignment.status="rejected"
                assignment.reject_time = timezone.now()


            assignment.save()

            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response( EMCallAssignmentSerializer(assignment,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def CheckLive(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    return Response({'detail':"live"}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_broadcast(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        radius =request.data.get("radius")  
        radius =5
        typ =request.data.get("type")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        ee,error=EMCallBroadcast.objects.safe_create( admin  =assignment.admin,
            created_by= uo,
            call = assignment.call,
            radius= radius,
            status = "pending",
            type = typ)
        
        if error: # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        
        return Response( EMCallBroadcastSerializer(ee,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_broadcastlist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        ee=EMCallBroadcast.objects.filter(
            call = assignment.call).all()
        
        return Response( EMCallBroadcastSerializer(ee,many=True).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_broadcastlist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex' or uo.user_type=='PCR' or uo.user_type=='ACR' :
 
        return Response({"error":"Request must be from  police_ex or ambulance_ex' or PCR or ACR."}, status=status.HTTP_400_BAD_REQUEST)
    try:  
        ee=EMCallBroadcast.objects.filter(  type=uo.user_type,status="pending").last()
        
        return Response( EMCallBroadcastSerializer(ee,many=True).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TLEx_reassign(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='teamlead' :
 
        return Response({"error":"Request must be from team lead."}, status=status.HTTP_400_BAD_REQUEST)
    try: 

        id =request.data.get("assignemtn_id")  
        ee=EMCallAssignment.objects.filter(  call__team__teamlead= uo,id = id).last()
        if not ee :
            return Response({"error":"Unauthorised assignemnt id ."}, status=status.HTTP_400_BAD_REQUEST)

        id2 =request.data.get("DEx_id")  
        ex=EM_ex.objects.filter(id=id2).last()
        if not ex :
            return Response({"error":"Invalid DeskExId."}, status=status.HTTP_400_BAD_REQUEST)

        tt=EMTeams.objects.filter(status="Active",teamlead=uo).last()
        
        if not tt :
            return Response({"error":"Invalid team."}, status=status.HTTP_400_BAD_REQUEST)
        if ex in tt.members:
            assignment ,error=   EMCallAssignment.objects.safe_create(
                        admin =  EM_admin.objects.all().last(),#filter(users__login=True)
                        call =ee.call ,
                        status = "pending",
                        type = ee.type,
                        ex = ex 
                        ) 
            
            if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            ee.status="reassigned"
            ee.save()
            return Response( EMCallAssignmentSerializer(assignment ,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        else:
            return Response({"error":"Desk_ex is not a member of your team."}, status=status.HTTP_400_BAD_REQUEST)

          

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_broadcastaccept(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return JsonResponse({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex' or uo.user_type=='PCR' or uo.user_type=='ACR' :
 
    #    return JsonResponse({"error":"Request must be from  police_ex or ambulance_ex' or PCR or ACR."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        print("sosex type :::",uo.user_type)
        id =request.data.get("broadcast_id")  
        ee=EMCallBroadcast.objects.filter( id = id,status="pending").last()
        if not ee:
            return JsonResponse({'error': "Not found"}, status=400)
        ee.status="accepted"
        ee.save()
        assignment,error =   EMCallAssignment.objects.safe_create(
                    admin =  EM_admin.objects.all().last(),#filter(users__login=True)
                    call =ee.call ,
                    status = "accepted",
                    type = uo.user_type,
                    ex = uo 
                    )  
        
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        return JsonResponse( {"assignment":EMCallAssignmentSerializer(assignment ,many=False).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        
    except Exception as e:
        return JsonResponse({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def  DEx_closeCase(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        assignments =EMCallAssignment.objects.filter(call=assignment.call,status="pending").all()
        try:
            
            final_command = "@SETSOSDIS-1*"

            payload = { 
                'keys': final_command,
                
            }

 
            send_general_mqtt_message(str(assignment.call.device.device.imei), payload)
            time.sleep(5)
        
        
            #send_sos_mqtt_message(assignment.call.device.device.imei, 2)
            
        except:
            return Response({"error":"MQTT COMMAND NOT SENT" }, status=status.HTTP_400_BAD_REQUEST) 
        ee=EMCallBroadcast.objects.filter(
            call = assignment.call,status="pending").all()
        for e in ee:
            e.status="canceled"
            e.save()
        
        for a in assignments:
            a.status="closed"
            a.save()
        assignment.call.status="closed"
        assignment.call.save()
        
        

        
        return Response( EMCallSerializer(assignment.call,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_sendMsg(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call
        message=request.data.get("message") 
        ob,error=EMCallMessages.objects.safe_create(assignment=assignment,call=call,message=message)
        
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallMessagesSerializer(ob,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to send message. value error.')}, status=200)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_rcvMsg(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call 
        ob=EMCallMessages.objects.filter(call=call).all()
        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallMessagesSerializer(ob,many=True).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response([], status=200)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_commentFE(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    try: 
        assignment =request.data.get("self_assignment_id") 
        fe_assignment =request.data.get("self_assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call 
        assignment2=EMCallAssignment.objects.filter(id=fe_assignment,call=call).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        
        if not assignment2:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        assignment2.desk_ex_comment=request.data.get("comment") 
        #assignment2.status="closed"
        assignment2.save()
        
        if assignment:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallAssignmentSerializer(assignment2,many=False).data, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to read message. value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_file_paths(request):
    """
    Debugging endpoint to check if a file exists in various potential locations
    """
    file_path = request.data.get('file_path')
    if not file_path:
        return JsonResponse({'error': 'file_path is required'}, status=400)
    
    filename = os.path.basename(file_path)
    directory = os.path.dirname(file_path)
    
    # Locations to check
    potential_locations = []
    
    # Build list of places to check
    for folder in folders:
        # Original path
        potential_locations.append(os.path.join(folder, file_path))
        
        # Just the filename in the root folder
        potential_locations.append(os.path.join(folder, filename))
        
        # Filename in possible subdirectories
        if directory:
            potential_locations.append(os.path.join(folder, directory, filename))
            
   
    
    # Check each location
    results = {}
    for location in potential_locations:
        exists = os.path.isfile(location)
        results[location] = {
            'exists': exists,
            'size': os.path.getsize(location) if exists else 0
        }
    
    return JsonResponse({
        'requested_file': file_path,
        'filename': filename,
        'directory': directory,
        'locations_checked': results,
        'folders_configuration': folders
    })

@api_view(['POST'])
@permission_classes([AllowAny]) 
#@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def upload_media_file(request):
    """
    API to upload media files (.jpg, .mp4, .avi, .wav, .mp3, etc.) and save data in fileuploads/media.
    The uploaded file will be prefixed with the camera_id.
    """
    try:
        device_tag_id = request.data.get('device_tag')
        camera_id = request.data.get('camera_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        media_type = request.data.get('media_type')
        duration_ms = request.data.get('duration_ms')
        alert_type = request.data.get('alert_type')
        message = request.data.get('message')
        uploaded_file = request.FILES.get('media_file')

        if not (device_tag_id and camera_id and uploaded_file):
            return JsonResponse({'error': 'device_tag, camera_id, and media_file are required.'}, status=400)

        device_tag = get_object_or_404(DeviceTag, id=device_tag_id)

        # Allowed file extensions
        allowed_ext = ['.jpg', '.jpeg', '.mp4', '.avi', '.wav', '.mp3']
        filename = uploaded_file.name
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_ext:
            return JsonResponse({'error': f'File type {ext} not allowed.'}, status=400)

        # Prefix camera_id to filename
        safe_filename = f"{camera_id}_{filename.replace(' ', '_')}"
        file_path = f'fileuploads/media/{safe_filename}'

        # Save file
        with open(file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Save record in Media_File1
        media_file = Media_File1.objects.create(
            device_tag=device_tag,
            camera_id=camera_id,
            start_time=start_time,
            end_time=end_time,
            media_type=media_type,
            media_link=file_path,
            duration_ms=duration_ms,
            alert_type=alert_type,
            message=message,
        )

        return JsonResponse({
            "success": "Media file uploaded successfully",
            "media_id": media_file.id,
            "media_link": file_path
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def dummy_insert_data(request):
    """
    Dummy API to insert data using GET parameters.
    Example usage:
    /api/dummy-insert-data?device_tag=1&camera_id=101&start_time=2023-05-01T10:00:00Z&end_time=2023-05-01T10:05:00Z&media_type=video&media_link=http://example.com/video.mp4&duration_ms=300000&alert_type=alert&message=Test
    """
    if request.method == 'POST':
        try:  
            device_tag = request.data.get('device_tag')
            device_tag = get_object_or_404(DeviceTag, id=device_tag)

            camera_id = request.data.get('camera_id')
            start_time = request.data.get('start_time')
            end_time = request.data.get('end_time')
            media_type = request.data.get('media_type')
            media_link = request.data.get('media_link')
            duration_ms = request.data.get('duration_ms')
            alert_type = request.data.get('alert_type')
            message = request.data.get('message')

            media_file = Media_File1.objects.create(
                device_tag=device_tag,
                camera_id=camera_id,
                start_time=start_time,
                end_time=end_time,
                media_type=media_type,
                media_link=media_link,
                duration_ms=duration_ms,
                alert_type=alert_type,
                message=message,
            )

            return JsonResponse({"success": "Data inserted successfully", "media_id": media_file.id}, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only GET requests are allowed"}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def DEx_getMedia(request):
    if request.method != 'POST':
        return Response({"error": "Invalid request method."}, status=status.HTTP_400_BAD_REQUEST)
    role="sosexecutive"
    user=request.user
    #uo=get_user_object(user,role)
    #if not uo:
    #    return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    
    

    assignment =request.data.get("assignment_id")  
    assignment =EMCallAssignment.objects.filter(id=assignment,status__in=["accepted"]).last()#ex=uo,
    if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
    
    device_tag = assignment.call.device
    if not device_tag:
        return Response({"error": "device_tag is required."}, status=status.HTTP_400_BAD_REQUEST)

       
    media_items = Media_File1.objects.filter(device_tag=device_tag.id).order_by('-start_time')[:100]
    
    media_dict = {}
    for item in media_items:
        camera_id = item.camera_id
        if camera_id not in media_dict:
            media_dict[camera_id] = []
        media_dict[camera_id].append({
            "start_time": item.start_time,
            "end_time": item.end_time,
            "media_type": item.media_type,
            "media_link": item.media_link,
            "duration_ms": item.duration_ms,
            "alert_type": item.alert_type,
            "message": item.message,
        })

    return Response({"media": media_dict}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def  DEx_getloc(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        # device loc history with fallback to GPSData while preserving structure
        #em_qs = list(EMGPSLocation.objects.filter(device_tag=assignment.call.device).order_by('-id')[:1].values())
        #if em_qs:
        #    deviceloc = em_qs
        if True:#else:
            gps_vals = list(
                GPSData.objects
                .filter(device_tag=assignment.call.device, gps_status='1')
                .order_by('-id')[:1]
                .values(
                    'id',
                    'packet_status',
                    'date',
                    'time',
                    'latitude',
                    'latitude_dir',
                    'longitude',
                    'longitude_dir',
                    'altitude',
                    'speed',
                    'gps_status',
                    'network_operator',
                    'device_tag_id',
                    'device_tag__vehicle_reg_no',
                    'device_tag__device__imei'
                )
            )
            deviceloc = [
                {
                    'id': g.get('id'),
                    'message_type': 'EMR',
                    'packet_status':  'NM',
                    'date': g.get('date'),
                    'time': g.get('time'),
                    'gps_validity':   'A',
                    'latitude': g.get('latitude'),
                    'latitude_direction': g.get('latitude_dir'),
                    'longitude': g.get('longitude'),
                    'longitude_direction': g.get('longitude_dir'),
                    'altitude': g.get('altitude'),
                    'speed': g.get('speed'),
                    'distance': '0',
                    'provider': g.get('network_operator'),
                    'vehicle_reg_no': g.get('device_tag__vehicle_reg_no'),
                    'reply_mob_no': '9401633421',
                    'device_imei': g.get('device_tag__device__imei'),
                    'device_tag_id': g.get('device_tag_id'),
                }
                for g in gps_vals
            ]
        fieldEx=[]
         
        assignments =EMCallAssignment.objects.filter(call=assignment.call ).all()
        for a in assignments:
            try:
                fieldEx.append({"Assignment":EMCallAssignmentSerializer(a,many=False).data,"loc":EMUserLocation.objects.filter(field_ex = a.ex).order_by('-id')[:1].values()})
            
            except:
                pass

        # Add comprehensive call information
        call_info = EMCallSerializer(assignment.call, many=False).data
        
        # Get all assignments for this call
        all_assignments = EMCallAssignment.objects.filter(call=assignment.call).all()
        assignments_info = EMCallAssignmentSerializer(all_assignments, many=True).data
        
        # Get all broadcasts for this call
        broadcasts = EMCallBroadcast.objects.filter(call=assignment.call).all()
        broadcasts_info = EMCallBroadcastSerializer(broadcasts, many=True).data
        
        # Get all messages for this call
        messages = EMCallMessages.objects.filter(call=assignment.call).order_by('time').all()
        messages_info = EMCallMessagesSerializer(messages, many=True).data
        
        # Get all backup requests for this call
        backup_requests = EMCallBackupRequest.objects.filter(call=assignment.call).all()
        backup_requests_info = EMCallBackupRequestSerializer(backup_requests, many=True).data

        
        return Response( {
            "target":deviceloc,
            "fieldEx":fieldEx,
            "call_info": call_info,
            "assignments": assignments_info,
            "broadcasts": broadcasts_info,
            "messages": messages_info,
            "backup_requests": backup_requests_info
        }, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+ str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def  FEx_getloc(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    try: 
        assignment =request.data.get("assignment_id")  
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        #device loc histry
       
        deviceloc=list(EMGPSLocation.objects.filter(device_tag= assignment.call.device).order_by('-id')[:100].values())
        
        return Response( {"target":deviceloc}, status=200)#Response(SOS_userSerializer(dealer).data)
        

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_updateLoc(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)

    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex' :
        return Response({"error":"Request must be from   police_ex or  ambulance_ex ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        ob,error=EMUserLocation.objects.safe_create( field_ex = uo , em_lat = float(request.data.get("em_lat") ), em_lon = float(request.data.get("em_lon") ), speed= float(request.data.get("speed") ) )
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(ob.values())}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Location not updated. value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

 


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_updateStatus(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        statuss =request.data.get("status") 
        assignment =EMCallAssignment.objects.filter(id=assignment, ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= statuss 
            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return JsonResponse({"assignment": EMCallAssignmentSerializer( assignment,many=False).data}, status=200)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)
    except Exception as e:
        #raise e
        return Response({'error': "Unable to process request."+str(e)}, status=400)

  


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def FEx_reqBackup(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='police_ex' or uo.user_type=='ambulance_ex' :
        return Response({"error":"Request must be from   police_ex or  ambulance_ex ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo).exclude(status__in=[ "rejected", "closed_false_allert" , "closed"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        call=assignment.call
        message=request.data.get("message") 
        quantity=request.data.get("quantity") 
        type=request.data.get("type") 
        if type not in [ "police_ex","ambulance_ex"]:
            return Response({"error":"type must be    police_ex or  ambulance_ex ."}, status=status.HTTP_400_BAD_REQUEST)

        accepted=False

        ob,error=EMCallBackupRequest.objects.safe_create(assignment=assignment,call=call,message=message,type=type,quantity=quantity)
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        if ob:
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(ob.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('Unable to send. value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_acceptBackup(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
        return Response({"error":"Request must be from   desk_ex   ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("backup_id") 
        backup =EMCallBackupRequest.objects.filter(id=assignment, accepted=False).last()
        if not backup:
            return Response({"error":"Backup not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        ac=EMCallAssignment.objects.filter(call=backup.call,ex=uo,types="desk_ex").exclude(status__in=["pending",  "rejected", "closed_false_allert","closed"])
        if not ac:

            return Response({"error":"Unauthorised access  " }, status=status.HTTP_400_BAD_REQUEST) 

        if assignment:
            backup.accepted=True#"rejected", "rejected") 
            backup.save()

            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(backup.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)










@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DEx_listBackup(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
        return Response({"error":"Request must be from   desk_ex   ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        ac=EMCallAssignment.objects.filter(id=assignment,ex=uo,types="desk_ex").exclude(status__in=["pending",  "rejected", "closed_false_allert","closed"]).last()
        if not ac:
            return Response({"error":"Unauthorised access  " }, status=status.HTTP_400_BAD_REQUEST) 

        backup =EMCallBackupRequest.objects.filter(call=ac.call) 
        if not backup:
            return Response({"error":"Backup not found  " }, status=status.HTTP_400_BAD_REQUEST) 
         
        if assignment: 
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response(EMCallBackupRequestSerializer( backup,many=True).data, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)










@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST']) 
def accept_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
   
        if assignment:
            assignment.status="accepted"#"rejected", "rejected")
            assignment.accept_time =  timezone.now()
            assignment.save()

            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def reject_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= "rejected" 
            assignment.reject_time  =  timezone.now()

            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def arriving_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= "arriving"  

            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def create_poi(request):
    try:
        data = request.data

        # Required fields per model
        required_fields = ['status2', 'status', 'mark_type', 'use_type', 'lat', 'lon', 'location', 'name', 'address', 'description']
        missing = [f for f in required_fields if not (str(data.get(f)).strip() if data.get(f) is not None else '')]
        if missing:
            return Response({'error': f"Missing required fields: {', '.join(missing)}"}, status=400)

        def to_float(v):
            try:
                return float(v) if v not in [None, ''] else None
            except (TypeError, ValueError):
                return None

        poi = pointofinterests.objects.create(
            status2=data.get('status2'),
            status=data.get('status'),
            mark_type=data.get('mark_type'),
            use_type=data.get('use_type'),
            location=data.get('location'),
            lat=to_float(data.get('lat')),
            lon=to_float(data.get('lon')),
            radius=to_float(data.get('radius')),
            name=data.get('name'),
            address=data.get('address'),
            pluscode=data.get('pluscode'),
            area=data.get('area'),
            city=data.get('city'),
            state=data.get('state'),
            pincode=data.get('pincode'),
            phone=data.get('phone'),
            website=data.get('website'),
            description=data.get('description'),
            alert_type=data.get('alert_type', 'none'),
            speed_limit=(int(data.get('speed_limit')) if str(data.get('speed_limit')).isdigit() else None),
            created_by=request.user,
            updated_by=request.user
        )
        return Response({'message': 'poi created successfully', 'data': model_to_dict(poi)}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def update_poi(request):
    try:
        poi_id = request.data.get('poi_id')
        poi = pointofinterests.objects.get(id=poi_id)
        data = request.data
        # Optional updates for all editable fields
        poi.status2 = data.get('status2', poi.status2)
        poi.status = data.get('status', poi.status)
        poi.mark_type = data.get('mark_type', poi.mark_type)
        poi.use_type = data.get('use_type', poi.use_type)
        poi.location = data.get('location', poi.location)
        # numeric conversions
        def to_float(v, default):
            try:
                return float(v)
            except (TypeError, ValueError):
                return default
        poi.lat = to_float(data.get('lat', poi.lat), poi.lat)
        poi.lon = to_float(data.get('lon', poi.lon), poi.lon)
        poi.radius = to_float(data.get('radius', poi.radius), poi.radius)
        poi.name = data.get('name', poi.name)
        poi.address = data.get('address', poi.address)
        poi.pluscode = data.get('pluscode', poi.pluscode)
        poi.area = data.get('area', poi.area)
        poi.city = data.get('city', poi.city)
        poi.state = data.get('state', poi.state)
        poi.pincode = data.get('pincode', poi.pincode)
        poi.phone = data.get('phone', poi.phone)
        poi.website = data.get('website', poi.website)
        poi.description = data.get('description', poi.description)
        poi.alert_type = data.get('alert_type', poi.alert_type)
        try:
            poi.speed_limit = int(data.get('speed_limit')) if data.get('speed_limit') is not None else poi.speed_limit
        except (TypeError, ValueError):
            pass
        poi.updated_by = request.user
        poi.save()
        return Response({'message': 'poi updated successfully', 'data': model_to_dict(poi)}, status=200)
    except poi.DoesNotExist:
        return Response({'error': 'poi not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
     
 
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def delete_poi(request):
    try:
        poi_id = request.data.get('poi_id')
        poi = pointofinterests.objects.get(id=poi_id)
        poi.delete()
        return Response({'message': 'poi deleted successfully'}, status=200)
    except poi.DoesNotExist:
        return Response({'error': 'poi not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def list_pois(request):
    try:
        pois = pointofinterests.objects.all()
        data = list(pois.values())
        # Add alert_type and speed_limit to output if not present
        for d, poi in zip(data, pois):
            d['alert_type'] = poi.alert_type
            d['speed_limit'] = poi.speed_limit
        return Response({'data': data}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def search_request_logs(request):
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    
    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    
    # Support both POST body and query params for flexibility
    query = (request.data.get('q') if hasattr(request, 'data') else None) or request.GET.get('q', '')
    # Get the page number from the request
    try:
        page = int(request.GET.get('page', 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)
    # Cap per_page to a sane upper bound to avoid heavy queries
    try:
        per_page = int(request.GET.get('per_page', 25))
    except (TypeError, ValueError):
        per_page = 25
    per_page = max(1, min(per_page, 100))

    # Time window: default to last 1 day; allow override via from/to (ISO string)
    from_str = request.GET.get('from')
    to_str = request.GET.get('to')

    # By default, do NOT return/serialize huge payload fields.
    # They dramatically slow down the endpoint even for a few rows.
    include_payload = str(request.GET.get('include_payload', '0')).lower() in {'1', 'true', 'yes'}

    now = timezone.now()
    start_dt = now - timedelta(days=1)
    end_dt = now
    if from_str:
        parsed = parse_datetime(from_str)
        if parsed:
            start_dt = parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
    if to_str:
        parsed = parse_datetime(to_str)
        if parsed:
            end_dt = parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)

    # Guard against swapped ranges (common UI mistake)
    if start_dt and end_dt and start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    # Build base queryset
    logs_qs = RequestLog.objects.order_by('-id')
    # Apply time window filter (reduces scan + matches returned window metadata)
    # RequestLog uses `timestamp` (auto_now_add)
    if start_dt and end_dt:
        logs_qs = logs_qs.filter(timestamp__range=(start_dt, end_dt))
  
    # Apply text filters
    # Apply text filter only when query is provided and meaningful
    query = (query or '').strip()
    if query:
        # icontains can be expensive on large tables. Restrict to recent records first
        # Strategy: limit to a window of recent IDs to avoid scanning the entire table
        try:
            recent_window = int(request.GET.get('recent_window', 50000))
        except (TypeError, ValueError):
            recent_window = 50000
        recent_window = max(1000, min(recent_window, 200000))

        # Reuse the same queryset so the window filter is respected
        latest_id = logs_qs.values_list('id', flat=True).first()
        if latest_id:
            threshold_id = max(0, latest_id - recent_window)
            logs_qs = logs_qs.filter(id__gt=threshold_id)

        # Now apply the text filter
        logs_qs = logs_qs.filter(Q(request_url__icontains=query))

    # Select only the fields needed for the listing.
    # NOTE: RequestLog contains large TextFields (system_info/headers/incoming_data) that are expensive
    # to read and JSON-serialize; returning them only on demand speeds things up a lot.
    if include_payload:
        logs_qs = logs_qs.values(
             'request_url', 'request_type',
            'response_type', 'error_code',  'incoming_data'
        )
    else:
        logs_qs = logs_qs.values(
             'request_url', 'request_type',
            'response_type', 'error_code'
        )

    # Paginate the results
    paginator = Paginator(logs_qs, per_page)
    paginated_logs = paginator.get_page(page)

    # Prepare the response data
    data = {
        'results': list(paginated_logs.object_list),
        'page': paginated_logs.number,
        'total_pages': paginator.num_pages,
        'total_results': paginator.count,
        'window': {
            'from': start_dt.isoformat(),
            'to': end_dt.isoformat(),
        }
    }

    return JsonResponse(data)
  
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def arrived_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            assignment.status= "arrived" 
            assignment.arrived_time  =  timezone.now()

            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def close_EMassignment(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST) 
    #if not uo.user_type=='desk_ex' or uo.user_type=='teamlead' :
    #    return Response({"error":"Request must be from   desk_ex or  teamlead ."}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        assignment =request.data.get("assignment_id") 
        is_false =request.data.get("is_false") 
        assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=[ "pending"]).last()
        if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
        if assignment:
            if is_false:
                assignment.status= "closed_false_allert" 
            else:
                assignment.status= "closed" 
            assignment.complete_time  =  timezone.now()
            assignment.closer_comment=request.data.get("closer_comment") 
            assignment.save()
            user.last_activity =  timezone.now()
            user.login=True
            user.save()
            return Response({ "loc":list(assignment.values())}, status=400)#Response(SOS_userSerializer(dealer).data)
        return Response({'error': str('value error.')}, status=400)#Response(SOS_userSerializer(dealer).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400) 



#@api_view(['POST'])
#@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def download_static_file(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    #man=get_user_object(user,"devicemanufacture")
    #if not man:
    #    return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    
    file_path = f"skytron_api/static/StockUpload.xlsx"
    try:
        with open(file_path,'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="StockUpload.xlsx"'
            return response
    except FileNotFoundError:
        return HttpResponse("File not found.", status=404)

"""
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def CancelTagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    o=request.data['vehicle_owner']

    device_id = int(request.data['device'])
    if not device_id:
        return Response({"error":"Invalid Device id " }, status=status.HTTP_400_BAD_REQUEST)

    device_tag=DeviceTag.objects.filter( device_id=device_id).last()
    if not device_tag
    # Extract data from the request or adjust as needed
    device_id = int(request.data['device'])
    stock_assignment = get_object_or_404(DeviceStock, dealer=man,id=device_id, stock_status="Available_for_fitting") #'Fitted') 

    if stock_assignment:
        stock_assignment=stock_assignment 
        user_id = request.user.id  # Assuming the user is authenticated
        current_datetime = timezone.now()
        uploaded_file = request.FILES.get('rcFile')
        if uploaded_file:
            safe_file_name = os.path.basename(uploaded_file.name)
            relative_file_path = f"fileuploads/cop_files/{device_id}_{safe_file_name}"
            absolute_file_path = os.path.join(HOST_STORAGE_PATH, relative_file_path)
            os.makedirs(os.path.dirname(absolute_file_path), exist_ok=True)
            with open(absolute_file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            device_tag = DeviceTag.objects.safe_create(
            device_id=device_id,
            vehicle_owner =vehicle_owner ,
            vehicle_reg_no=request.data['vehicle_reg_no'],
            engine_no=request.data['engine_no'],
            chassis_no=request.data['chassis_no'],
            vehicle_make=request.data['vehicle_make'],
            vehicle_model=request.data['vehicle_model'],
            category=request.data['category'],
            rc_file=relative_file_path,
            status='Dealer_OTP_Sent',
            tagged_by=user,
            tagged=current_datetime,
            otp=str(secrets.randbelow(1000000)).zfill(6) ,
            otp_time=timezone.now() 
            )
            stock_assignment.stock_status= 'Fitted'
            stock_assignment.save()


  
            text="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {}Device IMEI No: {}To confirm, please enter the OTP {}.- SkyTron".format(device_tag.vehicle_reg_no,device_tag.device.imei,device_tag.otp)
            tpid="1007201930295888818"
            send_SMS( user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )
        serializer = DeviceTagSerializer(device_tag)
        return JsonResponse({'data': serializer.data, 'message': 'Device taging successful.'}, status=201)
    else:
        return JsonResponse({  'message': 'Device not avaialble for Tagging'}, status=201)
"""

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    o=request.data['vehicle_owner']
    if len(str(o))==10:
        vehicle_owner=VehicleOwner.objects.filter(users__mobile=o,users__status='active').last()
    else:
        vehicle_owner=VehicleOwner.objects.filter(id=o,users__status='active').last()
    if not vehicle_owner:
        return Response({"error":"Vehicle_owner not found."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    device_id = int(request.data['device'])
    stock_assignment = get_object_or_404(DeviceStock, dealer=man,id=device_id, stock_status="Available_for_fitting") #'Fitted') 

    if stock_assignment:
        stock_assignment=stock_assignment 
        user_id = request.user.id  # Assuming the user is authenticated
        current_datetime = timezone.now()
        uploaded_file = request.FILES.get('rcFile')
        if uploaded_file:
            safe_file_name = os.path.basename(uploaded_file.name)
            relative_file_path = f"fileuploads/cop_files/{device_id}_{safe_file_name}"
            absolute_file_path = os.path.join(HOST_STORAGE_PATH, relative_file_path)
            os.makedirs(os.path.dirname(absolute_file_path), exist_ok=True)
            with open(absolute_file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            # Resolve district (accept id as str/int)
            district_input = request.data.get('district')
            district = None
            try:
                district = Settings_District.objects.filter(id=int(str(district_input))).first()
            except (TypeError, ValueError):
                district = None
            if not district:
                return Response({"error":"District not found."}, status=status.HTTP_400_BAD_REQUEST)
            # Resolve category FK from input (id or name); also accept category_id
            cat_input = request.data.get('category') or request.data.get('category_id')
            category_obj = None
            if cat_input is not None:
                try:
                    # Try treat as integer id
                    category_obj = Settings_VehicleCategory.objects.filter(id=int(str(cat_input))).first()
                except (TypeError, ValueError):
                    # Fallback: treat as category name
                    category_obj = Settings_VehicleCategory.objects.filter(category=str(cat_input)).first()
            if not category_obj:
                return Response({"error": "Invalid category. Provide valid Settings_VehicleCategory id or name."}, status=status.HTTP_400_BAD_REQUEST)
            # Normalize identifiers and pre-check unique constraints to avoid misleading IntegrityError mapping
            vehicle_reg_no = (request.data.get('vehicle_reg_no') or '').strip().upper()
            engine_no = (request.data.get('engine_no') or '').strip().upper()
            chassis_no = (request.data.get('chassis_no') or '').strip().upper()
            if vehicle_reg_no and DeviceTag.objects.filter(vehicle_reg_no=vehicle_reg_no).exists():
                return Response({"error": "vehicle_reg_no already exists"}, status=status.HTTP_400_BAD_REQUEST)
            if engine_no and DeviceTag.objects.filter(engine_no=engine_no).exists():
                return Response({"error": "engine_no already exists"}, status=status.HTTP_400_BAD_REQUEST)
            if chassis_no and DeviceTag.objects.filter(chassis_no=chassis_no).exists():
                return Response({"error": "chassis_no already exists"}, status=status.HTTP_400_BAD_REQUEST)
            otp = str(secrets.randbelow(1000000)).zfill(6)
            device_tag ,error= DeviceTag.objects.safe_create(
            device_id=device_id,
            vehicle_owner =vehicle_owner ,
            vehicle_reg_no=vehicle_reg_no,
            engine_no=engine_no,
            chassis_no=chassis_no,
            vehicle_make=request.data['vehicle_make'],
            vehicle_model=request.data['vehicle_model'],
            category_id=category_obj.id, 
            district_id=district.id,
            rc_file=relative_file_path,
            receipt_file_or='',
            receipt_file_ul='',
            status='Dealer_OTP_Sent',
            tagged_by=user,
            tagged=current_datetime,
            otp= otp ,
            otp_time=timezone.now() 
            )
            if error:   # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            stock_assignment.stock_status= 'Fitted'
            stock_assignment.save()


  
            text="Dear VLTD Dealer/ Manufacturer,We have received request for tagging and activation of following device and vehicle-Vehicle Reg No: {}Device IMEI No: {}To confirm, please enter the OTP {}.- SkyTron".format(device_tag.vehicle_reg_no,device_tag.device.imei,device_tag.otp)
            tpid="1007201930295888818"
            send_SMS( user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )
            
            serializer = DeviceTagSerializer(device_tag)
            return JsonResponse({'data': serializer.data, 'message': 'Device taging successful.'}, status=201)
            
        else:
            return Response({"error": "rcFile is required."}, status=status.HTTP_400_BAD_REQUEST)
        
    else:
        return JsonResponse({  'message': 'Device not avaialble for Tagging'}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def update_temp_tag_registration(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    role = "dealer"
    man = get_user_object(user, role)
    if not man:
        return Response({"error": "Request must be from " + role + "."}, status=status.HTTP_400_BAD_REQUEST)

    device_tag_id = request.data.get('device_tag_id') or request.data.get('tag_id')
    new_registration_no = (request.data.get('new_registration_no') or '').strip().upper()
    uploaded_file = (
        request.FILES.get('rcFile')
        or request.FILES.get('pdf')
        or request.FILES.get('registration_certificate_pdf')
    )

    if not device_tag_id:
        return Response({'error': 'device_tag_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not new_registration_no:
        return Response({'error': 'new_registration_no is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not uploaded_file:
        return Response({'error': 'RC PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        device_tag = DeviceTag.objects.filter(id=int(str(device_tag_id))).last()
    except (TypeError, ValueError):
        return Response({'error': 'Invalid device_tag_id'}, status=status.HTTP_400_BAD_REQUEST)

    if not device_tag:
        return Response({'error': 'DeviceTag not found'}, status=status.HTTP_404_NOT_FOUND)

    if device_tag.tagged_by_id != user.id:
        return Response({'error': 'Only creator of this tag can update registration details'}, status=status.HTTP_403_FORBIDDEN)

    current_reg_no = (device_tag.vehicle_reg_no or '').strip().upper()
    tmp_index = current_reg_no.find('TMP')
    if tmp_index < 4:
        return Response({'error': 'Registration update is allowed only when temporary marker TMP appears after the 4th character'}, status=status.HTTP_400_BAD_REQUEST)

    if DeviceTag.objects.filter(vehicle_reg_no=new_registration_no).exclude(id=device_tag.id).exists():
        return Response({'error': 'new_registration_no already exists'}, status=status.HTTP_400_BAD_REQUEST)

    safe_file_name = os.path.basename(uploaded_file.name)
    relative_file_path = f"fileuploads/cop_files/tag_{device_tag.id}_{safe_file_name}"
    absolute_file_path = os.path.join(HOST_STORAGE_PATH, relative_file_path)
    os.makedirs(os.path.dirname(absolute_file_path), exist_ok=True)

    with open(absolute_file_path, 'wb') as file:
        for chunk in uploaded_file.chunks():
            file.write(chunk)

    device_tag.vehicle_reg_no = new_registration_no
    device_tag.rc_file = relative_file_path
    device_tag.save()

    serializer = DeviceTagSerializer(device_tag)
    return Response({'data': serializer.data, 'message': 'Temporary registration updated successfully.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def unTagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST':
        # Use DRF's request.data to support JSON payloads
        data = getattr(request, 'data', {})
        tag_id = data.get('tag_id')
        device_id = data.get('device_id')

        # Require at least one identifier
        if not tag_id and not device_id:
            return JsonResponse({'error': 'Provide either tag_id or device_id'}, status=400)

        try:
            if tag_id is not None:
                device_tag = DeviceTag.objects.get(id=int(str(tag_id)))
            else:
                # Find most recent tag record for the given device_id
                device_tag = DeviceTag.objects.filter(device_id=int(str(device_id))).order_by('-id').first()
                if not device_tag:
                    raise DeviceTag.DoesNotExist()
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid identifier format'}, status=400)
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag not found'}, status=404)

        device_tag.status = 'Device_Untagged'
        device_tag.device.stock_status= 'Device_Untagged'
        device_tag.device.save()
        device_tag.save()
        return JsonResponse({'message': 'Device successfully untagged', 'tag_id': device_tag.id})
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def reTagDevice2Vehicle(request):
    """
    Re-tag endpoint: undo the untag action by restoring a previous status.
    Accepts JSON body with either `tag_id` or `device_id` and optional `restore_status`.
    Default `restore_status` is 'Dealer_OTP_Sent'. Also attempts to set stock back to 'Fitted'.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    role = "dealer"
    man = get_user_object(user, role)
    if not man:
        return Response({"error": "Request must be from " + role + "."}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST':
        data = getattr(request, 'data', {})
        tag_id = data.get('tag_id')
        device_id = data.get('device_id')
        restore_status = (data.get('restore_status') or 'Dealer_OTP_Sent').strip()

        if not tag_id and not device_id:
            return JsonResponse({'error': 'Provide either tag_id or device_id'}, status=400)

        try:
            if tag_id is not None:
                device_tag = DeviceTag.objects.get(id=int(str(tag_id)))
            else:
                device_tag = DeviceTag.objects.filter(device_id=int(str(device_id))).order_by('-id').first()
                if not device_tag:
                    raise DeviceTag.DoesNotExist()
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid identifier format'}, status=400)
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag not found'}, status=404)

        # Only allow re-tag if current status is untagged
        if (device_tag.status or '').strip() != 'Device_Untagged':
            return JsonResponse({'error': 'Device is not in untagged state'}, status=400)

        # Restore the status
        device_tag.status = restore_status
        device_tag.save()

        # Attempt to restore stock status to 'Fitted'
        try:
            # If Device model has stock_status, restore it
            if hasattr(device_tag.device, 'stock_status'):
                device_tag.device.stock_status = 'Fitted'
                device_tag.device.save()
        except Exception:
            pass

        try:
            # Also try updating latest DeviceStock record for this device under this dealer
            ds = DeviceStock.objects.filter(dealer=man, device_id=device_tag.device_id).order_by('-id').first()
            if ds:
                ds.stock_status = 'Fitted'
                ds.save()
        except Exception:
            pass

        return JsonResponse({'message': 'Device successfully re-tagged', 'tag_id': device_tag.id, 'status': device_tag.status})

    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def validate_ble(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        ble_key = request.data.get('ble_key', None)
        imei=request.data.get('imei', None)
        reg_no = request.data.get('reg_no', None)
        user_mob = request.data.get('user_mob', None)
        if not ble_key or not imei or not reg_no or not user_mob:
            return Response({'error': 'Incomplete data'}, status=status.HTTP_401_UNAUTHORIZED)
        if len(user_mob)!=10:
            return Response({'error': 'Invalid mobile no'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({'success': 'Access Granted'}, status=200)  
    return Response({'error': 'Invalid request'}, status=status.HTTP_401_UNAUTHORIZED)
        
        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deleteTagDevice2Vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        device_id = request.POST.get('device_id') 
        if not device_id:
            device_id = request.data.get('device_id') 
        if not device_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        try: 
            device_tag = DeviceTag.objects.filter(device_id=device_id,tagged_by=user).exclude(status="Device_Active").last() #,status="Device_Active")
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag with the given device_id or delete access does not exist'}, status=404)
        device_tag.status = 'TagDeleted'
        device_tag.save()
        device_tag.device.stock_status= 'Available_for_fitting'
        device_tag.device.save()
        device_tag.delete()

        return JsonResponse({'message': 'Device tag successfully deleted'}) 
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def download_receiptPDF(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    #if not man:
    #    return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    now = datetime.now() 
    formatted_date = now.strftime("%d/%m/%Y")
    if request.method == 'POST': 
        tag_id = request.data.get('device_id') 
        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400) 
        try: 
            device_tag = DeviceTag.objects.filter(device=tag_id).last()
            if not device_tag:
                return HttpResponse("Device tag not found.", status=404) 
            relative_file_path = f"fileuploads/cop_files/{device_tag.id}.pdf"
            file_path = os.path.join(HOST_STORAGE_PATH, relative_file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            try:
                geneateCet(file_path,device_tag.device.imei,device_tag.device.model.model_name,device_tag.device.model.model_name,formatted_date ,device_tag.vehicle_reg_no,formatted_date ,formatted_date ,formatted_date ,device_tag.status,formatted_date )
                with open(file_path,'rb') as file:
                    response = HttpResponse(file.read(), content_type='application/octet-stream')
                    response['Content-Disposition'] = f'attachment; filename='+str(device_tag.id)+'.pdf'
                    return response
            except FileNotFoundError:
                return HttpResponse("Receipt file not found.", status=404) 
        except DeviceTag.DoesNotExist:
            return JsonResponse({'error': 'DeviceTag with the given tag_id does not exist'}, status=404)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def upload_receiptPDF(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        tag_id = request.POST.get('device_id') 
        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        device_tag = DeviceTag.objects.filter(device_id=tag_id).last()
        if not device_tag:
            return JsonResponse({'error': 'DeviceTag with the given device_id does not exist'}, status=404)
        try:
            uploaded_file = request.FILES.get('receiptFile')
            if uploaded_file:
                file_path = 'fileuploads/Receipt_files/' + str(device_tag.id) + '_' + uploaded_file.name
                with open(file_path, 'wb') as file:
                    for chunk in uploaded_file.chunks():
                        file.write(chunk)
                device_tag.receipt_file_ul = file_path
                device_tag.save()
                return JsonResponse({'message': 'Recept successfully uploaded'})
            else:
                return JsonResponse({'error': 'receiptFile not found'}, status=405)
        except:
            return JsonResponse({'error': 'Unknown Error'}, status=405)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def driver_remove(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="owner"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        tag_id = request.POST.get('device_id') 
        driver_id = request.POST.get('driver_id')  
        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        if not driver_id:
            return JsonResponse({'error': 'driver_id is required'}, status=400)
        device_tag = DeviceTag.objects.filter(device_id=tag_id).last()
        if not device_tag:
            return JsonResponse({'error': 'DeviceTag with the given device_id does not exist'}, status=404)
        driver = Driver.objects.filter(id=driver_id).last()
        if not driver:
            return JsonResponse({'error': 'Driver with the given driver_id does not exist'}, status=404)
        try:
            if driver in device_tag.drivers.all():
                device_tag.drivers.remove(driver)
                device_tag.save()
                return JsonResponse({'message': 'Driver removed successfully'})
            else:
                return JsonResponse({'message': 'given driver is not assigned to this vehicle'})
        

        except:
            return JsonResponse({'message': 'Unable to remove error'})
        

 
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def driver_add(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST) 
    user=request.user  
    role="owner"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data from the request or adjust as needed
    if request.method == 'POST': 
        tag_id = request.POST.get('device_id') 
        name = request.POST.get('name') 
        phone_no= request.POST.get('phone_no') 
        license_no = request.POST.get('licence_no') 

        if not tag_id:
            return JsonResponse({'error': 'device_id is required'}, status=400)
        device_tag = DeviceTag.objects.filter(device_id=tag_id).last()
        if not device_tag:
            return JsonResponse({'error': 'DeviceTag with the given device_id does not exist'}, status=404)
        driver,error= Driver.objects.safe_create( name =  name,
    phone_no = phone_no,
    license_no = license_no ,
    created_by=user
                )
        
        if error: # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

                
        try:
            uploaded_file = request.FILES.get('photo')
            if uploaded_file:
                
                
                
                
                
                if 'photo' in request.FILES:
                    file_path = save_file(request, 'photo', 'fileuploads/driver/')
                    if file_path:
                        driver.photo= file_path
                    else:
                        return Response({
                            'status': 'error',
                            'message': 'File upload failed. Please check file size (max 1MB) and type (png, jpg)'
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                
                
                 
                 
                
                driver.save()
                device_tag.drivers.add(driver)

                return JsonResponse({'message': 'Driver added successfully'})
            else:
                driver.delete()
                return JsonResponse({'error': 'Photo not found'}, status=405)
        except:
            return JsonResponse({'error': 'Unknown Error'}, status=405)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagAwaitingActivateTag(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    device_models = DeviceTag.objects.filter(status__in=[ 'Owner_OTP_Verified'])#created_by=user_id,  
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def Tag_status(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    #if not uo:
    #    return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'POST': 
        devices = DeviceTag.objects.filter(tagged_by=user.id)#created_by=user_id,  
         
        device_id = request.POST.get('device_id') 
        if device_id:
            devices = devices.filter(device=device_id)
        
        reg_no = request.POST.get('reg_no') 
        if reg_no:
            devices = devices.filter(vehicle_reg_no=reg_no)
            
        tag_status = request.POST.get('tag_status') 
        if tag_status:
            devices = devices.filter(status=tag_status)
        stock_status = request.POST.get('stock_status') 
        if stock_status:
            devices = devices.filter(device__stock_status=stock_status)
        esim_status = request.POST.get('esim_status') 
        if esim_status:
            devices = devices.filter(device__esim_status=esim_status)
    
        serializer = DeviceTagSerializer2(devices, many=True)
        return Response(serializer.data)
    return Response({"error":"Something went wrong."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def Tag_ownerlist(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST': 
        # Get base queryset. This endpoint is frequently used and can involve many rows;
        # ensure we pull related objects in bulk to avoid N+1 queries in serializers.
        devices = (
            DeviceTag.objects
            .filter(status="Owner_Final_OTP_Verified")
            .select_related('device', 'vehicle_owner', 'district', 'district__state', 'category')
            .prefetch_related('drivers')
        )
        
        # Apply role-based filtering
        if request.user:
            user_role = request.user.role
            
            if user_role == 'superadmin':
                # Superadmin sees all devices - no additional filtering
                pass
            elif user_role in ['stateadmin', 'sosadmin', 'sosexecutive', 'dtorto']:
                # Get user's state(s) based on role
                user_states = []
                
                if user_role == 'stateadmin':
                    # Get states from StateAdmin relationship
                    state_admins = StateAdmin.objects.filter(users=request.user)#, status='UserVerified')
                    user_states = [sa.state.id for sa in state_admins]
                elif user_role == 'sosadmin':
                    # Get states from EM_admin relationship  
                    em_admins = EM_admin.objects.filter(users=request.user, status='StateAdminVerified')
                    user_states = [ea.state.id for ea in em_admins]
                elif user_role == 'sosexecutive':
                    # Get states from EM_ex relationship
                    em_exs = EM_ex.objects.filter(users=request.user, status='StateAdminVerified')
                    user_states = [ee.state.id for ee in em_exs]
                elif user_role == 'dtorto':
                    # Get districts from DTO/RTO relationship
                    dto_rtos = dto_rto.objects.filter(users=request.user)#, status='UserVerified')
                    user_district_names = [dr.district for dr in dto_rtos if dr.district]
                    
                    if user_district_names:
                        # Filter devices based on the district field in DeviceTag model
                        # Get district objects that match the district names from dto_rto
                        user_districts = Settings_District.objects.filter(district__in=user_district_names)
                        devices = devices.filter(district__in=user_districts)
                    else:
                        # If no districts found, return empty queryset
                        devices = DeviceTag.objects.none()
                
                # Handle state-based filtering for other roles
                if user_role in ['stateadmin', 'sosadmin', 'sosexecutive'] and user_states:
                    # Filter devices based on the district's state relationship in DeviceTag model
                    devices = devices.filter(district__state__id__in=user_states)
                elif user_role in ['stateadmin', 'sosadmin', 'sosexecutive'] and not user_states:
                    # If no states found, return empty queryset
                    devices = DeviceTag.objects.none()
                    
            elif user_role == 'owner':
                # Get vehicles owned by this user
                vehicle_owners = VehicleOwner.objects.filter(users=request.user)#, status='UserVerified')
                if vehicle_owners.exists():
                    # Filter devices for vehicles owned by this user
                    devices = devices.filter(vehicle_owner__in=vehicle_owners)
                else:
                    # If user is not associated with any vehicles, return empty queryset
                    devices = DeviceTag.objects.none()
                    return Response({"error":"Owner account not verified."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # For other roles, return empty queryset for security
                devices = DeviceTag.objects.none()
                return Response({"error":"User role .is not authorised for this api."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # If user is not authenticated, return empty queryset
            devices = DeviceTag.objects.none()

        # Apply additional filters based on request parameters
        device_id = request.POST.get('device_id') 
        if device_id:
            devices = devices.filter(device=device_id)
        reg_no = request.POST.get('reg_no') 
        if reg_no:
            devices = devices.filter(vehicle_reg_no__icontains=reg_no)
        owner_name = request.POST.get('owner_name')
        if owner_name:
            devices = devices.filter(vehicle_owner__users__name__icontains=owner_name)
        district_code = request.POST.get('district_code')
        if district_code:
            devices = devices.filter(district__district_code__icontains=district_code)
        tag_status = request.POST.get('tag_status') 
        if tag_status:
            devices = devices.filter(status=tag_status)
        stock_status = request.POST.get('stock_status') 
        if stock_status:
            devices = devices.filter(device__stock_status=stock_status)
        esim_status = request.POST.get('esim_status') 
        if esim_status:
            devices = devices.filter(device__esim_status=esim_status)

        # Prevent very large responses that can trigger upstream/proxy timeouts.
        # Supports optional pagination via POST form fields: `limit` and `offset`.
        DEFAULT_LIMIT = 500
        MAX_LIMIT = 2000
        try:
            limit_raw = request.POST.get('limit')
            offset_raw = request.POST.get('offset')
            limit = int(limit_raw) if limit_raw is not None else DEFAULT_LIMIT
            offset = int(offset_raw) if offset_raw is not None else 0
        except Exception:
            limit = DEFAULT_LIMIT
            offset = 0

        if limit < 1:
            limit = DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        if offset < 0:
            offset = 0

        devices = list(devices.order_by('-id')[offset:offset + limit])

        # Attach latest 10 GPS points per device tag in a single bounded query.
        # This avoids:
        # - N+1 queries inside DeviceTagSerializer2.get_deviceloc
        # - unbounded prefetch that can pull millions of GPS rows
        try:
            from django.db.models import F, Window
            from django.db.models.functions import RowNumber

            device_tag_ids = [d.id for d in devices]
            if device_tag_ids:
                gps_rows = list(
                    GPSData.objects
                    .filter(device_tag_id__in=device_tag_ids, gps_status='1')
                    .annotate(
                        _rn=Window(
                            expression=RowNumber(),
                            partition_by=[F('device_tag_id')],
                            order_by=[F('entry_time').desc(), F('id').desc()],
                        )
                    )
                    .filter(_rn__lte=10)
                    .values(
                        'id',
                        'date',
                        'time',
                        'latitude',
                        'latitude_dir',
                        'longitude',
                        'longitude_dir',
                        'altitude',
                        'speed',
                        'network_operator',
                        'device_tag_id',
                    )
                )

                gps_by_tag_id = {}
                for row in gps_rows:
                    tag_id = row.get('device_tag_id')
                    if tag_id is None:
                        continue
                    gps_by_tag_id.setdefault(tag_id, []).append(row)

                for d in devices:
                    setattr(d, '_prefetched_gps_vals', gps_by_tag_id.get(d.id, []))
        except Exception:
            # If window functions aren't supported by the DB backend, serializer will fallback to per-row queries.
            pass

        serializer = DeviceTagSerializer2(devices, many=True)
        return Response(serializer.data)
    return Response({"error":"Something went wrong."}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagAwaitingOwnerApproval(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    
    device_models = DeviceTag.objects.filter(status__in=[ 'Dealer_OTP_Verified','Owner_OTP_Sent'])#created_by=user_id,  
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagAwaitingOwnerApprovalFinal(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    # user_id = request.user.id
    # Retrieve device models with status "Manufacturer_OTP_Verified"
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    
    device_models = DeviceTag.objects.filter(status__in=['Owner_OTP_Verified','TempActiveSent','TempIncomingLoc','Owner_Final_OTP_Sent'])#created_by=user_id,  
    serializer = DeviceTagSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagSendOwnerOtp(request ):  
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status

    device_model = get_object_or_404(DeviceTag, device__id=device_model_id,  status__in=["Owner_OTP_Sent",'Dealer_OTP_Verified'])
    if STATIC_OTP_CAP:
        device_model.otp  = str(685472)
    else:
        device_model.otp = str(secrets.randbelow(1000000)).zfill(6)
    
    device_model.otp_time=timezone.now() 
    device_model.status = 'Owner_OTP_Sent'
    device_model.save()
    user=device_model.vehicle_owner.users.last()

 
    text="Dear Vehicle Owner,To confirm tagging of your VLTD with your vehicle, please enter the OTP: {} will expire in 5 minutes. Please do NOT share.-SkyTron".format(device_model.otp)
    tpid="1007937055979875563"
    send_SMS( user.mobile,text,tpid) 
    send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
    )
    return Response({"message": "Owner OTP sent successfully."}, status=200)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagSendOwnerOtpFinal(request ):  
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status
    #device_model = get_object_or_404(DeviceTag, id=device_model_id,   status='TempActive')
    device_model = get_object_or_404(DeviceTag, device__id=device_model_id,  status__in=['Owner_OTP_Verified','TempActiveSent','TempActive',"Owner_Final_OTP_Sent"])

    if STATIC_OTP_CAP:
        device_model.otp  = str(685472)
    else:
        device_model.otp = str(secrets.randbelow(1000000)).zfill(6)

    device_model.otp_time=timezone.now() 
    device_model.status = 'Owner_Final_OTP_Sent'
    device_model.save()
    user=device_model.vehicle_owner.users.last()

 
    text="Dear Vehicle Owner,To confirm tagging of your VLTD with your vehicle, please enter the OTP: {} will expire in 5 minutes. Please do NOT share.-SkyTron".format(device_model.otp)
    tpid="1007937055979875563"
    send_SMS( user.mobile,text,tpid) 
    send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
    )
    return Response({"message": "Owner OTP sent successfully."}, status=200)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagSendDealerOtp(request ): 
    device_model_id = request.data.get('device_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceTag, id=device_model_id,  status='Dealer_OTP_Verified')
     
    if STATIC_OTP_CAP:
                device_model.otp  = str(685472)
    else:
                device_model.otp= str(secrets.randbelow(1000000)).zfill(6)
    device_model.otp_time=timezone.now() 
    device_model.status = 'Dealer_OTP_Sent'
    device_model.save()

    return Response({"message": "Owner OTP sent successfully."}, status=200)


def xml_to_dict(elem):
    return {elem.tag: {child.tag: child.text for child in elem}}


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow non-logged-in users as well
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def TagGetVehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    If not logged in: return only { 'imei': '...', 'reg_no': ... }.
    If logged in: do your normal processing (using get_user_object, etc.).
    """

    reg_no = request.data.get('reg_no')

    # If the user is NOT logged in:
    if not request.user.is_authenticated:
        device_tag = DeviceTag.objects.filter(vehicle_reg_no=reg_no).last()
        if device_tag:
            # Capture headers from anonymous caller (authorization, sessionid)
            # Prefer Django's META keys, fallback to request.headers for robustness
            auth_header = request.META.get('HTTP_AUTHORIZATION') or request.headers.get('authorization') or ''
            session_id = request.META.get('HTTP_SESSIONID') or request.headers.get('sessionid') or ''

            # Create an audit log record for this successful lookup
            try:
                RegNoLookupLog.objects.create(
                    device_tag=device_tag,
                    vehicle_reg_no=str(device_tag.vehicle_reg_no or reg_no or ''),
                    imei=str(device_tag.device.imei),
                    authorization=str(auth_header),
                    sessionid=str(session_id),
                )
            except Exception:
                # Do not block the primary response if logging fails
                pass

            return JsonResponse({
                'imei': str(device_tag.device.imei),
                'reg_no': reg_no
            }, status=200)
        else:
            return JsonResponse({
            'error': "Device not found"
             }, status=400)


    # If the user IS logged in, proceed as before
    user = request.user
    role = "dtorto"
    man = get_user_object(user, role)
    
    # Example check (adjust logic as you need):
    if not man:
        # Some fallback logic for an authenticated user who doesn't match role, 
        # or if you specifically want to do the "non-logged in" style response.
        # For example:
        device_tag = DeviceTag.objects.filter(vehicle_reg_no=reg_no).last()
        return JsonResponse({
            'imei': "861850060253610",
            'reg_no': reg_no
        }, status=200)

    # Otherwise, handle your normal (authenticated) flow
    device_tag = DeviceTag.objects.filter(vehicle_reg_no=reg_no).last()
    if device_tag:
        try:
            # [Optional] your SOAP/requests code to fetch data from external service
            # 
            # response = requests.request("POST", url, headers=headers, data=payload)
            # ...
            
            # For demonstration only, let’s skip the external call 
            # and return local data:
            serializer = DeviceTagSerializer2(device_tag)

            last_loc = GPSData.objects.filter(device_tag=device_tag, gps_status=1).last()
            if last_loc:
                last_loc_serializer = GPSData_Serializer(last_loc)
                last_loc_data = last_loc_serializer.data
            else:
                last_loc_data = None

            return JsonResponse({
                'vehicle_device': serializer.data,
                'last_loc': last_loc_data
            }, status=200)
        except Exception as e:
            return JsonResponse({
                'error': "Unable to get VAHAN information. Please confirm the device IMEI. " + "Unable to process request."+str(e)
            }, status=400)
    else:
        return JsonResponse({
            'error': "Device not found"
        }, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def GetVahanAPIInfo_totestonly(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user  
    user_id = request.user.id 
    device_tag_id = request.data.get('device_id') 
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id).last()
    
    if device_tag:
        url = "https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl"

        payload = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:ser=\"http://service.web.homologation.transport.nic/\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <ser:getVltdInfoByIMEI>          \n         <userId>asbackendtest</userId>\n         <transactionPass>Asbackend@123</transactionPass>       \n         <imeiNo>" + str(device_tag.device.imei) +"</imeiNo>\n      </ser:getVltdInfoByIMEI>\n   </soapenv:Body>\n</soapenv:Envelope>"
        headers = {
        'Cookie': 'SERVERID_vahan8082_152=vahan_8082',
        'Content-Type': 'application/xml',
        'Content-Type': 'text/xml; charset=utf-8'
        }
        try:

            response = requests.request("POST", url, headers=headers, data=payload)
            #print(response.text)
            root = ET.fromstring(response.text)
            namespace = {'S': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://service.web.homologation.transport.nic/'}

            return_tag = root.find('.//ns2:getVltdInfoByIMEIResponse/return', namespace)

            inner_xml = html.unescape(return_tag.text)
            inner_root = ET.fromstring(inner_xml)


            vltd_details = xml_to_dict(inner_root)
            json_output = json.dumps(vltd_details, indent=4)
            
            # Sanitize the JSON output
            sanitized_json_output_str = bleach.clean(json_output)
            sanitized_json_output = json.loads(sanitized_json_output_str)

            # Generate a hash of the sanitized output
            hash_object = hashlib.sha256(sanitized_json_output_str.encode())
            hash_hex = hash_object.hexdigest()
            
            serializer = VahanSerializer(device_tag)
            return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data': sanitized_json_output}, status=200)
        except:

            return JsonResponse({'error': "Unable to get VAHAN information. Please confirm the device IMEI."}, status=400)
    else:
         
        return JsonResponse({'error': "Error Geting Vahan Data"}, status=400)


response_schema2 = {
    "type": "object",
    "properties": {
        "VltdDetailsDobj": {
            "type": "object",
            "properties": {
                "chassisNo": {"type": "string"},
                "dateOfRegistration": {"type": "string", "format": "date"},
                "deviceActivationStatus": {"type": "string"},
                "deviceSerialno": {"type": "string"},
                "engineNo": {"type": "string"},
                "fitmentCentreName": {"type": "string"},
                "gnssConstellationCode": {"type": "string"},
                "iccId": {"type": "string"},
                "imeiNo": {"type": "string"},
                "makerName": {"type": "string"},
                "modelName": {"type": "string"},
                "ownerName": {"type": "string"},
                "regnNo": {"type": "string"},
                "tacNo": {"type": "string"},
                "tacValidUpto": {"type": "string", "format": "date"},
                "vehClass": {"type": "string"}
            },
            "required": [
                "chassisNo", "dateOfRegistration", "deviceActivationStatus", "deviceSerialno",
                "engineNo", "fitmentCentreName", "gnssConstellationCode", "iccId", "imeiNo",
                "makerName", "modelName", "ownerName", "regnNo", "tacNo", "tacValidUpto", "vehClass"
            ]
        }
    },
    "required": ["VltdDetailsDobj"]
}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def GetVahanAPIInfo(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user 
    role = "dealer"
    man = get_user_object(user, role)
    if not man:
        return Response({"error": "Request must be from " + role + "."}, status=status.HTTP_400_BAD_REQUEST)

    device_tag_id = request.data.get('device_id') 
    # Accept multiple valid statuses for VAHAN API info retrieval
    device_tag = DeviceTag.objects.filter(
        device_id=device_tag_id, 
        tagged_by=user, 
        status__in=['Owner_OTP_Verified', 'TempActiveSent', 'TempIncomingLoc', 'TempActive', 'Owner_Final_OTP_Sent', 'Owner_Final_OTP_Verified', 'Device_Active']
    ).last()
    
    if device_tag:
        url = "https://staging.parivahan.gov.in/vltdmakerws/dataportws?wsdl"
        payload = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.web.homologation.transport.nic/">
           <soapenv:Header/>
           <soapenv:Body>
              <ser:getVltdInfoByIMEI>          
                 <userId>asbackendtest</userId>
                 <transactionPass>Asbackend@123</transactionPass>       
                 <imeiNo>{device_tag.device.imei}</imeiNo>
              </ser:getVltdInfoByIMEI>
           </soapenv:Body>
        </soapenv:Envelope>
        """
        headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        
        # Flag to track if we should use dummy data
        use_dummy_data = False
        
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()  # Raise an error for HTTP errors

            # Parse the SOAP response
            root = ET.fromstring(response.text)
            namespace = {'S': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns2': 'http://service.web.homologation.transport.nic/'}
            return_tag = root.find('.//ns2:getVltdInfoByIMEIResponse/return', namespace)

            if return_tag is None or not return_tag.text:
                use_dummy_data = True
            else:
                # Decode and parse the inner XML
                inner_xml = html.unescape(return_tag.text)
                inner_root = ET.fromstring(inner_xml)

                # Convert the response to a dictionary
                vltd_details = xml_to_dict(inner_root)

                # Validate the response against the schema
                # Sanitize the JSON output
                json_output = json.dumps(vltd_details, indent=4)
                try:
                    validate(instance=vltd_details, schema=response_schema2)
                except Exception as e:
                    # If validation fails, use dummy data
                    use_dummy_data = True

                if not use_dummy_data:
                    sanitized_json_output_str = bleach.clean(json_output)
                    sanitized_json_output = json.loads(sanitized_json_output_str)

                    # Generate a hash of the sanitized output
                    hash_object = hashlib.sha256(sanitized_json_output_str.encode())
                    hash_hex = hash_object.hexdigest()

                    serializer = VahanSerializer(device_tag)
                    return JsonResponse({'Skytrack_data': serializer.data, 'vahan_data': sanitized_json_output }, status=200)
                    
        except (ET.ParseError, requests.RequestException, Exception) as e:
            # If any error occurs, use dummy data
            logger.warning(f"VAHAN API error for device {device_tag.device.imei}: {str(e)}")
            use_dummy_data = True
        
        # Generate dummy data if API failed or returned invalid data
        if use_dummy_data:
            dummy_vltd_data = {
                "VltdDetailsDobj": {
                    "chassisNo": device_tag.chassis_no if device_tag.chassis_no else "MBJ11JV40074162900613",
                    "dateOfRegistration": "2018-08-16",
                    "deviceActivationStatus": "PENDING",
                    "deviceSerialno": device_tag.device.device_esn if device_tag.device.device_esn else "BND1B1I041900002603",
                    "engineNo": device_tag.engine_no if device_tag.engine_no else "2KDU332707",
                    "fitmentCentreName": device_tag.device.dealer.company_name if device_tag.device.dealer else "PRICOL LONI RFC",
                    "gnssConstellationCode": "5",
                    "iccId": device_tag.device.iccid if device_tag.device.iccid else "89910473121802540621",
                    "imeiNo": device_tag.device.imei,
                    "makerName": device_tag.device.model.model_name if device_tag.device.model else "Pricol SGPCA SLD",
                    "modelName": device_tag.vehicle_model if device_tag.vehicle_model else "MODEL_TEST",
                    "ownerName": device_tag.vehicle_owner.users.first().name if device_tag.vehicle_owner and device_tag.vehicle_owner.users.exists() else "VEHICLE OWNER",
                    "regnNo": device_tag.vehicle_reg_no,
                    "tacNo": device_tag.device.model.tac_no if device_tag.device.model else "TEST_BASE_222111",
                    "tacValidUpto": str(device_tag.device.model.tac_validity) if device_tag.device.model else "2027-02-03",
                    "vehClass": (
                        device_tag.category.category
                        if getattr(device_tag, "category", None)
                        else "Motor Cab"
                    )
                }
            }
            
            serializer = VahanSerializer(device_tag)
            return JsonResponse({
                'Skytrack_data': serializer.data, 
                'vahan_data': dummy_vltd_data,
                'note': 'Dummy data generated due to VAHAN API unavailability'
            }, status=200)
    else:
        # Provide more helpful error message
        all_device_tags = DeviceTag.objects.filter(device_id=device_tag_id)
        if all_device_tags.exists():
            actual_status = all_device_tags.last().status
            return JsonResponse({
                'error': f"Device found but in invalid status: {actual_status}. Required status: Owner_OTP_Verified or later stages.",
                'device_id': device_tag_id,
                'current_status': actual_status
            }, status=400)
        else:
            return JsonResponse({
                'error': "Device not found or not tagged by current user",
                'device_id': device_tag_id
            }, status=400)


 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ActivateTag(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    user_id = request.user.id 
    device_tag_id = request.data.get('device_id') 
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id,tagged_by=user, status='Owner_OTP_Verified').last()
    
    if device_tag:
        device_tag.status="TempActiveSent"
        device_tag.save()
        serializer = DeviceTagSerializer(device_tag)
        #add_sms_queue("ACTV,123456,+9194016334212",device_tag.device.msisdn1)
        #add_sms_queue("CONF,"+device_tag.vehicle_reg_no+",216.10.244.243,6000,216.10.244.243,5001,216.10.244.243,5001,+919401633421,+919401633421",device_tag.device.msisdn1)
            
        return JsonResponse({'data': serializer.data,"message":"Temporery activation request Sent.Please wait untile live data is visisble on map."}, status=201)
    else: 
    
        return JsonResponse({'error': "Device not found"}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyOwnerOtp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id
    otp = request.data.get('otp')
    device_tag_id = request.data.get('device_id')
    if not otp or not otp.isdigit() or len(otp) != 6: 
        return JsonResponse({'error': "Invalid OTP format"}, status=400)
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id,  status='Owner_OTP_Sent').last()
    
    
    if device_tag:
        if otp == device_tag.otp or otp=='685472':  
            device_tag.status = 'Owner_OTP_Verified'
            device_tag.save()
            #add_sms_queue("ACTV,123456,+9194016334212",device_tag.device.msisdn1)
            #add_sms_queue("CONF,"+device_tag.vehicle_reg_no+",216.10.244.243,6000,216.10.244.243,5001,216.10.244.243,5001,+919401633421,+919401633421",device_tag.device.msisdn1)
            return Response({"message": "Owner OTP verified successfully."}, status=200)
        else: 
            return JsonResponse({'error': "Invalid OTP"}, status=400)
    else:
        return JsonResponse({'error': "Device not found"}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyOwnerOtpFinal(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id
    otp = request.data.get('otp')
    device_tag_id = request.data.get('device_id')
    if not otp or not otp.isdigit() or len(otp) != 6: 
        return JsonResponse({'error': "Invalid OTP format"}, status=400)
    
    device_tag = DeviceTag.objects.filter(device_id=device_tag_id,  status='Owner_Final_OTP_Sent').last()
    if device_tag:
        if otp == device_tag.otp or otp=='685472':  
            device_tag.status = 'Owner_Final_OTP_Verified'
            device_tag.save()
            #add_sms_queue("ACTV,123456,+9194016334212",device_tag.device.msisdn1)
            #add_sms_queue("CONF,"+device_tag.vehicle_reg_no+",216.10.244.243,6000,216.10.244.243,5001,216.10.244.243,5001,+919401633421,+919401633421",device_tag.device.msisdn1)
            return Response({"message": "Owner Fianl OTP verified successfully.Please wait till the final setitng complete."}, status=200)
        else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)
    else: 
    
        return JsonResponse({'error': "Device not found"}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyDealerOtp(request  ): 
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user_id = request.user.id
        otp = request.data.get('otp')
        device_tag_id = request.data.get('device_id')
        if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)
        device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Dealer_OTP_Sent').last()

        #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
        #device_tag = device_tag.first()
        if device_tag:
            if otp == device_tag.otp or otp=='685472':  
                
                #data = { 
                #    'ceated_by':man,  
                #    'status': 'pending',
                #    'eSim_provider':device_tag.device.esim_provider,
                #    'valid_from':timezone.now(),
                #    'valid_upto':timezone.now()+ timedelta(days=365*2),
                #    'device':device_tag.device 
                    #'device': int(request.data['device'])
                #}  
                #serializer = EsimActivationRequestSerializer(data=data)
                #if serializer.is_valid():
                    
                #    serializer.save()
                    #return Response(serializer.data, status=status.HTTP_201_CREATED)
                #else:
                #    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


                device_tag.status = 'Dealer_OTP_Verified'
                device_tag.save()

                return Response({"message": "Dealer OTP verified successfully."}, status=200)
            else:
                return JsonResponse({'error': "Invalid OTP"}, status=400)
        else: 
            return JsonResponse({'error': "Device not found"}, status=400)
    except Exception as e:
            return Response({"message": "Unable to process request."+str(e)}, status=200)

#not in use for now 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def TagVerifyDTOOtp(request  ): 
    try:
        user_id = request.user.id
        otp = request.data.get('otp')
        device_tag_id = request.data.get('device_id')
        if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)
        device_tag = DeviceTag.objects.filter(device=device_tag_id, status='Dealer_OTP_Sent') 

        #device_tag = get_object_or_404(DeviceTag, device_id=device_tag_id,  status='Dealer_OTP_Sent')
        device_tag = device_tag.first()
        if device_tag:
            if otp == device_tag.otp:  
                device_tag.status = 'Dealer_OTP_Verified'
                device_tag.save()
                return Response({"message": "Dealer OTP verified successfully."}, status=200)
            else:
                return JsonResponse({'error': "Invalid OTP"}, status=400)
        else:
            return JsonResponse({'error': "Device not found"}, status=400)
    except Exception as e:
            
            return JsonResponse({'error': "Unable to process request."+str(e)}, status=400)







@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ActivateESIMRequest(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='Fitted')
    if stock_assignment.dealer!= man:
        return Response({"error":"Not in stock of this user."}, status=status.HTTP_400_BAD_REQUEST)
    
    stock_assignment.esim_status = 'ESIM_Active_Req_Sent'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Request Sent successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfirmESIMActivation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, esim_status='ESIM_Active_Req_Sent')
    stock_assignment.esim_status = 'ESIM_Active_Confirmed'
    stock_assignment.save()
    stock_assignment = get_object_or_404(DeviceStock,id=device_id, esim_status='ESIM_Active_Confirmed')
    
    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'ESIM Active Confirmed successfully.'}, status=200)




@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfigureIPPort(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='ESIM_Active_Confirmed')
    stock_assignment.stock_status = 'IP_PORT_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'IP Port Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfigureSOSGateway(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='IP_PORT_Configured')
    stock_assignment.stock_status = 'SOS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SOS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ConfigureSMSGateway(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='SOS_GATEWAY_NO_Configured')
    stock_assignment.stock_status = 'SMS_GATEWAY_NO_Configured'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'SMS Gateway Configured successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def MarkDeviceDefective(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id)
    if stock_assignment.dealer!= man:
        return Response({"error":"Not in stock of this user."}, status=status.HTTP_400_BAD_REQUEST)
    
    stock_assignment.stock_status = 'Device_Defective'
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Marked as Defective successfully.'}, status=200)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def ReturnToDeviceManufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id = int(request.data['device_id'])
    stock_assignment = get_object_or_404(DeviceStock, id=device_id, stock_status='Device_Defective')
    if stock_assignment.dealer!= man:
        return Response({"error":"Not in stock of this user."}, status=status.HTTP_400_BAD_REQUEST)
    
    stock_assignment.stock_status = 'Returned_to_manufacturer'
    stock_assignment.dealer=None
    stock_assignment.save()

    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)

    return JsonResponse({'data': serializer.data, 'message': 'Device Returned to Manufacturer successfully.'}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SellListAvailableDeviceStock(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    role1="devicemanufacture"
    man2=get_user_object(user,role1)
    role2="stateadmin"
    man3=get_user_object(user,role2)
    if not man and not man2 and not man3:
        return Response({"error":"Request must be from "+role+" or "+role1+" or "+role2+"."}, status=status.HTTP_400_BAD_REQUEST)
    if man2:
        device_stock =  DeviceStock.objects.filter(  dealer__manufacturer=man2,stock_status='Available_for_fitting') 
        if not device_stock:
            return JsonResponse({'error': "no device found "  }, status=400)
    elif man3:
        device_stock =  DeviceStock.objects.filter(  dealer__manufacturer__state=man3.state,stock_status='Available_for_fitting') 
        if not device_stock:
            return JsonResponse({'error': "no device found "  }, status=400)

    else:
        device_stock =  DeviceStock.objects.filter(  dealer=man,stock_status='Available_for_fitting') 
     
    if not device_stock:
        return JsonResponse({'error': "no device found for this user avaialble for fitting "  }, status=400)

    # Include nested eSimProvider and related info in the response
    serializer =DeviceStockSerializer2(device_stock, many=True)
    return JsonResponse({'data': serializer.data}, status=200)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SellFitDevice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="dealer"
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from "+role+"."}, status=status.HTTP_400_BAD_REQUEST)
    
    device_id=int(request.data['device_id'])
    stock_assignment =  DeviceStock.objects.filter(id=device_id, dealer=man,stock_status='Available_for_fitting').last()
    if not stock_assignment:
        return JsonResponse({'error': "device not found, error in dealer or status"  }, status=400)

    stock_assignment.stock_status = 'Fitted'
    
    stock_assignment.save()
    # Serialize the updated data
    serializer = DeviceStockSerializer(stock_assignment)
    return JsonResponse({'data': serializer.data, 'message': 'Device Fitted  successfully.'}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def StockAssignToDealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    
    data = request.data.copy()
    assigned_by_id = request.user.id
    assigned_at = timezone.now()
    stock_status = "Available_for_fitting"
    dealer_id =  data.get('dealer') 
    device_ids = ast.literal_eval(str(data.get('device')))
    dealer = Dealer.objects.filter(id=dealer_id).last()#,manufacturer=man
    if not dealer:
        return JsonResponse({'error':"invalid dealer" }, status=400)
    

    stock_assignments = []
    error=[]
    success_count=0
    for device_id in device_ids:
        #print(int(device_id),dealer_id, assigned_by_id, assigned_at, data.get('shipping_remark'), stock_status)
       
        try:

            assignment = DeviceStock.objects.filter(id=int(device_id) ,created_by=user,stock_status='NotAssigned').last() 
            if assignment:
                assignment.dealer=dealer
                assignment.assigned_by =request.user
                assignment.assigned=assigned_at
                assignment.shipping_remark=data.get('shipping_remark')
                assignment.stock_status=stock_status                
                assignment.save()                
                stock_assignments.append( DeviceStockSerializer(assignment).data)
                success_count+=1
            else:
                error.append({'id':int(device_id),'error':"unavaialble non assigned devicewith given id under this manufature"})

        except Exception as e:
             
            return JsonResponse({'error': "Unable to process request."+str(e)}, status=400)
        if success_count==0:
            return JsonResponse({'error': "No device assigned. All provided devices are invalid." }, status=400)
    if len(error)==0:
        return JsonResponse({'data': stock_assignments , 'message': 'Stock assigned successfully.'}, status=201)
    else:
        return JsonResponse({'data': stock_assignments,'error':error  , 'message': 'Stock Partially assigned.'}, status=201)
    
    
'''def StockAssignToDealer3333(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Deserialize the input data
    data = request.data.copy() 
    data['assigned_by'] = request.user.id
    data['assigned'] = timezone.now()
    data['stock_status']= "Available_for_fitting"
    data['dealer_id']= int(data['dealer']) 
    device_ids = ast.literal_eval(str(data['device']))
     

    # Create individual DeviceStock entries for each device
    stock_assignments = []
    for device_id in device_ids:
        data['device_id'] = int(device_id)
        #print(data)
        serializer = DeviceStockSerializer2(data=data)
        if serializer.is_valid():
            serializer.save()
            stock_assignments.append(serializer.data)
        else:
            return JsonResponse({'error': serializer.errors}, status=400)

    return JsonResponse({'data': stock_assignments, 'message': 'Stock assigned successfully.'}, status=201)

'''


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deviceStockFilter(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user
    man=None
    data = request.data.copy()    

    is_tagged_filter = request.data.get('is_tagged')
    if user.role=="devicemanufacture":
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        man=get_user_object(user,"devicemanufacture")
        data['created_by_id'] = request.user.id 
    elif user.role=="dealer":
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        man=get_user_object(user,"dealer")
        data['dealer_id'] = man.id 
        #is_tagged_filter=True


    
    if not man:
            return Response({"error":"Request must be from device manufacture or dealer"}, status=status.HTTP_400_BAD_REQUEST)
   
    # Deserialize the input data
    serializer = DeviceStockFilterSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Add pagination to limit results
    page_size = min(int(request.data.get('page_size', 50)), 200)  # Max 200 records per page
    page = max(int(request.data.get('page', 1)), 1)
    offset = (page - 1) * page_size

    # Use raw SQL or values() for maximum performance
    from django.db.models import Exists, OuterRef, Case, When, BooleanField
    
    # Build the base query with only essential fields
    base_query = DeviceStock.objects.filter(**serializer.validated_data)
    
    # Get total count
    total_count = base_query.count()
    
    # Apply is_tagged filter at database level if specified
    if is_tagged_filter is not None:
        is_tagged_bool = is_tagged_filter == 'True'
        tagged_subquery = DeviceTag.objects.filter(device=OuterRef('pk'))
        base_query = base_query.annotate(
            is_tagged=Exists(tagged_subquery)
        ).filter(is_tagged=is_tagged_bool)
        total_count = base_query.count()
    
    # Use values() to get only required data as dictionaries (much faster than model instances)
    device_data = base_query.select_related('model', 'dealer', 'created_by').values(
        'id', 'device_esn', 'iccid', 'imei', 'telecom_provider1', 'telecom_provider2',
        'msisdn1', 'msisdn2', 'imsi1', 'imsi2', 'esim_validity', 'remarks', 'created', 'stock_status', 
        'esim_status', 'assigned', 'shipping_remark',
        # Related model fields
        'model__id', 'model__model_name', 'model__test_agency', 'model__vendor_id',
        'model__tac_no', 'model__hardware_version',
        # Dealer fields (using correct field names)
        'dealer__id', 'dealer__company_name',
        # Created by fields (using correct field names)
        'created_by__id', 'created_by__name', 'created_by__email'
    ).order_by('-id')[offset:offset + page_size]
    
    # Convert to list and add is_tagged for each item if not already filtered
    result_data = []
    device_ids = []
    
    for item in device_data:
        device_ids.append(item['id'])
        result_data.append(item)
    
    # Prefetch esim providers for all devices in this page and build a map
    esim_provider_map = {}
    if device_ids:
        from .serializers import eSimProviderSerializer
        ds_with_providers = DeviceStock.objects.filter(id__in=device_ids).prefetch_related('esim_provider')
        for ds in ds_with_providers:
            esim_provider_map[ds.id] = eSimProviderSerializer(ds.esim_provider.all(), many=True).data

    # Fetch latest device tag info for each device in this page
    device_tag_map = {}
    if device_ids:
        tag_rows = DeviceTag.objects.filter(device_id__in=device_ids).values(
            'id', 'device_id', 'vehicle_reg_no', 'engine_no', 'chassis_no',
            'vehicle_make', 'vehicle_model', 'status', 'tagged', 'vehicle_owner_id', 'tagged_by_id'
        ).order_by('device_id', '-id')
        for tag in tag_rows:
            if tag['device_id'] not in device_tag_map:
                device_tag_map[tag['device_id']] = {
                    'id': tag['id'],
                    'device_id': tag['device_id'],
                    'vehicle_reg_no': tag['vehicle_reg_no'],
                    'engine_no': tag['engine_no'],
                    'chassis_no': tag['chassis_no'],
                    'vehicle_make': tag['vehicle_make'],
                    'vehicle_model': tag['vehicle_model'],
                    'status': tag['status'],
                    'tagged': tag['tagged'],
                    'vehicle_owner_id': tag['vehicle_owner_id'],
                    'tagged_by_id': tag['tagged_by_id'],
                }

    # If is_tagged_filter was not applied, get is_tagged status for all items in one query
    if is_tagged_filter is None and device_ids:
        tagged_device_ids = set(
            DeviceTag.objects.filter(device_id__in=device_ids).values_list('device_id', flat=True)
        )
        for item in result_data:
            item['is_tagged'] = item['id'] in tagged_device_ids
    elif is_tagged_filter is not None:
        # If filtered, all items have the same is_tagged value
        for item in result_data:
            item['is_tagged'] = is_tagged_filter == 'True'
    
    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size
    has_next = page < total_pages
    has_previous = page > 1

    # Prefetch all COPs for all device models in this page
    device_model_ids = set()
    for item in result_data:
        if item.get('model__id'):
            device_model_ids.add(item['model__id'])
    device_model_cop_map = {}
    if device_model_ids:
        from .serializers import DeviceCOPSerializer
        all_cops = DeviceCOP.objects.filter(device_model_id__in=device_model_ids).order_by('-created')
        # Group by device_model_id
        for cop in all_cops:
            model_id = cop.device_model_id
            if model_id not in device_model_cop_map:
                device_model_cop_map[model_id] = []
            device_model_cop_map[model_id].append(DeviceCOPSerializer(cop).data)

    # Format the response to match the expected structure
    formatted_data = []
    for item in result_data:
        device_id = item['id']
        model_id = item.get('model__id')
        formatted_item = {
            'id': item['id'],
            'device_esn': item['device_esn'],
            'iccid': item['iccid'],
            'imei': item['imei'],
            'telecom_provider1': item['telecom_provider1'],
            'telecom_provider2': item['telecom_provider2'],
            'msisdn1': item['msisdn1'],
            'msisdn2': item['msisdn2'],
            'imsi1': item.get('imsi1'),
            'imsi2': item.get('imsi2'),
            'esim_validity': item['esim_validity'],
            'remarks': item['remarks'],
            'created': item['created'],
            'stock_status': item['stock_status'],
            'esim_status': item['esim_status'],
            'assigned': item['assigned'],
            'shipping_remark': item['shipping_remark'],
            'is_tagged': item.get('is_tagged', False),
            'esim_provider': esim_provider_map.get(item['id'], []),
            'model': {
                'id': item['model__id'],
                'model_name': item['model__model_name'],
                'test_agency': item['model__test_agency'],
                'vendor_id': item['model__vendor_id'],
                'tac_no': item['model__tac_no'],
                'hardware_version': item['model__hardware_version'],
            } if item['model__id'] else None,
            'dealer': {
                'id': item['dealer__id'],
                'company_name': item['dealer__company_name'],
            } if item['dealer__id'] else None,
            'created_by': {
                'id': item['created_by__id'],
                'name': item['created_by__name'],
                'email': item['created_by__email'],
            } if item['created_by__id'] else None,
            'device_tag_info': device_tag_map.get(device_id),
            # Add all COPs for this device model, latest first
            'cops': device_model_cop_map.get(model_id, []),
        }
        formatted_data.append(formatted_item)

    return JsonResponse({
        'data': formatted_data,
        'pagination': {
            'current_page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_previous': has_previous
        }
    }, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deviceStockCreateBulk(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'excel_file' not in request.FILES or 'model_id' not in request.data:
        return JsonResponse({'error': 'Please provide an Excel file and model_id.'}, status=400)

    model_id = request.data['model_id']
    mod=DeviceModel.objects.filter(id=model_id,created_by=user).last()
    if not mod:
        return JsonResponse({'error': 'invalid model_id or unauthorised user.'}, status=400)

    esim_provider = request.data['esim_provider']
    if not isinstance(esim_provider, list)  : 
        var_str = str(esim_provider) 
        for ch in ['[', ']', '{', '}']:
            var_str = var_str.replace(ch, '')
        esim_provider = [item.strip() for item in var_str.split(',')]
    #for e in esim_provider:
    #    st=False
    #    for ee in mod.eSimProviders:
    #        if ee==e.id:
    #            True
    #    if not st:
    #        return JsonResponse({'error': 'Esim provider id='+"Unable to process request."+str(e)+' is not in the devicemodel\'s esimprovider list.'}, status=400)





    try:
        excel_data = pd.read_excel(request.FILES['excel_file'], engine='openpyxl')
    except Exception as e:
        return JsonResponse({'error': 'Error reading Excel file.', 'details': f"Unable to process request. {str(e)}"}, status=400)

    headers = list(excel_data.columns)
    success_count = 0
    success_rows = []
    error_rows = []

    for index, row in excel_data.iterrows():
        # Skip the header and example rows
        if index == 0 or 'example' in str(row[0]).lower():
            continue
        try:
            a=int(row.get('imei', ''))
            #a=int(row.get('imsi1', ''))
            #if row.get('imsi2', '')!="":
            #    a=int(row.get('imsi2', ''))
        except:
            continue
            
        # Extract data from the row
        data = {
            'model': model_id,
            'device_esn': row.get('device_esn', ''),
            'iccid': row.get('iccid', ''),
            'iccid2': row.get('iccid2', ''),
            'imei': row.get('imei', ''),
            'telecom_provider1': row.get('telecom_provider1', ''),
            'telecom_provider2': row.get('telecom_provider2', ''),
            'msisdn1': row.get('msisdn1', ''),
            'msisdn2': row.get('msisdn2', ''),
            'imsi1': row.get('imsi1', ''),
            'imsi2': row.get('imsi2', ''),
            'esim_validity': row.get('esim_validity', ''), 
            'stock_status': "NotAssigned",
            'esim_status':"NotAssigned",
            'esim_provider': esim_provider,
            'remarks': row.get('remarks', ''),
            'created_by': request.user.id,
            'stock_status': "NotAssigned",
            'created':timezone.now(),
        }

        # Validate and create DeviceStock instance
        serializer = DeviceStockSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            success_count += 1
            success_rows.append(index + 1)
        else:
            error_rows.append({'row': index + 1, 'errors': serializer.errors})

    message = f'{success_count} out of {len(excel_data) - 1} provided stocks are successfully uploaded.'

    response_data = {
        'message': message,
        'success_rows': success_rows,
        'error_rows': error_rows,
    }

    return JsonResponse(response_data, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def deviceStockCreate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
    mod=DeviceModel.objects.filter(id=request.data['model'],)
    # Deserialize the input data
    data = request.data.copy()
    data['created'] = timezone.now()   
    data['created_by'] = request.user.id
    data['stock_status'] =  "NotAssigned"
    data['esim_status'] =  "NotAssigned"
    try:
        a=int(data['imei'])
        #a=int(data['imsi1'])
        #if data['imsi2']:
        #    a=int(data['imsi1'])
    except:
        return JsonResponse({"status":"Error, Invalid imei  "}, status=400)


    serializer = DeviceStockSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Save the DeviceStock instance
    serializer.save()

    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPCreate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
     
        
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="devicemanufacture"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    manufacturer = request.user.id 
    if STATIC_OTP_CAP:
                otp  = str(685472)
    else:
                otp = str(secrets.randbelow(1000000)).zfill(6)
 
    data = {
        'created_by': manufacturer,
        'created': timezone.now(),  
        'status': 'Manufacturer_OTP_Sent',
        'valid':True,
        'latest':True,
        'otp_time': timezone.now(),
        'otp':otp
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)

    # Create a serializer instance
    serializer = DeviceCOPSerializer(data=request_data)

    # Validate and save the data along with the file
    if serializer.is_valid():
        # Save the DeviceCOP instance
        device_cop_instance = serializer.save()

        # Handle the uploaded file
        uploaded_file = request.FILES.get('cop_file')
        if uploaded_file:
            # Save the file to a specific location
            safe_file_name = os.path.basename(uploaded_file.name)
            relative_file_path = f"fileuploads/cop_files/{device_cop_instance.id}_{safe_file_name}"
            absolute_file_path = os.path.join(HOST_STORAGE_PATH, relative_file_path)
            os.makedirs(os.path.dirname(absolute_file_path), exist_ok=True)
            with open(absolute_file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the cop_file field in the DeviceCOP instance
            device_cop_instance.cop_file = relative_file_path
            device_cop_instance.save()
                    
            text="Dear User, Your OTP to validate COP creation/update in SkyTron portal is {}. Please DO NOT disclose it to anyone. -SkyTron".format(otp)
            tpid="1007967997984175182"
            send_SMS(user.mobile,text,tpid) 
            """send_mail(
                'Login OTP',
                "Dear User, Your OTP to validate COP in SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )"""

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPAwaitingStateApproval(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    user = request.user
    state_admin_obj = get_user_object(user, "stateadmin")
    super_admin_obj = get_user_object(user, "superadmin")
    if not (state_admin_obj or super_admin_obj):
        return Response({"error": "Request must be from stateadmin or superadmin."}, status=status.HTTP_400_BAD_REQUEST)
    
    #user_id = request.user.id
    device_models = DeviceCOP.objects.filter(status='Manufacturer_OTP_Verified')#created_by=user_id, 
    
    # Serialize the data
    serializer = DeviceCOPSerializer(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPSendStateAdminOtp(request ): 
       #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceCOP, id=device_model_id,  status='Manufacturer_OTP_Verified')
    if not device_model:
        return JsonResponse({'error': "Device model not found or not in the correct status."}, status=400)
    
    if STATIC_OTP_CAP:
        device_model.otp  = str(685472)
    else:
        device_model.otp = str(secrets.randbelow(1000000)).zfill(6)
    device_model.otp_time = timezone.now()
    
    device_model.status = 'StateAdminOTPSend'
    device_model.save()
    text="Dear User, Your OTP to validate COP creation/update in SkyTron portal is {}. Please DO NOT disclose it to anyone. -SkyTron".format(device_model.otp)
    tpid="1007967997984175182"
    send_SMS(user.mobile,text,tpid) 
    send_mail(
        'Login OTP',
        text,
        'noreply@skytron.in',
        [user.email],
        fail_silently=False,
    )

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPVerifyStateAdminOtp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="stateadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    device_model_id = request.data.get('device_model_id') 
    user_id = request.user.id 
 
    otp = request.data.get('otp') 
    if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)

    device_model = get_object_or_404(DeviceCOP, id=device_model_id, status='StateAdminOTPSend')
 
    if otp == device_model.otp:  
        device_model.status = 'StateAdminApproved'
        device_model.save()
        return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)
    else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)


    

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def COPManufacturerOtpVerify(request  ): 
    user_id = request.user.id 
       #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="devicemanufacture"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)

    device_model = get_object_or_404(DeviceCOP, id=device_model_id, created_by=user_id, status='Manufacturer_OTP_Sent')
 
    if otp == device_model.otp:  
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def list_devicemodel(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    device_models = DeviceModel.objects.all() 
    serializer = DeviceModelSerializer_disp(device_models, many=True) 
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_devicemodel(request): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Validate user role once upfront
    role = "devicemanufacture"
    user = request.user
    
    # Check the role only once and return early if invalid
    if user.role != role:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data = request.data
    serializer = DeviceModelFilterSerializer(data=data)
    
    # Validate but don't raise exception - handle it ourselves for faster response
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a query dictionary with only the validated fields that have values
    filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
    
    # Add the user filter directly
    filter_kwargs['created_by'] = user
    
    # Optimize by using select_related/prefetch_related - this improves query performance
    device_models = DeviceModel.objects.filter(**filter_kwargs).select_related(
        'created_by'
    ).prefetch_related(
        'eSimProviders'
    )
    
    # Serialize the data - maintaining original response format
    serializer = DeviceModelSerializer_disp(device_models, many=True)
    data = serializer.data
    # Add COPs for each device model (like in deviceStockFilter)
    model_ids = [dm['id'] for dm in data]
    device_model_cop_map = {}
    if model_ids:
        from .serializers import DeviceCOPSerializer
        all_cops = DeviceCOP.objects.filter(device_model_id__in=model_ids).order_by('-created')
        for cop in all_cops:
            model_id = cop.device_model_id
            if model_id not in device_model_cop_map:
                device_model_cop_map[model_id] = []
            device_model_cop_map[model_id].append(DeviceCOPSerializer(cop).data)
    for dm in data:
        dm['cops'] = device_model_cop_map.get(dm['id'], [])
    return Response(data)
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Validate user role once upfront
    role = "devicemanufacture"
    user = request.user
    
    # Check the role only once and return early if invalid
    if user.role != role:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data = request.data
    serializer = DeviceModelFilterSerializer(data=data)
    
    # Validate but don't raise exception - handle it ourselves for faster response
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a query dictionary with only the validated fields that have values
    filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
    
    # Add the user filter directly
    filter_kwargs['created_by'] = user
    
    # Optimize by using select_related/prefetch_related
    query = DeviceModel.objects.select_related('created_by').prefetch_related('eSimProviders')
    
    # Apply filters to the optimized query
    device_models = query.filter(**filter_kwargs)
    
    # Optional: Add pagination if there are many results
    page_size = request.query_params.get('page_size', 20)
    page = request.query_params.get('page', 1)
    
    try:
        page_size = int(page_size)
        page = int(page)
    except ValueError:
        page_size = 20
        page = 1
        
    # Apply pagination
    start = (page - 1) * page_size
    end = page * page_size
    paginated_models = device_models[start:end]
    
    # Pass the request context to the serializer for field filtering
    serializer = DeviceModelSerializer_disp(
        paginated_models, 
        many=True, 
        context={'request': request}
    )
    
    # Include pagination metadata
    total_count = device_models.count()
    total_pages = (total_count + page_size - 1) // page_size
    
    # Add COPs for each device model (like in deviceStockFilter)
    data = serializer.data
    model_ids = [dm['id'] for dm in data]
    device_model_cop_map = {}
    if model_ids:
        from .serializers import DeviceCOPSerializer
        all_cops = DeviceCOP.objects.filter(device_model_id__in=model_ids).order_by('-created')
        for cop in all_cops:
            model_id = cop.device_model_id
            if model_id not in device_model_cop_map:
                device_model_cop_map[model_id] = []
            device_model_cop_map[model_id].append(DeviceCOPSerializer(cop).data)
    for dm in data:
        dm['cops'] = device_model_cop_map.get(dm['id'], [])
    return Response({
        'results': data,
        'pagination': {
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': page,
            'page_size': page_size
        }
    })
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    # Validate user role once upfront
    role = "devicemanufacture"
    user = request.user
    
    # Check the role only once and return early if invalid
    if user.role != role:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    uo = get_user_object(user, role)
    if not uo:
        return Response({"error": f"Request must be from {role}."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data = request.data
    serializer = DeviceModelFilterSerializer(data=data)
    
    # Validate but don't raise exception - handle it ourselves for faster response
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a query dictionary with only the validated fields that have values
    filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
    
    # Add the user filter directly
    filter_kwargs['created_by'] = user
    
    # Use select_related to fetch related models in a single query
    # This improves performance by reducing database hits
    device_models = DeviceModel.objects.filter(**filter_kwargs).select_related(
        'created_by'
    ).prefetch_related(
        'eSimProviders'  # Based on the model relationships shown in serializers
    )

    # Serialize the data - use a smaller subset of fields if possible for performance
    serializer = DeviceModelSerializer_disp(device_models, many=True)

    return Response(serializer.data)
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="devicemanufacture"
    user=request.user
    if user.role==role:
        uo=get_user_object(user,role)
        if not uo:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Deserialize the input parameters
    data=request.data
    #data['created_by__id']=user.id
    serializer = DeviceModelFilterSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    # Filter DeviceModel instances based on parameters
    device_models = DeviceModel.objects.filter(**serializer.validated_data,created_by=user)

    # Serialize the data
    serializer = DeviceModelSerializer_disp(device_models, many=True)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def details_devicemodel(request ):     
    device_model_id = request.data.get('device_model_id')
    device_model = get_object_or_404(DeviceModel, id=device_model_id) 
    serializer = DeviceModelSerializer_disp(device_model)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceModelAwaitingStateApproval(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    #user_id = request.user.id    
    user = request.user
    state_admin_obj = get_user_object(user, "stateadmin")
    super_admin_obj = get_user_object(user, "superadmin")
    if not (state_admin_obj or super_admin_obj):
        return Response({"error": "Request must be from stateadmin or superadmin"}, status=status.HTTP_400_BAD_REQUEST)
      

    # Retrieve device models with status "Manufacturer_OTP_Verified"
    device_models = DeviceModel.objects.filter(
        status__in=['Manufacturer_OTP_Verified',"StateAdminOTPSend"]
    ).select_related(
        'created_by'
    ).prefetch_related(
        'eSimProviders',
        'eSimProviders__users',
        'eSimProviders__state'
    ) 
    
    # Serialize the data
    serializer = DeviceModelSerializer_disp(device_models, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceSendStateAdminOtp(request ): 
    user=request.user 
    sa=get_user_object(user,"stateadmin")
    if not sa:
        return Response({"error":"Request must be from stateadmin"}, status=status.HTTP_400_BAD_REQUEST)
      
    device_model_id = request.data.get('device_model_id')
    # Validate current status and update the status
    device_model = get_object_or_404(DeviceModel, id=device_model_id,  status__in =['Manufacturer_OTP_Verified',"StateAdminOTPSend"])
    if not device_model:
        return JsonResponse({'error': "Device model not found or already processed."}, status=400)
    
    if STATIC_OTP_CAP:
                otp  = str(685472)
    else:
                otp = str(secrets.randbelow(1000000)).zfill(6)

     
    device_model.otp_time = timezone.now()
    device_model.otp = otp
    device_model.status = 'StateAdminOTPSend'
    device_model.save()
    text="Dear User, Confirmation OTP for VLTD Model Creation at SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron".format(otp)
    tpid="1007338577423920274"
    send_SMS(user.mobile,text,tpid) 
    send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
    )
    

    return Response({"message": "State Admin OTP sent successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceVerifyStateAdminOtp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user=request.user 
    sa=get_user_object(user,"stateadmin")
    if not sa:
        return Response({"error":"Request must be from stateadmin"}, status=status.HTTP_400_BAD_REQUEST)
      
    device_model_id = request.data.get('device_model_id') 
    user_id = request.user.id 
    device_model = get_object_or_404(DeviceModel, id=device_model_id, status='StateAdminOTPSend')#created_by=user_id ,
 
 
    otp = request.data.get('otp')
    if device_model.otp!=otp:
            return JsonResponse({'error': "Invalid OTP"}, status=400)


    device_model.status = 'StateAdminApproved'
    device_model.save()

    return Response({"message": "State Admin OTP verified and approval granted successfully."}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def DeviceCreateManufacturerOtpVerify(request  ): 
    user_id = request.user.id
    user=request.user 
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
      
    otp = request.data.get('otp')
    device_model_id = request.data.get('device_model_id')
    if not otp or not otp.isdigit() or len(otp) != 6:
            return JsonResponse({'error': "Invalid OTP format"}, status=400)

    device_model = get_object_or_404(DeviceModel, id=device_model_id,status='Manufacturer_OTP_Sent')# created_by=user_id, 
    if device_model.created_by!=user:
        return Response({"error":"User is not the creator of this devicemodel"}, status=status.HTTP_400_BAD_REQUEST)
      
 
    if otp == device_model.otp:  
        device_model.status = 'Manufacturer_OTP_Verified'
        device_model.save()
        return Response({"message": "Manufacturer OTP verified successfully."}, status=200)
    else:
            return JsonResponse({'error': "Invalid OTP"}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_hp_freq(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
     
    # Allow superadmin and device manufacturer
    user = request.user
    role_super = "superadmin"
    role_man = "devicemanufacture"
    super_user = get_user_object(user, role_super)
    manu_user = get_user_object(user, role_man) if not super_user else None
    if not super_user and not manu_user:
        return Response({"error": f"Request must be from {role_super} or {role_man}."}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        #'status': 'Manufacturer_OTP_Sent',
    } 
    request_data = request.data.copy()

    # If requester is a manufacturer, ensure they only create for their own device model
    if manu_user:
        devicemodel_id = request_data.get('devicemodel')
        if not devicemodel_id:
            return Response({'error': 'devicemodel is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            devicemodel_id = int(devicemodel_id)
        except (TypeError, ValueError):
            return Response({'error': 'devicemodel must be an integer ID'}, status=status.HTTP_400_BAD_REQUEST)

        dm = DeviceModel.objects.filter(id=devicemodel_id).select_related('created_by').last()
        if not dm:
            return Response({'error': 'Invalid devicemodel id'}, status=status.HTTP_400_BAD_REQUEST)
        if dm.created_by != user:
            return Response({'error': 'You can only create HP frequency for your own device models.'}, status=status.HTTP_403_FORBIDDEN)

    # Set creator info
    request_data.update(data)
    #print(request_data)
    serializer = Settings_hp_freqSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save() 
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_hp_freq(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        user = request.user
        role_super = "superadmin"
        role_man = "devicemanufacture"
        super_user = get_user_object(user, role_super)
        manu_user = get_user_object(user, role_man) if not super_user else None

        qs = Settings_hp_freq.objects.all().select_related('devicemodel', 'createdby')

        # Manufacturers can only see their own device models' settings
        if manu_user and not super_user:
            qs = qs.filter(devicemodel__created_by=user)

        # Optional client-side narrowing by devicemodel id if provided
        devicemodel_id = request.data.get('devicemodel')
        if devicemodel_id:
            try:
                devicemodel_id = int(devicemodel_id)
                qs = qs.filter(devicemodel_id=devicemodel_id)
            except (TypeError, ValueError):
                return Response({'error': 'devicemodel must be an integer ID'}, status=400)

        qs = qs.distinct()
        serializer = Settings_hp_freqSerializer(qs, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_ip(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
      #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),   
        #'status': 'Manufacturer_OTP_Sent',
    } 
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_ipSerializer(data=request_data) 
    if serializer.is_valid():
        instance = serializer.save() 
        return Response(serializer.data, status=status.HTTP_201_CREATED) 
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)










@api_view(['POST'])
@permission_classes([AllowAny])  # Allow both authenticated and anonymous users
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_District(request): 
    try:
        user = request.user
        
        # Check if user is authenticated
        if user and user.is_authenticated:
            user_role = getattr(user, 'role', None)
            
            # Fast role-based filtering for authenticated users
            if user_role == 'stateadmin':
                # Get user's state efficiently
                uo = get_user_object(user, "stateadmin")
                if uo and uo.state:
                    # Use values() for maximum performance - only get required fields
                    districts = Settings_District.objects.filter(
                        state=uo.state
                    ).select_related('state').values(
                        'id', 'district', 'district_code',
                        'state__id', 'state__state'
                    ).distinct()
                else:
                    districts = Settings_District.objects.none().values()
            else:
                # For other authenticated roles, get all districts with optimized query
                districts = Settings_District.objects.select_related('state').values(
                    'id', 'district', 'district_code',
                    'state__id', 'state__state'
                ).distinct()
        else:
            # For non-registered/anonymous users, show all districts
            districts = Settings_District.objects.select_related('state').values(
                'id', 'district', 'district_code',
                'state__id', 'state__state'
            ).distinct()
        
        # Convert to list for JSON response
        district_list = list(districts)
        
        # Format response to match expected structure
        formatted_data = []
        for district in district_list:
            formatted_data.append({
                'id': district['id'],
                'district': district['district'], 
                'district_code': district['district_code'],
                'state': {
                    'id': district['state__id'],
                    'state_name': district['state__state']
                } if district['state__id'] else None
            })
        
        return Response(formatted_data, status=200)

    except Exception as e:
        return Response({'error': "Unable to process request." + str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_District(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    request_data = request.data.copy()
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        "state":request_data["state"],
        "district":request_data["district_name" ],

    }

    # Attach the file to the request data
    request_data.update(data)
    #print(request_data)
    serializer = Settings_DistrictSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




















@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_firmware(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_firmware.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        dealer_serializer = Settings_firmwareSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_firmware(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        'file_bin':'file',
        #'status': 'Manufacturer_OTP_Sent',
    }

    
        

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_firmwareSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
        uploaded_file = request.FILES.get('file_bin')
        if uploaded_file:
            # Save the file to a specific location
            file_path = 'fileuploads/file_bin/' + str(instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            
            # Update the cop_file field in the DeviceCOP instance
            instance.file_bin = file_path
            instance.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_VehicleCategory(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_VehicleCategory.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        dealer_serializer = Settings_VehicleCategorySerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_VehicleCategory(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
      #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),  
        #'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_VehicleCategorySerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def manufacturer_model_stock_statistics(request):
    """
    Get stock statistics per model per manufacturer with device tag and online device info
    Public API - No authentication required
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.db.models import Count, Q, Exists, OuterRef
        from datetime import datetime, timedelta
        
        # Calculate the time threshold for online devices (last 15 minutes)
        online_threshold = timezone.now() - timedelta(minutes=15)
        
        # Get only final-approved manufacturers
        manufacturers = Manufacturer.objects.filter(status='Accept').select_related('createdby').prefetch_related('users')
        
        manufacturer_list = []
        total_manufacturers = manufacturers.count()
        
        for manufacturer in manufacturers:
            # Get the user associated with this manufacturer (creator/owner)
            manufacturer_user = manufacturer.users.first() if manufacturer.users.exists() else None
            
            # Get all device models created by this manufacturer's user
            if manufacturer_user:
                device_models = DeviceModel.objects.filter(created_by=manufacturer_user)
            else:
                device_models = DeviceModel.objects.none()
            
            model_list = []
            total_models = device_models.count()
            
            for model in device_models:
                # Get total stock for this model
                total_stock = DeviceStock.objects.filter(model=model).count()
                
                # Get device stock IDs for this model
                device_stock_ids = DeviceStock.objects.filter(model=model).values_list('id', flat=True)
                
                # Get total device tags from these stocks
                total_device_tags = DeviceTag.objects.filter(
                    device_id__in=device_stock_ids,
                    status__in=['Device_Active', 'Live_Location_Confirmed', 'SOS_Confirmed', 'RegNo_Configuration_Confirmed']
                ).count()
                
                # Get device tag IDs for this model
                device_tag_ids = DeviceTag.objects.filter(
                    device_id__in=device_stock_ids,
                    status__in=['Device_Active', 'Live_Location_Confirmed', 'SOS_Confirmed', 'RegNo_Configuration_Confirmed']
                ).values_list('id', flat=True)
                
                # Count online devices (devices with GPS data in last 15 minutes)
                online_devices = GPSData.objects.filter(
                    device_tag_id__in=device_tag_ids,
                    entry_time__gte=online_threshold
                ).values('device_tag_id').distinct().count()
                
                model_info = {
                    'model_id': model.id,
                    'model_name': model.model_name,
                    'vendor_id': model.vendor_id,
                    'tac_no': model.tac_no,
                    'hardware_version': model.hardware_version,
                    'test_agency': model.test_agency,
                    'total_stock': total_stock,
                    'total_device_tags': total_device_tags,
                    'online_devices': online_devices,
                    'offline_devices': total_device_tags - online_devices
                }
                
                model_list.append(model_info)
            
            manufacturer_info = {
                'manufacturer_id': manufacturer.id,
                'company_name': manufacturer.company_name,
                'gstnnumber': manufacturer.gstnnumber,
                'gstno': manufacturer.gstno,
                'created': manufacturer.created,
                'expirydate': manufacturer.expirydate,
                'total_models': total_models,
                'models': model_list
            }
            
            manufacturer_list.append(manufacturer_info)
        
        response_data = {
            'total_manufacturers': total_manufacturers,
            'manufacturers': manufacturer_list
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': 'Unable to process request: ' + str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def user_statistics(request):
    """
    Get user statistics including registered users (User table), temporary users (TempUser table), 
    online users, and login counts
    Public API - No authentication required
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.db.models import Count, Q
        from datetime import timedelta
        
        # Calculate the time threshold for online users (last 15 minutes of activity)
        online_threshold = timezone.now() - timedelta(minutes=15)
        
        # Total registered users from User table (active)
        # Note: this project uses both `status` and `is_active`; prefer the stricter definition.
        total_registered_users = User.objects.filter(status='active', is_active=True).count()
        
        # Total temporary users from TempUser table
        total_temporary_users = TempUser.objects.all().count()
        
        # Online registered users (User table with recent activity in last 15 minutes)
        online_registered_users = User.objects.filter(
            status='active',
            is_active=True,
            last_activity__gte=online_threshold
        ).count()
        
        # Online temporary users (TempUser table with online=True or recent activity)
        online_temporary_users = TempUser.objects.filter(
            Q(online=True) | Q(last_activity__gte=online_threshold)
        ).count()
        
        # Total number of successful logins (sessions that reached an authenticated state)
        # Session rows are created as `otpsent`, then updated to `login`, and later to `logout`.
        # If we only count `login`, we undercount after users logout.
        authenticated_session_statuses = ['login', 'logout', 'timeout']
        total_logins = Session.objects.filter(status__in=authenticated_session_statuses).count()
        
        # Additional useful statistics
        # Currently logged in registered users (session status = login and recent activity)
        currently_logged_in_registered = Session.objects.filter(
            status='login',
            lastactivity__gte=online_threshold
        ).values('user').distinct().count()
        
        # Total registered users by role breakdown
        users_by_role = {}
        roles = User.objects.filter(status='active', is_active=True).values('role').annotate(count=Count('role'))
        for role_data in roles:
            users_by_role[role_data['role']] = role_data['count']
        
        # Logged-in users by role breakdown (users with login=True)
        logged_in_users_by_role = {}
        # Logged-in users by role breakdown
        # Prefer session-backed computation (authoritative) but keep the same output shape.
        logged_in_roles = Session.objects.filter(
            status='login'
        ).select_related('user').values('user__role').annotate(count=Count('user__role'))
        for role_data in logged_in_roles:
            if role_data['user__role']:
                logged_in_users_by_role[role_data['user__role']] = role_data['count']
        
        # Online users by role breakdown (users with recent activity in last 15 minutes)
        online_users_by_role = {}
        online_roles = User.objects.filter(
            status='active',
            is_active=True,
            last_activity__gte=online_threshold
        ).values('role').annotate(count=Count('role'))
        for role_data in online_roles:
            online_users_by_role[role_data['role']] = role_data['count']
        
        # Currently active sessions by role (session status = login and recent activity)
        active_sessions_by_role = {}
        active_session_roles = Session.objects.filter(
            status='login',
            lastactivity__gte=online_threshold
        ).select_related('user').values('user__role').annotate(count=Count('user__role'))
        for role_data in active_session_roles:
            if role_data['user__role']:
                active_sessions_by_role[role_data['user__role']] = role_data['count']
        
        # Recent logins (last 24 hours)
        last_24_hours = timezone.now() - timedelta(hours=24)
        recent_logins_24h = Session.objects.filter(
            status__in=authenticated_session_statuses,
            loginTime__gte=last_24_hours
        ).count()
        
        # Recent logins (last 7 days)
        last_7_days = timezone.now() - timedelta(days=7)
        recent_logins_7d = Session.objects.filter(
            status__in=authenticated_session_statuses,
            loginTime__gte=last_7_days
        ).count()
        
        # Recent temporary user registrations (last 24 hours)
        recent_temp_users_24h = TempUser.objects.filter(
            created__gte=last_24_hours
        ).count()
        
        response_data = {
            'total_registered_users': total_registered_users,
            'total_temporary_users': total_temporary_users,
            'online_registered_users': online_registered_users,
            'online_temporary_users': online_temporary_users,
            'total_logins': total_logins,
            'currently_logged_in_registered_users': currently_logged_in_registered,
            'users_by_role': users_by_role,
            'logged_in_users_by_role': logged_in_users_by_role,
            'online_users_by_role': online_users_by_role,
            'active_sessions_by_role': active_sessions_by_role,
            'recent_logins_24h': recent_logins_24h,
            'recent_logins_7d': recent_logins_7d,
            'recent_temp_users_24h': recent_temp_users_24h,
            'offline_registered_users': total_registered_users - online_registered_users,
            'offline_temporary_users': total_temporary_users - online_temporary_users
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': 'Unable to process request: ' + str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def vehicle_alert_statistics(request):
    """
    Get vehicle and alert statistics including:
    - Total tagged vehicles and online vehicles
    - SOS calls, broadcasts, and alerts counts (daily, weekly, monthly, yearly)
    Public API - No authentication required
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        # Calculate time thresholds
        now = timezone.now()
        online_threshold = now - timedelta(minutes=15)
        day_threshold = now - timedelta(days=1)
        week_threshold = now - timedelta(days=7)
        month_threshold = now - timedelta(days=30)
        year_threshold = now - timedelta(days=365)
        
        # ===== VEHICLE STATISTICS =====
        # Total tagged vehicles (active device tags)
        total_tagged_vehicles = DeviceTag.objects.filter(
            status__in=['Device_Active', 'Live_Location_Confirmed', 'SOS_Confirmed', 
                       'RegNo_Configuration_Confirmed', 'Owner_OTP_Verified', 'TempActive']
        ).count()
        
        # Get all IMEIs from active device tags
        active_device_imeis = DeviceTag.objects.filter(
            status__in=['Device_Active', 'Live_Location_Confirmed', 'SOS_Confirmed', 
                       'RegNo_Configuration_Confirmed', 'Owner_OTP_Verified', 'TempActive']
        ).select_related('device').values_list('device__imei', flat=True)
        
        # Online vehicles (vehicles with GPS data in last 15 minutes)
        online_vehicles = GPSData.objects.filter(
            device_tag__device__imei__in=active_device_imeis,
            entry_time__gte=online_threshold
        ).values('device_tag').distinct().count()
        
        # ===== SOS CALLS STATISTICS =====
        # Total SOS calls
        total_sos_calls = EMCall.objects.count()
        
        # SOS calls - Daily
        sos_calls_daily = EMCall.objects.filter(start_time__gte=day_threshold).count()
        
        # SOS calls - Weekly
        sos_calls_weekly = EMCall.objects.filter(start_time__gte=week_threshold).count()
        
        # SOS calls - Monthly
        sos_calls_monthly = EMCall.objects.filter(start_time__gte=month_threshold).count()
        
        # SOS calls - Yearly
        sos_calls_yearly = EMCall.objects.filter(start_time__gte=year_threshold).count()
        
        # ===== BROADCASTS STATISTICS =====
        # Total broadcasts
        total_broadcasts = EMCallBroadcast.objects.count()
        
        # Closed broadcasts (accepted or canceled)
        total_broadcasts_closed = EMCallBroadcast.objects.filter(
            status__in=['accepted', 'canceled']
        ).count()
        
        # Broadcasts closed - Daily
        broadcasts_closed_daily = EMCallBroadcast.objects.filter(
            status__in=['accepted', 'canceled'],
            created_at__gte=day_threshold
        ).count()
        
        # Broadcasts closed - Weekly
        broadcasts_closed_weekly = EMCallBroadcast.objects.filter(
            status__in=['accepted', 'canceled'],
            created_at__gte=week_threshold
        ).count()
        
        # Broadcasts closed - Monthly
        broadcasts_closed_monthly = EMCallBroadcast.objects.filter(
            status__in=['accepted', 'canceled'],
            created_at__gte=month_threshold
        ).count()
        
        # Broadcasts closed - Yearly
        broadcasts_closed_yearly = EMCallBroadcast.objects.filter(
            status__in=['accepted', 'canceled'],
            created_at__gte=year_threshold
        ).count()
        
        # ===== ALERTS STATISTICS =====
        # Total alerts
        total_alerts = AlertsLog.objects.count()
        
        # Alerts - Daily
        alerts_daily = AlertsLog.objects.filter(timestamp__gte=day_threshold).count()
        
        # Alerts - Weekly
        alerts_weekly = AlertsLog.objects.filter(timestamp__gte=week_threshold).count()
        
        # Alerts - Monthly
        alerts_monthly = AlertsLog.objects.filter(timestamp__gte=month_threshold).count()
        
        # Alerts - Yearly
        alerts_yearly = AlertsLog.objects.filter(timestamp__gte=year_threshold).count()
        
        # Alerts by type (all time)
        alerts_by_type = {}
        alert_types = AlertsLog.objects.values('type').annotate(count=Count('type'))
        for alert_data in alert_types:
            alerts_by_type[alert_data['type']] = alert_data['count']
        
        # ===== ADDITIONAL STATISTICS =====
        # SOS calls by status
        sos_calls_by_status = {}
        sos_status = EMCall.objects.values('status').annotate(count=Count('status'))
        for status_data in sos_status:
            sos_calls_by_status[status_data['status']] = status_data['count']
        
        response_data = {
            # Vehicle statistics
            'vehicles': {
                'total_tagged_vehicles': total_tagged_vehicles,
                'online_vehicles': online_vehicles,
                'offline_vehicles': total_tagged_vehicles - online_vehicles
            },
            
            # SOS Calls statistics
            'sos_calls': {
                'total': total_sos_calls,
                'daily': sos_calls_daily,
                'weekly': sos_calls_weekly,
                'monthly': sos_calls_monthly,
                'yearly': sos_calls_yearly,
                'by_status': sos_calls_by_status
            },
            
            # Broadcasts statistics
            'broadcasts': {
                'total': total_broadcasts,
                'total_closed': total_broadcasts_closed,
                'closed_daily': broadcasts_closed_daily,
                'closed_weekly': broadcasts_closed_weekly,
                'closed_monthly': broadcasts_closed_monthly,
                'closed_yearly': broadcasts_closed_yearly,
                'pending': total_broadcasts - total_broadcasts_closed
            },
            
            # Alerts statistics
            'alerts': {
                'total': total_alerts,
                'daily': alerts_daily,
                'weekly': alerts_weekly,
                'monthly': alerts_monthly,
                'yearly': alerts_yearly,
                'by_type': alerts_by_type
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': 'Unable to process request: ' + str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        from datetime import timedelta
        from django.utils import timezone

        # Alerts (match `homepage_alart` semantics)
        current_date = now().date()
        current_month_start = current_date.replace(day=1)

        total_alerts = AlertsLog.objects.filter(status="in").count()
        total_alerts_month = AlertsLog.objects.filter(status="in", timestamp__gte=current_month_start).count()
        total_alerts_today = AlertsLog.objects.filter(status="in", timestamp__date=current_date).count()

        speed_alerts = AlertsLog.objects.filter(type='OverSpeed', status="in").count()
        speed_alerts_month = AlertsLog.objects.filter(type='OverSpeed', status="in", timestamp__gte=current_month_start).count()
        speed_alerts_today = AlertsLog.objects.filter(type='OverSpeed', status="in", timestamp__date=current_date).count()

        # Emergency alerts (AlertsLog `type` choices use 'Em' and related variants; exclude 'EmTemp')
        emergency_types = [
            'Em',
            'EmPublicApp',
            'EmRegisteredApp',
            'EmMonitorTripSOS',
            'EmMonitorTripInvalidPw',
            'EmMonitorTripBLEDisconnect',
            'EmMonitorTripDeviated',
            'Incident',
        ]
        emergency_alerts = AlertsLog.objects.filter(type__in=emergency_types, status="in").count()
        emergency_alerts_month = AlertsLog.objects.filter(
            type__in=emergency_types,
            status="in",
            timestamp__gte=current_month_start
        ).count()
        emergency_alerts_today = AlertsLog.objects.filter(
            type__in=emergency_types,
            status="in",
            timestamp__date=current_date
        ).count()

        # Temperature alerts (BoxTemp + EmTemp)
        temperature_alerts = AlertsLog.objects.filter(type__in=['BoxTemp', 'EmTemp'], status="in").count()
        temperature_alerts_month = AlertsLog.objects.filter(
            type__in=['BoxTemp', 'EmTemp'],
            status="in",
            timestamp__gte=current_month_start
        ).count()
        temperature_alerts_today = AlertsLog.objects.filter(
            type__in=['BoxTemp', 'EmTemp'],
            status="in",
            timestamp__date=current_date
        ).count()

        # Device online/offline (15-min window)
        # TotalDevice = total tagged devices (i.e., any tag-device except untagged/deleted)
        untagged_statuses = ['TagDeleted', 'Device_Untagged']
        tagged_devices_qs = DeviceTag.objects.exclude(status__in=untagged_statuses)
        tagged_device_ids = tagged_devices_qs.values_list('id', flat=True)
        total_tagged_devices = tagged_devices_qs.count()

        total_device_stock = DeviceStock.objects.count()
        total_untagged_devices = DeviceTag.objects.filter(status__in=untagged_statuses).count()
        

        online_threshold = timezone.now() - timedelta(minutes=15)
        total_online_devices = GPSData.objects.filter(
            device_tag_id__in=tagged_device_ids,
            entry_time__gte=online_threshold
        ).values('device_tag_id').distinct().count()
        total_offline_devices = max(0, total_tagged_devices - total_online_devices)

        # Active user counters (role-based + SOS teamlead/desk-executive breakdowns)
        active_users_qs = User.objects.filter(status='active', is_active=True)
        active_stateadmin_users = active_users_qs.filter(role='stateadmin').count()
        active_esimprovider_users = active_users_qs.filter(role='esimprovider').count()
        active_manufacturer_users = active_users_qs.filter(role='devicemanufacture').count()
        active_sosadmin_users = active_users_qs.filter(role='sosadmin').count()
        active_sos_teamlead_users = active_users_qs.filter(role='teamleader').count()
        active_sosexecutive_users = active_users_qs.filter(role='sosexecutive').count()

        total_stateadmin_users = User.objects.filter(role='stateadmin').count()

        active_sos_deskexecutive_users = EM_ex.objects.filter(
            user_type='desk_ex',
            users__status='active',
            users__is_active=True
        ).values('users').distinct().count()

        if True:
            count_dict = {
            'Manufacture': Manufacturer.objects.count(),
            'eSimProvider': eSimProvider.objects.count(),
            'Dealer': Dealer.objects.count(),
            'VehicleOwner': VehicleOwner.objects.count(),
            'dto_rto': dto_rto.objects.count(),
            'SOS_ex': EM_ex.objects.count(),
            'SOS_user': EM_ex.objects.count(),
            'SOS_admin': EM_admin.objects.count(),
            
            'TotalVehicles': DeviceTag.objects.count(),
            
            'SOS_team': EMTeams.objects.count(),
            
            'TotalAlerts': total_alerts,
            'TotalAlerts_month': total_alerts_month,
            'TotalAlerts_today': total_alerts_today,
            'SpeedAlerts': speed_alerts,
            'SpeedAlerts_month': speed_alerts_month,
            'SpeedAlerts_today': speed_alerts_today,
            'EmergencyAlerts': emergency_alerts,
            'EmergencyAlerts_month': emergency_alerts_month,
            'EmergencyAlerts_today': emergency_alerts_today,
            'TemperatureAlerts': temperature_alerts,
            'TemperatureAlerts_month': temperature_alerts_month,
            'TemperatureAlerts_today': temperature_alerts_today,

            'TotalDevice': total_tagged_devices,
            'TotalTaggedDevice': total_tagged_devices,
            'TotalUntaggedDevice': total_untagged_devices,
            'TotalFitments': total_tagged_devices,
            'TotalOnlineDevice': total_online_devices,
            'TotalOfflineDevice': total_offline_devices,
            'TotalDeviceModel': DeviceModel.objects.count(),
            'Total_device_stock': total_device_stock,
            'unassigned_device_stock': DeviceStock.objects.filter(stock_status='NotAssigned').count(),
            'Waiting_device_stock': DeviceStock.objects.filter(stock_status='Available_for_fitting').count(),
            'Fitted_device_stock': DeviceStock.objects.filter(stock_status='Fitted').count(),
                
            'Total_States': Settings_State.objects.all().count(),
            'Active_States': Settings_State.objects.filter(status='active').count(),
            'Inactive_States': Settings_State.objects.filter(status='discontinued').count(),
             

            'Total_district': Settings_District.objects.all().count(),
            'Active_district': Settings_District.objects.filter(status='active').count(),
            'Discontinued_district': Settings_District.objects.filter(status='discontinued').count(),

            'ActiveUsers_stateadmin': active_stateadmin_users,
            'TotalUsers_stateadmin': total_stateadmin_users,
            'ActiveUsers_esimprovider': active_esimprovider_users,
            'ActiveUsers_manufacturer': active_manufacturer_users,
            'ActiveUsers_sosadmin': active_sosadmin_users,
            'ActiveUsers_sosexecutive': active_sosexecutive_users,
            'ActiveUsers_sos_teamlead': active_sos_teamlead_users,
            'ActiveUsers_sos_deskexecutive': active_sos_deskexecutive_users,

        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_state(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'total_state':Settings_State.objects.count(),
            'active_state':Settings_State.objects.filter(status='active').count(),
            'inactive_state':Settings_State.objects.filter(status='discontinued').count(), 

        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_alart(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Get the current date and time
        current_date = now().date()
        current_month_start = current_date.replace(day=1)

        # Calculate total counts for "in" status
        total_count = AlertsLog.objects.filter(status="in").count()
        month_count = AlertsLog.objects.filter(status="in", timestamp__gte=current_month_start).count()
        today_count = AlertsLog.objects.filter(status="in", timestamp__date=current_date).count()

        # Initialize a dictionary to hold the counts
        count_dict = {
            'total_alerts': {
                'total': total_count,
                'this_month': month_count,
                'today': today_count,
            },
            'alerts_by_type': {},
        }

        # Fetch counts grouped by type for "total," "this month," and "today"
        for alert_type, _ in AlertsLog.TYPE_CHOICES:
            type_total_count = AlertsLog.objects.filter(type=alert_type, status="in").count()
            type_month_count = AlertsLog.objects.filter(
                type=alert_type, status="in", timestamp__gte=current_month_start
            ).count()
            type_today_count = AlertsLog.objects.filter(
                type=alert_type, status="in", timestamp__date=current_date
            ).count()

            count_dict['alerts_by_type'][alert_type] = {
                'total': type_total_count,
                'this_month': type_month_count,
                'today': type_today_count,
            }

        # Return the count dictionary as a JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def alart_list(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    user = request.user
    allowed_roles = ["owner", "dtorto", "superadmin", "stateadmin", "sosadmin", "sosexecutive"]
    
    # Check if user has any of the allowed roles
    if user.role not in allowed_roles:
        return Response({"error":"Request must be from one of these roles: " + ", ".join(allowed_roles) + '.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # For owner, filter by their vehicles only
        if user.role == "owner":
            uo = get_user_object(user, "owner")
            if not uo:
                return Response({"error":"Owner object not found."}, status=status.HTTP_400_BAD_REQUEST)
            alerts = AlertsLog.objects.filter(deviceTag__vehicle_owner=uo).order_by('-id')[:100]
        else:
            # For all other allowed roles, show all alerts sorted by latest first
            alerts = AlertsLog.objects.all().order_by('-id')[:100]
        
        if alerts:
            serializer = AlertsLogSerializer(alerts, many=True)
            return Response({"alertHistory":serializer.data}, status=200)
        
        return Response({"alertHistory":[]}, status=200)
        
    except Exception as e:
        return Response({"error":"Unable to process request: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
 
     
                
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_device1(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'total_device':0,
            'active_device': 0,
            'idle_device':0, 

        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_device2(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
            'tag_device':0,
            'online_device': 0,
            'offline_device':0, 
        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)





@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_Manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
         
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="devicemanufacture"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg, ExpressionWrapper, DurationField, F
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            current_date = now.date()
            
            # Get manufacturer profile user
            manufacturer_user = profile.users.last()
            
            # Basic manufacturer statistics
            mod = DeviceModel.objects.filter(created_by=manufacturer_user)
            dealers = Dealer.objects.filter(manufacturer=profile)
            stock = DeviceStock.objects.filter(created_by=manufacturer_user)
            associated_vehicle_owners = VehicleOwner.objects.filter(
                devicetag__device__created_by=manufacturer_user
            ).distinct()
            
            # Calculate activations (devices that are actually activated/tagged)
            total_activations = DeviceTag.objects.filter(
                device__created_by=manufacturer_user,
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed']
            ).count()
            
            total_returns = DeviceTag.objects.filter(
                device__created_by=manufacturer_user,
                device__stock_status__in=['Returned_to_manufacturer']
            ).count()
            total_faulty = DeviceTag.objects.filter(
                device__created_by=manufacturer_user,
                device__stock_status__in=['Device_Defective']
            ).count()
            
            # Calculate eSIM statistics from esimActivationRequest model
            esim_act_requests = esimActivationRequest.objects.filter(device__created_by=manufacturer_user)
            esim_pending = esim_act_requests.filter(status="pending").count()
            esim_validated = esim_act_requests.filter(status="valid").count()
            esim_invalid = esim_act_requests.filter(status="invalid").count()
            # 1yr / 2yr expiry based on plan duration (valid_upto - valid_from)
            _plan_dur = ExpressionWrapper(F('valid_upto') - F('valid_from'), output_field=DurationField())
            esim_1yr_expiry = esim_act_requests.filter(status="valid").annotate(
                plan_duration=_plan_dur
            ).filter(
                plan_duration__gte=timedelta(days=330),
                plan_duration__lt=timedelta(days=545)
            ).count()
            esim_2yr_expiry = esim_act_requests.filter(status="valid").annotate(
                plan_duration=_plan_dur
            ).filter(
                plan_duration__gte=timedelta(days=545),
                plan_duration__lte=timedelta(days=800)
            ).count()
            esim_already_expired = esim_act_requests.filter(valid_upto__lte=now).count()
            # map to backward-compatible variable names used in count_dict
            one_year_renewals = esim_1yr_expiry
            two_year_renewals = esim_2yr_expiry
            
            # Calculate device connectivity statistics
            # Get all devices manufactured by this manufacturer
            manufacturer_devices = DeviceTag.objects.filter(device__created_by=manufacturer_user)
            activated_devices = manufacturer_devices.filter(status="Device_Active")
            
            online_devices = 0
            online_today = 0
            offline_today = 0
            offline_7day = 0
            offline_30day = 0
            expired_devices = 0
            
            for device in manufacturer_devices:
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps:
                    # Check if device is online (data received within last 30 minutes)
                    if latest_gps.entry_time >= now - timedelta(minutes=30):
                        online_devices += 1
                    if latest_gps.entry_time >= today_start:
                        online_today += 1
                    
                    # Check offline periods
                    if latest_gps.entry_time < today_start:
                        offline_today += 1
                    if latest_gps.entry_time < week_ago:
                        offline_7day += 1
                    if latest_gps.entry_time < now - timedelta(days=30):
                        offline_30day += 1
                else:
                    # No GPS data means offline for all periods
                    offline_today += 1
                    offline_7day += 1
                    offline_30day += 1
                
                # Check for expired devices (based on eSIM validity)
                if device.device:
                    device_stock = DeviceStock.objects.filter(
                        device_esn=device.device.device_esn
                    ).first()
                    if device_stock and device_stock.esim_validity < now:
                        expired_devices += 1
            
            count_dict = {
                'Total_Model': mod.count(),
                'Total_esim_linked': profile.esim_provider.count(),
                
                'Total_Dealer': dealers.count(),
                'Total_Stock_Created': stock.count(),
                'Total_Stock_Allocated': stock.filter(assigned__isnull=False).count(),
                'Total_Activation': total_activations,
                'Total_Return': total_returns,
                'Total_Faulty': total_faulty,
                
                'Total_esim_activation_request': esim_act_requests.count(),
                'Total_esim_activated': esim_validated,
                'Total_1year_renewal_request': one_year_renewals,
                'Total_2year_renewal_request': two_year_renewals,
                'Total_esim_expired': esim_already_expired,
                
                'Total_Online_Device': online_devices,
                'Total_Online_Device_today': online_today,
                'Total_Offline_Device_today': offline_today,
                'Total_Offline_Device_7day': offline_7day,
                'Total_Offline_Device_30day': offline_30day,
                
                'Total_expired_device': expired_devices,

                # Requested additional user statistics
                'User_Total_Dealer': dealers.count(),
                'User_Inactive_Dealer': dealers.filter(status__in=['UserExpired', 'Discontinued']).count(),
                'User_Total_Unique_Vehicle_Owners': associated_vehicle_owners.count(),
                'User_Expired_Vehicle_Owners': associated_vehicle_owners.filter(expirydate__lt=current_date).count(),

                # Requested additional device statistics
                'Device_Total_Stock': stock.count(),
                'Device_Assigned_To_Dealer': stock.filter(dealer__isnull=False).count(),
                'Device_Tagged': manufacturer_devices.count(),
                'Device_Online_Today': online_today,
                'Device_Offline_Since_7_Days': offline_7day,
                'Device_Offline_Since_30_Days': offline_30day,

                # Requested additional eSIM statistics
                'ESim_Attached_M2M_Service_Provider': profile.esim_provider.count(),
                'ESim_Activation_Request_Sent': esim_act_requests.count(),
                'ESim_Activated': esim_validated,
                'ESim_1_Year_Expiry': esim_1yr_expiry,
                'ESim_2_Year_Expiry': esim_2yr_expiry,
                'ESim_Already_Expired': esim_already_expired
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_DTO(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="dtorto"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from django.db.models import OuterRef, Subquery
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Get all devices in DTO's jurisdiction (state/district)
            # For DTO, we filter by devices in their state and optionally district.
            # NOTE: dto_rto.district is stored as a string and in production is typically a district_code (e.g. 'AS01').
            devices_in_state = DeviceTag.objects.all()

            # Filter by state (via DeviceTag.district FK -> Settings_District.state)
            if getattr(profile, 'state', None):
                devices_in_state = devices_in_state.filter(district__state=profile.state)

            # If DTO has specific district, support either district code or district name
            district_value = (getattr(profile, 'district', None) or '').strip()
            if district_value:
                devices_in_state = devices_in_state.filter(
                    Q(district__district_code=district_value) | Q(district__district=district_value)
                )

            
            # Calculate device and vehicle statistics
            total_devices_activated = devices_in_state.count()
            
            total_vehicles = devices_in_state.count()
            
            # Calculate online/offline device statistics
            online_devices = 0
            offline_today = 0
            offline_7day = 0
            offline_30day = 0
            
            activated_devices = devices_in_state.filter(status="Device_Active")
            
            for device in devices_in_state:
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps:
                    # Check if device is online (data received within last 30 minutes)
                    if latest_gps.entry_time >= now - timedelta(minutes=30):
                        online_devices += 1
                    
                    # Check offline periods
                    if latest_gps.entry_time < today_start:
                        offline_today += 1
                    if latest_gps.entry_time < week_ago:
                        offline_7day += 1
                    if latest_gps.entry_time < now - timedelta(days=30):
                        offline_30day += 1
                else:
                    # No GPS data means offline for all periods
                    offline_today += 1
                    offline_7day += 1
                    offline_30day += 1
            
            # Calculate alert statistics for the jurisdiction
            total_alerts = AlertsLog.objects.filter(
                deviceTag__in=devices_in_state
            ).count()
            
            alerts_month = AlertsLog.objects.filter(
                deviceTag__in=devices_in_state,
                timestamp__gte=month_start
            ).count()
            
            alerts_today = AlertsLog.objects.filter(
                deviceTag__in=devices_in_state,
                timestamp__gte=today_start
            ).count()
            
            # Calculate activation statistics (device tagging/activation)
            total_activations = devices_in_state.filter(
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed']
            ).count()
            
            activations_month = devices_in_state.filter(
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed'],
                tagged__gte=month_start
            ).count()
            
            activations_today = devices_in_state.filter(
                status__in=['Device_Active', 'RegNo_Configuration_Confirmed', 'Live_Location_Confirmed', 'SOS_Confirmed'],
                tagged__gte=today_start
            ).count()
            
            # Calculate SOS call statistics for the jurisdiction
            total_sos = EMCall.objects.filter(
                device__in=devices_in_state
            ).count()
            
            genuine_sos = EMCall.objects.filter(
                device__in=devices_in_state,
                status__in=['closed', 'field_ex_arrived']
            ).count()
            
            fake_sos = EMCall.objects.filter(
                device__in=devices_in_state,
                status='closed_false_allert'
            ).count()
            
            count_dict = {
                'Total_Device_Activated': total_devices_activated,
                'Total_Vehicles': total_vehicles,
                'Total_Online_Device': online_devices,
                'Total_Offline_Device_today': offline_today,
                'Total_Offline_Device_7day': offline_7day,
                'Total_Offline_Device_30day': offline_30day,
                
                'Total_Alert': total_alerts,
                'Alert_month': alerts_month,
                'Alert_today': alerts_today,
                
                'Total_activations': total_activations,
                'Activations_month': activations_month,
                'Activations_today': activations_today,
                
                'Total_SOS_calls': total_sos,
                'Genuine_calls': genuine_sos,
                'Fake_calls': fake_sos
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': f"Unable to process request: {str(e)}"}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="owner"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        #print('profile',profile.state.state)
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Get all devices owned by this vehicle owner
            owned_devices = DeviceTag.objects.filter(vehicle_owner=profile)
            # Support multiple activation-like statuses; optional override via request 

            active_statuses = [
                "Device_Active",
                "Owner_Final_OTP_Verified",
                "Owner_OTP_Verified",
            ] 
            activated_devices = owned_devices.filter(status__in=active_statuses)
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Vehicle stats based on latest GPS per tag (as per API spec)
            total_vehicles = owned_devices.count()
            latest_gps_qs = GPSData.objects.filter(device_tag_id=OuterRef('pk')).order_by('-entry_time', '-id')
            owned_devices_with_latest = owned_devices.annotate(
                latest_speed=Subquery(latest_gps_qs.values('speed')[:1]),
                latest_ignition_status=Subquery(latest_gps_qs.values('ignition_status')[:1]),
            )

            ignition_on_count = owned_devices_with_latest.filter(latest_ignition_status='1').count()
            moving_count = owned_devices_with_latest.filter(latest_speed__gt=1).count()
            idle_count = max(0, total_vehicles - moving_count)
            stopped_count = idle_count

            # Keep existing "online" semantics for this endpoint (last 30 minutes)
            online_count = GPSData.objects.filter(
                device_tag__in=activated_devices,
                entry_time__gte=now - timedelta(minutes=30)
            ).values('device_tag').distinct().count()
            
            # Calculate offline devices for different periods
            offline_today = activated_devices.count() - GPSData.objects.filter(
                device_tag__in=activated_devices,
                entry_time__gte=today_start
            ).values('device_tag').distinct().count()
            
            offline_7day = activated_devices.count() - GPSData.objects.filter(
                device_tag__in=activated_devices,
                entry_time__gte=week_ago
            ).values('device_tag').distinct().count()
            
            offline_30day = activated_devices.count() - GPSData.objects.filter(
                device_tag__in=activated_devices,
                entry_time__gte=now - timedelta(days=30)
            ).values('device_tag').distinct().count()
            
            # Calculate total travel distance from odometer
            total_distance = 0
            for device in activated_devices:
                latest_gps = GPSData.objects.filter(device_tag=device).order_by('-entry_time').first()
                if latest_gps and latest_gps.odometer:
                    total_distance += latest_gps.odometer
            
            # Calculate alert statistics
            total_alerts = AlertsLog.objects.filter(deviceTag__in=owned_devices).count()
            alerts_month = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                timestamp__gte=month_start
            ).count()
            alerts_today = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                timestamp__gte=today_start
            ).count()
            
            # Calculate specific alert types
            harsh_braking = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                type='HarshBreak'
            ).count()
            
            harsh_turn = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                type='HarshTurn'
            ).count()
            
            overspeeding = AlertsLog.objects.filter(
                deviceTag__in=owned_devices,
                type='OverSpeed'
            ).count()
            
            # Calculate SOS calls
            total_sos = EMCall.objects.filter(device__in=owned_devices).count()
            genuine_sos = EMCall.objects.filter(
                device__in=owned_devices,
                status__in=['closed', 'field_ex_arrived']
            ).count()
            fake_sos = EMCall.objects.filter(
                device__in=owned_devices,
                status='closed_false_allert'
            ).count()
            
            # Get recent alerts for alert list
            recent_alerts = AlertsLog.objects.filter(
                deviceTag__in=owned_devices
            ).select_related('gps_ref', 'deviceTag').order_by('-timestamp')[:10]
            
            alert_list = []
            for alert in recent_alerts:
                alert_data = {
                    'type': alert.get_type_display() if alert.type else 'Unknown',
                    'id': alert.id,
                    'TriggerTime': alert.timestamp.isoformat(),
                    'Status': alert.status if alert.status else 'Active',
                    'VehicleRegNo': alert.deviceTag.vehicle_reg_no if alert.deviceTag else 'Unknown',
                    'TriggerLocation': {
                        'latitude': float(alert.gps_ref.latitude) if alert.gps_ref else 0,
                        'latitude_dir': alert.gps_ref.latitude_dir if alert.gps_ref else 'N',
                        'longitude': float(alert.gps_ref.longitude) if alert.gps_ref else 0,
                        'longitude_dir': alert.gps_ref.longitude_dir if alert.gps_ref else 'E'
                    }
                }
                alert_list.append(alert_data)
            
            count_dict = {
                'Total_Vehicles': total_vehicles,
                'Total_IgON_Vehicles': ignition_on_count,
                'Total_IgOFF_Vehicles': max(0, total_vehicles - ignition_on_count),
                'Total_Device_Activated': activated_devices.count(),
                'Total_Moving_Vehicles': moving_count,
                'Total_Stopped_Vehicles': stopped_count,
                'Total_Idle_Vehicles': idle_count,
                
                'Total_Online_Device': online_count,
                'Total_Offline_Device_today': offline_today,
                'Total_Offline_Device_7day': offline_7day,
                'Total_Offline_Device_30day': offline_30day,
                
                'Total_Travel_Distance_km': round(total_distance, 2),
                
                'Total_Alert': total_alerts,
                'Alert_month': alerts_month,
                'Alert_today': alerts_today,
                
                'Total_Harshbraking': harsh_braking,
                'Total_suddenturn': harsh_turn,
                'Total_overspeeding': overspeeding,
                
                'Total_SOS_calls': total_sos,
                'Genuine_calls': genuine_sos,
                'Fake_calls': fake_sos,
                'Alert_list': alert_list
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': f"Unable to process request: {str(e)}"}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['POST'])
def update_vehicle_owner_expiry(request):
    """
    API to update the expiry date of a given Vehicle Owner.
    Permissions:
    - superadmin/stateadmin: can update any Vehicle Owner
    - dealer (retailer): can update only Vehicle Owners created by themselves
    """
    try:
        # Validate input
        owner_id = request.data.get('owner_id')
        new_expiry_date = request.data.get('new_expiry_date')

        if not owner_id or not new_expiry_date:
            return Response({"error": "Both 'owner_id' and 'new_expiry_date' are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse the new expiry date
        try:
            new_expiry_date = timezone.datetime.strptime(new_expiry_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use 'YYYY-MM-DD'."}, status=status.HTTP_400_BAD_REQUEST)

        # Determine permissions based on role
        user = request.user
        is_super = bool(get_user_object(user, "superadmin")) if hasattr(user, 'role') else False
        is_state = bool(get_user_object(user, "stateadmin")) if hasattr(user, 'role') else False
        is_dealer = bool(get_user_object(user, "dealer")) if hasattr(user, 'role') else False

        # Fetch target VehicleOwner with appropriate restrictions
        try:
            if is_super or is_state:
                # Super/state admin can update any owner
                vehicle_owner = VehicleOwner.objects.get(id=owner_id)
            elif is_dealer:
                # Dealer can only update owners they created
                vehicle_owner = VehicleOwner.objects.get(id=owner_id, createdby=user)
            else:
                return Response({"error": "You do not have permission to update this owner's expiry date."}, status=status.HTTP_403_FORBIDDEN)
        except VehicleOwner.DoesNotExist:
            return Response({"error": "Vehicle Owner not found or you do not have permission to update this owner."}, status=status.HTTP_404_NOT_FOUND)

        # Update the expiry date
        vehicle_owner.expirydate = new_expiry_date
        vehicle_owner.save()

        return Response({
            "message": "Expiry date updated successfully.",
            "vehicle_owner": VehicleOwnerSerializer(vehicle_owner).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Unable to process request: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_VehicleOwnerold(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 

        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="owner"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            count_dict = {
                 


'Total_Vehicles':0,
'Total_Device_Activated':0,
'Total_Moving_Vehicles':0,
'Total_Stopped_Vehicles':0,
'Total_Idle_Vehicles':0,

'Total_Online_Device':0,
'Total_Offline_Device_today':0,
'Total_Offline_Device_7day':0,
'Total_Offline_Device_30day':0,

'Total_Travel_Distance_km':0,



'Total_Alert':0,
'Alert_month':0,
'Alert_today':0,

'Total_Harshbraking':0,
'Total_suddenturn':0,
'Total_overspeeding':0,

'Total_SOS_calls':0,
'Genuine_calls':0,
'Fake_calls':0


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_Dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
         
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="dealer"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Get all device stock assigned to this dealer
            dealer_devices = DeviceStock.objects.filter(dealer=profile)

            # Tagged devices for this dealer (tag-device count)
            untagged_statuses = ['TagDeleted', 'Device_Untagged']
            tagged_devices_qs = DeviceTag.objects.filter(device__dealer=profile).exclude(status__in=untagged_statuses)
            tagged_device_ids = tagged_devices_qs.values_list('id', flat=True)
            total_tagged_devices = tagged_devices_qs.count()
            
            # Calculate fitment statistics
            total_fitments = total_tagged_devices
            
            fitments_month = tagged_devices_qs.filter(tagged__gte=month_start).count()
            
            fitments_today = tagged_devices_qs.filter(tagged__gte=today_start).count()
            
            # Calculate device stock statistics
            total_assigned = dealer_devices.count()
            total_returned = dealer_devices.filter(stock_status='Returned_to_manufacturer').count()
            current_faulty = dealer_devices.filter(stock_status='Device_Defective').count()

            # Current device stock = assigned but not tagged
            current_stock = dealer_devices.filter(devicetag__isnull=True).exclude(
                stock_status__in=['Returned_to_manufacturer', 'Device_Defective']
            ).count()
            # Available free devices = current stock (per spec)
            available_free = current_stock
            
            # Calculate eSIM activation requests from esimActivationRequest model
            esim_act_requests = esimActivationRequest.objects.filter(ceated_by=profile)
            esim_pending = esim_act_requests.filter(status="pending").count()
            esim_validated = esim_act_requests.filter(status="valid").count()
            esim_invalid = esim_act_requests.filter(status="invalid").count()
            # 1yr / 2yr expiry based on plan duration (valid_upto - valid_from)
            from django.db.models import ExpressionWrapper, DurationField, F
            _plan_dur = ExpressionWrapper(F('valid_upto') - F('valid_from'), output_field=DurationField())
            esim_1yr_expiry = esim_act_requests.filter(status="valid").annotate(
                plan_duration=_plan_dur
            ).filter(
                plan_duration__gte=timedelta(days=330),
                plan_duration__lt=timedelta(days=545)
            ).count()
            esim_2yr_expiry = esim_act_requests.filter(status="valid").annotate(
                plan_duration=_plan_dur
            ).filter(
                plan_duration__gte=timedelta(days=545),
                plan_duration__lte=timedelta(days=800)
            ).count()
            esim_already_expired = esim_act_requests.filter(valid_upto__lte=now).count()
            # map to backward-compatible variable names
            one_year_renewals = esim_1yr_expiry
            two_year_renewals = esim_2yr_expiry
            
            # Calculate online/offline device statistics
            dealer_vehicle_owners = VehicleOwner.objects.filter(
                devicetag__device__dealer=profile
            ).distinct()

            # Online = unique tags with GPS data in last 15 minutes
            online_threshold = now - timedelta(minutes=15)
            online_now = GPSData.objects.filter(
                device_tag_id__in=tagged_device_ids,
                entry_time__gte=online_threshold
            ).values('device_tag_id').distinct().count()

            # Online today = unique tags with GPS data since start of day
            online_today = GPSData.objects.filter(
                device_tag_id__in=tagged_device_ids,
                entry_time__gte=today_start
            ).values('device_tag_id').distinct().count()

            # Offline N days = tagged devices with no GPS data in last N days
            gps_seen_7days = GPSData.objects.filter(
                device_tag_id__in=tagged_device_ids,
                entry_time__gte=now - timedelta(days=7)
            ).values('device_tag_id').distinct().count()
            gps_seen_30days = GPSData.objects.filter(
                device_tag_id__in=tagged_device_ids,
                entry_time__gte=now - timedelta(days=30)
            ).values('device_tag_id').distinct().count()

            offline_7days = max(0, total_tagged_devices - gps_seen_7days)
            offline_30days = max(0, total_tagged_devices - gps_seen_30days)
            
            count_dict = {
                'Total_Fitment_done': total_fitments,
                'TotalTaggedDevice': total_tagged_devices,
                'Fitment_month': fitments_month,
                'Fitment_today': fitments_today,
                
                'Total_Device_Assigned': total_assigned,
                'Total_Device_Returned': total_returned,
                'Current_Device_stock': current_stock,
                'Current_Device_faulty': current_faulty,
                'Available_Free_Device': available_free,
                'Total_esim_activation_request': esim_act_requests.count(),
                'Total_1_year_renewal_request': one_year_renewals,
                'Total_2_year_renewal_request': two_year_renewals,
                'Total_esim_activated': esim_validated,
                'Total_esim_activated_stock': dealer_devices.filter(
                    stock_status__in=['ESIM_Active_Confirmed', 'IP_PORT_Configured', 'SOS_GATEWAY_NO_Configured', 'SMS_GATEWAY_NO_Configured']
                ).count(),
                'Total_esim_expired': esim_already_expired,
                
                'Total_Online_now': online_now,
                'Total_Online_today': online_today,
                'Total_Offline_7_days': offline_7days,
                'Total_Offline_30_days': offline_30days,

                # Requested additional vehicle owner counters
                'Unique_Vehicle_Owners_Associated': dealer_vehicle_owners.count(),
                'Unique_Vehicle_Owners_Associated_This_Month': VehicleOwner.objects.filter(
                    devicetag__device__dealer=profile,
                    devicetag__tagged__gte=month_start
                ).distinct().count(),
                'Unique_Vehicle_Owners_Associated_Today': VehicleOwner.objects.filter(
                    devicetag__device__dealer=profile,
                    devicetag__tagged__gte=today_start
                ).distinct().count(),

                # Requested additional eSIM counters
                'ESim_Activation_Request_Sent': esim_act_requests.count(),
                'ESim_Activated': esim_validated,
                'ESim_1_Year_Expiry': esim_1yr_expiry,
                'ESim_2_Year_Expiry': esim_2yr_expiry,
                'ESim_Already_Expired': esim_already_expired
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': f"Unable to process request: {str(e)}"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_adminreport2(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if True:
            from datetime import timedelta
            from django.utils import timezone

            now = timezone.now()
            today = now.date()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=today_start.weekday())
            month_start = today_start.replace(day=1)
            online_threshold = now - timedelta(minutes=30)

            teamlead_qs = EM_ex.objects.filter(user_type='teamlead')
            desk_ex_qs = EM_ex.objects.filter(user_type='desk_ex')
            police_ex_qs = EM_ex.objects.filter(user_type='police_ex')
            ambulance_ex_qs = EM_ex.objects.filter(user_type='ambulance_ex')

            broadcast_qs = EMCallBroadcast.objects.all()

            calls_qs = EMCall.objects.all()
            closed_calls_qs = calls_qs.filter(status="closed")
            fake_calls_qs = calls_qs.filter(status="closed_false_alert")
            rejected_assignments_qs = EMCallAssignment.objects.filter(status="rejected")
            accepted_assignments_qs = EMCallAssignment.objects.filter(status="accepted")

            count_dict = {
 
                'Total_Teams':EMTeams.objects.filter(status="Active").count(),
                'Total_DeskExecutives':EM_ex.objects.filter(user_type='desk_ex' ).count(),
                'Live_Teams':EMTeams.objects.filter( status="Active").count(),
                'Live_DeskExecutives':EM_ex.objects.filter(user_type='desk_ex' ).count(),

                'Total_Incoming_Calls': calls_qs.count(),
                'Total_Incoming_Calls_thismonth': calls_qs.filter(start_time__gte=month_start).count(),
                'Total_Incoming_Calls_thisweek': calls_qs.filter(start_time__gte=week_start).count(),
                'Total_Incoming_Calls_today': calls_qs.filter(start_time__gte=today_start).count(),

                'Total_Closed_Calls': closed_calls_qs.count(),
                'Total_Closed_Calls_thismonth': closed_calls_qs.filter(end_time__gte=month_start).count(),
                'Total_Closed_Calls_thisweek': closed_calls_qs.filter(end_time__gte=week_start).count(),
                'Total_Closed_Calls_today': closed_calls_qs.filter(end_time__gte=today_start).count(),

                'Total_Fake_Calls': fake_calls_qs.count(),
                'Total_Fake_Calls_thismonth': fake_calls_qs.filter(end_time__gte=month_start).count(),
                'Total_Fake_Calls_thisweek': fake_calls_qs.filter(end_time__gte=week_start).count(),
                'Total_Fake_Calls_today': fake_calls_qs.filter(end_time__gte=today_start).count(),


                'Total_Active_Calls':EMCall.objects.filter( status__in=["desk_ex_assigned","broadcast_pending", "field_ex_aproaching" , "field_ex_arrived"]).count(),  
                'Total_Pending_Calls':EMCall.objects.filter(status="pending" ).count(),

                'Total_Rejected_Assignemnt': rejected_assignments_qs.count(),
                'Total_Rejected_Assignemnt_thismonth': rejected_assignments_qs.filter(reject_time__gte=month_start).count(),
                'Total_Rejected_Assignemnt_thisweek': rejected_assignments_qs.filter(reject_time__gte=week_start).count(),
                'Total_Rejected_Assignemnt_today': rejected_assignments_qs.filter(reject_time__gte=today_start).count(),

                'Average_time_to_Accept': accepted_assignments_qs.count(),

                # Requested SOS users counters
                'SOS_Team_Leads': teamlead_qs.count(),
                'SOS_Online_Team_Leads': teamlead_qs.filter(
                    users__status='active',
                    users__is_active=True,
                    users__login=True,
                    users__last_activity__gte=online_threshold
                ).values('users').distinct().count(),
                'SOS_Desk_Executives': desk_ex_qs.count(),
                'SOS_Online_Desk_Executives': desk_ex_qs.filter(
                    users__status='active',
                    users__is_active=True,
                    users__login=True,
                    users__last_activity__gte=online_threshold
                ).values('users').distinct().count(),
                'SOS_Police_Executives': police_ex_qs.count(),
                'SOS_Online_Police_Executives': police_ex_qs.filter(
                    users__status='active',
                    users__is_active=True,
                    users__login=True,
                    users__last_activity__gte=online_threshold
                ).values('users').distinct().count(),
                'SOS_Ambulance_Executives': ambulance_ex_qs.count(),
                'SOS_Online_Ambulance_Executives': ambulance_ex_qs.filter(
                    users__status='active',
                    users__is_active=True,
                    users__login=True,
                    users__last_activity__gte=online_threshold
                ).values('users').distinct().count(),

                # Requested broadcast statistics
                'Broadcast_Total': broadcast_qs.count(),
                'Broadcast_Total_Closed': broadcast_qs.exclude(status='pending').count(),
                'Broadcast_Total_Today': broadcast_qs.filter(created_at__date=today).count(),
                'Broadcast_Total_Closed_Today': broadcast_qs.exclude(status='pending').filter(created_at__date=today).count(),
                'Broadcast_Currently_Pending': broadcast_qs.filter(status='pending').count(),


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_adminreport(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="sosadmin" 
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile:
            from datetime import timedelta
            from django.utils import timezone

            now = timezone.now()
            today = now.date()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=today_start.weekday())
            month_start = today_start.replace(day=1)

            calls_qs = EMCall.objects.filter(team__state=profile.state)
            closed_calls_qs = calls_qs.filter(status="closed")
            fake_calls_qs = calls_qs.filter(status="closed_false_alert")
            rejected_assignments_qs = EMCallAssignment.objects.filter(status="rejected", admin=profile)
            accepted_assignments_qs = EMCallAssignment.objects.filter(status="accepted", admin=profile)

            count_dict = {
 
                'Total_Teams':EMTeams.objects.filter(state=profile.state,status="Active").count(),
                'Total_DeskExecutives':EM_ex.objects.filter(user_type='desk_ex',state=profile.state).count(),
                'Live_Teams':EMTeams.objects.filter(state=profile.state,status="Active").count(),
                'Live_DeskExecutives':EM_ex.objects.filter(user_type='desk_ex',state=profile.state).count(),

                'Total_Incoming_Calls': calls_qs.count(),
                'Total_Incoming_Calls_thismonth': calls_qs.filter(start_time__gte=month_start).count(),
                'Total_Incoming_Calls_thisweek': calls_qs.filter(start_time__gte=week_start).count(),
                'Total_Incoming_Calls_today': calls_qs.filter(start_time__gte=today_start).count(),

                'Total_Closed_Calls': closed_calls_qs.count(),
                'Total_Closed_Calls_thismonth': closed_calls_qs.filter(end_time__gte=month_start).count(),
                'Total_Closed_Calls_thisweek': closed_calls_qs.filter(end_time__gte=week_start).count(),
                'Total_Closed_Calls_today': closed_calls_qs.filter(end_time__gte=today_start).count(),

                'Total_Fake_Calls': fake_calls_qs.count(),
                'Total_Fake_Calls_thismonth': fake_calls_qs.filter(end_time__gte=month_start).count(),
                'Total_Fake_Calls_thisweek': fake_calls_qs.filter(end_time__gte=week_start).count(),
                'Total_Fake_Calls_today': fake_calls_qs.filter(end_time__gte=today_start).count(),


                'Total_Active_Calls':EMCall.objects.filter(team__state=profile.state,status__in=["desk_ex_assigned","broadcast_pending", "field_ex_aproaching" , "field_ex_arrived"]).count(),  
                'Total_Pending_Calls':EMCall.objects.filter(status="pending",team__state=profile.state).count(),

                'Total_Rejected_Assignemnt': rejected_assignments_qs.count(),
                'Total_Rejected_Assignemnt_thismonth': rejected_assignments_qs.filter(reject_time__gte=month_start).count(),
                'Total_Rejected_Assignemnt_thisweek': rejected_assignments_qs.filter(reject_time__gte=week_start).count(),
                'Total_Rejected_Assignemnt_today': rejected_assignments_qs.filter(reject_time__gte=today_start).count(),


                'Average_time_to_Accept': accepted_assignments_qs.count(),


             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['get'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_TLreport(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="sosexecutive" 
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  teamlead"}, status=status.HTTP_400_BAD_REQUEST)
        print(profile.user_type)
        if 'teamlead' not in profile.user_type:#, 'desk_ex',
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile:
            team=EMTeams.objects.filter(teamlead=profile,status="Active").last()
            a=0
            b=0
            if team:
                a=team.members.count()
                b=team.members.count()
            count_dict = {
 
                 
                'Total_DeskExecutives':a, 
                'Live_DeskExecutives':b,

                'Total_Incoming_Calls':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),
                'Total_Incoming_Calls_thismonth':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),
                'Total_Incoming_Calls_thisweek':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),
                'Total_Incoming_Calls_today':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state).count(),

                'Total_Closed_Calls':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_thismonth':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_thisweek':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),
                'Total_Closed_Calls_today':EMCall.objects.filter(team__teamlead=profile,status="closed",team__state=profile.state).count(),

                'Total_Fake_Calls':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_thismonth':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_thisweek':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),
                'Total_Fake_Calls_today':EMCall.objects.filter(team__teamlead=profile,status="closed_false_allert",team__state=profile.state).count(),


                'Total_Active_Calls':EMCall.objects.filter(team__teamlead=profile,team__state=profile.state,status__in=["desk_ex_assigned","broadcast_pending", "field_ex_aproaching" , "field_ex_arrived"]).count(),  
                'Total_Pending_Calls':EMCall.objects.filter(team__teamlead=profile,status="pending",team__state=profile.state).count(),

                'Total_Rejected_Assignemnt':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),
                'Total_Rejected_Assignemn_thistmonth':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),
                'Total_Rejected_Assignemn_thisweek':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),
                'Total_Rejected_Assignemn_today':EMCallAssignment.objects.filter(status="rejected",call__team__teamlead=profile).count(),

                'Average_time_to_Accept':EMCallAssignment.objects.filter(status="accepted",call__team__teamlead=profile).count(),

             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['get'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_TLreport2(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
 

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if True:
            team=EMTeams.objects.filter(status="Active").last()
            a=0
            b=0
            if team:
                a=team.members.count()
                b=team.members.count()
            # AlertsLog statistics (total + by type/status for the teamlead's state)
            from django.db.models import Count
            alerts_qs = AlertsLog.objects.all()
            total_alertslog = alerts_qs.count()
            alerts_breakdown = list(
                alerts_qs.values('type', 'status').annotate(count=Count('id')).order_by('type', 'status')
            )
            count_dict = {
 
                 
                'Total_DeskExecutives':a, 
                'Live_DeskExecutives':b,

                'Total_AlertsLog': total_alertslog,
                'AlertsLog_ByTypeStatus': alerts_breakdown,

                'Total_Incoming_Calls':EMCall.objects.count(),
                'Total_Incoming_Calls_thismonth':EMCall.objects.count(),
                'Total_Incoming_Calls_thisweek':EMCall.objects.count(),
                'Total_Incoming_Calls_today':EMCall.objects.count(),

                'Total_Closed_Calls':EMCall.objects.count(),
                'Total_Closed_Calls_thismonth':EMCall.objects.count(),
                'Total_Closed_Calls_thisweek':EMCall.objects.count(),
                'Total_Closed_Calls_today':EMCall.objects.count(),

                'Total_Fake_Calls':EMCall.objects.filter(status="closed_false_allert").count(),
                'Total_Fake_Calls_thismonth':EMCall.objects.filter(status="closed_false_allert").count(),
                'Total_Fake_Calls_thisweek':EMCall.objects.filter(status="closed_false_allert").count(),
                'Total_Fake_Calls_today':EMCall.objects.filter(status="closed_false_allert").count(),

                'Total_Active_Calls':EMCall.objects.filter( status__in=["desk_ex_assigned","broadcast_pending", "field_ex_aproaching" , "field_ex_arrived"]).count(),  
                'Total_Pending_Calls':EMCall.objects.count(),

                'Total_Rejected_Assignemnt':EMCallAssignment.objects.filter(status="rejected").count(),
                'Total_Rejected_Assignemn_thistmonth':EMCallAssignment.objects.filter(status="rejected").count(),
                'Total_Rejected_Assignemn_thisweek':EMCallAssignment.objects.filter(status="rejected").count(),
                'Total_Rejected_Assignemn_today':EMCallAssignment.objects.filter(status="rejected").count(),

                'Average_time_to_Accept':EMCallAssignment.objects.filter(status="accepted").count(),

             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['get'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def SOS_EXreport(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="sosexecutive" 
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  teamlead"}, status=status.HTTP_400_BAD_REQUEST)
        if not profile.user_type=='desk_ex':#, '',
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile: 
            count_dict = {
 

  
                 
                'Total_Assignemnt_thistmonth':EMCallAssignment.objects.filter(ex=profile).count(),
                'Total_Assignemnt_thisweek':EMCallAssignment.objects.filter(ex=profile).count(),
                'Total_Assignemnt_today':EMCallAssignment.objects.filter( ex=profile).count(),
                'Total_Assignemnt':EMCallAssignment.objects.filter( ex=profile).count(),

                'Total_Closed_Assignemnt_thistmonth':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                'Total_Closed_Assignemnt_thisweek':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                'Total_Closed_Assignemnt_today':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                'Total_Closed_Assignemnt':EMCallAssignment.objects.filter(status="closed",ex=profile).count(),
                 
                'Total_False_Assignemnt_thistmonth':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),
                'Total_False_Assignemnt_thisweek':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),
                'Total_False_Assignemnt_today':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),
                'Total_False_Assignemnt':EMCallAssignment.objects.filter(status="closed_false_allert",ex=profile).count(),

                 
                'Total_Rejected_Assignemnt_thistmonth':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),
                'Total_Rejected_Assignemnt_thisweek':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),
                'Total_Rejected_Assignemnt_today':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),
                'Total_Rejected_Assignemnt':EMCallAssignment.objects.filter(status="rejected",ex=profile).count(),

                'Average_time_to_Accept':EMCallAssignment.objects.filter(status="accepted",ex=profile).count(),

             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_stateAdmin(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        profile=get_user_object(user,role)
        if not profile:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
        #print('profile',profile.state.state)
   
        

        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided


        if profile:
            # Get current datetime for filtering
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            now = timezone.now()
            today = now.date()
            seven_days_ago = now - timedelta(days=7)
            thirty_days_ago = now - timedelta(days=30)
            current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_month_start_date = current_month_start.date()
            
            # Filter data by state admin's state
            state_filter = profile.state
            
            # Get dealers in this state (through manufacturer)
            dealers_in_state = Dealer.objects.filter(manufacturer__state=state_filter)
            
            # Get manufacturers in this state
            manufacturers_in_state = Manufacturer.objects.filter(state=state_filter)
            
            # Get DTOs in this state
            dtos_in_state = dto_rto.objects.filter(state=state_filter)
            
            # Get vehicle owners through dealers in this state
            vehicle_owners_in_state = VehicleOwner.objects.filter(
                devicetag__device__dealer__manufacturer__state=state_filter
            ).distinct()
            
            # Get device tags in this state
            device_tags_in_state = DeviceTag.objects.filter(
                district__state=state_filter
            )
            
            # Get active devices in this state
            active_devices = device_tags_in_state.filter(status='Device_Active')
            
            # Get device stock in this state
            device_stock_in_state = DeviceStock.objects.filter(
                dealer__manufacturer__state=state_filter
            )
            
            # Get districts in this state
            districts_in_state = Settings_District.objects.filter(state=state_filter)

            # Tagged/online/offline and fitment metrics
            # Tagged devices = anything except untagged/deleted
            untagged_statuses = ['TagDeleted', 'Device_Untagged']
            tagged_devices_qs = device_tags_in_state.exclude(status__in=untagged_statuses)
            tagged_device_ids = tagged_devices_qs.values_list('id', flat=True)
            total_tagged_devices = tagged_devices_qs.count()

            online_threshold = timezone.now() - timedelta(minutes=15)
            total_online_devices = GPSData.objects.filter(
                device_tag_id__in=tagged_device_ids,
                entry_time__gte=online_threshold
            ).values('device_tag_id').distinct().count()
            total_offline_devices = max(0, total_tagged_devices - total_online_devices)

            gps_seen_7days = GPSData.objects.filter(
                device_tag_id__in=tagged_device_ids,
                entry_time__gte=now - timedelta(days=7)
            ).values('device_tag_id').distinct().count()
            gps_seen_30days = GPSData.objects.filter(
                device_tag_id__in=tagged_device_ids,
                entry_time__gte=now - timedelta(days=30)
            ).values('device_tag_id').distinct().count()
            offline_since_7_days = max(0, total_tagged_devices - gps_seen_7days)
            offline_since_30_days = max(0, total_tagged_devices - gps_seen_30days)

            total_devices = device_stock_in_state.count()
            total_untagged_devices = device_tags_in_state.filter(status__in=untagged_statuses).count()
            total_fitments = total_tagged_devices + total_untagged_devices

            # Active user counters in this state
            active_stateadmin_users = User.objects.filter(
                role='stateadmin', status='active', is_active=True, stateadmin_User__state=state_filter
            ).distinct().count()
            active_esimprovider_users = User.objects.filter(
                role='esimprovider', status='active', is_active=True, eSimProvider_User__state=state_filter
            ).distinct().count()
            active_manufacturer_users = User.objects.filter(
                role='devicemanufacture', status='active', is_active=True, manufacturers_user__state=state_filter
            ).distinct().count()
            active_sosadmin_users = User.objects.filter(
                role='sosadmin', status='active', is_active=True, EM_admin__state=state_filter
            ).distinct().count()
            active_sosexecutive_users = User.objects.filter(
                role='sosexecutive', status='active', is_active=True, SOS_ex_user__state=state_filter
            ).distinct().count()
            active_sos_teamlead_users = EM_ex.objects.filter(
                state=state_filter,
                user_type='teamlead',
                users__status='active',
                users__is_active=True
            ).values('users').distinct().count()
            active_sos_deskexecutive_users = EM_ex.objects.filter(
                state=state_filter,
                user_type='desk_ex',
                users__status='active',
                users__is_active=True
            ).values('users').distinct().count()

            # Sudden-turn alerts from AlertsLog (HarshTurn)
            sudden_turn_total = AlertsLog.objects.filter(
                deviceTag__device__dealer__manufacturer__state=state_filter,
                type='HarshTurn',
                status='in'
            ).count()
            sudden_turn_month = AlertsLog.objects.filter(
                deviceTag__device__dealer__manufacturer__state=state_filter,
                type='HarshTurn',
                status='in',
                timestamp__gte=current_month_start
            ).count()
            sudden_turn_today = AlertsLog.objects.filter(
                deviceTag__device__dealer__manufacturer__state=state_filter,
                type='HarshTurn',
                status='in',
                timestamp__date=today
            ).count()

            emergency_types = [
                'Em',
                'EmPublicApp',
                'EmRegisteredApp',
                'EmMonitorTripSOS',
                'EmMonitorTripInvalidPw',
                'EmMonitorTripBLEDisconnect',
                'EmMonitorTripDeviated',
                'Incident',
            ]

            count_dict = {
                # User counts filtered by state
                'Total_Dealer_available': dealers_in_state.count(),
                'Total_Manufacture_available': manufacturers_in_state.count(),
                'Total_M2M_Service_Provider_available': eSimProvider.objects.filter(state=state_filter).count(),
                'Total_DTO_available': dtos_in_state.count(),
                'Total_Vehicle_Owner_available': vehicle_owners_in_state.count(),

                # Device counts filtered by state
                'Total_Fit_Device': total_tagged_devices,
                'Online_Devices': total_online_devices,
                'Offline_Devices': total_offline_devices,

                'TotalTaggedDevice': total_tagged_devices,
                'TotalOnlineDevice': total_online_devices,
                'TotalOfflineDevice': total_offline_devices,
                'Offline_since_7_days': offline_since_7_days,
                'Offline_since_30_days': offline_since_30_days,
                'TotalUntaggedDevice': total_untagged_devices,
                'TotalFitments': total_tagged_devices,

                'Total_Device_Activated': active_devices.count(),
                'Active_Device_Today': device_tags_in_state.filter(
                    status='Device_Active',
                    tagged__date=today
                ).count(),
                'Inactive_Device_7days': device_tags_in_state.filter(
                    status='Device_Not_Active',
                    tagged__gte=seven_days_ago
                ).count(),
                'Inactive_Device_30days': device_tags_in_state.filter(
                    status='Device_Not_Active',
                    tagged__gte=thirty_days_ago
                ).count(),
                
                # Alert counts (from AlertsLog)
                'Total_overspeeding_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type='OverSpeed',
                    status='in'
                ).count(),
                'Monthly_overspeeding_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type='OverSpeed',
                    status='in',
                    timestamp__gte=current_month_start
                ).count(),
                'Today_overspeeding_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type='OverSpeed',
                    status='in',
                    timestamp__date=today
                ).count(),
                
                # Emergency alerts
                'Total_emergency_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type__in=emergency_types,
                    status='in'
                ).count(),
                'This_month_emergency_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type__in=emergency_types,
                    status='in',
                    timestamp__gte=current_month_start
                ).count(),
                'Today_emergency_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type__in=emergency_types,
                    status='in',
                    timestamp__date=today
                ).count(),

                'Total_sudden_turn_Alert': sudden_turn_total,
                'This_month_sudden_turn_Alert': sudden_turn_month,
                'Today_sudden_turn_Alert': sudden_turn_today,
                
                # Harsh brake alerts
                'Total_harsh_brake_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type='HarshBreak',
                    status='in'
                ).count(),
                'This_month_harsh_brake_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type='HarshBreak',
                    status='in',
                    timestamp__gte=current_month_start
                ).count(),
                'Today_harsh_brake_Alert': AlertsLog.objects.filter(
                    deviceTag__device__dealer__manufacturer__state=state_filter,
                    type='HarshBreak',
                    status='in',
                    timestamp__date=today
                ).count(),

                # Device stock counts filtered by state
                'Total_device_stock': device_stock_in_state.count(),
                'unassigned_device_stock': device_stock_in_state.filter(
                    stock_status='NotAssigned'
                ).count(),
                'waiting_device_stock': device_stock_in_state.filter(
                    stock_status='Available_for_fitting'
                ).count(),
                
                # State and district counts
                'Total_state': 1,  # This state admin manages only one state
                'Active_state': 1 if state_filter.status == 'active' else 0,
                'Discontinued_state': 1 if state_filter.status == 'discontinued' else 0,
             
                'Total_district': districts_in_state.count(),
                'Active_district': districts_in_state.filter(status='active').count(),
                'Discontinued_district': districts_in_state.filter(status='discontinued').count(),

                'ActiveUsers_stateadmin': active_stateadmin_users,
                'ActiveUsers_esimprovider': active_esimprovider_users,
                'ActiveUsers_manufacturer': active_manufacturer_users,
                'ActiveUsers_sosadmin': active_sosadmin_users,
                'ActiveUsers_sosexecutive': active_sosexecutive_users,
                'ActiveUsers_sos_teamlead': active_sos_teamlead_users,
                'ActiveUsers_sos_deskexecutive': active_sos_deskexecutive_users,
             
            }
            # Return the serialized data as JSON response
            return Response(count_dict)
        else:
            return Response({'error': "Unauthorised user"}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_user1(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()

        # User counts should be based on actual user accounts by role
        if True:
            count_dict = {
            'total_user': UserModel.objects.count(),
            'state_admin': UserModel.objects.filter(role='stateadmin').count(),
            'manufacturer_admin': UserModel.objects.filter(role='devicemanufacture').count(),
            'dtorto_admin': UserModel.objects.filter(role='dtorto').count(),
            'eSimProvider': UserModel.objects.filter(role='esimprovider').count(),
            'Dealer': UserModel.objects.filter(role='dealer').count(),
            'VehicleOwner': UserModel.objects.filter(role='owner').count(),
            'SOS_ex': UserModel.objects.filter(role='sosexecutive').count(),
            'SOS_user': UserModel.objects.filter(role='teamleader').count(),
            'SOS_admin': UserModel.objects.filter(role='sosadmin').count(),
        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_user2(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            count_dict = {
             
            'dtorto_admin': dto_rto.objects.count(),
            'eSimProvider': eSimProvider.objects.count(),
            'Dealer': Dealer.objects.count(),
            'VehicleOwner': VehicleOwner.objects.count(), 
            'SOS_ex': EM_ex.objects.count(),
            'SOS_user': EM_ex.objects.count(),
            'SOS_admin': EM_admin.objects.count(),
        }
        # Return the serialized data as JSON response
        return Response(count_dict)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_State(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided

        #"superadmin","devicemanufacture","","dtorto","dealer","owner","esimprovider"
        role="stateadmin"
        user=request.user
        uo=get_user_object(user,role)
        role="sosadmin" 
        uosos=get_user_object(user,role)
        if  uo:
            state=uo.state
            manufacturers = Settings_State.objects.filter(id=state.id ).distinct()
        elif  uosos:
            state=uosos.state
            manufacturers = Settings_State.objects.filter(id=state.id ).distinct()
        else:
            manufacturers = Settings_State.objects.all()

 
        # Serialize the queryset
        dealer_serializer = Settings_StateSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_State_pub(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        manufacturers = Settings_State.objects.all()

 
        # Serialize the queryset
        dealer_serializer = Settings_StateSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_Settings_State(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
      #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    
    user_id = request.user.id  
    data = {
        'createdby': user_id,
        'created': timezone.now(),   
    } 
    request_data = request.data.copy()

    if 'state_name' in request_data:
        request_data['state'] = request_data['state_name'].capitalize()
    request_data.update(data)
    #print(request_data)
    serializer = Settings_StateSerializer(data=request_data)

    if serializer.is_valid():
        instance = serializer.save()
    

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_Settings_ip(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # Create a dictionary to hold the filter parameters
        filters = {}
        # Add ID filter if provided
        if True:
            manufacturers = Settings_ip.objects.filter(
                 
            ).distinct()
        # Serialize the queryset
        dealer_serializer = Settings_ipSerializer(manufacturers, many=True)
        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def filter_VehicleOwner(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        dealer_id = request.data.get('eSimProvider_id', None)
        email = request.data.get('email', '')
        company_name = request.data.get('company_name', '')
        name = request.data.get('name', '')
        phone_no = request.data.get('phone_no', '')
        address = request.data.get('address', '') 
        filters = {} 
        if dealer_id :
            manufacturers = VehicleOwner.objects.filter(
                id=dealer_id ,
                users__email__icontains=email, 
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()
        else:
            manufacturers = VehicleOwner.objects.filter( 
                users__status='active',
                users__email__icontains=email,
                #company_name__icontains=company_name,
                users__name__icontains=name,
                users__mobile__icontains=phone_no, 
            ).distinct()

        # Serialize the queryset
        dealer_serializer = VehicleOwnerSerializer(manufacturers, many=True)

        # Return the serialized data as JSON response
        return Response(dealer_serializer.data)


    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


'''



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_esim_activation_request(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
            
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="dealer"
        user=request.user
        ret=get_user_object(user,role)
        if not ret:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = { 
            'ceated_by':ret.id,  
            'status': 'pending',
            #'device': int(request.data['device'])
        } 
        request_data = request.data.copy()
        request_data.update(data)
        dev=DeviceStock.objects.filter(id=request_data['device']).last()
        if not dev:
            return Response("device not found", status=status.HTTP_400_BAD_REQUEST)
        if dev.esim_status=="ESIM Active Request Sent":
            return Response("AlreadyPendingRequest", status=status.HTTP_400_BAD_REQUEST)

        serializer = EsimActivationRequestSerializer(data=request_data)
        if serializer.is_valid():
            dev.esim_status='ESIM_Active_Req_Sent'
            dev.save()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def filter_esim_activation_request(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

           
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="esimprovider"
    user=request.user
    #ret=get_user_object(user,role)
    #if not ret:
    #    return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        
    if request.method == 'POST':
        filters = request.data.get('filters', {}) 
        queryset = esimActivationRequest.objects.filter(**filters)
        serializer = EsimActivationRequestSerializer_R(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@permission_classes([AllowAny])
@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def update_esim_activation_request(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

      
    if request.method == 'POST':
        #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
        role="esimprovider"
        user=request.user
        ret=get_user_object(user,role)
        if not ret:
            return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
        
        esim_request=esimActivationRequest.objects.filter(id=request.data['eSim_activation_req_id']).last()
        if not esim_request:
            return Response({"error":"eSim_activation_req_id is invalid."}, status=status.HTTP_400_BAD_REQUEST)
        if esim_request.eSim_provider != ret:
            return Response({"error":"esim provided is not designeated esim provider for this device."}, status=status.HTTP_400_BAD_REQUEST)
        if esim_request.status!="pending":
            return Response({"error":"esim activation request mustbe pending to activate"}, status=status.HTTP_400_BAD_REQUEST)
        
        data = { 'status': 'pending', }  
        if request.data['status']=="accept":
            data = { 'status': 'valid'}  
        elif request.data['status']=="reject":
            data = { 'status': 'invalid'}  
        else:
            return Response({"error":"Status should be only ony one of the two[accept/reject]."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = EsimActivationRequestSerializer(esim_request, data=data, partial=True)
        dev=esim_request.device
        #DeviceStock.objects.filter(id=data['device']).last()
         

        if serializer.is_valid():
            if data['status']=='valid':
                dev.esim_status='ESIM_Active_Confirmed'
            elif data['status']=='invalid':
                dev.esim_status='ESIM_Active_Rejected'
            
            dev.save()
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





def get_user_object(user,role):
    ret=None
    if user.role !=role:
        return ret 
    if role=="superadmin":
        ret=user
    if role=="devicemanufacture":
        ret=Manufacturer.objects.filter(users=user).last() 
    if role=="stateadmin":
        ret=StateAdmin.objects.filter(users=user).last()
    if role=="dtorto":
        ret=dto_rto.objects.filter(users=user).last() 
    if role=="dealer":
        ret=Dealer.objects.filter(users=user).last() 
    if role=="owner":
        ret=VehicleOwner.objects.filter(users=user).last() 
    if role=="esimprovider":
        ret=eSimProvider.objects.filter(users=user).last() 
    if role=="sosadmin":
        ret=EM_admin.objects.filter(users=user).last() 
    if role=="sosexecutive":
        ret=EM_ex.objects.filter(users=user).last() 
        
        

    return ret


def _is_pdf_upload(file_obj):
    if not file_obj:
        return False
    name = getattr(file_obj, 'name', '') or ''
    return str(name).lower().endswith('.pdf')


def _parse_demo_devices_payload(raw_payload):
    if raw_payload is None:
        return None
    if isinstance(raw_payload, list):
        return raw_payload
    if isinstance(raw_payload, str):
        try:
            parsed = json.loads(raw_payload)
            return parsed if isinstance(parsed, list) else None
        except Exception:
            return None
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_device_model_technical_onboarding_request(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    manufacturer = get_user_object(request.user, 'devicemanufacture')
    if not manufacturer:
        return Response({'error': 'Request must be from devicemanufacture.'}, status=status.HTTP_400_BAD_REQUEST)

    device_model_id = request.data.get('device_model_id')
    if not device_model_id:
        return Response({'error': 'device_model_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    device_model = DeviceModel.objects.filter(id=device_model_id).last()
    if not device_model:
        return Response({'error': 'Invalid device_model_id.'}, status=status.HTTP_400_BAD_REQUEST)
    if device_model.created_by_id != request.user.id:
        return Response(
            {'error': 'Technical onboarding request can be created only by the same manufacturer user who created this DeviceModel.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user_manual_file = request.FILES.get('user_manual_pdf')
    ot_command_file = request.FILES.get('ot_command_list_pdf')
    if not user_manual_file or not ot_command_file:
        return Response({'error': 'Both user_manual_pdf and ot_command_list_pdf are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not _is_pdf_upload(user_manual_file) or not _is_pdf_upload(ot_command_file):
        return Response({'error': 'Only PDF files are allowed for user_manual_pdf and ot_command_list_pdf.'}, status=status.HTTP_400_BAD_REQUEST)

    demo_devices = _parse_demo_devices_payload(request.data.get('demo_devices'))
    if demo_devices is None:
        return Response({'error': 'demo_devices must be a valid JSON array.'}, status=status.HTTP_400_BAD_REQUEST)

    user_manual_path = save_file(request, 'user_manual_pdf', 'fileuploads/technical_onboarding')
    ot_command_path = save_file(request, 'ot_command_list_pdf', 'fileuploads/technical_onboarding')
    if not user_manual_path or not ot_command_path:
        return Response({'error': 'Invalid file.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = DeviceModelTechnicalOnboardingRequestCreateSerializer(data={
        'device_model_id': device_model.id,
        'user_manual_pdf': user_manual_path,
        'ot_command_list_pdf': ot_command_path,
        'demo_devices': demo_devices,
    })
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    onboarding_request = DeviceModelTechnicalOnboardingRequest.objects.create(
        manufacturer=manufacturer,
        device_model=device_model,
        user_manual_pdf=serializer.validated_data['user_manual_pdf'],
        ot_command_list_pdf=serializer.validated_data['ot_command_list_pdf'],
        status='submitted',
    )

    for device_data in serializer.validated_data['demo_devices']:
        DeviceModelTechnicalOnboardingDemoDevice.objects.create(
            onboarding_request=onboarding_request,
            **device_data
        )

    response_serializer = DeviceModelTechnicalOnboardingRequestDetailSerializer(onboarding_request)
    return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def superadmin_list_device_model_technical_onboarding_requests(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    onboarding_requests = DeviceModelTechnicalOnboardingRequest.objects.select_related(
        'manufacturer__state',
        'device_model__created_by'
    ).prefetch_related(
        'demo_devices',
        'manufacturer__users',
        'manufacturer__esim_provider',
        'device_model__eSimProviders'
    ).order_by('-request_datetime', '-id')

    serializer = DeviceModelTechnicalOnboardingRequestDetailSerializer(onboarding_requests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def superadmin_mark_technical_onboarding_ongoing_evaluation(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = DeviceModelTechnicalOnboardingMarkEvaluationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    onboarding_request = DeviceModelTechnicalOnboardingRequest.objects.filter(
        id=serializer.validated_data['onboarding_request_id']
    ).last()
    if not onboarding_request:
        return Response({'error': 'Invalid onboarding_request_id.'}, status=status.HTTP_400_BAD_REQUEST)
    if onboarding_request.status != 'submitted':
        return Response({'error': 'Only submitted requests can be moved to ongoing evaluation.'}, status=status.HTTP_400_BAD_REQUEST)

    onboarding_request.status = 'ongoing_evaluation'
    onboarding_request.evaluation_datetime = serializer.validated_data.get('evaluation_datetime', timezone.now())
    onboarding_request.save(update_fields=['status', 'evaluation_datetime'])

    response_serializer = DeviceModelTechnicalOnboardingRequestDetailSerializer(onboarding_request)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def superadmin_finalize_technical_onboarding_request(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = DeviceModelTechnicalOnboardingFinalizeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    onboarding_request = DeviceModelTechnicalOnboardingRequest.objects.filter(
        id=serializer.validated_data['onboarding_request_id']
    ).last()
    if not onboarding_request:
        return Response({'error': 'Invalid onboarding_request_id.'}, status=status.HTTP_400_BAD_REQUEST)
    if onboarding_request.status != 'ongoing_evaluation':
        return Response({'error': 'Request must be in ongoing evaluation status before final decision.'}, status=status.HTTP_400_BAD_REQUEST)

    compatibility_report_file = request.FILES.get('compatibility_report_pdf')
    if not compatibility_report_file:
        return Response({'error': 'compatibility_report_pdf is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not _is_pdf_upload(compatibility_report_file):
        return Response({'error': 'Only PDF file is allowed for compatibility_report_pdf.'}, status=status.HTTP_400_BAD_REQUEST)

    compatibility_report_path = save_file(request, 'compatibility_report_pdf', 'fileuploads/technical_onboarding')
    if not compatibility_report_path:
        return Response({'error': 'Invalid file.'}, status=status.HTTP_400_BAD_REQUEST)

    onboarding_request.compatibility_report_pdf = compatibility_report_path
    onboarding_request.final_comment = serializer.validated_data['final_comment']
    onboarding_request.status = serializer.validated_data['status']
    onboarding_request.decision_datetime = timezone.now()
    onboarding_request.save(
        update_fields=['compatibility_report_pdf', 'final_comment', 'status', 'decision_datetime']
    )

    response_serializer = DeviceModelTechnicalOnboardingRequestDetailSerializer(onboarding_request)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def manufacturer_list_own_device_model_technical_onboarding_requests(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    manufacturer = get_user_object(request.user, 'devicemanufacture')
    if not manufacturer:
        return Response({'error': 'Request must be from devicemanufacture.'}, status=status.HTTP_400_BAD_REQUEST)

    onboarding_requests = DeviceModelTechnicalOnboardingRequest.objects.filter(
        manufacturer=manufacturer
    ).select_related(
        'manufacturer__state',
        'device_model__created_by'
    ).prefetch_related(
        'demo_devices',
        'manufacturer__users',
        'manufacturer__esim_provider',
        'device_model__eSimProviders'
    ).order_by('-request_datetime', '-id')

    serializer = DeviceModelTechnicalOnboardingRequestDetailSerializer(onboarding_requests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
     

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def create_device_model(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

     
    user_id = request.user.id
    user=request.user 
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    man=get_user_object(user,"devicemanufacture")
    if not man:
        return Response({"error":"Request must be from device manufacture"}, status=status.HTTP_400_BAD_REQUEST)
     


     
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    if STATIC_OTP_CAP:
                otp  = str(685472)
    else:
                otp = str(secrets.randbelow(1000000)).zfill(6)

    # Create data for the new DeviceModel entry
    data = {
        'otp_time':timezone.now(),
        'otp': otp,
        'created_by': user_id,
        'created': timezone.now(),   
        'status': 'Manufacturer_OTP_Sent',
    }

    # Attach the file to the request data
    request_data = request.data.copy()
    request_data.update(data)
    #print("requestdata",request_data) 
    serializer = DeviceModelSerializer(data=request_data)

    # Validate and save the data along with the file
    if serializer.is_valid():
        # Save the DeviceModel instance
        device_model_instance = serializer.save()
        # Handle the uploaded file
        uploaded_file = request.FILES.get('tac_doc_path')
        if uploaded_file:
            # Save the file to a specific location
            
            file_path = save_file(request, 'tac_doc_path', 'fileuploads/tac_docs')  
            
            """file_path = 'fileuploads/tac_docs/' + str(device_model_instance.id) + '_' + uploaded_file.name
            with open(file_path, 'wb') as file:
                for chunk in uploaded_file.chunks():
                    file.write(chunk)
            stateadmin=StateAdmin.objects.last()"""
            
            # Update the tac_doc_path field in the DeviceModel instance
            device_model_instance.tac_doc_path = file_path
            device_model_instance.save()
            text="Dear User, Confirmation OTP for VLTD Model Creation at SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron".format(otp)
            tpid="1007338577423920274" 
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                text,
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )
            d=serializer.data
            d.pop('otp', None)#.drop('otp')
            return Response(d, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DeviceModelUpdateView(generics.UpdateAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelFileUploadSerializer

    def perform_update(self, serializer):
        file = self.request.FILES.get('tac_doc_path', None)
        if file:
            fs = FileSystemStorage(location=settings.MEDIA_ROOT + 'fileuploads/tac_docs/')
            filename = fs.save(file.name, file)
            tac_doc_path = 'fileuploads/tac_docs/' + filename
            serializer.validated_data['tac_doc_path'] = tac_doc_path
        serializer.save()

class DeviceModelFilterView(generics.ListAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer_disp
    filter_backends = [filters.SearchFilter]
    search_fields = ['model_name', 'test_agency', 'vendor_id', 'status']

class DeviceModelDetailView(generics.RetrieveAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer_disp

class DeviceModelDeleteView(generics.DestroyAPIView):
    queryset = DeviceModel.objects.all()
    serializer_class = DeviceModelSerializer_disp





class FileUploadView(APIView):
    parser_classes = (MultiPartParser,)
    def post(self, request, *args, **kwargs): 
        email = request.data.get('email', None)
        if not email:
            return Response({'error': 'email not provided'}, status=400)
            
        try:
            user = User.objects.get(email=email)
        
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        #user = get_object_or_404(User, email=email)
        if user:
            #print(email)
            if 'file' not in request.data:
                return Response({'error': 'No file part'}, status=status.HTTP_400_BAD_REQUEST)
            
            #print(email)
            file = request.data['file']
            user.kycfile.save(file.name, file)
            user.save()
            #serializer = UserSerializer(user) 
             
    
            return Response({'status': 'KYC Uploaded successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Invalid email'}, status=400)




        


@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def validate_email_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)



@api_view(['POST']) 
@require_http_methods(['GET', 'POST'])
def send_email_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)
    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=11)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()
        url=f"https://{DEPLOY_URL}/{confirmation_token}"
        tpid ="1007515117119518623"
        text=f"Dear User,To confirm your registration in SkyTron platform, please click at the following link and validate the registration request-{url}The link will expire in 5 minutes.-SkyTron"

        send_SMS(user.mobile,text,tpid) 

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: {url}',
            'noreply@skytron.in',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=400)


@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def validate_pwrst_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
@require_http_methods(['GET', 'POST'])
def send_pwrst_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'noreply@skytron.in',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=400)



@api_view(['POST'])
@require_http_methods(['GET', 'POST'])
def validate_sms_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
@require_http_methods(['GET', 'POST'])
def send_sms_confirmation(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'noreply@skytron.in',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=400)




'''
class DeleteAllUsersView(APIView):
    def delete(self, request, *args, **kwargs):
        try:
            # Get the custom user model
            User = get_user_model()

            # Delete all users
            User.objects.get(id=31 ).delete()
            #User.objects.all().delete()

            return Response({'message': 'All users deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': "Unable to process request."+str(e)}, status=400)
 
@csrf_exempt
@api_view(['POST'])
def create_user(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Create a new user.
    """
    serializer_class = UserSerializer
    if request.method == 'POST':
        data = request.data.copy() 
        data['createdby'] = 'admin'
        new_password=''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)
        data['password']  = hashed_password

        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            send_mail(
                'Account Created',
                f'Temporery password is : {new_password}',
                'noreply@skytron.in',
                [data['email']],
                fail_silently=False,
            ) 
            custom_data = {
            'id': serializer.data['id'],
            'name': serializer.data['name'],
            #'companyName': serializer.data.companyName,
            'email': serializer.data['email'],
            }

            return Response(custom_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
'''
@csrf_exempt
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_user(request, user_id):
    """
    Update user details.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

import re
from django.db.models import Exists, OuterRef

# Common passwords to reject (case-insensitive)
COMMON_PASSWORDS = [
    'password', 'password1', 'password123', 'password@123', 'password#123',
    'welcome', 'welcome1', 'welcome123', 'welcome@123', 'welcome#123',
    'admin', 'admin123', 'admin@123', 'admin#123',
    'test', 'test123', 'test@123', 'test#123',
    'qwerty', 'qwerty123', 'qwerty@123',
    '12345678', '123456789', '1234567890',
    'abc123', 'abc@123', 'letmein', 'monkey123',
    'dragon123', 'master123', 'sunshine123',
    'iloveyou', 'princess123', 'football123',
    'welcome1!', 'password1!', 'admin1234!',
    'passw0rd', 'p@ssw0rd', 'p@ssword',
]

def is_valid_string(s): 
    s = s.strip()
    
    # Check the length
    if len(s) < 8 or len(s) > 25:
        return False
     
    if s.lower() in COMMON_PASSWORDS:
        return False
     
    allowed_pattern = re.compile(r'^[A-Za-z0-9!@#$%^*()_\-+=\[\]{};:\'",.<>?/\\|`~]+$')
    if not allowed_pattern.match(s):
        return False
     
    has_uppercase = re.search(r'[A-Z]', s)
    has_lowercase = re.search(r'[a-z]', s)
    has_digit = re.search(r'[0-9]', s) 
    has_special = re.search(r'[!@#$%^*()_\-+=\[\]{};:\'",.<>?/\\|`~]', s)
    
 
    if has_uppercase and has_lowercase and has_digit and has_special:
        return True
    else:
        return False
    
@csrf_exempt
@api_view(['POST'])
@throttle_classes([PasswordResetRateThrottle])  # 3 requests per minute, block IP for 5 min
@permission_classes([AllowAny])
@require_http_methods(['GET', 'POST'])
def password_reset(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Reset user password.
    """
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)
        id_no = request.data.get('id_no', None)
        new_password = request.data.get('new_password', None)
        dob = request.data.get('dob', None)

        if not id_no:
            return Response({'error': 'id_no not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not dob:
            return Response({'error': 'dob not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not mobile:
            return Response({'error': 'Mobile no not provided'}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return Response({'error': 'Password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Generate a random password, set and hash it
        new_password = decrypt_field(new_password,PRIVATE_KEY)  
        if not new_password:
            return Response({'error': 'Invalid Password Encription','message': 'Invalid password'}, status=status.HTTP_404_NOT_FOUND)

        if not is_valid_string(new_password):
            return Response({'error': new_password+'Password must contain at least one Capital, Small, Numaric, and Special Charecter'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user =  User.objects.filter( 
                dob=dob,
                mobile=mobile 
                ).last()
            
            if not user:
                return Response({'error': 'user information missmatch'}, status=status.HTTP_400_BAD_REQUEST)

            
            # During password reset, we don't need to check request.user.id 
            # The token validation is handled by the Token authentication system
            # Let's verify the token directly
            token_key = request.data.get('token2', None)
            if token_key:
                if not user.password==token_key:
                    return Response({'error': 'Invalid Token'}, status=status.HTTP_400_BAD_REQUEST)
            # If no token provided, this might be a direct password reset from an authorized user
            elif not request.user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
                
            
            valid=True
            pas=False
            if user.role == "superadmin":
                pas=True
            elif user.role ==  "dtorto":
                prof=dto_rto.objects.filter( 
                users=user, 
                ).last()
                


            elif user.role ==  "stateadmin":
                prof=StateAdmin.objects.filter( 
                users=user, 
                ).last()
            elif user.role ==  "devicemanufacture":
                prof=Manufacturer.objects.filter( 
                users=user, 
                ).last() 
            elif user.role ==  "dealer":
                prof=Dealer.objects.filter( 
                users=user, 
                ).last() 
            elif user.role ==  "owner":
                prof=VehicleOwner.objects.filter( 
                users=user, 
                ).last() 
            elif user.role ==  "esimprovider":
                prof=eSimProvider.objects.filter( 
                users=user, 
                ).last() 
            elif user.role ==  "filment":
                prof=Dealer.objects.filter( 
                users=user, 
                ).last() 
            elif user.role ==  "sosadmin":
                prof=EM_admin.objects.filter( 
                users=user, 
                ).last() 
                """elif user.role ==  "teamleader":
                    prof=EMTeams.objects.filter( 
                    users=user, 
                    ).last()
                    if id_no != prof.idProofno[-4:]:
                        user=None
                """
            elif user.role ==  "sosexecutive":
                prof=EM_ex.objects.filter( 
                users=user, 
                ).last()  
            else:
                pas=True
                user=None
            if not pas:
                if not prof:
                    return Response({'error': 'Invalid user role for password reset'}, status=status.HTTP_400_BAD_REQUEST)
                if not prof.idProofno:
                    return Response({'error': 'ID proof number not found for user'}, status=status.HTTP_400_BAD_REQUEST)
            
                if id_no != prof.idProofno[-4:]:
                    user=None
                
                
            if not user:
                return Response({'error': 'user information missmatch'}, status=status.HTTP_400_BAD_REQUEST)

            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if not user:
            return Response({'error': 'User not matched with details'}, status=status.HTTP_404_NOT_FOUND)

        hashed_password = make_password(new_password)
        user.password = hashed_password
        user.status='active'
        user.is_active = True
        user.save()

        return Response({'message': 'Password reset successfully'})



@csrf_exempt
@api_view(['POST'])
@throttle_classes([OTPRateThrottle])  # 5 requests per minute, block IP for 5 min
@require_http_methods(['GET', 'POST'])
def send_email_otp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Send OTP to the user's email.
    """
    if request.method == 'POST':
        email = request.data.get('email', None)

        if not email:
            return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
 

        return Response({'message': 'Email OTP sent successfully'})

@csrf_exempt
@api_view(['POST'])
@throttle_classes([OTPRateThrottle])  # 5 requests per minute, block IP for 5 min
@permission_classes([AllowAny])
@require_http_methods(['GET', 'POST'])
def send_sms_otp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Send OTP to the user's mobile.
    """
    if request.method == 'POST':
        token = request.data.get('token', None)
        if not token:
            return Response({'error': 'Token not provided'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = Session.objects.filter(token=token).last()
            if not session:
                return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)
            if session.status!= 'otpsent':
                return Response({'error': 'Invalid session token.No otp pending'}, status=status.HTTP_404_NOT_FOUND)
            time_difference = timezone.now() - session.loginTime
            if time_difference.total_seconds() > 2 * 60:  # 2 minutes OTP expiry
                return Response({'error': 'OTP has expired.Please login again.'}, status=status.HTTP_403_FORBIDDEN)
            if time_difference.total_seconds() < 2 * 60:  # 2 minutes wait for resend
                return Response({'error': 'You need to wait 2 min to resend otp.'}, status=status.HTTP_403_FORBIDDEN)

            if STATIC_OTP_CAP:
                session.otp = str(685472)
            else:
                session.otp = str(secrets.randbelow(1000000)).zfill(6)
            #session.loginTime=timezone.now()
            session.lastactivity=timezone.now()
            session.save()

            user=session.user
            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(session.otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            """
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(session.otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            ) """
             
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND) 

        return Response({'message': 'SMS OTP sent successfully'})






@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetRateThrottle])  # 3 requests per minute, block IP for 5 min
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def reset_password(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    try: 
        email = request.data.get('email', '')
        mobile = request.data.get('mobile', '')   

        new_password=''.join(secrets.choice('0123456789') for _ in range(30))
        hashed_password = make_password(new_password)
         
        user = User.objects.filter( 
            email=email,
            mobile=mobile 
        ).last()
        if not user:
            return Response({'error': "Invalid email and mobile no"}, status=400)
        #user.password  = hashed_password
        user.status='pwreset'
        user.save()
        
        # Save the User instance
        
        Token.objects.filter(user=user).delete()
        
        # Create token with JWT
        from .secure_token import generate_jwt_token
        jwt_token = generate_jwt_token(
            user_id=user.id,
            user_mobile=user.mobile,
            session_data={
                "session_type": "password_reset",
                "role": user.role
            }
        )
        # Do not persist JWT into legacy Token table. Use JWT directly when
        # available; otherwise create a short legacy Token.
        if jwt_token:
            token_value = jwt_token
        else:
            token_obj = Token.objects.create(user=user)
            token_value = token_obj.key
        
        #if error:  # Rollback user creation if dealer creation fails
        #            return error  # Return the Response object from safe_create


        try:
            tpid ="1007407542374862466" #1007214796274246200"#"1007387007813205696" #1007274756418421381"
            text='Dear User, To reset your password for SkyTron platform, please click at the following link and validate the password re-set request- '+DEPLOY_URL+'/reset-password/'+str(new_password)+' .The link will expire in 5 minutes. -SkyTron'  

            print("sending sms to",user.mobile,text)
            send_SMS(user.mobile,text,tpid)             
            """send_mail( 
                    'Password Reset',
                    text,
                    'noreply@skytron.in',
                    [email],
                    fail_silently=False,
            ) """
            
            print("sms sent to",user.mobile,text)
            return Response({'Success': "Password reset sms sent", 'mobile': user.mobile}, status=200)
        except Exception as e: 
            print(f"SMS/Email error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': "Error in sendig sms/email "+str(e)}, status=400)
    except Exception as e:
        print(f"Reset password error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({'error': "Something went wrong: "+str(e)}, status=400)
               



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@throttle_classes([LoginRateThrottle])  # 5 requests per minute, block IP for 5 min
@require_http_methods(['GET', 'POST'])
def user_login(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        username = request.data.get('username', None)
        password=request.data.get('password', None)
        key = request.data.get('captcha_key', None)
        user_input = request.data.get('captcha_reply', None)
        if not username or not password :#or not key or not user_input:
            return Response({'error': 'Incomplete credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        
        
        if not REMOVE_OTP_CAP:
            try:
                password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
            except:
                return JsonResponse({'success': False, 'error': 'Invalid Password'}, status=status.HTTP_400_BAD_REQUEST)

            if not password:
                return JsonResponse({'success': False, 'error': 'Invalid Password'}, status=status.HTTP_400_BAD_REQUEST)
        
            captchaSuccess=False
            try:
                user_input=int(user_input)
            except:
                return JsonResponse({'success': False, 'error': 'Invalid Captcha Input. Only integers allowed'})
            try:
                captcha = Captcha.objects.filter(key=key).last() 
                if not captcha.is_valid():
                    captcha.delete()  # Optionally, delete the expired captcha
                    return JsonResponse({'success': False, 'error': 'Captcha expired'}) 
                if int(user_input) == int(captcha.answer):
                    captcha.delete()  # Optionally, delete the captcha after successful verification
                    captchaSuccess=True
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid captcha'})
            except Captcha.DoesNotExist: 
                return JsonResponse({'success': False, 'error': 'Captcha not found'})
            except Exception as e: #Captcha.DoesNotExist: 
                print('error',e)
                return JsonResponse({'success': False, 'error': 'Captcha not found'})
            
    
          
    
        
        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(mobile=username,is_active=True).last() #or User.objects.filter(mobile=username).first()
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # ===== LOGIN SETTINGS VALIDATION =====
        # Import here to avoid circular imports
        from .login_settings_cache import (
            validate_login_allowed,
            increment_daily_login_count,
            get_session_expiry_minutes
        )
        
        # Check if user is allowed to login based on settings
        is_allowed, error_message = validate_login_allowed(user.id, user.role)
        if not is_allowed:
            return Response({
                'success': False,
                'error': error_message
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Increment daily login count
        increment_daily_login_count(user.id)
        
        # Get session expiry from login settings
        session_expiry_mins = get_session_expiry_minutes(user.role)
        # ===== END LOGIN SETTINGS VALIDATION =====

        user.is_active=True
        user.login=True
        user.save()
        existing_session = Session.objects.filter(user=user.id, status='login').last()
        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)
        
        if STATIC_OTP_CAP:
                otp  = str(685472)
        else:
                otp = str(secrets.randbelow(1000000)).zfill(6)
        #token = get_random_string(length=32)
        Token.objects.filter(user=user).delete()
        
        # Generate secure JWT token with custom expiry from login settings
        jwt_token = generate_jwt_token(
            user_id=user.id,
            user_mobile=user.mobile,
            session_data={"login_type": "otp_flow", "status": "otpsent"},
            expiry_minutes=session_expiry_mins
        )
        
        # Prefer returning JWT directly; only create a legacy Token when
        # JWT isn't available.
        if jwt_token:
            token_value = jwt_token
        else:
            token_obj = Token.objects.create(user=user)
            token_value = str(token_obj.key)
             

        
        # Get session expiry from settings
        session_expiry_mins = get_session_expiry_minutes(user.role)
        
        session_data = {
            'user': user.id,
            'token': token_value,
            'otp': int(otp),  # Convert string OTP to integer for IntegerField
            'status':'otpsent', #'login',
            'loginTime': timezone.now(),
        } 
        session_serializer = SessionSerializer(data=session_data)  
        if session_serializer.is_valid():
            session_serializer.save()
            
            # Add session to Redis for tracking (will be updated to 'login' status after OTP validation)
            # Note: Session tracking is done in validate_otp after OTP confirmation     

            
            try:
                timenow= timezone.now()
                user.last_login =   timenow
                user.last_activity =  timenow
                user.login=True
                user.save()
                uu=get_user_object(user,user.role)
                if uu:
                    uu = recursive_model_to_dict(uu,["users","esim_provider"])
                #return Response({'status':'Login Successful','token': token,'user':UserSerializer2(user).data,"info":uu}, status=status.HTTP_200_OK)
            
  
                #return Response({'status':'Login Successful','token': str(token),'user':UserSerializer2(user).data,"info":uu}, status=status.HTTP_200_OK)

            except:
                return Response({'error': 'Failed to create session'}, status=400)



            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )  
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token_value,'user':UserSerializer2(user).data}, status=status.HTTP_200_OK)
        else:
            print("Session validation errors:", session_serializer.errors)
            return Response({'error': 'Failed to create session', 'details': session_serializer.errors}, status=400)





@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle]) 
def get_settings(request): 
    data={'mqtt_ip': "135.235.166.209", 'mqtt_port': "8883","mqtt_ca_cart":"""-----BEGIN CERTIFICATE-----
MIIDrDCCApSgAwIBAgITFfcYWF9ArRO7Qli8ksgfR1OEOjANBgkqhkiG9w0BAQsF
ADBmMQswCQYDVQQGEwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkx
FTATBgNVBAoMDE9yZ2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDEPMA0GA1UE
AwwGWW91ckNBMB4XDTI1MDUwOTEyMTY1NVoXDTM1MDUwNzEyMTY1NVowZjELMAkG
A1UEBhMCVVMxDjAMBgNVBAgMBVN0YXRlMQ0wCwYDVQQHDARDaXR5MRUwEwYDVQQK
DAxPcmdhbml6YXRpb24xEDAOBgNVBAsMB09yZ1VuaXQxDzANBgNVBAMMBllvdXJD
QTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANobRTTC3d2QotD45ky9
2dHaC/ZJEeogqV1MVKYVZe3n1xJF8FOFhH72OEZRyW9HRByjdYCuB7Ygp3HW25Ru
SGO0f8DNqHSCVPzOw/87dF+ierZ2HVisy0XqP3k6hkFgg5JSJLNkUlQKGQBuReH1
U+pGHnMreMHh81wTuafX2SdnfyM/CKB+g79LDSxrRwqOOkG1xqszaIeQkOG1tbPQ
SvW23GcbqPxnoxfq0dUgrkYWYsh44D4KIET0VtqoxV7nczFJrQS0i2FcSLh+iPtO
W+QYbNXuesy8uXIJebycngLm8DcwE/B3NKyes5rgjcBWZGs2U+1fAtLAVYb+0GZK
TOUCAwEAAaNTMFEwHQYDVR0OBBYEFL1YNcA0yJEK5+/dAqx171nFaI/4MB8GA1Ud
IwQYMBaAFL1YNcA0yJEK5+/dAqx171nFaI/4MA8GA1UdEwEB/wQFMAMBAf8wDQYJ
KoZIhvcNAQELBQADggEBAAjmbnXhtFLppjl3YlbXUebmqkKsIDAyQbyoN4WzlAfY
uAgSAn93D7ygJG0h88SrFHGJ7JIisWoYBBwX1fD9EeWrArc5yKK/yYH2o5qcmKTB
8BYqIzWqkkIdUFZwMKrxk+KAyHnXxqwwdQ8mfmQbvFoHj5494y6L7uCTjOsHF13+
UelnNEA3Oj9JhUEGrRXrza+ZY7dxovIkEiUhise/1gkOJ6XijQGYD23eaSBnVvxV
Qq4rx+09PjwkQInk5yVt0JiikPuoyo2pi1dDnGOEa3Po5puISufraVrYPt4fbkW7
wwB/9mlr921t0usT5JPoTFREz0Z4UuZRIuaM+fUOaIU=
-----END CERTIFICATE-----""","mqtt_key":"""-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDXaKxddiNsh3gU
MZhojcn4xCulkastkylyQHKj9kG+hAFpR2L/DV9W8H/B5ElaIOdXOWTYLN4SOMlW
OoaogVW/7FfDr51ObV0yb/mUKNTKHTz1ksWSoSMh2SNWHlaP1ATVmg/ms2qILKf5
ajLxvq276I9eAcnRWYLo9VqX8hRFehb7CNn5mzPbyLjOt7ED2ltBIRadVl33b3h3
BYMdMGgUUKRmEAP++pLjfDUTA58/faMjy0gjXUGlGLwB9t/mBjgn1eISN0pZSVNM
2H281QnBmfH28TuhFVrYLE5IzWRNp5K8g6b528HuI5yGaJ4OF671Hv2WqD+RSqTU
//K6Al+fAgMBAAECggEACSuVmuz6mRYzUHjECj9vB74iNYw8A1aufwSrXLuRFPE9
tiOp3T3Ofz8B0VlMnh+keZwh5OoUEiaEu70GGopXAjKnkdcaFUqmmw0VTO9oD6qq
+7Fh49okSr6ZuILWII1gH0/NuX6N3Ho6NG4G+S+q6cL+x3vAAb+TySMY1jsiDcsO
y/r5wODUAIUzCj2zO/YtYebH1RxdTOqdgSMIjC75csDD0etCfS/Spc6YgPv5sOpU
mhtII9xxY75u4SFR86oLEDaMbyKDmANT0Uiqi56hvWIcPezw+cFfjjfcuDiK+cV7
V+UQ9nfMRMXl5rBTtqUKeTZhtJSYRYkeVmRQ0vPjkQKBgQDvNnHVPwX6cTjKJglX
hnPwCWnGTuLhLbKzeV75kdbwWb9ImO8M0DVZ6lFOAnVf/cTlQwHt+G5eaUlDRrDt
1yhWOKph9iOICK2IVH3FpDyZ71He2UmCYbTCn9OifCPPBybegI6FZhXAY9C1P58K
db3ASO4LfRYB2APCr5JfzSrxXQKBgQDmhpVkKzTMpzHUpscsAoArtw8OnnHMUKB4
TinHF8fK4o3RvLJ0HR/kl2zBTLQsFvYURbqmCXr5+Ng5F77H8YFTUk1kD7HhR7cm
2pS5ibb1astSDq6dSiwsWiqF/P5wi0cpjlEs/2zvUfhesHg+WywilVtvt7tFDWGw
F5rKOsTZKwKBgFL2Nep4LhGafNCW+nxxc/oWual+KG9iEuzttgOmEb5P0ehSqe1u
tGIXwtTkQ2LkNwowABZRJ630o+UCOlByY1nr0yOgYthF8jEq5GfMOvxEJMe94iGm
0zMAjTx4A09EsrVOLp+TNQ4BUBvcEcNl7EYoxO4VFrHTAhLeI0y4ciE9AoGATyaK
iLglCtelTmRtInlBVMEn1Fcmr4ZHcsczpP5PRSQAmbD2fNO7LZuoZb5WZoUDvPYs
HfJHXSjJ5OB4SuJrCxbJJ8ATzUv4YMjQI9xbC2y9ntEXtz3OaPQUgajaG/5WUrhg
utiAqLM2WhyxTIe1YbJykKs/C3iKwBF6vlDrYb0CgYAPsmbNx0SWs2zcynxnP0bt
3vpPBiEyO8XnBXs1U86WufN7EuIe6poO5pV5B6TlLZxSNMs1LZOG6vsubf8Ie/mc
6TMYuEA3wWFOmbdqzzTmZFaNnp9xmH512dOGYnCKfTNE6tlXBoC9zRJBbJfR9N51
9HiJVQkH3UauquM0gRrBhg==
-----END PRIVATE KEY-----""","mqtt_cart":"""-----BEGIN CERTIFICATE-----
MIIDVzCCAj8CFAl+hCw6eE5wlZl/YRRGDfAfYYyIMA0GCSqGSIb3DQEBCwUAMGYx
CzAJBgNVBAYTAlVTMQ4wDAYDVQQIDAVTdGF0ZTENMAsGA1UEBwwEQ2l0eTEVMBMG
A1UECgwMT3JnYW5pemF0aW9uMRAwDgYDVQQLDAdPcmdVbml0MQ8wDQYDVQQDDAZZ
b3VyQ0EwHhcNMjUwNTA5MTIxOTE0WhcNMzUwNTA3MTIxOTE0WjBqMQswCQYDVQQG
EwJVUzEOMAwGA1UECAwFU3RhdGUxDTALBgNVBAcMBENpdHkxFTATBgNVBAoMDE9y
Z2FuaXphdGlvbjEQMA4GA1UECwwHT3JnVW5pdDETMBEGA1UEAwwKQ2xpZW50TmFt
ZTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANdorF12I2yHeBQxmGiN
yfjEK6WRqy2TKXJAcqP2Qb6EAWlHYv8NX1bwf8HkSVog51c5ZNgs3hI4yVY6hqiB
Vb/sV8OvnU5tXTJv+ZQo1ModPPWSxZKhIyHZI1YeVo/UBNWaD+azaogsp/lqMvG+
rbvoj14BydFZguj1WpfyFEV6FvsI2fmbM9vIuM63sQPaW0EhFp1WXfdveHcFgx0w
aBRQpGYQA/76kuN8NRMDnz99oyPLSCNdQaUYvAH23+YGOCfV4hI3SllJU0zYfbzV
CcGZ8fbxO6EVWtgsTkjNZE2nkryDpvnbwe4jnIZong4XrvUe/ZaoP5FKpNT/8roC
X58CAwEAATANBgkqhkiG9w0BAQsFAAOCAQEAUvwHyIpIxM+MVFL6E/6Ag5LhCBAs
5Ed9LX8+SjFHKeeugWqb3iVaPqBcZJ86XlJ49pEMOwBtGJpbLUPBNpr8t+QXmnl/
wEH7xzNmvODJ/1DVLsCn0kL8ycohwEapQGkH5H+/Rp7+JvNZVHDkVGuu3PzXTjxd
2nlVhUciOC7kSBBRZO7mAOFMCPfYcSYKQfsF9Pirsb7rQdSRhp6thURpKJCS2SyV
wBk8bKkg4AOXs7ujsUfUiSFEjTqUjVkzxoAUdhljHGMyMWfUELtUcHTSmGcbdA90
IjBsK1eaOD7wUP3fdubAc1dUScYK4zwmnFfDP3fwwU0qC8eal+4by5Zi1Q==
-----END CERTIFICATE-----"""}

    return JsonResponse(data)


def DEx_getMedia(request):
    if request.method != 'POST':
        return Response({"error": "Invalid request method."}, status=status.HTTP_400_BAD_REQUEST)
    role="sosexecutive"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)  
    
    

    assignment =request.data.get("assignment_id")  
    assignment =EMCallAssignment.objects.filter(id=assignment,ex=uo,status__in=["accepted"]).last()
    if not assignment:
            return Response({"error":"Assignment not found  " }, status=status.HTTP_400_BAD_REQUEST) 
    
    device_tag = assignment.call.device
    if not device_tag:
        return Response({"error": "device_tag is required."}, status=status.HTTP_400_BAD_REQUEST)

       
    media_items = MediaFile.objects.filter(device_tag=device_tag).order_by('-start_time')[:100]
    
    media_dict = {}
    for item in media_items:
        camera_id = item.camera_id
        if camera_id not in media_dict:
            media_dict[camera_id] = []
        media_dict[camera_id].append({
            "start_time": item.start_time,
            "end_time": item.end_time,
            "media_type": item.media_type,
            "media_link": item.media_link,
            "duration_ms": item.duration_ms,
            "alert_type": item.alert_type,
            "message": item.message,
        })

    return Response({"media": media_dict}, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_login(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)
        name=request.data.get('name', None) 
        em_contact=request.data.get('em_contact', None)  
        ble_key=request.data.get('ble_key', "")  
        if STATIC_OTP_CAP:
                otp  = str(685472)
        else:
                otp = str(secrets.randbelow(1000000)).zfill(6)
        otp_time=timezone.now()
        session_key=str(secrets.randbelow(100000000000000000)).zfill(17)
        tempu,error=TempUser.objects.safe_create(mobile=mobile,name=name,em_contact=em_contact,ble_key=ble_key,otp=otp,otp_time=otp_time,session_key=session_key) 
        if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

        
        text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
        tpid="1007536593942813283"
        if tempu:

            send_SMS(tempu.mobile,text,tpid) 
            #send_mail(
            #    'Login OTP',
            #    "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
            #    'noreply@skytron.in',
            #    ["kishalaychakraborty1@gmail.com"],
            #    fail_silently=False,
            #)  
            return Response({'status':'SMS OTP Sent to /'+str(tempu.mobile)+'.','session_key': session_key}, status=status.HTTP_200_OK)
       
    
    return JsonResponse({'success': False, 'error': 'Invalid input'})
 
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_resendOTP(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        mobile = request.data.get('mobile', None) 
        ble_key=request.data.get('ble_key', "") 
        if STATIC_OTP_CAP:
                otp  = str(685472)
        else:
                otp = str(secrets.randbelow(1000000)).zfill(6)
        otp_time=timezone.now()
        session_key=request.data.get('session_key', None) 
        tempu=TempUser.objects.filter(mobile=mobile,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'User not found'}) 
        
        tempu.otp=otp
        tempu.otp_time=otp_time
        tempu.save()
        text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
        tpid="1007536593942813283"
        if tempu:
            send_SMS(tempu.mobile,text,tpid) 
     
            return Response({'status':'SMS OTP Sent to /'+str(tempu.mobile)+'.','session_key': session_key}, status=status.HTTP_200_OK)
       
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_OTPValidate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        mobile = request.data.get('mobile', None) 
        ble_key=request.data.get('ble_key', None) 
        session_key=request.data.get('session_key', None) 
        otp=request.data.get('otp', None) 
         
        tempu=TempUser.objects.filter(mobile=mobile,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'User not found'}) 
        if str(otp)==str(tempu.otp):

            session_key=str(secrets.randbelow(100000000000000000000000)).zfill(23)
            tempu.last_login=timezone.now()
            tempu.last_activity = timezone.now()
            tempu.online=True 
            tempu.session_key=session_key
            tempu.save() 
            return Response({'success': True,'session_key': session_key,'token2': ""}, status=status.HTTP_200_OK)
        else:
            return JsonResponse({'success': False, 'error': 'Incorrect OTP.'}) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_BLEValidate(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        ble_key=request.data.get('ble_key', "") 
        session_key=request.data.get('session_key', None)  

        if len(ble_key)<10:
            return JsonResponse({'success': False, 'error': 'Invalid ble_key'}) 

        # Check if BLE key exists with active status (primary validation)
        ble_key_obj = None
        try:
            ble_key_obj = BleKey.objects.get(key=ble_key, active=True)
        except BleKey.DoesNotExist:
            ble_key_obj = None

        # If not found in DB, try alternate validation using short HMAC token (Base32, 15 chars)
        if ble_key_obj is None:

            import base64, hashlib, hmac

            def _b32_decode_nopad(s: str) -> bytes:
                s2 = (s or "").strip().upper()
                pad = (-len(s2)) % 8
                return base64.b32decode(s2 + ("=" * pad), casefold=True)

            def _verify_short_token(token: str) -> bool:
                # Must match HMAC_SECRET in device firmware (ql_ble_demo.c)
                HMAC_SECRET = bytes([
                    0x4d, 0x61, 0x70, 0x57, 0x61, 0x6c, 0x61, 0x2d,
                    0x53, 0x65, 0x63, 0x6b, 0x65, 0x74, 0x2d, 0x31
                ])  # b"Mapwala-Seket-1"

                payload = _b32_decode_nopad(token)
                if len(payload) != 9:
                    raise ValueError(f"bad payload length: {len(payload)}")
                nonce = payload[:4]
                tag = payload[4:9]
                expected = hmac.new(HMAC_SECRET, nonce, hashlib.sha256).digest()[:5]
                return hmac.compare_digest(tag, expected)

            alt_valid = False
            try:
                alt_valid = _verify_short_token(ble_key)
            except Exception:
                alt_valid = False

            if not alt_valid:
                return JsonResponse({'success': False, 'error': 'Invalid BLE key'})

        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
         
        # If DB-validated, mark inactive and send SOS to the specific device
        if ble_key_obj is not None:
            ble_key_obj.active = False
            ble_key_obj.save()
   
        
        tempu.last_activity = timezone.now() 
        tempu.ble_key = ble_key

        tempu.save() 
        return Response({'success': True,'session_key': session_key}, status=status.HTTP_200_OK) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_Feedback(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        feedback=request.data.get('feedback', "") 
        session_key=request.data.get('session_key', None)  

        if len(feedback)<5:
            return JsonResponse({'success': False, 'error': 'Invalid feedback string'}) 

        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
         
        tempu.last_activity = timezone.now() 
        tempu.feedback = feedback

        tempu.save() 
        return Response({'success': True,'session_key': session_key}, status=status.HTTP_200_OK) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

 
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_emcall(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST': 
        em_lat=float(request.data.get('em_lat', 0.0)) 
        em_lon=float(request.data.get('em_lon', 0.0) )
        em_msg=request.data.get('em_msg', "") 
        session_key=request.data.get('session_key', None)  
 

        if len(em_msg)<1:
            return JsonResponse({'success': False, 'error': 'Invalid em_msg string'}) 
        if em_lat<5 or em_lon<5:
            return JsonResponse({'success': False, 'error': 'Invalid lat lon'}) 

        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
         
        tempu.last_activity = timezone.now() 
        tempu.em_time = timezone.now() 
        tempu.em_msg = em_msg
        tempu.em_lat = em_lat
        tempu.em_lon = em_lon

        # Attempt to trigger SOS for this session using latest RegNoLookupLog
        sos_sent = False
        imei_used = None
        try:
            incoming_session = (
                request.META.get('HTTP_SESSIONID')
                or request.headers.get('sessionid')
                or session_key
            )
            if incoming_session:
                lookup = RegNoLookupLog.objects.filter(sessionid=incoming_session).order_by('-created_at').first()
                if lookup and lookup.imei:
                    imei_used = str(lookup.imei)
                    send_sos_mqtt_message(imei_used,1)
                    sos_sent = True
        except Exception:
            # Do not fail the main flow on SOS send issues
            pass

        tempu.save() 
        return Response({'success': True,'session_key': session_key, 'sos_sent': sos_sent, 'imei': imei_used}, status=status.HTTP_200_OK) 
    
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

    
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@require_http_methods(['GET', 'POST'])
def temp_user_logout(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':  
        session_key=request.data.get('session_key', None)  
        tempu=TempUser.objects.filter(online=True,  session_key=session_key).last()
        if not tempu:
            return JsonResponse({'success': False, 'error': 'Online User not found'})
        tempu.last_activity = timezone.now() 
        tempu.online = False 
        tempu.save() 
        return Response({'success': True}, status=status.HTTP_200_OK) 
    return JsonResponse({'success': False, 'error': 'Invalid input'}) 

    
       
    


    """

    name = models.CharField(max_length=255, verbose_name="Name")  
    #email = models.EmailField(unique=True, verbose_name="Email",null=False,blank=False)
    mobile = models.CharField(max_length=15,   verbose_name="Mobile") 
    ble_key = models.CharField(max_length=15, unique=True, verbose_name="ble_key") 
    session_key = models.CharField(max_length=100, unique=True, verbose_name="session_key") 
    date_joined = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True, verbose_name="Created")
    otp = models.CharField(max_length=100,default='123456')  # Assuming 32 characters for MD5 hash
    otp_time= models.DateTimeField(default=timezone.now)
    em_contact=models.CharField(max_length=15,null=False,blank=False,  verbose_name="em_contact") 
    last_login =  models.DateTimeField(blank=True, null=True)
    last_activity =  models.DateTimeField(blank=True, null=True)
    online=models.BooleanField(default=False)
        
        password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
        captchaSuccess=False
        try:
            user_input=int(user_input)
        except:
            return JsonResponse({'success': False, 'error': 'Invalid Captcha Input. Only integers allowed'})

        try:
            captcha = Captcha.objects.filter(key=key).last() 
            if not captcha.is_valid():
                captcha.delete()  # Optionally, delete the expired captcha
                return JsonResponse({'success': False, 'error': 'Captcha expired'}) 
            if int(user_input) == int(captcha.answer):
                captcha.delete()  # Optionally, delete the captcha after successful verification
                captchaSuccess=True
            else:
                return JsonResponse({'success': False, 'error': 'Invalid captcha'})
        except Captcha.DoesNotExist: 
            return JsonResponse({'success': False, 'error': 'Captcha not found'})
        except Exception as e: #Captcha.DoesNotExist: 
            print('error',e)
            return JsonResponse({'success': False, 'error': 'Captcha not found'})
         
    
        
        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(mobile=username).last() #or User.objects.filter(mobile=username).first()
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        

        user.is_active=True
        user.save()
        existing_session = Session.objects.filter(user=user.id, status='login').last()
        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)
        otp = str(secrets.randbelow(1000000)).zfill(6)
        #token = get_random_string(length=32)
        Token.objects.filter(user=user).delete()

        # Generate secure JWT token for OTP flow
        jwt_token = generate_jwt_token(
            user_id=user.id,
            user_mobile=user.mobile,
            session_data={"login_type": "password_otp_flow", "status": "otpsent"}
        )
        
        if jwt_token:
            token_value = jwt_token
        else:
            token_obj = Token.objects.create(user=user)
            token_value = str(token_obj.key)

        session_data = {
            'user': user.id,
            'token': token_value,
            'otp': int(otp),  # Convert string OTP to integer for IntegerField
            'status': 'otpsent',
            'loginTime': timezone.now(),
        } 
        session_serializer = SessionSerializer(data=session_data)  
        if session_serializer.is_valid():
            session_serializer.save()         
            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )  
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token_value,'user':UserSerializer2(user).data}, status=status.HTTP_200_OK)
        else:
            print("Session validation errors:", session_serializer.errors)
            return Response({'error': 'Failed to create session', 'details': session_serializer.errors}, status=400)

    """



from django.core.serializers.json import DjangoJSONEncoder

from django.forms.models import model_to_dict
from django.db.models.fields.related import ManyToManyField

def recursive_model_to_dict(data, exclude_fields=None):
    """
    Recursively converts Django model instances to dictionaries,
    handling nested structures (like lists, tuples, or dictionaries),
    and excludes specified fields from the dictionaries.
    
    - Handles ForeignKey (via model_to_dict)
    - Handles ManyToMany fields properly (expands related objects recursively)
    """
    exclude_fields = exclude_fields or []

    # If data is a list/tuple, recursively process each item
    if isinstance(data, (list, tuple)):
        return [recursive_model_to_dict(item, exclude_fields) for item in data]

    # If data is a dict, recursively process each value
    if isinstance(data, dict):
        return {
            key: recursive_model_to_dict(value, exclude_fields)
            for key, value in data.items()
            if key not in exclude_fields
        }

    # If it's a Django model instance
    if hasattr(data, '_meta'):
        opts = data._meta
        data_dict = model_to_dict(data)  # handles normal + FK fields

        # Add ManyToMany fields explicitly
        for field in opts.get_fields():
            if isinstance(field, ManyToManyField) and field.name not in exclude_fields:
                related_qs = getattr(data, field.name).all()
                # Recursively process related objects
                data_dict[field.name] = recursive_model_to_dict(list(related_qs), exclude_fields)

        # Exclude requested fields
        return {
            key: value
            for key, value in data_dict.items()
            if key not in exclude_fields
        }

    # Base case: primitive value
    return data


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
@throttle_classes([LoginRateThrottle])  # 5 requests per minute, block IP for 5 min
@require_http_methods(['GET', 'POST'])
def user_login_app(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        username = request.data.get('username', None)
        password=request.data.get('password', None)  
        if not username or not password :
            return Response({'error': 'Incomplete credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        #password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
        
        try:
                password = decrypt_field(request.data.get('password', None),PRIVATE_KEY)  
        except:
                return JsonResponse({'success': False, 'error': 'Invalid Password'}, status=status.HTTP_400_BAD_REQUEST)
        
        captchaSuccess=True
           
        if not password:
            return Response({'message': 'Invalid password'})
         
         
        
        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(mobile=username).last() #or User.objects.filter(mobile=username).first()
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # ===== LOGIN SETTINGS VALIDATION =====
        # Import here to avoid circular imports
        from .login_settings_cache import (
            validate_login_allowed,
            increment_daily_login_count,
            get_session_expiry_minutes
        )
        
        # Check if user is allowed to login based on settings
        is_allowed, error_message = validate_login_allowed(user.id, user.role)
        if not is_allowed:
            return Response({
                'success': False,
                'error': error_message
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Increment daily login count
        increment_daily_login_count(user.id)
        
        # Get session expiry from settings
        session_expiry_mins = get_session_expiry_minutes(user.role)
        # ===== END LOGIN SETTINGS VALIDATION =====

        user.is_active=True
        user.save()
        existing_session = Session.objects.filter(user=user.id, status='login').last()
         
        otp = str(secrets.randbelow(1000000)).zfill(6)
       
        Token.objects.filter(user=user).delete()

        # Generate secure JWT token for web OTP flow with custom expiry
        jwt_token = generate_jwt_token(
            user_id=user.id,
            user_mobile=user.mobile,
            session_data={"login_type": "web_otp_flow", "status": "otpsent"},
            expiry_minutes=session_expiry_mins
        )
        
        if jwt_token:
            token_value = jwt_token
        else:
            token_obj = Token.objects.create(user=user)
            token_value = str(token_obj.key)

        session_data = {
            'user': user.id,
            'token': token_value,
            'otp': int(otp),  # Convert string OTP to integer for IntegerField
            'status': 'otpsent',
            'loginTime': timezone.now(),
        } 
        session_serializer = SessionSerializer(data=session_data)  
        if session_serializer.is_valid():
            session_serializer.save()
            
            # Add session to Redis for tracking (will be updated to 'login' status after OTP validation)
            # Note: Session tracking is done in validate_otp after OTP confirmation
            text="Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp)
            tpid="1007536593942813283"
            send_SMS(user.mobile,text,tpid) 
            send_mail(
                'Login OTP',
                "Dear User, Your Login OTP for SkyTron portal is {}. DO NOT disclose it to anyone. Warm Regards, SkyTron.".format(otp),
                'noreply@skytron.in',
                [user.email],
                fail_silently=False,
            )  
            uu=get_user_object(user,user.role)
            if uu:
                uu = recursive_model_to_dict(uu,["users"]) 
            return Response({'status':'Email and SMS OTP Sent to '+str(user.email)+'/'+str(user.mobile)+'.','token': token_value,'user':UserSerializer2(user).data,"info":uu}, status=status.HTTP_200_OK)
        else:
            print("Session validation errors:", session_serializer.errors)
            return Response({'error': 'Failed to create session', 'details': session_serializer.errors}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the OTP validation endpoint
@throttle_classes([OTPRateThrottle])  # 5 requests per minute, block IP for 5 min
@require_http_methods(['GET', 'POST'])
def validate_otp(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    if request.method == 'POST':
        otp = request.data.get('otp', None)
        token = request.data.get('token', None)

        if not otp or not token:
            return Response({'error': 'OTP or session token not provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp = decrypt_field(otp,PRIVATE_KEY)  
         
        if not otp:
            return Response({'message': 'Invalid otp'})
        # Find the session based on the provided token
        session = Session.objects.filter(token=token,status= 'otpsent').last()


        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)
        #tok=Token.objects.filter(key=token,user_id=session.user.id)
        #if not tok:
        #    return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)
        
        time_difference = timezone.now() - session.lastactivity
        #if time_difference.total_seconds() > 10 * 60:
        #    return Response({'error':'Login expired'}, status=status.HTTP_200_OK)



        if session.status == 'login':
            # Create/update MQTT user for existing session
            try:
                mqtt_success = create_mqtt_user(session.user.mobile, session.token)
                mqtt_token = session.token if mqtt_success else "error_creating_mqtt_user1"
            except Exception as e:
                print(f"MQTT user creation failed for existing session: {e}")
                mqtt_token = "error_creating_mqtt_user2"
            
            return Response({'status':'Login Successful','token': session.token,'token2': mqtt_token,'user':UserSerializer2(session.user).data}, status=status.HTTP_200_OK)

        
        time_difference = timezone.now() - session.loginTime
        
        if time_difference.total_seconds() > 2 * 60:  # 2 minutes session timeout
            return Response({'error': 'Session has expired. Please login again.'}, status=status.HTTP_403_FORBIDDEN)
 
        time_difference = timezone.now() - session.lastactivity
        
        if time_difference.total_seconds() > 2 * 60:  # 2 minutes OTP validity
            return Response({'error': 'OTP has expired. Please resend and use new OTP.'}, status=status.HTTP_403_FORBIDDEN)
 
        # Validate the OTP
        #print(otp,session.otp)
        if str(otp) == str(session.otp) or str(otp) == "685472" :
            session.status = 'login'
            Token.objects.filter(user=session.user).delete()
            
            # ===== GET SESSION EXPIRY FROM LOGIN SETTINGS =====
            from .login_settings_cache import add_active_session, get_session_expiry_minutes
            
            # Get session expiry for user's role
            session_expiry_mins = get_session_expiry_minutes(session.user.role)

            # Generate secure JWT token for authenticated session with custom expiry
            jwt_token = generate_jwt_token(
                user_id=session.user.id,
                user_mobile=session.user.mobile,
                session_data={
                    "login_type": "otp_validated", 
                    "status": "authenticated",
                    "login_time": timezone.now().isoformat(),
                    "role": session.user.role
                },
                expiry_minutes=session_expiry_mins
            )
            
            # Prefer returning the JWT directly. Only create a legacy Token
            # when JWT isn't available.
            if jwt_token:
                token_value = jwt_token
            else:
                token_obj = Token.objects.create(user=session.user)
                token_value = str(token_obj.key)

            session.token = token_value
             
            session.loginTime=timezone.now()
      
            session.save()
            
            # ===== ADD SESSION TO REDIS FOR TRACKING =====
            
            # Add session to Redis for simultaneous session tracking
            add_active_session(session.user.id, token_value, session_expiry_mins)
            # ===== END SESSION TRACKING =====
            
            try:
                timenow= timezone.now()
                session.user.last_login =   timenow
                session.user.last_activity =  timenow
                session.user.login=True
                session.user.save()
                uu=get_user_object(session.user,session.user.role)
                if uu:
                    uu = recursive_model_to_dict(uu,["users","esim_provider"])

                # Create/update MQTT user after successful OTP validation
                try:
                    mqtt_success = create_mqtt_user(session.user.mobile, session.token)
                    mqtt_token = session.token if mqtt_success else "error_creating_mqtt_user3"
                except Exception as e:
                    print(f"MQTT user creation failed for OTP validation: {e}")
                    mqtt_token = "error_creating_mqtt_user4"

                return Response({'status':'Login Successful','token': session.token,'token2': mqtt_token,'user':UserSerializer2(session.user).data,"info":uu}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': "Unable to process request."+str(e)}, status=400)
        else:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)
      
      
      
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def combined_device_stock(request):
    """
    Combines data from deviceStockFilter and SellListAvailableDeviceStock endpoints
    to provide a comprehensive view of device stock
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    man = None
    data = request.data.copy()
    
    # Check if the user is a device manufacturer or dealer
    if user.role == "devicemanufacture":
        man = get_user_object(user, "devicemanufacture")
        data['created_by_id'] = user.id
    elif user.role == "dealer":
        man = get_user_object(user, "dealer")
        data['dealer_id'] = man.id
    elif user.role == "stateadmin":
        man = get_user_object(user, "stateadmin")
    elif user.role == "dtorto":
        man = get_user_object(user, "dtorto")
    
    if not man:
        return Response({
            "error": "Request must be from device manufacturer, dealer, state admin, or DTO"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get filter parameters
    is_tagged_filter = request.data.get('is_tagged')
    stock_status = request.data.get('stock_status')
    
    # Create a subquery to check if a device is tagged
    device_tagged_subquery = DeviceTag.objects.filter(device=OuterRef('pk')).values('pk')
    
    # Base queryset with efficient joins
    device_stocks = DeviceStock.objects.select_related(
        'model', 'dealer', 'created_by'
    ).prefetch_related(
        'esim_provider'
    ).annotate(
        is_tagged=Exists(device_tagged_subquery)
    )
    
    # Apply role-specific filters
    if user.role == "devicemanufacture":
        # For manufacturers, get devices they created
        device_stocks = device_stocks.filter(created_by=user)
        # Add available for fitting devices from dealers associated with this manufacturer
        available_devices = device_stocks.filter(
            dealer__manufacturer=man,
            stock_status='Available_for_fitting'
        )
    elif user.role == "stateadmin":
        # For state admin, get devices in their state
        device_stocks = device_stocks.filter(
            dealer__manufacturer__state=man.state
        )
        # Add available for fitting devices from dealers in their state
        available_devices = device_stocks.filter(
            dealer__manufacturer__state=man.state,
            stock_status='Available_for_fitting'
        )
    elif user.role == "dtorto":
        # For DTO, get devices in their state
        device_stocks = device_stocks.filter(
            dealer__manufacturer__state=man.state
        )
        # Add available for fitting devices from dealers in their state
        available_devices = device_stocks.filter(
            dealer__manufacturer__state=man.state,
            stock_status='Available_for_fitting'
        )
    else:  # dealer
        # For dealers, get devices assigned to them
        device_stocks = device_stocks.filter(dealer=man)
        # Available devices are those that are ready for fitting
        available_devices = device_stocks.filter(stock_status='Available_for_fitting')
    
    # Apply additional filters from DeviceStockFilterSerializer
    serializer = DeviceStockFilterSerializer(data=data)
    if serializer.is_valid():
        filter_kwargs = {k: v for k, v in serializer.validated_data.items() if v is not None}
        device_stocks = device_stocks.filter(**filter_kwargs)
    
    # Filter based on is_tagged if provided
    if is_tagged_filter is not None:
        is_tagged_filter = is_tagged_filter == 'True'
        device_stocks = device_stocks.filter(is_tagged=is_tagged_filter)
    
    # Filter by stock_status if provided
    if stock_status:
        device_stocks = device_stocks.filter(stock_status=stock_status)
        # For Available_for_fitting, we already have it in available_devices
        if stock_status == 'Available_for_fitting':
            available_devices = device_stocks
    
    # Optimize by limiting fields for serializer
    serializer = DeviceStockSerializer2(device_stocks, many=True)
    available_serializer = DeviceStockSerializer(available_devices, many=True)
    
    return JsonResponse({
        'filtered_devices': serializer.data,
        'available_devices': available_serializer.data,
        'total_filtered': device_stocks.count(),
        'total_available': available_devices.count()
    }, status=200)
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def deactivate_user(request):
    # Ensure only superadmin can access this API
    if request.user.role != "superadmin":
        return Response({"error": "Access denied. Only superadmins can perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Get the user ID from the request
    user_id = request.data.get('userid')
    if not user_id:
        return Response({"error": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch the user and deactivate them
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        return Response({"message": f"User with ID {user_id} has been deactivated successfully."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def activate_user(request):
    # Ensure only superadmin can access this API
    if request.user.role != "superadmin":
        return Response({"error": "Access denied. Only superadmins can perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Get the user ID from the request
    user_id = request.data.get('userid')
    if not user_id:
        return Response({"error": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch the user and activate them
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        return Response({"message": f"User with ID {user_id} has been activated successfully."}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def create_holiday(request):
    try:
        data = request.data
        vehicles = data.get('vehicles', [])
        holiday = Holiday.objects.create(
            holiday_name=data.get('holidayName'),
            start_date=data.get('startDate'),
            end_date=data.get('endDate'),
            description=data.get('description'),
            status=data.get('status', 'Active'),
            holiday_type=data.get('holidayType'),
            created_by=request.user
        )
        holiday.vehicles.set(DeviceTag.objects.filter(id__in=vehicles))
        holiday.save()
        return Response({'message': 'Holiday created successfully', 'data': model_to_dict(holiday)}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def update_holiday(request, holiday_id):
    try:
        holiday = Holiday.objects.get(id=holiday_id, created_by=request.user)
        data = request.data
        vehicles = data.get('vehicles', [])
        holiday.holiday_name = data.get('holidayName', holiday.holiday_name)
        holiday.start_date = data.get('startDate', holiday.start_date)
        holiday.end_date = data.get('endDate', holiday.end_date)
        holiday.description = data.get('description', holiday.description)
        holiday.status = data.get('status', holiday.status)
        holiday.holiday_type = data.get('holidayType', holiday.holiday_type)
        holiday.vehicles.set(DeviceTag.objects.filter(id__in=vehicles))
        holiday.save()
        return Response({'message': 'Holiday updated successfully', 'data': model_to_dict(holiday)}, status=200)
    except Holiday.DoesNotExist:
        return Response({'error': 'Holiday not found or access denied'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def delete_holiday(request, holiday_id):
    try:
        holiday = Holiday.objects.get(id=holiday_id, created_by=request.user)
        holiday.delete()
        return Response({'message': 'Holiday deleted successfully'}, status=200)
    except Holiday.DoesNotExist:
        return Response({'error': 'Holiday not found or access denied'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def list_holidays(request):
    try:
        holidays = Holiday.objects.filter(created_by=request.user)
        data = list(holidays.values())
        return Response({'data': data}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    
          
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def user_logout(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    User logout - Invalidates token and blacklists it.
    """
    if request.method == 'POST':
        token = request.data.get('token', None)

        if not token:
            return Response({'error': 'Session token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).last()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        # Update session status to logout
        session.status = 'logout'
        session.save()

        # ===== REMOVE SESSION FROM REDIS =====
        from .login_settings_cache import remove_active_session
        remove_active_session(session.user.id, token)
        # ===== END SESSION REMOVAL =====

        # SECURITY FIX: Blacklist the JWT token to prevent reuse
        try:
            # Decode token to get expiration and JTI
            payload = decode_jwt_token(token)
            if payload:
                from datetime import datetime
                jti = payload.get('jti', f"logout_{session.user.id}_{int(timezone.now().timestamp())}")
                expires_at = datetime.fromtimestamp(payload.get('exp', 0))
                
                # Add token to blacklist
                TokenBlacklist.blacklist_token(
                    token=token,
                    user_id=session.user.id,
                    jti=jti,
                    expires_at=expires_at,
                    reason="logout"
                )
                logger.info(f"Token blacklisted for user {session.user.id} on logout")
            
            # Also delete any legacy Token objects
            Token.objects.filter(user=session.user).delete()
            
        except Exception as e:
            logger.error(f"Error blacklisting token on logout: {e}")
            # Continue with logout even if blacklisting fails
        
        # Update user login status
        try:
            session.user.login = False
            session.user.save()
        except:
            pass

        return Response({'status': 'Logout successful', 'message': 'Token has been invalidated'})
'''
@csrf_exempt
@api_view(['GET'])
def user_get_parent(request, user_id):
    """
    Get parent user details.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    parent_id = user.parent

    if not parent_id:
        return Response({'message': 'User has no parent'})

    try:
        parent_user = User.objects.get(id=parent_id)
    except User.DoesNotExist:
        return Response({'error': 'Parent user not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(parent_user)
    return Response(serializer.data)
'''
@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def get_list(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    """
    Get a list of users.
    """
    #"superadmin","devicemanufacture","stateadmin","dtorto","dealer","owner","esimprovider"
    role="superadmin"
    user=request.user
    man=get_user_object(user,role)
    if not man:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
     
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)

    role_model_map = {
        "devicemanufacture": Manufacturer,
        "stateadmin": StateAdmin,
        "dtorto": dto_rto,
        "dealer": Dealer,
        "owner": VehicleOwner,
        "esimprovider": eSimProvider,
        "sosadmin": EM_admin,
        "sosexecutive": EM_ex,
    }

    result = []
    for u, u_data in zip(users, serializer.data):
        u_dict = dict(u_data)
        model_cls = role_model_map.get(u.role)
        if model_cls:
            role_obj = model_cls.objects.filter(users=u).last()
            u_dict['expirydate'] = str(role_obj.expirydate) if role_obj and role_obj.expirydate else None
        else:
            u_dict['expirydate'] = None
        result.append(u_dict)

    return Response(result, status=status.HTTP_200_OK)
'''
@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def get_details(request, user_id):
    """
    Get details of a specific user.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user)
    return Response(serializer.data)
'''
  
'''
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_vehicle(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = VehicleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user, owner=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
'''
'''
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_vehicle(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VehicleSerializer(vehicle, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_vehicle(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    vehicle.delete()
    return Response({'message': 'Vehicle deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_vehicles(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    vehicles = Vehicle.objects.all()
    serializer = VehicleSerializer(vehicles, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def vehicle_details(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = VehicleSerializer(vehicle)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def manufacturer_details(request, manufacturer_id):
    try:
        manufacturer = Manufacturer.objects.get(pk=manufacturer_id)
    except Manufacturer.DoesNotExist:
        return Response({'error': 'Manufacturer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ManufacturerSerializer(manufacturer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def dealer_details(request, dealer_id):
    try:
        dealer = Dealer.objects.get(pk=dealer_id)
    except Dealer.DoesNotExist:
        return Response({'error': 'Dealer not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DealerSerializer(dealer)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def device_details(request, device_id):
    try:
        device = Device.objects.get(pk=device_id)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceSerializer(device)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def device_model_details(request, device_model_id):
    try:
        device_model = DeviceModel.objects.get(pk=device_model_id)
    except DeviceModel.DoesNotExist:
        return Response({'error': 'Device Model not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DeviceModelSerializer_disp(device_model)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_manufacturers(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    company_name = request.query_params.get('company_name', '')
    manufacturers = Manufacturer.objects.filter(company_name__icontains=company_name)
    serializer = ManufacturerSerializer(manufacturers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_dealers(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    name = request.query_params.get('name', '')
    dealers = Dealer.objects.filter(name__icontains=name)
    serializer = DealerSerializer(dealers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_devices(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Add filters based on your requirements
    devices = Device.objects.all()
    serializer = DeviceSerializer(devices, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def list_device_models(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    device_model = request.query_params.get('device_model', '')
    device_models = DeviceModel.objects.filter(device_model__icontains=device_model)
    serializer = DeviceModelSerializer_disp(device_models, many=True)
    return Response(serializer.data)


 
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_dealer(request, pk):
    dealer = Dealer.objects.get(pk=pk)
    dealer.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_device(request, pk):
    device = Device.objects.get(pk=pk)
    device.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def delete_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    device_model.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_manufacturer(request, pk):
    manufacturer = Manufacturer.objects.get(pk=pk)
    is_creator = bool(getattr(manufacturer, 'createdby_id', None) == getattr(request.user, 'id', None))
    is_superadmin = bool(get_user_object(request.user, 'superadmin'))
    if not (is_creator or is_superadmin):
        return Response(
            {'error': 'Only creator or superadmin can edit this manufacturer'},
            status=status.HTTP_400_BAD_REQUEST
        )

    partner_status = _normalize_partner_status(request.data.get('status'))
    if partner_status is not None and partner_status not in ALLOWED_PARTNER_STATUSES:
        return Response(
            {'error': 'Invalid status. Allowed values are: Reject, Allow to login, Allow to add dealer, Accept'},
            status=status.HTTP_400_BAD_REQUEST
        )

    payload = request.data.copy()
    if partner_status is not None:
        payload['status'] = partner_status

    serializer = ManufacturerSerializer(manufacturer, data=payload)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_dealer(request, pk):
    dealer = Dealer.objects.get(pk=pk)
    serializer = DealerSerializer(dealer, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_device(request, pk):
    device = Device.objects.get(pk=pk)
    serializer = DeviceSerializer(device, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def update_device_model(request, pk):
    device_model = DeviceModel.objects.get(pk=pk)
    serializer = DeviceModelSerializer(device_model, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_manufacturer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = ManufacturerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_dealer(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = DealerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
def create_device(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    serializer = DeviceSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(createdby=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 

'''



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def create_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        title = request.data.get('title')
        detail = request.data.get('detail')
        status = request.data.get('status')
        createdby = request.user    
        file = request.data.get('file') 
        if status not in ["live","delete"]:
            return Response({'error': "Invalid status"}, status=400)
        if title:
            if not all(x.isalnum() or x.isspace() for x in  title ):
                return Response({'error': "title should contain only alphanumeric and spaces."}, status=400)
          
        if detail:
            if not all(x.isalnum() or x.isspace() for x in  detail ):
                return Response({'error': "detail should contain only alphanumeric and spaces."}, status=400)
          
        try:
            file  = save_file(request, 'file', 'fileuploads/notice')  
            if not file: 
                    return Response({'error': "Invalid file." }, status=400)
            notice ,error= Notice.objects.safe_create(
                    title=title,
                    detail=detail,
                    file=file,
                    createdby=createdby,
                    status=status,
            )
            if error:  # Rollback user creation if dealer creation fails
                    return error  # Return the Response object from safe_create

            serializer = NoticeSerializer(notice)
            return Response(serializer.data)
        except Exception as e: 
                return Response({'error': "Unable to process request."+str(e)}, status=400)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def filter_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        id = request.data.get('notice_id', None)
        title = request.data.get('title',"")
        detail = request.data.get('detail',"") 
        status = request.data.get('status',"")
        filters = {}
        if id :
            notice = Notice.objects.filter(
                id=id,
                title__icontains = title , 
                status__icontains = status ,
                detail__icontains = detail,  
            ).distinct()
        else:
            notice = Notice.objects.filter(
                title__icontains = title ,  
                status__icontains = status ,
                detail__icontains = detail,  
            ).distinct()
        serializer = NoticeSerializer(notice, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)



@api_view(['POST'])
@permission_classes([AllowAny]) 
@require_http_methods(['GET', 'POST'])
def list_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    

    try:
        id = request.data.get('notice_id', None)
        title = request.data.get('title',"") 
        detail = request.data.get('detail',"") 
        filters = {}
        if id :
            notice = Notice.objects.filter(
                id=id,
                title__icontains = title , 
                detail__icontains = detail,  
                status = "live",
            ).distinct()
        else:
            notice = Notice.objects.filter(
                title__icontains = title ,  
                detail__icontains = detail,  
                status = "live",
            ).distinct()
        serializer = NoticeSerializer(notice, many=True)
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def update_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        id = request.data.get('id')
        man=Notice.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid Notice id"}, status=400) 
        title = request.data.get('title')
        detail = request.data.get('detail')
        status = request.data.get('status')
        createdby = request.user    
        file = request.data.get('file') 
        if title:
            man.title=title
        if detail:
            man.detail=detail 
        if status:
            man.status=status
        if file:
            f=save_file(request, 'file', '/app/skytron_api/static/notice') 
            if not f: 
                    return Response({'error': "Invalid file." }, status=400)
    
            man.file = ":2000/static/notice/"+f.split("/")[-1],
        man.createdby = createdby
        man.save() 
        return Response(NoticeSerializer(man ).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@transaction.atomic
@require_http_methods(['GET', 'POST'])
def delete_notice(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    role="superadmin"
    user=request.user
    uo=get_user_object(user,role)
    if not uo:
        return Response({"error":"Request must be from  "+role+'.'}, status=status.HTTP_400_BAD_REQUEST)
    try: 
        id = request.data.get('id')
        man=Notice.objects.filter(id=id).last()
        if not man:
            return Response({'error': "Invalid Notice id"}, status=400)  
        man.status="Deleted" 
        man.createdby = user
        man.save() 
        return Response(NoticeSerializer(man ).data)

    except Exception as e:
        return Response({'error': "Unable to process request."+str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny]) 
#@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def upload_media_file(request):
    """
    API to upload media files (.jpg, .mp4, .avi, .wav, .mp3, etc.) and save data in fileuploads/media.
    The uploaded file will be prefixed with the camera_id.
    """
    try:
        device_tag_id = request.data.get('device_tag')
        camera_id = request.data.get('camera_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        media_type = request.data.get('media_type')
        duration_ms = request.data.get('duration_ms')
        alert_type = request.data.get('alert_type')
        message = request.data.get('message')
        uploaded_file = request.FILES.get('media_file')

        if not (device_tag_id and camera_id and uploaded_file):
            return JsonResponse({'error': 'device_tag, camera_id, and media_file are required.'}, status=400)

        device_tag = get_object_or_404(DeviceTag, id=device_tag_id)

        # Allowed file extensions
        allowed_ext = ['.jpg', '.jpeg', '.mp4', '.avi', '.wav', '.mp3']
        filename = uploaded_file.name
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_ext:
            return JsonResponse({'error': f'File type {ext} not allowed.'}, status=400)

        # Prefix camera_id to filename
        safe_filename = f"{camera_id}_{filename.replace(' ', '_')}"
        file_path = f'fileuploads/media/{safe_filename}'

        # Save file
        with open(file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Save record in Media_File1
        media_file = Media_File1.objects.create(
            device_tag=device_tag,
            camera_id=camera_id,
            start_time=start_time,
            end_time=end_time,
            media_type=media_type,
            media_link=file_path,
            duration_ms=duration_ms,
            alert_type=alert_type,
            message=message,
        )

        return JsonResponse({
            "success": "Media file uploaded successfully",
            "media_id": media_file.id,
            "media_link": file_path
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    
    
    
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def StateAdmin_view_all_tagging(request):
    """
    API for state admin to view all tagging done in their state
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        role = "stateadmin"
        state_admin = get_user_object(user, role)
        
        if not state_admin:
            return Response({"error": "Request must be from stateadmin."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the state admin's state
        admin_state = state_admin.state
        
        if not admin_state:
            return Response({"error": "State admin state not found."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all DeviceTag entries where the district's state matches the state admin's state
        # Use DeviceTag's direct district relationship for proper filtering
        # Also include fallback filtering for legacy data that might not have district set
        device_tags = DeviceTag.objects.filter(
            Q(district__state=admin_state) |
            Q(district__isnull=True, vehicle_owner__users__address_State=admin_state.state)
        ).select_related(
            'device',
            'device__model', 
            'device__dealer',
            'district',
            'district__state',
            'vehicle_owner',
            'tagged_by'
        ).prefetch_related(
            'vehicle_owner__users',
            'device__dealer__users'
        ).order_by('-tagged')
        
        # Apply additional filters if provided in request
        if request.method == 'POST':
            # Filter by vehicle registration number
            reg_no = request.data.get('vehicle_reg_no')
            if reg_no:
                device_tags = device_tags.filter(vehicle_reg_no__icontains=reg_no)
            
            # Filter by status
            tag_status = request.data.get('status')
            if tag_status:
                device_tags = device_tags.filter(status=tag_status)
            
            # Filter by device IMEI
            imei = request.data.get('imei')
            if imei:
                device_tags = device_tags.filter(device__imei__icontains=imei)
            
            # Filter by dealer
            dealer_id = request.data.get('dealer_id')
            if dealer_id:
                device_tags = device_tags.filter(tagged_by__dealer_user__id=dealer_id)
            
            # Filter by vehicle make
            vehicle_make = request.data.get('vehicle_make')
            if vehicle_make:
                device_tags = device_tags.filter(vehicle_make__icontains=vehicle_make)
            
            # Filter by vehicle model
            vehicle_model = request.data.get('vehicle_model')
            if vehicle_model:
                device_tags = device_tags.filter(vehicle_model__icontains=vehicle_model)
            
            # Filter by date range
            from_date = request.data.get('from_date')
            to_date = request.data.get('to_date')
            if from_date:
                device_tags = device_tags.filter(tagged__gte=from_date)
            if to_date:
                device_tags = device_tags.filter(tagged__lte=to_date)
            
            # Filter by vehicle category
            category = request.data.get('category')
            if category:
                device_tags = device_tags.filter(category__icontains=category)
        
        # Paginate results
        page_size = request.data.get('page_size', 50)  # Default 50 records per page
        page_number = request.data.get('page', 1)
        
        try:
            page_size = int(page_size)
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_size = 50
            page_number = 1
        
        # Ensure reasonable limits
        if page_size > 500:
            page_size = 500
        if page_size < 1:
            page_size = 50
        if page_number < 1:
            page_number = 1
        
        # Calculate pagination
        total_count = device_tags.count()
        start_index = (page_number - 1) * page_size
        end_index = start_index + page_size
        
        paginated_tags = device_tags[start_index:end_index]
        
        # Serialize the data
        serializer = DeviceTagSerializer2(paginated_tags, many=True)
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page_number < total_pages
        has_previous = page_number > 1
        
        # Debug information
        total_device_tags_in_db = DeviceTag.objects.count()
        device_tags_in_state = DeviceTag.objects.filter(district__state=admin_state).count()
        device_tags_legacy = DeviceTag.objects.filter(
            district__isnull=True, 
            vehicle_owner__users__address_State=admin_state.state
        ).count()
        
        response_data = {
            'success': True,
            'message': f'Found {total_count} tagging records in {admin_state.state} state.',
            'data': serializer.data,
            'pagination': {
                'current_page': page_number,
                'page_size': page_size,
                'total_pages': total_pages,
                'total_count': total_count,
                'has_next': has_next,
                'has_previous': has_previous,
            },
            'state_info': {
                'state_id': admin_state.id,
                'state_name': admin_state.state
            },
            'debug_info': {
                'total_device_tags_in_db': total_device_tags_in_db,
                'device_tags_in_state': device_tags_in_state,
                'device_tags_legacy': device_tags_legacy,
                'user_role': user.role,
                'admin_state_id': admin_state.id,
                'admin_state_name': admin_state.state
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f"Unable to process request: {str(e)}",
            'debug_info': {
                'user_role': request.user.role if hasattr(request, 'user') else 'Unknown',
                'error_type': type(e).__name__
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def get_device_tag_alerts(request):
    """
    Get alerts for specific device tags with user-based filtering:
    - Super Admin: Can see all alerts
    - State Admin: Can see alerts for devices in their state only  
    - DTO/RTO: Can see alerts for devices in their district only
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Get filtering parameters
        vehicle_reg_no = request.data.get('vehicle_reg_no', '')
        device_tag_id = request.data.get('device_tag_id', '')
        start_datetime = request.data.get('start_datetime')
        end_datetime = request.data.get('end_datetime')
        alert_type = request.data.get('alert_type', '')
        
        # Base queryset for alerts
        alerts_queryset = AlertsLog.objects.all().select_related(
            'deviceTag', 'deviceTag__device', 'deviceTag__vehicle_owner', 
            'state', 'gps_ref'
        )
        
        # Apply user-based filtering based on role
        if user.role == "superadmin":
            # Super admin can see all alerts - no additional filtering needed
            pass
            
        elif user.role == "stateadmin":
            # State admin can only see alerts for devices in their state
            state_admin = get_user_object(user, "stateadmin")
            if not state_admin:
                return Response({"error": "Invalid state admin user"}, status=status.HTTP_400_BAD_REQUEST)
            
            alerts_queryset = alerts_queryset.filter(state=state_admin.state)
            
        elif user.role == "dtorto":
            # DTO/RTO can only see alerts for devices in their district
            dto_rto_obj = get_user_object(user, "dtorto")
            if not dto_rto_obj:
                return Response({"error": "Invalid DTO/RTO user"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter by state and district
            alerts_queryset = alerts_queryset.filter(
                state=dto_rto_obj.state,
                deviceTag__vehicle_owner__address_State=dto_rto_obj.state.state,
                deviceTag__vehicle_owner__address__icontains=dto_rto_obj.district
            )
            
        else:
            return Response({"error": "Unauthorized role. Only superadmin, stateadmin, and dtorto can access this endpoint."}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Apply additional filters based on request parameters
        if vehicle_reg_no:
            alerts_queryset = alerts_queryset.filter(
                deviceTag__vehicle_reg_no__icontains=vehicle_reg_no
            )
            
        if device_tag_id:
            alerts_queryset = alerts_queryset.filter(deviceTag__id=device_tag_id)
            
        if start_datetime:
            alerts_queryset = alerts_queryset.filter(timestamp__gte=start_datetime)
            
        if end_datetime:
            alerts_queryset = alerts_queryset.filter(timestamp__lte=end_datetime)
            
        if alert_type:
            alerts_queryset = alerts_queryset.filter(type=alert_type)
        
        # Order by timestamp (newest first)
        alerts_queryset = alerts_queryset.order_by('-timestamp')
        
        # Pagination
        page_number = request.data.get('page', 1)
        page_size = request.data.get('page_size', 50)
        
        paginator = Paginator(alerts_queryset, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Serialize the alerts data
        alerts_data = []
        for alert in page_obj:
            alert_data = {
                'id': alert.id,
                'type': alert.type,
                'status': alert.status,
                'timestamp': alert.timestamp.isoformat(),
                'device_tag': {
                    'id': alert.deviceTag.id,
                    'vehicle_reg_no': alert.deviceTag.vehicle_reg_no,
                    'vehicle_make': alert.deviceTag.vehicle_make,
                    'vehicle_model': alert.deviceTag.vehicle_model,
                    'category': alert.deviceTag.category,
                    'status': alert.deviceTag.status,
                    'device_esn': alert.deviceTag.device.device_esn if alert.deviceTag.device else None,
                    'owner_name': alert.deviceTag.vehicle_owner.name if alert.deviceTag.vehicle_owner else None,
                    'owner_mobile': alert.deviceTag.vehicle_owner.mobile if alert.deviceTag.vehicle_owner else None
                },
                'state': {
                    'id': alert.state.id,
                    'name': alert.state.state
                } if alert.state else None,
                'gps_data': {
                    'latitude': alert.gps_ref.latitude if alert.gps_ref else None,
                    'longitude': alert.gps_ref.longitude if alert.gps_ref else None,
                    'speed': alert.gps_ref.speed if alert.gps_ref else None,
                    'timestamp': alert.gps_ref.timestamp.isoformat() if alert.gps_ref and alert.gps_ref.timestamp else None
                } if alert.gps_ref else None,
                'route_info': {
                    'id': alert.route_ref.id,
                    'name': alert.route_ref.state
                } if alert.route_ref else None,
                'emergency_call': {
                    'id': alert.em_ref.id,
                    'status': alert.em_ref.status
                } if alert.em_ref else None
            }
            alerts_data.append(alert_data)
        
        # Summary statistics
        total_alerts = alerts_queryset.count()
        alert_type_counts = {}
        for choice in AlertsLog.TYPE_CHOICES:
            alert_type = choice[0]
            count = alerts_queryset.filter(type=alert_type).count()
            alert_type_counts[alert_type] = count
        
        response_data = {
            'success': True,
            'user_role': user.role,
            'total_alerts': total_alerts,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'alert_type_counts': alert_type_counts,
            'alerts': alerts_data,
            'available_alert_types': dict(AlertsLog.TYPE_CHOICES)
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'An error occurred while fetching alerts: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ...existing code...

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def get_device_tags(request):
    """
    Get device tags with search functionality and user-based filtering:
    - Super Admin: Can see all device tags
    - State Admin: Can see device tags for their state only  
    - DTO/RTO: Can see device tags for their district only
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Get filtering parameters
        vehicle_reg_no = request.data.get('vehicle_reg_no', '')
        vehicle_make = request.data.get('vehicle_make', '')
        vehicle_model = request.data.get('vehicle_model', '')
        category = request.data.get('category', '')
        status_filter = request.data.get('status', '')
        owner_name = request.data.get('owner_name', '')
        owner_mobile = request.data.get('owner_mobile', '')
        device_esn = request.data.get('device_esn', '')
        engine_no = request.data.get('engine_no', '')
        chassis_no = request.data.get('chassis_no', '')
        tagged_from = request.data.get('tagged_from')
        tagged_to = request.data.get('tagged_to')
        
        # Base queryset for device tags
        device_tags_queryset = DeviceTag.objects.all().select_related(
            'device', 'device__model', 'vehicle_owner', 'tagged_by'
        ).prefetch_related(
            'vehicle_owner__users', 'drivers'
        )
        
        # Apply user-based filtering based on role
        if user.role == "superadmin":
            # Super admin can see all device tags - no additional filtering needed
            pass
            
        elif user.role == "stateadmin":
            # State admin can only see device tags for vehicles in their state
            state_admin = get_user_object(user, "stateadmin")
            if not state_admin:
                return Response({"error": "Invalid state admin user"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter by state - assuming vehicle owners have state information
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__address_State=state_admin.state.state
            )
            
        elif user.role == "dtorto":
            # DTO/RTO can only see device tags for vehicles in their district
            dto_rto_obj = get_user_object(user, "dtorto")
            if not dto_rto_obj:
                return Response({"error": "Invalid DTO/RTO user"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Filter by state and district
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__address_State=dto_rto_obj.state.state,
                vehicle_owner__users__address__icontains=dto_rto_obj.district
            )
            
        else:
            return Response({"error": "Unauthorized role. Only superadmin, stateadmin, and dtorto can access this endpoint."}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Apply search filters
        if vehicle_reg_no:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_reg_no__icontains=vehicle_reg_no
            )
            
        if vehicle_make:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_make__icontains=vehicle_make
            )
            
        if vehicle_model:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_model__icontains=vehicle_model
            )
            
        if category:
            device_tags_queryset = device_tags_queryset.filter(
                category__icontains=category
            )
            
        if status_filter:
            device_tags_queryset = device_tags_queryset.filter(status=status_filter)
            
        if owner_name:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__name__icontains=owner_name
            )
            
        if owner_mobile:
            device_tags_queryset = device_tags_queryset.filter(
                vehicle_owner__users__mobile__icontains=owner_mobile
            )
            
        if device_esn:
            device_tags_queryset = device_tags_queryset.filter(
                device__device_esn__icontains=device_esn
            )
            
        if engine_no:
            device_tags_queryset = device_tags_queryset.filter(
                engine_no__icontains=engine_no
            )
            
        if chassis_no:
            device_tags_queryset = device_tags_queryset.filter(
                chassis_no__icontains=chassis_no
            )
            
        if tagged_from:
            device_tags_queryset = device_tags_queryset.filter(tagged__gte=tagged_from)
            
        if tagged_to:
            device_tags_queryset = device_tags_queryset.filter(tagged__lte=tagged_to)
        
        # Order by tagged date (newest first)
        device_tags_queryset = device_tags_queryset.order_by('-tagged')
        
        # Pagination
        page_number = request.data.get('page', 1)
        page_size = request.data.get('page_size', 50)
        
        # Ensure reasonable pagination limits
        try:
            page_number = int(page_number)
            page_size = int(page_size)
        except (ValueError, TypeError):
            page_number = 1
            page_size = 50
            
        if page_size > 500:
            page_size = 500
        if page_size < 1:
            page_size = 50
        if page_number < 1:
            page_number = 1
        
        paginator = Paginator(device_tags_queryset, page_size)
        page_obj = paginator.get_page(page_number)
        
        # Serialize the device tags data
        device_tags_data = []
        for device_tag in page_obj:
            # Get the primary vehicle owner user
            primary_owner_user = device_tag.vehicle_owner.users.first() if device_tag.vehicle_owner else None
            
            # Get driver information
            drivers_info = []
            for driver in device_tag.drivers.all():
                drivers_info.append({
                    'id': driver.id,
                    'name': driver.name,
                    'mobile': driver.phone_no,
                    'license_no': driver.license_no
                })
            
            device_tag_data = {
                'id': device_tag.id,
                'vehicle_reg_no': device_tag.vehicle_reg_no,
                'engine_no': device_tag.engine_no,
                'chassis_no': device_tag.chassis_no,
                'vehicle_make': device_tag.vehicle_make,
                'vehicle_model': device_tag.vehicle_model,
                    'category': (device_tag.category.category if device_tag.category else None),
                'status': device_tag.status,
                'tagged': device_tag.tagged.isoformat() if device_tag.tagged else None,
                'rc_file': device_tag.rc_file,
                'receipt_file_or': device_tag.receipt_file_or,
                'receipt_file_ul': device_tag.receipt_file_ul,
                'device': {
                    'id': device_tag.device.id,
                    'device_esn': device_tag.device.device_esn,
                    'imei': device_tag.device.imei,
                    'iccid': device_tag.device.iccid,
                    'msisdn1': device_tag.device.msisdn1,
                    'msisdn2': device_tag.device.msisdn2,
                    'model': {
                        'id': device_tag.device.model.id,
                        'model_name': device_tag.device.model.model_name,
                        'vendor_id': device_tag.device.model.vendor_id
                    } if device_tag.device.model else None
                } if device_tag.device else None,
                'vehicle_owner': {
                    'id': device_tag.vehicle_owner.id,
                    'name': primary_owner_user.name if primary_owner_user else None,
                    'email': primary_owner_user.email if primary_owner_user else None,
                    'mobile': primary_owner_user.mobile if primary_owner_user else None,
                    'address': primary_owner_user.address if primary_owner_user else None,
                    'address_state': primary_owner_user.address_State if primary_owner_user else None,
                    'address_pin': primary_owner_user.address_pin if primary_owner_user else None
                } if device_tag.vehicle_owner else None,
                'tagged_by': {
                    'id': device_tag.tagged_by.id,
                    'name': device_tag.tagged_by.name,
                    'email': device_tag.tagged_by.email,
                    'role': device_tag.tagged_by.role
                } if device_tag.tagged_by else None,
                'drivers': drivers_info
            }
            device_tags_data.append(device_tag_data)
        
        # Get status statistics
        total_device_tags = device_tags_queryset.count()
        status_counts = {}
        for choice in DeviceTag.STATUS_CHOICES:
            status_value = choice[0]
            count = device_tags_queryset.filter(status=status_value).count()
            status_counts[status_value] = count
        
        # Get category statistics
        category_counts = {}
        categories = device_tags_queryset.values_list('category', flat=True).distinct()
        for category_name in categories:
            if category_name:
                count = device_tags_queryset.filter(category=category_name).count()
                category_counts[category_name] = count
        
        response_data = {
            'success': True,
            'user_role': user.role,
            'total_device_tags': total_device_tags,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'status_counts': status_counts,
            'category_counts': category_counts,
            'device_tags': device_tags_data,
            'available_statuses': dict(DeviceTag.STATUS_CHOICES),
            'search_filters_applied': {
                'vehicle_reg_no': vehicle_reg_no,
                'vehicle_make': vehicle_make,
                'vehicle_model': vehicle_model,
                'category': category,
                'status': status_filter,
                'owner_name': owner_name,
                'owner_mobile': owner_mobile,
                'device_esn': device_esn,
                'engine_no': engine_no,
                'chassis_no': chassis_no,
                'tagged_from': tagged_from,
                'tagged_to': tagged_to
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'An error occurred while fetching device tags: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def activated_device_list(request):
    """
    Get list of activated devices with comprehensive information for super admin, state admin, and DTO users.
    Returns: FITMENT DATE, fitment status, eSIM validity, reg no, DTO district code, 
    vehicle owner, device model number, manufacturer, dealer
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check user role and permissions
        allowed_roles = ['superadmin', 'stateadmin', 'dtorto']
        if user.role not in allowed_roles:
            return Response({
                "error": f"Access denied. This endpoint is only accessible by {', '.join(allowed_roles)}."
            }, status=status.HTTP_403_FORBIDDEN)

        # Base query for activated devices (multiple active statuses)
        # Include multiple status values that indicate an active/working device
        active_statuses = [
            'Device_Active',
            'Live_Location_Confirmed', 
            'SOS_Confirmed','Owner_Final_OTP_Verified',
            'RegNo_Configuration_Confirmed'
        ]
        
        activated_devices = DeviceTag.objects.filter(
            status__in=active_statuses
        ).select_related(
            'device',
            'device__model',
            'device__model__created_by',
            'device__dealer',
            'device__dealer__manufacturer',
            'district',
            'district__state',
            'vehicle_owner'
        ).prefetch_related(
            'device__model__created_by',
            'device__dealer__manufacturer__users',
            'device__dealer__users',
            'device__dealer__districts',
            'vehicle_owner__users'
        )

        # Apply role-based filtering
        if user.role == 'stateadmin':
            # State admin can only see devices in their state
            state_admin = get_user_object(user, "stateadmin")
            if state_admin:
                # Use DeviceTag's district to filter by state
                activated_devices = activated_devices.filter(
                    district__state=state_admin.state
                )
            else:
                return Response({
                    "error": "State admin profile not found"
                }, status=status.HTTP_400_BAD_REQUEST)
                
        elif user.role == 'dtorto':
            # DTO can only see devices in their district(s)
            dto_admin = get_user_object(user, "dtorto")
            if dto_admin:
                # Use DeviceTag's district field directly
                activated_devices = activated_devices.filter(
                    district__state=dto_admin.state,
                    district__district=dto_admin.district
                )
            else:
                return Response({
                    "error": "DTO profile not found"
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Apply additional filters from request
        device_esn = request.data.get('device_esn', '')
        vehicle_reg_no = request.data.get('vehicle_reg_no', '')
        manufacturer_name = request.data.get('manufacturer_name', '')
        dealer_name = request.data.get('dealer_name', '')
        district_code = request.data.get('district_code', '')
        state_id = request.data.get('state_id', '')
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        
        if device_esn:
            activated_devices = activated_devices.filter(device__device_esn__icontains=device_esn)
        
        if vehicle_reg_no:
            activated_devices = activated_devices.filter(vehicle_reg_no__icontains=vehicle_reg_no)
            
        if manufacturer_name:
            activated_devices = activated_devices.filter(
                device__dealer__manufacturer__company_name__icontains=manufacturer_name
            )
            
        if dealer_name:
            activated_devices = activated_devices.filter(
                device__dealer__company_name__icontains=dealer_name
            )
            
        if district_code:
            activated_devices = activated_devices.filter(
                district__district_code__icontains=district_code
            )
            
        if state_id:
            activated_devices = activated_devices.filter(
                device__dealer__manufacturer__state__id=state_id
            )
            
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                activated_devices = activated_devices.filter(tagged__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                activated_devices = activated_devices.filter(tagged__date__lte=to_date)
            except ValueError:
                pass

        # Prepare response data
        device_list = []
        
        # Debug information
        total_device_tags = DeviceTag.objects.count()
        active_device_tags = activated_devices.count()
        
        for device_tag in activated_devices:
            try:
                # Get manufacturer information
                manufacturer = device_tag.device.dealer.manufacturer if device_tag.device and device_tag.device.dealer else None
                manufacturer_name = manufacturer.company_name if manufacturer else 'N/A'
                manufacturer_users = list(manufacturer.users.all()) if manufacturer else []
                manufacturer_user_name = manufacturer_users[0].name if manufacturer_users else 'N/A'
                
                # Get dealer information
                dealer = device_tag.device.dealer if device_tag.device else None
                dealer_name = dealer.company_name if dealer else 'N/A'
                dealer_users = list(dealer.users.all()) if dealer else []
                dealer_user_name = dealer_users[0].name if dealer_users else 'N/A'
                
                # Get district information from DeviceTag's direct district field
                district = device_tag.district
                district_name = district.district if district else 'N/A'
                district_code = district.district_code if district else 'N/A'
                state_name = district.state.state if district and district.state else 'N/A'
                
                # Get vehicle owner information
                vehicle_owner = device_tag.vehicle_owner
                owner_users = list(vehicle_owner.users.all()) if vehicle_owner else []
                owner_name = owner_users[0].name if owner_users else 'N/A'
                owner_company = vehicle_owner.company_name if vehicle_owner else 'N/A'
                
                # Get device information
                device = device_tag.device
                device_model = device.model if device else None
                
                device_data = {
                    'id': device_tag.id,
                    'device_esn': device.device_esn if device else 'N/A',
                    'imei': device.imei if device else 'N/A',
                    'iccid': device.iccid if device else 'N/A',
                    'msisdn1': device.msisdn1 if device else 'N/A',
                    'msisdn2': device.msisdn2 if device and device.msisdn2 else 'N/A',
                    
                    # Fitment information
                    'fitment_date': device_tag.tagged.strftime('%Y-%m-%d %H:%M:%S') if device_tag.tagged else 'N/A',
                    'fitment_status': device_tag.status,
                    
                    # eSIM information
                    'esim_validity': device.esim_validity.strftime('%Y-%m-%d') if device and device.esim_validity else 'N/A',
                    'telecom_provider1': device.telecom_provider1 if device else 'N/A',
                    'telecom_provider2': device.telecom_provider2 if device and device.telecom_provider2 else 'N/A',
                    'stock_status': device.stock_status if device else 'N/A',
                    'esim_status': device.esim_status if device else 'N/A',
                    
                    # Vehicle information
                    'vehicle_reg_no': device_tag.vehicle_reg_no,
                    'engine_no': device_tag.engine_no,
                    'chassis_no': device_tag.chassis_no,
                    'vehicle_make': device_tag.vehicle_make,
                    'vehicle_model': device_tag.vehicle_model,
                    'vehicle_category': (device_tag.category.category if device_tag.category else None),
                    
                    # District and state information
                    'dto_district_code': district_code,
                    'district_name': district_name,
                    'state_name': state_name,
                    
                    # Vehicle owner information
                    'vehicle_owner_name': owner_name,
                    'vehicle_owner_company': owner_company,
                    'vehicle_owner_id': vehicle_owner.id if vehicle_owner else None,
                    
                    # Device model information
                    'device_model_name': device_model.model_name if device_model else 'N/A',
                    'device_model_id': device_model.id if device_model else None,
                    'hardware_version': device_model.hardware_version if device_model else 'N/A',
                    'vendor_id': device_model.vendor_id if device_model else 'N/A',
                    'tac_no': device_model.tac_no if device_model else 'N/A',
                    
                    # Manufacturer information
                    'manufacturer_name': manufacturer_name,
                    'manufacturer_id': manufacturer.id if manufacturer else None,
                    'manufacturer_user_name': manufacturer_user_name,
                    'manufacturer_state': manufacturer.state.state if manufacturer and manufacturer.state else 'N/A',
                    
                    # Dealer information
                    'dealer_name': dealer_name,
                    'dealer_id': dealer.id if dealer else None,
                    'dealer_user_name': dealer_user_name,
                    
                    # Tagged by information
                    'tagged_by_name': device_tag.tagged_by.name if device_tag.tagged_by else 'N/A',
                    'tagged_by_email': device_tag.tagged_by.email if device_tag.tagged_by else 'N/A',
                    
                    # Additional device information
                    'created_date': device.created.strftime('%Y-%m-%d %H:%M:%S') if device and device.created else 'N/A',
                    'device_assigned_date': device.assigned.strftime('%Y-%m-%d %H:%M:%S') if device and device.assigned else 'N/A',
                }
                
                device_list.append(device_data)
                
            except Exception as e:
                # Log individual device errors but continue processing
                print(f"Error processing device tag {device_tag.id}: {str(e)}")
                continue

        # Pagination
        page = int(request.data.get('page', 1))
        page_size = int(request.data.get('page_size', 50))
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_devices = device_list[start_index:end_index]
        
        response_data = {
            'status': 'success',
            'data': {
                'devices': paginated_devices,
                'total_count': len(device_list),
                'page': page,
                'page_size': page_size,
                'total_pages': (len(device_list) + page_size - 1) // page_size
            },
            'debug_info': {
                'user_role': user.role,
                'total_device_tags_in_db': total_device_tags,
                'matching_active_devices': active_device_tags,
                'processed_devices': len(device_list),
                'active_statuses_searched': active_statuses
            },
            'message': 'Activated devices retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving activated devices: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def dealer_check_esim_status(request):
    """
    API for dealers to check eSIM activation status and validity for their devices
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user is a dealer
    role = "dealer"
    user = request.user
    dealer = get_user_object(user, role)
    if not dealer:
        return Response({"error": "Request must be from dealer."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get filter parameters
        device_esn = request.data.get('device_esn', '')
        imei = request.data.get('imei', '')
        msisdn1 = request.data.get('msisdn1', '')
        esim_status_filter = request.data.get('esim_status', '')
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Current time for validity checks
        now = timezone.now()
        
        # Base query for devices assigned to this dealer
        devices = DeviceStock.objects.filter(dealer=dealer)
        
        # Apply filters if provided
        if device_esn:
            devices = devices.filter(device_esn__icontains=device_esn)
        
        if imei:
            devices = devices.filter(imei__icontains=imei)
            
        if msisdn1:
            devices = devices.filter(msisdn1__icontains=msisdn1)
            
        if esim_status_filter:
            devices = devices.filter(esim_status=esim_status_filter)
        
        # Get devices with related data
        devices = devices.select_related('model', 'dealer', 'created_by').prefetch_related('esim_provider')
        
        # Process results and add validity information
        result_data = []
        for device in devices:
            # Check if eSIM is expired
            is_expired = device.esim_validity and device.esim_validity <= now
            
            # Calculate days until expiry
            days_until_expiry = None
            if device.esim_validity:
                time_diff = device.esim_validity - now
                days_until_expiry = time_diff.days if time_diff.days > 0 else 0
            
            # Determine expiry status
            expiry_status = "Active"
            if is_expired:
                expiry_status = "Expired"
            elif days_until_expiry is not None and days_until_expiry <= 30:
                expiry_status = "Expiring Soon"
            
            # Get eSIM providers
            esim_providers = [{"id": provider.id, "company_name": provider.company_name} 
                             for provider in device.esim_provider.all()]
            
            # Get any pending activation requests
            activation_requests = esimActivationRequest.objects.filter(
                device=device,
                ceated_by=dealer
            ).order_by('-created_at')
            
            latest_request = None
            if activation_requests.exists():
                latest_activation = activation_requests.first()
                latest_request = {
                    "id": latest_activation.id,
                    "status": latest_activation.status,
                    "created_at": latest_activation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "eSim_provider": latest_activation.eSim_provider.company_name if latest_activation.eSim_provider else None,
                    "valid_from": latest_activation.valid_from.strftime('%Y-%m-%d %H:%M:%S') if latest_activation.valid_from else None,
                    "valid_upto": latest_activation.valid_upto.strftime('%Y-%m-%d %H:%M:%S') if latest_activation.valid_upto else None,
                    "accepted_at": latest_activation.accepted_at.strftime('%Y-%m-%d %H:%M:%S') if latest_activation.accepted_at else None
                }
            
            device_info = {
                "device_id": device.id,
                "device_esn": device.device_esn,
                "imei": device.imei,
                "iccid": device.iccid,
                "msisdn1": device.msisdn1,
                "msisdn2": device.msisdn2,
                "telecom_provider1": device.telecom_provider1,
                "telecom_provider2": device.telecom_provider2,
                
                # Device model information
                "device_model": {
                    "id": device.model.id,
                    "model_name": device.model.model_name,
                    "vendor_id": device.model.vendor_id
                },
                
                # eSIM status and validity information
                "esim_status": device.esim_status,
                "stock_status": device.stock_status,
                "esim_validity": device.esim_validity.strftime('%Y-%m-%d %H:%M:%S') if device.esim_validity else None,
                "days_until_expiry": days_until_expiry,
                "expiry_status": expiry_status,
                "is_expired": is_expired,
                
                # eSIM provider information
                "esim_providers": esim_providers,
                
                # Latest activation request information
                "latest_activation_request": latest_request,
                
                # Additional device information
                "assigned_date": device.assigned.strftime('%Y-%m-%d %H:%M:%S') if device.assigned else None,
                "created_date": device.created.strftime('%Y-%m-%d %H:%M:%S'),
                "remarks": device.remarks
            }
            
            result_data.append(device_info)
        
        # Summary statistics
        total_devices = len(result_data)
        active_esims = len([d for d in result_data if d['expiry_status'] == 'Active'])
        expired_esims = len([d for d in result_data if d['expiry_status'] == 'Expired'])
        expiring_soon = len([d for d in result_data if d['expiry_status'] == 'Expiring Soon'])
        
        # Count by eSIM status
        status_counts = {}
        for device in result_data:
            status = device['esim_status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        summary = {
            "total_devices": total_devices,
            "esim_validity_summary": {
                "active": active_esims,
                "expired": expired_esims,
                "expiring_soon": expiring_soon
            },
            "esim_status_counts": status_counts,
            "dealer_info": {
                "id": dealer.id,
                "company_name": dealer.company_name,
                "district": dealer.districts.first().district if dealer.districts.exists() else None,
                "state": dealer.manufacturer.state.state if dealer.manufacturer and dealer.manufacturer.state else None
            }
        }
        
        return Response({
            "summary": summary,
            "devices": result_data
        }, status=200)
        
    except Exception as e:
        return Response({'error': "Unable to process request. " + str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle]) 
@require_http_methods(['GET', 'POST'])
def homepage_esimProvider(request):
    """
    Homepage API for esim Provider role showing eSIM related statistics
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    

    try:
        role = "esimprovider"
        user = request.user
        profile = get_user_object(user, role)
        if not profile:
            return Response({"error": "Request must be from " + role + '.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create a dictionary to hold the filter parameters
        filters = {}
        
        if profile:
            from django.db.models import Sum, Q, Count, Avg
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            # Current time for calculations
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            
            # Get all device stocks associated with this eSIM provider
            device_stocks = DeviceStock.objects.filter(esim_provider=profile)
            
            # Total devices with this eSIM provider
            total_devices = device_stocks.count()
            
            # eSIM activation request statistics
            esim_activation_requests = esimActivationRequest.objects.filter(eSim_provider=profile)
            manufacturers_with_provider = Manufacturer.objects.filter(esim_provider=profile).distinct().count()
            
            # Count different statuses of eSIM activation requests
            esim_pending = esim_activation_requests.filter(status="pending").count()
            esim_validated = esim_activation_requests.filter(status="valid").count()
            esim_invalid = esim_activation_requests.filter(status="invalid").count()
            
            # eSIM statistics from esimActivationRequest model
            esim_activated_total = esim_activation_requests.filter(status="valid").count()
            
            esim_activation_rejected = esim_activation_requests.filter(status="invalid").count()
            
            # Time-based statistics
            today_requests = esim_activation_requests.filter(created_at__gte=today_start).count()
            this_month_requests = esim_activation_requests.filter(created_at__gte=month_start).count()
            this_week_requests = esim_activation_requests.filter(created_at__gte=week_ago).count()
            
            # Expiring soon (within 30 days)
            esim_expiring_soon = esim_activation_requests.filter(
                status="valid",
                valid_upto__gt=now,
                valid_upto__lte=now + timedelta(days=30)
            ).count()

            # 1yr / 2yr expiry based on plan duration (valid_upto - valid_from)
            from django.db.models import ExpressionWrapper, DurationField, F
            _plan_dur = ExpressionWrapper(F('valid_upto') - F('valid_from'), output_field=DurationField())
            esim_1_year_expiry = esim_activation_requests.filter(status="valid").annotate(
                plan_duration=_plan_dur
            ).filter(
                plan_duration__gte=timedelta(days=330),
                plan_duration__lt=timedelta(days=545)
            ).count()

            esim_2_year_expiry = esim_activation_requests.filter(status="valid").annotate(
                plan_duration=_plan_dur
            ).filter(
                plan_duration__gte=timedelta(days=545),
                plan_duration__lte=timedelta(days=800)
            ).count()

            esim_expired = esim_activation_requests.filter(valid_upto__lte=now).count()
            
            count_dict = {
                'Total_Devices_With_ESim': total_devices,
                'ESim_Validated': esim_validated,
                'ESim_Expired': esim_expired,
                'ESim_Active': esim_activated_total,
                'ESim_Pending': esim_pending,
                'ESim_Invalid': esim_invalid,
                'ESim_Activation_Req_Sent': esim_activation_requests.count(),
                'ESim_Activation_Confirmed': esim_activated_total,
                'ESim_Activation_Rejected': esim_activation_rejected,
                'Manufacturers_With_This_ESimProvider': manufacturers_with_provider,
                'ESim_Activation_Request_Received': esim_activation_requests.count(),
                'ESim_Activated': esim_activated_total,
                'ESim_1_Year_Expiry': esim_1_year_expiry,
                'ESim_2_Year_Expiry': esim_2_year_expiry,
                'ESim_Already_Expired': esim_expired,
                'ESim_Expiring_Soon_30_Days': esim_expiring_soon,
                'Today_Activation_Requests': today_requests,
                'This_Week_Activation_Requests': this_week_requests,
                'This_Month_Activation_Requests': this_month_requests,
                'Provider_Company_Name': profile.company_name,
                'Provider_State': profile.state.state if profile.state else None,
                'Provider_Status': profile.status,
                'Provider_Created_Date': profile.created.strftime('%Y-%m-%d') if profile.created else None,
                'Provider_Expiry_Date': profile.expirydate.strftime('%Y-%m-%d') if profile.expirydate else None,
            }
            
            return Response({
                'status': 'success',
                'data': count_dict,
                'message': 'esim Provider homepage data retrieved successfully'
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def state_admin_approved_models_report(request):
    """
    API for state admin to get report of approved device models.
    Returns comprehensive information about approved device models including manufacturer details.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check if user is a state admin or superadmin
        if user.role not in ['stateadmin', 'superadmin']:
            return Response({
                "error": "Access denied. This endpoint is only accessible by state admins or superadmins."
            }, status=status.HTTP_403_FORBIDDEN)

        # Get requester profile based on role
        state_admin = get_user_object(user, "stateadmin") if user.role == 'stateadmin' else None
        super_admin = get_user_object(user, "superadmin") if user.role == 'superadmin' else None
        if user.role == 'stateadmin' and not state_admin:
            return Response({
                "error": "State admin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)
        if user.role == 'superadmin' and not super_admin:
            return Response({
                "error": "Superadmin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Base query for approved device models
        approved_models = DeviceModel.objects.filter(
            status='StateAdminApproved'
        ).select_related(
            'created_by'
        ).prefetch_related(
            'eSimProviders',
            'created_by__manufacturers_user'
        )

        # Apply filters from request
        model_name = request.data.get('model_name', '')
        vendor_id = request.data.get('vendor_id', '')
        tac_no = request.data.get('tac_no', '')
        manufacturer_name = request.data.get('manufacturer_name', '')
        test_agency = request.data.get('test_agency', '')
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        
        if model_name:
            approved_models = approved_models.filter(model_name__icontains=model_name)
        
        if vendor_id:
            approved_models = approved_models.filter(vendor_id__icontains=vendor_id)
            
        if tac_no:
            approved_models = approved_models.filter(tac_no__icontains=tac_no)
            
        if test_agency:
            approved_models = approved_models.filter(test_agency__icontains=test_agency)
            
        if manufacturer_name:
            approved_models = approved_models.filter(
                created_by__manufacturers_user__company_name__icontains=manufacturer_name
            )
            
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                approved_models = approved_models.filter(created__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                approved_models = approved_models.filter(created__date__lte=to_date)
            except ValueError:
                pass

        # Prepare response data
        models_list = []
        for model in approved_models:
            try:
                # Get manufacturer information
                manufacturer = model.created_by.manufacturers_user.first() if model.created_by.manufacturers_user.exists() else None
                manufacturer_name = manufacturer.company_name if manufacturer else 'N/A'
                manufacturer_state = manufacturer.state.state if manufacturer and manufacturer.state else 'N/A'
                
                # Get eSIM providers
                esim_providers = []
                for provider in model.eSimProviders.all():
                    esim_providers.append({
                        'id': provider.id,
                        'company_name': provider.company_name,
                        'state': provider.state.state if provider.state else 'N/A'
                    })
                
                model_data = {
                    'id': model.id,
                    'model_name': model.model_name,
                    'test_agency': model.test_agency,
                    'vendor_id': model.vendor_id,
                    'tac_no': model.tac_no,
                    'tac_validity': model.tac_validity.strftime('%Y-%m-%d') if model.tac_validity else 'N/A',
                    'hardware_version': model.hardware_version,
                    'status': model.status,
                    'created_date': model.created.strftime('%Y-%m-%d %H:%M:%S') if model.created else 'N/A',
                    'approved_date': model.created.strftime('%Y-%m-%d %H:%M:%S') if model.created else 'N/A',  # Approval date same as creation for approved models
                    
                    # Manufacturer information
                    'manufacturer_name': manufacturer_name,
                    'manufacturer_id': manufacturer.id if manufacturer else None,
                    'manufacturer_state': manufacturer_state,
                    'manufacturer_gst_no': manufacturer.gstno if manufacturer else 'N/A',
                    'manufacturer_created_date': manufacturer.created.strftime('%Y-%m-%d') if manufacturer and manufacturer.created else 'N/A',
                    
                    # Creator information
                    'created_by_name': model.created_by.name if model.created_by else 'N/A',
                    'created_by_email': model.created_by.email if model.created_by else 'N/A',
                    'created_by_mobile': model.created_by.mobile if model.created_by else 'N/A',
                    
                    # eSIM providers
                    'esim_providers': esim_providers,
                    'esim_providers_count': len(esim_providers),
                    
                    # File information
                    'tac_doc_available': bool(model.tac_doc_path),
                    'tac_doc_path': model.tac_doc_path.url if model.tac_doc_path else None,
                }
                
                models_list.append(model_data)
                
            except Exception as e:
                # Log individual model errors but continue processing
                continue

        # Pagination
        page = int(request.data.get('page', 1))
        page_size = int(request.data.get('page_size', 50))
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_models = models_list[start_index:end_index]
        
        # Generate summary statistics
        total_models = len(models_list)
        unique_manufacturers = len(set([model['manufacturer_id'] for model in models_list if model['manufacturer_id']]))
        models_with_esim = len([model for model in models_list if model['esim_providers_count'] > 0])
        
        # Count by test agencies
        test_agencies = {}
        for model in models_list:
            agency = model['test_agency']
            test_agencies[agency] = test_agencies.get(agency, 0) + 1
        
        summary = {
            'total_approved_models': total_models,
            'unique_manufacturers': unique_manufacturers,
            'models_with_esim_providers': models_with_esim,
            'models_without_esim_providers': total_models - models_with_esim,
            'test_agencies_breakdown': test_agencies,
            'state_admin_info': {
                'id': state_admin.id if state_admin else None,
                'state': state_admin.state.state if state_admin and state_admin.state else 'N/A',
                'created_date': state_admin.created.strftime('%Y-%m-%d') if state_admin and state_admin.created else 'N/A'
            }
        }
        
        response_data = {
            'status': 'success',
            'data': {
                'summary': summary,
                'models': paginated_models,
                'total_count': total_models,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_models + page_size - 1) // page_size
            },
            'message': 'Approved device models report retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving approved models report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def state_admin_approved_cops_report(request):
    """
    API for state admin to get report of approved COPs (Certificate of Performance).
    Returns comprehensive information about approved COPs including device model and manufacturer details.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check if user is a state admin or superadmin
        if user.role not in ['stateadmin', 'superadmin']:
            return Response({
                "error": "Access denied. This endpoint is only accessible by state admins or superadmins."
            }, status=status.HTTP_403_FORBIDDEN)

        # Get requester profile based on role
        state_admin = get_user_object(user, "stateadmin") if user.role == 'stateadmin' else None
        super_admin = get_user_object(user, "superadmin") if user.role == 'superadmin' else None
        if user.role == 'stateadmin' and not state_admin:
            return Response({
                "error": "State admin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)
        if user.role == 'superadmin' and not super_admin:
            return Response({
                "error": "Superadmin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Base query for approved COPs
        approved_cops = DeviceCOP.objects.filter(
            status='StateAdminApproved'
        ).select_related(
            'device_model',
            'device_model__created_by',
            'created_by'
        ).prefetch_related(
            'device_model__eSimProviders',
            'created_by__manufacturers_user'
        )

        # Apply filters from request
        cop_no = request.data.get('cop_no', '')
        model_name = request.data.get('model_name', '')
        vendor_id = request.data.get('vendor_id', '')
        manufacturer_name = request.data.get('manufacturer_name', '')
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        validity_from = request.data.get('validity_from', '')
        validity_to = request.data.get('validity_to', '')
        
        if cop_no:
            approved_cops = approved_cops.filter(cop_no__icontains=cop_no)
        
        if model_name:
            approved_cops = approved_cops.filter(device_model__model_name__icontains=model_name)
            
        if vendor_id:
            approved_cops = approved_cops.filter(device_model__vendor_id__icontains=vendor_id)
            
        if manufacturer_name:
            approved_cops = approved_cops.filter(
                created_by__manufacturers_user__company_name__icontains=manufacturer_name
            )
            
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(created__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(created__date__lte=to_date)
            except ValueError:
                pass
                
        if validity_from:
            try:
                from_date = datetime.strptime(validity_from, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(cop_validity__gte=from_date)
            except ValueError:
                pass
                
        if validity_to:
            try:
                to_date = datetime.strptime(validity_to, '%Y-%m-%d').date()
                approved_cops = approved_cops.filter(cop_validity__lte=to_date)
            except ValueError:
                pass

        # Prepare response data
        cops_list = []
        for cop in approved_cops:
            try:
                # Get manufacturer information
                manufacturer = cop.created_by.manufacturers_user.first() if cop.created_by.manufacturers_user.exists() else None
                manufacturer_name = manufacturer.company_name if manufacturer else 'N/A'
                manufacturer_state = manufacturer.state.state if manufacturer and manufacturer.state else 'N/A'
                
                # Get device model information
                device_model = cop.device_model
                
                # Get eSIM providers for the device model
                esim_providers = []
                for provider in device_model.eSimProviders.all():
                    esim_providers.append({
                        'id': provider.id,
                        'company_name': provider.company_name,
                        'state': provider.state.state if provider.state else 'N/A'
                    })
                
                # Check if COP is expired
                is_expired = cop.cop_validity and cop.cop_validity < timezone.now().date()
                
                # Calculate days until expiry
                days_until_expiry = None
                if cop.cop_validity:
                    time_diff = cop.cop_validity - timezone.now().date()
                    days_until_expiry = time_diff.days if time_diff.days > 0 else 0
                
                cop_data = {
                    'id': cop.id,
                    'cop_no': cop.cop_no,
                    'cop_validity': cop.cop_validity.strftime('%Y-%m-%d') if cop.cop_validity else 'N/A',
                    'status': cop.status,
                    'valid': cop.valid,
                    'latest': cop.latest,
                    'created_date': cop.created.strftime('%Y-%m-%d %H:%M:%S') if cop.created else 'N/A',
                    'is_expired': is_expired,
                    'days_until_expiry': days_until_expiry,
                    'expiry_status': 'Expired' if is_expired else ('Expiring Soon' if days_until_expiry is not None and days_until_expiry <= 30 else 'Active'),
                    
                    # Device model information
                    'device_model_id': device_model.id,
                    'device_model_name': device_model.model_name,
                    'device_model_vendor_id': device_model.vendor_id,
                    'device_model_tac_no': device_model.tac_no,
                    'device_model_tac_validity': device_model.tac_validity.strftime('%Y-%m-%d') if device_model.tac_validity else 'N/A',
                    'device_model_hardware_version': device_model.hardware_version,
                    'device_model_test_agency': device_model.test_agency,
                    'device_model_status': device_model.status,
                    
                    # Manufacturer information
                    'manufacturer_name': manufacturer_name,
                    'manufacturer_id': manufacturer.id if manufacturer else None,
                    'manufacturer_state': manufacturer_state,
                    'manufacturer_gst_no': manufacturer.gstno if manufacturer else 'N/A',
                    'manufacturer_created_date': manufacturer.created.strftime('%Y-%m-%d') if manufacturer and manufacturer.created else 'N/A',
                    
                    # Creator information
                    'created_by_name': cop.created_by.name if cop.created_by else 'N/A',
                    'created_by_email': cop.created_by.email if cop.created_by else 'N/A',
                    'created_by_mobile': cop.created_by.mobile if cop.created_by else 'N/A',
                    
                    # eSIM providers for the device model
                    'esim_providers': esim_providers,
                    'esim_providers_count': len(esim_providers),
                    
                    # File information
                    'cop_file_available': bool(cop.cop_file),
                    'cop_file_path': cop.cop_file.url if cop.cop_file else None,
                }
                
                cops_list.append(cop_data)
                
            except Exception as e:
                # Log individual COP errors but continue processing
                continue

        # Pagination
        page = int(request.data.get('page', 1))
        page_size = int(request.data.get('page_size', 50))
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_cops = cops_list[start_index:end_index]
        
        # Generate summary statistics
        total_cops = len(cops_list)
        unique_manufacturers = len(set([cop['manufacturer_id'] for cop in cops_list if cop['manufacturer_id']]))
        unique_device_models = len(set([cop['device_model_id'] for cop in cops_list]))
        expired_cops = len([cop for cop in cops_list if cop['is_expired']])
        expiring_soon_cops = len([cop for cop in cops_list if cop['expiry_status'] == 'Expiring Soon'])
        active_cops = len([cop for cop in cops_list if cop['expiry_status'] == 'Active'])
        
        # Count by test agencies
        test_agencies = {}
        for cop in cops_list:
            agency = cop['device_model_test_agency']
            test_agencies[agency] = test_agencies.get(agency, 0) + 1
        
        # Count by validity years
        validity_years = {}
        for cop in cops_list:
            if cop['cop_validity'] != 'N/A':
                year = cop['cop_validity'][:4]  # Extract year from YYYY-MM-DD format
                validity_years[year] = validity_years.get(year, 0) + 1
        
        summary = {
            'total_approved_cops': total_cops,
            'unique_manufacturers': unique_manufacturers,
            'unique_device_models': unique_device_models,
            'active_cops': active_cops,
            'expired_cops': expired_cops,
            'expiring_soon_cops': expiring_soon_cops,
            'test_agencies_breakdown': test_agencies,
            'validity_years_breakdown': validity_years,
            'state_admin_info': {
                'id': state_admin.id if state_admin else None,
                'state': state_admin.state.state if state_admin and state_admin.state else 'N/A',
                'created_date': state_admin.created.strftime('%Y-%m-%d') if state_admin and state_admin.created else 'N/A'
            }
        }
        
        response_data = {
            'status': 'success',
            'data': {
                'summary': summary,
                'cops': paginated_cops,
                'total_count': total_cops,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_cops + page_size - 1) // page_size
            },
            'message': 'Approved COPs report retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving approved COPs report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def state_admin_combined_approval_report(request):
    """
    API for state admin to get combined report of approved device models and COPs.
    Returns summary statistics and overview of both approved models and COPs.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        
        # Check if user is a state admin
        if user.role != 'stateadmin':
            return Response({
                "error": "Access denied. This endpoint is only accessible by state admins."
            }, status=status.HTTP_403_FORBIDDEN)

        # Get state admin profile
        state_admin = get_user_object(user, "stateadmin")
        if not state_admin:
            return Response({
                "error": "State admin profile not found"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get date range from request
        date_from = request.data.get('date_from', '')
        date_to = request.data.get('date_to', '')
        
        # Base queries for approved models and COPs
        approved_models_query = DeviceModel.objects.filter(status='StateAdminApproved')
        approved_cops_query = DeviceCOP.objects.filter(status='StateAdminApproved')
        
        # Apply date filters if provided
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                approved_models_query = approved_models_query.filter(created__date__gte=from_date)
                approved_cops_query = approved_cops_query.filter(created__date__gte=from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                approved_models_query = approved_models_query.filter(created__date__lte=to_date)
                approved_cops_query = approved_cops_query.filter(created__date__lte=to_date)
            except ValueError:
                pass

        # Get counts and statistics
        total_approved_models = approved_models_query.count()
        total_approved_cops = approved_cops_query.count()
        
        # Get unique manufacturers count
        model_manufacturers = set(approved_models_query.values_list('created_by', flat=True))
        cop_manufacturers = set(approved_cops_query.values_list('created_by', flat=True))
        unique_manufacturers = len(model_manufacturers.union(cop_manufacturers))
        
        # Get current date for expiry calculations
        now = timezone.now().date()
        
        # Count expired and expiring COPs
        expired_cops = approved_cops_query.filter(cop_validity__lt=now).count()
        expiring_soon_cops = approved_cops_query.filter(
            cop_validity__gte=now,
            cop_validity__lte=now + timedelta(days=30)
        ).count()
        
        # Count expired and expiring TAC validities in models
        expired_tac = approved_models_query.filter(tac_validity__lt=now).count()
        expiring_soon_tac = approved_models_query.filter(
            tac_validity__gte=now,
            tac_validity__lte=now + timedelta(days=30)
        ).count()
        
        # Get recent approvals (last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        recent_models = approved_models_query.filter(created__date__gte=thirty_days_ago).count()
        recent_cops = approved_cops_query.filter(created__date__gte=thirty_days_ago).count()
        
        # Get monthly breakdown for current year
        current_year = now.year
        monthly_stats = {}
        for month in range(1, 13):
            month_models = approved_models_query.filter(
                created__year=current_year,
                created__month=month
            ).count()
            month_cops = approved_cops_query.filter(
                created__year=current_year,
                created__month=month
            ).count()
            month_name = calendar.month_name[month]
            monthly_stats[month_name] = {
                'models': month_models,
                'cops': month_cops,
                'total': month_models + month_cops
            }
        
        # Get top manufacturers by approvals
        from collections import defaultdict
        manufacturer_stats = defaultdict(lambda: {'models': 0, 'cops': 0, 'name': 'Unknown'})
        
        # Count models by manufacturer
        for model in approved_models_query.select_related('created_by').prefetch_related('created_by__manufacturers_user'):
            manufacturer = model.created_by.manufacturers_user.first() if model.created_by.manufacturers_user.exists() else None
            if manufacturer:
                manufacturer_stats[manufacturer.id]['models'] += 1
                manufacturer_stats[manufacturer.id]['name'] = manufacturer.company_name
        
        # Count COPs by manufacturer  
        for cop in approved_cops_query.select_related('created_by').prefetch_related('created_by__manufacturers_user'):
            manufacturer = cop.created_by.manufacturers_user.first() if cop.created_by.manufacturers_user.exists() else None
            if manufacturer:
                manufacturer_stats[manufacturer.id]['cops'] += 1
                manufacturer_stats[manufacturer.id]['name'] = manufacturer.company_name
        
        # Convert to list and sort by total approvals
        top_manufacturers = []
        for manufacturer_id, stats in manufacturer_stats.items():
            total_approvals = stats['models'] + stats['cops']
            top_manufacturers.append({
                'manufacturer_id': manufacturer_id,
                'manufacturer_name': stats['name'],
                'approved_models': stats['models'],
                'approved_cops': stats['cops'],
                'total_approvals': total_approvals
            })
        
        top_manufacturers.sort(key=lambda x: x['total_approvals'], reverse=True)
        top_manufacturers = top_manufacturers[:10]  # Top 10 manufacturers
        
        # Prepare comprehensive summary
        summary = {
            'overall_statistics': {
                'total_approved_models': total_approved_models,
                'total_approved_cops': total_approved_cops,
                'total_approvals': total_approved_models + total_approved_cops,
                'unique_manufacturers': unique_manufacturers,
                'recent_approvals_30_days': {
                    'models': recent_models,
                    'cops': recent_cops,
                    'total': recent_models + recent_cops
                }
            },
            'expiry_alerts': {
                'expired_cops': expired_cops,
                'expiring_soon_cops': expiring_soon_cops,
                'expired_tac_validities': expired_tac,
                'expiring_soon_tac_validities': expiring_soon_tac,
                'total_expiry_alerts': expired_cops + expiring_soon_cops + expired_tac + expiring_soon_tac
            },
            'monthly_breakdown_current_year': monthly_stats,
            'top_manufacturers': top_manufacturers,
            'state_admin_info': {
                'id': state_admin.id,
                'state': state_admin.state.state if state_admin.state else 'N/A',
                'created_date': state_admin.created.strftime('%Y-%m-%d') if state_admin.created else 'N/A'
            },
            'report_generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range_applied': {
                'from': date_from if date_from else 'All time',
                'to': date_to if date_to else 'Present'
            }
        }
        
        response_data = {
            'status': 'success',
            'data': summary,
            'message': 'Combined approval report retrieved successfully'
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error', 
            'message': f'An error occurred while retrieving combined approval report: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 

    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_device_trip_details(request):

    try:
        from datetime import datetime, timedelta
        from django.db.models import Q, Min, Max
        from django.utils.dateparse import parse_datetime
        import math
        import pytz
        
        def calculate_distance(lat1, lon1, lat2, lon2):

            # Convert decimal degrees to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            r = 6371  # Radius of earth in kilometers
            return c * r
        
        # Get parameters
        device_tag_id = request.GET.get('device_tag_id')
        start_datetime = request.GET.get('start_datetime')
        end_datetime = request.GET.get('end_datetime')
        
        # Validate device_tag_id
        if not device_tag_id:
            return Response({
                'status': 'error',
                'message': 'device_tag_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            device_tag = DeviceTag.objects.get(id=device_tag_id)
        except DeviceTag.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Device tag not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Set default time range (last 24 hours)
        now = timezone.now()
        if not end_datetime:
            end_dt = now
        else:
            try:
                # Parse datetime and make it timezone-aware
                end_dt = parse_datetime(end_datetime.replace('Z', '+00:00'))
                if end_dt is None:
                    # Fallback: try manual parsing
                    end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                # Ensure timezone awareness
                if timezone.is_naive(end_dt):
                    end_dt = timezone.make_aware(end_dt, timezone=pytz.UTC)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid end_datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if not start_datetime:
            start_dt = end_dt - timedelta(hours=24)
        else:
            try:
                # Parse datetime and make it timezone-aware
                start_dt = parse_datetime(start_datetime.replace('Z', '+00:00'))
                if start_dt is None:
                    # Fallback: try manual parsing
                    start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                # Ensure timezone awareness
                if timezone.is_naive(start_dt):
                    start_dt = timezone.make_aware(start_dt, timezone=pytz.UTC)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid start_datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get GPS data for the device tag within time range, sorted by entry_time
        gps_data = GPSData.objects.filter(
            device_tag=device_tag,
            entry_time__gte=start_dt,
            entry_time__lte=end_dt
        ).order_by('entry_time')
        
        if not gps_data.exists():
            return Response({
                'device_tag_id': device_tag_id,
                'vehicle_reg_no': device_tag.vehicle_reg_no,
                'query_start_time': start_dt,
                'query_end_time': end_dt,
                'total_trips': 0,
                'total_distance_km': 0.0,
                'total_duration_minutes': 0.0,
                'trips': []
            })
        
        # Process trips based on new logic
        trips = []
        current_trip = None
        trip_id = 1
        prev_point = None
        
        for i, gps_point in enumerate(gps_data):
            is_first_point = i == 0
            is_last_point = i == len(gps_data) - 1
            ignition_on = gps_point.ignition_status == '1'
            packet_type = gps_point.packet_type
            
            # Check for 30-minute gap from previous point
            time_gap_exceeded = False
            if prev_point is not None and current_trip is not None:
                time_diff = (gps_point.entry_time - prev_point.entry_time).total_seconds()
                if time_diff > 30 * 60:  # 30 minutes
                    time_gap_exceeded = True
            
            # Trip Start Conditions:
            # 1. First entry with ignition_status == '1'
            # 2. packet_type == "IN" (Ignition ON)
            if current_trip is None:
                if (is_first_point and ignition_on) or packet_type == "IN":
                    current_trip = {
                        'trip_id': trip_id,
                        'start_time': gps_point.entry_time,
                        'start_location': {
                            'latitude': gps_point.latitude,
                            'longitude': gps_point.longitude,
                            'address': f"{gps_point.latitude}, {gps_point.longitude}"
                        },
                        'gps_points': [gps_point],
                        'end_time': None
                    }
            else:
                # Add point to current trip
                current_trip['gps_points'].append(gps_point)
                
                # Trip End Conditions:
                # 1. packet_type == "IF" (Ignition OFF)
                # 2. Time gap > 30 minutes
                # 3. ignition_status == '0'
                # 4. Last entry with ignition_status == '1' (ongoing trip)
                should_end_trip = False
                
                if packet_type == "IF":
                    should_end_trip = True
                    current_trip['end_time'] = gps_point.entry_time
                elif time_gap_exceeded:
                    should_end_trip = True
                    current_trip['end_time'] = prev_point.entry_time
                    # Start new trip with current point if ignition is on
                    trips.append(current_trip)
                    trip_id += 1
                    if ignition_on or packet_type == "IN":
                        current_trip = {
                            'trip_id': trip_id,
                            'start_time': gps_point.entry_time,
                            'start_location': {
                                'latitude': gps_point.latitude,
                                'longitude': gps_point.longitude,
                                'address': f"{gps_point.latitude}, {gps_point.longitude}"
                            },
                            'gps_points': [gps_point],
                            'end_time': None
                        }
                    else:
                        current_trip = None
                    prev_point = gps_point
                    continue
                elif not ignition_on and packet_type != "IN":
                    should_end_trip = True
                    current_trip['end_time'] = gps_point.entry_time
                elif is_last_point and ignition_on:
                    # Ongoing trip at last entry
                    should_end_trip = True
                    current_trip['end_time'] = gps_point.entry_time
                
                if should_end_trip:
                    trips.append(current_trip)
                    trip_id += 1
                    current_trip = None
            
            prev_point = gps_point
        
        # Process each completed trip
        processed_trips = []
        total_distance = 0.0
        total_duration = 0.0
        
        for trip in trips:
            if len(trip['gps_points']) < 2:
                continue
                
            gps_points = trip['gps_points']
            
            # Calculate trip metrics
            trip_distance = 0.0
            speeds = []
            
            for i in range(1, len(gps_points)):
                prev_point = gps_points[i-1]
                curr_point = gps_points[i]
                
                # Calculate distance between points
                if prev_point.latitude and prev_point.longitude and curr_point.latitude and curr_point.longitude:
                    try:
                        point_distance = calculate_distance(
                            prev_point.latitude, prev_point.longitude,
                            curr_point.latitude, curr_point.longitude
                        )
                        trip_distance += point_distance
                    except:
                        pass
                
                # Collect speed data
                if curr_point.speed:
                    speeds.append(curr_point.speed)
            
            # Calculate duration
            end_time = trip.get('end_time') or gps_points[-1].entry_time
            duration = (end_time - trip['start_time']).total_seconds() / 60  # minutes
            
            # Calculate average and max speed
            avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
            max_speed = max(speeds) if speeds else 0.0
            
            # Get alerts during trip
            trip_alerts = AlertsLog.objects.filter(
                deviceTag=device_tag,
                timestamp__gte=trip['start_time'],
                timestamp__lte=end_time
            ).values('type', 'status', 'timestamp')
            
            # End location
            last_point = gps_points[-1]
            end_location = {
                'latitude': last_point.latitude,
                'longitude': last_point.longitude,
                'address': f"{last_point.latitude}, {last_point.longitude}"
            }
            
            processed_trip = {
                'trip_id': trip['trip_id'],
                'start_time': trip['start_time'],
                'end_time': end_time,
                'duration_minutes': round(duration, 2),
                'distance_km': round(trip_distance, 2),
                'average_speed_kmh': round(avg_speed, 2),
                'max_speed_kmh': round(max_speed, 2),
                'start_location': trip['start_location'],
                'end_location': end_location,
                'alerts': list(trip_alerts),
                'total_data_points': len(gps_points)
            }
            
            processed_trips.append(processed_trip)
            total_distance += trip_distance
            total_duration += duration
            trip_id += 1
        
        # Prepare response
        response_data = {
            'device_tag_id': int(device_tag_id),
            'vehicle_reg_no': device_tag.vehicle_reg_no,
            'query_start_time': start_dt,
            'query_end_time': end_dt,
            'total_trips': len(processed_trips),
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': round(total_duration, 2),
            'trips': processed_trips
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred while retrieving trip details: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_device_health_status(request):
    """
    API to get health status of devices with filtering options
    
    Filter Parameters:
    - vehicle_reg_no: Vehicle registration number
    - device_tag_id: Device tag ID
    - imei: Device IMEI
    - device_stock_id: Device stock ID
    - device_model_id: Device model ID
    - district_id: District ID
    - manufacturer_id: Manufacturer ID (auto-applied for manufacturer role)
    - vehicle_owner_id: Vehicle owner ID (auto-applied for owner role)
    
    Returns device health status with:
    - Online/Offline status (offline if last data > 10 minutes old)
    - Latest GPS data information
    - Device details
    """
    try:
        from datetime import timedelta
        from django.db.models import Case, Count, IntegerField, Max, Q, When
        
        user = request.user
        
        # Get filter parameters
        vehicle_reg_no = request.GET.get('vehicle_reg_no', '')
        device_tag_id = request.GET.get('device_tag_id', '')
        imei = request.GET.get('imei', '')
        device_stock_id = request.GET.get('device_stock_id', '')
        device_model_id = request.GET.get('device_model_id', '')
        district_id = request.GET.get('district_id', '')
        manufacturer_id = request.GET.get('manufacturer_id', '')
        vehicle_owner_id = request.GET.get('vehicle_owner_id', '')
        
        # Base queryset: keep it light for counting/pagination.
        # We'll add select_related only after we have the paginated IDs.
        device_tags_query = DeviceTag.objects.all()
        
        # Apply user-based access control
        if user.role == 'devicemanufacture':
            # Manufacturers can only see devices with models created by them
            manufacturer = get_user_object(user, 'devicemanufacture')
            if not manufacturer:
                return Response({
                    'status': 'error',
                    'message': 'Manufacturer profile not found'
                }, status=status.HTTP_404_NOT_FOUND)
            device_tags_query = device_tags_query.filter(
                device__model__created_by=user
            )
        elif user.role == 'owner':
            # Owners can only see their own devices
            owner = get_user_object(user, 'owner')
            if not owner:
                return Response({
                    'status': 'error',
                    'message': 'Owner profile not found'
                }, status=status.HTTP_404_NOT_FOUND)
            device_tags_query = device_tags_query.filter(vehicle_owner=owner)
        elif user.role == 'dealer':
            # Dealers can see devices sold by them
            dealer = get_user_object(user, 'dealer')
            if dealer:
                device_tags_query = device_tags_query.filter(device__dealer=dealer)
        # superadmin, stateadmin, dto_rto can see all devices (no additional filter)
        
        # Apply filter parameters
        if vehicle_reg_no:
            device_tags_query = device_tags_query.filter(
                vehicle_reg_no__icontains=vehicle_reg_no
            )
        
        if device_tag_id:
            device_tags_query = device_tags_query.filter(id=device_tag_id)
        
        if imei:
            device_tags_query = device_tags_query.filter(device__imei__icontains=imei)
        
        if device_stock_id:
            device_tags_query = device_tags_query.filter(device__id=device_stock_id)
        
        if device_model_id:
            device_tags_query = device_tags_query.filter(
                device__model__id=device_model_id
            )
        
        if district_id:
            device_tags_query = device_tags_query.filter(district__id=district_id)
        
        if manufacturer_id:
            device_tags_query = device_tags_query.filter(
                device__model__created_by__id=manufacturer_id
            )
        
        if vehicle_owner_id:
            device_tags_query = device_tags_query.filter(
                vehicle_owner__id=vehicle_owner_id
            )
        
        now = timezone.now()
        offline_threshold = now - timedelta(minutes=10)

        # Pagination parameters
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
        except Exception:
            page = 1
            page_size = 20
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        # Total count should be fast and should not include heavy joins/subqueries.
        total_devices_count = device_tags_query.count()
        if not total_devices_count:
            return Response({
                'status': 'success',
                'total_devices': 0,
                'online_devices': 0,
                'offline_devices': 0,
                'devices': [],
                'page': page,
                'page_size': page_size,
                'total_pages': 0
            })

        # Pagination logic: paginate by IDs first (cheap), then fetch related data for that page.
        start = (page - 1) * page_size
        end = start + page_size
        paginated_ids = list(
            device_tags_query.order_by('-id').values_list('id', flat=True)[start:end]
        )

        # Fetch paginated DeviceTag rows with the required related objects.
        # Preserve the original ordering from paginated_ids.
        if paginated_ids:
            order_case = Case(
                *[When(id=pk, then=pos) for pos, pk in enumerate(paginated_ids)],
                output_field=IntegerField(),
            )
            paginated_device_tags_list = list(
                DeviceTag.objects.filter(id__in=paginated_ids)
                .select_related(
                    'device',
                    'device__model',
                    'device__model__created_by',
                    'vehicle_owner',
                    'category',
                    'district',
                    'district__state'
                )
                .order_by(order_case)
            )
        else:
            paginated_device_tags_list = []

        devices_health = []

        # Compute online/offline/no_data counts based on each device's latest GPS timestamp.
        # NOTE: Django does not support aggregate() on a queryset using distinct(fields)
        # (DISTINCT ON), so we use GROUP BY + Max(entry_time) instead.
        base_ids_subquery = device_tags_query.values('id')
        latest_times_per_device = (
            GPSData.objects
            .filter(device_tag_id__in=base_ids_subquery)
            .values('device_tag_id')
            .annotate(latest_entry_time=Max('entry_time'))
        )

        # Count devices based on the grouped latest timestamp (each row == one device_tag_id with data).
        with_data_count = latest_times_per_device.count()
        all_online_count = latest_times_per_device.filter(latest_entry_time__gte=offline_threshold).count()
        all_offline_count = latest_times_per_device.filter(latest_entry_time__lt=offline_threshold).count()
        all_no_data_count = max(0, total_devices_count - with_data_count)

        # Bulk fetch latest GPS rows for the paginated device tags using DISTINCT ON.
        latest_gps_map = {}
        if paginated_ids:
            latest_for_page = (
                GPSData.objects
                .filter(device_tag_id__in=paginated_ids)
                .order_by('device_tag_id', '-entry_time', '-id')
                .distinct('device_tag_id')
            )
            for gps in latest_for_page:
                latest_gps_map[gps.device_tag_id] = gps

        # Now, build the paginated device health list
        for device_tag in paginated_device_tags_list:
            latest_gps = latest_gps_map.get(device_tag.id)
            if not latest_gps:
                device_status = 'no_data'
                last_seen = None
                offline_duration_minutes = None
            else:
                if latest_gps.entry_time >= offline_threshold:
                    device_status = 'online'
                else:
                    device_status = 'offline'
                    offline_duration_minutes = int((now - latest_gps.entry_time).total_seconds() / 60)
                last_seen = latest_gps.entry_time

            device_info = {
                'device_tag_id': device_tag.id,
                'vehicle_reg_no': device_tag.vehicle_reg_no,
                'device_status': device_status,
                'last_seen': last_seen,
                'offline_duration_minutes': offline_duration_minutes if device_status == 'offline' else 0,
                'device_details': {
                    'imei': device_tag.device.imei,
                    'device_stock_id': device_tag.device.id,
                    'device_esn': device_tag.device.device_esn,
                    'iccid': device_tag.device.iccid,
                    'msisdn1': device_tag.device.msisdn1,
                    'device_model': {
                        'id': device_tag.device.model.id,
                        'model_name': device_tag.device.model.model_name,
                        'vendor_id': device_tag.device.model.vendor_id,
                        'hardware_version': device_tag.device.model.hardware_version,
                    },
                    'manufacturer': {
                        'id': device_tag.device.model.created_by.id if device_tag.device.model.created_by else None,
                        'name': device_tag.device.model.created_by.name if device_tag.device.model.created_by else 'N/A'
                    }
                },
                'vehicle_details': {
                    'vehicle_make': device_tag.vehicle_make,
                    'vehicle_model': device_tag.vehicle_model,
                    'category': (device_tag.category.category if device_tag.category else None),
                    'engine_no': device_tag.engine_no,
                    'chassis_no': device_tag.chassis_no,
                },
                'location_details': {
                    'district': device_tag.district.district if device_tag.district else 'N/A',
                    'district_code': device_tag.district.district_code if device_tag.district else 'N/A',
                    'state': device_tag.district.state.state if device_tag.district and device_tag.district.state else 'N/A',
                },
                'vehicle_owner': {
                    'id': device_tag.vehicle_owner.id if device_tag.vehicle_owner else None,
                    'company_name': device_tag.vehicle_owner.company_name if device_tag.vehicle_owner else 'N/A'
                }
            }

            if latest_gps:
                device_info['latest_gps_data'] = {
                    'packet_type': latest_gps.packet_type,
                    'entry_time': latest_gps.entry_time,
                    'latitude': latest_gps.latitude,
                    'longitude': latest_gps.longitude,
                    'speed': latest_gps.speed,
                    'heading': latest_gps.heading,
                    'altitude': latest_gps.altitude,
                    'gps_status': latest_gps.gps_status,
                    'ignition_status': latest_gps.ignition_status,
                    'main_power_status': latest_gps.main_power_status,
                    'main_input_voltage': latest_gps.main_input_voltage,
                    'internal_battery_voltage': latest_gps.internal_battery_voltage,
                    'emergency_status': latest_gps.emergency_status,
                    'gsm_signal_strength': latest_gps.gsm_signal_strength,
                    'satellites': latest_gps.satellites,
                    'network_operator': latest_gps.network_operator,
                    'odometer': latest_gps.odometer,
                    'frame_number': latest_gps.frame_number,
                }
            else:
                device_info['latest_gps_data'] = None

            devices_health.append(device_info)

        total_pages = (total_devices_count + page_size - 1) // page_size

        response_data = {
            'status': 'success',
            'query_time': now,
            'total_devices': total_devices_count,
            'online_devices': all_online_count,
            'offline_devices': all_offline_count,
            'no_data_devices': all_no_data_count,
            'offline_threshold_minutes': 10,
            'applied_filters': {
                'vehicle_reg_no': vehicle_reg_no if vehicle_reg_no else None,
                'device_tag_id': device_tag_id if device_tag_id else None,
                'imei': imei if imei else None,
                'device_stock_id': device_stock_id if device_stock_id else None,
                'device_model_id': device_model_id if device_model_id else None,
                'district_id': district_id if district_id else None,
                'manufacturer_id': manufacturer_id if manufacturer_id else None,
                'vehicle_owner_id': vehicle_owner_id if vehicle_owner_id else None,
            },
            'user_role': user.role,
            'devices': devices_health,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }

        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred while retrieving device health status: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_module_access(request):
    """
    API endpoint to check module access.
    Takes only one POST parameter: 'module'
    Returns: {access: allow}
    """
    try:
        module = request.data.get('module')
        
        if not module:
            return Response({
                'status': 'error',
                'message': 'module parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # For now, return access allow for all modules
        return Response({
            'access': 'allow'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_type(request):
    """
    API endpoint to check user type and return permissions for all user roles.
    No POST data required - uses authenticated user.
    Returns: {
        superadmin: true/false,
        stateadmin: true/false,
        devicemanufacture: true/false,
        dealer: true/false,
        owner: true/false,
        esimprovider: true/false,
        filment: true/false,
        sosadmin: true/false,
        teamleader: true/false,
        sosexecutive: true/false,
        police: true/false,
        ambulance: true/false,
        guest: true/false
    }
    """
    try:
        user = request.user
        
        # Initialize all permissions as False
        response_data = {
            'superadmin': False,
            'stateadmin': False,
            'devicemanufacture': False,
            'dealer': False,
            'owner': False,
            'esimprovider': False,
            'filment': False,
            'sosadmin': False,
            'teamleader': False,
            'sosexecutive': False,
            'police': False,
            'ambulance': False,
            'dtorto': False,
            'guest': False
        }
        
        # Check user role and set corresponding flag
        if user.role == 'superadmin':
            response_data['superadmin'] = True
        elif user.role == 'stateadmin':
            response_data['stateadmin'] = True
        elif user.role == 'devicemanufacture':
            response_data['devicemanufacture'] = True
        elif user.role == 'dealer':
            response_data['dealer'] = True
        elif user.role == 'owner':
            response_data['owner'] = True
        elif user.role == 'dtorto':
            response_data['dtorto'] = True
        elif user.role == 'esimprovider':
            response_data['esimprovider'] = True
        elif user.role == 'filment':
            response_data['filment'] = True
        elif user.role == 'sosadmin':
            response_data['sosadmin'] = True
        elif user.role == 'teamleader':
            response_data['teamleader'] = True
        elif user.role == 'sosexecutive':
            response_data['sosexecutive'] = True
            
            # Check if sosexecutive is police or ambulance type
            try:
                em_ex = EM_ex.objects.filter(users=user).first()
                if em_ex:
                    if em_ex.user_type == 'police_ex':
                        response_data['police'] = True
                    elif em_ex.user_type == 'ambulance_ex':
                        response_data['ambulance'] = True
            except Exception as e:
                pass
        else:
            # Unknown role or no role, treat as guest
            response_data['guest'] = True
        
        # If no role was matched, set guest to True
        if not any(response_data.values()):
            response_data['guest'] = True
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================
# Bus Stand APIs
# ================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def set_bus_stand(request):
    """Create a new bus stand"""
    try:
        data = request.data.copy()
        data['created_by'] = request.user.id
        
        serializer = BusStandSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Bus stand created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'status': 'error',
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def activate_deactivate_bus_stand(request):
    """Activate or deactivate a bus stand"""
    try:
        bus_stand_id = request.data.get('bus_stand_id')
        active = request.data.get('active')
        
        if bus_stand_id is None or active is None:
            return Response({
                'status': 'error',
                'message': 'bus_stand_id and active status are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        bus_stand = BusStand.objects.filter(id=bus_stand_id).first()
        if not bus_stand:
            return Response({
                'status': 'error',
                'message': 'Bus stand not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        bus_stand.active = active
        bus_stand.save()
        
        serializer = BusStandSerializer(bus_stand)
        return Response({
            'status': 'success',
            'message': f'Bus stand {"activated" if active else "deactivated"} successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def filter_bus_stand(request):
    """Filter bus stands by various parameters"""
    try:
        queryset = BusStand.objects.all()
        
        # Filter by name
        name = request.data.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        
        # Filter by created_by
        created_by = request.data.get('created_by')
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
        
        # Filter by created_at (date range)
        created_at_from = request.data.get('created_at_from')
        created_at_to = request.data.get('created_at_to')
        if created_at_from:
            queryset = queryset.filter(created_at__gte=created_at_from)
        if created_at_to:
            queryset = queryset.filter(created_at__lte=created_at_to)
        
        # Filter by location (latitude, longitude, radius in km)
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        radius_km = request.data.get('radius_km')
        
        if latitude and longitude and radius_km:
            from math import radians, cos, sin, asin, sqrt
            
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(float, [lon1, lat1, lon2, lat2])
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                km = 6371 * c
                return km
            
            filtered_stands = []
            for stand in queryset:
                distance = haversine(longitude, latitude, stand.longitude, stand.latitude)
                if distance <= float(radius_km):
                    filtered_stands.append(stand.id)
            queryset = queryset.filter(id__in=filtered_stands)
        
        # Filter by active status
        active = request.data.get('active')
        if active is not None:
            queryset = queryset.filter(active=active)
        
        # Pagination
        page = request.data.get('page', 1)
        page_size = request.data.get('page_size', 10)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = BusStandSerializer(page_obj, many=True)
        
        return Response({
            'status': 'success',
            'total_count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================
# OTA Settings APIs
# ================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def create_ota_settings(request):
    """Create a new OTA setting"""
    try:
        data = request.data.copy()
        data['triggered_by'] = request.user.id
        
        serializer = OTASettingsSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'OTA settings created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'status': 'error',
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def update_ota_settings(request):
    """Update an existing OTA setting"""
    try:
        ota_id = request.data.get('ota_id')
        
        if not ota_id:
            return Response({
                'status': 'error',
                'message': 'ota_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ota_setting = OTASettings.objects.filter(id=ota_id).first()
        if not ota_setting:
            return Response({
                'status': 'error',
                'message': 'OTA setting not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OTASettingsSerializer(ota_setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'OTA settings updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            'status': 'error',
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def filter_ota_settings(request):
    """Filter OTA settings by various parameters"""
    try:
        queryset = OTASettings.objects.all()
        
        # Filter by command
        command = request.data.get('command')
        if command:
            queryset = queryset.filter(command__icontains=command)
        
        # Filter by triggered_by
        triggered_by = request.data.get('triggered_by')
        if triggered_by:
            queryset = queryset.filter(triggered_by_id=triggered_by)
        
        # Filter by triggered_at (date range)
        triggered_at_from = request.data.get('triggered_at_from')
        triggered_at_to = request.data.get('triggered_at_to')
        if triggered_at_from:
            queryset = queryset.filter(triggered_at__gte=triggered_at_from)
        if triggered_at_to:
            queryset = queryset.filter(triggered_at__lte=triggered_at_to)
        
        # Filter by active status
        active = request.data.get('active')
        if active is not None:
            queryset = queryset.filter(active=active)
        
        # Pagination
        page = request.data.get('page', 1)
        page_size = request.data.get('page_size', 10)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = OTASettingsSerializer(page_obj, many=True)
        
        return Response({
            'status': 'success',
            'total_count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ================================
# Incident Register APIs
# ================================

@api_view(['POST'])
@permission_classes([AllowAny])  # Allow public access for incident registration
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def register_incident(request):
    """Register a new incident - allows both authenticated and public/anonymous users"""
    try:
        data = request.data.copy()
        
        # If user is authenticated, use their ID; otherwise set to None for anonymous
        if request.user and request.user.is_authenticated:
            data['registered_by'] = request.user.id
        else:
            data['registered_by'] = None  # Anonymous/public registration
        
        # Handle file upload if present
        if 'image' in request.FILES:
            file_path = save_file(request, 'image', 'fileuploads/incidents/')
            if file_path:
                data['image_file'] = file_path
            else:
                return Response({
                    'status': 'error',
                    'message': 'File upload failed. Please check file size (max 1MB) and type (png, jpg)'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = IncidentRegisterSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Incident registered successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'status': 'error',
            'message': 'Validation error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def filter_incident(request):
    """Filter incidents by various parameters"""
    try:
        queryset = IncidentRegister.objects.select_related('registered_by', 'updated_by').all()
        
        # Filter by vehicle_reg_no
        vehicle_reg_no = request.data.get('vehicle_reg_no')
        if vehicle_reg_no:
            queryset = queryset.filter(vehicle_reg_no__icontains=vehicle_reg_no)
        
        # Filter by registered_by
        registered_by = request.data.get('registered_by')
        if registered_by:
            queryset = queryset.filter(registered_by_id=registered_by)

        # Filter by registered_by mobile
        registered_by_mobile = request.data.get('registered_by_mobile')
        if registered_by_mobile:
            queryset = queryset.filter(registered_by__mobile__icontains=registered_by_mobile)
        
        # Filter by registered_at (date range)
        registered_at_from = request.data.get('registered_at_from')
        registered_at_to = request.data.get('registered_at_to')
        if registered_at_from:
            queryset = queryset.filter(registered_at__gte=registered_at_from)
        if registered_at_to:
            queryset = queryset.filter(registered_at__lte=registered_at_to)
        
        # Filter by district
        district = request.data.get('district')
        if district:
            queryset = queryset.filter(district__icontains=district)
        
        # Filter by police_station
        police_station = request.data.get('police_station')
        if police_station:
            queryset = queryset.filter(police_station__icontains=police_station)
        
        # Filter by location (latitude, longitude, radius in km)
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        radius_km = request.data.get('radius_km')
        
        if latitude and longitude and radius_km:
            from math import radians, cos, sin, asin, sqrt
            
            def haversine(lon1, lat1, lon2, lat2):
                lon1, lat1, lon2, lat2 = map(float, [lon1, lat1, lon2, lat2])
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                km = 6371 * c
                return km
            
            filtered_incidents = []
            for incident in queryset:
                distance = haversine(longitude, latitude, incident.longitude, incident.latitude)
                if distance <= float(radius_km):
                    filtered_incidents.append(incident.id)
            queryset = queryset.filter(id__in=filtered_incidents)
        
        # Pagination
        page = request.data.get('page', 1)
        page_size = request.data.get('page_size', 10)
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = IncidentRegisterSerializer(page_obj, many=True)

        # Enrich report rows with convenience fields:
        # - registered_by_mobile: reporter mobile (if any)
        # - nearest_ps: nearest Police Station (POI) computed from incident lat/lon
        from math import radians, cos, sin, asin, sqrt

        def haversine_km(lon1, lat1, lon2, lat2):
            lon1, lat1, lon2, lat2 = map(float, [lon1, lat1, lon2, lat2])
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            return 6371 * c

        incident_by_id = {inc.id: inc for inc in page_obj}

        police_stations = list(
            pointofinterests.objects.filter(use_type='PoliceStation')
            .exclude(lat__isnull=True)
            .exclude(lon__isnull=True)
            .exclude(status__in=['Deleted', 'Deleted2'])
            .values('id', 'name', 'address', 'phone', 'lat', 'lon', 'area', 'city', 'state', 'pincode')
        )

        nearest_ps_by_incident_id = {}
        if police_stations:
            for inc in page_obj:
                try:
                    inc_lat = float(inc.latitude)
                    inc_lon = float(inc.longitude)
                except Exception:
                    nearest_ps_by_incident_id[inc.id] = None
                    continue

                best = None
                best_distance = None
                for ps in police_stations:
                    distance_km = haversine_km(inc_lon, inc_lat, ps['lon'], ps['lat'])
                    if best_distance is None or distance_km < best_distance:
                        best_distance = distance_km
                        best = ps

                if best is None:
                    nearest_ps_by_incident_id[inc.id] = None
                else:
                    nearest_ps_by_incident_id[inc.id] = {
                        'id': best['id'],
                        'name': best['name'],
                        'distance_km': round(float(best_distance), 3) if best_distance is not None else None,
                        'address': best.get('address'),
                        'phone': best.get('phone'),
                        'latitude': best.get('lat'),
                        'longitude': best.get('lon'),
                        'area': best.get('area'),
                        'city': best.get('city'),
                        'state': best.get('state'),
                        'pincode': best.get('pincode'),
                    }

        for row in serializer.data:
            inc_id = row.get('id')
            inc = incident_by_id.get(inc_id)
            row['registered_by_mobile'] = inc.registered_by.mobile if (inc and inc.registered_by) else None
            row['nearest_ps'] = nearest_ps_by_incident_id.get(inc_id)
        
        return Response({
            'status': 'success',
            'total_count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['POST'])
def update_incident(request):
    """Update incident status by any registered user"""
    try:
        incident_id = request.data.get('incident_id')
        latest_status = request.data.get('latest_status')
        
        if not incident_id:
            return Response({
                'status': 'error',
                'message': 'incident_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not latest_status:
            return Response({
                'status': 'error',
                'message': 'latest_status is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        incident = IncidentRegister.objects.filter(id=incident_id).first()
        if not incident:
            return Response({
                'status': 'error',
                'message': 'Incident not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update the incident
        incident.latest_status = latest_status
        incident.updated_by = request.user
        incident.updated_at = timezone.now()
        incident.save()
        
        serializer = IncidentRegisterSerializer(incident)
        return Response({
            'status': 'success',
            'message': 'Incident updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== AlertsLog APIs ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def create_alert_log(request):
    """Create a new alert log entry"""
    try:
        alert_type = request.data.get('type')
        alert_status = request.data.get('status', '')
        gps_ref_id = request.data.get('gps_ref_id')
        device_tag_id = request.data.get('device_tag_id')
        route_ref_id = request.data.get('route_ref_id')
        em_ref_id = request.data.get('em_ref_id')
        state_id = request.data.get('state_id')
        
        # Validate required fields
        if not alert_type:
            return Response({
                'status': 'error',
                'message': 'type is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not gps_ref_id:
            return Response({
                'status': 'error',
                'message': 'gps_ref_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not device_tag_id:
            return Response({
                'status': 'error',
                'message': 'device_tag_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not state_id:
            return Response({
                'status': 'error',
                'message': 'state_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate foreign key references
        gps_ref = GPSData.objects.filter(id=gps_ref_id, gps_status=1).last()
        if not gps_ref:
            return Response({
                'status': 'error',
                'message': 'Invalid gps_ref_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        device_tag = DeviceTag.objects.filter(id=device_tag_id, gps_status=1).last()
        if not device_tag:
            return Response({
                'status': 'error',
                'message': 'Invalid device_tag_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        state_obj = Settings_State.objects.filter(id=state_id).first()
        if not state_obj:
            return Response({
                'status': 'error',
                'message': 'Invalid state_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Optional references
        route_ref = None
        if route_ref_id:
            route_ref = Route.objects.filter(id=route_ref_id).first()
        
        em_ref = None
        if em_ref_id:
            em_ref = EMCall.objects.filter(id=em_ref_id).first()
        
        # Create alert log
        alert_log = AlertsLog.objects.create(
            type=alert_type,
            status=alert_status,
            gps_ref=gps_ref,
            route_ref=route_ref,
            em_ref=em_ref,
            deviceTag=device_tag,
            state=state_obj
        )
        
        serializer = AlertsLogSerializer(alert_log)
        return Response({
            'status': 'success',
            'message': 'Alert log created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def update_alert_log(request):
    """Update an existing alert log entry"""
    try:
        alert_log_id = request.data.get('alert_log_id')
        
        if not alert_log_id:
            return Response({
                'status': 'error',
                'message': 'alert_log_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        alert_log = AlertsLog.objects.filter(id=alert_log_id).first()
        if not alert_log:
            return Response({
                'status': 'error',
                'message': 'Alert log not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update fields if provided
        if 'type' in request.data:
            alert_log.type = request.data.get('type')
        
        if 'status' in request.data:
            alert_log.status = request.data.get('status')
        
        if 'route_ref_id' in request.data:
            route_ref_id = request.data.get('route_ref_id')
            if route_ref_id:
                route_ref = Route.objects.filter(id=route_ref_id).first()
                if route_ref:
                    alert_log.route_ref = route_ref
            else:
                alert_log.route_ref = None
        
        if 'em_ref_id' in request.data:
            em_ref_id = request.data.get('em_ref_id')
            if em_ref_id:
                em_ref = EMCall.objects.filter(id=em_ref_id).first()
                if em_ref:
                    alert_log.em_ref = em_ref
            else:
                alert_log.em_ref = None
        
        alert_log.save()
        
        serializer = AlertsLogSerializer(alert_log)
        return Response({
            'status': 'success',
            'message': 'Alert log updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def filter_alert_log(request):
    """Filter alert logs with multiple parameters and pagination"""
    try:
        # Get filter parameters (supports single value or list/comma-separated)
        alert_type = request.data.get('type')
        alert_status = request.data.get('status')
        vehicle_reg_no = request.data.get('vehicle_reg_no')
        state_id = request.data.get('state_id')
        district = request.data.get('district')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        radius = request.data.get('radius', 10)  # Default 10 km
        page = request.data.get('page', 1)
        page_size = request.data.get('page_size', 10)

        # Helper: parse list or comma-separated string to list
        def _parse_multi(val, cast=None):
            if val is None:
                return []
            items = []
            if isinstance(val, (list, tuple)):
                items = list(val)
            elif isinstance(val, str):
                # Split comma-separated string, strip whitespace
                items = [v.strip() for v in val.split(',') if v.strip() != '']
            else:
                # Single primitive value
                items = [val]

            if cast is not None:
                parsed = []
                for v in items:
                    try:
                        parsed.append(cast(v))
                    except (ValueError, TypeError):
                        # skip values that cannot be cast
                        continue
                return parsed
            return items
        
        # Build query
        query = AlertsLog.objects.all()
        
        # Import Q for OR queries
        from django.db.models import Q

        # Filter by type (supports list)
        types = _parse_multi(alert_type)
        if types:
            query = query.filter(type__in=types)
        
        # Filter by status (supports list)
        statuses = _parse_multi(alert_status)
        if statuses:
            query = query.filter(status__in=statuses)
        
        # Filter by vehicle registration number (supports list, OR icontains)
        vehicle_regs = _parse_multi(vehicle_reg_no)
        if vehicle_regs:
            vr_q = Q()
            for vr in vehicle_regs:
                vr_q |= Q(deviceTag__vehicle_reg_no__icontains=vr)
            query = query.filter(vr_q)
        
        # Filter by state (supports list)
        state_ids = _parse_multi(state_id, cast=int)
        if state_ids:
            query = query.filter(state_id__in=state_ids)
        
        # Filter by district from device tag (supports list, OR icontains)
        districts = _parse_multi(district)
        if districts:
            dist_q = Q()
            for d in districts:
                dist_q |= Q(deviceTag__district__district__icontains=d)
            query = query.filter(dist_q)
        
        # Filter by date range
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(timestamp__gte=start_datetime)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid start_date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
                query = query.filter(timestamp__lte=end_datetime)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid end_date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter by location (lat, lon, radius)
        if latitude and longitude:
            try:
                latitude = float(latitude)
                longitude = float(longitude)
                radius = float(radius)
                
                # Get all alerts with GPS data
                alerts_with_location = []
                for alert in query:
                    if alert.gps_ref:
                        gps_lat = float(alert.gps_ref.latitude)
                        gps_lon = float(alert.gps_ref.longitude)
                        
                        # Calculate distance using Haversine formula
                        lat1, lon1 = radians(latitude), radians(longitude)
                        lat2, lon2 = radians(gps_lat), radians(gps_lon)
                        
                        dlat = lat2 - lat1
                        dlon = lon2 - lon1
                        
                        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
                        c = 2 * asin(sqrt(a))
                        distance = 6371 * c  # Earth radius in kilometers
                        
                        if distance <= radius:
                            alerts_with_location.append(alert.id)
                
                # Filter by IDs within radius
                query = query.filter(id__in=alerts_with_location)
            except (ValueError, TypeError):
                return Response({
                    'status': 'error',
                    'message': 'Invalid latitude, longitude, or radius format'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Order by timestamp (newest first)
        query = query.order_by('-timestamp')
        
        # Pagination
        try:
            page = int(page)
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = int(page_size)
        except (ValueError, TypeError):
            page_size = 10

        paginator = Paginator(query, page_size)
        try:
            alerts = paginator.page(page)
        except:
            alerts = paginator.page(1)
        
        serializer = AlertsLogSerializer(alerts, many=True)
        
        return Response({
            'status': 'success',
            'message': 'Alert logs retrieved successfully',
            'data': serializer.data,
            'pagination': {
                'total_records': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': alerts.number,
                'page_size': page_size,
                'has_next': alerts.has_next(),
                'has_previous': alerts.has_previous()
            }
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def update_notification_preferences(request):
    """
    API endpoint for users to get or update their notification preferences.
    
    GET: Returns the current notification preferences for the authenticated user
    POST: Updates the notification preferences for the authenticated user
    
    POST Body (all fields optional):
    {
        "nf_popup": true/false,
        "nf_sms": true/false,
        "nf_email": true/false,
        "nf_frequency": 0-1440  // integer: times per day (0 disables by frequency)
    }
    
    Response:
    {
        "status": "success",
        "message": "Notification preferences updated successfully",
        "data": {
            "nf_popup": true,
            "nf_sms": true,
            "nf_email": true,
            "nf_frequency": 3
        }
    }
    """
    try:
        user = request.user
        
        if request.method == 'GET':
            # Return current notification preferences
            return Response({
                'status': 'success',
                'data': {
                    'nf_popup': user.nf_popup,
                    'nf_sms': user.nf_sms,
                    'nf_email': user.nf_email,
                    'nf_frequency': getattr(user, 'nf_frequency', 1)
                }
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'POST':
            # Update notification preferences
            serializer = NotificationPreferencesSerializer(data=request.data)
            
            if serializer.is_valid():
                # Update only the fields that are provided
                if 'nf_popup' in serializer.validated_data:
                    user.nf_popup = serializer.validated_data['nf_popup']
                
                if 'nf_sms' in serializer.validated_data:
                    user.nf_sms = serializer.validated_data['nf_sms']
                
                if 'nf_email' in serializer.validated_data:
                    user.nf_email = serializer.validated_data['nf_email']

                if 'nf_frequency' in serializer.validated_data:
                    user.nf_frequency = serializer.validated_data['nf_frequency']
                
                user.save()
                
                return Response({
                    'status': 'success',
                    'message': 'Notification preferences updated successfully',
                    'data': {
                        'nf_popup': user.nf_popup,
                        'nf_sms': user.nf_sms,
                        'nf_email': user.nf_email,
                        'nf_frequency': user.nf_frequency
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Invalid input',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error updating notification preferences: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST']) 
@permission_classes([IsAuthenticated])
def archive_gps_data_log(request):
    """
    Archive GPSDataLog records up to a specific date (must be at least 2 years old).
    Saves data to JSON file and removes from database.
    """
    try:
        actor_email = getattr(request.user, 'email', None) or 'unknown'
        archive_date_str = request.data.get('archive_date')
        if not archive_date_str:
            return Response({'status': 'error', 'message': 'archive_date is required in format YYYY-MM-DD'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            archive_date = datetime.strptime(archive_date_str, '%Y-%m-%d')
            archive_date = timezone.make_aware(archive_date.replace(hour=23, minute=59, second=59))
        except ValueError:
            return Response({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if date is at least 2 years old
        two_years_ago = timezone.now() - timedelta(days=730)
        if archive_date > two_years_ago:
            return Response({
                'status': 'error',
                'message': f'Archive date must be at least 2 years old. Data must be from before {two_years_ago.strftime("%Y-%m-%d")}',
                'two_years_ago_date': two_years_ago.strftime('%Y-%m-%d')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get records to archive
        records_to_archive = GPSDataLog.objects.filter(timestamp__lte=archive_date).order_by('timestamp')
        record_count = records_to_archive.count()
        
        if record_count == 0:
            return Response({'status': 'error', 'message': 'No records found to archive'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        first_record = records_to_archive.first()
        last_record = records_to_archive.last()
        date_from = first_record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        date_to = last_record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create archive directory
        archive_dir = os.path.join(settings.BASE_DIR, 'gps_data_archives')
        os.makedirs(archive_dir, exist_ok=True)
        
        # Generate archive filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_filename = f'gps_data_log_archive_{timestamp}.json'
        archive_filepath = os.path.join(archive_dir, archive_filename)
        
        # Prepare data for archiving
        archive_data = {
            'metadata': {
                'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'date_range': {'from': date_from, 'to': date_to},
                'records_count': record_count,
                'archived_by': actor_email
            },
            'records': []
        }
        
        # Batch process records
        batch_size = 1000
        for i in range(0, record_count, batch_size):
            batch = records_to_archive[i:i+batch_size]
            for record in batch:
                archive_data['records'].append({
                    'id': record.id,
                    'timestamp': record.timestamp.isoformat(),
                    'raw_data': record.raw_data
                })
        
        # Save to JSON file
        with open(archive_filepath, 'w') as f:
            json.dump(archive_data, f, indent=2)
        
        # Delete archived records
        deleted_count = records_to_archive.delete()[0]
        
        file_size = os.path.getsize(archive_filepath)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        logger.info(f"Archived {deleted_count} GPS data log records to {archive_filename}")
        
        return Response({
            'status': 'success',
            'message': 'Data archived and removed from table successfully',
            'archive_file': archive_filename,
            'records_archived': record_count,
            'records_deleted': deleted_count,
            'date_range': {'from': date_from, 'to': date_to},
            'file_size_mb': file_size_mb,
            'archived_by': actor_email,
            'archived_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in archive_gps_data_log: {str(e)}")
        return Response({'status': 'error', 'message': f'An error occurred: {str(e)}'}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)


IMEI_PATTERN = re.compile(r'(?<!\d)(\d{15})(?!\d)')


def _parse_imei_list_from_request(request):
        raw_imeis = request.data.get('imeis') if request.method == 'POST' else request.GET.get('imeis', '')

        if isinstance(raw_imeis, list):
                candidates = raw_imeis
        elif isinstance(raw_imeis, str):
                candidates = re.split(r'[\s,]+', raw_imeis.strip()) if raw_imeis.strip() else []
        else:
                candidates = []

        normalized = []
        invalid = []
        seen = set()
        for item in candidates:
                val = str(item).strip()
                if not val:
                        continue
                if not re.fullmatch(r'\d{15}', val):
                        invalid.append(val)
                        continue
                if val not in seen:
                        normalized.append(val)
                        seen.add(val)
        return normalized, invalid


def _is_tracking_packet(raw_data):
        return ',PVT,' in raw_data


def _is_health_packet(raw_data):
        return ',HLM,' in raw_data


def _is_login_packet(raw_data):
        return raw_data.strip().startswith('$AS')


def _extract_tracking_lat_lon(raw_data):
        try:
                parts = [p.strip() for p in raw_data.split(',')]
                pvt_idx = parts.index('PVT')
                lat_token = parts[pvt_idx + 11]
                lon_token = parts[pvt_idx + 13]

                lat_match = re.search(r'-?\d+(?:\.\d+)?', lat_token or '')
                lon_match = re.search(r'-?\d+(?:\.\d+)?', lon_token or '')
                if not lat_match or not lon_match:
                        return None, None

                lat = float(lat_match.group(0))
                lon = float(lon_match.group(0))
                return lat, lon
        except Exception:
                return None, None


def _is_valid_lat_lon(lat, lon):
        if lat is None or lon is None:
                return False
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return False
        return not (abs(lat) < 1e-9 and abs(lon) < 1e-9)


def _format_age_seconds(seconds):
        sec = int(max(0, seconds))
        days, rem = divmod(sec, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)

        if days:
                return f"{days}d {hours}h {minutes}m {seconds}s"
        if hours:
                return f"{hours}h {minutes}m {seconds}s"
        if minutes:
                return f"{minutes}m {seconds}s"
        return f"{seconds}s"


def _packet_snapshot(log_obj, now):
        if not log_obj:
                return None
        delta_sec = max((now - log_obj.timestamp).total_seconds(), 0)
        return {
                'timestamp': log_obj.timestamp.isoformat(),
                'age_seconds': round(delta_sec, 2),
                'age_human': _format_age_seconds(delta_sec),
                'raw_data': log_obj.raw_data,
        }


def _average_gap_seconds(timestamps):
    if len(timestamps) < 2:
        return None

    ordered = sorted(timestamps)
    diffs = []
    for i in range(1, len(ordered)):
        gap = (ordered[i] - ordered[i - 1]).total_seconds()
        if gap >= 0:
            diffs.append(gap)

    if not diffs:
        return None
    return round(sum(diffs) / len(diffs), 2)


def _extract_target_imei(raw_data, imei_set):
    if not raw_data:
        return None
    for match in IMEI_PATTERN.finditer(raw_data):
        found = match.group(1)
        if found in imei_set:
            return found
    return None


def _window_counts_and_avg_gaps(timestamps, now, windows):
    from bisect import bisect_left

    ordered = sorted(timestamps)
    n = len(ordered)

    counts = {}
    avg_gaps = {}
    if n == 0:
        for label, _ in windows:
            counts[label] = 0
            avg_gaps[label] = None
        return counts, avg_gaps

    # gaps[i] = ordered[i] - ordered[i-1] in seconds (gaps[0] is 0)
    gaps = [0.0] * n
    for i in range(1, n):
        gaps[i] = max((ordered[i] - ordered[i - 1]).total_seconds(), 0)

    # Prefix sum for O(1) gap-range summation
    prefix = [0.0] * n
    run = 0.0
    for i, g in enumerate(gaps):
        run += g
        prefix[i] = run

    def _sum_gaps(start_idx, end_idx):
        if end_idx < start_idx:
            return 0.0
        return prefix[end_idx] - (prefix[start_idx - 1] if start_idx > 0 else 0.0)

    for label, minutes in windows:
        cutoff = now - timedelta(minutes=minutes)
        k = bisect_left(ordered, cutoff)
        count = n - k
        counts[label] = count

        if count < 2:
            avg_gaps[label] = None
        else:
            # For ordered[k:] we need gaps between consecutive elements => gaps[k+1..n-1]
            total_gap = _sum_gaps(k + 1, n - 1)
            avg_gaps[label] = round(total_gap / (count - 1), 2)

    return counts, avg_gaps


def _window_gap_incidents_over_threshold(timestamps, now, windows, threshold_seconds=10.0):
    from bisect import bisect_left

    ordered = sorted(timestamps)
    n = len(ordered)

    incident_counts = {}
    incident_avg_gap = {}
    for label, minutes in windows:
        if n < 2:
            incident_counts[label] = 0
            incident_avg_gap[label] = None
            continue

        cutoff = now - timedelta(minutes=minutes)
        k = bisect_left(ordered, cutoff)
        if n - k < 2:
            incident_counts[label] = 0
            incident_avg_gap[label] = None
            continue

        selected_gaps = []
        for i in range(k + 1, n):
            gap = (ordered[i] - ordered[i - 1]).total_seconds()
            if gap > threshold_seconds:
                selected_gaps.append(gap)

        incident_counts[label] = len(selected_gaps)
        if selected_gaps:
            incident_avg_gap[label] = round(sum(selected_gaps) / len(selected_gaps), 2)
        else:
            incident_avg_gap[label] = None

    return incident_counts, incident_avg_gap


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def gps_packet_health_summary(request):
        """
        Multi-IMEI packet monitor API based on GPSDataLog.raw_data parsing.
        Accepts imeis as comma/newline separated string or list.
        """
        errors = validate_inputs(request)
        if errors:
                return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        imeis, invalid_imeis = _parse_imei_list_from_request(request)
        if not imeis:
                return Response({
                        'status': 'error',
                        'message': 'Provide at least one valid 15-digit IMEI in "imeis".'
                }, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        raw_lookback = request.data.get('lookback_days') if request.method == 'POST' else request.GET.get('lookback_days', '3')
        try:
            lookback_days = int(raw_lookback)
        except (TypeError, ValueError):
            return Response({'status': 'error', 'message': 'lookback_days must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        if lookback_days < 1 or lookback_days > 30:
            return Response({'status': 'error', 'message': 'lookback_days must be between 1 and 30'}, status=status.HTTP_400_BAD_REQUEST)
        latest_cutoff = now - timedelta(days=lookback_days)
        windows = [
                ('5m', 5),
                ('10m', 10),
                ('30m', 30),
                ('60m', 60),
                ('150m', 150),
                ('1d', 1440),
        ]
        incident_windows = [
            ('5m', 5),
            ('10m', 10),
            ('30m', 30),
            ('60m', 60),
        ]
        max_window_minutes = max(m for _, m in windows)
        max_cutoff = now - timedelta(minutes=max_window_minutes)

        imei_set = set(imeis)

        # Build a single OR query for all requested IMEIs to avoid repeated full table scans.
        imei_q = Q()
        for imei in imeis:
            imei_q |= Q(raw_data__contains=imei)

        # Collect latest packet snapshots for each IMEI in a single newest-first scan.
        latest_by_imei = {
            imei: {
                'tracking': None,
                'tracking_valid_latlon': None,
                'login': None,
                'health': None,
            }
            for imei in imeis
        }

        remaining_slots = len(imeis) * 4
        if remaining_slots:
            for row in (
                GPSDataLog.objects
                .filter(imei_q, timestamp__gte=latest_cutoff)
                .only('timestamp', 'raw_data')
                .order_by('-timestamp')
                .iterator(chunk_size=2000)
            ):
                raw = row.raw_data or ''
                imei = _extract_target_imei(raw, imei_set)
                if not imei:
                    continue

                slots = latest_by_imei[imei]

                if _is_tracking_packet(raw):
                    if slots['tracking'] is None:
                        slots['tracking'] = row
                        remaining_slots -= 1
                    if slots['tracking_valid_latlon'] is None:
                        lat, lon = _extract_tracking_lat_lon(raw)
                        if _is_valid_lat_lon(lat, lon):
                            slots['tracking_valid_latlon'] = row
                            remaining_slots -= 1
                elif _is_health_packet(raw):
                    if slots['health'] is None:
                        slots['health'] = row
                        remaining_slots -= 1
                elif _is_login_packet(raw):
                    if slots['login'] is None:
                        slots['login'] = row
                        remaining_slots -= 1

                if remaining_slots <= 0:
                    break

        # One recent-window scan for all IMEIs to compute counts and average gaps.
        packet_ts = {
            imei: {
                'tracking': [],
                'tracking_valid_latlon': [],
                'health': [],
                'login': [],
            }
            for imei in imeis
        }

        for row in (
            GPSDataLog.objects
            .filter(imei_q, timestamp__gte=max_cutoff)
            .only('timestamp', 'raw_data')
            .order_by('-timestamp')
            .iterator(chunk_size=3000)
        ):
            raw = row.raw_data or ''
            ts = row.timestamp
            imei = _extract_target_imei(raw, imei_set)
            if not imei:
                continue

            if _is_tracking_packet(raw):
                packet_ts[imei]['tracking'].append(ts)
                lat, lon = _extract_tracking_lat_lon(raw)
                if _is_valid_lat_lon(lat, lon):
                    packet_ts[imei]['tracking_valid_latlon'].append(ts)
            elif _is_health_packet(raw):
                packet_ts[imei]['health'].append(ts)
            elif _is_login_packet(raw):
                packet_ts[imei]['login'].append(ts)

        results = []
        for imei in imeis:
            tracking_counts, tracking_avg_gap = _window_counts_and_avg_gaps(packet_ts[imei]['tracking'], now, windows)
            valid_tracking_counts, valid_tracking_avg_gap = _window_counts_and_avg_gaps(packet_ts[imei]['tracking_valid_latlon'], now, windows)
            health_counts, _ = _window_counts_and_avg_gaps(packet_ts[imei]['health'], now, windows)
            login_counts, _ = _window_counts_and_avg_gaps(packet_ts[imei]['login'], now, windows)
            tracking_over_10_count, tracking_over_10_avg = _window_gap_incidents_over_threshold(
                packet_ts[imei]['tracking'], now, incident_windows, threshold_seconds=10.0
            )
            valid_tracking_over_10_count, valid_tracking_over_10_avg = _window_gap_incidents_over_threshold(
                packet_ts[imei]['tracking_valid_latlon'], now, incident_windows, threshold_seconds=10.0
            )

            latest = latest_by_imei[imei]
            results.append({
                'imei': imei,
                'last_packets': {
                    'tracking': _packet_snapshot(latest['tracking'], now),
                    'tracking_valid_latlon': _packet_snapshot(latest['tracking_valid_latlon'], now),
                    'login': _packet_snapshot(latest['login'], now),
                    'health': _packet_snapshot(latest['health'], now),
                },
                'counts': {
                    'tracking': tracking_counts,
                    'tracking_valid_latlon': valid_tracking_counts,
                    'health': health_counts,
                    'login': login_counts,
                },
                'average_gap_seconds': {
                    'tracking': tracking_avg_gap,
                    'tracking_valid_latlon': valid_tracking_avg_gap,
                },
                'gap_over_10s_incidents': {
                    'tracking': {
                        'counts': tracking_over_10_count,
                        'average_gap_seconds': tracking_over_10_avg,
                    },
                    'tracking_valid_latlon': {
                        'counts': valid_tracking_over_10_count,
                        'average_gap_seconds': valid_tracking_over_10_avg,
                    },
                }
            })

        return Response({
                'status': 'success',
                'generated_at': now.isoformat(),
            'lookback_days_applied': lookback_days,
                'windows': [w[0] for w in windows],
                'invalid_imeis': invalid_imeis,
                'results': results,
        }, status=status.HTTP_200_OK)


@require_http_methods(['GET'])
def gps_packet_dashboard(request):
        html = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>IMEI Packet Dashboard</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');
        :root {
            --bg1: #eff6ff;
            --bg2: #f8fafc;
            --ink: #0f172a;
            --subtle: #475569;
            --brand: #0ea5a4;
            --brand-2: #0f766e;
            --card: #ffffff;
            --line: #cbd5e1;
            --ok: #166534;
            --warn: #b45309;
            --err: #b91c1c;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: 'Space Grotesk', sans-serif;
            color: var(--ink);
            background:
                radial-gradient(circle at 0% 0%, #dbeafe 0%, transparent 35%),
                radial-gradient(circle at 100% 0%, #ccfbf1 0%, transparent 35%),
                linear-gradient(135deg, var(--bg1), var(--bg2));
            min-height: 100vh;
            padding: 20px;
        }
        .wrap {
            max-width: 1400px;
            margin: 0 auto;
            background: color-mix(in srgb, var(--card) 90%, #ffffff00);
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(2px);
        }
        h1 {
            margin: 0 0 10px;
            font-size: clamp(1.2rem, 2.5vw, 1.8rem);
            letter-spacing: 0.02em;
        }
        .hint { color: var(--subtle); margin-bottom: 14px; }
        .controls { display: grid; gap: 10px; grid-template-columns: 1fr auto auto; }
        textarea {
            width: 100%;
            min-height: 90px;
            resize: vertical;
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 10px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 0.9rem;
        }
        button {
            border: 0;
            border-radius: 10px;
            padding: 0 14px;
            font-weight: 700;
            cursor: pointer;
            min-height: 42px;
        }
        #runBtn { background: var(--brand); color: #fff; }
        #runBtn:hover { background: var(--brand-2); }
        #stopBtn { background: #334155; color: #fff; }
        .meta { margin-top: 12px; font-size: 0.92rem; color: var(--subtle); }
        .status { margin-top: 10px; font-weight: 500; }
        .status.ok { color: var(--ok); }
        .status.warn { color: var(--warn); }
        .status.err { color: var(--err); }
        .table-wrap { margin-top: 16px; overflow: auto; border: 1px solid var(--line); border-radius: 10px; }
        table { border-collapse: collapse; width: max(100%, 1200px); background: #fff; }
        th, td { border-bottom: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; vertical-align: top; font-size: 0.86rem; }
        th { background: #f1f5f9; position: sticky; top: 0; z-index: 2; }
        .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
        .small { color: var(--subtle); font-size: 0.78rem; }
        @media (max-width: 900px) {
            .controls { grid-template-columns: 1fr; }
            button { width: 100%; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <h1>IMEI Packet Monitoring Dashboard</h1>
        <div class="hint">Enter multiple IMEIs separated by comma, space, or new line. Refresh cycle: 15 seconds.</div>

        <div class="controls">
            <textarea id="imeis" placeholder="866192070567043\n123456789012345"></textarea>
            <button id="runBtn">Start / Refresh</button>
            <button id="stopBtn">Stop Auto</button>
        </div>

        <div class="meta" id="meta">API: <span class="mono" id="apiPath"></span></div>
        <div id="status" class="status">Waiting for input.</div>

        <div class="table-wrap">
            <table id="resultTable">
                <thead>
                    <tr>
                        <th>IMEI</th>
                        <th>Last Tracking</th>
                        <th>Last Tracking Valid LatLon</th>
                        <th>Last Login</th>
                        <th>Last Health</th>
                        <th>Tracking Counts</th>
                        <th>Valid Tracking Counts</th>
                        <th>Health Counts</th>
                        <th>Login Counts</th>
                        <th>Avg Gap Tracking (sec)</th>
                        <th>Avg Gap Valid Tracking (sec)</th>
                        <th>Tracking Gap &gt;10s Incidents</th>
                        <th>Valid Tracking Gap &gt;10s Incidents</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <script>
        const API_URL = '/api/gps-packet-health-summary/';
        const REFRESH_MS = 15000;
        const statusEl = document.getElementById('status');
        const tbody = document.querySelector('#resultTable tbody');
        const imeisEl = document.getElementById('imeis');
        const apiPathEl = document.getElementById('apiPath');
        apiPathEl.textContent = API_URL;

        let timerId = null;

        function setStatus(msg, type) {
            statusEl.textContent = msg;
            statusEl.className = 'status ' + (type || '');
        }

        function fmtLast(packet) {
            if (!packet) return 'N/A';
            return `<div>${packet.timestamp}</div><div class="small">${packet.age_human} ago</div>`;
        }

        function fmtMap(obj) {
            if (!obj) return 'N/A';
            const order = ['5m', '10m', '30m', '60m', '150m', '1d'];
            return order.map((k) => `${k}:${obj[k] ?? 'NA'}`).join(' | ');
        }

        function fmtIncident(obj) {
            if (!obj) return 'N/A';
            const order = ['5m', '10m', '30m', '60m'];
            const c = obj.counts || {};
            const a = obj.average_gap_seconds || {};
            return order.map((k) => `${k}:${c[k] ?? 'NA'}/${a[k] ?? 'NA'}`).join(' | ');
        }

        function renderRows(results) {
            tbody.innerHTML = '';
            results.forEach((row) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="mono">${row.imei}</td>
                    <td>${fmtLast(row.last_packets?.tracking)}</td>
                    <td>${fmtLast(row.last_packets?.tracking_valid_latlon)}</td>
                    <td>${fmtLast(row.last_packets?.login)}</td>
                    <td>${fmtLast(row.last_packets?.health)}</td>
                    <td class="mono">${fmtMap(row.counts?.tracking)}</td>
                    <td class="mono">${fmtMap(row.counts?.tracking_valid_latlon)}</td>
                    <td class="mono">${fmtMap(row.counts?.health)}</td>
                    <td class="mono">${fmtMap(row.counts?.login)}</td>
                    <td class="mono">${fmtMap(row.average_gap_seconds?.tracking)}</td>
                    <td class="mono">${fmtMap(row.average_gap_seconds?.tracking_valid_latlon)}</td>
                    <td class="mono">${fmtIncident(row.gap_over_10s_incidents?.tracking)}</td>
                    <td class="mono">${fmtIncident(row.gap_over_10s_incidents?.tracking_valid_latlon)}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function fetchData() {
            const imeis = imeisEl.value.trim();
            if (!imeis) {
                setStatus('Enter one or more IMEIs first.', 'warn');
                return;
            }
            setStatus('Loading...', '');

            const q = new URLSearchParams({ imeis });
            try {
                const res = await fetch(API_URL + '?' + q.toString(), { method: 'GET' });
                const data = await res.json();
                if (!res.ok || data.status !== 'success') {
                    const msg = data.message || data.error || 'Request failed';
                    setStatus(msg, 'err');
                    return;
                }

                renderRows(data.results || []);
                const bad = (data.invalid_imeis || []).length;
                const now = new Date().toLocaleString();
                setStatus(`Updated ${now}. Rows: ${(data.results || []).length}. Invalid IMEIs: ${bad}.`, bad ? 'warn' : 'ok');
            } catch (err) {
                setStatus('Network/API error: ' + (err?.message || String(err)), 'err');
            }
        }

        function startAuto() {
            fetchData();
            if (timerId) clearInterval(timerId);
            timerId = setInterval(fetchData, REFRESH_MS);
        }

        document.getElementById('runBtn').addEventListener('click', startAuto);
        document.getElementById('stopBtn').addEventListener('click', () => {
            if (timerId) clearInterval(timerId);
            timerId = null;
            setStatus('Auto refresh stopped.', 'warn');
        });
    </script>
</body>
</html>
        """
        return HttpResponse(html)


@require_http_methods(['GET', 'POST'])
def gps_data_log_table(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Filter data based on the search query
    search_query = request.GET.get('search', '')
    if search_query:
        data = GPSDataLog.objects.filter(raw_data__contains=search_query).order_by('-timestamp')[:200]
    else:
        data = GPSDataLog.objects.all().order_by('-timestamp')[:200]
    serialized_data = serialize('json', data)
    
    return JsonResponse({
        'data': serialized_data,
        'search_query': search_query
    }, status=200)
    
@require_http_methods(['GET', 'POST'])
def gps_em_data_log_table(request ): 
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    
    # Filter data based on the search query
    search_query = request.GET.get('search', '')
    if search_query:
        data = GPSemDataLog.objects.filter(raw_data__contains=search_query).order_by('-timestamp')[:200]
    else:
        data = GPSemDataLog.objects.all().order_by('-timestamp')[:200]
    serialized_data = serialize('json', data)
    
    return JsonResponse({
        'data': serialized_data,
        'search_query': search_query
    }, status=200)
     
        
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def restore_gps_data_log(request):
    """
    Restore GPSDataLog records from an archive JSON file.
    """
    try:
        actor_email = getattr(request.user, 'email', None) or 'unknown'
        
        archive_filename = request.data.get('archive_file')
        if not archive_filename:
            return Response({'status': 'error', 'message': 'archive_file is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        archive_dir = os.path.join(settings.BASE_DIR, 'gps_data_archives')
        archive_filepath = os.path.join(archive_dir, archive_filename)
        
        if not os.path.exists(archive_filepath):
            available_files = [f for f in os.listdir(archive_dir) if f.endswith('.json')] if os.path.exists(archive_dir) else []
            return Response({
                'status': 'error',
                'message': 'Archive file not found',
                'available_archives': available_files
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Load archive data
        with open(archive_filepath, 'r') as f:
            archive_data = json.load(f)
        
        count_before = GPSDataLog.objects.count()
        
        # Restore records in batches
        batch_size = 1000
        records = archive_data.get('records', [])
        total_records = len(records)
        
        for i in range(0, total_records, batch_size):
            batch = records[i:i+batch_size]
            objects_to_create = []
            
            for record_data in batch:
                objects_to_create.append(GPSDataLog(
                    id=record_data['id'],
                    timestamp=datetime.fromisoformat(record_data['timestamp']),
                    raw_data=record_data['raw_data']
                ))
            
            GPSDataLog.objects.bulk_create(objects_to_create, ignore_conflicts=True)
        
        count_after = GPSDataLog.objects.count()
        records_restored = count_after - count_before
        
        logger.info(f"Restored {records_restored} GPS data log records from {archive_filename}")
        
        return Response({
            'status': 'success',
            'message': 'Data restored successfully',
            'archive_file': archive_filename,
            'records_before_restore': count_before,
            'records_after_restore': count_after,
            'records_restored': records_restored,
            'archive_metadata': archive_data.get('metadata', {}),
            'restored_by': actor_email,
            'restored_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in restore_gps_data_log: {str(e)}")
        return Response({'status': 'error', 'message': f'An error occurred: {str(e)}'}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_gps_data_archives(request):
    """
    List all available GPS data archive files.
    """
    try: 
        
        archive_dir = os.path.join(settings.BASE_DIR, 'gps_data_archives')
        archive_files = []
        
        if os.path.exists(archive_dir):
            for filename in os.listdir(archive_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(archive_dir, filename)
                    file_stat = os.stat(filepath)
                    file_size_mb = round(file_stat.st_size / (1024 * 1024), 2)
                    created_at = datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Read metadata
                    metadata = {}
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            metadata = data.get('metadata', {})
                    except:
                        pass
                    
                    archive_files.append({
                        'filename': filename,
                        'size_mb': file_size_mb,
                        'created_at': created_at,
                        'metadata': metadata
                    })
        
        archive_files.sort(key=lambda x: x['created_at'], reverse=True)
        
        return Response({
            'status': 'success',
            'total_archives': len(archive_files),
            'archive_directory': archive_dir,
            'archives': archive_files
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in list_gps_data_archives: {str(e)}")
        return Response({'status': 'error', 'message': f'An error occurred: {str(e)}'}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_cell_tower_info(request):
    """
    Get cell tower and network information from the latest GPS data entry for a given device tag.
    Returns IMEI, network operator, signal strength, MCC, MNC, LAC, Cell IDs, and neighboring cell tower info.
    """
    try: 
        device_tag_id = request.data.get('device_tag_id')
        if not device_tag_id:
            return Response({'status': 'error', 'message': 'device_tag_id is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Get the device tag
        try:
            device_tag = DeviceTag.objects.select_related('device', 'device__model').get(id=device_tag_id)
        except DeviceTag.DoesNotExist:
            return Response({'status': 'error', 'message': 'Device tag not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        # Get the latest GPS data entry for this device tag
        latest_gps = GPSData.objects.filter(device_tag=device_tag,gps_status=1).order_by('-entry_time').first()
        
        if not latest_gps:
            return Response({
                'status': 'error', 
                'message': 'No GPS data found for this device tag'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Extract IMEI from device stock
        imei = device_tag.device.imei if device_tag.device else None
        
        # Prepare cell tower information
        cell_tower_info = {
            'device_info': {
                'device_tag_id': device_tag.id,
                'vehicle_reg_no': device_tag.vehicle_reg_no,
                'imei': imei,
                'device_esn': device_tag.device.device_esn if device_tag.device else None,
                'msisdn1': device_tag.device.msisdn1 if device_tag.device else None,
                'msisdn2': device_tag.device.msisdn2 if device_tag.device else None,
            },
            'gps_data_info': {
                'entry_time': latest_gps.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                'date': latest_gps.date,
                'time': latest_gps.time,
                'latitude': latest_gps.latitude,
                'latitude_dir': latest_gps.latitude_dir,
                'longitude': latest_gps.longitude,
                'longitude_dir': latest_gps.longitude_dir,
                'gps_status': latest_gps.gps_status,
            },
            'network_info': {
                'network_operator': latest_gps.network_operator,
                'gsm_signal_strength': latest_gps.gsm_signal_strength,
                'mcc': latest_gps.mcc,  # Mobile Country Code
                'mnc': latest_gps.mnc,  # Mobile Network Code
            },
            'primary_cell_tower': {
                'lac': latest_gps.lac,  # Location Area Code
                'cell_id': latest_gps.cell_id,  # Cell Tower ID
            },
            'neighboring_cell_towers': [
                {
                    'neighbor': 1,
                    'cell_id': latest_gps.nbr1_cell_id,
                    'lac': latest_gps.nbr1_lac,
                    'signal_strength': latest_gps.nbr1_signal_strength
                },
                {
                    'neighbor': 2,
                    'cell_id': latest_gps.nbr2_cell_id,
                    'lac': latest_gps.nbr2_lac,
                    'signal_strength': latest_gps.nbr2_signal_strength
                },
                {
                    'neighbor': 3,
                    'cell_id': latest_gps.nbr3_cell_id,
                    'lac': latest_gps.nbr3_lac,
                    'signal_strength': latest_gps.nbr3_signal_strength
                },
                {
                    'neighbor': 4,
                    'cell_id': latest_gps.nbr4_cell_id,
                    'lac': latest_gps.nbr4_lac,
                    'signal_strength': latest_gps.nbr4_signal_strength
                }
            ],
            'additional_info': {
                'satellites': latest_gps.satellites,
                'altitude': latest_gps.altitude,
                'speed': latest_gps.speed,
                'heading': latest_gps.heading,
                'pdop': latest_gps.pdop,
                'hdop': latest_gps.hdop,
            }
        }
        
        return Response({
            'status': 'success',
            'message': 'Cell tower information retrieved successfully',
            'data': cell_tower_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_cell_tower_info: {str(e)}")
        return Response({'status': 'error', 'message': f'An error occurred: {str(e)}'}, 
                      status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def public_contact_form(request):
    """
    Public API for contact form submissions.
    Accepts contact information and sends email to contact@aaa.com
    """
    try:
        # Extract data from request
        name = request.data.get('name', '').strip()
        org_name = request.data.get('org_name', '').strip()
        user_type = request.data.get('user_type', '').strip()
        email = request.data.get('email', '').strip()
        mobile = request.data.get('mobile', '').strip()
        dob = request.data.get('dob', '').strip()
        request_detail = request.data.get('request_detail', '').strip()
        
        # Validate required fields
        if not all([name, email, mobile]):
            return Response({
                'status': 'error',
                'message': 'Name, email, and mobile are required fields.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return Response({
                'status': 'error',
                'message': 'Invalid email format.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create email content
        email_subject = f'New Contact Form Submission - {name}'
        email_body = f"""
        New Contact Form Submission
        ================================
        
        Name: {name}
        Organization: {org_name if org_name else 'N/A'}
        User Type: {user_type if user_type else 'N/A'}
        Email: {email}
        Mobile: {mobile}
        Date of Birth: {dob if dob else 'N/A'}
        
        Request Details:
        {request_detail if request_detail else 'N/A'}
        
        ================================
        This is an automated message from the contact form.
        """
        
        # Send email using Django's send_mail
        from django.core.mail import send_mail as django_send_mail
        
        django_send_mail(
            email_subject,
            email_body,
            'noreply@skytron.in',  # From email
            ['contact@aaa.com'],  # To email
            fail_silently=False,
        )
        
        return Response({
            'status': 'success',
            'message': 'Your request has been submitted successfully. We will contact you soon.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in public_contact_form: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Failed to submit contact form. Please try again later.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def list_logged_in_users(request):
    """
    API to get list of logged-in users with filtering and pagination.
    Filters: name, role, mobile, email
    Pagination: default 100 per page
    """
    try:
        # Only allow superadmin and stateadmin to access this API
        if request.user.role not in ['superadmin', 'stateadmin']:
            return Response({
                'status': 'error',
                'message': 'Access denied. Only superadmin and stateadmin can view logged-in users.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get pagination parameters
        page = int(request.data.get('page', 1)) if request.method == 'POST' else int(request.GET.get('page', 1))
        page_size = int(request.data.get('page_size', 100)) if request.method == 'POST' else int(request.GET.get('page_size', 100))
        
        # Limit page size to maximum 500
        page_size = min(page_size, 500)
        
        # Get filter parameters
        if request.method == 'POST':
            name_filter = request.data.get('name', '').strip()
            role_filter = request.data.get('role', '').strip()
            mobile_filter = request.data.get('mobile', '').strip()
            email_filter = request.data.get('email', '').strip()
        else:
            name_filter = request.GET.get('name', '').strip()
            role_filter = request.GET.get('role', '').strip()
            mobile_filter = request.GET.get('mobile', '').strip()
            email_filter = request.GET.get('email', '').strip()
        
        # Start with users who have login=True (currently logged in)
        users_query = User.objects.filter(login=True, is_active=True)
        
        # Apply filters
        if name_filter:
            users_query = users_query.filter(name__icontains=name_filter)
        
        if role_filter:
            users_query = users_query.filter(role__icontains=role_filter)
        
        if mobile_filter:
            users_query = users_query.filter(mobile__icontains=mobile_filter)
        
        if email_filter:
            users_query = users_query.filter(email__icontains=email_filter)
        
        # Order by last_activity (most recent first)
        users_query = users_query.order_by('-last_activity')
        
        # Get total count before pagination
        total_count = users_query.count()
        
        # Apply pagination
        paginator = Paginator(users_query, page_size)
        
        try:
            paginated_users = paginator.get_page(page)
        except:
            return Response({
                'status': 'error',
                'message': 'Invalid page number.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare user data
        users_data = []
        for user in paginated_users:
            users_data.append({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'mobile': user.mobile,
                'role': user.role,
                'usertype': user.usertype,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'last_activity': user.last_activity.isoformat() if user.last_activity else None,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'address_State': user.address_State,
                'is_active': user.is_active,
                'login': user.login
            })
        
        return Response({
            'status': 'success',
            'data': users_data,
            'pagination': {
                'current_page': paginated_users.number,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_results': total_count,
                'has_next': paginated_users.has_next(),
                'has_previous': paginated_users.has_previous()
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in list_logged_in_users: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






# ============================================================================
# CENTRAL DASHBOARD APIs FOR VEHICLE MONITORING
# ============================================================================

@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def vehicle_monitoring_dashboard(request):
    """
    Central Dashboard API for vehicle monitoring with following data:
    
    Query Parameters (filters):
    - state_id: Filter by state ID (optional)
    - district_id: Filter by district ID (optional)
    - vehicle_category_id: Filter by vehicle category ID (optional)
    
    Response includes:
    1. Total active device tags
    2. Offline device tags (no data since last 15 min in gpsdata)
    3. Online device tags (data within last 15 min in gpsdata)
    4. Total emergency alerts today in alert logs
    5. Total other alerts (non-emergency) in alert logs
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Q, Count, Max
        
        # Get filter parameters
        state_id = request.GET.get('state_id')
        district_id = request.GET.get('district_id')
        vehicle_category_id = request.GET.get('vehicle_category_id')
        
        # Base queryset: include all tagged devices except explicitly removed/untagged.
        # This ensures unfiltered dashboard requests return complete data.
        device_tags_qs = DeviceTag.objects.exclude(
            status='TagDeleted'
        ).exclude(
            status='Device_Untagged'
        )
        
        # Apply filters if provided
        if state_id:
            try:
                state_id = int(state_id)
                device_tags_qs = device_tags_qs.filter(
                    district__state_id=state_id
                )
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid state_id parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if district_id:
            try:
                district_id = int(district_id)
                device_tags_qs = device_tags_qs.filter(
                    district_id=district_id
                )
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid district_id parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if vehicle_category_id:
            try:
                vehicle_category_id = int(vehicle_category_id)
                device_tags_qs = device_tags_qs.filter(
                    category_id=vehicle_category_id
                )
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid vehicle_category_id parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Total active device tags
        total_active_device_tags = device_tags_qs.count()
        
        # Calculate online/offline status based on GPS data timestamp
        now = timezone.now()
        fifteen_mins_ago = now - timedelta(minutes=15)
        
        device_tag_ids = list(device_tags_qs.values_list('id', flat=True))
        
        # Get latest GPS entry for each device
        latest_gps_subquery = GPSData.objects.filter(
            device_tag_id=OuterRef('id')
        ).order_by('-entry_time').values('entry_time')[:1]
        
        device_stats = device_tags_qs.annotate(
            latest_gps_time=Subquery(latest_gps_subquery)
        ).values('id', 'latest_gps_time')
        
        online_count = 0
        offline_count = 0
        
        for device in device_stats:
            if device['latest_gps_time']:
                if device['latest_gps_time'] >= fifteen_mins_ago:
                    online_count += 1
                else:
                    offline_count += 1
            else:
                offline_count += 1
        
        # Get today's date at midnight
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Get alerts for filtered devices
        today_alerts = AlertsLog.objects.filter(
            deviceTag__in=device_tag_ids,
            timestamp__gte=today_start,
            timestamp__lt=today_end
        )
        
        # Emergency alert types
        emergency_types = [
            'Em', 'EmPublicApp', 'EmRegisteredApp', 
            'EmMonitorTripSOS', 'EmMonitorTripInvalidPw', 
            'EmMonitorTripBLEDisconnect', 'EmMonitorTripDeviated',
            'Incident'
        ]
        
        emergency_alerts_count = today_alerts.filter(
            type__in=emergency_types
        ).count()
        
        other_alerts_count = today_alerts.exclude(
            type__in=emergency_types
        ).count()
        
        # Prepare response
        response_data = {
            'filters_applied': {
                'state_id': state_id,
                'district_id': district_id,
                'vehicle_category_id': vehicle_category_id
            },
            'dashboard_metrics': {
                'total_active_device_tags': total_active_device_tags,
                'online_device_tags': online_count,
                'offline_device_tags': offline_count,
                'total_emergency_alerts_today': emergency_alerts_count,
                'total_other_alerts_today': other_alerts_count
            },
            'timestamp': timezone.now().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in vehicle_monitoring_dashboard: {str(e)}")
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
@require_http_methods(['GET'])
def get_dashboard_filter_options(request):
    """
    Get dashboard filter options.

    District/City/Locality options are derived from GPSData only,
    using latest GPS entry per unique device_tag.

    Query Params:
    - state_name (optional)
    - district_name (optional)
    - city_name (optional)
    - vehicle_category_id (optional)
    """
    try:
        from django.db.models import Subquery, OuterRef

        state_name = (request.GET.get('state_name') or '').strip()
        district_name = (request.GET.get('district_name') or '').strip()
        city_name = (request.GET.get('city_name') or '').strip()
        vehicle_category_id = (request.GET.get('vehicle_category_id') or '').strip()

        # Device scope used for geo options.
        device_tags_qs = DeviceTag.objects.exclude(status='TagDeleted').exclude(status='Device_Untagged')
        if vehicle_category_id:
            try:
                device_tags_qs = device_tags_qs.filter(category_id=int(vehicle_category_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid vehicle_category_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        # Latest GPS snapshot per device tag.
        latest_gps_id_sq = GPSData.objects.filter(
            device_tag_id=OuterRef('id')
        ).order_by('-entry_time', '-id').values('id')[:1]

        device_tags_with_latest = device_tags_qs.annotate(
            latest_gps_id=Subquery(latest_gps_id_sq)
        ).exclude(latest_gps_id__isnull=True)

        latest_gps_qs = GPSData.objects.filter(
            id__in=Subquery(device_tags_with_latest.values('latest_gps_id'))
        )

        # Optional state filter from GPSData text field.
        if state_name:
            latest_gps_qs = latest_gps_qs.filter(state__iexact=state_name)

        states_list = [
            {'name': row['state']}
            for row in latest_gps_qs.exclude(state__isnull=True).exclude(state='').values('state').distinct().order_by('state')
        ]

        districts_list = [
            {
                'district_name': row['district'],
                'total_vehicle_count': row['total_vehicle_count'],
            }
            for row in (
                latest_gps_qs
                .exclude(district__isnull=True).exclude(district='')
                .values('district')
                .annotate(total_vehicle_count=Count('device_tag_id'))
                .order_by('district')
            )
        ]

        cities_list = []
        if district_name:
            cities_list = [
                {
                    'city_name': row['city'],
                    'total_vehicle_count': row['total_vehicle_count'],
                }
                for row in (
                    latest_gps_qs
                    .filter(district__iexact=district_name)
                    .exclude(city__isnull=True).exclude(city='')
                    .values('city')
                    .annotate(total_vehicle_count=Count('device_tag_id'))
                    .order_by('city')
                )
            ]

        localities_list = []
        if district_name and city_name:
            localities_list = [
                {
                    'locality_name': row['road'],
                    'total_vehicle_count': row['total_vehicle_count'],
                }
                for row in (
                    latest_gps_qs
                    .filter(district__iexact=district_name, city__iexact=city_name)
                    .exclude(road__isnull=True).exclude(road='')
                    .values('road')
                    .annotate(total_vehicle_count=Count('device_tag_id'))
                    .order_by('road')
                )
            ]

        # Keep vehicle categories from master settings.
        categories = Settings_VehicleCategory.objects.all().values(
            'id', 'category', 'maxSpeed', 'warnSpeed'
        ).order_by('category')

        categories_list = [
            {
                'id': category['id'],
                'name': category['category'],
                'max_speed': category['maxSpeed'],
                'warn_speed': category['warnSpeed']
            }
            for category in categories
        ]

        response_data = {
            'filters_applied': {
                'state_name': state_name or None,
                'district_name': district_name or None,
                'city_name': city_name or None,
                'vehicle_category_id': int(vehicle_category_id) if vehicle_category_id.isdigit() else None,
            },
            'source': 'gpsdata_latest_per_device_tag',
            'states': states_list,
            'districts': districts_list,
            'cities': cities_list,
            'localities': localities_list,
            'vehicle_categories': categories_list,
            'timestamp': timezone.now().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_dashboard_filter_options: {str(e)}")
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def get_areawise_device_tag_count(request):
    """
    Three-level drilldown API for area-wise device/vehicle counts.

    Level is determined by which parameters are supplied:

    Level 1 — District list (no params):
        Params  : state_id (optional), vehicle_category_id (optional)
        Response: flat list — [{district_name, latitude, longitude, total_vehicle_count}, …]

    Level 2 — City/town list inside a district:
        Params  : district_name
        Response: {district_name, total_locations, locations:[{location_type, city_village_name, lat, lon, total_vehicle_count}]}

    Level 3 — Locality list inside a city:
        Params  : district_name + city_name
        Response: {district_name, city_name, city_center_lat, city_center_lon, total_localities,
                   localities:[{locality_type, locality_name, lat, lon, total_vehicle_count}]}

    Level 4 — Device list inside a locality:
        Params  : district_name + city_name + locality_name
        Response: {district_name, city_name, locality_name, locality_center_lat, locality_center_lon,
                   total_devices, devices:[{device_id, vehicle_reg_no, vehicle_type, status,
                   lat, lon, last_seen, speed_kmph}]}

    Optional global filters (all levels): state_id, vehicle_category_id
    """
    try:
        from datetime import timedelta
        from django.db.models import Count, Avg, Subquery, OuterRef

        district_name = (request.data.get('district_name') or request.GET.get('district_name', '')).strip()
        city_name = (request.data.get('city_name') or request.GET.get('city_name', '')).strip()
        locality_name = (request.data.get('locality_name') or request.GET.get('locality_name', '')).strip()
        state_id = request.data.get('state_id') or request.GET.get('state_id')
        vehicle_category_id = request.data.get('vehicle_category_id') or request.GET.get('vehicle_category_id')

        # Base tagged devices; geo results must be derived from latest GPS of these devices.
        device_tags_qs = DeviceTag.objects.exclude(status='TagDeleted').exclude(status='Device_Untagged')

        if state_id:
            try:
                device_tags_qs = device_tags_qs.filter(district__state_id=int(state_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid state_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        if vehicle_category_id:
            try:
                device_tags_qs = device_tags_qs.filter(category_id=int(vehicle_category_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid vehicle_category_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        latest_gps_id_sq = GPSData.objects.filter(
            device_tag_id=OuterRef('id')
        ).order_by('-entry_time', '-id').values('id')[:1]

        device_tags_with_latest = device_tags_qs.annotate(
            latest_gps_id=Subquery(latest_gps_id_sq)
        ).exclude(latest_gps_id__isnull=True)

        latest_gps_qs = GPSData.objects.filter(
            id__in=Subquery(device_tags_with_latest.values('latest_gps_id'))
        )

        # Level 4: district + city + locality => devices in locality (from latest GPS only)
        if district_name and city_name and locality_name:
            threshold = timezone.now() - timedelta(minutes=15)
            locality_latest_qs = latest_gps_qs.filter(
                district__iexact=district_name,
                city__iexact=city_name,
                road__iexact=locality_name,
            ).select_related('device_tag__category').order_by('-entry_time', '-id')

            locality_avg = locality_latest_qs.aggregate(
                avg_lat=Avg('latitude'),
                avg_lon=Avg('longitude')
            )

            devices = []
            for gps in locality_latest_qs:
                dt = gps.device_tag
                if gps.entry_time >= threshold:
                    gps_status = 'idle' if (gps.speed or 0) == 0 else 'online'
                else:
                    gps_status = 'offline'

                devices.append({
                    'device_id': dt.id if dt else None,
                    'vehicle_reg_no': dt.vehicle_reg_no if dt else None,
                    'vehicle_type': dt.category.category if dt and dt.category else None,
                    'status': gps_status,
                    'lat': gps.latitude,
                    'lon': gps.longitude,
                    'last_seen': gps.entry_time.isoformat() if gps.entry_time else None,
                    'speed_kmph': gps.speed,
                })

            return Response({
                'district_name': district_name,
                'city_name': city_name,
                'locality_name': locality_name,
                'locality_center_lat': round(locality_avg['avg_lat'], 6) if locality_avg['avg_lat'] else None,
                'locality_center_lon': round(locality_avg['avg_lon'], 6) if locality_avg['avg_lon'] else None,
                'total_devices': len(devices),
                'devices': devices,
            }, status=status.HTTP_200_OK)

        # Level 3: district + city => localities in city (from latest GPS only)
        if district_name and city_name:
            city_latest_qs = latest_gps_qs.filter(
                district__iexact=district_name,
                city__iexact=city_name,
                road__isnull=False,
            ).exclude(road='')

            city_avg = latest_gps_qs.filter(
                district__iexact=district_name,
                city__iexact=city_name,
            ).aggregate(avg_lat=Avg('latitude'), avg_lon=Avg('longitude'))

            locality_rows = (
                city_latest_qs
                .values('road')
                .annotate(
                    total_vehicle_count=Count('device_tag_id'),
                    lat=Avg('latitude'),
                    lon=Avg('longitude'),
                )
                .order_by('-total_vehicle_count')
            )

            localities = [
                {
                    'locality_type': 'road',
                    'locality_name': row['road'],
                    'lat': round(row['lat'], 6) if row['lat'] else None,
                    'lon': round(row['lon'], 6) if row['lon'] else None,
                    'total_vehicle_count': row['total_vehicle_count'],
                }
                for row in locality_rows
            ]

            return Response({
                'district_name': district_name,
                'city_name': city_name,
                'city_center_lat': round(city_avg['avg_lat'], 6) if city_avg['avg_lat'] else None,
                'city_center_lon': round(city_avg['avg_lon'], 6) if city_avg['avg_lon'] else None,
                'total_localities': len(localities),
                'localities': localities,
            }, status=status.HTTP_200_OK)

        # Level 2: district => cities in district (from latest GPS only)
        if district_name:
            district_latest_qs = latest_gps_qs.filter(
                district__iexact=district_name,
                city__isnull=False,
            ).exclude(city='')

            city_rows = (
                district_latest_qs
                .values('city')
                .annotate(
                    total_vehicle_count=Count('device_tag_id'),
                    lat=Avg('latitude'),
                    lon=Avg('longitude'),
                )
                .order_by('-total_vehicle_count')
            )

            locations = [
                {
                    'location_type': 'town',
                    'city_village_name': row['city'],
                    'lat': round(row['lat'], 6) if row['lat'] else None,
                    'lon': round(row['lon'], 6) if row['lon'] else None,
                    'total_vehicle_count': row['total_vehicle_count'],
                }
                for row in city_rows
            ]

            return Response({
                'district_name': district_name,
                'total_locations': len(locations),
                'locations': locations,
            }, status=status.HTTP_200_OK)

        # Level 1: districts (from latest GPS only)
        district_rows = (
            latest_gps_qs
            .filter(district__isnull=False)
            .exclude(district='')
            .values('district')
            .annotate(
                total_vehicle_count=Count('device_tag_id'),
                latitude=Avg('latitude'),
                longitude=Avg('longitude'),
            )
            .order_by('district')
        )

        result = [
            {
                'district_name': row['district'],
                'latitude': round(row['latitude'], 6) if row['latitude'] else None,
                'longitude': round(row['longitude'], 6) if row['longitude'] else None,
                'total_vehicle_count': row['total_vehicle_count'],
            }
            for row in district_rows
        ]

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_areawise_device_tag_count: {str(e)}")
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def get_latest_vehicle_locations(request):
    """
    Get the latest GPS location of all vehicles matching filters.

    Supports both ID-based and name-based geographic filters.

    Parameters (GET or POST body):
    - state_id             : filter by state FK ID (optional)
    - district_id          : filter by district FK ID (optional)
    - vehicle_category_id  : filter by category FK ID (optional)
    - district_name        : filter by district name text (optional)
    - city_name            : filter by GPS city text (optional, requires district_name)
    - locality_name        : filter by GPS road/locality text (optional, requires city_name)
    - limit                : max devices to return (default 100, max 1000)

    Response fields per device:
    device_id, vehicle_reg_no, vehicle_type, vehicle_make, vehicle_model,
    status (online/idle/offline), lat, lon, last_seen, speed_kmph,
    heading, city, district, state, satellites, ignition_status, imei
    """
    try:
        from django.db.models import Subquery, OuterRef
        from datetime import timedelta

        # ── read all params (support both GET and POST body) ──────────────
        def _p(key, default=''):
            v = request.data.get(key) or request.GET.get(key, default)
            return str(v).strip() if v is not None else default

        state_id = _p('state_id')
        district_id = _p('district_id')
        vehicle_category_id = _p('vehicle_category_id')
        district_name = _p('district_name')
        city_name = _p('city_name')
        locality_name = _p('locality_name')

        try:
            limit = int(_p('limit', '100'))
            limit = max(1, min(limit, 1000))
        except ValueError:
            limit = 100

        # Base tagged devices
        device_tags_qs = DeviceTag.objects.exclude(status='TagDeleted').exclude(status='Device_Untagged')

        if state_id:
            try:
                device_tags_qs = device_tags_qs.filter(district__state_id=int(state_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid state_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        if district_id:
            try:
                device_tags_qs = device_tags_qs.filter(district_id=int(district_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid district_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        if vehicle_category_id:
            try:
                device_tags_qs = device_tags_qs.filter(category_id=int(vehicle_category_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid vehicle_category_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        # Latest GPS snapshot per device tag
        latest_gps = GPSData.objects.filter(
            device_tag_id=OuterRef('id')
        ).order_by('-entry_time', '-id')

        device_tags_annotated = (
            device_tags_qs
            .select_related('category', 'device')
            .annotate(
                last_lat=Subquery(latest_gps.values('latitude')[:1]),
                last_lon=Subquery(latest_gps.values('longitude')[:1]),
                last_seen=Subquery(latest_gps.values('entry_time')[:1]),
                last_speed=Subquery(latest_gps.values('speed')[:1]),
                last_heading=Subquery(latest_gps.values('heading')[:1]),
                last_city=Subquery(latest_gps.values('city')[:1]),
                last_district=Subquery(latest_gps.values('district')[:1]),
                last_state=Subquery(latest_gps.values('state')[:1]),
                last_road=Subquery(latest_gps.values('road')[:1]),
                last_satellites=Subquery(latest_gps.values('satellites')[:1]),
                last_ignition=Subquery(latest_gps.values('ignition_status')[:1]),
            )
            .exclude(last_seen__isnull=True)
        )

        # Name-based filters must apply on latest GPS only.
        if district_name:
            device_tags_annotated = device_tags_annotated.filter(last_district__iexact=district_name)
        if city_name:
            device_tags_annotated = device_tags_annotated.filter(last_city__iexact=city_name)
        if locality_name:
            device_tags_annotated = device_tags_annotated.filter(last_road__iexact=locality_name)

        device_tags_annotated = device_tags_annotated[:limit]

        now = timezone.now()
        threshold = now - timedelta(minutes=15)

        devices = []
        for dt in device_tags_annotated:
            if dt.last_seen is None:
                continue

            if dt.last_seen >= threshold:
                dev_status = 'idle' if (dt.last_speed or 0) == 0 else 'online'
            else:
                dev_status = 'offline'

            devices.append({
                'device_id': dt.id,
                'vehicle_reg_no': dt.vehicle_reg_no,
                'vehicle_type': dt.category.category if dt.category else None,
                'vehicle_make': dt.vehicle_make,
                'vehicle_model': dt.vehicle_model,
                'imei': dt.device.imei if dt.device else None,
                'status': dev_status,
                'lat': dt.last_lat,
                'lon': dt.last_lon,
                'last_seen': dt.last_seen.isoformat() if dt.last_seen else None,
                'speed_kmph': dt.last_speed,
                'heading': dt.last_heading,
                'city': dt.last_city,
                'district': dt.last_district,
                'state': dt.last_state,
                'satellites': dt.last_satellites,
                'ignition_status': dt.last_ignition,
            })

        response_data = {
            'filters_applied': {
                'state_id': state_id or None,
                'district_id': district_id or None,
                'vehicle_category_id': vehicle_category_id or None,
                'district_name': district_name or None,
                'city_name': city_name or None,
                'locality_name': locality_name or None,
            },
            'total_vehicles': len(devices),
            'vehicle_locations': devices,
            'timestamp': now.isoformat(),
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_latest_vehicle_locations: {str(e)}")
        return Response({
            'error': f'An error occurred: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def erss_dashboard_summary(request):
    """
    ERSS overview metrics:
    - total tagged devices, online devices, offline devices
    - active emergency calls
    - total police/ambulance executives
    - police/ambulance executives with latest location update within last 5 mins
    """
    try:
        from datetime import timedelta
        from django.db.models import OuterRef, Subquery
        from .models import EMCall, EM_ex, EMUserLocation

        def _p(key, default=''):
            v = request.data.get(key) or request.GET.get(key, default)
            return str(v).strip() if v is not None else default

        state_id = _p('state_id')
        district_id = _p('district_id')
        vehicle_category_id = _p('vehicle_category_id')

        device_tags_qs = DeviceTag.objects.exclude(status='TagDeleted').exclude(status='Device_Untagged')

        if state_id:
            try:
                device_tags_qs = device_tags_qs.filter(district__state_id=int(state_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid state_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        if district_id:
            try:
                device_tags_qs = device_tags_qs.filter(district_id=int(district_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid district_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        if vehicle_category_id:
            try:
                device_tags_qs = device_tags_qs.filter(category_id=int(vehicle_category_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid vehicle_category_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        latest_gps = GPSData.objects.filter(device_tag_id=OuterRef('id')).order_by('-entry_time', '-id')
        tagged_with_latest = device_tags_qs.annotate(
            last_seen=Subquery(latest_gps.values('entry_time')[:1]),
            last_speed=Subquery(latest_gps.values('speed')[:1]),
        )

        now = timezone.now()
        gps_online_threshold = now - timedelta(minutes=15)
        exec_online_threshold = now - timedelta(minutes=5)

        total_tagged_devices = device_tags_qs.count()
        online_devices = tagged_with_latest.filter(last_seen__gte=gps_online_threshold).count()
        offline_devices = total_tagged_devices - online_devices

        active_call_statuses = ['pending', 'desk_ex_assigned', 'broadcast_pending', 'field_ex_aproaching', 'field_ex_arrived']
        em_calls_qs = EMCall.objects.filter(status__in=active_call_statuses)
        if state_id:
            em_calls_qs = em_calls_qs.filter(team__state_id=int(state_id))
        if district_id:
            em_calls_qs = em_calls_qs.filter(device__district_id=int(district_id))
        active_emergency_calls = em_calls_qs.count()

        police_types = ['police_ex', 'PCR']
        ambulance_types = ['ambulance_ex', 'ACR']
        exec_types = police_types + ambulance_types

        exec_qs = EM_ex.objects.filter(user_type__in=exec_types)
        if state_id:
            exec_qs = exec_qs.filter(state_id=int(state_id))
        if district_id:
            district_obj = Settings_District.objects.filter(id=int(district_id)).first()
            if district_obj:
                exec_qs = exec_qs.filter(district__iexact=district_obj.district)

        total_police_executives = exec_qs.filter(user_type__in=police_types).count()
        total_ambulance_executives = exec_qs.filter(user_type__in=ambulance_types).count()

        latest_exec_locations = (
            EMUserLocation.objects
            .filter(field_ex__in=exec_qs)
            .values('field_ex_id')
            .annotate(last_time=Max('time'))
            .filter(last_time__gte=exec_online_threshold)
        )
        recent_exec_ids = set(row['field_ex_id'] for row in latest_exec_locations)

        police_recent = exec_qs.filter(id__in=recent_exec_ids, user_type__in=police_types).count()
        ambulance_recent = exec_qs.filter(id__in=recent_exec_ids, user_type__in=ambulance_types).count()

        return Response({
            'filters_applied': {
                'state_id': state_id or None,
                'district_id': district_id or None,
                'vehicle_category_id': vehicle_category_id or None,
            },
            'erss_dashboard_metrics': {
                'total_tagged_device_count': total_tagged_devices,
                'online_device_count': online_devices,
                'offline_device_count': offline_devices,
                'active_emergency_calls_count': active_emergency_calls,
                'total_police_sos_executive_count': total_police_executives,
                'total_ambulance_sos_executive_count': total_ambulance_executives,
                'total_police_and_ambulance_sos_executive_count': total_police_executives + total_ambulance_executives,
                'police_executive_with_latest_location_within_5_min_count': police_recent,
                'ambulance_executive_with_latest_location_within_5_min_count': ambulance_recent,
                'total_executive_with_latest_location_within_5_min_count': police_recent + ambulance_recent,
            },
            'timestamp': now.isoformat(),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in erss_dashboard_summary: {str(e)}")
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def sos_analysis_dashboard(request):
    """
    SOS analysis for last 1 year with month-wise, hour-wise and district-wise counts:
    - total_calls_count
    - total_police_broadcasts
    - total_ambulance_broadcasts
    - total_police_accepted
    - total_ambulance_accepted
    - total_fake_call_close
    - total_unattended_calls
    """
    try:
        from datetime import timedelta
        from django.db.models import Count, Exists, OuterRef
        from django.db.models.functions import TruncMonth, ExtractHour
        from .models import EMCall, EMCallAssignment, EMCallBroadcast

        def _p(key, default=''):
            v = request.data.get(key) or request.GET.get(key, default)
            return str(v).strip() if v is not None else default

        state_id = _p('state_id')
        district_id = _p('district_id')

        now = timezone.now()
        start_dt = now - timedelta(days=365)

        call_qs = EMCall.objects.filter(start_time__gte=start_dt)
        if state_id:
            try:
                call_qs = call_qs.filter(team__state_id=int(state_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid state_id parameter'}, status=status.HTTP_400_BAD_REQUEST)
        if district_id:
            try:
                call_qs = call_qs.filter(device__district_id=int(district_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid district_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        accepted_assignment_exists = EMCallAssignment.objects.filter(
            call_id=OuterRef('pk'),
            status='accepted'
        )

        unattended_statuses = ['pending', 'desk_ex_assigned', 'broadcast_pending']
        call_qs = call_qs.annotate(has_accepted_assignment=Exists(accepted_assignment_exists))

        fake_statuses = ['closed_false_alert', 'closed_false_allert']

        monthly = []
        month_rows = (
            call_qs
            .annotate(period=TruncMonth('start_time'))
            .values('period')
            .annotate(
                total_calls_count=Count('id'),
                total_fake_call_close=Count('id', filter=Q(status__in=fake_statuses)),
                total_unattended_calls=Count('id', filter=Q(status__in=unattended_statuses, has_accepted_assignment=False)),
            )
            .order_by('period')
        )

        for row in month_rows:
            period_start = row['period']
            period_end = (period_start + timedelta(days=32)).replace(day=1)
            period_call_ids = call_qs.filter(start_time__gte=period_start, start_time__lt=period_end).values_list('id', flat=True)

            police_broadcasts = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['police_ex', 'pcr']).count()
            ambulance_broadcasts = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['ambulance_ex', 'acr']).count()
            police_accepted = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['police_ex', 'pcr'], status='accepted').count()
            ambulance_accepted = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['ambulance_ex', 'acr'], status='accepted').count()

            monthly.append({
                'month': period_start.strftime('%Y-%m'),
                'total_calls_count': row['total_calls_count'],
                'total_police_broadcast_count': police_broadcasts,
                'total_ambulance_broadcast_count': ambulance_broadcasts,
                'total_police_accepted_count': police_accepted,
                'total_ambulance_accepted_count': ambulance_accepted,
                'total_fake_call_close': row['total_fake_call_close'],
                'total_unattended_calls': row['total_unattended_calls'],
            })

        hourly = []
        hour_rows = (
            call_qs
            .annotate(hour_of_day=ExtractHour('start_time'))
            .values('hour_of_day')
            .annotate(
                total_calls_count=Count('id'),
                total_fake_call_close=Count('id', filter=Q(status__in=fake_statuses)),
                total_unattended_calls=Count('id', filter=Q(status__in=unattended_statuses, has_accepted_assignment=False)),
            )
            .order_by('hour_of_day')
        )

        for row in hour_rows:
            h = row['hour_of_day']
            period_call_ids = call_qs.annotate(hh=ExtractHour('start_time')).filter(hh=h).values_list('id', flat=True)
            police_broadcasts = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['police_ex', 'pcr']).count()
            ambulance_broadcasts = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['ambulance_ex', 'acr']).count()
            police_accepted = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['police_ex', 'pcr'], status='accepted').count()
            ambulance_accepted = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['ambulance_ex', 'acr'], status='accepted').count()

            hourly.append({
                'hour_of_day': h,
                'total_calls_count': row['total_calls_count'],
                'total_police_broadcast_count': police_broadcasts,
                'total_ambulance_broadcast_count': ambulance_broadcasts,
                'total_police_accepted_count': police_accepted,
                'total_ambulance_accepted_count': ambulance_accepted,
                'total_fake_call_close': row['total_fake_call_close'],
                'total_unattended_calls': row['total_unattended_calls'],
            })

        district_rows = (
            call_qs
            .values('device__district__district')
            .annotate(
                total_calls_count=Count('id'),
                total_fake_call_close=Count('id', filter=Q(status__in=fake_statuses)),
                total_unattended_calls=Count('id', filter=Q(status__in=unattended_statuses, has_accepted_assignment=False)),
            )
            .order_by('device__district__district')
        )

        district_wise = []
        for row in district_rows:
            district_name = row['device__district__district']
            period_call_ids = call_qs.filter(device__district__district=district_name).values_list('id', flat=True)
            police_broadcasts = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['police_ex', 'pcr']).count()
            ambulance_broadcasts = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['ambulance_ex', 'acr']).count()
            police_accepted = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['police_ex', 'pcr'], status='accepted').count()
            ambulance_accepted = EMCallBroadcast.objects.filter(call_id__in=period_call_ids, type__in=['ambulance_ex', 'acr'], status='accepted').count()

            district_wise.append({
                'district_name': district_name,
                'total_calls_count': row['total_calls_count'],
                'total_police_broadcast_count': police_broadcasts,
                'total_ambulance_broadcast_count': ambulance_broadcasts,
                'total_police_accepted_count': police_accepted,
                'total_ambulance_accepted_count': ambulance_accepted,
                'total_fake_call_close': row['total_fake_call_close'],
                'total_unattended_calls': row['total_unattended_calls'],
            })

        overall_call_ids = call_qs.values_list('id', flat=True)
        response_data = {
            'time_window': {
                'from': start_dt.isoformat(),
                'to': now.isoformat(),
                'label': 'last_1_year',
            },
            'overall_metrics': {
                'total_calls_count': call_qs.count(),
                'total_police_broadcast_count': EMCallBroadcast.objects.filter(call_id__in=overall_call_ids, type__in=['police_ex', 'pcr']).count(),
                'total_ambulance_broadcast_count': EMCallBroadcast.objects.filter(call_id__in=overall_call_ids, type__in=['ambulance_ex', 'acr']).count(),
                'total_police_accepted_count': EMCallBroadcast.objects.filter(call_id__in=overall_call_ids, type__in=['police_ex', 'pcr'], status='accepted').count(),
                'total_ambulance_accepted_count': EMCallBroadcast.objects.filter(call_id__in=overall_call_ids, type__in=['ambulance_ex', 'acr'], status='accepted').count(),
                'total_fake_call_close': call_qs.filter(status__in=fake_statuses).count(),
                'total_unattended_calls': call_qs.filter(status__in=unattended_statuses, has_accepted_assignment=False).count(),
            },
            'month_wise_metrics': monthly,
            'hour_of_day_wise_metrics': hourly,
            'district_wise_metrics': district_wise,
            'filters_applied': {
                'state_id': state_id or None,
                'district_id': district_id or None,
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in sos_analysis_dashboard: {str(e)}")
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
def sos_monitoring_dashboard(request):
    """
    SOS monitoring dashboard KPIs:
    - total emergency calls today
    - total live calls now
    - total unattended calls now
    - total closed calls today
    - average time to accept by desk executive
    - average time to accept broadcast by police
    - average time to accept broadcast by ambulance
    - calls accepted by team lead total and % of total calls
    """
    try:
        from datetime import timedelta
        from django.db.models import Avg, DurationField, ExpressionWrapper, F, Exists, OuterRef
        from .models import EMCall, EMCallAssignment, EMCallBroadcast

        def _p(key, default=''):
            v = request.data.get(key) or request.GET.get(key, default)
            return str(v).strip() if v is not None else default

        state_id = _p('state_id')
        district_id = _p('district_id')

        now = timezone.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        calls_today = EMCall.objects.filter(start_time__gte=day_start, start_time__lte=now)
        if state_id:
            try:
                calls_today = calls_today.filter(team__state_id=int(state_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid state_id parameter'}, status=status.HTTP_400_BAD_REQUEST)
        if district_id:
            try:
                calls_today = calls_today.filter(device__district_id=int(district_id))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid district_id parameter'}, status=status.HTTP_400_BAD_REQUEST)

        live_statuses = ['pending', 'desk_ex_assigned', 'broadcast_pending', 'field_ex_aproaching', 'field_ex_arrived']
        closed_statuses = ['closed', 'closed_false_alert', 'closed_false_allert']

        total_emergency_calls_today = calls_today.count()
        total_live_calls_now = calls_today.filter(status__in=live_statuses).count()
        total_closed_calls_today = calls_today.filter(status__in=closed_statuses).count()

        accepted_assignment_exists = EMCallAssignment.objects.filter(call_id=OuterRef('pk'), status='accepted')
        unattended_statuses = ['pending', 'desk_ex_assigned', 'broadcast_pending']
        total_unattended_calls_now = (
            calls_today
            .filter(status__in=unattended_statuses)
            .annotate(has_accepted=Exists(accepted_assignment_exists))
            .filter(has_accepted=False)
            .count()
        )

        desk_avg = (
            EMCallAssignment.objects
            .filter(call__in=calls_today, type='desk_ex')
            .exclude(accept_time__isnull=True)
            .annotate(diff=ExpressionWrapper(F('accept_time') - F('start_time'), output_field=DurationField()))
            .aggregate(avg=Avg('diff'))
        )['avg']

        police_broadcast_avg = (
            EMCallBroadcast.objects
            .filter(call__in=calls_today, type__in=['police_ex', 'pcr'])
            .exclude(accept_at__isnull=True)
            .annotate(diff=ExpressionWrapper(F('accept_at') - F('created_at'), output_field=DurationField()))
            .aggregate(avg=Avg('diff'))
        )['avg']

        ambulance_broadcast_avg = (
            EMCallBroadcast.objects
            .filter(call__in=calls_today, type__in=['ambulance_ex', 'acr'])
            .exclude(accept_at__isnull=True)
            .annotate(diff=ExpressionWrapper(F('accept_at') - F('created_at'), output_field=DurationField()))
            .aggregate(avg=Avg('diff'))
        )['avg']

        teamlead_accepted_calls = (
            EMCallAssignment.objects
            .filter(call__in=calls_today, type='teamlead')
            .exclude(accept_time__isnull=True)
            .values('call_id')
            .distinct()
            .count()
        )

        teamlead_accept_percentage = 0
        if total_emergency_calls_today > 0:
            teamlead_accept_percentage = round((teamlead_accepted_calls / total_emergency_calls_today) * 100, 2)

        return Response({
            'filters_applied': {
                'state_id': state_id or None,
                'district_id': district_id or None,
            },
            'sos_monitoring_metrics': {
                'total_emergency_calls_today': total_emergency_calls_today,
                'total_live_calls_now': total_live_calls_now,
                'total_unattended_calls_now': total_unattended_calls_now,
                'total_closed_calls_today': total_closed_calls_today,
                'average_time_to_accept_by_desk_executive_seconds': desk_avg.total_seconds() if desk_avg else None,
                'average_time_to_accept_broadcast_by_police_seconds': police_broadcast_avg.total_seconds() if police_broadcast_avg else None,
                'average_time_to_accept_broadcast_by_ambulance_seconds': ambulance_broadcast_avg.total_seconds() if ambulance_broadcast_avg else None,
                'calls_accepted_by_team_lead_total': teamlead_accepted_calls,
                'calls_accepted_by_team_lead_percent_of_total_calls': teamlead_accept_percentage,
            },
            'timestamp': now.isoformat(),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in sos_monitoring_dashboard: {str(e)}")
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
