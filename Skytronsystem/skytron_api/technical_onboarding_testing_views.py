"""
Technical onboarding testing: courier tracking, per-IMEI stock receipt
confirmation, the backend-driven 39-checkpoint test catalog, and the
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
from datetime import timedelta

from django.db import transaction
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
)
from .views import validate_inputs, get_user_object, _packet_fields

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
}


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

    return {'mode': 'unknown', 'pass': False, 'reason': 'Unrecognised source_table.', 'refreshed_at': now.isoformat()}


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

    demo_device.receipt_confirmed = True
    demo_device.receipt_confirmed_at = timezone.now()
    demo_device.receipt_confirmed_by = request.user
    demo_device.save(update_fields=['receipt_confirmed', 'receipt_confirmed_at', 'receipt_confirmed_by'])

    if onboarding_request.status == 'submitted':
        all_received = not onboarding_request.demo_devices.filter(receipt_confirmed=False).exists()
        if all_received:
            onboarding_request.status = 'stock_received'
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
        if not data.get('manual_result'):
            return Response({'error': 'manual_result is required for this test.'}, status=status.HTTP_400_BAD_REQUEST)
        passed = data['manual_result'] == 'pass'
        execution.manual_result = data['manual_result']
        execution.manual_notes = data.get('manual_notes', '')
    else:
        if not execution.last_refreshed_at or execution.last_refreshed_at < execution.started_at:
            return Response({'error': 'Refresh the test log at least once before completing this test.'}, status=status.HTTP_400_BAD_REQUEST)
        auto_passed = bool((execution.test_log_snapshot or {}).get('pass'))
        if test_case.requires_manual_confirmation:
            # The automated check only proves a packet arrived -- it can't
            # judge an accuracy comparison, a field-by-field protocol read,
            # or an A-vs-B firmware check. Both have to pass. And the
            # confirmation can't come first: without the packet already in
            # GPSDataLog/GPSemDataLog there's nothing for the tester to be
            # confirming, so a "pass" attempted before the automated check
            # has found the data is rejected outright rather than silently
            # accepted and then failed by the AND below.
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
            if not data.get('manual_result'):
                return Response({'error': 'manual_result is required for this test.'}, status=status.HTTP_400_BAD_REQUEST)
            execution.manual_result = data['manual_result']
            execution.manual_notes = data.get('manual_notes', '')
            passed = auto_passed and data['manual_result'] == 'pass'
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
    DEV-ONLY -- force checkpoint `test_no` (1-39) to 'complete' for `imei`
    with a dummy snapshot, bypassing every real trigger/detection path.

    Exists so the rest of the pipeline (sequential gating, certificate
    issuance, dashboards) can be exercised end-to-end without physically
    operating a device through all 39 checkpoints. Blocked automatically
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
        return Response({'error': 'test_no must be an integer from 1 to 39.'}, status=status.HTTP_400_BAD_REQUEST)
    if not 1 <= test_no <= 39:
        return Response({'error': 'test_no must be an integer from 1 to 39.'}, status=status.HTTP_400_BAD_REQUEST)

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
