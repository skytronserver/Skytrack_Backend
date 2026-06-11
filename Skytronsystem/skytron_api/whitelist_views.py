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

from .jwt_authentication import JWTAuthentication
from .models import (
    ActiveWhitelist, Dealer, DeviceStock, Manufacturer,
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
        return DeviceStock.objects.filter(dealer__manufacturer=mfr)
    if role == 'dealer':
        dealer = _get_dealer(user)
        if not dealer:
            return DeviceStock.objects.none()
        return DeviceStock.objects.filter(dealer=dealer)
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
        for w in qs
    ]
    return Response({'active_whitelists': data, 'count': len(data)})
