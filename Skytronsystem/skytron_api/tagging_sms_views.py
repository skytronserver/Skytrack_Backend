"""
SMS checks in device tagging step 4 (dealer), after the packet check:

  1. Health check on profile 1: @SET SENDHCHK-1* SMSed to the primary SIM
     number -> device SMSes back HCHKR,000000,<vendor>,<fw>,<imei>,...
  2. Switch to profile 2 (@SETPROF-2*), wait 2-5 min for the device to
     re-register, then the health check again on the secondary number.
  3. (Suggested) switch back to profile 1 (@SETPROF-1*).
  4. Activation, last: ACTV,<6-digit code>,<our VMN> -> device SMSes back
     ACTVR,<same code>,<vendor>,<fw>,<imei>,... If no reply comes, it can be
     sent again (new code) 30 minutes after the last one.

    POST /api/device-tagging/step4/sms/send/    {"id": 12, "action": "health", "profile": 1}
                                                {"id": 12, "action": "set_profile", "profile": 2}
                                                {"id": 12, "action": "activation"}
    POST /api/device-tagging/step4/sms/status/  {"id": 12}

The SMS go out from our Airtel VMN (device_sms.send_device_sms); replies are
read from AirtelSmsInLog / SmppSmsIn. Results are kept on
DeviceStockMaster.sms_checks once passed.

TAGGING_SMS_CHECKS_REQUIRED (env, default 1): step 4 completes only when
these checks have passed as well as the packets; 0 = shown but optional.
"""
import logging
import os
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .device_sms import (
    SMS_REPLY_NUMBER,
    number_matches,
    send_device_sms,
    sim_slot,
    sms_delivery_status,
    sms_received,
    status_replies,
)
from .models import DeviceStock, DeviceTaggingSmsCommand

logger = logging.getLogger(__name__)

# On by default; TAGGING_SMS_CHECKS_REQUIRED=0 turns the gate off.
SMS_CHECKS_REQUIRED = (os.environ.get('TAGGING_SMS_CHECKS_REQUIRED') or '1').strip().lower() not in ('0', 'false', 'no', 'off')

HEALTH_COMMAND = '@SET SENDHCHK-1*'
PROFILE_COMMAND = '@SETPROF-{profile}*'
ACTIVATION_COMMAND = 'ACTV,{code},{number}'      # sent as is, no @...* framing

ACTIVATION_RESEND_AFTER = timedelta(minutes=30)
# Spacing between two SMS of the same kind, so a double click or an
# impatient dealer does not flood the device (and the daily SMS quota).
SEND_COOLDOWN = {
    'set_profile': timedelta(seconds=60),
    'health': timedelta(minutes=2),
}
# Health / activation replies older than this before the first command don't count.
REPLY_SLACK = timedelta(minutes=1)

CHECK_KEYS = ('health_p1', 'health_p2', 'activation')


def _sim_numbers(record):
    """(msisdn1, msisdn2) of the device: from the M2M check in step 2, else DeviceStock."""
    msisdn1 = (record.m2m_primary_msisdn or '').strip()
    msisdn2 = (record.m2m_fallback_msisdn or '').strip()
    if not msisdn1 or not msisdn2:
        stock = DeviceStock.objects.filter(imei=record.imei).values('msisdn1', 'msisdn2').first() or {}
        msisdn1 = msisdn1 or (stock.get('msisdn1') or '').strip()
        msisdn2 = msisdn2 or (stock.get('msisdn2') or '').strip()
    return msisdn1, msisdn2


def _profile_acks(imei, since):
    from .technical_onboarding_testing_views import _profile_acks as acks
    return acks(imei, since)


def _profile_timeline(record, commands):
    """
    [(time, profile)] of every profile change we know of: SETPROF commands
    sent from tagging and the device's own SETPROF acknowledgements (OT,12).
    """
    events = [(c.sent_at, c.profile) for c in commands if c.kind == 'set_profile' and c.profile]
    since = min((c.sent_at for c in commands), default=timezone.now()) - timedelta(days=1)
    events += _profile_acks(record.imei, since)
    events.sort(key=lambda e: e[0])
    return events


