"""
Minimal SMPP 3.4 client (ESME side) for Airtel's SMSC: TLS transceiver bind,
submit_sm, delivery receipts and incoming SMS (deliver_sm), enquire_link.

Only the protocol lives here - no Django. The queue, rate limit and database
writes are in management/commands/smpp_worker.py. Written by hand rather than
using a library so no new package is needed in the shared backend images.
"""
import re
import select
import socket
import ssl
import struct
import time

# Command ids
GENERIC_NACK = 0x80000000
BIND_TRANSCEIVER = 0x00000009
BIND_TRANSCEIVER_RESP = 0x80000009
SUBMIT_SM = 0x00000004
SUBMIT_SM_RESP = 0x80000004
DELIVER_SM = 0x00000005
DELIVER_SM_RESP = 0x80000005
UNBIND = 0x00000006
UNBIND_RESP = 0x80000006
ENQUIRE_LINK = 0x00000015
ENQUIRE_LINK_RESP = 0x80000015

# Command status codes we act on
ESME_ROK = 0x00000000
ESME_RINVCMDID = 0x00000003
ESME_RMSGQFUL = 0x00000014
ESME_RTHROTTLED = 0x00000058
ESME_RSYSERR = 0x00000008
ESME_RX_T_APPN = 0x00000064     # temporary application error
RETRYABLE_STATUSES = {ESME_RMSGQFUL, ESME_RTHROTTLED, ESME_RSYSERR, ESME_RX_T_APPN}

STATUS_NAMES = {
    0x00: 'ESME_ROK', 0x01: 'ESME_RINVMSGLEN', 0x02: 'ESME_RINVCMDLEN', 0x03: 'ESME_RINVCMDID',
    0x04: 'ESME_RINVBNDSTS', 0x05: 'ESME_RALYBND', 0x08: 'ESME_RSYSERR', 0x0A: 'ESME_RINVSRCADR',
    0x0B: 'ESME_RINVDSTADR', 0x0D: 'ESME_RBINDFAIL', 0x0E: 'ESME_RINVPASWD', 0x0F: 'ESME_RINVSYSID',
    0x14: 'ESME_RMSGQFUL', 0x45: 'ESME_RSUBMITFAIL', 0x48: 'ESME_RINVSRCTON', 0x49: 'ESME_RINVSRCNPI',
    0x50: 'ESME_RINVDSTTON', 0x51: 'ESME_RINVDSTNPI', 0x58: 'ESME_RTHROTTLED', 0x61: 'ESME_RINVSCHED',
    0x62: 'ESME_RINVEXPIRY', 0x64: 'ESME_RX_T_APPN', 0x65: 'ESME_RX_P_APPN', 0x66: 'ESME_RX_R_APPN',
}

# Optional parameter (TLV) tags
TLV_RECEIPTED_MESSAGE_ID = 0x001E
TLV_NETWORK_ERROR_CODE = 0x0423
TLV_MESSAGE_PAYLOAD = 0x0424
TLV_MESSAGE_STATE = 0x0427

MESSAGE_STATES = {1: 'ENROUTE', 2: 'DELIVRD', 3: 'EXPIRED', 4: 'DELETED', 5: 'UNDELIV',
                  6: 'ACCEPTD', 7: 'UNKNOWN', 8: 'REJECTD'}

DLR_TEXT_RE = re.compile(r'id:(?P<id>\S+).*?stat:(?P<stat>\w+)(?:.*?err:(?P<err>\w+))?', re.IGNORECASE | re.DOTALL)

MAX_PDU_LEN = 64 * 1024


def status_name(code):
    return STATUS_NAMES.get(code, f'0x{code:08X}')


class SmppError(Exception):
    pass


def _cstr(value):
    return (value or '').encode('latin-1') + b'\0'


def _read_cstr(body, pos):
    end = body.index(b'\0', pos)
    return body[pos:end].decode('latin-1', 'replace'), end + 1


def encode_text(text, data_coding_ascii=0):
    """(data_coding, bytes): plain ASCII as-is, anything else as UCS2."""
    try:
        return data_coding_ascii, text.encode('ascii')
    except UnicodeEncodeError:
        return 8, text.encode('utf-16-be')


