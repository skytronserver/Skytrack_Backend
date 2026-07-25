"""
Whitelist Request Management — API views.

Endpoints
---------
POST  /api/whitelist/request/create/              – Create add/remove request (Manufacturer, Dealer)
GET   /api/whitelist/request/list/                – List own requests (Manufacturer, Dealer)
GET   /api/whitelist/request/esim/all/            – List requests directed to provider (eSimProvider)
POST  /api/whitelist/request/<pk>/approve/        – Approve a request (eSimProvider)
POST  /api/whitelist/request/<pk>/deny/           – Deny a request (eSimProvider)
GET   /api/whitelist/active/list/                 – Active whitelisted entries (all roles, scoped)
"""

from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Prefetch

from .jwt_authentication import JWTAuthentication
from .models import (
    ActiveWhitelist, Dealer, DeviceActivationLog, DeviceStock, Manufacturer,
    WhitelistEntry, WhitelistRequest, WhitelistRequestReview, eSimProvider,
)

_REQUESTER_ROLES = {'devicemanufacture', 'dealer'}
_ESIM_ROLE = 'esimprovider'
_ADMIN_ROLES = {'superadmin', 'stateadmin'}
_ALL_ALLOWED_ROLES = _REQUESTER_ROLES | {_ESIM_ROLE} | _ADMIN_ROLES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_esim_provider(user):
    return eSimProvider.objects.filter(users=user).first()


def _get_manufacturer(user):
    return Manufacturer.objects.filter(users=user).first()


def _get_dealer(user):
    return Dealer.objects.filter(users=user).first()


def _accessible_stocks(user):
    """DeviceStock queryset visible to the requesting user."""
    role = getattr(user, 'role', None)
    if role == 'devicemanufacture':
        mfr = _get_manufacturer(user)
        if not mfr:
            return DeviceStock.objects.none()
        return DeviceStock.objects.filter(dealer__manufacturer=mfr).exclude(stock_status='Deleted')
    if role == 'dealer':
        dealer = _get_dealer(user)
        if not dealer:
            return DeviceStock.objects.none()
        return DeviceStock.objects.filter(dealer=dealer).exclude(stock_status='Deleted')
    return DeviceStock.objects.none()


def _serialize_request(req):
    review_data = None
    try:
        rv = req.review
        review_data = {
            'action': rv.action,
            'reason': rv.reason,
            'reviewed_by_id': rv.reviewed_by_id,
            'reviewed_by_name': getattr(rv.reviewed_by, 'name', ''),
            'reviewed_at': rv.reviewed_at,
        }
    except WhitelistRequestReview.DoesNotExist:
        pass

    return {
        'id': req.id,
        'request_type': req.request_type,
        'status': req.status,
        'requester_type': req.requester_type,
        'requested_by_id': req.requested_by_id,
        'requested_by_name': getattr(req.requested_by, 'name', ''),
        'esim_provider_id': req.esim_provider_id,
        'esim_provider_name': req.esim_provider.company_name if req.esim_provider_id else '',
        'manufacturer_id': req.manufacturer_id,
        'dealer_id': req.dealer_id,
        'requester_remarks': req.requester_remarks,
        'device_stock_ids': list(req.device_stocks.values_list('id', flat=True)),
        'device_stock_count': req.device_stocks.count(),
        'entries': list(req.entries.values('id', 'whitelist_type', 'value')),
        'review': review_data,
        'created_at': req.created_at,
        'updated_at': req.updated_at,
    }


