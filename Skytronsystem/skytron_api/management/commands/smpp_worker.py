"""
python manage.py smpp_worker

Keeps one TLS transceiver bind to Airtel's SMSC and:
  - sends SmppSmsOut rows with status 'queued' (at most SMPP_TPS parts a second,
    at most SMPP_WINDOW submit_sm waiting for a reply)
  - records each part's SMSC message id and its delivery receipt
  - stores SMS sent to our VMN in SmppSmsIn
Runs in its own container (run_smpp.sh), only on the dev VM. A row that was
'sending' when the worker stopped is sent again (at-least-once).

Settings (env):
    SMPP_SYSTEM_ID, SMPP_PASSWORD   required
    SMPP_HOSTS          comma-separated, tried in turn (default: Airtel's two SMSCs)
    SMPP_PORT           default 2775          SMPP_TLS          1 (default) | 0
    SMPP_SYSTEM_TYPE    default ''
    SMPP_SOURCE_ADDR    our VMN               SMPP_SOURCE_TON / SMPP_SOURCE_NPI   default 0 / 1
    SMPP_DEST_TON / SMPP_DEST_NPI   default 0 / 1
    SMPP_DATA_CODING    for ASCII text, default 0 (non-ASCII always goes as UCS2)
    SMPP_TPS            default 100           SMPP_WINDOW       default 10
    SMPP_MAX_ATTEMPTS   default 3             SMPP_ENQUIRE_INTERVAL   seconds, default 30
"""
import logging
import os
import signal
import time
from datetime import timedelta

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, close_old_connections
from django.db.models import F, Q
from django.utils import timezone

from skytron_api import smpp_client as smpp
from skytron_api.models import SmppSmsIn, SmppSmsOut, SmppSmsPart

logger = logging.getLogger(__name__)

HEARTBEAT_KEY = 'smpp:worker:status'
HEARTBEAT_TTL = 60
FINAL_STATS = {'DELIVRD', 'UNDELIV', 'EXPIRED', 'DELETED', 'REJECTD', 'UNKNOWN'}
AUTH_FAILURES = {0x0D, 0x0E, 0x0F}      # don't hammer the SMSC with a wrong password
RESP_TIMEOUT = 30
ENQUIRE_TIMEOUT = 15
IDLE_POLL = 0.5


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise CommandError(f'{name} must be a number')


