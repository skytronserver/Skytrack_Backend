"""
Technical onboarding testing: courier tracking, per-IMEI stock receipt
confirmation, the backend-driven checkpoint test catalog, and the
per-IMEI test-execution engine (start / heartbeat / refresh-log / complete).

Data-source strategy: the 5 demo IMEIs used during onboarding have no
DeviceStock/verified DeviceTag, so the parsed telemetry tables (GPSData,
AlertsLog, EMGPSLocation) stay empty for them. Automated checks instead
scan the raw, unconditionally-written GPSDataLog/GPSemDataLog tables by
IMEI substring within a bounded time window -- the same strategy already
used by device_tagging_step4_packet_check (views.py) -- or read the
structured OTACommandHistory/ActivationCommandDispatch ack fields.
"""

import math
import re
import statistics
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from . import protocol_formats as pf
from .dev_views import _dev_only
from .models import (
    DeviceModelTechnicalOnboardingRequest,
    DeviceModelTechnicalOnboardingDemoDevice,
    TechnicalOnboardingTestCase,
    TechnicalOnboardingTestExecution,
    TechnicalOnboardingCommandDispatch,
    GPSDataLog,
    GPSemDataLog,
    OTACommandHistory,
    ActivationCommandDispatch,
)
from .rbac import require_permission
from .serializers import (
    DeviceModelTechnicalOnboardingRequestDetailSerializer,
    TechnicalOnboardingCourierTrackingSerializer,
    TechnicalOnboardingConfirmReceiptSerializer,
    TechnicalOnboardingTestCaseSerializer,
    TechnicalOnboardingTestBoardRequestSerializer,
    TechnicalOnboardingStartTestSerializer,
    TechnicalOnboardingExecutionActionSerializer,
    TechnicalOnboardingCompleteTestSerializer,
    TechnicalOnboardingSendTestCommandSerializer,
    TechnicalOnboardingRefreshTestLogSerializer,
    TechnicalOnboardingTestExecutionSerializer,
    TechnicalOnboardingDemoDeviceHistorySerializer,
    build_checkpoint_status_map,
)
from .views import (
    send_general_mqtt_message,
    validate_inputs,
    get_user_object,
    _packet_fields,
    _packet_type_in_header,
    _extract_pvt_datetime,
    _extract_pvt_lat_lon,
)

# Packets older than this are not scanned; also bounds each query, since
# GPSDataLog/GPSemDataLog have no IMEI column/index (see docstring above).
GPS_PACKET_SCAN_LIMIT = 5000

# An in_progress execution with no heartbeat inside this window is
# considered abandoned (browser/tab closed) and auto-marked incomplete.
STALE_HEARTBEAT_SECONDS = 45

SOURCE_TABLE_LABEL = {
    'gps': 'GPSDataLog',
    'gpsem': 'GPSemDataLog',
    'ota_command': 'OTACommandHistory',
    'activation_command': 'ActivationCommandDispatch',
    'firmware_diff': 'GPSDataLog',
    'voltage_internal': 'GPSDataLog',
    'voltage_external': 'GPSDataLog',
    'esim_primary_to_secondary': 'GPSDataLog',
    'esim_secondary_to_primary': 'GPSDataLog',
    'vehicle_registration_diff': 'GPSDataLog',
    'reboot_restart_gap': 'GPSDataLog + OTACommandHistory',
    'pvt_packet_drop': 'GPSDataLog + GPSemDataLog',
}

# The eSIM switch tests cross-check each other's network order.
ESIM_SIBLING_SOURCE = {
    'esim_primary_to_secondary': 'esim_secondary_to_primary',
    'esim_secondary_to_primary': 'esim_primary_to_secondary',
}

# _packet_fields() index (after the leading '$'/'$,' is normalised away) for
# the PVT fields these distinct-value checks read.
PVT_NETWORK_OPERATOR_IDX = 21
PVT_MAIN_VOLTAGE_IDX = 24       # external / main input voltage
PVT_INTERNAL_VOLTAGE_IDX = 25   # internal / backup battery voltage
PVT_VEHICLE_REG_NO_IDX = 7

# PVT field offsets relative to the 'PVT' token, used by the history API.
PVT_OFFSET_PACKET_TYPE = 3
PVT_OFFSET_FIRMWARE = 2
PVT_OFFSET_ALERT_ID = 4
PVT_OFFSET_PACKET_STATUS = 5    # L = live, H = history (buffered)
PVT_OFFSET_IMEI = 6
PVT_OFFSET_VEHICLE_REG_NO = 7
PVT_OFFSET_SPEED = 15
PVT_OFFSET_HEADING = 16
PVT_OFFSET_NETWORK_OPERATOR = 21
PVT_OFFSET_IGNITION = 22        # then main power, external voltage, internal voltage
PVT_OFFSET_EMERGENCY_STATUS = 26  # then box tamper
PVT_OFFSET_MCC = 29             # then MNC, LAC, cell ID

# PVT field offset of the GPS fix flag (1 = fix, 0 = no fix).
PVT_OFFSET_GPS_FIX = 8

# Packet drop test (#41): a fixed window from the test start in which the
# device, moving with emergency ON, must send one PVT and one EPB packet
# every ~5s. Both streams' average gap must fall inside the band below and
# every packet must carry a valid GPS fix and coordinate. The window length
# comes from the test case's scan_window_seconds (falls back to the default).
DEFAULT_PVT_DROP_WINDOW_SECONDS = 15 * 60
PVT_DROP_AVG_GAP_MIN_SECONDS = 4
PVT_DROP_AVG_GAP_MAX_SECONDS = 6
PVT_DROP_MAX_SINGLE_GAP_SECONDS = 180
PVT_DROP_MOVING_SPEED_KMPH = 10
PVT_DROP_MIN_MOVING_SHARE = 0.70

# Times in tester-facing failure reasons are shown in IST.
IST = ZoneInfo('Asia/Kolkata')

# A device timestamp is only trusted inside this band around the server
# receive time: devices without a GPS fix report junk clocks (e.g. year
# 2080), while buffered history (H) packets legitimately arrive late.
DEVICE_CLOCK_MAX_AHEAD = timedelta(minutes=5)
DEVICE_CLOCK_MAX_BEHIND = timedelta(days=7)

# Demo-device history API: how late a buffered (H) packet may arrive after
# its device timestamp and still be picked up, and a hard cap on rows read.
HISTORY_LATE_ARRIVAL_SLACK = timedelta(hours=1)
HISTORY_ROW_LIMIT = 150000

# Default minimum silence (no packets) after a reboot command is sent
# before resumed packets count as proof of an actual restart, used when
# the test case doesn't set its own max_interval_seconds.
DEFAULT_REBOOT_GAP_SECONDS = 20


# ===========================================================================
# Shared helpers
# ===========================================================================

def _sweep_stale_executions(onboarding_request):
    """Flip any in_progress execution with a stale heartbeat to incomplete."""
    cutoff = timezone.now() - timedelta(seconds=STALE_HEARTBEAT_SECONDS)
    TechnicalOnboardingTestExecution.objects.filter(
        onboarding_request=onboarding_request,
        status='in_progress',
        last_heartbeat_at__lt=cutoff,
    ).update(status='incomplete')


def _complete_counts_by_test_case(onboarding_request):
    """{test_case_id: number of demo devices with a complete execution}, in one query."""
    return dict(
        TechnicalOnboardingTestExecution.objects.filter(
            onboarding_request=onboarding_request,
            status='complete',
        ).values_list('test_case_id').annotate(complete_count=Count('id'))
    )


def _current_unlocked_serial_no(onboarding_request):
    """
    Lowest serial_no among active, non-optional test cases where not all
    5 demo devices are complete. None means everything gate-worthy is done.
    """
    device_count = onboarding_request.demo_devices.count()
    complete_counts = _complete_counts_by_test_case(onboarding_request)
    test_cases = TechnicalOnboardingTestCase.objects.filter(
        active=True, is_optional=False
    ).order_by('serial_no').values_list('id', 'serial_no')
    for test_case_id, serial_no in test_cases:
        if complete_counts.get(test_case_id, 0) < device_count:
            return serial_no
    return None


def _all_tests_complete(onboarding_request):
    device_count = onboarding_request.demo_devices.count()
    if device_count == 0:
        return False
    complete_counts = _complete_counts_by_test_case(onboarding_request)
    test_case_ids = TechnicalOnboardingTestCase.objects.filter(
        active=True, is_optional=False
    ).values_list('id', flat=True)
    return all(complete_counts.get(test_case_id, 0) >= device_count for test_case_id in test_case_ids)


def _window_start(execution):
    test_case = execution.test_case
    now = timezone.now()
    window_floor = now - timedelta(seconds=test_case.scan_window_seconds)
    started_at = execution.started_at or window_floor
    return max(window_floor, started_at)


def _run_test_check(execution):
    """
    Dispatches on test_case.source_table and returns a snapshot dict, with
    the commands sent for this execution (and any device replies) attached.
    Does not persist anything -- the caller decides what to do with it.
    """
    snapshot = _run_mode_check(execution)
    snapshot['commands_sent'] = _commands_sent(execution)
    return snapshot


def _run_mode_check(execution):
    test_case = execution.test_case
    imei = execution.demo_device.imei
    now = timezone.now()

    if test_case.source_table == 'manual':
        return {
            'mode': 'manual',
            'pass': None,
            'reason': 'No automated log source configured for this test. Record the observed result directly.',
            'refreshed_at': now.isoformat(),
        }

    if test_case.source_table == 'pvt_packet_drop':
        return _pvt_packet_drop_check(execution, imei, now)

    window_start = _window_start(execution)

    handler = _MODE_HANDLERS.get(test_case.source_table)
    if handler:
        snapshot = handler(execution, imei, window_start, now)
        snapshot.setdefault('mode', test_case.source_table)
        snapshot.setdefault('window_start', window_start.isoformat())
        snapshot.setdefault('refreshed_at', now.isoformat())
        return snapshot

    if test_case.source_table in ('ota_command', 'activation_command'):
        if test_case.source_table == 'ota_command':
            qs = OTACommandHistory.objects.filter(imei=imei, sent_at__gte=window_start, send_status='replied')
            text_field = 'command_sent'
        else:
            qs = ActivationCommandDispatch.objects.filter(
                imei=imei, sent_at__gte=window_start, send_status='replied'
            )
            text_field = 'command_sent'

        pattern = re.compile(test_case.regex_pattern) if test_case.regex_pattern else None
        rows = list(qs.order_by('-sent_at')[:GPS_PACKET_SCAN_LIMIT])
        matched = []
        for row in rows:
            text = getattr(row, text_field, '') or ''
            if pattern and not pattern.search(text):
                continue
            matched.append(row)

        matched_count = len(matched)
        result_pass = matched_count >= test_case.min_match_count
        samples = [
            {'command_sent': getattr(r, text_field, None), 'sent_at': r.sent_at.isoformat() if r.sent_at else None}
            for r in matched[:5]
        ]
        reason = None if result_pass else (
            f"Only {matched_count} acknowledged command(s) found, need at least {test_case.min_match_count}."
        )
        return {
            'mode': test_case.source_table,
            'matched_count': matched_count,
            'required': test_case.min_match_count,
            'pass': result_pass,
            'reason': reason,
            'samples': samples,
            'window_start': window_start.isoformat(),
            'refreshed_at': now.isoformat(),
        }

    return {'mode': 'unknown', 'pass': False, 'reason': 'Unrecognised source_table.', 'refreshed_at': now.isoformat()}


# ===========================================================================
# Packet parsing helpers for the automated checks
# ===========================================================================

def _scan_rows(model, imei, start, end=None, limit=GPS_PACKET_SCAN_LIMIT):
    """(raw_data, server_time) rows for an IMEI, oldest first."""
    qs = model.objects.filter(timestamp__gte=start, raw_data__contains=imei)
    if end is not None:
        qs = qs.filter(timestamp__lte=end)
    rows = list(qs.order_by('-timestamp').values_list('raw_data', 'timestamp')[:limit])
    rows.reverse()
    return rows


def _fragments(raw_data):
    """
    One raw_data row can hold several '$'-framed packets back to back
    ('$HEL,...*$PVT,...'). The whole row comes first so an ARAI login
    packet -- which has a '$' in every field -- is still seen intact.
    """
    raw = (raw_data or '').strip()
    pieces = [raw] if raw else []
    for part in raw.split('$'):
        frag = '$' + part.strip()
        if len(frag) > 4 and frag != raw:
            pieces.append(frag)
    return pieces