# ---------------------------------------------------------------------------
# Manufacturer / Dealer endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_whitelist_request(request):
    """
    Create a whitelist add or remove request.

    Body (JSON):
      request_type      – "add" | "remove"
      esim_provider_id  – int
      entries           – [{whitelist_type: "ip"|"url"|"phone"|"apn", value: str}, ...]
      device_stock_ids  – list of int | "all"  (default: "all")
      requester_remarks – str (optional)
    """
    user = request.user
    role = getattr(user, 'role', None)
    if role not in _REQUESTER_ROLES:
        return Response({'error': 'Only manufacturers and dealers can create whitelist requests.'}, status=403)

    data = request.data
    request_type = data.get('request_type')
    if request_type not in ('add', 'remove'):
        return Response({'error': 'request_type must be "add" or "remove".'}, status=400)

    esim_provider_id = data.get('esim_provider_id')
    if not esim_provider_id:
        return Response({'error': 'esim_provider_id is required.'}, status=400)
    try:
        provider = eSimProvider.objects.get(id=esim_provider_id)
    except eSimProvider.DoesNotExist:
        return Response({'error': 'eSimProvider not found.'}, status=404)

    entries_data = data.get('entries', [])
    if not entries_data or not isinstance(entries_data, list):
        return Response({'error': 'entries must be a non-empty list of {whitelist_type, value} objects.'}, status=400)

    valid_types = {'ip', 'url', 'phone', 'apn'}
    for entry in entries_data:
        if entry.get('whitelist_type') not in valid_types:
            return Response(
                {'error': f'Invalid whitelist_type. Must be one of: {", ".join(sorted(valid_types))}'},
                status=400,
            )
        if not str(entry.get('value', '')).strip():
            return Response({'error': 'Each entry must have a non-empty value.'}, status=400)

    # Resolve device stocks — must be accessible by this user AND linked to the provider
    accessible_qs = _accessible_stocks(user)
    device_stock_ids = data.get('device_stock_ids', 'all')

    if device_stock_ids == 'all':
        selected = accessible_qs.filter(esim_provider=provider)
    else:
        if not isinstance(device_stock_ids, list) or not device_stock_ids:
            return Response({'error': 'device_stock_ids must be a list of IDs or the string "all".'}, status=400)
        selected = accessible_qs.filter(id__in=device_stock_ids, esim_provider=provider)
        found_ids = set(selected.values_list('id', flat=True))
        missing = [i for i in device_stock_ids if i not in found_ids]
        if missing:
            return Response(
                {'error': f'Device stocks not found / not accessible / not linked to the specified eSimProvider: {missing}'},
                status=403,
            )

    if not selected.exists():
        return Response({'error': 'No accessible device stocks found linked to the specified eSimProvider.'}, status=400)

    # Identify requester entity
    manufacturer = None
    dealer = None
    if role == 'devicemanufacture':
        manufacturer = _get_manufacturer(user)
        if not manufacturer:
            return Response({'error': 'No manufacturer record found for this user.'}, status=400)
        requester_type = 'manufacturer'
    else:
        dealer = _get_dealer(user)
        if not dealer:
            return Response({'error': 'No dealer record found for this user.'}, status=400)
        requester_type = 'dealer'

    whitelist_req = WhitelistRequest.objects.create(
        request_type=request_type,
        esim_provider=provider,
        requested_by=user,
        requester_type=requester_type,
        manufacturer=manufacturer,
        dealer=dealer,
        status='pending',
        requester_remarks=data.get('requester_remarks', ''),
    )
    whitelist_req.device_stocks.set(selected)

    for entry in entries_data:
        WhitelistEntry.objects.create(
            request=whitelist_req,
            whitelist_type=entry['whitelist_type'],
            value=str(entry['value']).strip(),
        )

    return Response(
        {'message': 'Whitelist request created.', 'request': _serialize_request(whitelist_req)},
        status=201,
    )


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def list_whitelist_requests(request):
    """
    List own whitelist requests.

    Query params (all optional):
      status       – pending | approved | denied
      request_type – add | remove
    """
    user = request.user
    role = getattr(user, 'role', None)
    if role not in _REQUESTER_ROLES:
        return Response({'error': 'Only manufacturers and dealers can access this endpoint.'}, status=403)

    qs = (
        WhitelistRequest.objects
        .filter(requested_by=user)
        .select_related('requested_by', 'esim_provider', 'manufacturer', 'dealer')
        .prefetch_related('entries', 'device_stocks')
    )

    if s := request.query_params.get('status'):
        qs = qs.filter(status=s)
    if t := request.query_params.get('request_type'):
        qs = qs.filter(request_type=t)

    return Response({'requests': [_serialize_request(r) for r in qs], 'count': qs.count()})