def _profile_at(timeline, when):
    return next((p for t, p in reversed(timeline) if t <= when), 1)


def _iso(value):
    return value.isoformat() if value else None


def _command_row(c, delivery):
    state = delivery.get((c.sms_via, c.sms_ref)) or {}
    return {
        'id': c.id,
        'kind': c.kind,
        'profile': c.profile,
        'value': c.value or None,
        'command_sent': c.command_sent,
        'sms_to': c.sms_to,
        'send_status': c.send_status,
        'error': c.error or None,
        'sms_status': state.get('status'),
        'sent_at': _iso(c.sent_at),
    }


def tagging_sms_state(record, persist=True):
    """Current SMS check state of a tagging record; stores newly passed checks on the record."""
    now = timezone.now()
    commands = list(record.sms_commands.all().order_by('sent_at'))
    queued = [c for c in commands if c.send_status == 'queued']
    msisdn1, msisdn2 = _sim_numbers(record)
    distinct_numbers = bool(msisdn1 and msisdn2 and not number_matches(msisdn1, msisdn2))
    timeline = _profile_timeline(record, queued)
    stored = dict(record.sms_checks or {})
    checks = {key: dict(stored.get(key) or {'passed': False}) for key in CHECK_KEYS}

    first_sent = queued[0].sent_at if queued else None
    messages = sms_received(first_sent - REPLY_SLACK) if first_sent else []

    # Health check replies, one per profile.
    health_sent = [c for c in queued if c.kind == 'health']
    if health_sent:
        start = health_sent[0].sent_at - REPLY_SLACK
        for m in messages:
            if m['time'] < start:
                continue
            for parsed in status_replies(m['text'], 'HCHKR'):
                if parsed['imei'] != record.imei:
                    continue
                profile = (sim_slot(m['sender'], msisdn1, msisdn2) if distinct_numbers else None) \
                    or _profile_at(timeline, m['time'])
                key = f'health_p{profile}'
                if key in checks and not checks[key].get('passed'):
                    checks[key] = {
                        'passed': True,
                        'passed_at': m['time'].isoformat(),
                        'sms': {'sender': m['sender'], 'text': m['text'], 'received_at': m['time'].isoformat()},
                        'network': f"{parsed.get('mcc', '')}/{parsed.get('mnc', '')}",
                        'firmware': parsed.get('firmware'),
                    }

    # Activation reply carrying one of the codes sent.
    activation_sent = [c for c in queued if c.kind == 'activation']
    codes = {c.value for c in activation_sent if c.value}
    if activation_sent and not checks['activation'].get('passed'):
        start = activation_sent[0].sent_at - REPLY_SLACK
        for m in messages:
            if m['time'] < start:
                continue
            for parsed in status_replies(m['text'], 'ACTVR'):
                if parsed['imei'] == record.imei and parsed['code'] in codes:
                    checks['activation'] = {
                        'passed': True,
                        'passed_at': m['time'].isoformat(),
                        'code': parsed['code'],
                        'sms': {'sender': m['sender'], 'text': m['text'], 'received_at': m['time'].isoformat()},
                        'firmware': parsed.get('firmware'),
                        'vendor': parsed.get('vendor'),
                    }
                    break
            if checks['activation'].get('passed'):
                break

    if persist and checks != stored:
        record.sms_checks = checks
        record.save(update_fields=['sms_checks', 'updated_at'])

    current_profile = _profile_at(timeline, now)
    health_done = checks['health_p1'].get('passed') and checks['health_p2'].get('passed')
    last_activation = activation_sent[-1] if activation_sent else None
    activation_resend_at = (last_activation.sent_at + ACTIVATION_RESEND_AFTER) if last_activation else None
    can_send_activation = bool(health_done and not checks['activation'].get('passed') and (
        not last_activation or now >= activation_resend_at))

    def last_of(kind, profile=None):
        found = [c for c in queued if c.kind == kind and (profile is None or c.profile == profile)]
        return found[-1] if found else None

    def cooldown_until(kind, profile=None):
        last = last_of(kind, profile)
        if not last or kind not in SEND_COOLDOWN:
            return None
        until = last.sent_at + SEND_COOLDOWN[kind]
        return until if until > now else None

    delivery = sms_delivery_status([(c.sms_via, c.sms_ref) for c in commands[-20:] if c.sms_ref])

    steps = []
    for profile in (1, 2):
        key = f'health_p{profile}'
        last = last_of('health', profile)
        steps.append({
            'key': key,
            'label': f'Health check SMS on profile {profile} ({"primary" if profile == 1 else "secondary"} network)',
            'profile': profile,
            'sms_to': msisdn1 if profile == 1 else msisdn2,
            'passed': bool(checks[key].get('passed')),
            'result': checks[key] if checks[key].get('passed') else None,
            'last_sent_at': _iso(last.sent_at) if last else None,
            'next_send_at': _iso(cooldown_until('health', profile)),
            'device_on_profile': current_profile == profile,
        })
    steps.append({
        'key': 'activation',
        'label': 'Activation command and reply',
        'sms_to': msisdn1 if current_profile == 1 else msisdn2,
        'passed': bool(checks['activation'].get('passed')),
        'result': checks['activation'] if checks['activation'].get('passed') else None,
        'last_sent_at': _iso(last_activation.sent_at) if last_activation else None,
        'codes_sent': [c.value for c in activation_sent],
        'can_send': can_send_activation,
        'next_send_at': _iso(activation_resend_at) if last_activation and not checks['activation'].get('passed') else None,
        'blocked_reason': (None if health_done else 'Pass the health check on both profiles first.'),
    })

    return {
        'required': SMS_CHECKS_REQUIRED,
        'all_passed': all(checks[k].get('passed') for k in CHECK_KEYS),
        'msisdn1': msisdn1 or None,
        'msisdn2': msisdn2 or None,
        'reply_number': SMS_REPLY_NUMBER,
        'current_profile': current_profile,
        'profile_cooldown_until': _iso(cooldown_until('set_profile')),
        'steps': steps,
        'commands': [_command_row(c, delivery) for c in reversed(commands[-20:])],
    }


