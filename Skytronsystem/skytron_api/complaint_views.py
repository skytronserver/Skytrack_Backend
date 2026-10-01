"""
Complaint Management System — API views.

Endpoints
---------
POST   /api/complaint/create/                    – Create ticket (anon or authenticated)
GET    /api/complaint/list/                      – List all tickets (staff + manufacturer roles)
GET    /api/complaint/device-imei/               – Search DeviceStock by IMEI (staff roles)
GET    /api/complaint/<int:pk>/                  – Ticket detail (staff + manufacturer roles)
PATCH  /api/complaint/<int:pk>/update-status/    – Change ticket status (staff roles)
PATCH  /api/complaint/<int:pk>/escalate/         – Escalate ticket (staff roles)
POST   /api/complaint/<int:pk>/final-report/     – Upload final report + text (staff roles)
POST   /api/complaint/<int:pk>/comment/          – Add comment to audit trail (staff roles)
GET    /api/complaint/<int:pk>/activity/         – Full activity log (staff + manufacturer roles)
GET    /api/complaint/track/<str:ticket_ref>/    – Public status lookup (no auth)
"""

import re
import secrets

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .jwt_authentication import JWTAuthentication
from .throttles import ComplaintCreateRateThrottle, ComplaintCreateDailyThrottle
from .models import ComplaintTicket, DeviceStock, Manufacturer, TicketActivity, TicketAttachment

# Roles that may view and manage tickets (internal staff)
_STAFF_ROLES = {'helpdesk', 'teamleader', 'sosexecutive', 'sosadmin', 'stateadmin', 'superadmin'}

# Manufacturer role code — can only see tickets explicitly escalated to their manufacturer
_MANUFACTURER_ROLE = 'devicemanufacture'

# All roles that have any access to complaint APIs
_ALL_ALLOWED_ROLES = _STAFF_ROLES | {_MANUFACTURER_ROLE}

# Roles that can see all tickets (not scoped to escalation target)
_ELEVATED_ROLES = {'teamleader', 'sosexecutive', 'stateadmin', 'superadmin'}

ALLOWED_TRANSITIONS = {
    ComplaintTicket.STATUS_CREATED:   {ComplaintTicket.STATUS_IN_REVIEW, ComplaintTicket.STATUS_CANCELED},
    ComplaintTicket.STATUS_IN_REVIEW: {ComplaintTicket.STATUS_PENDING, ComplaintTicket.STATUS_CLOSED, ComplaintTicket.STATUS_CANCELED},
    ComplaintTicket.STATUS_PENDING:   {ComplaintTicket.STATUS_IN_REVIEW, ComplaintTicket.STATUS_CLOSED, ComplaintTicket.STATUS_CANCELED},
    ComplaintTicket.STATUS_CLOSED:    set(),
    ComplaintTicket.STATUS_CANCELED:  set(),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_staff(user):
    return hasattr(user, 'role') and user.role in _STAFF_ROLES


def _is_manufacturer(user):
    return hasattr(user, 'role') and user.role == _MANUFACTURER_ROLE


def _has_complaint_access(user):
    return hasattr(user, 'role') and user.role in _ALL_ALLOWED_ROLES


def _actor_name(user):
    if user and not user.is_anonymous:
        return getattr(user, 'name', '') or user.email
    return 'Anonymous'


def _log(ticket, actor, action_type, old_value=None, new_value=None, comment=None):
    TicketActivity.objects.create(
        ticket=ticket,
        actor=actor if (actor and not actor.is_anonymous) else None,
        actor_name=_actor_name(actor),
        action_type=action_type,
        old_value=old_value,
        new_value=new_value,
        comment=comment,
    )


def _save_attachment(request, tag, ticket, uploader):
    """Upload one file from request.FILES[tag] to MinIO and return a TicketAttachment, or None."""
    uploaded_file = request.FILES.get(tag)
    if not uploaded_file:
        return None

    import magic

    max_size = 10 * 1024 * 1024  # 10 MB
    if uploaded_file.size > max_size:
        return None

    valid_mime_types = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'application/pdf': 'pdf',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    }

    try:
        m = magic.Magic(mime=True)
        mime_type = m.from_buffer(uploaded_file.read(2048) or b'')
    except Exception:
        return None
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

    if mime_type not in valid_mime_types:
        return None

    uploaded_file.seek(0)
    header = uploaded_file.read(2048)
    if (
        header.startswith(b'MZ')
        or header.startswith(b'\x7FELF')
        or header.startswith(b'\xcf\xfa\xed\xfe')
        or header.startswith(b'\xce\xfa\xed\xfe')
        or header.startswith(b'\xca\xfe\xba\xbe')
        or header.startswith(b'#!')
    ):
        return None

    ext = valid_mime_types[mime_type]
    rand_name = secrets.token_hex(20) + '.' + ext
    object_key = f'fileuploads/complaints/{rand_name}'

    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    try:
        from . import minio_storage
        minio_storage.upload_bytes(object_key, file_bytes, mime_type)
    except Exception:
        return None

    return TicketAttachment.objects.create(
        ticket=ticket,
        file_path=object_key,
        file_name=uploaded_file.name or rand_name,
        uploaded_by=uploader if (uploader and not uploader.is_anonymous) else None,
    )