def _packets_in_row(raw_data):
    """The individual packets in a row: an ARAI login row as-is, else each '$' packet."""
    pieces = _fragments(raw_data)
    if pieces and _packet_kind(pieces[0]) == 'login':
        return [pieces[0]]
    return pieces[1:] or pieces


def _field(parts, idx, offset):
    position = idx + offset
    return parts[position].strip() if len(parts) > position else None


def _pvt_info(raw_data, server_time):
    """
    Parsed view of one PVT packet for checks and display, or None.
    'time' is the device time when plausible, else the server time.
    """
    parts = _packet_fields(raw_data)
    idx = _pvt_index(parts)
    if idx is None:
        return None
    effective_time, time_source = _packet_time(raw_data, server_time)
    latitude, longitude = _extract_pvt_lat_lon(raw_data)
    return {
        'raw_data': raw_data,
        'time': effective_time,
        'time_source': time_source,
        'packet_type': (_field(parts, idx, PVT_OFFSET_PACKET_TYPE) or '').upper(),
        'alert_id': _field(parts, idx, PVT_OFFSET_ALERT_ID),
        'packet_status': (_field(parts, idx, PVT_OFFSET_PACKET_STATUS) or '').upper(),
        'vehicle_reg_no': _field(parts, idx, PVT_OFFSET_VEHICLE_REG_NO),
        'firmware': _field(parts, idx, PVT_OFFSET_FIRMWARE),
        'gps_fix': _field(parts, idx, PVT_OFFSET_GPS_FIX),
        'latitude': float(latitude) if latitude is not None else None,
        'longitude': float(longitude) if longitude is not None else None,
        'speed': _to_float(_field(parts, idx, PVT_OFFSET_SPEED)),
        'heading': _to_float(_field(parts, idx, PVT_OFFSET_HEADING)),
        'network_operator': _field(parts, idx, PVT_OFFSET_NETWORK_OPERATOR),
        'ignition': _field(parts, idx, PVT_OFFSET_IGNITION),
        'main_power': _field(parts, idx, PVT_OFFSET_IGNITION + 1),
        'external_voltage': _field(parts, idx, PVT_OFFSET_IGNITION + 2),
        'internal_voltage': _field(parts, idx, PVT_OFFSET_IGNITION + 3),
        'emergency_status': _field(parts, idx, PVT_OFFSET_EMERGENCY_STATUS),
        'box_tamper': _field(parts, idx, PVT_OFFSET_EMERGENCY_STATUS + 1),
        'mcc': _field(parts, idx, PVT_OFFSET_MCC),
        'mnc': _field(parts, idx, PVT_OFFSET_MCC + 1),
        'lac': _field(parts, idx, PVT_OFFSET_MCC + 2),
        'cell_id': _field(parts, idx, PVT_OFFSET_MCC + 3),
    }


def _pvt_packets(imei, start, end=None, lookback_seconds=0):
    """Every PVT packet for the IMEI (split out of multi-packet rows), oldest first by device time."""
    packets = []
    for raw_data, server_time in _scan_rows(GPSDataLog, imei, start - timedelta(seconds=lookback_seconds), end):
        for frag in _packets_in_row(raw_data):
            info = _pvt_info(frag, server_time)
            if info:
                packets.append(info)
    # The same packet is sometimes logged twice; count it once.
    seen, unique = set(), []
    for packet in packets:
        if packet['raw_data'] not in seen:
            seen.add(packet['raw_data'])
            unique.append(packet)
    unique.sort(key=lambda p: p['time'])
    return unique


_DISPLAY_KEYS = (
    'packet_type', 'alert_id', 'packet_status', 'vehicle_reg_no', 'firmware', 'gps_fix',
    'latitude', 'longitude', 'speed', 'heading', 'network_operator', 'ignition', 'main_power',
    'external_voltage', 'internal_voltage', 'emergency_status', 'box_tamper', 'mcc', 'mnc', 'lac', 'cell_id',
)


def _sample(packet, **extra):
    """A snapshot sample: the usual raw_data/timestamp plus parsed fields under 'packet'."""
    sample = {
        'raw_data': packet['raw_data'],
        'timestamp': packet['time'].isoformat(),
        'packet': {k: packet.get(k) for k in _DISPLAY_KEYS},
    }
    sample.update(extra)
    return sample


def _haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Onboarding validates every packet against one reference format: the
# layout sent by the reference test device AS01AA0005 (ARAI layout --
# see protocol_formats.validate_arai_*), checksum included.
REFERENCE_PROTOCOL_FORMAT = pf.ARAI_FORMAT_ID
REFERENCE_DEVICE = 'AS01AA0005'
REFERENCE_PACKET_START = {
    'login': '$<VRN>,$<IMEI>,$<FW>,$<PROTO>,$<LAT><N|S><LON><E|W>',
    'health': '$,HLM,...',
    'tracking': '$,PVT,...',
    'emergency': '$,EPB,...',
}


def _validate_reference_format(frag, category, imei):
    """
    (format_id, ValidationResult) against the reference format, or
    (None, None) when the packet doesn't have the reference layout at all.
    """
    result = pf.classify_and_validate(frag, category, imei=imei, protocol_format=REFERENCE_PROTOCOL_FORMAT)
    if result is None or not result.matched:
        return None, None
    return REFERENCE_PROTOCOL_FORMAT, result


# Header codes seen for each packet kind across ARAI / Amendment 3 /
# vendor variants -- used to recognise a packet even when its fields
# don't validate.
PACKET_KIND_HEADERS = {
    'login': ('LGN',),
    'health': ('HLM', 'HEL'),
    'tracking': ('PVT',),
    'emergency': ('EPB',),
}


def _packet_kind(frag):
    """'login' | 'health' | 'tracking' | 'emergency' | None, by header only."""
    raw = frag.strip()
    parts = [p.strip() for p in raw.split(',')]
    # ARAI login: $<VRN>,$<IMEI>,$<FW>,$<PROTO>,$<LATLON> -- every field '$'-prefixed.
    if len(parts) == 5 and all(p.startswith('$') and len(p) > 1 for p in parts):
        return 'login'
    header = _packet_fields(raw)[:2]
    for kind, codes in PACKET_KIND_HEADERS.items():
        if any(h.upper().rstrip('*') in codes for h in header):
            return kind
    return None


def _fail_reason(lines):
    """'Failed N checks: 1) ... 2) ...' or None."""
    if not lines:
        return None
    if len(lines) == 1:
        return lines[0]
    return f"Failed {len(lines)} checks: " + ' '.join(f"{n}) {line}" for n, line in enumerate(lines, 1))


def _cfg(test_case):
    return test_case.check_config or {}


# ===========================================================================
# Automated check modes
# ===========================================================================

def _check_raw_match(execution, imei, window_start, now):
    """
    'gps' / 'gpsem': packets whose raw text matches regex_pattern.

    With max_interval_seconds set the packets must arrive as a burst: a
    run of min_match_count consecutive matches, each within
    max_interval_seconds of the last (and the run inside
    check_config.run_within_seconds when set) -- e.g. 10 SOS packets at a
    5s cadence within one minute. Otherwise min_match_count matches anywhere
    in the window are enough.
    """
    test_case = execution.test_case
    cfg = _cfg(test_case)
    model = GPSDataLog if test_case.source_table == 'gps' else GPSemDataLog
    pattern = re.compile(test_case.regex_pattern) if test_case.regex_pattern else None
    sample_limit = cfg.get('sample_limit', 5)

    matched = []
    for raw_data, server_time in _scan_rows(model, imei, window_start):
        if pattern and not pattern.search(raw_data):
            continue
        info = _pvt_info(raw_data, server_time) if model is GPSDataLog else None
        if info is None:
            info = {'raw_data': raw_data, 'time': server_time}
        matched.append(info)

    required = test_case.min_match_count
    matched_count = len(matched)
    label = cfg.get('packet_label', 'matching')
    samples = [_sample(p) if 'packet_type' in p else {'raw_data': p['raw_data'], 'timestamp': p['time'].isoformat()}
               for p in reversed(matched)][:sample_limit]
    result = {
        'matched_count': matched_count,
        'required': required,
        'samples': samples,
    }

    if not test_case.max_interval_seconds:
        result['pass'] = matched_count >= required
        result['reason'] = None if result['pass'] else (
            f"Only {matched_count} {label} packet(s) received since the test started, need at least {required}."
        )
        return result

    # Burst check: split into runs where each packet is within max_gap of
    # the previous one, then look for `required` packets in a row inside a
    # run (spanning at most `within` seconds when set).
    max_gap = test_case.max_interval_seconds
    within = cfg.get('run_within_seconds')
    by_time = sorted(matched, key=lambda p: p['time'])
    runs = []
    for packet in by_time:
        if runs and (packet['time'] - runs[-1][-1]['time']).total_seconds() <= max_gap:
            runs[-1].append(packet)
        else:
            runs.append([packet])
    burst = None
    for run in runs:
        for j in range(len(run) - required + 1):
            if not within or (run[j + required - 1]['time'] - run[j]['time']).total_seconds() <= within:
                burst = run[j:j + required]
                break
        if burst:
            break

    if burst:
        result.update({
            'pass': True,
            'reason': None,
            'samples': [_sample(p) if 'packet_type' in p else {'raw_data': p['raw_data'], 'timestamp': p['time'].isoformat()}
                        for p in burst],
        })
        return result

    window_text = f" within {_duration(within)}" if within else ''
    if not matched:
        reason = f"No {label} packets received since the test started (need {required} at a {max_gap}s cadence{window_text})."
    else:
        run = max(runs, key=len)
        reason = (
            f"Need {required} {label} packets in a row, each at most {max_gap}s apart{window_text}; "
            f"the best run was {len(run)} packet(s) from {_ist(run[0]['time'])} to {_ist(run[-1]['time'])} "
            f"({matched_count} received in total). Packets came slower than the {max_gap}s cadence or stopped early."
        )
    result.update({'pass': False, 'reason': reason})
    return result


def _matches_condition(packet, condition):
    if not condition:
        return True
    if condition.get('packet_type') and packet['packet_type'] != condition['packet_type'].upper():
        return False
    if condition.get('field'):
        return packet.get(condition['field']) == str(condition.get('equals'))
    return True


def _condition_text(condition):
    parts = []
    if condition.get('packet_type'):
        parts.append(f"{condition['packet_type']} packet")
    if condition.get('field'):
        parts.append(f"{condition.get('label', condition['field'])} = {condition.get('equals')}")
    return ' with '.join(parts) or 'any packet'


def _check_packet_sequence(execution, imei, window_start, now):
    """
    'packet_sequence': an alert packet, optionally preceded by a packet in
    the old state and followed by N packets in the new state, e.g.
    ignition ON = last ignition-OFF packet, IN alert, 8 ignition-ON packets.

    check_config:
      trigger_regex   regex the alert packet must match (required)
      trigger_label   e.g. 'Ignition ON alert (IN,07)'
      before          {"field": "ignition", "equals": "0", "label": "ignition"} or null
      after           {"field": ..., "equals": ..., "packet_type": "NR"}
      after_count     packets needed after the alert
      within_seconds  the after-packets must arrive within this long of the alert (optional)
    """
    test_case = execution.test_case
    cfg = _cfg(test_case)
    trigger_re = re.compile(cfg.get('trigger_regex') or test_case.regex_pattern or r'(?!)')
    trigger_label = cfg.get('trigger_label', 'alert')
    before_cond = cfg.get('before')
    after_cond = cfg.get('after') or {}
    after_count = int(cfg.get('after_count', 0))
    within = cfg.get('within_seconds')

    packets = _pvt_packets(imei, window_start, lookback_seconds=300)
    triggers = [i for i, p in enumerate(packets) if p['time'] >= window_start and trigger_re.search(p['raw_data'])]
    if not triggers:
        return {
            'matched_count': 0,
            'required': 1 + after_count,
            'pass': False,
            'reason': f"No {trigger_label} packet received since the test started.",
            'samples': [],
        }

    attempts = []
    for t in triggers:
        trigger = packets[t]
        problems = []
        samples = []

        before = None
        if before_cond:
            before = next((p for p in reversed(packets[:t]) if not trigger_re.search(p['raw_data'])), None)
            if before is None:
                problems.append(
                    f"No packet before the {trigger_label} at {_ist(trigger['time'])} to show the previous state "
                    f"(expected {_condition_text(before_cond)})."
                )
            else:
                samples.append(_sample(before, role='before'))
                if not _matches_condition(before, before_cond):
                    problems.append(
                        f"The last packet before the {trigger_label} ({_ist(before['time'])}) shows "
                        f"{before_cond.get('label', before_cond['field'])} = {before.get(before_cond['field'])}, "
                        f"expected {before_cond.get('equals')}."
                    )
        samples.append(_sample(trigger, role='trigger'))

        after_type = (after_cond.get('packet_type') or '').upper()
        followers = [
            p for p in packets[t + 1:]
            if not trigger_re.search(p['raw_data']) and (not after_type or p['packet_type'] == after_type)
        ][:after_count]
        if within:
            in_time = [p for p in followers if (p['time'] - trigger['time']).total_seconds() <= within]
        else:
            in_time = followers
        good = [p for p in in_time if _matches_condition(p, after_cond)]
        samples.extend(_sample(p, role='after') for p in followers)

        if len(good) < after_count:
            detail = f"Only {len(good)} of the {after_count} {_condition_text(after_cond)} packet(s) needed after the {trigger_label} ({_ist(trigger['time'])})"
            if within:
                detail += f" arrived within {_duration(within)}"
            wrong = [p for p in in_time if not _matches_condition(p, after_cond)]
            if wrong and after_cond.get('field'):
                detail += (
                    f"; {len(wrong)} packet(s) show {after_cond.get('label', after_cond['field'])} = "
                    f"{wrong[0].get(after_cond['field'])} (first at {_ist(wrong[0]['time'])})"
                )
            elif len(followers) < after_count:
                detail += f"; only {len(followers)} packet(s) received after it so far"
            problems.append(detail + '.')

        attempts.append({'problems': problems, 'samples': samples, 'good': len(good)})
        if not problems:
            break

    best = next((a for a in attempts if not a['problems']), None) or max(attempts, key=lambda a: a['good'])
    return {
        'matched_count': 1 + best['good'],
        'required': 1 + after_count,
        'pass': not best['problems'],
        'reason': _fail_reason(best['problems']),
        'samples': best['samples'],
        'trigger_count': len(triggers),
    }