# ---------------------------------------------------------------------------
# eSimProvider endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def esim_list_whitelist_requests(request):
    """
    List whitelist requests directed to the logged-in eSimProvider.

    Query params (all optional):
      status       – pending | approved | denied
      request_type – add | remove
    """
    user = request.user
    if getattr(user, 'role', None) != _ESIM_ROLE:
        return Response({'error': 'Only eSimProvider users can access this endpoint.'}, status=403)

    provider = _get_esim_provider(user)
    if not provider:
        return Response({'error': 'No eSimProvider record found for this user.'}, status=400)

    qs = (
        WhitelistRequest.objects
        .filter(esim_provider=provider)
        .select_related('requested_by', 'esim_provider', 'manufacturer', 'dealer')
        .prefetch_related('entries', 'device_stocks')
    )

    if s := request.query_params.get('status'):
        qs = qs.filter(status=s)
    if t := request.query_params.get('request_type'):
        qs = qs.filter(request_type=t)

    return Response({'requests': [_serialize_request(r) for r in qs], 'count': qs.count()})


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def approve_whitelist_request(request, pk):
    """
    Approve a pending whitelist request.
    Automatically creates/reactivates ActiveWhitelist entries (add) or
    deactivates them (remove).

    Body (JSON, optional):
      reason – str
    """
    user = request.user
    if getattr(user, 'role', None) != _ESIM_ROLE:
        return Response({'error': 'Only eSimProvider users can approve requests.'}, status=403)

    provider = _get_esim_provider(user)
    if not provider:
        return Response({'error': 'No eSimProvider record found for this user.'}, status=400)

    try:
        whitelist_req = WhitelistRequest.objects.get(id=pk, esim_provider=provider)
    except WhitelistRequest.DoesNotExist:
        return Response({'error': 'Whitelist request not found or not directed to your provider.'}, status=404)

    if whitelist_req.status != 'pending':
        return Response({'error': 'Only pending requests can be approved.'}, status=400)

    if hasattr(whitelist_req, 'review'):
        return Response({'error': 'This request has already been reviewed.'}, status=400)

    WhitelistRequestReview.objects.create(
        request=whitelist_req,
        reviewed_by=user,
        esim_provider=provider,
        action='approved',
        reason=request.data.get('reason', ''),
    )
    whitelist_req.status = 'approved'
    whitelist_req.save(update_fields=['status', 'updated_at'])

    entries = list(whitelist_req.entries.all())
    stocks = list(whitelist_req.device_stocks.all())

    if whitelist_req.request_type == 'add':
        for stock in stocks:
            for entry in entries:
                obj, created = ActiveWhitelist.objects.get_or_create(
                    device_stock=stock,
                    esim_provider=provider,
                    whitelist_type=entry.whitelist_type,
                    value=entry.value,
                    defaults={'source_request': whitelist_req, 'is_active': True},
                )
                if not created and not obj.is_active:
                    obj.is_active = True
                    obj.deactivated_at = None
                    obj.source_request = whitelist_req
                    obj.save(update_fields=['is_active', 'deactivated_at', 'source_request'])

    elif whitelist_req.request_type == 'remove':
        now = timezone.now()
        for stock in stocks:
            for entry in entries:
                ActiveWhitelist.objects.filter(
                    device_stock=stock,
                    esim_provider=provider,
                    whitelist_type=entry.whitelist_type,
                    value=entry.value,
                    is_active=True,
                ).update(is_active=False, deactivated_at=now)

    return Response({'message': 'Request approved.', 'request': _serialize_request(whitelist_req)})


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def deny_whitelist_request(request, pk):
    """
    Deny a pending whitelist request.

    Body (JSON):
      reason – str (required)
    """
    user = request.user
    if getattr(user, 'role', None) != _ESIM_ROLE:
        return Response({'error': 'Only eSimProvider users can deny requests.'}, status=403)

    provider = _get_esim_provider(user)
    if not provider:
        return Response({'error': 'No eSimProvider record found for this user.'}, status=400)

    try:
        whitelist_req = WhitelistRequest.objects.get(id=pk, esim_provider=provider)
    except WhitelistRequest.DoesNotExist:
        return Response({'error': 'Whitelist request not found or not directed to your provider.'}, status=404)

    if whitelist_req.status != 'pending':
        return Response({'error': 'Only pending requests can be denied.'}, status=400)

    if hasattr(whitelist_req, 'review'):
        return Response({'error': 'This request has already been reviewed.'}, status=400)

    reason = str(request.data.get('reason', '')).strip()
    if not reason:
        return Response({'error': 'A reason is required when denying a request.'}, status=400)

    WhitelistRequestReview.objects.create(
        request=whitelist_req,
        reviewed_by=user,
        esim_provider=provider,
        action='denied',
        reason=reason,
    )
    whitelist_req.status = 'denied'
    whitelist_req.save(update_fields=['status', 'updated_at'])

    return Response({'message': 'Request denied.', 'request': _serialize_request(whitelist_req)})