def split_message(data, data_coding, ref):
    """
    One short_message per part. Above one SMS the parts carry a concatenation
    UDH (8-bit reference), so the phone/device reassembles them.
    Returns [(esm_class, short_message)].
    """
    # Part sizes in bytes; 134 is even, so a UCS2 character is never split.
    single, part = (140, 134) if data_coding == 8 else (160, 153)
    if len(data) <= single:
        return [(0x00, data)]
    chunks = [data[i:i + part] for i in range(0, len(data), part)]
    total = len(chunks)
    if total > 255:
        raise SmppError('message too long')
    return [(0x40, bytes([5, 0, 3, ref & 0xFF, total, n + 1]) + chunk) for n, chunk in enumerate(chunks)]


def parse_tlvs(body, pos):
    tlvs = {}
    while pos + 4 <= len(body):
        tag, length = struct.unpack('>HH', body[pos:pos + 4])
        tlvs[tag] = body[pos + 4:pos + 4 + length]
        pos += 4 + length
    return tlvs


def parse_deliver_sm(body):
    """Fields of a deliver_sm body we use (receipts and incoming SMS)."""
    pos = 0
    _service_type, pos = _read_cstr(body, pos)
    src_ton, src_npi = body[pos], body[pos + 1]
    source_addr, pos = _read_cstr(body, pos + 2)
    dst_ton, dst_npi = body[pos], body[pos + 1]
    dest_addr, pos = _read_cstr(body, pos + 2)
    esm_class, _protocol_id, _priority = body[pos], body[pos + 1], body[pos + 2]
    pos += 3
    _schedule, pos = _read_cstr(body, pos)
    _validity, pos = _read_cstr(body, pos)
    _registered_delivery, _replace, data_coding, _default_msg_id, sm_length = body[pos:pos + 5]
    pos += 5
    short_message = body[pos:pos + sm_length]
    tlvs = parse_tlvs(body, pos + sm_length)
    if not short_message and TLV_MESSAGE_PAYLOAD in tlvs:
        short_message = tlvs[TLV_MESSAGE_PAYLOAD]
    return {
        'source_addr': source_addr, 'source_ton': src_ton, 'source_npi': src_npi,
        'dest_addr': dest_addr, 'dest_ton': dst_ton, 'dest_npi': dst_npi,
        'esm_class': esm_class, 'data_coding': data_coding,
        'short_message': short_message, 'tlvs': tlvs,
    }


def is_receipt(esm_class):
    return (esm_class & 0x3C) in (0x04, 0x20)


def decode_text(data, data_coding, esm_class=0):
    """Text of an incoming short_message (UDH stripped)."""
    if esm_class & 0x40 and data:
        data = data[data[0] + 1:]
    if data_coding == 8:
        return data.decode('utf-16-be', 'replace')
    return data.decode('latin-1', 'replace')


def parse_receipt(pdu):
    """(message_id, stat, err, text) of a delivery receipt; TLVs win over the text form."""
    text = pdu['short_message'].decode('latin-1', 'replace')
    m = DLR_TEXT_RE.search(text)
    tlvs = pdu['tlvs']
    message_id = tlvs.get(TLV_RECEIPTED_MESSAGE_ID, b'').rstrip(b'\0').decode('latin-1') or (m and m.group('id')) or ''
    stat = ''
    if TLV_MESSAGE_STATE in tlvs and tlvs[TLV_MESSAGE_STATE]:
        stat = MESSAGE_STATES.get(tlvs[TLV_MESSAGE_STATE][0], '')
    if not stat and m:
        stat = m.group('stat').upper()
    err = (m and m.group('err')) or ''
    if not err and TLV_NETWORK_ERROR_CODE in tlvs:
        err = tlvs[TLV_NETWORK_ERROR_CODE].hex()
    return message_id, stat, err, text[:255]


