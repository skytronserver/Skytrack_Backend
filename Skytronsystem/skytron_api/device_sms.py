"""
SMS to a tracked device's SIM (msisdn), for protocol commands: onboarding test
commands, tagging health / activation commands.

The SMS goes out from our Airtel VMN, so the device's SMS reply comes back to
the VMN. Three ways to send, picked by DEVICE_SMS_VIA:

    smpp         queue it in SmppSmsOut here; the smpp_worker on this host
                 sends it (dev VM, which holds the SMPP bind)
    gateway      POST it to the SMS gateway API on the dev VM
                 (https://dev-api.skytron.in/api/smpp/gateway/send/) - NIC
    phone_queue  the old sms_out phone queue (add_sms_queue), as before

Default: gateway when DEVICE_SMS_GATEWAY_URL is set, else smpp when this host
runs the gateway API (SMPP_API_KEYS set), else phone_queue.

Not the OTP gateway (sms_send) - that is a different sender and route.

Settings (env):
    DEVICE_SMS_VIA               smpp | gateway | phone_queue (optional)
    DEVICE_SMS_GATEWAY_URL       e.g. https://dev-api.skytron.in/api/smpp/gateway/send/
    DEVICE_SMS_GATEWAY_KEY       X-Api-Key for that gateway (a key from its SMPP_API_KEYS)
    ONBOARDING_SMS_REPLY_NUMBER  number a device SMSes its activation / health reply to
                                 (the VMN); default SMPP_SOURCE_ADDR, else 9181016496
"""
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

GATEWAY_URL = (os.environ.get('DEVICE_SMS_GATEWAY_URL') or '').strip()
GATEWAY_KEY = (os.environ.get('DEVICE_SMS_GATEWAY_KEY') or '').strip()
GATEWAY_TIMEOUT = 10

SMS_REPLY_NUMBER = (
    (os.environ.get('ONBOARDING_SMS_REPLY_NUMBER') or '').strip()
    or (os.environ.get('SMPP_SOURCE_ADDR') or '').strip()
    or '9181016496'
)


def send_via():
    via = (os.environ.get('DEVICE_SMS_VIA') or '').strip().lower()
    if via in ('smpp', 'gateway', 'phone_queue'):
        return via
    if GATEWAY_URL:
        return 'gateway'
    if (os.environ.get('SMPP_API_KEYS') or '').strip():
        return 'smpp'
    return 'phone_queue'


def _status_url():
    return GATEWAY_URL.replace('/gateway/send/', '/gateway/status/')


def send_device_sms(number, text, imei='', user=None):
    """
    Send one SMS to a device SIM. Never raises.
    Returns {'ok': bool, 'via': str, 'ref': str, 'dest_no': str, 'error': str}.
    ref = SmppSmsOut id (smpp) or gateway txn_id (gateway); '' for phone_queue.
    """
    via = send_via()
    result = {'ok': False, 'via': via, 'ref': '', 'dest_no': str(number or ''), 'error': ''}
    if not number:
        result['error'] = 'No SIM number on record for the device.'
        return result

    if via == 'smpp':
        from .smpp_views import SmppNumberError, queue_smpp_sms
        try:
            sms = queue_smpp_sms(number, text, imei=imei, user=user)
        except SmppNumberError as e:
            result['error'] = f'SIM number {number}: {e}'
            return result
        except Exception:
            logger.exception('device SMS: could not queue SMPP SMS to %s', number)
            result['error'] = 'Could not queue the SMS.'
            return result
        result.update(ok=True, ref=str(sms.id), dest_no=sms.dest_no)
        return result

    if via == 'gateway':
        if not GATEWAY_URL or not GATEWAY_KEY:
            result['error'] = 'SMS gateway is not configured (DEVICE_SMS_GATEWAY_URL / DEVICE_SMS_GATEWAY_KEY).'
            return result
        try:
            resp = requests.post(
                GATEWAY_URL, json={'receiver_no': str(number), 'text': text},
                headers={'X-Api-Key': GATEWAY_KEY}, timeout=GATEWAY_TIMEOUT,
            )
            body = resp.json() if resp.content else {}
        except (requests.RequestException, ValueError) as e:
            logger.warning('device SMS: gateway call failed for %s: %s', number, e)
            result['error'] = 'SMS gateway did not answer.'
            return result
        if resp.status_code != 201 or not body.get('txn_id'):
            logger.warning('device SMS: gateway refused SMS to %s: %s %s', number, resp.status_code, body)
            result['error'] = f"SMS gateway refused the SMS ({resp.status_code}): {body.get('message') or body.get('error') or ''}".strip()
            return result
        result.update(ok=True, ref=body['txn_id'], dest_no=body.get('receiver_no') or str(number))
        return result

    # phone_queue
    from .views import add_sms_queue
    if add_sms_queue(text, number) is not None:
        result['error'] = 'Could not queue the SMS.'
        return result
    result['ok'] = True
    return result


def sms_delivery_status(items):
    """
    Delivery state of sent SMS. items: iterable of (via, ref).
    Returns {(via, ref): {'status': ..., 'error': ...}}; unknown refs are left out.
    Gateway lookups are one HTTP call (up to 50 ids); failures are ignored.
    """
    out = {}
    smpp_ids = [ref for via, ref in items if via == 'smpp' and ref and ref.isdigit()]
    if smpp_ids:
        from .models import SmppSmsOut
        for sms_id, sms_status, error in SmppSmsOut.objects.filter(id__in=smpp_ids).values_list('id', 'status', 'error'):
            out[('smpp', str(sms_id))] = {'status': sms_status, 'error': error}

    txn_ids = [ref for via, ref in items if via == 'gateway' and ref][:50]
    if txn_ids and GATEWAY_URL and GATEWAY_KEY:
        try:
            resp = requests.get(_status_url(), params={'txn_id': ','.join(txn_ids)},
                                headers={'X-Api-Key': GATEWAY_KEY}, timeout=5)
            if resp.status_code == 200:
                for row in resp.json().get('data', []):
                    out[('gateway', row.get('txn_id'))] = {'status': row.get('sms_status'), 'error': row.get('error') or ''}
        except (requests.RequestException, ValueError) as e:
            logger.info('device SMS: gateway status lookup failed: %s', e)
    return out