# ---------------------------------------------------------------------------
# Shared endpoint — active whitelist
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def list_active_whitelist(request):
    """
    List currently active whitelist entries scoped to the user's access level.

    - Manufacturer: all active entries on their device stocks (across all dealers)
    - Dealer: active entries on their assigned device stocks
    - eSimProvider: all active entries managed by their provider
    - superadmin / stateadmin: all entries

    Query params (all optional):
      whitelist_type  – ip | url | phone | apn
      device_stock_id – int
      esim_provider_id – int
    """
    user = request.user
    role = getattr(user, 'role', None)

    if role not in _ALL_ALLOWED_ROLES:
        return Response({'error': 'Access denied.'}, status=403)

    qs = ActiveWhitelist.objects.select_related('device_stock', 'esim_provider').filter(is_active=True)

    if role == 'devicemanufacture':
        mfr = _get_manufacturer(user)
        if not mfr:
            return Response({'error': 'No manufacturer record found for this user.'}, status=400)
        qs = qs.filter(device_stock__dealer__manufacturer=mfr)

    elif role == 'dealer':
        dealer = _get_dealer(user)
        if not dealer:
            return Response({'error': 'No dealer record found for this user.'}, status=400)
        qs = qs.filter(device_stock__dealer=dealer)

    elif role == _ESIM_ROLE:
        provider = _get_esim_provider(user)
        if not provider:
            return Response({'error': 'No eSimProvider record found for this user.'}, status=400)
        qs = qs.filter(esim_provider=provider)

    # superadmin / stateadmin see everything — no additional filter

    if wl_type := request.query_params.get('whitelist_type'):
        qs = qs.filter(whitelist_type=wl_type)
    if stock_id := request.query_params.get('device_stock_id'):
        qs = qs.filter(device_stock_id=stock_id)
    if esim_id := request.query_params.get('esim_provider_id'):
        qs = qs.filter(esim_provider_id=esim_id)

    page_qs, pagination = _paginate(qs, request.query_params)

    data = [
        {
            'id': w.id,
            'device_stock_id': w.device_stock_id,
            'device_esn': w.device_stock.device_esn,
            'esim_provider_id': w.esim_provider_id,
            'esim_provider_name': w.esim_provider.company_name if w.esim_provider_id else '',
            'whitelist_type': w.whitelist_type,
            'value': w.value,
            'source_request_id': w.source_request_id,
            'activated_at': w.activated_at,
        }
        for w in page_qs
    ]
    return Response({'active_whitelists': data, **pagination})


# ===========================================================================
# Device Dashboard, KYC Update, and Device Detail
# ===========================================================================

# Valid DeviceStock STATUS_CHOICES values (mirrors model)
_VALID_ACTIVATION_STATUSES = {
    'NotAssigned', 'In_transit_to_dealer', 'Available_for_fitting', 'Fitted',
    'ESIM_Active_Req_Sent', 'ESIM_Active_Confirmed', 'ESIM_Active_Rejected',
    'IP_PORT_Configured', 'SOS_GATEWAY_NO_Configured', 'SMS_GATEWAY_NO_Configured',
    'Device_Defective', 'Returned_to_manufacturer', 'Device_Untagged',
}

# Maps sort_by query param → ORM field name
_SORT_FIELDS = {
    'imei':          'imei',
    'esn':           'device_esn',
    'iccid':         'iccid',
    'esim_status':   'esim_status',
    'stock_status':  'stock_status',
    'kyc_status':    'kyc_status',
    'kyc_updated':   'kyc_updated_at',
    'created':       'created',
    'assigned':      'assigned',
    'esim_validity': 'esim_validity',
}