def sms_checks_passed(record):
    """For step 4: True when the SMS checks are not required or have all passed."""
    if not SMS_CHECKS_REQUIRED:
        return True
    return tagging_sms_state(record)['all_passed']


def _err(message, code=status.HTTP_400_BAD_REQUEST, **extra):
    body = {'status': 'failed', 'error': message}
    body.update(extra)
    return Response(body, status=code)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def device_tagging_step4_sms_status(request):
    """POST /api/device-tagging/step4/sms/status/  {"id": <entry id>}"""
    from .views import _get_tagging_record, validate_inputs
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    record, _dealer, error = _get_tagging_record(request, request.data.get('id'), expected_step=4)
    if error:
        return error
    return Response({'status': 'success', 'data': tagging_sms_state(record)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def device_tagging_step4_sms_send(request):
    """
    POST /api/device-tagging/step4/sms/send/
      {"id": 12, "action": "set_profile", "profile": 2}   -> @SETPROF-2* to the number of the current profile
      {"id": 12, "action": "health", "profile": 1}        -> @SET SENDHCHK-1* to msisdn<profile>
      {"id": 12, "action": "activation"}                  -> ACTV,<new code>,<VMN> to the current profile's number
    """
    from .views import _get_tagging_record, validate_inputs
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    action = (request.data.get('action') or '').strip()
    if action not in ('set_profile', 'health', 'activation'):
        return _err("action must be 'set_profile', 'health' or 'activation'.")
    profile = request.data.get('profile')
    if action in ('set_profile', 'health'):
        try:
            profile = int(profile)
        except (TypeError, ValueError):
            profile = None
        if profile not in (1, 2):
            return _err('profile must be 1 or 2.')
    else:
        profile = None

    with transaction.atomic():
        record, _dealer, error = _get_tagging_record(request, request.data.get('id'), expected_step=4)
        if error:
            return error
        # One send at a time per entry, so the cooldown checks below hold.
        type(record).objects.select_for_update().filter(id=record.id).first()

        state = tagging_sms_state(record)
        now = timezone.now()
        current_profile = state['current_profile']
        msisdn = {1: state['msisdn1'], 2: state['msisdn2']}
        value = ''

        if action == 'set_profile':
            if state['profile_cooldown_until']:
                return _err('A profile switch was just sent. Wait a minute before sending another.',
                            status.HTTP_429_TOO_MANY_REQUESTS, retry_at=state['profile_cooldown_until'])
            # The device takes the command on the network it is on now.
            sms_to = msisdn[current_profile] or msisdn[1]
            text = PROFILE_COMMAND.format(profile=profile)
        elif action == 'health':
            step = next(s for s in state['steps'] if s['key'] == f'health_p{profile}')
            if step['passed']:
                return _err(f'The health check on profile {profile} has already passed.')
            if step['next_send_at']:
                return _err('The health check was just sent. Wait 2 minutes for the reply before sending it again.',
                            status.HTTP_429_TOO_MANY_REQUESTS, retry_at=step['next_send_at'])
            sms_to = msisdn[profile]
            text = HEALTH_COMMAND
        else:
            step = next(s for s in state['steps'] if s['key'] == 'activation')
            if step['passed']:
                return _err('The activation reply has already been received.')
            if not step['can_send']:
                if step['blocked_reason']:
                    return _err(step['blocked_reason'])
                return _err('The activation command was sent less than 30 minutes ago. Wait for the reply; '
                            'it can be sent again 30 minutes after the last one.',
                            status.HTTP_429_TOO_MANY_REQUESTS, retry_at=step['next_send_at'])
            sms_to = msisdn[current_profile] or msisdn[1]
            value = str(secrets.randbelow(1000000)).zfill(6)
            text = ACTIVATION_COMMAND.format(code=value, number=SMS_REPLY_NUMBER)

        if not sms_to:
            return _err('No SIM number is on record for this device'
                        + (f' (profile {profile}).' if profile else '.'))

        sent = send_device_sms(sms_to, text, imei=record.imei, user=request.user)
        command = DeviceTaggingSmsCommand.objects.create(
            record=record, imei=record.imei, kind=action, profile=profile, value=value,
            command_sent=text, sms_to=sms_to, sms_via=sent['via'], sms_ref=sent['ref'],
            send_status='queued' if sent['ok'] else 'failed', error=(sent['error'] or '')[:255],
            sent_by=request.user, sent_at=now,
        )

    if not sent['ok']:
        logger.warning('Tagging SMS %s for record %s failed: %s', action, record.id, sent['error'])
        return _err(sent['error'] or 'Could not send the SMS.', status.HTTP_502_BAD_GATEWAY,
                    data=tagging_sms_state(record, persist=False))

    hint = {
        'set_profile': f'Profile {profile} switch sent. The device takes 2-5 minutes to move to the new network.',
        'health': f'Health check request sent to {sms_to}. The device replies by SMS, usually within a few minutes.',
        'activation': f'Activation command sent to {sms_to} (code {value}). The device replies by SMS; '
                      f'if no reply comes it can be sent again after 30 minutes.',
    }[action]
    return Response({
        'status': 'success',
        'message': hint,
        'command': {'id': command.id, 'kind': action, 'profile': profile, 'value': value or None,
                    'command_sent': text, 'sms_to': sms_to, 'sent_at': command.sent_at.isoformat()},
        'data': tagging_sms_state(record, persist=False),
    })