def _serialize_ticket(ticket, include_activities=False):
    attachments = [
        {
            'id': a.id,
            'file_name': a.file_name,
            'file_path': a.file_path,
            'uploaded_at': a.uploaded_at,
        }
        for a in ticket.attachments.all()
    ]

    manufacturer_info = None
    if ticket.escalated_to_manufacturer_id:
        try:
            mfr = ticket.escalated_to_manufacturer
            manufacturer_info = {
                'id': mfr.id,
                'company_name': mfr.company_name,
            }
        except Exception:
            manufacturer_info = {'id': ticket.escalated_to_manufacturer_id}

    device_stock_info = None
    if ticket.device_stock_id:
        try:
            ds = ticket.device_stock
            device_stock_info = {
                'id': ds.id,
                'imei': ds.imei,
                'device_esn': ds.device_esn,
                'model_name': ds.model.model_name if ds.model_id else None,
            }
        except Exception:
            device_stock_info = {'id': ticket.device_stock_id}

    data = {
        'id': ticket.id,
        'ticket_ref': ticket.ticket_ref,
        'applicant_name': ticket.applicant_name,
        'applicant_phone': ticket.applicant_phone,
        'applicant_email': ticket.applicant_email,
        'title': ticket.title,
        'details': ticket.details,
        'status': ticket.status,
        'source': ticket.source,
        'escalated_to': ticket.escalated_to,
        'escalated_to_manufacturer': manufacturer_info,
        'device_stock': device_stock_info,
        'solution': ticket.solution,
        'final_report_file': ticket.final_report_file,
        'entry_date': ticket.entry_date,
        'created_at': ticket.created_at,
        'updated_at': ticket.updated_at,
        'created_by': ticket.created_by_id,
        'attachments': attachments,
    }
    if include_activities:
        data['activities'] = _serialize_activities(ticket)
    return data


def _serialize_activities(ticket):
    return [
        {
            'id': a.id,
            'actor_name': a.actor_name,
            'action_type': a.action_type,
            'old_value': a.old_value,
            'new_value': a.new_value,
            'comment': a.comment,
            'timestamp': a.timestamp,
        }
        for a in ticket.activities.all()
    ]


_PHONE_RE = re.compile(r'^\+?[0-9]{10,15}$')
_IMEI_RE = re.compile(r'^[0-9]{4,20}$')


