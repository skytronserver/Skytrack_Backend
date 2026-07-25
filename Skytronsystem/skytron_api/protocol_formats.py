"""
Device wire-protocol parsing/validation (Login, Health, Tracking, Emergency),
derived verbatim from the ARAI & Amendment 3 firmware protocol reference
(mw_packet.c / mw_cmd.c, branch 2026). Field layouts, field order, checksum
placement, and the alert-ID/packet-type reference table are all taken
directly from that spec, without reconciling against what the currently
deployed device fleet actually sends -- this module is a strict compliance
checker, not a lenient re-implementation of the production parser in
data_processor.py.

Used by the device-data-health dashboard to classify a raw packet line as:
  - matched=False              -- doesn't even look like this packet class
  - matched=True,  valid=True  -- looks like it AND every field checks out (green)
  - matched=True,  valid=False -- looks like it but at least one field is
                                   wrong (red) or missing (yellow)

Every field of every matched packet gets its own status via FieldTracker:
  green  = present and valid
  red    = present but fails its check (wrong type/format/enum)
  yellow = the packet didn't have enough fields to include this one at all

Both ARAI_2025 and Amendment3 are implemented.
"""
import re

ARAI_FORMAT_ID = 'ARAI_2025'
AMENDMENT3_FORMAT_ID = 'Amendment3'

PROTOCOL_FORMATS = {
    ARAI_FORMAT_ID: {
        'label': 'ARAI (current)',
        'implemented': True,
    },
    AMENDMENT3_FORMAT_ID: {
        'label': 'Amendment 3',
        'implemented': True,
    },
}

_LATLON_RE = re.compile(r'^(\d{1,3}\.\d+)([NS])(\d{1,3}\.\d+)([EW])$')
_AIN_SPACE_RE = re.compile(r'^(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)$')
_HEX2_RE = re.compile(r'^[0-9A-Fa-f]{2}$')
_ENVELOPE_RE = re.compile(r'\(([^()]*)\)')


def _is_int(s):
    try:
        int(s)
        return True
    except (TypeError, ValueError):
        return False