class Command(BaseCommand):
    help = "Send queued SMS over Airtel SMPP and record delivery receipts and incoming SMS."

    last_error = ''

    def handle(self, *args, **options):
        # Project logging only shows ERROR; the worker's log is `docker logs`.
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False

        self.system_id = os.environ.get('SMPP_SYSTEM_ID', '')
        self.password = os.environ.get('SMPP_PASSWORD', '')
        if not self.system_id or not self.password:
            raise CommandError('SMPP_SYSTEM_ID and SMPP_PASSWORD must be set')
        self.hosts = [h.strip() for h in os.environ.get('SMPP_HOSTS', '125.17.6.63,125.16.74.228').split(',') if h.strip()]
        self.port = _env_int('SMPP_PORT', 2775)
        self.use_tls = os.environ.get('SMPP_TLS', '1') != '0'
        self.system_type = os.environ.get('SMPP_SYSTEM_TYPE', '')
        self.source = os.environ.get('SMPP_SOURCE_ADDR', '')
        self.source_ton = _env_int('SMPP_SOURCE_TON', 0)
        self.source_npi = _env_int('SMPP_SOURCE_NPI', 1)
        self.dest_ton = _env_int('SMPP_DEST_TON', 0)
        self.dest_npi = _env_int('SMPP_DEST_NPI', 1)
        self.data_coding = _env_int('SMPP_DATA_CODING', 0)
        self.tps = max(1, _env_int('SMPP_TPS', 100))
        self.window = max(1, _env_int('SMPP_WINDOW', 10))
        self.max_attempts = max(1, _env_int('SMPP_MAX_ATTEMPTS', 3))
        self.enquire_interval = max(5, _env_int('SMPP_ENQUIRE_INTERVAL', 30))

        self.stop = False
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)

        recovered = SmppSmsOut.objects.filter(status='sending').update(status='queued')
        if recovered:
            logger.warning(f"SMPP: {recovered} SMS were mid-send when the worker stopped; sending them again")

        host_index, backoff = 0, 5
        while not self.stop:
            host = self.hosts[host_index % len(self.hosts)]
            self.conn = None
            try:
                self._heartbeat('connecting', host)
                self.conn = smpp.SmppConnection(host, self.port, self.use_tls)
                self.conn.bind_transceiver(self.system_id, self.password, self.system_type)
                logger.info(f"SMPP: bound as {self.system_id} to {host}:{self.port}")
                backoff, self.last_error = 5, ''
                self._serve(host)
            except (smpp.SmppError, OSError) as e:
                logger.error(f"SMPP: {host}:{self.port}: {e}")
                self.last_error = str(e)
                host_index += 1
            finally:
                self._abandon_inflight()
                if self.conn:
                    if self.stop:
                        self.conn.unbind()
                    self.conn.close()
            if self.stop:
                break
            wait = 300 if 'RINVPASWD' in self.last_error or 'RINVSYSID' in self.last_error \
                or 'RBINDFAIL' in self.last_error else backoff
            backoff = min(backoff * 2, 60)
            self._heartbeat('backoff', host)
            self._sleep(wait)
        self._heartbeat('stopped', '')
        logger.info("SMPP: worker stopped")

    def _on_signal(self, *_):
        self.stop = True

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while not self.stop and time.monotonic() < end:
            time.sleep(0.5)

    # ------------------------------------------------------------------ main loop

    def _serve(self, host):
        self.inflight = {}           # seq -> (sms_id, part_no, sent monotonic)
        self.sending = {}            # sms_id -> {'parts', 'answered', 'accepted', 'failed'}
        self.tokens, self.token_time = float(self.tps), time.monotonic()
        self.next_poll = 0
        self.bound_since = timezone.now()
        last_rx = time.monotonic()
        enquire_seq, enquire_sent = None, 0
        next_heartbeat = 0

        while not self.stop:
            now = time.monotonic()
            try:
                pdus = self.conn.read_pdus(0.02 if self.inflight else 0.1)
                if pdus:
                    last_rx = now
                for command_id, command_status, seq, body in pdus:
                    if command_id == smpp.ENQUIRE_LINK_RESP and seq == enquire_seq:
                        enquire_seq = None
                    else:
                        self._handle_pdu(command_id, command_status, seq, body)

                if enquire_seq is None and now - last_rx >= self.enquire_interval:
                    enquire_seq, enquire_sent = self.conn.send_pdu(smpp.ENQUIRE_LINK), now
                elif enquire_seq is not None and now - enquire_sent > ENQUIRE_TIMEOUT:
                    raise smpp.SmppError('no reply to enquire_link')
                if self.inflight and now - min(t for _, _, t in self.inflight.values()) > RESP_TIMEOUT:
                    raise smpp.SmppError('no submit_sm_resp within %ss' % RESP_TIMEOUT)

                self._dispatch()
            except DatabaseError as e:
                # Keep the bind: the SMSC is fine, our DB is not. Rows stay queued.
                logger.error(f"SMPP: database error: {e}")
                close_old_connections()
                self._sleep(2)
            if now >= next_heartbeat:
                self._heartbeat('bound', host)
                next_heartbeat = now + 10

    # ------------------------------------------------------------------ sending

    def _dispatch(self):
        now = time.monotonic()
        self.tokens = min(float(self.tps), self.tokens + (now - self.token_time) * self.tps)
        self.token_time = now
        room = self.window - len(self.inflight)
        if room <= 0 or self.tokens < 1 or now < self.next_poll:
            return

        due = Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now())
        batch = list(SmppSmsOut.objects.filter(status='queued').filter(due).order_by('id')[:room])
        if not batch:
            self.next_poll = now + IDLE_POLL
            return

        for sms in batch:
            try:
                data_coding, data = smpp.encode_text(sms.text, self.data_coding)
                parts = smpp.split_message(data, data_coding, sms.id)
            except smpp.SmppError as e:
                SmppSmsOut.objects.filter(id=sms.id).update(status='failed', error=str(e), final_at=timezone.now())
                continue
            # A long SMS may need more than the free room; send it alone rather than never.
            if self.inflight and (len(parts) > self.window - len(self.inflight) or len(parts) > self.tokens):
                break
            claimed = SmppSmsOut.objects.filter(id=sms.id, status='queued').update(
                status='sending', attempts=F('attempts') + 1, parts_total=len(parts))
            if not claimed:
                continue
            self.sending[sms.id] = {'parts': len(parts), 'answered': 0, 'accepted': 0, 'failed': None,
                                    'attempts': sms.attempts + 1}
            for part_no, (esm_class, short_message) in enumerate(parts, 1):
                seq = self.conn.submit_sm(self.source, self.source_ton, self.source_npi,
                                          sms.dest_no, self.dest_ton, self.dest_npi,
                                          esm_class, data_coding, short_message)
                self.inflight[seq] = (sms.id, part_no, time.monotonic())
            self.tokens -= len(parts)

    def _submit_result(self, seq, command_status, body):
        entry = self.inflight.pop(seq, None)
        if entry is None:
            return
        sms_id, part_no, _ = entry
        state = self.sending.get(sms_id)
        if state is None:
            return
        state['answered'] += 1
        if command_status == smpp.ESME_ROK:
            message_id = body.split(b'\0', 1)[0].decode('latin-1')
            SmppSmsPart.objects.create(sms_id=sms_id, part_no=part_no, message_id=message_id)
            state['accepted'] += 1
        else:
            state['failed'] = command_status
            logger.warning(f"SMPP: SMS {sms_id} part {part_no} rejected: {smpp.status_name(command_status)}")
        if state['answered'] == state['parts']:
            self._finish(sms_id, self.sending.pop(sms_id))

    def _finish(self, sms_id, state):
        now = timezone.now()
        pending = SmppSmsOut.objects.filter(id=sms_id, status='sending')
        if state['failed'] is None:
            pending.update(status='submitted', submitted_at=now, error='')
            return
        code = state['failed']
        error = smpp.status_name(code)
        if not state['accepted'] and code in smpp.RETRYABLE_STATUSES and state['attempts'] < self.max_attempts:
            pending.update(status='queued', error=error,
                           next_attempt_at=now + timedelta(seconds=10 * 2 ** state['attempts']))
            return
        if state['accepted']:
            error = f"{error} ({state['accepted']} of {state['parts']} parts accepted)"
        pending.update(status='failed', error=error, final_at=now)

    def _abandon_inflight(self):
        """Connection lost: SMS the SMSC never answered go back to the queue."""
        sending = getattr(self, 'sending', {})
        try:
            for sms_id, state in sending.items():
                pending = SmppSmsOut.objects.filter(id=sms_id, status='sending')
                if state['accepted']:
                    pending.update(status='failed', final_at=timezone.now(),
                                   error=f"connection lost ({state['accepted']} of {state['parts']} parts accepted)")
                elif state['attempts'] >= self.max_attempts:
                    pending.update(status='failed', final_at=timezone.now(), error='connection lost')
                else:
                    pending.update(status='queued', next_attempt_at=timezone.now() + timedelta(seconds=5))
        except DatabaseError as e:
            logger.error(f"SMPP: could not requeue in-flight SMS (they are retried on restart): {e}")
        self.sending, self.inflight = {}, {}

    # ------------------------------------------------------------------ incoming

    def _handle_pdu(self, command_id, command_status, seq, body):
        if command_id == smpp.SUBMIT_SM_RESP:
            self._submit_result(seq, command_status, body)
        elif command_id == smpp.DELIVER_SM:
            self._deliver(seq, body)
        elif command_id == smpp.ENQUIRE_LINK:
            self.conn.send_pdu(smpp.ENQUIRE_LINK_RESP, seq=seq)
        elif command_id == smpp.UNBIND:
            self.conn.send_pdu(smpp.UNBIND_RESP, seq=seq)
            raise smpp.SmppError('SMSC unbound us')
        elif command_id == smpp.GENERIC_NACK:
            if seq in self.inflight:
                self._submit_result(seq, command_status or smpp.ESME_RSYSERR, b'')
            else:
                logger.warning(f"SMPP: generic_nack {smpp.status_name(command_status)} for seq {seq}")
        elif not command_id & 0x80000000:
            self.conn.send_pdu(smpp.GENERIC_NACK, seq=seq, command_status=smpp.ESME_RINVCMDID)

    def _deliver(self, seq, body):
        try:
            pdu = smpp.parse_deliver_sm(body)
        except (ValueError, IndexError) as e:
            logger.error(f"SMPP: unreadable deliver_sm ({e}): {body.hex()}")
            self.conn.send_pdu(smpp.DELIVER_SM_RESP, b'\0', seq=seq)   # acknowledged so it isn't resent forever
            return
        try:
            if smpp.is_receipt(pdu['esm_class']):
                self._receipt(pdu)
            else:
                SmppSmsIn.objects.create(
                    source_no=pdu['source_addr'][:21], dest_no=pdu['dest_addr'][:21],
                    text=smpp.decode_text(pdu['short_message'], pdu['data_coding'], pdu['esm_class']),
                    data_coding=pdu['data_coding'], esm_class=pdu['esm_class'],
                    raw_hex=pdu['short_message'].hex())
        except DatabaseError:
            # Not stored: ask the SMSC to deliver it again later.
            self.conn.send_pdu(smpp.DELIVER_SM_RESP, b'\0', seq=seq, command_status=smpp.ESME_RX_T_APPN)
            raise
        self.conn.send_pdu(smpp.DELIVER_SM_RESP, b'\0', seq=seq)

    def _receipt(self, pdu):
        message_id, stat, err, text = smpp.parse_receipt(pdu)
        part = SmppSmsPart.objects.filter(message_id__in=smpp.message_id_candidates(message_id)) \
            .order_by('-id').first() if message_id else None
        if part is None:
            logger.warning(f"SMPP: receipt for unknown message id {message_id!r}: {text}")
            return
        now = timezone.now()
        SmppSmsPart.objects.filter(id=part.id).update(dlr_stat=stat[:16], dlr_err=err[:16], dlr_text=text, dlr_at=now)
        if stat not in FINAL_STATS:
            return
        sms = SmppSmsOut.objects.get(id=part.sms_id)
        stats = list(sms.parts.values_list('dlr_stat', flat=True))
        open_states = SmppSmsOut.objects.filter(id=sms.id, status__in=['sending', 'submitted'])
        bad = [s for s in stats if s in FINAL_STATS and s != 'DELIVRD']
        if bad:
            open_states.update(status='undelivered', final_at=now,
                               error=f"{bad[0]}{' err:' + err if err and stat == bad[0] else ''}")
        elif len(stats) == sms.parts_total and all(s == 'DELIVRD' for s in stats):
            open_states.update(status='delivered', final_at=now, error='')

    # ------------------------------------------------------------------ status

    def _heartbeat(self, state, host):
        try:
            cache.set(HEARTBEAT_KEY, {
                'state': state,
                'host': host,
                'port': self.port,
                'system_id': self.system_id,
                'bound_since': getattr(self, 'bound_since', None).isoformat()
                if state == 'bound' and getattr(self, 'bound_since', None) else None,
                'in_flight': len(getattr(self, 'inflight', {})),
                'last_error': self.last_error,
                'updated_at': timezone.now().isoformat(),
            }, HEARTBEAT_TTL)
        except Exception as e:     # Redis down must not stop sending
            logger.warning(f"SMPP: heartbeat not saved: {e}")
