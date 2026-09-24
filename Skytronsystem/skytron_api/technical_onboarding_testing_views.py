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

import re
import statistics
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
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
)
from .views import (
    validate_inputs,
    get_user_object,
    _packet_fields,
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
    'pvt_packet_drop': 'GPSDataLog',
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

# Default max allowed gap between consecutive PVT packets for the packet
# drop test, used when the test case doesn't set max_interval_seconds.
DEFAULT_PVT_DROP_MAX_GAP_SECONDS = 75

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


def _current_unlocked_serial_no(onboarding_request):
    """
    Lowest serial_no among active, non-optional test cases where not all
    5 demo devices are complete. None means everything gate-worthy is done.
    """
    device_count = onboarding_request.demo_devices.count()
    test_cases = TechnicalOnboardingTestCase.objects.filter(active=True, is_optional=False).order_by('serial_no')
    for test_case in test_cases:
        complete_count = TechnicalOnboardingTestExecution.objects.filter(
            onboarding_request=onboarding_request,
            test_case=test_case,
            status='complete',
        ).count()
        if complete_count < device_count:
            return test_case.serial_no
    return None


def _all_tests_complete(onboarding_request):
    device_count = onboarding_request.demo_devices.count()
    if device_count == 0:
        return False
    for test_case in TechnicalOnboardingTestCase.objects.filter(active=True, is_optional=False):
        complete_count = TechnicalOnboardingTestExecution.objects.filter(
            onboarding_request=onboarding_request,
            test_case=test_case,
            status='complete',
        ).count()
        if complete_count < device_count:
            return False
    return True


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
        # Gaps are measured on the device's own timestamp (when plausible)
        # so buffered history (H) packets that arrive late still close the
        # gap they cover -- only data that never reached the server counts
        # as dropped.
        rows = list(
            GPSDataLog.objects
            .filter(timestamp__gte=window_start, raw_data__contains=imei)
            .order_by('-timestamp')
            .values_list('raw_data', 'timestamp')[:GPS_PACKET_SCAN_LIMIT]
        )
        packet_times = []
        for raw_data, packet_time in rows:
            if _pvt_index(_packet_fields(raw_data)) is None:
                continue
            effective_time, _time_source = _packet_time(raw_data, packet_time)
            if effective_time >= window_start:
                packet_times.append(effective_time)

        max_gap_allowed = test_case.max_interval_seconds or DEFAULT_PVT_DROP_MAX_GAP_SECONDS
        stats = _gap_stats(packet_times)
        matched_count = stats['packet_count']

        # Silence before the first packet or since the last one is a drop
        # too -- a device that goes quiet mid-test must not pass.
        gaps = list(stats['gaps'])
        if packet_times:
            first, last = min(packet_times), max(packet_times)
            gaps.append({'seconds': (first - window_start).total_seconds(), 'from': window_start.isoformat(), 'to': first.isoformat()})
            gaps.append({'seconds': (now - last).total_seconds(), 'from': last.isoformat(), 'to': now.isoformat()})
        over_limit = sorted((g for g in gaps if g['seconds'] > max_gap_allowed), key=lambda g: g['from'])

        result_pass = matched_count >= test_case.min_match_count and not over_limit
        if matched_count < test_case.min_match_count:
            reason = f"Only {matched_count} PVT packet(s) found, need at least {test_case.min_match_count}."
        elif over_limit:
            longest = max(over_limit, key=lambda g: g['seconds'])
            reason = (
                f"{len(over_limit)} gap(s) above the allowed {max_gap_allowed}s between PVT packets -- "
                f"longest {longest['seconds']:.0f}s from {longest['from']} to {longest['to']}."
            )
        else:
            reason = None

        return {
            'mode': test_case.source_table,
            'matched_count': matched_count,
            'required': test_case.min_match_count,
            'pass': result_pass,
            'reason': reason,
            'samples': over_limit[:5],
            'max_gap_allowed_seconds': max_gap_allowed,
            'drop_count': len(over_limit),
            'gap_stats': {k: v for k, v in stats.items() if k != 'gaps'},
            'window_start': window_start.isoformat(),
            'refreshed_at': now.isoformat(),
        }

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
    test_cases = TechnicalOnboardingTestCase.objects.filter(active=True).order_by('serial_no')
    demo_devices = list(onboarding_request.demo_devices.all().order_by('id'))

    existing = {
        (e.demo_device_id, e.test_case_id): e
        for e in TechnicalOnboardingTestExecution.objects.filter(onboarding_request=onboarding_request)
        .select_related('test_case', 'demo_device')
    }

    to_create = []
    for test_case in test_cases:
        for demo_device in demo_devices:
            if (demo_device.id, test_case.id) not in existing:
                to_create.append(TechnicalOnboardingTestExecution(
                    onboarding_request=onboarding_request, demo_device=demo_device, test_case=test_case,
                ))
    if to_create:
        TechnicalOnboardingTestExecution.objects.bulk_create(to_create, ignore_conflicts=True)
        existing = {
            (e.demo_device_id, e.test_case_id): e
            for e in TechnicalOnboardingTestExecution.objects.filter(onboarding_request=onboarding_request)
            .select_related('test_case', 'demo_device')
        }

    rows = []
    for test_case in test_cases:
        executions = [existing[(d.id, test_case.id)] for d in demo_devices if (d.id, test_case.id) in existing]
        rows.append({
            'test_case': TechnicalOnboardingTestCaseSerializer(test_case).data,
            'executions': TechnicalOnboardingTestExecutionSerializer(executions, many=True).data,
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