def _get_scoped_stock_qs(user):
    """
    Return (queryset, None) scoped to the user's access level,
    or (None, Response) on access/config error.
    """
    role = getattr(user, 'role', None)
    if role == 'devicemanufacture':
        mfr = _get_manufacturer(user)
        if not mfr:
            return None, Response({'error': 'No manufacturer record found for this user.'}, status=400)
        return DeviceStock.objects.filter(dealer__manufacturer=mfr).exclude(stock_status='Deleted'), None
    if role == 'dealer':
        dealer = _get_dealer(user)
        if not dealer:
            return None, Response({'error': 'No dealer record found for this user.'}, status=400)
        return DeviceStock.objects.filter(dealer=dealer).exclude(stock_status='Deleted'), None
    if role == _ESIM_ROLE:
        provider = _get_esim_provider(user)
        if not provider:
            return None, Response({'error': 'No eSimProvider record found for this user.'}, status=400)
        return DeviceStock.objects.filter(esim_provider=provider).exclude(stock_status='Deleted'), None
    if role in _ADMIN_ROLES:
        return DeviceStock.objects.exclude(stock_status='Deleted'), None
    return None, Response({'error': 'Access denied.'}, status=403)


def _paginate(qs, params):
    """Return (page_slice, pagination_meta)."""
    try:
        page = max(1, int(params.get('page', 1)))
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page, page_size = 1, 20
    total = qs.count()
    start = (page - 1) * page_size
    return qs[start:start + page_size], {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': max(1, (total + page_size - 1) // page_size),
    }


def _group_whitelists(active_wl_qs):
    """Group active whitelist entries by type for a device."""
    grouped = {'ip': [], 'url': [], 'phone': [], 'apn': []}
    for w in active_wl_qs:
        grouped.setdefault(w.whitelist_type, []).append({
            'id': w.id,
            'value': w.value,
            'source_request_id': w.source_request_id,
            'activated_at': w.activated_at,
        })
    return grouped


def _serialize_stock(stock, include_logs=False):
    """Serialize a DeviceStock instance with KYC, whitelist, and optional activation log."""
    # eSIM providers
    providers = [
        {'id': p.id, 'name': p.company_name}
        for p in stock.esim_provider.all()
    ]

    # Active whitelists (already prefetched as stock.prefetched_whitelists)
    wl_qs = getattr(stock, 'prefetched_whitelists', stock.active_whitelists.filter(is_active=True))
    whitelist = _group_whitelists(wl_qs)

    # Dealer / manufacturer info
    dealer_id = stock.dealer_id
    dealer_name = stock.dealer.company_name if stock.dealer_id else ''
    mfr_id = stock.dealer.manufacturer_id if stock.dealer_id else None
    mfr_name = stock.dealer.manufacturer.company_name if (stock.dealer_id and stock.dealer.manufacturer_id) else ''

    data = {
        'id': stock.id,
        'device_esn': stock.device_esn,
        'imei': stock.imei,
        'iccid': stock.iccid,
        'iccid2': stock.iccid2,
        'msisdn1': stock.msisdn1,
        'msisdn2': stock.msisdn2,
        'telecom_provider1': stock.telecom_provider1,
        'telecom_provider2': stock.telecom_provider2,
        'esim_status': stock.esim_status,
        'stock_status': stock.stock_status,
        'esim_validity': stock.esim_validity,
        'created': stock.created,
        'assigned': stock.assigned,
        'dealer_id': dealer_id,
        'dealer_name': dealer_name,
        'manufacturer_id': mfr_id,
        'manufacturer_name': mfr_name,
        'esim_providers': providers,
        # KYC
        'kyc_status': stock.kyc_status,
        'last_kyc_date': stock.last_kyc_date,
        'kyc_updated_at': stock.kyc_updated_at,
        'kyc_updated_by_id': stock.kyc_updated_by_id,
        'kyc_updated_by_name': getattr(stock.kyc_updated_by, 'name', '') if stock.kyc_updated_by_id else '',
        'kyc_remarks': stock.kyc_remarks,
        # Whitelist summary
        'active_whitelist_count': sum(len(v) for v in whitelist.values()),
        'active_whitelists': whitelist,
    }

    if include_logs:
        logs_qs = getattr(stock, 'prefetched_logs', stock.activation_logs.all())
        data['activation_logs'] = [
            {
                'id': log.id,
                'status': log.status,
                'changed_by_id': log.changed_by_id,
                'changed_by_name': getattr(log.changed_by, 'name', '') if log.changed_by_id else '',
                'esim_provider_id': log.esim_provider_id,
                'changed_at': log.changed_at,
                'remarks': log.remarks,
            }
            for log in logs_qs
        ]

    return data


