"""
Complaint Management System — API views.

Endpoints
---------
POST   /api/complaint/create/                   – Create ticket (anon or authenticated)
GET    /api/complaint/list/                     – List all tickets (staff roles)
GET    /api/complaint/<int:pk>/                 – Ticket detail (staff roles)
PATCH  /api/complaint/<int:pk>/update-status/   – Change ticket status (staff roles)
POST   /api/complaint/<int:pk>/final-report/    – Upload final report + text (staff roles)
POST   /api/complaint/<int:pk>/comment/         – Add comment to audit trail (staff roles)
GET    /api/complaint/<int:pk>/activity/        – Full activity log (staff roles)
GET    /api/complaint/track/<str:ticket_ref>/   – Public status lookup (no auth)
"""

import secrets

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .jwt_authentication import JWTAuthentication
from .models import ComplaintTicket, TicketActivity, TicketAttachment

# Roles that may view and manage tickets
_STAFF_ROLES = {'helpdesk', 'teamleader', 'sosexecutive', 'stateadmin', 'superadmin'}

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


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([AllowAny])
def create_ticket(request):
    """
    Create a complaint ticket.
    Anonymous callers must not send an Authorization header (or send one with a valid token).
    Source is inferred: authenticated helpdesk users set it via `source` field;
    all others default to public_app.
    """
    data = request.data

    applicant_name  = (data.get('applicant_name') or '').strip()
    applicant_phone = (data.get('applicant_phone') or '').strip()
    applicant_email = (data.get('applicant_email') or '').strip() or None
    title           = (data.get('title') or '').strip()
    details         = (data.get('details') or '').strip()
    source          = (data.get('source') or 'public_app').strip()

    if not applicant_name:
        return Response({'error': 'applicant_name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not applicant_phone:
        return Response({'error': 'applicant_phone is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not title:
        return Response({'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not details:
        return Response({'error': 'details is required'}, status=status.HTTP_400_BAD_REQUEST)

    valid_sources = {c[0] for c in ComplaintTicket.SOURCE_CHOICES}
    if source not in valid_sources:
        source = 'public_app'

    user = request.user
    creator = user if (user and not user.is_anonymous) else None

    # Non-helpdesk authenticated users are always public_app source
    if creator and getattr(creator, 'role', '') not in _STAFF_ROLES:
        source = 'public_app'

    ticket = ComplaintTicket.objects.create(
        applicant_name=applicant_name,
        applicant_phone=applicant_phone,
        applicant_email=applicant_email,
        title=title,
        details=details,
        source=source,
        created_by=creator,
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
    """List all tickets. Supports optional query filters: status, source, search (ref/name/phone)."""
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    qs = ComplaintTicket.objects.prefetch_related('attachments').all()

    filter_status = request.GET.get('status')
    if filter_status:
        qs = qs.filter(status=filter_status)

    filter_source = request.GET.get('source')
    if filter_source:
        qs = qs.filter(source=filter_source)

    search = (request.GET.get('search') or '').strip()
    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(ticket_ref__icontains=search)
            | Q(applicant_name__icontains=search)
            | Q(applicant_phone__icontains=search)
            | Q(applicant_email__icontains=search)
            | Q(title__icontains=search)
        )

    # Simple pagination
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
    """Full ticket detail including attachments."""
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.prefetch_related('attachments').get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response(_serialize_ticket(ticket))


@api_view(['PATCH'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_ticket_status(request, pk):
    """Change the status of a ticket. Enforces allowed transitions."""
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
    """Return the full activity trail for a ticket."""
    if not _is_staff(request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ticket = ComplaintTicket.objects.get(pk=pk)
    except ComplaintTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'ticket_ref': ticket.ticket_ref, 'activities': _serialize_activities(ticket)})


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
