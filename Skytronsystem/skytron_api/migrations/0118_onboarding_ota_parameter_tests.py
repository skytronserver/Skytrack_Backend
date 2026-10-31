from django.db import migrations, models


# Technical onboarding, "OTA para (through SMS)" block of the test-plan sheet
# (2026-10-31): one test per device parameter, #42-#59 (shown to testers as
# #41-#58, since #23 is inactive). Each test sends the sheet's SET command
# and passes when the device's OT,12 packet echoes it with the sheet's reply,
# e.g. SETHBT-0.75 -> 'SET SUCCESSFULLY HBT-0.75'. The SET can come from the
# test board (MQTT) or by SMS to the device from the tester's phone, as in the
# sheet -- the check reads the OT packet either way. The GET command is the
# read-back and is shown, not required (the sheet gives no GET replies).
#
# Also from the sheet's command columns:
#   * #6 FOTA gets the @FOTA-<url>* command.
#   * #24 / #25 eSIM switch get @SETPROF-2* / @SETPROF-1* (sheet "Network switch").
#
# Sheet rows not added: "OTA Update" and "SMS FALL BACK" (no command or
# expected result in the sheet); "Emergency NM / SP / SEM" and "Network
# switch" are marked already live (#1-#2, #20, #5, #24-#25).

CATEGORY = 'OTA Parameters (SMS)'

DECIMAL = r'^\d+(\.\d+)?$'
INTEGER = r'^\d{1,6}$'
IPV4 = r'^\d{1,3}(\.\d{1,3}){3}$'


def _set_get(key, label, set_command, get_command, value_hint, value_regex):
    commands = [{'key': f'set_{key}', 'label': f'Set {label}', 'command': set_command,
                 'value_hint': value_hint, 'value_regex': value_regex}]
    if get_command:
        commands.append({'key': f'get_{key}', 'label': f'Read {label}', 'command': get_command})
    return commands


def _param_test(name, key, label, code, value_hint, value_regex, set_command=None, reply=True, extra_step=''):
    """A SET/GET parameter test whose reply is 'SET SUCCESSFULLY <code>-<value>'."""
    set_command = set_command or f'SET{code}-{{value}}'
    get_command = f'GET{code}'
    expected_reply = [f'SET SUCCESSFULLY {code}-{{value}}'] if reply else []
    reply_text = (f"'SET SUCCESSFULLY {code}-<value>'" if reply
                  else 'the command echoed back (the device sends an empty reply text)')
    return {
        'name': name,
        'description': f'Set {label} with @{set_command.replace("{value}", value_hint)}* and verify the device reply.',
        'procedure': (
            f'1. Press Start.\n'
            f'2. Optional: send @{get_command}* to read the current value.\n'
            f'3. Send @{set_command.replace("{value}", "<value>")}* (e.g. {value_hint}) from the test commands, '
            f'or by SMS to the device SIM.{extra_step}\n'
            f'4. Wait for the device reply (OT packet).\n'
            f'5. Optional: send @{get_command}* again to read the new value back.'
        ),
        'expected_result': f'OT,12 packet echoing the command, with reply {reply_text}.',
        'commands': _set_get(key, label, set_command, get_command, value_hint, value_regex),
        'check_config': {'command_key': f'set_{key}', 'expected_reply': expected_reply},
    }


NETWORK_WARNING = (
    '\n   Use the value the device must keep (read it first with GET): a wrong value disconnects the device '
    'from the server.'
)