def _check_sos_stop_both(execution, imei, window_start, now):
    """
    'sos_stop_both': after the SOS stop command the device must send the
    EA,11 alert on the tracking server and an EPB SEM packet on the
    emergency server, and its NR packets must return to SOS flag = 0.
    """
    cfg = _cfg(execution.test_case)
    nr_needed = int(cfg.get('nr_after_count', 1))
    packets = _pvt_packets(imei, window_start)
    tracking_stop = next((p for p in packets if p['packet_type'] == 'EA' and p['alert_id'] == '11'), None)

    emergency_stop = None
    for raw_data, server_time in _scan_rows(GPSemDataLog, imei, window_start):
        parts = _packet_fields(raw_data)
        if _packet_type_in_header(raw_data, 'EPB') and 'SEM' in [p.upper() for p in parts[:4]]:
            info = _epb_packet_info(raw_data, server_time)
            emergency_stop = {'raw_data': raw_data, 'timestamp': info['time'].isoformat()}
            break

    problems, samples = [], []
    if tracking_stop:
        samples.append(_sample(tracking_stop, role='tracking_stop'))
    else:
        problems.append("No SOS stop alert (EA,11) on the tracking server since the test started.")
    if emergency_stop:
        samples.append(dict(emergency_stop, role='emergency_stop'))
    else:
        problems.append("No SOS stop packet (EPB SEM) on the emergency server since the test started.")

    if tracking_stop:
        after = [p for p in packets if p['time'] > tracking_stop['time'] and p['packet_type'] == 'NR'][:max(nr_needed, 3)]
        cleared = [p for p in after if p['emergency_status'] == '0']
        samples.extend(_sample(p, role='after') for p in after)
        if len(cleared) < nr_needed:
            if not after:
                problems.append(f"No NR packets received after the SOS stop alert ({_ist(tracking_stop['time'])}) yet.")
            else:
                problems.append(
                    f"NR packets after the SOS stop still show SOS flag = {after[0]['emergency_status']} "
                    f"(first at {_ist(after[0]['time'])}); expected 0."
                )

    found = int(bool(tracking_stop)) + int(bool(emergency_stop))
    return {
        'matched_count': found,
        'required': 2,
        'pass': not problems,
        'reason': _fail_reason(problems),
        'samples': samples,
    }


def _check_protocol_packet(execution, imei, window_start, now):
    """
    'protocol_packet': a packet of check_config.category ('login' |
    'health' | 'tracking' | 'emergency'), optionally narrowed by
    regex_pattern, whose every field validates against the protocol.
    The field-by-field validation is returned for display.
    """
    test_case = execution.test_case
    cfg = _cfg(test_case)
    category = cfg.get('category', 'tracking')
    label = cfg.get('packet_label', f'{category} packet')
    require_location = cfg.get('require_location', False)
    pattern = re.compile(test_case.regex_pattern) if test_case.regex_pattern else None
    model = GPSemDataLog if category == 'emergency' else GPSDataLog

    found = []
    for raw_data, server_time in reversed(_scan_rows(model, imei, window_start)):
        for frag in _packets_in_row(raw_data):
            if pattern and not pattern.search(frag):
                continue
            format_id, result = _validate_reference_format(frag, category, imei)
            if result is None:
                if _packet_kind(frag) == category:
                    found.append({
                        'raw_data': frag,
                        'timestamp': server_time.isoformat(),
                        'protocol_format': None,
                        'valid': False,
                        'errors': [
                            f"packet layout does not match the reference format (test device {REFERENCE_DEVICE}): "
                            f"it starts '{frag[:12]}...' but a {category} packet must look like "
                            f"'{REFERENCE_PACKET_START[category]}'"
                        ],
                        'validation': None,
                    })
                    break
                continue
            errors = list(result.errors)
            if require_location:
                lat = pf._field_value(result.fields, 'latitude')
                lon = pf._field_value(result.fields, 'longitude')
                if _to_float(lat) in (None, 0.0) or _to_float(lon) in (None, 0.0):
                    errors.append(f"location: {lat},{lon} is not a valid coordinate (no GPS fix)")
            found.append({
                'raw_data': frag,
                'timestamp': server_time.isoformat(),
                'protocol_format': format_id,
                'valid': not errors,
                'errors': errors,
                'validation': result.to_dict(),
            })
            break
        if len(found) >= 20:
            break

    valid = [f for f in found if f['valid']]
    required = test_case.min_match_count
    if len(valid) >= required:
        reason = None
    elif not found:
        reason = f"No {label} received since the test started."
    else:
        latest = found[0]
        reason = (
            f"{label[0].upper() + label[1:]} received at {_ist(latest['timestamp'])} but "
            f"{len(latest['errors'])} field(s) don't match the protocol: " + '; '.join(latest['errors'][:6])
            + ('' if len(latest['errors']) <= 6 else f"; and {len(latest['errors']) - 6} more") + '.'
        )
    return {
        'matched_count': len(valid),
        'required': required,
        'pass': len(valid) >= required,
        'reason': reason,
        'samples': (valid or found)[:5],
    }


def _check_speed_accuracy(execution, imei, window_start, now):
    """
    'speed_accuracy': for each target speed, a stretch of at least
    min_duration_seconds where every PVT packet reports target +/-
    tolerance_kmph. The stretch's start/end points are returned for the map.
    """
    cfg = _cfg(execution.test_case)
    targets = cfg.get('target_speeds_kmph', [20, 40, 70])
    tolerance = cfg.get('tolerance_kmph', 5)
    min_duration = cfg.get('min_duration_seconds', 60)
    max_gap = cfg.get('max_packet_gap_seconds', 15)
    packets = [p for p in _pvt_packets(imei, window_start) if p['speed'] is not None and p['latitude'] is not None]

    stretches, problems = [], []
    for target in targets:
        # Runs of consecutive in-band packets with no packet gap above max_gap.
        runs = []
        previous_in_band = False
        for packet in packets:
            in_band = abs(packet['speed'] - target) <= tolerance
            if in_band and previous_in_band and (packet['time'] - runs[-1][-1]['time']).total_seconds() <= max_gap:
                runs[-1].append(packet)
            elif in_band:
                runs.append([packet])
            previous_in_band = in_band
        longest = max(runs, key=lambda r: (r[-1]['time'] - r[0]['time']).total_seconds()) if runs else None
        best = ((longest[-1]['time'] - longest[0]['time']).total_seconds(), longest) if longest else None
        if best:
            duration, run = best
            speeds = [p['speed'] for p in run]
            stretches.append({
                'target_speed_kmph': target,
                'passed': duration >= min_duration,
                'duration_seconds': round(duration, 1),
                'packet_count': len(run),
                'average_speed_kmph': round(sum(speeds) / len(speeds), 2),
                'min_speed_kmph': min(speeds),
                'max_speed_kmph': max(speeds),
                'start': _sample(run[0]),
                'end': _sample(run[-1]),
            })
            if duration < min_duration:
                problems.append(
                    f"{target} km/h: the longest steady stretch at {target - tolerance}-{target + tolerance} km/h "
                    f"was {_duration(duration)} ({_ist(run[0]['time'])}-{_ist(run[-1]['time'])}); needs {_duration(min_duration)}."
                )
        else:
            stretches.append({'target_speed_kmph': target, 'passed': False, 'duration_seconds': 0, 'packet_count': 0})
            problems.append(f"{target} km/h: no packet reported a speed between {target - tolerance} and {target + tolerance} km/h.")

    passed = sum(1 for s in stretches if s['passed'])
    return {
        'matched_count': passed,
        'required': len(targets),
        'pass': not problems,
        'reason': _fail_reason(problems),
        'samples': [s['start'] for s in stretches if s.get('start')][:5],
        'stretches': stretches,
        'criteria': {'target_speeds_kmph': targets, 'tolerance_kmph': tolerance, 'min_duration_seconds': min_duration},
    }


def _resolve_geofence_point(point, packets):
    """
    A tester-marked geofence point -> the recorded packet it refers to.
    `point` is {"timestamp": iso} (nearest packet in time) or
    {"latitude": .., "longitude": ..} (nearest packet on the route).
    """
    if not point or not packets:
        return None
    if point.get('timestamp'):
        try:
            when = datetime.fromisoformat(str(point['timestamp']).replace('Z', '+00:00'))
        except ValueError:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt_timezone.utc)
        return min(packets, key=lambda p: abs((p['time'] - when).total_seconds()))
    lat, lon = _to_float(point.get('latitude')), _to_float(point.get('longitude'))
    if lat is None or lon is None:
        return None
    return min(packets, key=lambda p: _haversine_m(lat, lon, p['latitude'], p['longitude']))


def _alert_id_is(packet, alert_id):
    try:
        return int(packet['alert_id']) == int(alert_id)
    except (TypeError, ValueError):
        return False


def _geofence_alert_pair(packets, in_alert_id, out_alert_id, low, high):
    """
    (entry, exit, alerts_seen) from the device's own geofence alerts: each
    IN alert paired with the next OUT alert after it. The first pair whose
    distance is in range wins, else the latest pair. alerts_seen counts
    the IN / OUT alerts found.
    """
    ins = [p for p in packets if _alert_id_is(p, in_alert_id)]
    outs = [p for p in packets if _alert_id_is(p, out_alert_id)]
    pairs = []
    for entry in ins:
        exit_ = next((p for p in outs if p['time'] > entry['time']), None)
        if exit_:
            distance = _haversine_m(entry['latitude'], entry['longitude'], exit_['latitude'], exit_['longitude'])
            pairs.append((entry, exit_, low <= distance <= high))
    best = next((pair for pair in pairs if pair[2]), None) or (pairs[-1] if pairs else None)
    seen = {'in': len(ins), 'out': len(outs)}
    return (best[0], best[1], seen) if best else (None, None, seen)


