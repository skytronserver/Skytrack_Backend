from django.db import migrations, models


# Catalog changes:
#   * #9 "Ignition ON/OFF status" is split into #9 "Ignition ON status" and a
#     new #10 "Ignition OFF status"; every test from the old #10 onward
#     shifts down by one serial_no (old #10-39 -> #11-40).
#   * Renames: "SOS button" -> "Physical SOS button", "BLE SOS" -> "App SOS",
#     "Rough-turning" -> "Rush-turning".
#   * New #41 "PVT packet drop test" (source_table='pvt_packet_drop').
#
# Only name/description/serial_no are touched on existing rows -- their
# source_table/regex/thresholds were tuned live through the catalog API and
# are left as they are. The new #10 copies #9's live check settings.

SPLIT_SERIAL_NO = 9
PVT_DROP_SERIAL_NO = 41

IGNITION_COMBINED_NAME = "Ignition ON/OFF status"
IGNITION_COMBINED_DESCRIPTION = "Verify the ignition switch ON and OFF status."
IGNITION_ON_NAME = "Ignition ON status"
IGNITION_ON_DESCRIPTION = "Verify the ignition switch ON status."
IGNITION_OFF_NAME = "Ignition OFF status"
IGNITION_OFF_DESCRIPTION = "Verify the ignition switch OFF status."

CARRIED_OVER_NOTE = (
    "Carried over from the combined 'Ignition ON/OFF status' checkpoint, "
    "which already covered the OFF state."
)

# Name renames only apply when the name starts with the old text; description
# renames apply anywhere in the text.
NAME_RENAMES = [
    ("SOS button", "Physical SOS button"),
    ("BLE SOS", "App SOS"),
    ("Rough-turning", "Rush-turning"),
]
DESCRIPTION_RENAMES = [
    ("rough-turning", "rush-turning"),
]

PVT_DROP_TEST = dict(
    serial_no=PVT_DROP_SERIAL_NO,
    name="PVT packet drop test",
    description=(
        "Verify that no PVT (tracking) packets are dropped: over the test window the device must keep "
        "reporting PVT packets with no gap between consecutive packets (by device timestamp) longer "
        "than the allowed interval. Buffered history (H) packets that fill a gap count as delivered."
    ),
    source_table='pvt_packet_drop',
    regex_pattern=None,
    min_match_count=8,            # ~10 min at the fleet's 60s idle cadence
    max_interval_seconds=75,      # 60s cadence + 15s tolerance; tune per model via the catalog API
    scan_window_seconds=600,
    requires_manual_confirmation=False,
    is_optional=False,
    active=True,
)


def _rename_prefix(text, pairs):
    for old, new in pairs:
        if text.startswith(old):
            return new + text[len(old):]
    return text