# ---------------------------------------------------------------------------
# 1. KYC Update (eSimProvider)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_device_kyc(request, pk):
    """
    M2M provider updates KYC status and/or logs a new activation status for a device.

    Body (JSON) — at least one of the two groups must be present:

    KYC group (all optional individually):
      kyc_status            – "active" | "inactive"
      last_kyc_date         – ISO 8601 datetime
      kyc_remarks           – str

    Activation log group (optional):
      new_activation_status – one of the DeviceStock STATUS_CHOICES values
      activation_remarks    – str (optional note for the log)
    """
    user = request.user
    if getattr(user, 'role', None) != _ESIM_ROLE:
        return Response({'error': 'Only eSimProvider users can update KYC status.'}, status=403)

    provider = _get_esim_provider(user)
    if not provider:
        return Response({'error': 'No eSimProvider record found for this user.'}, status=400)

    try:
        stock = DeviceStock.objects.select_related('kyc_updated_by').get(id=pk, esim_provider=provider)
    except DeviceStock.DoesNotExist:
        return Response({'error': 'Device stock not found or not linked to your provider.'}, status=404)

    data = request.data
    kyc_status          = data.get('kyc_status')
    last_kyc_date       = data.get('last_kyc_date')
    kyc_remarks         = data.get('kyc_remarks')
    new_activation_status = data.get('new_activation_status')
    activation_remarks  = data.get('activation_remarks', '')

    has_kyc_update = any(v is not None for v in [kyc_status, last_kyc_date, kyc_remarks])
    has_activation = new_activation_status is not None

    if not has_kyc_update and not has_activation:
        return Response({'error': 'Provide at least one of: kyc_status, last_kyc_date, kyc_remarks, new_activation_status.'}, status=400)

    kyc_fields_changed = []

    if has_kyc_update:
        if kyc_status is not None:
            if kyc_status not in ('active', 'inactive'):
                return Response({'error': 'kyc_status must be "active" or "inactive".'}, status=400)
            stock.kyc_status = kyc_status
            kyc_fields_changed.append('kyc_status')

        if last_kyc_date is not None:
            stock.last_kyc_date = last_kyc_date
            kyc_fields_changed.append('last_kyc_date')

        if kyc_remarks is not None:
            stock.kyc_remarks = kyc_remarks
            kyc_fields_changed.append('kyc_remarks')

        stock.kyc_updated_by = user
        stock.kyc_updated_at = timezone.now()
        kyc_fields_changed += ['kyc_updated_by', 'kyc_updated_at']
        stock.save(update_fields=kyc_fields_changed)

    activation_log = None
    if has_activation:
        if new_activation_status not in _VALID_ACTIVATION_STATUSES:
            return Response(
                {'error': f'Invalid new_activation_status. Valid values: {sorted(_VALID_ACTIVATION_STATUSES)}'},
                status=400,
            )
        # Update esim_status on the device and log the change
        stock.esim_status = new_activation_status
        stock.save(update_fields=['esim_status'])

        activation_log = DeviceActivationLog.objects.create(
            device_stock=stock,
            esim_provider=provider,
            status=new_activation_status,
            changed_by=user,
            remarks=activation_remarks,
        )

    # Refresh for serialization
    stock.refresh_from_db()
    response_data = {
        'message': 'Device updated successfully.',
        'device': _serialize_stock(stock, include_logs=False),
    }
    if activation_log:
        response_data['activation_log_created'] = {
            'id': activation_log.id,
            'status': activation_log.status,
            'changed_at': activation_log.changed_at,
        }
    return Response(response_data)