# ---------------------------------------------------------------------------
# SMS from devices (read side)
# ---------------------------------------------------------------------------
# Device SMS reach us two ways: Airtel's gateway pushes SMS sent to our
# receive number to /api/airtel-sms/receive/ (AirtelSmsInLog), and SMS to our
# VMN arrive over the SMPP bind (SmppSmsIn). Both are read together.

SMS_SCAN_LIMIT = 500

# Status replies to ACTV (activation) and SENDHCHK (health check):
#   ACTVR,<code>,<vendor>,<fw>,<imei>,1,<lat>,N,<lon>,E,<fix>,<date time>,<heading>,<speed>,
#         <csq>,<mcc>,<mnc>,<lac>,<mainpwr>,<ign>,<vin>,<frame>,<mode>
#   HCHKR,000000,<vendor>,... (same fields)
STATUS_REPLY_LINE = re.compile(r'\b(ACTVR|HCHKR),[^\r\n]*', re.IGNORECASE)
STATUS_REPLY_FIELDS = (
    'type', 'code', 'vendor', 'firmware', 'imei', 'status', 'lat', 'lat_dir', 'lon', 'lon_dir',
    'fix', 'datetime', 'heading', 'speed', 'csq', 'mcc', 'mnc', 'lac', 'main_power', 'ignition',
    'vin', 'frame', 'mode',
)

# SMS fallback (SOS with no emergency server connection):
#   <IMEI>,<lat>,<N|S>,<lon>,<E|W>,<A|V>,<speed>,<cellid>,<lac>,<date><time>
#   866192070567340,26.192999,N,91.752838,E,A,0.0,C44C,114F,04112026125541
FALLBACK_SMS = re.compile(
    r'^\s*(?P<imei>\d{15}),(?P<lat>-?\d+(?:\.\d+)?),(?P<lat_dir>[NS]),(?P<lon>-?\d+(?:\.\d+)?),'
    r'(?P<lon_dir>[EW]),(?P<fix>[AV]),(?P<speed>\d+(?:\.\d+)?),(?P<cell_id>[0-9A-Fa-f]+),'
    r'(?P<lac>[0-9A-Fa-f]+),(?P<datetime>\d{14})\s*$',
    re.IGNORECASE,
)


def parse_status_reply(line):
    """'ACTVR,...' / 'HCHKR,...' -> dict of named fields (None when too short)."""
    fields = [f.strip() for f in line.strip().split(',')]
    if len(fields) < 5:
        return None
    parsed = dict(zip(STATUS_REPLY_FIELDS, fields))
    parsed['type'] = parsed['type'].upper()
    parsed['field_count'] = len(fields)
    parsed['complete'] = len(fields) >= len(STATUS_REPLY_FIELDS)
    return parsed


def status_replies(text, kind=None):
    """Every ACTVR / HCHKR reply in an SMS text, parsed; kind='ACTVR'|'HCHKR' filters."""
    out = []
    for match in STATUS_REPLY_LINE.finditer(text or ''):
        parsed = parse_status_reply(match.group(0))
        if parsed and (kind is None or parsed['type'] == kind.upper()):
            parsed['line'] = match.group(0).strip()
            out.append(parsed)
    return out


def parse_fallback_sms(text):
    match = FALLBACK_SMS.match(text or '')
    return match.groupdict() if match else None


def digits(value):
    return re.sub(r'\D', '', value or '')


def number_matches(incoming, stored):
    """Same phone number, ignoring +91 / leading digits (needs 10+ digits on both sides)."""
    a, b = digits(incoming), digits(stored)
    if len(a) < 10 or len(b) < 10:
        return False
    return a == b or a.endswith(b[-10:]) or b.endswith(a[-10:])


def sms_received(start, end=None):
    """Every SMS received since `start`, oldest first: {channel, sender, receiver, text, time}."""
    from .models import AirtelSmsInLog, SmppSmsIn
    airtel = AirtelSmsInLog.objects.filter(received_at__gte=start)
    smpp = SmppSmsIn.objects.filter(received_at__gte=start)
    if end is not None:
        airtel, smpp = airtel.filter(received_at__lte=end), smpp.filter(received_at__lte=end)
    messages = [
        {'channel': 'airtel', 'sender': sender, 'receiver': receiver, 'text': text or '', 'time': received_at}
        for sender, receiver, text, received_at in
        airtel.order_by('-received_at').values_list('sender_no', 'receiver_no', 'sms_text', 'received_at')[:SMS_SCAN_LIMIT]
    ] + [
        {'channel': 'smpp', 'sender': sender, 'receiver': receiver, 'text': text or '', 'time': received_at}
        for sender, receiver, text, received_at in
        smpp.order_by('-received_at').values_list('source_no', 'dest_no', 'text', 'received_at')[:SMS_SCAN_LIMIT]
    ]
    messages.sort(key=lambda m: m['time'])
    return messages


def sim_slot(sender, msisdn1, msisdn2):
    """1 / 2 when the SMS came from the device's msisdn1 / msisdn2, else None."""
    if msisdn1 and number_matches(sender, msisdn1):
        return 1
    if msisdn2 and number_matches(sender, msisdn2):
        return 2
    return None