NEW_TESTS = {
    42: _param_test('Vehicle Number (SMS)', 'reg_no', 'vehicle registration number', 'REGNO',
                    'AS01AA0002', r'^[A-Za-z0-9]{4,15}$'),
    43: {
        'name': 'Emergency State OFF (SMS)',
        'description': 'Turn the emergency state off with @SET SOSDIS-1* and verify the device stops SOS.',
        'procedure': (
            '1. Trigger SOS on the device, then press Start.\n'
            '2. Send @SET SOSDIS-1* from the test commands, or by SMS to the device SIM.\n'
            '3. Wait for the device reply and the SOS stop alert.'
        ),
        'expected_result': "OT,12 packet with reply 'SOS DISABLED', followed by the SOS stop alert (EA,11).",
        'commands': [{'key': 'sos_stop', 'label': 'SOS stop', 'command': 'SET SOSDIS-1'}],
        'check_config': {'command_key': 'sos_stop', 'expected_reply': ['SOS DISABLED'],
                         'after_packet': {'regex': ',EA,11,', 'label': 'SOS stop alert (EA,11)'}},
    },
    44: _param_test('Harsh Brake Threshold (SMS)', 'hbt', 'harsh-brake threshold', 'HBT', '0.75', DECIMAL),
    45: _param_test('Harsh Acceleration Threshold (SMS)', 'hat', 'harsh-acceleration threshold', 'HAT', '0.29', DECIMAL),
    46: _param_test('Rash Turning Threshold (SMS)', 'rtt', 'rash-turning threshold', 'RTT', '06', INTEGER),
    47: _param_test('Over Speed Threshold (SMS)', 'ott', 'over-speed threshold (km/h)', 'OTT', '80', INTEGER),
    48: _param_test('Data Update Rate in Ignition ON Mode (SMS)', 'urion', 'ignition-ON update rate (s)', 'URION',
                    '10', INTEGER),
    49: _param_test('Data Update Rate in Ignition OFF Mode (SMS)', 'urioff', 'ignition-OFF update rate (s)', 'URIOFF',
                    '10', INTEGER),
    50: _param_test('Automatic Emergency Cutoff Rate (SMS)', 'emcr', 'automatic emergency cutoff (s)', 'EMCR',
                    '180', INTEGER, reply=False),
    51: _param_test('Data Update Rate of Health Packets (SMS)', 'urhp', 'health packet rate (s)', 'URHP',
                    '36000', INTEGER),
    52: _param_test('Primary IP and Port (SMS)', 'ip1', 'primary IP and port', 'IP1',
                    '135.235.166.209,PORT1-8883,MODE1-0,PROTO1-0',
                    r'^\d{1,3}(\.\d{1,3}){3},PORT1-\d{1,5},MODE1-\d,PROTO1-\d$',
                    set_command='SET IP1-{value}', extra_step=NETWORK_WARNING),
    53: _param_test('Emergency IP (SMS)', 'eip', 'emergency server IP', 'EIP', '135.235.166.209', IPV4,
                    extra_step=NETWORK_WARNING),
    54: _param_test('Emergency SMS Center Number (SMS)', 'escn', 'emergency SMS centre number', 'ESCN',
                    '9211252018', r'^\+?\d{10,13}$'),
    55: _param_test('Primary APN (SMS)', 'apn', 'primary APN', 'APN', 'airtelgprs.com', r'^[A-Za-z0-9._-]{1,64}$',
                    extra_step=NETWORK_WARNING),
    56: {
        'name': 'Get Device Info (SMS)',
        'description': 'Read the device info with @GET INFO*.',
        'procedure': (
            '1. Press Start.\n'
            '2. Send @GET INFO* from the test commands, or by SMS to the device SIM.\n'
            '3. Wait for the device reply (OT packet).'
        ),
        'expected_result': ('OT,12 packet with reply IMEI-<imei>, VID-<vendor>, VRN-<vehicle no.>, NETWORK-<operator>, '
                            'VERSION-<firmware>.'),
        'commands': [{'key': 'get_info', 'label': 'Get device info', 'command': 'GET INFO'}],
        'check_config': {'command_key': 'get_info',
                         'expected_reply': ['IMEI-{imei}', 'VID-', 'VRN-', 'NETWORK-', 'VERSION-']},
    },
    57: {
        'name': 'Get Device Location (SMS)',
        'description': 'Read the device location with @GETLOC*.',
        'procedure': (
            '1. Press Start.\n'
            '2. Send @GETLOC* from the test commands, or by SMS to the device SIM.\n'
            '3. Wait for the device reply (OT packet).'
        ),
        'expected_result': 'OT,12 packet with reply GPS: Lt-<latitude>, N, Ln-<longitude>, E.',
        'commands': [{'key': 'get_loc', 'label': 'Get device location', 'command': 'GETLOC'}],
        'check_config': {'command_key': 'get_loc', 'expected_reply': ['GPS:', 'LT-', 'LN-']},
    },
    58: {
        'name': 'Reset Device (SMS)',
        'description': 'Reset the device with @DEVRESET*.',
        'procedure': (
            '1. Press Start.\n'
            '2. Send @DEVRESET* from the test commands, or by SMS to the device SIM.\n'
            '3. Wait for the device to restart and log in again.'
        ),
        'expected_result': ('Device restarts and sends a login packet after the command. A reply '
                            "'DEV RESET SEQUENCE BUSY (OT PENDING)' means it did not reset -- send it again."),
        'commands': [{'key': 'dev_reset', 'label': 'Reset device', 'command': 'DEVRESET'}],
        'check_config': {'command_key': 'dev_reset', 'expected_reply': [], 'reply_required': False,
                         'after_packet': {'kind': 'login', 'label': 'login packet (device restarted)'}},
    },
    59: {
        'name': 'Health Packet Log on SMS Request',
        'description': 'Request a health packet with @SET SENDHCHK-1*.',
        'procedure': (
            '1. Press Start.\n'
            '2. Send @SET SENDHCHK-1* from the test commands, or by SMS to the device SIM.\n'
            '3. Wait for the device reply (OT packet).'
        ),
        # The device answers with the health log in the reply itself, e.g. 'HCHK,000000,7635975659'.
        'expected_result': "OT,12 packet with the health log in the reply: 'HCHK,<status>,<number>'.",
        'commands': [{'key': 'send_health', 'label': 'Request health packet', 'command': 'SET SENDHCHK-1'}],
        'check_config': {'command_key': 'send_health', 'expected_reply': ['HCHK']},
    },
}

