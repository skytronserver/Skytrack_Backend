"""
SMS to devices over Airtel SMPP, sent from our VMN by the smpp_worker container
(management/commands/smpp_worker.py). Separate from the OTP gateway (sms_send)
and from the sms_out phone queue.

    POST /api/smpp/send/              superadmin: queue one SMS
    GET  /api/smpp/sms/list/          superadmin: sent SMS with status and receipts
    GET  /api/smpp/incoming/list/     superadmin: SMS received on the VMN
    GET  /api/smpp/status/            superadmin: worker bind state + queue counts

Other code queues an SMS with queue_smpp_sms(); the worker picks it up within
about half a second.
"""
import logging
import math
import os
import re

from django.core.cache import cache
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .ble_sos_app_log_views import _Invalid, _date_param, _err, _int_param
from .models import DeviceStock, SmppSmsIn, SmppSmsOut

logger = logging.getLogger(__name__)

HEARTBEAT_KEY = 'smpp:worker:status'     # written by smpp_worker
MAX_TEXT_LEN = 1000
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
COUNTRY_CODE = os.environ.get('SMPP_DEFAULT_COUNTRY_CODE', '91')


class SmppNumberError(ValueError):
    pass


def normalise_number(raw):
    """Digits only; a 10-digit mobile number gets the country code. M2M numbers are kept as they are."""
    number = re.sub(r'[\s()-]', '', str(raw or '')).lstrip('+')
    if not re.fullmatch(r'\d{10,15}', number):
        raise SmppNumberError('Number must be 10 to 15 digits.')
    return COUNTRY_CODE + number if len(number) == 10 else number


def queue_smpp_sms(dest_no, text, imei='', user=None):
    """Queue one SMS for the SMPP worker. Raises SmppNumberError for a bad number."""
    return SmppSmsOut.objects.create(dest_no=normalise_number(dest_no), text=text,
                                     imei=imei or '', sent_by=user)


def _superadmin_only(request):
    if getattr(request.user, 'role', None) != 'superadmin':
        return _err('Only superadmin can access this.', status.HTTP_403_FORBIDDEN)
    return None


def _page(request, qs, row):
    page = _int_param(request, 'page', 1, 1, 100000)
    page_size = _int_param(request, 'page_size', DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)
    total = qs.count()
    start = (page - 1) * page_size
    return Response({
        'status': 'success',
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total else 0,
        },
        'data': [row(obj) for obj in qs[start:start + page_size]],
    })


