"""
Super-admin VLTD summary: one call that returns every tile on the VLTD
overview screen (fleet summary, vendor-wise installs, inactivity breakdown,
health request status, manufacturer details, eSIM validity buckets).

Definitions
-----------
Installed VLTD    DeviceTag with a device attached, excluding deleted /
                  untagged tags.
Registered        Installed VLTD whose tagging finished
                  (status Owner_Final_OTP_Verified).
Active            Last GPS packet within ONLINE_THRESHOLD (10 min — same
                  threshold get_device_health_status uses).
Inactive          Has sent GPS data, but not within ONLINE_THRESHOLD.
Never active      No GPS data at all.
Active + Inactive + Never active == Installed.
"""
from datetime import timedelta

from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Dealer, DeviceModel, DeviceTag, GPSData, Manufacturer, OTACommandDefinition,
    OTACommandHistory,
)
from .rbac import require_permission

ONLINE_THRESHOLD = timedelta(minutes=10)
# OTA command (command_id or PK) that requests device health.
HEALTH_OTA_COMMAND = '0'
EXCLUDED_TAG_STATUSES = ['TagDeleted', 'Device_Untagged', 'untaged_after_failed_taging']
REGISTERED_TAG_STATUSES = ['Owner_Final_OTP_Verified']

# (label, lower bound, upper bound) of time since the last GPS packet.
INACTIVE_BUCKETS = [
    ('10_min_to_24_hours', ONLINE_THRESHOLD, timedelta(hours=24)),
    ('24_hours_to_7_days', timedelta(hours=24), timedelta(days=7)),
    ('7_to_15_days', timedelta(days=7), timedelta(days=15)),
    ('15_to_30_days', timedelta(days=15), timedelta(days=30)),
    ('more_than_30_days', timedelta(days=30), None),
]

# (label, first day, last day) of eSIM validity remaining.
ESIM_BUCKETS = [
    ('0_7_days_remaining', 0, 7),
    ('8_15_days_remaining', 8, 15),
    ('16_30_days_remaining', 16, 30),
]


def _vendor_wise(installed_qs):
    """Installed VLTD count per manufacturer. DeviceModel.created_by is a
    manufacturer user, so map those users back to their Manufacturer."""
    per_creator = dict(
        installed_qs.values('device__model__created_by_id')
        .annotate(c=Count('id'))
        .values_list('device__model__created_by_id', 'c')
    )
    user_to_mfr = dict(Manufacturer.users.through.objects.values_list('user_id', 'manufacturer_id'))

    counts = {m.id: 0 for m in Manufacturer.objects.only('id')}
    unmapped = 0
    for user_id, c in per_creator.items():
        mfr_id = user_to_mfr.get(user_id)
        if mfr_id is None:
            unmapped += c
        else:
            counts[mfr_id] = counts.get(mfr_id, 0) + c

    names = dict(Manufacturer.objects.values_list('id', 'company_name'))
    rows = [
        {'manufacturer_id': mid, 'vendor_name': names.get(mid), 'installed_vltd_count': c}
        for mid, c in counts.items()
    ]
    if unmapped:
        rows.append({'manufacturer_id': None, 'vendor_name': 'Unknown', 'installed_vltd_count': unmapped})
    rows.sort(key=lambda r: (-r['installed_vltd_count'], r['vendor_name'] or ''))
    return rows


def _health_status(ota_command):
    """Health requests are sent as an OTA command, so count that command's
    rows in the OTA command log. ota_command is its command_id or PK.
    Returns None if no such command definition exists."""
    definition = OTACommandDefinition.objects.filter(
        Q(command_id=ota_command) | Q(pk=int(ota_command) if ota_command.isdigit() else None)
    ).first()
    if not definition:
        return None

    agg = OTACommandHistory.objects.filter(ota_command=definition).aggregate(
        sent=Count('id', filter=~Q(send_status='failed')),
        received=Count('id', filter=Q(send_status='replied') | Q(received_at__isnull=False)),
        awaited=Count('id', filter=Q(send_status__in=['queued', 'sent'], received_at__isnull=True)),
    )
    return {
        'health_request_sent': agg['sent'],
        'health_response_received': agg['received'],
        'health_response_awaited': agg['awaited'],
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_permission('dashboard_central', 'view')
def superadmin_vltd_summary(request):
    """
    GET /api/superadmin/vltd-summary/
    Optional: ?ota_command=<OTACommandDefinition command_id or id> — the
    command whose history backs the health status (default: HEALTH_OTA_COMMAND).
    """
    if getattr(request.user, 'role', None) != 'superadmin':
        return Response({'error': 'Only superadmin can access this API'}, status=status.HTTP_403_FORBIDDEN)

    ota_command = (request.GET.get('ota_command') or '').strip()
    health = _health_status(ota_command or HEALTH_OTA_COMMAND)
    if health is None:
        if ota_command:
            return Response({'error': 'OTA command not found'}, status=status.HTTP_400_BAD_REQUEST)
        # Default health command not configured yet — show zeros, don't break the dashboard.
        health = {'health_request_sent': 0, 'health_response_received': 0, 'health_response_awaited': 0}

    now = timezone.now()
    installed_qs = DeviceTag.objects.filter(device__isnull=False).exclude(status__in=EXCLUDED_TAG_STATUSES)

    # Latest GPS time per installed tag (GROUP BY on gpsdata_tag_time_id_idx).
    latest_by_tag = dict(
        GPSData.objects.filter(device_tag_id__in=installed_qs.values('id'))
        .values('device_tag_id')
        .annotate(last=Max('entry_time'))
        .values_list('device_tag_id', 'last')
    )

    installed = installed_qs.count()
    active = 0
    inactive_buckets = {label: 0 for label, _, _ in INACTIVE_BUCKETS}
    for last in latest_by_tag.values():
        age = now - last
        if age < ONLINE_THRESHOLD:
            active += 1
            continue
        for label, lo, hi in INACTIVE_BUCKETS:
            if age >= lo and (hi is None or age < hi):
                inactive_buckets[label] += 1
                break
    inactive = sum(inactive_buckets.values())

    esim_filters = {
        label: Q(device__esim_validity__gte=now + timedelta(days=first),
                 device__esim_validity__lt=now + timedelta(days=last + 1))
        for label, first, last in ESIM_BUCKETS
    }
    esim_agg = installed_qs.aggregate(
        registered=Count('id', filter=Q(status__in=REGISTERED_TAG_STATUSES)),
        esim_exhausted=Count('id', filter=Q(device__esim_validity__lt=now)),
        **{label: Count('id', filter=f) for label, f in esim_filters.items()},
    )

    return Response({
        'vltd_summary': {
            'installed_vltds_in_all_vehicles': installed,
            'vltds_in_registered_vehicles': esim_agg['registered'],
            'active_vltds': active,
            'inactive_vltds': inactive,
            'never_active_vltds': installed - len(latest_by_tag),
            'esim_validity_exhausted': esim_agg['esim_exhausted'],
        },
        'vendor_wise_vltds': _vendor_wise(installed_qs),
        'inactive_breakdown': inactive_buckets,
        'vltd_health_status': health,
        'manufacturer_details': {
            'total_vltd_manufacturers': Manufacturer.objects.count(),
            'total_rfcs': Dealer.objects.count(),
            'total_vltd_models': DeviceModel.objects.exclude(status='StateAdminRejected').count(),
        },
        'esim_validity': {label: esim_agg[label] for label, _, _ in ESIM_BUCKETS},
        'generated_at': now.isoformat(),
    }, status=status.HTTP_200_OK)