def message_id_candidates(message_id):
    """
    Some SMSCs give the id in hex in submit_sm_resp and in decimal in the
    receipt (or the other way round); match on any of the forms.
    """
    ids = {message_id, message_id.lower(), message_id.upper()}
    if re.fullmatch(r'[0-9a-fA-F]+', message_id):
        ids.add(str(int(message_id, 16)))
    if message_id.isdigit():
        ids.add(format(int(message_id), 'x'))
        ids.add(format(int(message_id), 'X'))
    return ids


class SmppConnection:
    """One TLS connection and bind. Not thread-safe; owned by the worker loop."""

    def __init__(self, host, port, use_tls=True, timeout=15):
        raw = socket.create_connection((host, port), timeout=timeout)
        if use_tls:
            ctx = ssl.create_default_context()
            # Airtel's certificate is for its SMS domain; we connect by IP.
            # The chain is still verified.
            ctx.check_hostname = False
            self.sock = ctx.wrap_socket(raw)
        else:
            self.sock = raw
        self.sock.settimeout(timeout)
        self.host, self.port = host, port
        self._buf = b''
        self._seq = 0

    def next_seq(self):
        self._seq = self._seq % 0x7FFFFFFF + 1
        return self._seq

    def send_pdu(self, command_id, body=b'', seq=None, command_status=0):
        seq = self.next_seq() if seq is None else seq
        self.sock.sendall(struct.pack('>IIII', 16 + len(body), command_id, command_status, seq) + body)
        return seq

    def read_pdus(self, wait):
        """Every complete PDU available within `wait` seconds: [(command_id, status, seq, body)]."""
        # TLS may already hold decrypted bytes that select() cannot see.
        if not self._has_pdu() and not self._pending():
            if select.select([self.sock], [], [], wait)[0]:
                self._recv()
        while self._pending():
            self._recv()
        pdus = []
        while self._has_pdu():
            length, command_id, command_status, seq = struct.unpack('>IIII', self._buf[:16])
            pdus.append((command_id, command_status, seq, self._buf[16:length]))
            self._buf = self._buf[length:]
        return pdus

    def _pending(self):
        return self.sock.pending() if isinstance(self.sock, ssl.SSLSocket) else 0

    def _recv(self):
        data = self.sock.recv(65536)
        if not data:
            raise SmppError('connection closed by SMSC')
        self._buf += data

    def _has_pdu(self):
        if len(self._buf) < 16:
            return False
        length = struct.unpack('>I', self._buf[:4])[0]
        if length < 16 or length > MAX_PDU_LEN:
            raise SmppError(f'bad PDU length {length}')
        return len(self._buf) >= length

    def wait_for(self, seq, timeout):
        """Block until the response to `seq` (used only while binding/unbinding)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for command_id, command_status, rseq, body in self.read_pdus(0.5):
                if rseq == seq and command_id & 0x80000000:
                    return command_id, command_status, body
                if command_id == ENQUIRE_LINK:
                    self.send_pdu(ENQUIRE_LINK_RESP, seq=rseq)
        raise SmppError('timed out waiting for SMSC response')

    def bind_transceiver(self, system_id, password, system_type=''):
        body = _cstr(system_id) + _cstr(password) + _cstr(system_type) + bytes([0x34, 0, 0]) + _cstr('')
        command_id, command_status, _ = self.wait_for(self.send_pdu(BIND_TRANSCEIVER, body), 20)
        if command_id != BIND_TRANSCEIVER_RESP or command_status != ESME_ROK:
            raise SmppError(f'bind failed: {status_name(command_status)}')

    def submit_sm(self, source, source_ton, source_npi, dest, dest_ton, dest_npi,
                  esm_class, data_coding, short_message):
        body = (_cstr('') + bytes([source_ton, source_npi]) + _cstr(source)
                + bytes([dest_ton, dest_npi]) + _cstr(dest)
                + bytes([esm_class, 0, 0]) + _cstr('') + _cstr('')
                + bytes([1, 0, data_coding, 0, len(short_message)]) + short_message)
        return self.send_pdu(SUBMIT_SM, body)

    def unbind(self):
        try:
            self.wait_for(self.send_pdu(UNBIND), 5)
        except (SmppError, OSError):
            pass

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
