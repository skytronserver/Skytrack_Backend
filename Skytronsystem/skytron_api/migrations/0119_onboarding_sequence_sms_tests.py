from django.db import migrations, models


# Technical onboarding (2026-10-31):
#   * New `sequence`: the order tests run in and the number testers see.
#     Indoor tests first (OT / SMS command tests included), then the outdoor
#     (road) tests, each group in serial_no order; 1..N over active tests.
#     serial_no stays the fixed identity, so old executions and code that
#     refers to a test by serial_no are unaffected.
#   * #41 Activation: the device's ACTVR reply must come in through the SMS
#     receive mechanism (AirtelSmsInLog / SmppSmsIn) -- mode activation_sms.
#   * #60 SMS fallback (new): with no data connection the device's alert SMS
#     must come in through the same mechanism -- mode sms_fallback.
#   * Dummy executions on removed tests (#23: never started, or force-passed
#     through the DEV bypass) are deleted; real attempts are kept.
# {sms_number} in command templates is filled at send time with
# ONBOARDING_SMS_RECEIVE_NUMBER (technical_onboarding_testing_views).

ACTIVATION_SERIAL = 41
SMS_FALLBACK_SERIAL = 60

ACTIVATION = {
    'source_table': 'activation_sms',
    'regex_pattern': None,
    'min_match_count': 1,
    'requires_command': True,
    'requires_manual_confirmation': False,
    'procedure': (
        '1. Make sure our SMS number is whitelisted on the device.\n'
        '2. Press Start, then send "Activation command" from the test commands. It goes by SMS with a random '
        '6-digit key and our SMS number as the reply-to number.\n'
        '3. Wait for the device\'s activation reply (ACTVR), received through the SMS gateway.'
    ),
    'expected_result': (
        'The device replies by SMS with ACTVR,<the same key>,...,<its IMEI>,..., received through the SMS '
        'gateway.'
    ),
    'commands': [{
        'key': 'activation', 'label': 'Activation command',
        'command': 'ACTV,{value},{sms_number}',
        'value_hint': 'Leave blank for a random 6-digit key', 'value_regex': r'^\d{6}$',
        'auto_value': 'random6', 'frame': False, 'channel': 'sms',
    }],
    'check_config': {'command_key': 'activation'},
}

SMS_FALLBACK = {
    'name': 'SMS fallback (no data connection)',
    'description': 'With no data connection the device sends its emergency alert by SMS.',
    'category': 'SMS',
    'test_environment': 'Indoor',
    'source_table': 'sms_fallback',
    'regex_pattern': None,
    'min_match_count': 1,
    'max_interval_seconds': None,
    'scan_window_seconds': 600,
    'requires_manual_confirmation': False,
    'requires_command': True,
    'requires_map': False,
    'requires_physical_test': True,
    'is_optional': False,
    'active': True,
    'procedure': (
        '1. Press Start, then send "Set emergency SMS number" so the device\'s emergency SMS go to our SMS number.\n'
        '2. Cut the device\'s data connection but keep the GSM network (e.g. block data for the SIM on the M2M '
        'portal), so it cannot reach the servers.\n'
        '3. Press the SOS button.\n'
        '4. Wait for the device\'s emergency SMS, received through the SMS gateway.\n'
        '5. Restore the data connection and stop SOS.'
    ),
    'expected_result': (
        'The device sends the alert by SMS to the emergency SMS centre number, and the SMS is received through '
        'the SMS gateway (from the device\'s SIM number or carrying its IMEI).'
    ),
    'commands': [
        {'key': 'set_escn', 'label': 'Set emergency SMS number', 'command': 'SETESCN-{sms_number}'},
        {'key': 'sos_stop', 'label': 'SOS stop', 'command': 'SET SOSDIS-1'},
    ],
    'check_config': {},
}


def _assign_sequence(TestCase):
    TestCase.objects.update(sequence=None)
    active = list(TestCase.objects.filter(active=True).order_by('serial_no'))
    indoor = [t for t in active if not (t.test_environment or '').lower().startswith('outdoor')]
    outdoor = [t for t in active if (t.test_environment or '').lower().startswith('outdoor')]
    for number, test_case in enumerate(indoor + outdoor, 1):
        test_case.sequence = number
        test_case.save(update_fields=['sequence'])


def apply(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    Execution = apps.get_model('skytron_api', 'TechnicalOnboardingTestExecution')

    TestCase.objects.filter(serial_no=ACTIVATION_SERIAL).update(**ACTIVATION)
    TestCase.objects.update_or_create(serial_no=SMS_FALLBACK_SERIAL, defaults=SMS_FALLBACK)

    removed = Execution.objects.filter(test_case__active=False)
    removed.filter(status='not_started').delete()
    removed.filter(test_log_snapshot__mode='dev_bypass').delete()

    _assign_sequence(TestCase)


def revert(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    TestCase.objects.filter(serial_no=SMS_FALLBACK_SERIAL).update(active=False)
    TestCase.objects.filter(serial_no=ACTIVATION_SERIAL).update(
        source_table='activation_command', commands=[], check_config={})


SOURCE_CHOICES = [
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
    ('pvt_packet_drop', 'PVT + Emergency Packet Drop -- 15 min Fixed Window, 4-6s Average Gap (GPSDataLog + GPSemDataLog)'),
    ('packet_sequence', 'Trigger Packet + Before/After State Packets (GPSDataLog)'),
    ('sos_stop_both', 'SOS Stop on Tracking (EA,11) + Emergency (SEM) Servers'),
    ('protocol_packet', 'Protocol Field Validation of a Packet Type (GPSDataLog / GPSemDataLog)'),
    ('speed_accuracy', 'Constant-Speed Stretches at Target Speeds (GPSDataLog)'),
    ('geofence_crossing', 'Geofence Entry/Exit Distance (GPSDataLog)'),
    ('history_coverage', 'History (H) Packets Covering the No-Network Period (GPSDataLog)'),
    ('unique_cell_towers', 'Unique Cell Towers Seen (GPSDataLog)'),
    ('command_reply', 'Command Echo + Expected Reply in an OT,12 Packet (GPSDataLog)'),
    ('activation_sms', 'Activation Reply (ACTVR) Received by SMS (AirtelSmsInLog / SmppSmsIn)'),
    ('sms_fallback', 'Fallback SMS from the Device Received by SMS (AirtelSmsInLog / SmppSmsIn)'),
    ('manual', 'Manual / Observed'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0118_onboarding_ota_parameter_tests'),
    ]

    operations = [
        migrations.AddField(
            model_name='technicalonboardingtestcase',
            name='sequence',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='technicalonboardingtestcase',
            options={'ordering': ['sequence', 'serial_no']},
        ),
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(choices=SOURCE_CHOICES, default='manual', max_length=30),
        ),
        migrations.RunPython(apply, revert),
    ]