def _check_geofence_crossing(execution, imei, window_start, now):
    """
    'geofence_crossing': the geofence IN and OUT points must be about
    expected_distance_m apart (1 km, +/- tolerance_pct). The points come
    from, in order:
      1. the device's geofence alerts -- NR packets with alert ID
         in_alert_id (18, entry) followed by out_alert_id (19, exit);
      2. points the tester marked on the map (sent as geofence_in /
         geofence_out with the refresh, see superadmin_refresh_test_log),
         each snapped to the recorded packet it refers to;
      3. check_config centre_lat / center_lon + radius_m, if set.
    The route is always returned for the map.
    """
    cfg = _cfg(execution.test_case)
    expected = cfg.get('expected_distance_m', 1000)
    tolerance_pct = cfg.get('tolerance_pct', 5)
    low, high = expected * (1 - tolerance_pct / 100), expected * (1 + tolerance_pct / 100)
    in_alert_id, out_alert_id = cfg.get('in_alert_id', 18), cfg.get('out_alert_id', 19)

    packets = [p for p in _pvt_packets(imei, window_start) if p['latitude'] is not None and p['gps_fix'] == '1']
    route = [{'latitude': p['latitude'], 'longitude': p['longitude'], 'timestamp': p['time'].isoformat(),
              'speed': p['speed']} for p in packets]

    entry, exit_, alerts_seen = _geofence_alert_pair(packets, in_alert_id, out_alert_id, low, high)
    detection = 'device_alert'

    marked = getattr(execution, 'geofence_points', None) or {}
    if not (entry and exit_) and (marked.get('in') or marked.get('out')):
        entry = _resolve_geofence_point(marked.get('in'), packets)
        exit_ = _resolve_geofence_point(marked.get('out'), packets)
        detection = 'marked'

    center_lat, center_lon = _to_float(cfg.get('center_lat')), _to_float(cfg.get('center_lon'))
    if not (entry or exit_) and center_lat is not None and center_lon is not None:
        detection = 'centre'
        radius = cfg.get('radius_m', expected / 2)
        inside = [_haversine_m(center_lat, center_lon, p['latitude'], p['longitude']) <= radius for p in packets]
        for i in range(1, len(packets)):
            if entry is None and inside[i] and not inside[i - 1]:
                entry = packets[i]
            elif entry is not None and not inside[i] and inside[i - 1]:
                exit_ = packets[i]
                break

    distance = None
    if not packets:
        reason = "No PVT packets with a valid GPS fix received since the test started."
    elif entry is None or exit_ is None:
        reason = (
            f"No geofence IN alert (NR,{in_alert_id}) followed by an OUT alert (NR,{out_alert_id}) since the "
            f"test started (seen {alerts_seen['in']} IN, {alerts_seen['out']} OUT). Drive through the geofence, "
            f"or mark the IN and OUT points on the map (about {expected / 1000:g} km apart), then refresh."
        )
    else:
        if exit_['time'] < entry['time']:
            entry, exit_ = exit_, entry
        distance = round(_haversine_m(entry['latitude'], entry['longitude'], exit_['latitude'], exit_['longitude']), 1)
        reason = None if low <= distance <= high else (
            f"The geofence IN point ({_ist(entry['time'])}) and OUT point ({_ist(exit_['time'])}) are "
            f"{distance:.0f} m apart; they must be {low:.0f}-{high:.0f} m apart."
        )

    samples = []
    if entry:
        samples.append(_sample(entry, role='geofence_in'))
    if exit_:
        samples.append(_sample(exit_, role='geofence_out'))
    return {
        'matched_count': int(reason is None),
        'required': 1,
        'pass': reason is None,
        'reason': reason,
        'samples': samples,
        'detection': detection,
        'geofence_alerts_seen': alerts_seen,
        'geofence_points': {k: marked[k] for k in ('in', 'out') if marked.get(k)},
        'entry_exit_distance_m': distance,
        'criteria': {'distance_range_m': [round(low), round(high)]},
        'route': route[-1000:],
    }


def _check_history_coverage(execution, imei, window_start, now):
    """
    'history_coverage': history (H) packets sent after the network came
    back must cover at least min_coverage_seconds of the no-network
    period, measured on device time across one continuous stretch.
    """
    cfg = _cfg(execution.test_case)
    min_coverage = cfg.get('min_coverage_seconds', 120)
    max_gap = cfg.get('max_gap_seconds', 60)
    history = [p for p in _pvt_packets(imei, window_start) if p['packet_status'] == 'H' and p['time_source'] == 'device']

    best, run = None, []
    for packet in history + [None]:
        if packet is not None and (not run or (packet['time'] - run[-1]['time']).total_seconds() <= max_gap):
            run.append(packet)
            continue
        if run:
            span = (run[-1]['time'] - run[0]['time']).total_seconds()
            if best is None or span > best[0]:
                best = (span, run)
        run = [packet] if packet is not None else []

    if not history:
        reason = ("No history (H) packets received since the test started. Keep the device in the Faraday box for "
                  "3 minutes, then bring it to open sky so it uploads the stored packets.")
        coverage, samples = 0, []
    else:
        coverage, run = best
        samples = [_sample(run[0], role='first_history'), _sample(run[-1], role='last_history')]
        reason = None if coverage >= min_coverage else (
            f"History packets cover only {_duration(coverage)} ({_ist(run[0]['time'])}-{_ist(run[-1]['time'])}, "
            f"{len(run)} packets); need at least {_duration(min_coverage)} of the no-network period."
        )
    return {
        'matched_count': len(history),
        'required': 1,
        'pass': reason is None,
        'reason': reason,
        'samples': samples,
        'history_coverage_seconds': round(coverage, 1),
        'criteria': {'min_coverage_seconds': min_coverage},
    }


def _check_unique_cell_towers(execution, imei, window_start, now):
    """
    'unique_cell_towers': every distinct serving cell (operator, MCC, MNC,
    LAC, cell ID) the device reported, first packet for each, for the
    tester to compare against a phone. Needs min_match_count towers.
    """
    test_case = execution.test_case
    towers = {}
    for p in _pvt_packets(imei, window_start):
        if p['packet_status'] != 'L' or not p['cell_id'] or p['cell_id'].strip('0') == '' or p['mcc'] in (None, '', '0'):
            continue
        key = (p['network_operator'], p['mcc'], p['mnc'], p['lac'], p['cell_id'])
        if key not in towers:
            towers[key] = p

    required = test_case.min_match_count
    unique = list(towers.values())
    operators = sorted({p['network_operator'] for p in unique if p['network_operator']})
    return {
        'matched_count': len(unique),
        'required': required,
        'pass': len(unique) >= required,
        'reason': None if len(unique) >= required else (
            f"Only {len(unique)} unique cell tower(s) reported since the test started, need {required}. "
            f"Move to the next location (about 1 km away) and wait for a few packets."
        ),
        'samples': [_sample(p) for p in unique],
        'operators_seen': operators,
    }


def _check_firmware_diff(execution, imei, window_start, now):
    """
    'firmware_diff': PVT/HLM packets carry the running firmware version;
    the version must change during the window (A before, B after). The
    last packet on each old version and the first on the next are shown.
    """
    test_case = execution.test_case
    timeline = []
    for raw_data, server_time in _scan_rows(GPSDataLog, imei, window_start):
        for frag in _packets_in_row(raw_data):
            parts = _packet_fields(frag)
            if len(parts) < 3 or parts[0].upper() not in ('PVT', 'HLM'):
                continue
            version = parts[2]
            if not version:
                continue
            if not timeline or timeline[-1]['version'] != version:
                timeline.append({'version': version, 'first': (frag, server_time), 'last': (frag, server_time)})
            else:
                timeline[-1]['last'] = (frag, server_time)
            break

    versions = list(dict.fromkeys(t['version'] for t in timeline))
    samples = []
    for earlier, later in zip(timeline, timeline[1:]):
        samples.append({'raw_data': earlier['last'][0], 'timestamp': earlier['last'][1].isoformat(),
                        'role': 'before_upgrade', 'version': earlier['version']})
        samples.append({'raw_data': later['first'][0], 'timestamp': later['first'][1].isoformat(),
                        'role': 'after_upgrade', 'version': later['version']})
    if not samples and timeline:
        samples.append({'raw_data': timeline[-1]['last'][0], 'timestamp': timeline[-1]['last'][1].isoformat(),
                        'version': timeline[-1]['version']})

    required = test_case.min_match_count
    passed = len(versions) >= required
    return {
        'matched_count': len(versions),
        'required': required,
        'pass': passed,
        'reason': None if passed else (
            f"Only {len(versions)} firmware version(s) seen ({', '.join(versions) or 'none'}) since the test started, "
            f"need {required} -- the upgrade hasn't taken effect on the device yet."
        ),
        'samples': samples[:10],
        'versions_seen': versions,
    }


def _check_voltage_levels(execution, imei, window_start, now):
    """
    'voltage_internal' / 'voltage_external': every packet that reported a
    new voltage level during the window, so the tester can compare each
    with the applied voltage. Needs min_match_count distinct levels.
    """
    test_case = execution.test_case
    internal = test_case.source_table == 'voltage_internal'
    key = 'internal_voltage' if internal else 'external_voltage'
    label = 'internal battery voltage' if internal else 'external/main voltage'

    levels = {}
    for p in _pvt_packets(imei, window_start):
        value = p.get(key)
        if value and value not in levels:
            levels[value] = p

    required = test_case.min_match_count
    return {
        'matched_count': len(levels),
        'required': required,
        'pass': len(levels) >= required,
        'reason': None if len(levels) >= required else (
            f"Only {len(levels)} distinct {label} level(s) seen ({', '.join(levels) or 'none'}) since the test "
            f"started, need {required}. Apply the next voltage level and wait for a packet."
        ),
        'samples': [_sample(p, voltage=v) for v, p in levels.items()],
        'values_seen': list(levels.keys()),
    }


def _check_esim_switch(execution, imei, window_start, now):
    """
    eSIM switch: the last N packets on the old network followed by the
    next N on the new one (N = check_config.packets_each_side, default 2).
    The network order is cross-checked against the opposite-direction test.
    """
    test_case = execution.test_case
    each_side = int(_cfg(test_case).get('packets_each_side', 2))
    packets = [p for p in _pvt_packets(imei, window_start) if p['network_operator'] and p['packet_status'] == 'L']

    switch_at = next((i for i in range(1, len(packets))
                      if packets[i]['network_operator'] != packets[i - 1]['network_operator']), None)
    networks = list(dict.fromkeys(p['network_operator'] for p in packets))
    if switch_at is None:
        return {
            'matched_count': len(networks),
            'required': 2,
            'pass': False,
            'reason': (
                f"No network switch seen since the test started -- every packet is on "
                f"'{networks[0]}'." if networks else "No PVT packets with a network operator received since the test started."
            ),
            'samples': [_sample(p) for p in packets[-each_side:]],
            'networks_seen': networks,
        }

    old, new = packets[switch_at - 1]['network_operator'], packets[switch_at]['network_operator']
    before = packets[max(0, switch_at - each_side):switch_at]
    after = []
    for p in packets[switch_at:]:
        if p['network_operator'] != new or len(after) == each_side:
            break
        after.append(p)

    problems = []
    if len(before) < each_side:
        problems.append(f"Only {len(before)} packet(s) on '{old}' before the switch, need {each_side}.")
    if len(after) < each_side:
        problems.append(f"Only {len(after)} packet(s) on '{new}' after the switch so far, need {each_side} in a row.")

    sibling_source = ESIM_SIBLING_SOURCE.get(test_case.source_table)
    if not problems and sibling_source:
        sibling_case = TechnicalOnboardingTestCase.objects.filter(
            source_table=sibling_source, active=True
        ).order_by('serial_no').first()
        sibling_execution = TechnicalOnboardingTestExecution.objects.filter(
            onboarding_request=execution.onboarding_request,
            demo_device=execution.demo_device,
            test_case=sibling_case,
            status='complete',
        ).order_by('-completed_at').first() if sibling_case else None
        sibling_networks = (sibling_execution.test_log_snapshot or {}).get('networks_seen') if sibling_execution else None
        if sibling_networks and len(sibling_networks) >= 2 and (old, new) != (sibling_networks[1], sibling_networks[0]):
            problems.append(
                f"Network order does not mirror '{sibling_case.name}': expected '{sibling_networks[1]}' -> "
                f"'{sibling_networks[0]}' (reverse of that test), but saw '{old}' -> '{new}'."
            )

    return {
        'matched_count': len(before) + len(after),
        'required': 2 * each_side,
        'pass': not problems,
        'reason': _fail_reason(problems),
        'samples': [_sample(p, role='before_switch') for p in before] + [_sample(p, role='after_switch') for p in after],
        'networks_seen': [old, new],
    }