# --------------------------------------------------------------------------
# POST /api/smpp/send/
# --------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def smpp_send(request):
    """POST /api/smpp/send/
    {"dest_no": "5754xxxxxxxxx", "text": "@GET,IP*"}   or   {"imei": "86026...", "text": "..."}
    With imei and no dest_no, the SMS goes to that device's msisdn1.
    """
    denied = _superadmin_only(request)
    if denied:
        return denied

    text = request.data.get('text')
    if not isinstance(text, str) or not text:
        return _err('text is required.', status.HTTP_400_BAD_REQUEST)
    if len(text) > MAX_TEXT_LEN:
        return _err(f'text must be at most {MAX_TEXT_LEN} characters.', status.HTTP_400_BAD_REQUEST)

    imei = str(request.data.get('imei') or '').strip()
    if imei and not re.fullmatch(r'\d{1,20}', imei):
        return _err('imei must be digits.', status.HTTP_400_BAD_REQUEST)
    dest_no = request.data.get('dest_no')
    if not dest_no:
        if not imei:
            return _err('dest_no or imei is required.', status.HTTP_400_BAD_REQUEST)
        stock = DeviceStock.objects.filter(imei=imei).first()
        dest_no = stock.msisdn1 if stock else None
        if not dest_no:
            return _err(f'No SMS number (msisdn1) found for imei {imei}.', status.HTTP_400_BAD_REQUEST)

    try:
        sms = queue_smpp_sms(dest_no, text, imei=imei, user=request.user)
    except SmppNumberError as e:
        return _err(f'dest_no: {e}', status.HTTP_400_BAD_REQUEST)
    return Response({'status': 'success', 'message': 'SMS queued.', 'data': _out_row(sms)},
                    status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------
# GET /api/smpp/sms/list/
# --------------------------------------------------------------------------

def _out_row(sms, parts=None):
    return {
        'id': sms.id,
        'dest_no': sms.dest_no,
        'imei': sms.imei,
        'text': sms.text,
        'status': sms.status,
        'error': sms.error,
        'parts_total': sms.parts_total,
        'attempts': sms.attempts,
        'next_attempt_at': sms.next_attempt_at,
        'sent_by': sms.sent_by_id,
        'created_at': sms.created_at,
        'submitted_at': sms.submitted_at,
        'final_at': sms.final_at,
        'parts': [{
            'part_no': p.part_no,
            'message_id': p.message_id,
            'dlr_stat': p.dlr_stat,
            'dlr_err': p.dlr_err,
            'dlr_text': p.dlr_text,
            'submitted_at': p.submitted_at,
            'dlr_at': p.dlr_at,
        } for p in (parts if parts is not None else [])],
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def smpp_sms_list(request):
    """GET /api/smpp/sms/list/
        ?status=delivered &dest_no=5754 &imei=8602 &date_from=2026-10-01 &date_to=2026-10-29
        &search=... &page=1 &page_size=50
    Newest first; dest_no and imei are partial matches; dates filter on created_at.
    """
    denied = _superadmin_only(request)
    if denied:
        return denied

    p = request.GET
    qs = SmppSmsOut.objects.all()
    status_filter = (p.get('status') or '').strip()
    if status_filter:
        valid = {choice for choice, _ in SmppSmsOut.STATUS_CHOICES}
        if status_filter not in valid:
            return _err(f"status must be one of: {', '.join(sorted(valid))}.", status.HTTP_400_BAD_REQUEST)
        qs = qs.filter(status=status_filter)
    for field in ('dest_no', 'imei'):
        value = (p.get(field) or '').strip().lstrip('+')
        if value:
            qs = qs.filter(**{f'{field}__icontains': value})
    search = (p.get('search') or '').strip()[:100]
    if search:
        qs = qs.filter(Q(text__icontains=search) | Q(dest_no__icontains=search) | Q(imei__icontains=search))
    try:
        date_from = _date_param(request, 'date_from')
        date_to = _date_param(request, 'date_to', end_of_day=True)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        return _page(request, qs.order_by('-id').prefetch_related('parts'),
                     lambda sms: _out_row(sms, sorted(sms.parts.all(), key=lambda part: part.part_no)))
    except _Invalid as e:
        return _err(str(e), status.HTTP_400_BAD_REQUEST)


# --------------------------------------------------------------------------
# GET /api/smpp/incoming/list/
# --------------------------------------------------------------------------

def _in_row(sms):
    return {
        'id': sms.id,
        'source_no': sms.source_no,
        'dest_no': sms.dest_no,
        'text': sms.text,
        'data_coding': sms.data_coding,
        'esm_class': sms.esm_class,
        'raw_hex': sms.raw_hex,
        'received_at': sms.received_at,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def smpp_incoming_list(request):
    """GET /api/smpp/incoming/list/
        ?source_no=5754 &date_from=2026-10-01 &date_to=2026-10-29 &search=... &page=1 &page_size=50
    Newest first. The text is stored as received; show it as plain text.
    """
    denied = _superadmin_only(request)
    if denied:
        return denied

    p = request.GET
    qs = SmppSmsIn.objects.all()
    source = (p.get('source_no') or '').strip().lstrip('+')
    if source:
        qs = qs.filter(source_no__icontains=source)
    search = (p.get('search') or '').strip()[:100]
    if search:
        qs = qs.filter(Q(text__icontains=search) | Q(source_no__icontains=search))
    try:
        date_from = _date_param(request, 'date_from')
        date_to = _date_param(request, 'date_to', end_of_day=True)
        if date_from:
            qs = qs.filter(received_at__gte=date_from)
        if date_to:
            qs = qs.filter(received_at__lte=date_to)
        return _page(request, qs.order_by('-id'), _in_row)
    except _Invalid as e:
        return _err(str(e), status.HTTP_400_BAD_REQUEST)


# --------------------------------------------------------------------------
# GET /api/smpp/status/
# --------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def smpp_status(request):
    """GET /api/smpp/status/  worker state (from its heartbeat) and SMS counts by status."""
    denied = _superadmin_only(request)
    if denied:
        return denied

    try:
        worker = cache.get(HEARTBEAT_KEY)
    except Exception as e:
        logger.warning(f"SMPP status: cache unavailable: {e}")
        worker = None
    counts = {row['status']: row['n'] for row in
              SmppSmsOut.objects.order_by().values('status').annotate(n=Count('id'))}
    return Response({
        'status': 'success',
        'worker': worker or {'state': 'down', 'message': 'No heartbeat from the SMPP worker in the last minute.'},
        'counts': {choice: counts.get(choice, 0) for choice, _ in SmppSmsOut.STATUS_CHOICES},
    })