def _is_float(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _xor_checksum_hex(s):
    cs = 0
    for ch in s:
        cs ^= ord(ch)
    return f"{cs:02X}"


# ---------------------------------------------------------------------------
# Per-field status tracking
# ---------------------------------------------------------------------------

class FieldTracker:
    """Accumulates a green/red/yellow status per named field while a
    validator runs, so the dashboard can render a field-by-field breakdown
    instead of just a pass/fail verdict."""

    def __init__(self):
        self.fields = {}

    def literal(self, name, value, expected):
        if value is None:
            self.fields[name] = {'value': None, 'status': 'yellow', 'error': f'missing (expected literal {expected!r})'}
        elif value == expected:
            self.fields[name] = {'value': value, 'status': 'green', 'error': None}
        else:
            self.fields[name] = {'value': value, 'status': 'red', 'error': f'expected literal {expected!r}'}

    def enum(self, name, value, allowed):
        if value is None:
            self.fields[name] = {'value': None, 'status': 'yellow', 'error': f'missing (expected one of {sorted(allowed)})'}
        elif value in allowed:
            self.fields[name] = {'value': value, 'status': 'green', 'error': None}
        else:
            self.fields[name] = {'value': value, 'status': 'red', 'error': f'expected one of {sorted(allowed)}'}

    def integer(self, name, value):
        self._typed(name, value, _is_int, 'not an integer')

    def number(self, name, value):
        self._typed(name, value, _is_float, 'not numeric')

    def nonempty(self, name, value):
        if value is None:
            self.fields[name] = {'value': None, 'status': 'yellow', 'error': 'missing'}
        elif value == '':
            self.fields[name] = {'value': value, 'status': 'red', 'error': 'empty'}
        else:
            self.fields[name] = {'value': value, 'status': 'green', 'error': None}

    def regex(self, name, value, pattern, hint):
        if value is None:
            self.fields[name] = {'value': None, 'status': 'yellow', 'error': f'missing (expected {hint})'}
        elif pattern.match(value):
            self.fields[name] = {'value': value, 'status': 'green', 'error': None}
        else:
            self.fields[name] = {'value': value, 'status': 'red', 'error': f'does not match {hint}'}

    def raw(self, name, value):
        """No validation -- just record presence/absence (used for opaque
        passthrough fields like vendor_id, fw_version)."""
        if value is None:
            self.fields[name] = {'value': None, 'status': 'yellow', 'error': 'missing'}
        else:
            self.fields[name] = {'value': value, 'status': 'green', 'error': None}

    def custom(self, name, value, ok, error=None):
        if value is None:
            self.fields[name] = {'value': None, 'status': 'yellow', 'error': error or 'missing'}
        elif ok:
            self.fields[name] = {'value': value, 'status': 'green', 'error': None}
        else:
            self.fields[name] = {'value': value, 'status': 'red', 'error': error}

    def _typed(self, name, value, check_fn, error_msg):
        if value is None:
            self.fields[name] = {'value': None, 'status': 'yellow', 'error': 'missing'}
        elif check_fn(value):
            self.fields[name] = {'value': value, 'status': 'green', 'error': None}
        else:
            self.fields[name] = {'value': value, 'status': 'red', 'error': error_msg}

    def overall_valid(self):
        return all(f['status'] == 'green' for f in self.fields.values())

    def errors(self):
        return [f"{name}: {f['error']}" for name, f in self.fields.items() if f['error']]


class ValidationResult:
    def __init__(self, packet_class, matched, fields=None, checksum_ok=None, extra_errors=None):
        self.packet_class = packet_class
        self.matched = matched
        tracker_fields = fields or {}
        self.fields = tracker_fields
        errors = [f"{name}: {f['error']}" for name, f in tracker_fields.items() if f.get('error')]
        if extra_errors:
            errors = list(extra_errors) + errors
        self.errors = errors
        self.valid = matched and not errors
        self.checksum_ok = checksum_ok

    def to_dict(self):
        return {
            'packet_class': self.packet_class,
            'matched': self.matched,
            'valid': self.valid,
            'fields': self.fields,
            'errors': self.errors,
            'checksum_ok': self.checksum_ok,
        }


def _field_value(fields, name):
    entry = fields.get(name)
    return entry.get('value') if entry else None


# ---------------------------------------------------------------------------
# ARAI_2025
# ---------------------------------------------------------------------------

def validate_arai_login(raw, imei=None):
    """$<VRN>,$<IMEI>,$<FW>,$<PROTO>,$<LAT><LATDIR><LON><LONDIR> -- no checksum, no terminator.

    Per the firmware snprintf ("$%s,$%s,$%s,$%s,$%s%c%s%c"), all five fields
    -- including the lat/lon field -- carry a leading '$'.
    """
    parts = raw.strip().split(',')
    if len(parts) != 5 or not all(p.startswith('$') and len(p) > 1 for p in parts):
        return ValidationResult('login', matched=False)

    t = FieldTracker()
    vrn, imei_f, fw, proto = (p[1:] for p in parts[:4])
    t.nonempty('vehicle_reg_no', vrn)
    if imei and imei_f != imei:
        t.custom('imei', imei_f, False, error=f"does not match requested {imei!r}")
    else:
        t.nonempty('imei', imei_f)
    t.nonempty('fw_version', fw)
    t.nonempty('proto_version', proto)

    m = _LATLON_RE.match(parts[4][1:])
    if not m:
        t.custom('latitude', parts[4], False, error="lat/lon field does not match $<lat><N|S><lon><E|W>")
        t.custom('lat_dir', None, False)
        t.custom('longitude', None, False)
        t.custom('lon_dir', None, False)
    else:
        lat, lat_dir, lon, lon_dir = m.groups()
        t.number('latitude', lat)
        t.enum('lat_dir', lat_dir, {'N', 'S'})
        t.number('longitude', lon)
        t.enum('lon_dir', lon_dir, {'E', 'W'})

    return ValidationResult('login', matched=True, fields=t.fields)


_HEALTH_EXPECTED_LEN = 13


def validate_arai_health(raw, imei=None):
    """$,HLM,<VENDOR>,<FW>,<IMEI>,<BATT%>,<LOWBATT%>,<MEM%>,<URI_ON>,<URI_OFF>,<DIN>,<AIN1> <AIN2>,*"""
    parts = raw.strip().split(',')
    if len(parts) < 2 or parts[0] != '$' or parts[1] != 'HLM':
        return ValidationResult('health', matched=False)

    def _get(i):
        return parts[i] if i < len(parts) else None

    extra_errors = []
    if len(parts) != _HEALTH_EXPECTED_LEN:
        extra_errors.append(f"expected {_HEALTH_EXPECTED_LEN} comma fields, got {len(parts)}")

    t = FieldTracker()
    t.literal('header', _get(1), 'HLM')
    t.raw('vendor_id', _get(2))
    t.raw('fw_version', _get(3))
    imei_f = _get(4)
    if imei and imei_f is not None and imei_f != imei:
        t.custom('imei', imei_f, False, error=f"does not match requested {imei!r}")
    else:
        t.nonempty('imei', imei_f)
    t.integer('battery_pct', _get(5))
    t.integer('low_battery_pct', _get(6))
    t.integer('memory_pct', _get(7))
    t.integer('update_rate_ign_on_s', _get(8))
    t.integer('update_rate_ign_off_s', _get(9))
    t.raw('digital_input', _get(10))

    ain = _get(11)
    if ain is None:
        t.custom('analog_in_1', None, False)
        t.custom('analog_in_2', None, False)
    else:
        m = _AIN_SPACE_RE.match(ain)
        if not m:
            t.custom('analog_in_1', ain, False, error="analog input field does not match '<AIN1> <AIN2>' (space-separated)")
            t.custom('analog_in_2', None, False)
        else:
            t.number('analog_in_1', m.group(1))
            t.number('analog_in_2', m.group(2))

    t.literal('end_marker', _get(12), '*')

    return ValidationResult('health', matched=True, fields=t.fields, extra_errors=extra_errors)


# spec field 1 ('PVT' literal) through field 49 (checksum); index i here == parts[i+1]
_PVT_FIELD_NAMES = [
    'header', 'vendor_id', 'fw_version', 'packet_type', 'alert_id',
    'packet_status', 'imei', 'vehicle_reg_no', 'gps_fix', 'date', 'time',
    'latitude', 'lat_dir', 'longitude', 'lon_dir', 'speed', 'heading',
    'satellites', 'altitude', 'pdop', 'hdop', 'network_operator',
    'ignition', 'main_power', 'ext_voltage', 'batt_voltage',
    'emergency_status', 'box_tamper', 'csq', 'mcc', 'mnc', 'lac', 'cell_id',
    'nmr1_cell', 'nmr1_lac', 'nmr1_sig', 'nmr2_cell', 'nmr2_lac', 'nmr2_sig',
    'nmr3_cell', 'nmr3_lac', 'nmr3_sig', 'nmr4_cell', 'nmr4_lac', 'nmr4_sig',
    'digital_input', 'digital_output', 'frame_number', 'checksum',
]
_PVT_EXPECTED_LEN = 51  # '$' + 49 fields + '*' terminator
_PVT_CHECKSUM_PART_IDX = 49


def _validate_pvt_common(t, fields_by_name, imei):
    imei_f = fields_by_name.get('imei')
    if imei and imei_f is not None and imei_f != imei:
        t.custom('imei', imei_f, False, error=f"does not match requested {imei!r}")
    else:
        t.nonempty('imei', imei_f)
    t.enum('packet_status', fields_by_name.get('packet_status'), {'L', 'H'})
    t.enum('gps_fix', fields_by_name.get('gps_fix'), {'0', '1'})
    t.enum('lat_dir', fields_by_name.get('lat_dir'), {'N', 'S'})
    t.enum('lon_dir', fields_by_name.get('lon_dir'), {'E', 'W'})
    t.enum('box_tamper', fields_by_name.get('box_tamper'), {'C', 'O'})
    for name in ('latitude', 'longitude', 'speed', 'heading', 'altitude', 'pdop', 'hdop',
                 'ext_voltage', 'batt_voltage'):
        t.number(name, fields_by_name.get(name))
    for name in ('satellites', 'ignition', 'main_power', 'emergency_status', 'csq', 'mcc', 'mnc'):
        t.integer(name, fields_by_name.get(name))
    frame = fields_by_name.get('frame_number')
    if frame is not None:
        t.custom('frame_number', frame, frame.isdigit() and len(frame) == 6,
                  error='must be 6 zero-padded digits')
    else:
        t.custom('frame_number', None, False)


def validate_arai_pvt(raw, imei=None):
    """$,PVT,<VENDOR>,<FW>,<TYPE>,<ALERTID>,...,<DIN>,<DOUT>,<FRAME>,<CS>,*\\r\\n"""
    raw = raw.strip()
    parts = raw.split(',')
    if len(parts) < 2 or parts[0] != '$' or parts[1] != 'PVT':
        return ValidationResult('tracking', matched=False)

    packet_type = parts[4] if len(parts) > 4 else None
    alert_id = parts[5] if len(parts) > 5 else None
    allows_trailing_extra = (packet_type == 'OT' and alert_id == '12') or \
                             (packet_type == 'EA' and alert_id == '10')

    extra_errors = []
    if len(parts) < _PVT_EXPECTED_LEN:
        extra_errors.append(f"expected at least {_PVT_EXPECTED_LEN} comma fields, got {len(parts)}")
    elif len(parts) > _PVT_EXPECTED_LEN and not allows_trailing_extra:
        extra_errors.append(
            f"expected {_PVT_EXPECTED_LEN} comma fields, got {len(parts)} "
            f"(extra trailing fields not expected for packet_type={packet_type!r}, alert_id={alert_id!r})"
        )

    def _get(i):
        return parts[i] if i < len(parts) else None

    raw_fields = {name: _get(i + 1) for i, name in enumerate(_PVT_FIELD_NAMES)}

    t = FieldTracker()
    t.literal('header', raw_fields['header'], 'PVT')
    t.raw('vendor_id', raw_fields['vendor_id'])
    t.raw('fw_version', raw_fields['fw_version'])
    t.nonempty('packet_type', raw_fields['packet_type'])
    t.nonempty('alert_id', raw_fields['alert_id'])
    t.nonempty('vehicle_reg_no', raw_fields['vehicle_reg_no'])
    t.raw('date', raw_fields['date'])
    t.raw('time', raw_fields['time'])
    t.raw('network_operator', raw_fields['network_operator'])
    for name in ('lac', 'cell_id', 'nmr1_cell', 'nmr1_lac', 'nmr2_cell', 'nmr2_lac',
                 'nmr3_cell', 'nmr3_lac', 'nmr4_cell', 'nmr4_lac', 'digital_input', 'digital_output'):
        t.raw(name, raw_fields[name])
    for name in ('nmr1_sig', 'nmr2_sig', 'nmr3_sig', 'nmr4_sig'):
        t.integer(name, raw_fields[name])

    _validate_pvt_common(t, raw_fields, imei)

    checksum_field = raw_fields['checksum']
    checksum_ok = None
    if checksum_field is None:
        t.custom('checksum', None, False)
    elif not _HEX2_RE.match(checksum_field):
        t.custom('checksum', checksum_field, False, error='must be 2 hex digits')
    else:
        if len(parts) > _PVT_CHECKSUM_PART_IDX:
            prefix = ','.join(parts[1:_PVT_CHECKSUM_PART_IDX]) + ','
            expected = _xor_checksum_hex(prefix)
            checksum_ok = expected.upper() == checksum_field.upper()
            t.custom('checksum', checksum_field, checksum_ok,
                      error=None if checksum_ok else f'mismatch: packet says {checksum_field!r}, computed {expected!r}')
        else:
            t.raw('checksum', checksum_field)

    return ValidationResult('tracking', matched=True, fields=t.fields, checksum_ok=checksum_ok,
                             extra_errors=extra_errors)


_EPB_FIELD_NAMES = [
    'header', 'msg_type', 'imei', 'packet_status', 'datetime', 'gnss_valid',
    'latitude', 'lat_dir', 'longitude', 'lon_dir', 'altitude', 'speed',
    'hdop_placeholder', 'provider', 'vehicle_reg_no', 'reply_no',
    'end_marker', 'checksum',
]
_EPB_EXPECTED_LEN = 19


def validate_arai_epb(raw, imei=None):
    """$,EPB,<MSGTYPE>,<IMEI>,<PKTSTATUS>,<DATE><TIME>,<GNSSVALID>,...,<VRN>,<REPLYNO>,*,<CS>

    Covers emergency start (msg_type=EMR), end (msg_type=SEM), and stored/
    queued-while-offline (packet_status=SP) sub-types.

    Checksum verification is intentionally skipped (checksum_ok stays None)
    -- the source protocol reference disagrees with itself on whether a
    comma precedes the checksum for this packet class.
    """
    raw = raw.strip()
    parts = raw.split(',')
    if len(parts) < 2 or parts[0] != '$' or parts[1] != 'EPB':
        return ValidationResult('emergency', matched=False)

    msg_type = parts[2] if len(parts) > 2 else None
    allows_trailing_extra = msg_type == 'EMR'

    extra_errors = []
    if len(parts) < _EPB_EXPECTED_LEN:
        extra_errors.append(f"expected at least {_EPB_EXPECTED_LEN} comma fields, got {len(parts)}")
    elif len(parts) > _EPB_EXPECTED_LEN and not allows_trailing_extra:
        extra_errors.append(
            f"expected {_EPB_EXPECTED_LEN} comma fields, got {len(parts)} "
            f"(extra trailing fields not expected for msg_type={msg_type!r})"
        )

    def _get(i):
        return parts[i] if i < len(parts) else None

    raw_fields = {name: _get(i + 1) for i, name in enumerate(_EPB_FIELD_NAMES)}

    t = FieldTracker()
    t.literal('header', raw_fields['header'], 'EPB')
    t.enum('msg_type', raw_fields['msg_type'], {'EMR', 'SEM'})
    imei_f = raw_fields['imei']
    if imei and imei_f is not None and imei_f != imei:
        t.custom('imei', imei_f, False, error=f"does not match requested {imei!r}")
    else:
        t.nonempty('imei', imei_f)
    t.enum('packet_status', raw_fields['packet_status'], {'NM', 'SP'})
    dt = raw_fields['datetime']
    if dt is not None:
        t.custom('datetime', dt, dt.isdigit() and len(dt) == 12, error='must be 12 digits (DDMMYY+HHMMSS)')
    else:
        t.custom('datetime', None, False)
    t.enum('gnss_valid', raw_fields['gnss_valid'], {'A', 'V'})
    t.number('latitude', raw_fields['latitude'])
    t.enum('lat_dir', raw_fields['lat_dir'], {'N', 'S'})
    t.number('longitude', raw_fields['longitude'])
    t.enum('lon_dir', raw_fields['lon_dir'], {'E', 'W'})
    t.number('altitude', raw_fields['altitude'])
    t.number('speed', raw_fields['speed'])
    t.literal('hdop_placeholder', raw_fields['hdop_placeholder'], '0.000')
    t.literal('provider', raw_fields['provider'], 'G')
    t.nonempty('vehicle_reg_no', raw_fields['vehicle_reg_no'])
    t.raw('reply_no', raw_fields['reply_no'])
    t.literal('end_marker', raw_fields['end_marker'], '*')
    if raw_fields['checksum'] is not None:
        t.custom('checksum', raw_fields['checksum'], bool(_HEX2_RE.match(raw_fields['checksum'])),
                  error='must be 2 hex digits' if not _HEX2_RE.match(raw_fields['checksum']) else None)
    else:
        t.custom('checksum', None, False)

    return ValidationResult('emergency', matched=True, fields=t.fields, checksum_ok=None,
                             extra_errors=extra_errors)


# ---------------------------------------------------------------------------
# Amendment 3
# ---------------------------------------------------------------------------

_LGN_A3_FIELD_NAMES = [
    'header', 'vehicle_reg_no', 'imei', 'iccid', 'fw_version', 'proto_version',
    'latitude', 'lat_dir', 'longitude', 'lon_dir', 'end_marker', 'checksum',
]
_LGN_A3_EXPECTED_LEN = 13
_LGN_A3_CHECKSUM_PART_IDX = 12


def validate_amendment3_login(raw, imei=None):
    """$,LGN,<VRN>,<IMEI>,<ICCID>,<FW>,<PROTO>,<LAT>,<LATDIR>,<LON>,<LONDIR>,*,<CS>\\r\\n"""
    raw = raw.strip()
    parts = raw.split(',')
    if len(parts) < 2 or parts[0] != '$' or parts[1] != 'LGN':
        return ValidationResult('login', matched=False)

    extra_errors = []
    if len(parts) != _LGN_A3_EXPECTED_LEN:
        extra_errors.append(f"expected {_LGN_A3_EXPECTED_LEN} comma fields, got {len(parts)}")

    def _get(i):
        return parts[i] if i < len(parts) else None

    raw_fields = {name: _get(i + 1) for i, name in enumerate(_LGN_A3_FIELD_NAMES)}

    t = FieldTracker()
    t.literal('header', raw_fields['header'], 'LGN')
    t.nonempty('vehicle_reg_no', raw_fields['vehicle_reg_no'])
    imei_f = raw_fields['imei']
    if imei and imei_f is not None and imei_f != imei:
        t.custom('imei', imei_f, False, error=f"does not match requested {imei!r}")
    else:
        t.nonempty('imei', imei_f)
    t.raw('iccid', raw_fields['iccid'])
    t.nonempty('fw_version', raw_fields['fw_version'])
    t.nonempty('proto_version', raw_fields['proto_version'])
    t.number('latitude', raw_fields['latitude'])
    t.enum('lat_dir', raw_fields['lat_dir'], {'N', 'S'})
    t.number('longitude', raw_fields['longitude'])
    t.enum('lon_dir', raw_fields['lon_dir'], {'E', 'W'})
    t.literal('end_marker', raw_fields['end_marker'], '*')

    checksum_field = raw_fields['checksum']
    checksum_ok = None
    if checksum_field is None:
        t.custom('checksum', None, False)
    elif not _HEX2_RE.match(checksum_field):
        t.custom('checksum', checksum_field, False, error='must be 2 hex digits')
    else:
        if len(parts) > _LGN_A3_CHECKSUM_PART_IDX:
            prefix = ','.join(parts[1:_LGN_A3_CHECKSUM_PART_IDX]) + ','
            expected = _xor_checksum_hex(prefix)
            checksum_ok = expected.upper() == checksum_field.upper()
            t.custom('checksum', checksum_field, checksum_ok,
                      error=None if checksum_ok else f'mismatch: packet says {checksum_field!r}, computed {expected!r}')
        else:
            t.raw('checksum', checksum_field)

    return ValidationResult('login', matched=True, fields=t.fields, checksum_ok=checksum_ok,
                             extra_errors=extra_errors)


_HLM_A3_FIELD_NAMES = [
    'header', 'vendor_id', 'fw_version', 'imei', 'battery_pct', 'low_battery_pct',
    'memory_pct', 'update_rate_ign_on_s', 'update_rate_ign_off_s', 'digital_io',
    'analog_in_1', 'analog_in_2', 'end_marker', 'checksum',
]
_HLM_A3_EXPECTED_LEN = 15
_HLM_A3_CHECKSUM_PART_IDX = 14


def validate_amendment3_health(raw, imei=None):
    """$,HLM,<VENDOR>,<FW>,<IMEI>,<BATT%>,<LOWBATT%>,<MEM%>,<URI_ON>,<URI_OFF>,<DIN><DOUT>,<AIN1>,<AIN2>,*,<CS>\\r\\n"""
    raw = raw.strip()
    parts = raw.split(',')
    if len(parts) < 2 or parts[0] != '$' or parts[1] != 'HLM':
        return ValidationResult('health', matched=False)

    extra_errors = []
    if len(parts) != _HLM_A3_EXPECTED_LEN:
        extra_errors.append(f"expected {_HLM_A3_EXPECTED_LEN} comma fields, got {len(parts)}")

    def _get(i):
        return parts[i] if i < len(parts) else None

    raw_fields = {name: _get(i + 1) for i, name in enumerate(_HLM_A3_FIELD_NAMES)}

    t = FieldTracker()
    t.literal('header', raw_fields['header'], 'HLM')
    t.raw('vendor_id', raw_fields['vendor_id'])
    t.raw('fw_version', raw_fields['fw_version'])
    imei_f = raw_fields['imei']
    if imei and imei_f is not None and imei_f != imei:
        t.custom('imei', imei_f, False, error=f"does not match requested {imei!r}")
    else:
        t.nonempty('imei', imei_f)
    t.integer('battery_pct', raw_fields['battery_pct'])
    t.integer('low_battery_pct', raw_fields['low_battery_pct'])
    t.integer('memory_pct', raw_fields['memory_pct'])
    t.integer('update_rate_ign_on_s', raw_fields['update_rate_ign_on_s'])
    t.integer('update_rate_ign_off_s', raw_fields['update_rate_ign_off_s'])
    t.raw('digital_io', raw_fields['digital_io'])
    t.number('analog_in_1', raw_fields['analog_in_1'])
    t.number('analog_in_2', raw_fields['analog_in_2'])
    t.literal('end_marker', raw_fields['end_marker'], '*')

    checksum_field = raw_fields['checksum']
    checksum_ok = None
    if checksum_field is None:
        t.custom('checksum', None, False)
    elif not _HEX2_RE.match(checksum_field):
        t.custom('checksum', checksum_field, False, error='must be 2 hex digits')
    else:
        if len(parts) > _HLM_A3_CHECKSUM_PART_IDX:
            prefix = ','.join(parts[1:_HLM_A3_CHECKSUM_PART_IDX]) + ','
            expected = _xor_checksum_hex(prefix)
            checksum_ok = expected.upper() == checksum_field.upper()
            t.custom('checksum', checksum_field, checksum_ok,
                      error=None if checksum_ok else f'mismatch: packet says {checksum_field!r}, computed {expected!r}')
        else:
            t.raw('checksum', checksum_field)

    return ValidationResult('health', matched=True, fields=t.fields, checksum_ok=checksum_ok,
                             extra_errors=extra_errors)


_PVT_A3_FIELD_NAMES = [
    'header', 'vendor_id', 'fw_version', 'packet_type', 'alert_id',
    'packet_status', 'imei', 'vehicle_reg_no', 'gps_fix', 'date', 'time',
    'latitude', 'lat_dir', 'longitude', 'lon_dir', 'speed', 'heading',
    'satellites', 'altitude', 'pdop', 'hdop', 'network_operator',
    'ignition', 'main_power', 'ext_voltage', 'batt_voltage',
    'emergency_status', 'box_tamper', 'csq', 'mcc', 'mnc', 'lac', 'cell_id',
    'nmr1_sig', 'nmr1_lac', 'nmr1_cell', 'nmr2_sig', 'nmr2_lac', 'nmr2_cell',
    'nmr3_sig', 'nmr3_lac', 'nmr3_cell', 'nmr4_sig', 'nmr4_lac', 'nmr4_cell',
    'digital_input', 'digital_output', 'frame_number',
    'analog_in_1', 'analog_in_2', 'delta_distance', 'ota_envelope',
    'end_marker', 'checksum',
]
_PVT_A3_EXPECTED_LEN = 55  # '$' + 54 fields
_PVT_A3_CHECKSUM_PART_IDX = 54


def _split_amendment3_pvt(raw):
    """Comma-split, but treat the parenthesized OTA-response envelope
    (which may itself contain commas, e.g. "(ip:port|SET|002:val:1,003:val:1)")
    as a single atomic field."""
    m = _ENVELOPE_RE.search(raw)
    if not m:
        return raw.split(',')
    before, envelope, after = raw[:m.start()], raw[m.start():m.end()], raw[m.end():]
    before_parts = before.split(',')
    after_parts = after.split(',')
    if before_parts and before_parts[-1] == '':
        before_parts = before_parts[:-1]
    if after_parts and after_parts[0] == '':
        after_parts = after_parts[1:]
    return before_parts + [envelope] + after_parts


def validate_amendment3_pvt(raw, imei=None):
    """Same as ARAI for fields 1-33 (header..cell_id), NMR order swapped
    (sig,lac,cell per neighbour), then digital_input/output/frame, then 4
    extra fields (AIN1, AIN2, delta-distance, OTA-response envelope) before
    the '*,<CS>' tail."""
    raw = raw.strip()
    parts = _split_amendment3_pvt(raw)
    if len(parts) < 2 or parts[0] != '$' or parts[1] != 'PVT':
        return ValidationResult('tracking', matched=False)

    extra_errors = []
    if len(parts) != _PVT_A3_EXPECTED_LEN:
        extra_errors.append(f"expected {_PVT_A3_EXPECTED_LEN} comma/envelope fields, got {len(parts)}")

    def _get(i):
        return parts[i] if i < len(parts) else None

    raw_fields = {name: _get(i + 1) for i, name in enumerate(_PVT_A3_FIELD_NAMES)}

    t = FieldTracker()
    t.literal('header', raw_fields['header'], 'PVT')
    t.raw('vendor_id', raw_fields['vendor_id'])
    t.raw('fw_version', raw_fields['fw_version'])
    t.nonempty('packet_type', raw_fields['packet_type'])
    t.nonempty('alert_id', raw_fields['alert_id'])
    t.nonempty('vehicle_reg_no', raw_fields['vehicle_reg_no'])
    t.raw('date', raw_fields['date'])
    t.raw('time', raw_fields['time'])
    t.raw('network_operator', raw_fields['network_operator'])
    for name in ('lac', 'cell_id', 'nmr1_lac', 'nmr1_cell', 'nmr2_lac', 'nmr2_cell',
                 'nmr3_lac', 'nmr3_cell', 'nmr4_lac', 'nmr4_cell', 'digital_input', 'digital_output'):
        t.raw(name, raw_fields[name])
    for name in ('nmr1_sig', 'nmr2_sig', 'nmr3_sig', 'nmr4_sig'):
        t.integer(name, raw_fields[name])

    _validate_pvt_common(t, raw_fields, imei)

    t.number('analog_in_1', raw_fields['analog_in_1'])
    t.number('analog_in_2', raw_fields['analog_in_2'])
    t.number('delta_distance', raw_fields['delta_distance'])

    envelope = raw_fields['ota_envelope']
    if envelope is None:
        t.custom('ota_envelope', None, False)
    else:
        t.custom('ota_envelope', envelope, envelope.startswith('(') and envelope.endswith(')'),
                  error=None if (envelope.startswith('(') and envelope.endswith(')')) else 'expected (...)-wrapped envelope')

    t.literal('end_marker', raw_fields['end_marker'], '*')

    checksum_field = raw_fields['checksum']
    checksum_ok = None
    if checksum_field is None:
        t.custom('checksum', None, False)
    elif not _HEX2_RE.match(checksum_field):
        t.custom('checksum', checksum_field, False, error='must be 2 hex digits')
    else:
        if len(parts) > _PVT_A3_CHECKSUM_PART_IDX:
            prefix = ','.join(parts[1:_PVT_A3_CHECKSUM_PART_IDX]) + ','
            expected = _xor_checksum_hex(prefix)
            checksum_ok = expected.upper() == checksum_field.upper()
            t.custom('checksum', checksum_field, checksum_ok,
                      error=None if checksum_ok else f'mismatch: packet says {checksum_field!r}, computed {expected!r}')
        else:
            t.raw('checksum', checksum_field)

    return ValidationResult('tracking', matched=True, fields=t.fields, checksum_ok=checksum_ok,
                             extra_errors=extra_errors)


_EPB_A3_FIELD_NAMES = [
    'header', 'msg_type', 'imei', 'packet_status', 'date', 'time', 'gnss_valid',
    'latitude', 'lat_dir', 'longitude', 'lon_dir', 'altitude', 'speed',
    'delta_distance', 'provider', 'vehicle_reg_no', 'emergency_sms_center',
    'end_marker', 'checksum',
]
_EPB_A3_EXPECTED_LEN = 20
_EPB_A3_CHECKSUM_PART_IDX = 19


def validate_amendment3_epb(raw, imei=None):
    """$,EPB,<MSGTYPE>,<IMEI>,<PKTSTATUS>,<DATE>,<TIME>,<GNSSVALID>,...,<VRN>,<EMERGENCY_SMS_CENTER>,*,<CS>\\r\\n

    TCP/server variant only (the SMS-fallback grammar is a different shape
    but never reaches the backend since it's device-to-SMS-center, not
    device-to-server -- nothing in GPSemDataLog would ever be that shape).
    """
    raw = raw.strip()
    parts = raw.split(',')
    if len(parts) < 2 or parts[0] != '$' or parts[1] != 'EPB':
        return ValidationResult('emergency', matched=False)

    extra_errors = []
    if len(parts) != _EPB_A3_EXPECTED_LEN:
        extra_errors.append(f"expected {_EPB_A3_EXPECTED_LEN} comma fields, got {len(parts)}")

    def _get(i):
        return parts[i] if i < len(parts) else None

    raw_fields = {name: _get(i + 1) for i, name in enumerate(_EPB_A3_FIELD_NAMES)}

    t = FieldTracker()
    t.literal('header', raw_fields['header'], 'EPB')
    t.enum('msg_type', raw_fields['msg_type'], {'EMR', 'SEM'})
    imei_f = raw_fields['imei']
    if imei and imei_f is not None and imei_f != imei:
        t.custom('imei', imei_f, False, error=f"does not match requested {imei!r}")
    else:
        t.nonempty('imei', imei_f)
    t.enum('packet_status', raw_fields['packet_status'], {'NM', 'SP'})
    t.raw('date', raw_fields['date'])
    t.raw('time', raw_fields['time'])
    t.enum('gnss_valid', raw_fields['gnss_valid'], {'A', 'V'})
    t.number('latitude', raw_fields['latitude'])
    t.enum('lat_dir', raw_fields['lat_dir'], {'N', 'S'})
    t.number('longitude', raw_fields['longitude'])
    t.enum('lon_dir', raw_fields['lon_dir'], {'E', 'W'})
    t.number('altitude', raw_fields['altitude'])
    t.number('speed', raw_fields['speed'])
    t.number('delta_distance', raw_fields['delta_distance'])
    t.literal('provider', raw_fields['provider'], 'G')
    t.nonempty('vehicle_reg_no', raw_fields['vehicle_reg_no'])
    t.raw('emergency_sms_center', raw_fields['emergency_sms_center'])
    t.literal('end_marker', raw_fields['end_marker'], '*')

    checksum_field = raw_fields['checksum']
    checksum_ok = None
    if checksum_field is None:
        t.custom('checksum', None, False)
    elif not _HEX2_RE.match(checksum_field):
        t.custom('checksum', checksum_field, False, error='must be 2 hex digits')
    else:
        if len(parts) > _EPB_A3_CHECKSUM_PART_IDX:
            prefix = ','.join(parts[1:_EPB_A3_CHECKSUM_PART_IDX]) + ','
            expected = _xor_checksum_hex(prefix)
            checksum_ok = expected.upper() == checksum_field.upper()
            t.custom('checksum', checksum_field, checksum_ok,
                      error=None if checksum_ok else f'mismatch: packet says {checksum_field!r}, computed {expected!r}')
        else:
            t.raw('checksum', checksum_field)

    return ValidationResult('emergency', matched=True, fields=t.fields, checksum_ok=checksum_ok,
                             extra_errors=extra_errors)


_VALIDATORS = {
    ARAI_FORMAT_ID: {
        'login': validate_arai_login,
        'health': validate_arai_health,
        'tracking': validate_arai_pvt,
        'emergency': validate_arai_epb,
    },
    AMENDMENT3_FORMAT_ID: {
        'login': validate_amendment3_login,
        'health': validate_amendment3_health,
        'tracking': validate_amendment3_pvt,
        'emergency': validate_amendment3_epb,
    },
}


def classify_and_validate(raw, category, imei=None, protocol_format=ARAI_FORMAT_ID):
    """Validate `raw` against `category` ('login'|'health'|'tracking'|'emergency')
    for the given protocol_format. Returns a ValidationResult, or None if the
    format/category combination isn't implemented."""
    fmt = PROTOCOL_FORMATS.get(protocol_format)
    if fmt is None or not fmt['implemented']:
        return None
    validator = _VALIDATORS.get(protocol_format, {}).get(category)
    if validator is None:
        return None
    return validator(raw, imei=imei)


# ---------------------------------------------------------------------------
# Alert-ID / packet-type reference (section 8 of the protocol reference)
# ---------------------------------------------------------------------------

ALERT_TYPE_REFERENCE = [
    {'packet_type': 'NR', 'alert_id': '01', 'applies_to': 'both', 'trigger': 'Normal periodic tracking, live (connected)'},
    {'packet_type': 'NR', 'alert_id': '02', 'applies_to': 'both', 'trigger': 'Normal periodic tracking, history (offline/flash-drained); also pre-boot placeholder'},
    {'packet_type': 'IN', 'alert_id': '07', 'applies_to': 'both', 'trigger': 'Ignition turned ON (edge)'},
    {'packet_type': 'IF', 'alert_id': '08', 'applies_to': 'both', 'trigger': 'Ignition turned OFF (edge)'},
    {'packet_type': 'BR', 'alert_id': '06', 'applies_to': 'both', 'trigger': 'Main/external power restored (edge)'},
    {'packet_type': 'BD', 'alert_id': '03', 'applies_to': 'both', 'trigger': 'Main/external power disconnected (edge)'},
    {'packet_type': 'BL', 'alert_id': '04', 'applies_to': 'both', 'trigger': 'Internal battery voltage drops below 3.5V (edge)'},
    {'packet_type': 'BH', 'alert_id': '05', 'applies_to': ARAI_FORMAT_ID, 'trigger': 'Internal battery recovers above 4.1V (edge)'},
    {'packet_type': 'BC', 'alert_id': '05', 'applies_to': AMENDMENT3_FORMAT_ID, 'trigger': 'Internal battery recovers above 4.1V (edge) -- Amendment 3 spelling of BH'},
    {'packet_type': 'TA', 'alert_id': '09', 'applies_to': 'both', 'trigger': 'Box tamper open/close transition, or SOS-exit tamper'},
    {'packet_type': 'TA', 'alert_id': '16', 'applies_to': 'both', 'trigger': 'Wire-cut: SOS line held >10s / released after cut'},
    {'packet_type': 'OS', 'alert_id': '17', 'applies_to': AMENDMENT3_FORMAT_ID, 'trigger': 'Overspeed edge: speed crosses above configured speed_limit_kmph'},
    {'packet_type': 'EA', 'alert_id': '10', 'applies_to': 'both', 'trigger': 'SOS/emergency activated (entry edge, or first cadence packet after entry)'},
    {'packet_type': 'EA', 'alert_id': '11', 'applies_to': 'both', 'trigger': 'One-shot "SOS disabled" alert (only if no concurrent tamper)'},
    {'packet_type': 'OT', 'alert_id': '12', 'applies_to': ARAI_FORMAT_ID, 'trigger': 'OT/command-response alert; plaintext debug tail appended'},
    {'packet_type': 'OA', 'alert_id': '12', 'applies_to': AMENDMENT3_FORMAT_ID, 'trigger': 'Same trigger as OT,12; structured OTA-response envelope in packet body'},
]


def scan_tracking_alert_combinations(rows, split_fn, imei, protocol_format):
    """rows: iterable of (timestamp, raw_data), newest first.
    split_fn: callable(raw_data) -> list of '$'-prefixed fragments.
    Returns {(packet_type, alert_id): last_seen_timestamp} across every
    tracking-shaped fragment found (not just the most recent)."""
    seen = {}
    for ts, raw_data in rows:
        for frag in split_fn(raw_data):
            result = classify_and_validate(frag, 'tracking', imei=imei, protocol_format=protocol_format)
            if result is None or not result.matched:
                continue
            pt = _field_value(result.fields, 'packet_type')
            aid = _field_value(result.fields, 'alert_id')
            if not pt or not aid:
                continue
            key = (pt, aid)
            if key not in seen:
                seen[key] = ts
    return seen