def _check_vehicle_registration(execution, imei, window_start, now):
    """
    'vehicle_registration_diff': after the set-registration command the
    device must acknowledge it (an OT,12 packet) and its NR packets must
    carry the new number -- the value sent when the command went through
    the onboarding send-command API, else any number different from the
    one reported before the test.
    """
    cfg = _cfg(execution.test_case)
    packets = _pvt_packets(imei, window_start, lookback_seconds=3600)
    before = [p for p in packets if p['time'] < window_start and p['vehicle_reg_no']]
    baseline = before[-1]['vehicle_reg_no'] if before else None

    dispatch = execution.command_dispatches.filter(sent_at__gte=window_start).exclude(value__isnull=True).exclude(value='').order_by('-sent_at').first()
    expected = dispatch.value.strip() if dispatch else None

    in_window = [p for p in packets if p['time'] >= window_start]
    ack = next((p for p in in_window if p['packet_type'] == 'OT'), None)
    nr_new = next((
        p for p in in_window
        if p['packet_type'] == 'NR' and p['vehicle_reg_no']
        and (p['vehicle_reg_no'] == expected if expected else p['vehicle_reg_no'] != baseline)
    ), None)

    problems, samples = [], []
    if cfg.get('require_ot_ack', True):
        if ack:
            samples.append(_sample(ack, role='ot_ack'))
        else:
            problems.append("No OT acknowledgement packet (OT,12) received since the test started.")
    if nr_new:
        samples.append(_sample(nr_new, role='nr_with_new_reg_no'))
    else:
        latest = next((p['vehicle_reg_no'] for p in reversed(in_window) if p['packet_type'] == 'NR'), None) or baseline
        problems.append(
            f"No NR packet carries the new registration number"
            + (f" '{expected}'" if expected else '')
            + f" yet -- latest NR shows '{latest or 'unknown'}'."
        )
    return {
        'matched_count': int(bool(ack)) + int(bool(nr_new)),
        'required': 2 if cfg.get('require_ot_ack', True) else 1,
        'pass': not problems,
        'reason': _fail_reason(problems),
        'samples': samples,
        'baseline_value': baseline,
        'expected_value': expected,
    }


def _check_reboot(execution, imei, window_start, now):
    """
    'reboot_restart_gap': after the reboot command the device restarts and
    sends a login packet, then a health packet, then an NR packet.
    The command is looked up in this execution's onboarding dispatches
    (command_key 'reboot' or regex_pattern) and in the OTA command history.
    """
    test_case = execution.test_case
    pattern = re.compile(test_case.regex_pattern) if test_case.regex_pattern else None
    sent_times = [
        d.sent_at for d in execution.command_dispatches.filter(sent_at__gte=window_start, send_status='queued')
        if d.command_key == 'reboot' or (pattern and pattern.search(d.command_sent or ''))
    ]
    sent_times += [
        row.sent_at for row in OTACommandHistory.objects.filter(imei=imei, sent_at__gte=window_start).exclude(send_status='failed')
        if not pattern or pattern.search(row.command_sent or '')
    ]
    if not sent_times:
        return {
            'matched_count': 0,
            'required': 3,
            'pass': False,
            'reason': 'No reboot command sent to this device since the test started. Send it from the test commands.',
            'samples': [],
        }
    command_sent_at = min(sent_times)

    # Order of packet kinds after the command; the packets only need to be
    # recognisable here -- their field layout is covered by tests 26/27/30.
    sequence = []
    for raw_data, server_time in _scan_rows(GPSDataLog, imei, command_sent_at):
        for frag in _packets_in_row(raw_data):
            kind = _packet_kind(frag)
            if kind in ('login', 'health') or (
                kind == 'tracking' and (_pvt_info(frag, server_time) or {}).get('packet_type') == 'NR'
            ):
                sequence.append((kind, frag, server_time))

    steps = [('login', 'login packet'), ('health', 'health packet'), ('tracking', 'NR packet')]
    found, samples, cursor = [], [], 0
    for category, label in steps:
        hit = next((i for i in range(cursor, len(sequence)) if sequence[i][0] == category), None)
        if hit is None:
            break
        found.append(label)
        samples.append({'raw_data': sequence[hit][1], 'timestamp': sequence[hit][2].isoformat(), 'role': category})
        cursor = hit + 1

    missing = [label for _c, label in steps][len(found):]
    if not missing:
        reason = None
    elif not sequence:
        reason = (f"Reboot command sent at {_ist(command_sent_at)} -- the device hasn't sent any packets since; "
                  f"it may still be rebooting or offline.")
    else:
        reason = (
            f"After the reboot command ({_ist(command_sent_at)}) the device must send a login packet, then a health "
            f"packet, then an NR packet. Seen so far: {', '.join(found) or 'none of them'}; missing: {', '.join(missing)}. "
            + ("A missing login packet means the device did not actually restart." if not found else '')
        ).strip()
    return {
        'matched_count': len(found),
        'required': 3,
        'pass': not missing,
        'reason': reason,
        'samples': samples,
        'command_sent_at': command_sent_at.isoformat(),
    }


_MODE_HANDLERS = {
    'gps': _check_raw_match,
    'gpsem': _check_raw_match,
    'packet_sequence': _check_packet_sequence,
    'sos_stop_both': _check_sos_stop_both,
    'protocol_packet': _check_protocol_packet,
    'speed_accuracy': _check_speed_accuracy,
    'geofence_crossing': _check_geofence_crossing,
    'history_coverage': _check_history_coverage,
    'unique_cell_towers': _check_unique_cell_towers,
    'firmware_diff': _check_firmware_diff,
    'voltage_internal': _check_voltage_levels,
    'voltage_external': _check_voltage_levels,
    'esim_primary_to_secondary': _check_esim_switch,
    'esim_secondary_to_primary': _check_esim_switch,
    'vehicle_registration_diff': _check_vehicle_registration,
    'reboot_restart_gap': _check_reboot,
}


# ===========================================================================
# Test commands (sent to the demo device over MQTT)
# ===========================================================================

COMMAND_REPLY_WINDOW = timedelta(minutes=2)


def _frame_command(command):
    """Wrap a command body in the device's '@...*' framing (idempotent)."""
    body = command.strip()
    if not body.startswith('@'):
        body = '@' + body
    if not body.endswith('*'):
        body = body + '*'
    return body


def _device_source_ip(imei):
    return (
        GPSDataLog.objects.filter(imei=imei, source_ip__isnull=False)
        .order_by('-timestamp').values_list('source_ip', flat=True).first()
    )


def _command_replies(imei, source_ip, sent_at):
    """
    Device replies to a command within COMMAND_REPLY_WINDOW: plain-text
    replies ('SET SUCCESSFULLY ...', 'SOS DISABLED') carry no IMEI, so they
    are matched on the device's connection IP; OT,12 packets by IMEI.
    """
    until = sent_at + COMMAND_REPLY_WINDOW
    replies = []
    if source_ip:
        for raw_data, ts in (
            GPSDataLog.objects.filter(source_ip=source_ip, timestamp__gte=sent_at, timestamp__lte=until)
            .exclude(raw_data__startswith='$').order_by('timestamp').values_list('raw_data', 'timestamp')[:10]
        ):
            replies.append({'raw_data': raw_data.strip(), 'timestamp': ts.isoformat()})
    for raw_data, ts in (
        GPSDataLog.objects.filter(timestamp__gte=sent_at, timestamp__lte=until, raw_data__contains=imei)
        .filter(raw_data__contains=',OT,').order_by('timestamp').values_list('raw_data', 'timestamp')[:5]
    ):
        replies.append({'raw_data': raw_data.strip(), 'timestamp': ts.isoformat()})
    replies.sort(key=lambda r: r['timestamp'])
    return replies


def _commands_sent(execution):
    if not execution.started_at:
        return []
    dispatches = list(execution.command_dispatches.filter(sent_at__gte=execution.started_at).order_by('sent_at')[:20])
    if not dispatches:
        return []
    source_ip = _device_source_ip(execution.demo_device.imei)
    return [
        {
            'id': d.id,
            'command_key': d.command_key,
            'command_label': d.command_label,
            'command_sent': d.command_sent,
            'value': d.value,
            'send_status': d.send_status,
            'error': d.error,
            'sent_at': d.sent_at.isoformat(),
            'replies': _command_replies(d.imei, source_ip, d.sent_at) if d.send_status == 'queued' else [],
        }
        for d in dispatches
    ]


def _pvt_index(parts):
    """Index of the 'PVT' token in a packet's fields, or None."""
    for i, part in enumerate(parts[:3]):
        if part.upper() == 'PVT':
            return i
    return None


def _packet_time(raw_data, server_time):
    """
    (effective_time, time_source) for a PVT packet: the device timestamp
    when it's plausible ('device'), else the server receive time ('server').
    """
    device_time = _extract_pvt_datetime(raw_data)
    if device_time and server_time - DEVICE_CLOCK_MAX_BEHIND <= device_time <= server_time + DEVICE_CLOCK_MAX_AHEAD:
        return device_time, 'device'
    return server_time, 'server'


def _epb_packet_info(raw_data, server_time):
    """
    Effective time, GPS validity and speed for an emergency (EPB) packet.

    Field positions are anchored on the N/S + E/W direction fields, since
    older firmware inserts an extra field after 'EPB' (EPB,EM,11,<imei>,...)
    and the fix flag / datetime always sit just before the latitude:
      EPB,EMR,<imei>,NM,<ddmmyyyyHHMMSS>,A,<lat>,N,<lon>,E,<alt>,<speed>,...
    """
    parts = _packet_fields(raw_data)
    info = {'time': server_time, 'time_source': 'server', 'valid_gps': False, 'speed': None}
    lat_idx = next(
        (i for i in range(2, len(parts) - 3)
         if parts[i + 1].upper() in ('N', 'S') and parts[i + 3].upper() in ('E', 'W')),
        None,
    )
    if lat_idx is None:
        return info

    stamp = parts[lat_idx - 2]
    for fmt in ('%d%m%Y%H%M%S', '%d%m%y%H%M%S'):
        try:
            device_time = datetime.strptime(stamp, fmt).replace(tzinfo=dt_timezone.utc)
        except ValueError:
            continue
        if server_time - DEVICE_CLOCK_MAX_BEHIND <= device_time <= server_time + DEVICE_CLOCK_MAX_AHEAD:
            info['time'], info['time_source'] = device_time, 'device'
        break

    try:
        lat, lon = float(parts[lat_idx]), float(parts[lat_idx + 2])
    except ValueError:
        lat = lon = 0.0
    info['valid_gps'] = parts[lat_idx - 1].upper() == 'A' and (lat, lon) != (0.0, 0.0)
    info['speed'] = _to_float(parts[lat_idx + 5] if len(parts) > lat_idx + 5 else None)
    return info


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cadence_summary(label, packets, window_start, window_end):
    """
    Average-gap verdict for one packet stream inside the fixed window.

    The average includes the silence from the window start to the first
    packet and from the last packet to the window end, so it equals
    window length / (packets + 1): a device that stops halfway can't pass
    on the strength of a tidy 5s cadence before it went quiet. The same
    edge silences count toward the single-gap limit.
    """
    times = [p['time'] for p in packets]
    stats = _gap_stats(times)
    stats.pop('gaps')
    edges = [window_start] + sorted(times) + [window_end]
    gaps = [
        {'seconds': (later - earlier).total_seconds(), 'from': earlier.isoformat(), 'to': later.isoformat()}
        for earlier, later in zip(edges, edges[1:])
    ]
    over_limit = [g for g in gaps if g['seconds'] > PVT_DROP_MAX_SINGLE_GAP_SECONDS]
    window_seconds = (window_end - window_start).total_seconds()
    average_gap = round(window_seconds / (len(times) + 1), 2)
    invalid = sorted((p for p in packets if not p['valid_gps']), key=lambda p: p['time'])
    return {
        'label': label,
        'packet_count': len(times),
        'average_gap_seconds': average_gap,
        'average_gap_ok': PVT_DROP_AVG_GAP_MIN_SECONDS <= average_gap <= PVT_DROP_AVG_GAP_MAX_SECONDS,
        'longest_gap': max(gaps, key=lambda g: g['seconds']),
        'over_max_gap_count': len(over_limit),
        'over_max_gap_samples': over_limit[:5],
        'invalid_gps_count': len(invalid),
        'invalid_gps_samples': [{'raw_data': p['raw_data'], 'timestamp': p['time'].isoformat()} for p in invalid[:5]],
        'gap_stats': stats,
    }