# ---------------------------------------------------------------------------
# 2. Device Dashboard — paginated, filterable, sortable
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def device_dashboard(request):
    """
    Paginated device list with activation status, KYC status, and whitelist summary.
    Results are scoped to the caller's access level.

    Query params:
      Filters:
        imei             – partial match
        esn              – partial match
        iccid            – partial match
        msisdn           – partial match on msisdn1 or msisdn2
        esim_status      – exact match
        stock_status     – exact match
        kyc_status       – exact match (active | inactive)
        esim_provider_id – exact match

      Sorting:
        sort_by    – imei | esn | iccid | esim_status | stock_status |
                     kyc_status | kyc_updated | created | assigned | esim_validity
        sort_order – asc | desc  (default: desc)

      Pagination:
        page       – default 1
        page_size  – default 20, max 100
    """
    user = request.user
    qs, err = _get_scoped_stock_qs(user)
    if err:
        return err

    p = request.query_params

    # --- Filters ---
    if imei := p.get('imei'):
        qs = qs.filter(imei__icontains=imei)
    if esn := p.get('esn'):
        qs = qs.filter(device_esn__icontains=esn)
    if iccid := p.get('iccid'):
        qs = qs.filter(iccid__icontains=iccid)
    if msisdn := p.get('msisdn'):
        from django.db.models import Q
        qs = qs.filter(Q(msisdn1__icontains=msisdn) | Q(msisdn2__icontains=msisdn))
    if esim_status := p.get('esim_status'):
        qs = qs.filter(esim_status=esim_status)
    if stock_status := p.get('stock_status'):
        qs = qs.filter(stock_status=stock_status)
    if kyc_status := p.get('kyc_status'):
        qs = qs.filter(kyc_status=kyc_status)
    if esim_pid := p.get('esim_provider_id'):
        qs = qs.filter(esim_provider__id=esim_pid)

    # --- Sorting ---
    sort_by = _SORT_FIELDS.get(p.get('sort_by', ''), 'created')
    if p.get('sort_order', 'desc').lower() == 'asc':
        qs = qs.order_by(sort_by)
    else:
        qs = qs.order_by(f'-{sort_by}')

    # --- Eager loading ---
    qs = qs.select_related(
        'model', 'dealer', 'dealer__manufacturer', 'kyc_updated_by',
    ).prefetch_related(
        'esim_provider',
        Prefetch(
            'active_whitelists',
            queryset=ActiveWhitelist.objects.filter(is_active=True),
            to_attr='prefetched_whitelists',
        ),
    )

    page_qs, meta = _paginate(qs, p)

    results = []
    for stock in page_qs:
        results.append(_serialize_stock(stock, include_logs=False))

    return Response({'pagination': meta, 'devices': results})


# ---------------------------------------------------------------------------
# 3. Single Device Detail
# ---------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def device_detail(request, pk):
    """
    Full detail for a single device: activation status, KYC, whitelists,
    full activation log history, and all whitelist requests for this device.
    Access is scoped to the caller's role.
    """
    user = request.user
    qs, err = _get_scoped_stock_qs(user)
    if err:
        return err

    try:
        stock = (
            qs
            .select_related('model', 'dealer', 'dealer__manufacturer', 'kyc_updated_by')
            .prefetch_related(
                'esim_provider',
                Prefetch(
                    'active_whitelists',
                    queryset=ActiveWhitelist.objects.filter(is_active=True).select_related('esim_provider'),
                    to_attr='prefetched_whitelists',
                ),
                Prefetch(
                    'activation_logs',
                    queryset=DeviceActivationLog.objects.select_related('changed_by', 'esim_provider'),
                    to_attr='prefetched_logs',
                ),
            )
            .get(id=pk)
        )
    except DeviceStock.DoesNotExist:
        return Response({'error': 'Device not found or not accessible.'}, status=404)

    # Full whitelist request history for this device
    wl_requests = (
        WhitelistRequest.objects
        .filter(device_stocks=stock)
        .select_related('requested_by', 'esim_provider')
        .prefetch_related('entries')
        .order_by('-created_at')
    )
    wl_request_list = [
        {
            'id': r.id,
            'request_type': r.request_type,
            'status': r.status,
            'requester_type': r.requester_type,
            'requested_by_name': getattr(r.requested_by, 'name', ''),
            'esim_provider_name': r.esim_provider.company_name if r.esim_provider_id else '',
            'entries': list(r.entries.values('whitelist_type', 'value')),
            'created_at': r.created_at,
        }
        for r in wl_requests
    ]

    device_data = _serialize_stock(stock, include_logs=True)
    device_data['whitelist_request_history'] = wl_request_list

    return Response({'device': device_data})