COMMON = {
    'category': CATEGORY,
    'test_environment': 'Indoor',
    'source_table': 'command_reply',
    'regex_pattern': None,
    'min_match_count': 1,
    'max_interval_seconds': None,
    'scan_window_seconds': 300,
    'requires_manual_confirmation': False,
    'requires_command': True,
    'requires_map': False,
    'requires_physical_test': False,
    'is_optional': False,
    'active': True,
}

# Commands from the sheet for tests that already exist.
EXISTING_COMMANDS = {
    6: [{'key': 'fota', 'label': 'FOTA upgrade', 'command': 'FOTA-{value}',
         'value_hint': 'https://135.235.166.209/SKTN/1.0.8_23.pac', 'value_regex': r'^https?://\S+$'}],
    24: [{'key': 'set_profile_2', 'label': 'Switch to secondary profile', 'command': 'SETPROF-2'}],
    25: [{'key': 'set_profile_1', 'label': 'Switch to primary profile', 'command': 'SETPROF-1'}],
}


def apply(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for serial_no, values in NEW_TESTS.items():
        TestCase.objects.update_or_create(serial_no=serial_no, defaults={**COMMON, **values})
    for serial_no, commands in EXISTING_COMMANDS.items():
        test_case = TestCase.objects.filter(serial_no=serial_no).first()
        if not test_case:
            continue
        keys = {c['key'] for c in commands}
        test_case.commands = [c for c in (test_case.commands or []) if c.get('key') not in keys] + commands
        test_case.requires_command = True
        test_case.save(update_fields=['commands', 'requires_command'])


def revert(apps, schema_editor):
    # Deactivate rather than delete, so executions already run are kept.
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    TestCase.objects.filter(serial_no__in=NEW_TESTS).update(active=False)
    for serial_no, commands in EXISTING_COMMANDS.items():
        test_case = TestCase.objects.filter(serial_no=serial_no).first()
        if not test_case:
            continue
        keys = {c['key'] for c in commands}
        test_case.commands = [c for c in (test_case.commands or []) if c.get('key') not in keys]
        test_case.save(update_fields=['commands'])


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
    ('manual', 'Manual / Observed'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0117_onboarding_time_bound_tests'),
    ]

    operations = [
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(choices=SOURCE_CHOICES, default='manual', max_length=30),
        ),
        migrations.RunPython(apply, revert),
    ]
