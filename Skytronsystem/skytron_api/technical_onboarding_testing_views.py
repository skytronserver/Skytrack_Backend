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

from .dev_views import _dev_only
from .models import (
    DeviceModelTechnicalOnboardingRequest,
    DeviceModelTechnicalOnboardingDemoDevice,
    TechnicalOnboardingTestCase,
    TechnicalOnboardingTestExecution,
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
    TechnicalOnboardingTestExecutionSerializer,
    TechnicalOnboardingDemoDeviceHistorySerializer,
    build_checkpoint_status_map,
)
from .views import (
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
PVT_OFFSET_PACKET_STATUS = 5    # L = live, H = history (buffered)
PVT_OFFSET_IMEI = 6
PVT_OFFSET_SPEED = 15
PVT_OFFSET_HEADING = 16
PVT_OFFSET_IGNITION = 22

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
    Dispatches on test_case.source_table and returns a snapshot dict.
    Does not persist anything -- the caller decides what to do with it.
    """
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

    window_start = _window_start(execution)

    if test_case.source_table in ('gps', 'gpsem'):
        model = GPSDataLog if test_case.source_table == 'gps' else GPSemDataLog
        rows = list(
            model.objects
            .filter(timestamp__gte=window_start, raw_data__contains=imei)
            .order_by('-timestamp')
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        )
        pattern = re.compile(test_case.regex_pattern) if test_case.regex_pattern else None
        matched_times = []
        samples = []
        for raw_data, packet_time in rows:
            if pattern and not pattern.search(raw_data):
                continue
            matched_times.append(packet_time)
            if len(samples) < 5:
                samples.append({'raw_data': raw_data, 'timestamp': packet_time.isoformat()})

        matched_count = len(matched_times)
        result_pass = matched_count >= test_case.min_match_count
        reason = None
        if result_pass and test_case.max_interval_seconds:
            ordered = sorted(matched_times)
            for earlier, later in zip(ordered, ordered[1:]):
                if (later - earlier).total_seconds() > test_case.max_interval_seconds:
                    result_pass = False
                    reason = (
                        f"Gap of {(later - earlier).total_seconds():.0f}s between packets exceeds "
                        f"the required {test_case.max_interval_seconds}s cadence."
                    )
                    break
        if not result_pass and reason is None:
            reason = f"Only {matched_count} matching packet(s) found, need at least {test_case.min_match_count}."

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

    if test_case.source_table == 'firmware_diff':
        # A FOTA upgrade doesn't have its own packet type -- every PVT/HLM
        # packet already carries the running firmware version as its 3rd
        # field ($,PVT,MAPW,1.1.1,... / $,HLM,MAPW,1.1.1,...). Seeing 2+
        # distinct version strings for this device inside the window is
        # direct proof the firmware actually changed, not just that an
        # upgrade command was sent.
        rows = list(
            GPSDataLog.objects
            .filter(timestamp__gte=window_start, raw_data__contains=imei)
            .order_by('-timestamp')
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        )
        versions_seen = {}
        for raw_data, packet_time in rows:
            parts = _packet_fields(raw_data)
            if len(parts) < 3 or parts[0].upper() not in ('PVT', 'HLM'):
                continue
            version = parts[2]
            if version and version not in versions_seen:
                versions_seen[version] = {'raw_data': raw_data, 'timestamp': packet_time.isoformat()}

        matched_count = len(versions_seen)
        result_pass = matched_count >= test_case.min_match_count
        reason = None if result_pass else (
            f"Only {matched_count} distinct firmware version(s) seen ({', '.join(versions_seen) or 'none'}), "
            f"need at least {test_case.min_match_count} -- the upgrade hasn't taken effect on the device yet."
        )
        return {
            'mode': test_case.source_table,
            'matched_count': matched_count,
            'required': test_case.min_match_count,
            'pass': result_pass,
            'reason': reason,
            'samples': list(versions_seen.values())[:5],
            'versions_seen': list(versions_seen.keys()),
            'window_start': window_start.isoformat(),
            'refreshed_at': now.isoformat(),
        }

    if test_case.source_table in ('voltage_internal', 'voltage_external'):
        # A single PVT packet only proves one voltage reading -- the check
        # is that the tester actually varied the supply/battery across the
        # window, which shows up as 3+ distinct voltage strings.
        field_idx = PVT_INTERNAL_VOLTAGE_IDX if test_case.source_table == 'voltage_internal' else PVT_MAIN_VOLTAGE_IDX
        label = 'internal battery voltage' if test_case.source_table == 'voltage_internal' else 'external/main voltage'
        rows = list(
            GPSDataLog.objects
            .filter(timestamp__gte=window_start, raw_data__contains=imei)
            .order_by('-timestamp')
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        )
        values_seen = {}
        for raw_data, packet_time in rows:
            parts = _packet_fields(raw_data)
            if len(parts) <= field_idx or parts[0].upper() != 'PVT':
                continue
            value = parts[field_idx].strip()
            if value and value not in values_seen:
                values_seen[value] = {'raw_data': raw_data, 'timestamp': packet_time.isoformat()}

        matched_count = len(values_seen)
        result_pass = matched_count >= test_case.min_match_count
        reason = None if result_pass else (
            f"Only {matched_count} distinct {label} level(s) seen ({', '.join(values_seen) or 'none'}), "
            f"need at least {test_case.min_match_count} within the test window."
        )
        return {
            'mode': test_case.source_table,
            'matched_count': matched_count,
            'required': test_case.min_match_count,
            'pass': result_pass,
            'reason': reason,
            'samples': list(values_seen.values())[:5],
            'values_seen': list(values_seen.keys()),
            'window_start': window_start.isoformat(),
            'refreshed_at': now.isoformat(),
        }

    if test_case.source_table in ('esim_primary_to_secondary', 'esim_secondary_to_primary'):
        rows = list(
            GPSDataLog.objects
            .filter(timestamp__gte=window_start, raw_data__contains=imei)
            .order_by('timestamp')  # ascending -- order of first appearance matters here
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        )
        ordered_networks = []
        seen = set()
        for raw_data, packet_time in rows:
            parts = _packet_fields(raw_data)
            if len(parts) <= PVT_NETWORK_OPERATOR_IDX or parts[0].upper() != 'PVT':
                continue
            network = parts[PVT_NETWORK_OPERATOR_IDX].strip()
            if network and network not in seen:
                seen.add(network)
                ordered_networks.append({'network': network, 'raw_data': raw_data, 'timestamp': packet_time.isoformat()})

        matched_count = len(ordered_networks)
        result_pass = matched_count >= test_case.min_match_count
        reason = None
        if not result_pass:
            reason = (
                f"Only {matched_count} distinct network(s) seen "
                f"({', '.join(n['network'] for n in ordered_networks) or 'none'}), need at least "
                f"{test_case.min_match_count} within the test window to prove the eSIM switch happened."
            )

        # Cross-check direction against the sibling eSIM test: the network
        # order seen here should be the exact reverse of whatever the other
        # direction's most recent completed run recorded.
        sibling_source = ESIM_SIBLING_SOURCE.get(test_case.source_table)
        if result_pass and sibling_source:
            sibling_case = TechnicalOnboardingTestCase.objects.filter(
                source_table=sibling_source, active=True
            ).order_by('serial_no').first()
            sibling_execution = None
            if sibling_case:
                sibling_execution = TechnicalOnboardingTestExecution.objects.filter(
                    onboarding_request=execution.onboarding_request,
                    demo_device=execution.demo_device,
                    test_case=sibling_case,
                    status='complete',
                ).order_by('-completed_at').first()
            sibling_networks = (
                (sibling_execution.test_log_snapshot or {}).get('networks_seen')
                if sibling_execution else None
            )
            if sibling_networks and len(sibling_networks) >= 2:
                this_first, this_second = ordered_networks[0]['network'], ordered_networks[1]['network']
                expected_first, expected_second = sibling_networks[1], sibling_networks[0]
                if this_first != expected_first or this_second != expected_second:
                    result_pass = False
                    reason = (
                        f"Network order does not mirror '{sibling_case.name}': expected first "
                        f"'{expected_first}' then '{expected_second}' (reverse of that test's order), "
                        f"but saw '{this_first}' then '{this_second}'."
                    )

        return {
            'mode': test_case.source_table,
            'matched_count': matched_count,
            'required': test_case.min_match_count,
            'pass': result_pass,
            'reason': reason,
            'samples': [{'raw_data': n['raw_data'], 'timestamp': n['timestamp']} for n in ordered_networks[:5]],
            'networks_seen': [n['network'] for n in ordered_networks],
            'window_start': window_start.isoformat(),
            'refreshed_at': now.isoformat(),
        }

    if test_case.source_table == 'vehicle_registration_diff':
        # Only proof required is that the registration number reported by
        # the device changed to something new during the window -- find
        # the last known value before the window as the baseline, then
        # look for any different value inside it.
        baseline_raw = (
            GPSDataLog.objects
            .filter(timestamp__lt=window_start, raw_data__contains=imei)
            .order_by('-timestamp')
            .values_list('raw_data', flat=True)
            .first()
        )
        baseline_value = None
        if baseline_raw:
            parts = _packet_fields(baseline_raw)
            if len(parts) > PVT_VEHICLE_REG_NO_IDX and parts[0].upper() == 'PVT':
                baseline_value = parts[PVT_VEHICLE_REG_NO_IDX].strip() or None

        rows = list(
            GPSDataLog.objects
            .filter(timestamp__gte=window_start, raw_data__contains=imei)
            .order_by('-timestamp')
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        )
        new_values = {}
        for raw_data, packet_time in rows:
            parts = _packet_fields(raw_data)
            if len(parts) <= PVT_VEHICLE_REG_NO_IDX or parts[0].upper() != 'PVT':
                continue
            value = parts[PVT_VEHICLE_REG_NO_IDX].strip()
            if value and value != baseline_value and value not in new_values:
                new_values[value] = {'raw_data': raw_data, 'timestamp': packet_time.isoformat()}

        matched_count = len(new_values)
        result_pass = matched_count >= test_case.min_match_count
        reason = None if result_pass else (
            f"Registration number is still '{baseline_value or 'unknown'}' -- no new value seen within the test window."
        )
        return {
            'mode': test_case.source_table,
            'matched_count': matched_count,
            'required': test_case.min_match_count,
            'pass': result_pass,
            'reason': reason,
            'samples': list(new_values.values())[:5],
            'baseline_value': baseline_value,
            'window_start': window_start.isoformat(),
            'refreshed_at': now.isoformat(),
        }

    if test_case.source_table == 'reboot_restart_gap':
        # A reboot has no meaningful text reply -- the real proof is the
        # device dropping off the tracking stream and then resuming after
        # the reboot command was actually dispatched.
        pattern = re.compile(test_case.regex_pattern) if test_case.regex_pattern else None
        command_row = None
        for row in (
            OTACommandHistory.objects
            .filter(imei=imei, sent_at__gte=window_start)
            .exclude(send_status='failed')
            .order_by('sent_at')
        ):
            if not pattern or pattern.search(row.command_sent or ''):
                command_row = row
                break

        if not command_row:
            return {
                'mode': test_case.source_table,
                'matched_count': 0,
                'required': 1,
                'pass': False,
                'reason': 'No reboot command found for this device within the test window.',
                'samples': [],
                'window_start': window_start.isoformat(),
                'refreshed_at': now.isoformat(),
            }

        command_sent_at = command_row.sent_at
        min_gap_seconds = test_case.max_interval_seconds or DEFAULT_REBOOT_GAP_SECONDS

        packets_after = list(
            GPSDataLog.objects
            .filter(timestamp__gt=command_sent_at, raw_data__contains=imei)
            .order_by('timestamp')
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        )

        if not packets_after:
            return {
                'mode': test_case.source_table,
                'matched_count': 0,
                'required': 1,
                'pass': False,
                'reason': (
                    f"Reboot command sent at {command_sent_at.isoformat()} -- device hasn't sent any "
                    f"packets since; it may still be rebooting or offline."
                ),
                'samples': [],
                'command_sent_at': command_sent_at.isoformat(),
                'window_start': window_start.isoformat(),
                'refreshed_at': now.isoformat(),
            }

        first_after_raw, first_after_time = packets_after[0]
        gap_seconds = (first_after_time - command_sent_at).total_seconds()
        result_pass = gap_seconds >= min_gap_seconds
        reason = None if result_pass else (
            f"Device kept sending packets with only a {gap_seconds:.0f}s gap after the reboot command "
            f"(need at least {min_gap_seconds}s of silence to prove an actual restart) -- it may not have rebooted."
        )
        return {
            'mode': test_case.source_table,
            'matched_count': 1 if result_pass else 0,
            'required': 1,
            'pass': result_pass,
            'reason': reason,
            'samples': [{'raw_data': first_after_raw, 'timestamp': first_after_time.isoformat()}],
            'command_sent_at': command_sent_at.isoformat(),
            'restart_gap_seconds': gap_seconds,
            'window_start': window_start.isoformat(),
            'refreshed_at': now.isoformat(),
        }

    if test_case.source_table == 'pvt_packet_drop':
        return _pvt_packet_drop_check(execution, imei, now)

    return {'mode': 'unknown', 'pass': False, 'reason': 'Unrecognised source_table.', 'refreshed_at': now.isoformat()}


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
        pvt_packets.append({
            'raw_data': raw_data,
            'time': effective_time,
            'valid_gps': gps_fix == '1' and _extract_pvt_lat_lon(raw_data) != (None, None),
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

    serializer = TechnicalOnboardingExecutionActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    execution = TechnicalOnboardingTestExecution.objects.select_related(
        'test_case', 'demo_device', 'onboarding_request'
    ).filter(id=serializer.validated_data['execution_id']).last()
    if not execution:
        return Response({'error': 'Invalid execution_id.'}, status=status.HTTP_400_BAD_REQUEST)

    _sweep_stale_executions(execution.onboarding_request)
    execution.refresh_from_db()

    if execution.status != 'in_progress':
        return Response(
            {'error': f'Test is {execution.status}, not in progress.', 'status': execution.status},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