def _validate_ticket_input(name, phone, email, title, details, device_imei):
    """Return a user-facing error message for invalid ticket input, else None."""
    texts = (name, phone, email or '', title, details, device_imei or '')
    if any('\x00' in t for t in texts):
        return 'Input contains invalid characters.'
    if len(name) > 255:
        return 'Applicant name must be at most 255 characters.'
    if not _PHONE_RE.match(phone):
        return 'Enter a valid phone number (10 to 15 digits).'
    if email:
        try:
            validate_email(email)
        except DjangoValidationError:
            return 'Enter a valid email address.'
        if len(email) > 254:
            return 'Email must be at most 254 characters.'
    if len(title) > 500:
        return 'Title must be at most 500 characters.'
    if len(details) > 5000:
        return 'Details must be at most 5000 characters.'
    if device_imei and not _IMEI_RE.match(device_imei):
        return 'Enter a valid device IMEI.'
    return None


def _get_manufacturer_ids_for_user(user):
    """Return list of Manufacturer PKs this user belongs to."""
    return list(Manufacturer.objects.filter(users=user).values_list('id', flat=True))


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
@throttle_classes([ComplaintCreateRateThrottle, ComplaintCreateDailyThrottle])
def create_ticket(request):
    """
    Create a complaint ticket.
    Anonymous callers must not send an Authorization header (or send one with a valid token).
    Source is inferred: authenticated helpdesk users set it via `source` field;
    all others default to public_app.
    Optional: device_imei — links the ticket to a DeviceStock record.
    """
    data = request.data

    applicant_name  = (data.get('applicant_name') or '').strip()
    applicant_phone = (data.get('applicant_phone') or '').strip()
    applicant_email = (data.get('applicant_email') or '').strip() or None
    title           = (data.get('title') or '').strip()
    details         = (data.get('details') or '').strip()
    source          = (data.get('source') or 'public_app').strip()
    device_imei     = (data.get('device_imei') or '').strip() or None

    if not applicant_name:
        return Response({'error': 'applicant_name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not applicant_phone:
        return Response({'error': 'applicant_phone is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not title:
        return Response({'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not details:
        return Response({'error': 'details is required'}, status=status.HTTP_400_BAD_REQUEST)

    input_error = _validate_ticket_input(
        applicant_name, applicant_phone, applicant_email, title, details, device_imei,
    )
    if input_error:
        return Response({'error': input_error}, status=status.HTTP_400_BAD_REQUEST)

    valid_sources = {c[0] for c in ComplaintTicket.SOURCE_CHOICES}
    if source not in valid_sources:
        source = 'public_app'

    user = request.user
    creator = user if (user and not user.is_anonymous) else None

    # Non-helpdesk authenticated users are always public_app source
    if creator and getattr(creator, 'role', '') not in _STAFF_ROLES:
        source = 'public_app'

    # Resolve device_imei → DeviceStock (only allowed for staff)
    device_stock_obj = None
    if device_imei:
        if creator and getattr(creator, 'role', '') in _STAFF_ROLES:
            try:
                device_stock_obj = DeviceStock.objects.get(imei=device_imei)
            except DeviceStock.DoesNotExist:
                return Response(
                    {'error': f'No device found with IMEI {device_imei}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # Silently ignore device_imei for non-staff callers

    ticket = ComplaintTicket.objects.create(
        applicant_name=applicant_name,
        applicant_phone=applicant_phone,
        applicant_email=applicant_email,
        title=title,
        details=details,
        source=source,
        created_by=creator,
        device_stock=device_stock_obj,
    )

    # Handle multiple file attachments: file_0, file_1, … or file (single)
    file_keys = [k for k in request.FILES if k.startswith('file')]
    for key in file_keys:
        att = _save_attachment(request, key, ticket, creator)
        if att:
            _log(ticket, creator, TicketActivity.ACTION_ATTACHMENT,
                 new_value=att.file_name)

    _log(ticket, creator, TicketActivity.ACTION_CREATED, new_value=ticket.ticket_ref)

    return Response(
        {'message': 'Ticket created successfully', 'ticket_ref': ticket.ticket_ref, 'id': ticket.id},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def list_tickets(request):
    """
    List tickets.

    Staff roles (helpdesk, teamleader, sosexecutive, stateadmin, superadmin):
      - See ALL tickets.
      - Default ordering: active tickets (created/pending) first, then newest-first overall.

    Manufacturer role (devicemanufacture):
      - Sees ONLY tickets where escalated_to='manufacturer' AND
        escalated_to_manufacturer belongs to one of their manufacturers.

    Query params:
      status            – filter by exact status value
      source            – filter by source
      escalated_to      – filter by escalation target (teamlead/sosadmin/manufacturer)
      search            – full-text search on ref/name/phone/email/title
      page              – page number (default 1)
      page_size         – results per page (default 20, max 100)
    """
    user = request.user

    if not _has_complaint_access(user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    qs = ComplaintTicket.objects.prefetch_related('attachments').select_related(
        'escalated_to_manufacturer', 'device_stock', 'device_stock__model'
    )

    # Manufacturer role: tickets escalated to them OR created by them
    if _is_manufacturer(user):
        mfr_ids = _get_manufacturer_ids_for_user(user)
        qs = qs.filter(
            Q(escalated_to='manufacturer', escalated_to_manufacturer_id__in=mfr_ids)
            | Q(created_by=user)
        )
    else:
        # Apply optional escalated_to filter for staff
        filter_escalated_to = request.GET.get('escalated_to')
        if filter_escalated_to:
            if filter_escalated_to == 'none':
                qs = qs.filter(escalated_to__isnull=True)
            else:
                qs = qs.filter(escalated_to=filter_escalated_to)

    filter_status = request.GET.get('status')
    if filter_status:
        qs = qs.filter(status=filter_status)

    filter_source = request.GET.get('source')
    if filter_source:
        qs = qs.filter(source=filter_source)

    search = (request.GET.get('search') or '').strip()
    if search:
        qs = qs.filter(
            Q(ticket_ref__icontains=search)
            | Q(applicant_name__icontains=search)
            | Q(applicant_phone__icontains=search)
            | Q(applicant_email__icontains=search)
            | Q(title__icontains=search)
        )

    # Ordering: pending/created tickets bubble up (active first), then newest-first
    qs = qs.annotate(
        _priority=Case(
            When(status__in=[ComplaintTicket.STATUS_PENDING, ComplaintTicket.STATUS_CREATED], then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by('_priority', '-created_at')

    try:
        page      = max(1, int(request.GET.get('page', 1)))
        page_size = min(100, max(1, int(request.GET.get('page_size', 20))))
    except (TypeError, ValueError):
        page, page_size = 1, 20

    total  = qs.count()
    offset = (page - 1) * page_size
    tickets = qs[offset: offset + page_size]

    return Response({
        'total': total,
        'page': page,
        'page_size': page_size,
        'results': [_serialize_ticket(t) for t in tickets],
    })


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ticket_detail(request, pk):
    """
    Full ticket detail including attachments.
    Staff roles: any ticket.
    Manufacturer role: only tickets escalated to their manufacturer.
    """
    user = request.user

    if not _has_complaint_access(user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.prefetch_related('attachments').select_related(
            'escalated_to_manufacturer', 'device_stock', 'device_stock__model'
        ).get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    if _is_manufacturer(user):
        mfr_ids = _get_manufacturer_ids_for_user(user)
        escalated_to_them = (
            ticket.escalated_to == 'manufacturer'
            and ticket.escalated_to_manufacturer_id in mfr_ids
        )
        created_by_them = ticket.created_by_id == user.pk
        if not escalated_to_them and not created_by_them:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    return Response(_serialize_ticket(ticket))


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_ticket_status(request, pk):
    """Change the status of a ticket. Enforces allowed transitions. Staff roles only."""
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    new_status = (request.data.get('status') or '').strip()
    valid = {c[0] for c in ComplaintTicket.STATUS_CHOICES}
    if new_status not in valid:
        return Response(
            {'error': f'Invalid status. Choices: {sorted(valid)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_status == ticket.status:
        return Response({'message': 'Status unchanged', 'status': ticket.status})

    allowed = ALLOWED_TRANSITIONS.get(ticket.status, set())
    if new_status not in allowed:
        return Response(
            {'error': f'Cannot move from "{ticket.status}" to "{new_status}".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    old_status = ticket.status
    ticket.status = new_status

    comment = (request.data.get('comment') or '').strip() or None
    if new_status == ComplaintTicket.STATUS_CLOSED and not ticket.solution:
        solution = (request.data.get('solution') or '').strip()
        if solution:
            ticket.solution = solution

    ticket.save()
    _log(ticket, request.user, TicketActivity.ACTION_STATUS_CHANGE,
         old_value=old_status, new_value=new_status, comment=comment)

    return Response({'message': 'Status updated', 'status': ticket.status})


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def escalate_ticket(request, pk):
    """
    Escalate a ticket to a higher level or to a manufacturer.

    Body:
      escalate_to      (required) – "teamlead" | "sosadmin" | "manufacturer"
      manufacturer_id  (required when escalate_to="manufacturer")
      comment          (optional) – reason for escalation

    Role permissions:
      helpdesk            → can escalate to teamlead, sosadmin
      teamleader          → can escalate to sosadmin, manufacturer
      sosexecutive        → can escalate to manufacturer
      stateadmin          → can escalate to any level
      superadmin          → can escalate to any level
    """
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    escalate_to = (request.data.get('escalate_to') or '').strip()
    valid_levels = {c[0] for c in ComplaintTicket.ESCALATION_CHOICES}
    if escalate_to not in valid_levels:
        return Response(
            {'error': f'Invalid escalate_to. Choices: {sorted(valid_levels)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Role-based escalation permission check
    role = getattr(request.user, 'role', '')
    role_allowed = {
        'helpdesk':     {'teamlead', 'sosadmin'},
        'teamleader':   {'sosadmin', 'manufacturer'},
        'sosexecutive': {'sosadmin', 'manufacturer'},
        'sosadmin':     valid_levels,
        'stateadmin':   valid_levels,
        'superadmin':   valid_levels,
    }
    permitted = role_allowed.get(role, set())
    if escalate_to not in permitted:
        return Response(
            {'error': f'Your role ({role}) is not permitted to escalate to "{escalate_to}".'},
            status=status.HTTP_403_FORBIDDEN,
        )

    manufacturer_obj = None
    if escalate_to == 'manufacturer':
        manufacturer_id = request.data.get('manufacturer_id')
        if not manufacturer_id:
            return Response(
                {'error': 'manufacturer_id is required when escalating to manufacturer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            manufacturer_obj = Manufacturer.objects.get(pk=int(manufacturer_id))
        except (Manufacturer.DoesNotExist, (TypeError, ValueError)):
            return Response({'error': 'Manufacturer not found.'}, status=status.HTTP_400_BAD_REQUEST)

    old_escalation = ticket.escalated_to or 'none'
    ticket.escalated_to = escalate_to
    ticket.escalated_to_manufacturer = manufacturer_obj
    ticket.save(update_fields=['escalated_to', 'escalated_to_manufacturer', 'updated_at'])

    comment = (request.data.get('comment') or '').strip() or None
    _log(
        ticket, request.user, TicketActivity.ACTION_ESCALATION,
        old_value=old_escalation,
        new_value=escalate_to + (f':{manufacturer_obj.company_name}' if manufacturer_obj else ''),
        comment=comment,
    )

    return Response({
        'message': 'Ticket escalated',
        'escalated_to': ticket.escalated_to,
        'manufacturer_id': manufacturer_obj.id if manufacturer_obj else None,
    })


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def submit_final_report(request, pk):
    """
    Submit the final report for a ticket.
    Accepts: solution (text), final_report (file), and optionally moves status to closed.
    """
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    solution = (request.data.get('solution') or '').strip()
    if solution:
        ticket.solution = solution

    file_saved = _save_attachment(request, 'final_report', ticket, request.user)
    if file_saved:
        ticket.final_report_file = file_saved.file_path
        _log(ticket, request.user, TicketActivity.ACTION_FINAL_REPORT,
             new_value=file_saved.file_name, comment=solution or None)
    elif solution:
        _log(ticket, request.user, TicketActivity.ACTION_FINAL_REPORT,
             comment=solution)
    else:
        return Response(
            {'error': 'Provide solution text and/or a final_report file.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ticket.save()
    return Response({'message': 'Final report submitted'})


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def add_comment(request, pk):
    """Add a free-text comment to the ticket audit trail."""
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    comment = (request.data.get('comment') or '').strip()
    if not comment:
        return Response({'error': 'comment is required'}, status=status.HTTP_400_BAD_REQUEST)

    _log(ticket, request.user, TicketActivity.ACTION_COMMENT, comment=comment)
    return Response({'message': 'Comment added'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def ticket_activity_log(request, pk):
    """
    Return the full activity trail for a ticket.
    Staff roles: any ticket.
    Manufacturer role: only tickets escalated to their manufacturer.
    """
    user = request.user

    if not _has_complaint_access(user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    if _is_manufacturer(user):
        mfr_ids = _get_manufacturer_ids_for_user(user)
        escalated_to_them = (
            ticket.escalated_to == 'manufacturer'
            and ticket.escalated_to_manufacturer_id in mfr_ids
        )
        created_by_them = ticket.created_by_id == user.pk
        if not escalated_to_them and not created_by_them:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    return Response({'ticket_ref': ticket.ticket_ref, 'activities': _serialize_activities(ticket)})


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def device_imei_lookup(request):
    """
    Search DeviceStock by partial IMEI for use when creating or escalating a ticket.
    Staff roles only.
    Query param: q (min 4 chars)
    Returns up to 20 matching devices.
    """
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    q = (request.GET.get('q') or '').strip()
    if len(q) < 4:
        return Response({'error': 'Query must be at least 4 characters.'}, status=status.HTTP_400_BAD_REQUEST)

    devices = (
        DeviceStock.objects
        .filter(imei__icontains=q)
        .exclude(stock_status='Deleted')
        .select_related('model')[:20]
    )

    results = []
    for ds in devices:
        results.append({
            'id': ds.id,
            'imei': ds.imei,
            'device_esn': ds.device_esn,
            'model_name': ds.model.model_name if ds.model_id else None,
            'stock_status': ds.stock_status,
        })

    return Response({'results': results})


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def public_track_ticket(request, ticket_ref):
    """
    Public endpoint: look up a ticket by reference number.
    Returns limited fields only (no internal notes or file paths).
    """
    try:
        ticket = ComplaintTicket.objects.get(ticket_ref=ticket_ref.upper())
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    public_activities = [
        {
            'action_type': a.action_type,
            'new_value': a.new_value,
            'comment': a.comment if a.action_type == TicketActivity.ACTION_COMMENT else None,
            'timestamp': a.timestamp,
        }
        for a in ticket.activities.filter(
            action_type__in=[
                TicketActivity.ACTION_CREATED,
                TicketActivity.ACTION_STATUS_CHANGE,
                TicketActivity.ACTION_COMMENT,
            ]
        )
    ]

    return Response({
        'ticket_ref': ticket.ticket_ref,
        'title': ticket.title,
        'status': ticket.status,
        'entry_date': ticket.entry_date,
        'updated_at': ticket.updated_at,
        'solution': ticket.solution,
        'activities': public_activities,
    })