def _rename_anywhere(text, pairs):
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def apply_changes(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    Execution = apps.get_model('skytron_api', 'TechnicalOnboardingTestExecution')

    ignition = TestCase.objects.filter(serial_no=SPLIT_SERIAL_NO).first()

    # Shift old #10+ down by one, highest first so the unique serial_no
    # constraint never sees a collision mid-way.
    for test_case in TestCase.objects.filter(serial_no__gt=SPLIT_SERIAL_NO).order_by('-serial_no'):
        test_case.serial_no += 1
        test_case.save(update_fields=['serial_no'])

    if ignition:
        ignition.name = IGNITION_ON_NAME
        ignition.description = IGNITION_ON_DESCRIPTION
        ignition.save(update_fields=['name', 'description'])

        ignition_off = TestCase.objects.create(
            serial_no=SPLIT_SERIAL_NO + 1,
            name=IGNITION_OFF_NAME,
            description=IGNITION_OFF_DESCRIPTION,
            source_table=ignition.source_table,
            regex_pattern=ignition.regex_pattern,
            min_match_count=ignition.min_match_count,
            max_interval_seconds=ignition.max_interval_seconds,
            scan_window_seconds=ignition.scan_window_seconds,
            requires_manual_confirmation=ignition.requires_manual_confirmation,
            is_optional=ignition.is_optional,
            active=ignition.active,
        )

        # A completed combined ON/OFF run already proved the OFF state, so
        # carry it over -- otherwise every in-progress evaluation would be
        # gated back to the new #10.
        Execution.objects.bulk_create([
            Execution(
                onboarding_request_id=e.onboarding_request_id,
                demo_device_id=e.demo_device_id,
                test_case=ignition_off,
                status='complete',
                attempt_number=e.attempt_number,
                started_at=e.started_at,
                started_by_id=e.started_by_id,
                last_heartbeat_at=e.last_heartbeat_at,
                completed_at=e.completed_at,
                completed_by_id=e.completed_by_id,
                test_log_snapshot=e.test_log_snapshot,
                last_refreshed_at=e.last_refreshed_at,
                manual_result=e.manual_result,
                manual_notes=((e.manual_notes + "\n") if e.manual_notes else "") + CARRIED_OVER_NOTE,
            )
            for e in Execution.objects.filter(test_case=ignition, status='complete')
        ], ignore_conflicts=True)

    for test_case in TestCase.objects.all():
        new_name = _rename_prefix(test_case.name, NAME_RENAMES)
        new_description = _rename_anywhere(test_case.description, DESCRIPTION_RENAMES)
        if new_name != test_case.name or new_description != test_case.description:
            test_case.name = new_name
            test_case.description = new_description
            test_case.save(update_fields=['name', 'description'])

    if not TestCase.objects.filter(serial_no=PVT_DROP_SERIAL_NO).exists():
        TestCase.objects.create(**PVT_DROP_TEST)


def revert_changes(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')

    TestCase.objects.filter(serial_no=PVT_DROP_SERIAL_NO, source_table='pvt_packet_drop').delete()
    TestCase.objects.filter(serial_no=SPLIT_SERIAL_NO + 1, name=IGNITION_OFF_NAME).delete()

    for test_case in TestCase.objects.filter(serial_no__gt=SPLIT_SERIAL_NO + 1).order_by('serial_no'):
        test_case.serial_no -= 1
        test_case.save(update_fields=['serial_no'])

    TestCase.objects.filter(serial_no=SPLIT_SERIAL_NO, name=IGNITION_ON_NAME).update(
        name=IGNITION_COMBINED_NAME, description=IGNITION_COMBINED_DESCRIPTION,
    )

    reverse_names = [(new, old) for old, new in NAME_RENAMES]
    reverse_descriptions = [(new, old) for old, new in DESCRIPTION_RENAMES]
    for test_case in TestCase.objects.all():
        old_name = _rename_prefix(test_case.name, reverse_names)
        old_description = _rename_anywhere(test_case.description, reverse_descriptions)
        if old_name != test_case.name or old_description != test_case.description:
            test_case.name = old_name
            test_case.description = old_description
            test_case.save(update_fields=['name', 'description'])


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0098_device_model_reject'),
    ]

    operations = [
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(
                choices=[
                    ('gps', 'GPS Raw Log (GPSDataLog)'),
                    ('gpsem', 'Emergency Raw Log (GPSemDataLog)'),
                    ('ota_command', 'OTA Command History'),
                    ('activation_command', 'Activation Command'),
                    ('firmware_diff', 'Firmware Version Change (GPSDataLog)'),
                    ('voltage_internal', 'Internal Battery Voltage -- 3 Distinct Levels (GPSDataLog)'),
                    ('voltage_external', 'External/Main Voltage -- 3 Distinct Levels (GPSDataLog)'),
                    ('esim_primary_to_secondary', 'eSIM Switch Primary->Secondary -- 2 Distinct Networks (GPSDataLog)'),
                    ('esim_secondary_to_primary', 'eSIM Switch Secondary->Primary -- 2 Distinct Networks, Reversed (GPSDataLog)'),
                    ('vehicle_registration_diff', 'Vehicle Registration Number Changed (GPSDataLog)'),
                    ('reboot_restart_gap', 'Reboot Command -- Connectivity Gap Proves Restart (GPSDataLog)'),
                    ('pvt_packet_drop', 'PVT Packet Drop -- No Gap Above Allowed Interval (GPSDataLog)'),
                    ('manual', 'Manual / Observed'),
                ],
                default='manual',
                max_length=30,
            ),
        ),
        migrations.RunPython(apply_changes, revert_changes),
    ]