def _ist(value):
    """'HH:MM:SS IST' for a datetime or ISO string, for tester-facing reasons."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.astimezone(IST).strftime('%H:%M:%S IST')


def _duration(seconds):
    """'4m 20s' / '45s'."""
    seconds = int(round(seconds))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m {seconds}s" if minutes else f"{seconds}s"


def _pvt_drop_stream_checks(key, summary, window_seconds, window_start, window_end, window_complete, no_packets_hint):
    """
    Pass/fail checks for one packet stream, each with a plain-language
    explanation of what went wrong so the tester knows what to fix.
    """
    label = summary['label']
    count = summary['packet_count']
    checks = [{
        'check': f'{key}_received',
        'label': f'{label} packets received',
        'passed': count > 0,
        'detail': None if count else f"No {label} packets were received during the test. {no_packets_hint}",
    }]
    if not count:
        return checks

    # Packet counts that land inside the 4-6s band over this window length.
    min_expected = int(window_seconds // PVT_DROP_AVG_GAP_MAX_SECONDS)
    max_expected = int(window_seconds // PVT_DROP_AVG_GAP_MIN_SECONDS)
    average_gap = summary['average_gap_seconds']
    detail = None
    if average_gap > PVT_DROP_AVG_GAP_MAX_SECONDS:
        detail = (
            f"{label} packets arrived too slowly: {count} received in {_duration(window_seconds)}, "
            f"average gap {average_gap}s (allowed {PVT_DROP_AVG_GAP_MIN_SECONDS}-{PVT_DROP_AVG_GAP_MAX_SECONDS}s, "
            f"i.e. {min_expected}-{max_expected} packets). The device is sending less often than every 5s "
            f"or packets were lost on the way to the server."
        )
    elif average_gap < PVT_DROP_AVG_GAP_MIN_SECONDS:
        detail = (
            f"{label} packets arrived too often: {count} received in {_duration(window_seconds)}, "
            f"average gap {average_gap}s (allowed {PVT_DROP_AVG_GAP_MIN_SECONDS}-{PVT_DROP_AVG_GAP_MAX_SECONDS}s, "
            f"i.e. {min_expected}-{max_expected} packets). The device's reporting interval is shorter than 5s."
        )
    checks.append({
        'check': f'{key}_average_gap',
        'label': f'{label} average gap {PVT_DROP_AVG_GAP_MIN_SECONDS}-{PVT_DROP_AVG_GAP_MAX_SECONDS}s',
        'passed': detail is None,
        'detail': detail,
    })

    gap_lines = []
    start_iso, end_iso = window_start.isoformat(), window_end.isoformat()
    for gap in summary['over_max_gap_samples'][:3]:
        if gap['from'] == start_iso:
            gap_lines.append(
                f"first packet only at {_ist(gap['to'])}, {_duration(gap['seconds'])} after the test started"
            )
        elif gap['to'] == end_iso and window_complete:
            gap_lines.append(
                f"stopped sending at {_ist(gap['from'])}, {_duration(gap['seconds'])} before the test ended"
            )
        elif gap['to'] == end_iso:
            gap_lines.append(f"nothing received since {_ist(gap['from'])} ({_duration(gap['seconds'])} ago)")
        else:
            gap_lines.append(
                f"nothing received from {_ist(gap['from'])} to {_ist(gap['to'])} ({_duration(gap['seconds'])})"
            )
    over = summary['over_max_gap_count']
    if over > len(gap_lines):
        gap_lines.append(f"and {over - len(gap_lines)} more")
    checks.append({
        'check': f'{key}_max_single_gap',
        'label': f'No {label} gap longer than {_duration(PVT_DROP_MAX_SINGLE_GAP_SECONDS)}',
        'passed': not over,
        'detail': None if not over else (
            f"{over} {label} gap(s) longer than the {_duration(PVT_DROP_MAX_SINGLE_GAP_SECONDS)} limit: "
            + '; '.join(gap_lines) + '.'
        ),
    })

    invalid = summary['invalid_gps_count']
    checks.append({
        'check': f'{key}_valid_gps',
        'label': f'All {label} packets have a valid GPS fix and coordinate',
        'passed': not invalid,
        'detail': None if not invalid else (
            f"{invalid} of {count} {label} packets had no valid GPS fix or a 0,0 coordinate "
            f"(first at {_ist(summary['invalid_gps_samples'][0]['timestamp'])}). The device lost its GPS fix -- "
            f"run the test under open sky with the antenna connected."
        ),
    })
    return checks


def _pvt_packet_drop_check(execution, imei, now):
    """
    Test #41: over a fixed window from the test start (15 min by default)
    the device, moving with emergency ON, must send one PVT packet and one
    EPB emergency packet every ~5s.

    Pass when, for each stream, the average gap is within 4-6s, no single
    gap exceeds 3 min and every packet has a valid GPS fix + coordinate,
    and at least 70% of PVT packets report a speed above 10 km/h. Each
    failed check carries a plain-language reason in 'checks'. Until the window ends the
    snapshot is a live progress report and never passes.

    Packets are placed on the device's own timestamp (when plausible), so
    buffered history packets that arrive late still count for the moment
    they cover. Duplicate rows of the same raw packet count once.
    """
    test_case = execution.test_case
    window_seconds = test_case.scan_window_seconds or DEFAULT_PVT_DROP_WINDOW_SECONDS
    window_start = execution.started_at
    window_end = window_start + timedelta(seconds=window_seconds)
    window_complete = now >= window_end
    evaluated_until = window_end if window_complete else now
    server_until = min(now, window_end + HISTORY_LATE_ARRIVAL_SLACK)

    def scan(model):
        seen = set()
        for raw_data, server_time in (
            model.objects
            .filter(timestamp__gte=window_start, timestamp__lte=server_until, raw_data__contains=imei)
            .order_by('timestamp')
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        ):
            key = raw_data.strip()
            if key not in seen:
                seen.add(key)
                yield raw_data, server_time

    pvt_packets = []
    for raw_data, server_time in scan(GPSDataLog):
        parts = _packet_fields(raw_data)
        idx = _pvt_index(parts)
        if idx is None:
            continue
        effective_time, time_source = _packet_time(raw_data, server_time)
        if not window_start <= effective_time <= evaluated_until:
            continue
        gps_fix = parts[idx + PVT_OFFSET_GPS_FIX] if len(parts) > idx + PVT_OFFSET_GPS_FIX else None
        latitude, longitude = _extract_pvt_lat_lon(raw_data)
        pvt_packets.append({
            'raw_data': raw_data,
            'time': effective_time,
            'latitude': latitude,
            'longitude': longitude,
            'valid_gps': gps_fix == '1' and latitude is not None,
            'speed': _to_float(parts[idx + PVT_OFFSET_SPEED] if len(parts) > idx + PVT_OFFSET_SPEED else None),
        })

    epb_packets = []
    for raw_data, server_time in scan(GPSemDataLog):
        if not _packet_type_in_header(raw_data, 'EPB'):
            continue
        info = _epb_packet_info(raw_data, server_time)
        if window_start <= info['time'] <= evaluated_until:
            epb_packets.append({'raw_data': raw_data, **info})

    pvt = _cadence_summary('PVT', pvt_packets, window_start, evaluated_until)
    epb = _cadence_summary('Emergency (EPB)', epb_packets, window_start, evaluated_until)

    moving = sum(1 for p in pvt_packets if p['speed'] is not None and p['speed'] > PVT_DROP_MOVING_SPEED_KMPH)
    moving_share = round(moving / len(pvt_packets), 4) if pvt_packets else 0.0
    moving_ok = moving_share >= PVT_DROP_MIN_MOVING_SHARE

    elapsed_seconds = (evaluated_until - window_start).total_seconds()
    checks = _pvt_drop_stream_checks(
        'pvt', pvt, elapsed_seconds, window_start, evaluated_until, window_complete,
        'Check that the device is powered on, has mobile network and is reporting to the tracking server.',
    ) + _pvt_drop_stream_checks(
        'emergency', epb, elapsed_seconds, window_start, evaluated_until, window_complete,
        'Emergency mode was not switched ON, or the device is not sending emergency packets to the emergency server.',
    )
    if pvt_packets:
        needed = math.ceil(len(pvt_packets) * PVT_DROP_MIN_MOVING_SHARE)
        checks.append({
            'check': 'moving_share',
            'label': f'At least {PVT_DROP_MIN_MOVING_SHARE:.0%} of PVT packets above {PVT_DROP_MOVING_SPEED_KMPH} km/h',
            'passed': moving_ok,
            'detail': None if moving_ok else (
                f"Only {moving} of {len(pvt_packets)} PVT packets ({moving_share:.0%}) show a speed above "
                f"{PVT_DROP_MOVING_SPEED_KMPH} km/h; at least {needed} ({PVT_DROP_MIN_MOVING_SHARE:.0%}) are needed. "
                f"The vehicle was stationary or moving too slowly during the test."
            ),
        })

    failed = [c for c in checks if not c['passed']]
    failure_lines = ' '.join(f"{n}) {c['detail']}" for n, c in enumerate(failed, 1))

    if window_complete:
        result_pass = not failed
        reason = None if result_pass else f"Failed {len(failed)} of {len(checks)} checks: {failure_lines}"
    else:
        result_pass = False
        reason = (
            f"Test still running -- {_duration((window_end - now).total_seconds())} left "
            f"(ends at {_ist(window_end)}). Keep the browser page open and the vehicle moving above "
            f"{PVT_DROP_MOVING_SPEED_KMPH} km/h with emergency ON, then refresh after it ends."
        )
        if failed:
            reason += f" Problems so far: {failure_lines}"

    return {
        'mode': test_case.source_table,
        'matched_count': min(pvt['packet_count'], epb['packet_count']),
        'pass': result_pass,
        'reason': reason,
        'checks': checks,
        'failed_checks': [c['check'] for c in failed],
        'window_complete': window_complete,
        'window_seconds': window_seconds,
        'remaining_seconds': 0 if window_complete else int((window_end - now).total_seconds()),
        'criteria': {
            'average_gap_seconds_range': [PVT_DROP_AVG_GAP_MIN_SECONDS, PVT_DROP_AVG_GAP_MAX_SECONDS],
            'max_single_gap_seconds': PVT_DROP_MAX_SINGLE_GAP_SECONDS,
            'all_packets_valid_gps': True,
            'moving_speed_kmph': PVT_DROP_MOVING_SPEED_KMPH,
            'min_moving_share': PVT_DROP_MIN_MOVING_SHARE,
        },
        'pvt': pvt,
        'emergency': epb,
        'moving_share': moving_share,
        'moving_ok': moving_ok,
        # Map route: every PVT packet with a valid position, oldest first.
        'route': [
            {'latitude': float(p['latitude']), 'longitude': float(p['longitude']),
             'timestamp': p['time'].isoformat(), 'speed': p['speed']}
            for p in sorted(pvt_packets, key=lambda p: p['time']) if p['valid_gps']
        ],
        'window_start': window_start.isoformat(),
        'window_end': window_end.isoformat(),
        'refreshed_at': now.isoformat(),
    }


def _gap_stats(times):
    """
    Time-gap statistics between consecutive packets. `times` need not be
    sorted. Gaps are in seconds; 'gaps' lists every gap with its endpoints.
    """
    ordered = sorted(times)
    gaps = [
        {'seconds': (later - earlier).total_seconds(), 'from': earlier.isoformat(), 'to': later.isoformat()}
        for earlier, later in zip(ordered, ordered[1:])
    ]
    seconds = [g['seconds'] for g in gaps]
    return {
        'packet_count': len(ordered),
        'first_packet_at': ordered[0].isoformat() if ordered else None,
        'last_packet_at': ordered[-1].isoformat() if ordered else None,
        'gap_count': len(gaps),
        'average_gap_seconds': round(statistics.mean(seconds), 2) if seconds else None,
        'median_gap_seconds': round(statistics.median(seconds), 2) if seconds else None,
        'min_gap_seconds': min(seconds) if seconds else None,
        'max_gap_seconds': max(seconds) if seconds else None,
        'longest_gap': max(gaps, key=lambda g: g['seconds']) if gaps else None,
        'gaps': gaps,
    }


def _get_onboarding_request_or_error(onboarding_request_id):
    onboarding_request = DeviceModelTechnicalOnboardingRequest.objects.filter(id=onboarding_request_id).last()
    if not onboarding_request:
        return None, Response({'error': 'Invalid onboarding_request_id.'}, status=status.HTTP_400_BAD_REQUEST)
    return onboarding_request, None


# ===========================================================================
# Manufacturer-side: courier tracking
# ===========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def manufacturer_update_courier_tracking(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    manufacturer = get_user_object(request.user, 'devicemanufacture')
    if not manufacturer:
        return Response({'error': 'Request must be from devicemanufacture.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingCourierTrackingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data

    onboarding_request, error = _get_onboarding_request_or_error(data['onboarding_request_id'])
    if error:
        return error
    if onboarding_request.manufacturer_id != manufacturer.id:
        return Response({'error': 'This onboarding request does not belong to your manufacturer account.'}, status=status.HTTP_400_BAD_REQUEST)
    if onboarding_request.status != 'submitted':
        return Response({'error': 'Courier tracking can only be updated while the request is submitted.'}, status=status.HTTP_400_BAD_REQUEST)

    update_fields = []
    for field in ('courier_name', 'courier_tracking_number', 'courier_shipped_date'):
        if field in data:
            setattr(onboarding_request, field, data[field])
            update_fields.append(field)
    if update_fields:
        onboarding_request.save(update_fields=update_fields)

    response_serializer = DeviceModelTechnicalOnboardingRequestDetailSerializer(onboarding_request)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


# ===========================================================================
# Superadmin-side: stock receipt confirmation
# ===========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def superadmin_confirm_demo_device_receipt(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingConfirmReceiptSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data

    onboarding_request, error = _get_onboarding_request_or_error(data['onboarding_request_id'])
    if error:
        return error

    demo_device = DeviceModelTechnicalOnboardingDemoDevice.objects.filter(
        id=data['demo_device_id'], onboarding_request=onboarding_request
    ).last()
    if not demo_device:
        return Response({'error': 'Invalid demo_device_id for this onboarding request.'}, status=status.HTTP_400_BAD_REQUEST)

    fields = [
        'receipt_confirmed', 'receipt_confirmed_at', 'receipt_confirmed_by',
        'receipt_rejected', 'receipt_rejected_at', 'receipt_rejected_by', 'receipt_reject_reason',
    ]
    if data['status'] == 'rejected':
        demo_device.receipt_confirmed = False
        demo_device.receipt_confirmed_at = None
        demo_device.receipt_confirmed_by = None
        demo_device.receipt_rejected = True
        demo_device.receipt_rejected_at = timezone.now()
        demo_device.receipt_rejected_by = request.user
        demo_device.receipt_reject_reason = data['remarks'].strip()
        demo_device.save(update_fields=fields)
        if onboarding_request.status in ('submitted', 'stock_received'):
            onboarding_request.status = 'stock_rejected'
            onboarding_request.save(update_fields=['status'])
    else:
        demo_device.receipt_confirmed = True
        demo_device.receipt_confirmed_at = timezone.now()
        demo_device.receipt_confirmed_by = request.user
        demo_device.receipt_rejected = False
        demo_device.receipt_rejected_at = None
        demo_device.receipt_rejected_by = None
        demo_device.receipt_reject_reason = ''
        demo_device.save(update_fields=fields)

        if onboarding_request.status in ('submitted', 'stock_rejected'):
            devices = onboarding_request.demo_devices
            if not devices.filter(receipt_confirmed=False).exists():
                onboarding_request.status = 'stock_received'
                onboarding_request.save(update_fields=['status'])
            elif onboarding_request.status == 'stock_rejected' and not devices.filter(receipt_rejected=True).exists():
                onboarding_request.status = 'submitted'
                onboarding_request.save(update_fields=['status'])

    response_serializer = DeviceModelTechnicalOnboardingRequestDetailSerializer(onboarding_request)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


# ===========================================================================
# Test case catalog
# ===========================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'view')
def technical_onboarding_test_case_list(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    test_cases = TechnicalOnboardingTestCase.objects.filter(active=True).order_by('serial_no')
    serializer = TechnicalOnboardingTestCaseSerializer(test_cases, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def technical_onboarding_test_case_upsert(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    test_case_id = request.data.get('id')
    instance = TechnicalOnboardingTestCase.objects.filter(id=test_case_id).last() if test_case_id else None

    serializer = TechnicalOnboardingTestCaseSerializer(instance=instance, data=request.data, partial=bool(instance))
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    test_case = serializer.save()

    return Response(
        TechnicalOnboardingTestCaseSerializer(test_case).data,
        status=status.HTTP_200_OK if instance else status.HTTP_201_CREATED,
    )


# ===========================================================================
# Test board + execution engine
# ===========================================================================

def _serialize_board(onboarding_request):
    test_cases = list(TechnicalOnboardingTestCase.objects.filter(active=True).order_by('serial_no'))
    demo_devices = list(onboarding_request.demo_devices.all().order_by('id'))

    def load_existing():
        return {
            (e.demo_device_id, e.test_case_id): e
            for e in TechnicalOnboardingTestExecution.objects.filter(onboarding_request=onboarding_request)
        }

    existing = load_existing()

    to_create = []
    for test_case in test_cases:
        for demo_device in demo_devices:
            if (demo_device.id, test_case.id) not in existing:
                to_create.append(TechnicalOnboardingTestExecution(
                    onboarding_request=onboarding_request, demo_device=demo_device, test_case=test_case,
                ))
    if to_create:
        TechnicalOnboardingTestExecution.objects.bulk_create(to_create, ignore_conflicts=True)
        existing = load_existing()

    # Each execution embeds its test case and demo device. Attach the objects
    # already loaded above and share one serializer context, so the board
    # needs one checkpoint query in total instead of one per execution.
    test_case_by_id = {test_case.id: test_case for test_case in test_cases}
    demo_device_by_id = {demo_device.id: demo_device for demo_device in demo_devices}
    for execution in existing.values():
        if execution.test_case_id in test_case_by_id:
            execution.test_case = test_case_by_id[execution.test_case_id]
        if execution.demo_device_id in demo_device_by_id:
            execution.demo_device = demo_device_by_id[execution.demo_device_id]
    context = {'_checkpoint_status_cache': build_checkpoint_status_map(demo_device_by_id)}

    rows = []
    for test_case in test_cases:
        executions = [existing[(d.id, test_case.id)] for d in demo_devices if (d.id, test_case.id) in existing]
        rows.append({
            'test_case': TechnicalOnboardingTestCaseSerializer(test_case).data,
            'executions': TechnicalOnboardingTestExecutionSerializer(executions, many=True, context=context).data,
        })

    return {
        'onboarding_request_id': onboarding_request.id,
        'status': onboarding_request.status,
        'current_unlocked_serial_no': _current_unlocked_serial_no(onboarding_request),
        'rows': rows,
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'view')
def superadmin_get_onboarding_test_board(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingTestBoardRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    onboarding_request, error = _get_onboarding_request_or_error(serializer.validated_data['onboarding_request_id'])
    if error:
        return error
    if onboarding_request.status in ('submitted',):
        return Response({'error': 'Testing is only available once all stock has been received.'}, status=status.HTTP_400_BAD_REQUEST)

    _sweep_stale_executions(onboarding_request)
    return Response(_serialize_board(onboarding_request), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def superadmin_start_test(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingStartTestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data

    onboarding_request, error = _get_onboarding_request_or_error(data['onboarding_request_id'])
    if error:
        return error
    if onboarding_request.status not in ('stock_received', 'ongoing_evaluation'):
        return Response({'error': 'Testing is only available once all stock has been received.'}, status=status.HTTP_400_BAD_REQUEST)

    _sweep_stale_executions(onboarding_request)

    demo_device = DeviceModelTechnicalOnboardingDemoDevice.objects.filter(
        id=data['demo_device_id'], onboarding_request=onboarding_request
    ).last()
    test_case = TechnicalOnboardingTestCase.objects.filter(id=data['test_case_id'], active=True).last()
    if not demo_device or not test_case:
        return Response({'error': 'Invalid demo_device_id or test_case_id.'}, status=status.HTTP_400_BAD_REQUEST)

    if not test_case.is_optional:
        unlocked = _current_unlocked_serial_no(onboarding_request)
        if unlocked is not None and test_case.serial_no != unlocked:
            return Response(
                {'error': f'Test #{test_case.serial_no} is locked. Complete test #{unlocked} for all IMEIs first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    execution, _created = TechnicalOnboardingTestExecution.objects.get_or_create(
        onboarding_request=onboarding_request, demo_device=demo_device, test_case=test_case,
    )
    if execution.status in ('in_progress', 'complete'):
        return Response(
            {'error': f'This test is already {execution.status} for this IMEI.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    execution.status = 'in_progress'
    execution.attempt_number += 1
    execution.started_at = now
    execution.started_by = request.user
    execution.last_heartbeat_at = now
    execution.completed_at = None
    execution.completed_by = None
    execution.test_log_snapshot = None
    execution.last_refreshed_at = None
    execution.manual_result = None
    execution.manual_notes = None
    execution.save()

    if onboarding_request.status == 'stock_received':
        onboarding_request.status = 'ongoing_evaluation'
        onboarding_request.evaluation_datetime = now
        onboarding_request.save(update_fields=['status', 'evaluation_datetime'])

    return Response(TechnicalOnboardingTestExecutionSerializer(execution).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def superadmin_test_heartbeat(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingExecutionActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    execution = TechnicalOnboardingTestExecution.objects.filter(id=serializer.validated_data['execution_id']).last()
    if not execution:
        return Response({'error': 'Invalid execution_id.'}, status=status.HTTP_400_BAD_REQUEST)

    if execution.status != 'in_progress':
        return Response({'error': f'Test is {execution.status}, not in progress.'}, status=status.HTTP_400_BAD_REQUEST)

    execution.last_heartbeat_at = timezone.now()
    execution.save(update_fields=['last_heartbeat_at'])
    return Response({'status': 'ok', 'last_heartbeat_at': execution.last_heartbeat_at}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def superadmin_refresh_test_log(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingRefreshTestLogSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data

    execution = TechnicalOnboardingTestExecution.objects.select_related(
        'test_case', 'demo_device', 'onboarding_request'
    ).filter(id=data['execution_id']).last()
    if not execution:
        return Response({'error': 'Invalid execution_id.'}, status=status.HTTP_400_BAD_REQUEST)

    _sweep_stale_executions(execution.onboarding_request)
    execution.refresh_from_db()

    if execution.status != 'in_progress':
        return Response(
            {'error': f'Test is {execution.status}, not in progress.', 'status': execution.status},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Geofence test: points marked on the map stick for the rest of the
    # attempt (the snapshot is cleared when the test is started again).
    points = dict((execution.test_log_snapshot or {}).get('geofence_points') or {})
    for key, field in (('in', 'geofence_in'), ('out', 'geofence_out')):
        if data.get(field):
            points[key] = data[field]
    execution.geofence_points = points

    snapshot = _run_test_check(execution)
    execution.test_log_snapshot = snapshot
    execution.last_refreshed_at = timezone.now()
    execution.save(update_fields=['test_log_snapshot', 'last_refreshed_at'])

    return Response(snapshot, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def superadmin_complete_test(request):
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingCompleteTestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data

    execution = TechnicalOnboardingTestExecution.objects.select_related(
        'test_case', 'demo_device', 'onboarding_request'
    ).filter(id=data['execution_id']).last()
    if not execution:
        return Response({'error': 'Invalid execution_id.'}, status=status.HTTP_400_BAD_REQUEST)

    onboarding_request = execution.onboarding_request
    _sweep_stale_executions(onboarding_request)
    execution.refresh_from_db()

    if execution.status != 'in_progress':
        return Response(
            {
                'error': f'Test is already {execution.status} (likely due to an inactive session). '
                         f'Start the test again to retry.',
                'status': execution.status,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    test_case = execution.test_case
    now = timezone.now()

    if test_case.source_table == 'manual':
        # Manual-only tests no longer require the caller to submit a
        # manual_result -- completion auto-marks it 'pass' unless the
        # caller explicitly overrides it (e.g. to record a fail).
        manual_result = data.get('manual_result') or 'pass'
        passed = manual_result == 'pass'
        execution.manual_result = manual_result
        execution.manual_notes = data.get('manual_notes', '')
    else:
        if not execution.last_refreshed_at or execution.last_refreshed_at < execution.started_at:
            return Response({'error': 'Refresh the test log at least once before completing this test.'}, status=status.HTTP_400_BAD_REQUEST)
        auto_passed = bool((execution.test_log_snapshot or {}).get('pass'))
        if test_case.requires_manual_confirmation:
            # The automated check only proves a packet arrived -- it can't
            # judge an accuracy comparison, a field-by-field protocol read,
            # or an A-vs-B firmware check. The confirmation can't come
            # first: without the packet already in GPSDataLog/GPSemDataLog
            # there's nothing for the tester to be confirming, so
            # completion attempted before the automated check has found
            # the data is rejected outright. Once the automated check has
            # passed, the manual side is auto-marked 'pass' unless the
            # caller explicitly overrides it.
            if not auto_passed:
                table_label = SOURCE_TABLE_LABEL.get(test_case.source_table, test_case.source_table)
                return Response(
                    {
                        'error': (
                            f'The required packet has not been found in {table_label} yet. '
                            'Trigger the event on the device, refresh the test log, and confirm once it shows up.'
                        ),
                        'snapshot': execution.test_log_snapshot,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            manual_result = data.get('manual_result') or 'pass'
            execution.manual_result = manual_result
            execution.manual_notes = data.get('manual_notes', '')
            passed = auto_passed and manual_result == 'pass'
        else:
            passed = auto_passed

    execution.status = 'complete' if passed else 'incomplete'
    execution.completed_at = now
    execution.completed_by = request.user
    execution.save()

    if execution.status == 'complete' and _all_tests_complete(onboarding_request):
        onboarding_request.status = 'testing_complete'
        onboarding_request.save(update_fields=['status'])

    return Response(TechnicalOnboardingTestExecutionSerializer(execution).data, status=status.HTTP_200_OK)


def _get_execution_or_error(execution_id):
    execution = TechnicalOnboardingTestExecution.objects.select_related(
        'test_case', 'demo_device', 'onboarding_request'
    ).filter(id=execution_id).last()
    if not execution:
        return None, Response({'error': 'Invalid execution_id.'}, status=status.HTTP_400_BAD_REQUEST)
    return execution, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'view')
def superadmin_list_test_commands(request):
    """
    The commands configured for an execution's test case, plus every
    command already sent during the current attempt with the device's
    replies (plain-text replies and OT,12 packets within 2 minutes).
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingExecutionActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    execution, error = _get_execution_or_error(serializer.validated_data['execution_id'])
    if error:
        return error

    return Response({
        'execution_id': execution.id,
        'imei': execution.demo_device.imei,
        'requires_command': execution.test_case.requires_command,
        'commands': execution.test_case.commands or [],
        'commands_sent': _commands_sent(execution),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@transaction.atomic
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'update')
def superadmin_send_test_command(request):
    """
    Send a command to the demo device of an in-progress test over MQTT
    (published to deviceResponse/{imei} as {"keys": "@...*"}).

    Body: {"execution_id": 1, "command_key": "sos_stop"}
          {"execution_id": 1, "command_key": "set_reg_no", "value": "AS01AA0009"}
          {"execution_id": 1, "command": "SETSOSDIS-1"}   -- custom command
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingSendTestCommandSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data

    execution, error = _get_execution_or_error(data['execution_id'])
    if error:
        return error

    _sweep_stale_executions(execution.onboarding_request)
    execution.refresh_from_db()
    if execution.status != 'in_progress':
        return Response(
            {'error': f'Test is {execution.status}, not in progress. Start the test before sending commands.', 'status': execution.status},
            status=status.HTTP_400_BAD_REQUEST,
        )

    value = (data.get('value') or '').strip() or None
    command_key = data.get('command_key') or ''
    if command_key:
        definition = next((c for c in (execution.test_case.commands or []) if c.get('key') == command_key), None)
        if not definition or not definition.get('command'):
            return Response(
                {'error': f"Command '{command_key}' is not configured for this test."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        template = definition['command']
        label = definition.get('label') or command_key
        if '{value}' in template:
            if not value:
                return Response({'error': f"A value is required for '{label}'."}, status=status.HTTP_400_BAD_REQUEST)
            if definition.get('value_regex') and not re.fullmatch(definition['value_regex'], value):
                return Response(
                    {'error': f"Value '{value}' is not in the expected format for '{label}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            template = template.replace('{value}', value)
    else:
        template = data['command']
        label = 'Custom command'

    imei = execution.demo_device.imei
    wire_command = _frame_command(template)
    dispatch = TechnicalOnboardingCommandDispatch(
        execution=execution,
        imei=imei,
        command_key=command_key,
        command_label=label,
        command_sent=wire_command,
        value=value,
        sent_by=request.user,
        sent_at=timezone.now(),
    )
    try:
        send_general_mqtt_message(imei, {'keys': wire_command})
    except Exception:
        dispatch.send_status = 'failed'
        dispatch.error = 'Could not publish the command to the MQTT broker.'
    dispatch.save()

    # Heartbeat on send, so a tester busy sending commands isn't timed out.
    execution.last_heartbeat_at = timezone.now()
    execution.save(update_fields=['last_heartbeat_at'])

    body = {
        'id': dispatch.id,
        'execution_id': execution.id,
        'imei': imei,
        'command_key': command_key,
        'command_label': label,
        'command_sent': wire_command,
        'value': value,
        'send_status': dispatch.send_status,
        'error': dispatch.error,
        'sent_at': dispatch.sent_at.isoformat(),
    }
    return Response(body, status=status.HTTP_200_OK if dispatch.send_status == 'queued' else status.HTTP_502_BAD_GATEWAY)


# ===========================================================================
# Demo-device location history + packet gap statistics
# ===========================================================================

def _pvt_history_entry(raw_data, parts, idx, server_time, effective_time, time_source):
    def field(offset):
        return parts[idx + offset] if len(parts) > idx + offset else None

    latitude, longitude = _extract_pvt_lat_lon(raw_data)
    device_time = _extract_pvt_datetime(raw_data)
    return {
        'timestamp': effective_time.isoformat(),
        'time_source': time_source,
        'device_timestamp': device_time.isoformat() if device_time else None,
        'server_timestamp': server_time.isoformat(),
        'latitude': float(latitude) if latitude is not None else None,
        'longitude': float(longitude) if longitude is not None else None,
        'speed': field(PVT_OFFSET_SPEED),
        'heading': field(PVT_OFFSET_HEADING),
        'ignition': field(PVT_OFFSET_IGNITION),
        'packet_type': field(PVT_OFFSET_PACKET_TYPE),
        'packet_status': field(PVT_OFFSET_PACKET_STATUS),
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
@require_http_methods(['GET', 'POST'])
@require_permission('manufacturer_management', 'view')
def superadmin_demo_device_location_history(request):
    """
    PVT location history for every demo device on an onboarding request,
    with per-device time-gap statistics between packets.

    Request body:
      {"onboarding_request_id": 12, "timestamp": "2026-09-24T10:00:00Z"}
          -> the 1 hour ending at `timestamp` (defaults to now)
      {"onboarding_request_id": 12,
       "start_datetime": "...", "end_datetime": "..."}
          -> any range up to 24 hours

    Entries and gaps are keyed on the device timestamp inside the packet
    (server receive time when it's missing or implausible -- see
    _packet_time), so buffered history (H) packets land where they belong
    in the timeline.
    """
    errors = validate_inputs(request)
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not get_user_object(request.user, 'superadmin'):
        return Response({'error': 'Request must be from superadmin.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TechnicalOnboardingDemoDeviceHistorySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data

    onboarding_request, error = _get_onboarding_request_or_error(data['onboarding_request_id'])
    if error:
        return error

    start, end = data['start_datetime'], data['end_datetime']
    demo_devices = list(onboarding_request.demo_devices.all().order_by('id'))
    if not demo_devices:
        return Response({'error': 'This onboarding request has no demo devices.'}, status=status.HTTP_400_BAD_REQUEST)

    imei_filter = Q()
    for demo_device in demo_devices:
        imei_filter |= Q(raw_data__contains=demo_device.imei)

    rows = list(
        GPSDataLog.objects
        .filter(timestamp__gte=start, timestamp__lte=end + HISTORY_LATE_ARRIVAL_SLACK)
        .filter(imei_filter)
        .filter(raw_data__contains='PVT')
        .order_by('timestamp')
        .values_list('raw_data', 'timestamp')[:HISTORY_ROW_LIMIT + 1]
    )
    truncated = len(rows) > HISTORY_ROW_LIMIT
    rows = rows[:HISTORY_ROW_LIMIT]

    entries_by_imei = {d.imei: [] for d in demo_devices}
    for raw_data, server_time in rows:
        parts = _packet_fields(raw_data)
        idx = _pvt_index(parts)
        if idx is None:
            continue
        imei = parts[idx + PVT_OFFSET_IMEI] if len(parts) > idx + PVT_OFFSET_IMEI else None
        if imei not in entries_by_imei:
            continue
        effective_time, time_source = _packet_time(raw_data, server_time)
        if not start <= effective_time <= end:
            continue
        entries_by_imei[imei].append(
            (effective_time, _pvt_history_entry(raw_data, parts, idx, server_time, effective_time, time_source))
        )

    devices = []
    for demo_device in demo_devices:
        timed_entries = sorted(entries_by_imei[demo_device.imei], key=lambda pair: pair[0])
        stats = _gap_stats([t for t, _entry in timed_entries])
        stats.pop('gaps')
        devices.append({
            'demo_device_id': demo_device.id,
            'device_serial_no': demo_device.device_serial_no,
            'imei': demo_device.imei,
            'location_count': sum(1 for _t, e in timed_entries if e['latitude'] is not None),
            'gap_stats': stats,
            'entries': [entry for _t, entry in timed_entries],
        })

    return Response(
        {
            'onboarding_request_id': onboarding_request.id,
            'start_datetime': start.isoformat(),
            'end_datetime': end.isoformat(),
            'truncated': truncated,
            'devices': devices,
        },
        status=status.HTTP_200_OK,
    )


# ===========================================================================
# Demo page
# ===========================================================================

def technical_onboarding_demo_page(request):
    return render(request, 'technical_onboarding_demo.html')


def technical_onboarding_test_catalog_page(request):
    return render(request, 'technical_onboarding_test_catalog.html')


def technical_onboarding_test_requirements_page(request):
    return render(request, 'technical_onboarding_test_requirements.html')


# ===========================================================================
# DEV-ONLY: force-pass a checkpoint
# ===========================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
@_dev_only
@transaction.atomic
def dev_force_pass_test(request):
    """
    DEV-ONLY -- force checkpoint `test_no` (any catalog serial_no) to 'complete' for `imei`
    with a dummy snapshot, bypassing every real trigger/detection path.

    Exists so the rest of the pipeline (sequential gating, certificate
    issuance, dashboards) can be exercised end-to-end without physically
    operating a device through every checkpoint. Blocked automatically
    outside DEBUG by @_dev_only, same as dev_get_token/dev_list_users.

    Request body: {"imei": "<imei>", "test_no": 1}
    """
    imei = (request.data.get('imei') or '').strip()
    test_no = request.data.get('test_no')

    if not imei:
        return Response({'error': 'imei is required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        test_no = int(test_no)
    except (TypeError, ValueError):
        return Response({'error': 'test_no must be an integer serial_no from the test catalog.'}, status=status.HTTP_400_BAD_REQUEST)

    test_case = TechnicalOnboardingTestCase.objects.filter(serial_no=test_no).last()
    if not test_case:
        return Response({'error': f'No test case with serial_no={test_no}.'}, status=status.HTTP_400_BAD_REQUEST)

    demo_device = (
        DeviceModelTechnicalOnboardingDemoDevice.objects
        .filter(imei=imei)
        .select_related('onboarding_request')
        .last()
    )
    if not demo_device:
        return Response(
            {'error': f'IMEI {imei} is not registered as a demo device on any technical onboarding request.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    onboarding_request = demo_device.onboarding_request
    now = timezone.now()

    execution, _created = TechnicalOnboardingTestExecution.objects.get_or_create(
        onboarding_request=onboarding_request, demo_device=demo_device, test_case=test_case,
    )

    execution.status = 'complete'
    execution.attempt_number += 1
    execution.started_at = execution.started_at or now
    execution.last_heartbeat_at = now
    execution.test_log_snapshot = {
        'mode': 'dev_bypass',
        'pass': True,
        'reason': 'Force-passed via the DEV bypass endpoint -- not real device evidence.',
        'samples': [],
        'window_start': now.isoformat(),
        'refreshed_at': now.isoformat(),
        'forced': True,
    }
    execution.last_refreshed_at = now
    execution.manual_result = 'pass'
    execution.manual_notes = 'Force-passed via DEV bypass endpoint (dev_force_pass_test).'
    execution.completed_at = now
    execution.completed_by = None
    execution.save()

    if onboarding_request.status == 'stock_received':
        onboarding_request.status = 'ongoing_evaluation'
        onboarding_request.evaluation_datetime = onboarding_request.evaluation_datetime or now
        onboarding_request.save(update_fields=['status', 'evaluation_datetime'])

    if _all_tests_complete(onboarding_request):
        onboarding_request.status = 'testing_complete'
        onboarding_request.save(update_fields=['status'])

    return Response(
        {
            'status': 'forced_complete',
            'message': f"Checkpoint #{test_no} ({test_case.name}) force-passed for IMEI {imei}. This is dummy evidence, not a real result.",
            'execution': TechnicalOnboardingTestExecutionSerializer(execution).data,
        },
        status=status.HTTP_200_OK,
    )
