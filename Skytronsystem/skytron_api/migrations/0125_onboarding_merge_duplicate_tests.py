from django.db import migrations, models


# Merge duplicate technical onboarding tests (2026-11-06). Every check of a
# retired test still runs: either the test it merges into already checks
# exactly the same thing, or the check moves into it unchanged (as a part of
# a 'composite' test, or as an after-command packet check).
#
#   Physical SOS (#1)  <- #1 EMR burst on the emergency server, #3 EA,10 + NR
#                         SOS=1 on tracking, #28 EA,10 protocol fields, #43 SOS
#                         stop reply over MQTT, #5 stop on both servers, #31
#                         EA,11 protocol fields. SOS from the physical button,
#                         stopped by an MQTT command.
#   App SOS (#2)       <- #2, #4, #29 (app/BLE versions), #43 over SMS (reply
#                         SMS too), #5, #31. SOS from the app, stopped by SMS.
#   #9 / #10 ignition  <- #36 / #37: the same IN,07 / IF,08 alert is #9 / #10's
#                         trigger packet, so #36 / #37 are retired.
#   #17 power cut      <- #32: the same BD,03 alert is #17's trigger.
#   #42 vehicle number <- #39: per channel, an NR packet must carry the new
#                         number after the SET command (the OT ack is #42's
#                         reply check).
#   #58 device reset   <- #38: per channel, login -> health -> NR after
#                         DEVRESET; #26 / #27: login (with a valid location) and
#                         health packet protocol fields.

RETIRED = [3, 4, 5, 26, 27, 28, 29, 31, 32, 36, 37, 38, 39, 43]
PART_DROP_KEYS = ('time_limit_seconds', 'task_seconds')


def _part(t, key, label):
    """One composite part copied from test t, its check settings unchanged."""
    return {
        'key': key,
        'label': label,
        'from_test': t.serial_no,
        'source_table': t.source_table,
        'check_config': {k: v for k, v in (t.check_config or {}).items() if k not in PART_DROP_KEYS},
        'regex_pattern': t.regex_pattern,
        'min_match_count': t.min_match_count,
        'max_interval_seconds': t.max_interval_seconds,
    }


def _flags(target, sources):
    for flag in ('requires_command', 'requires_manual_confirmation', 'requires_map', 'requires_physical_test'):
        setattr(target, flag, any(getattr(t, flag) for t in sources))


def _sos_test(t, start_tests, t43, t5, t31, channel, who):
    emr, tracking, protocol = start_tests
    stop_cmd = dict(next(c for c in (t43.commands or []) if c.get('key') == 'sos_stop'))
    stop_cmd['channel'] = channel
    ch = channel.upper()
    stop_cfg = {k: v for k, v in (t43.check_config or {}).items() if k not in PART_DROP_KEYS}
    stop_cfg.update({'channels': [channel], 'required_commands': ['sos_stop']})
    by_sms = channel == 'sms'
    parts = [
        _part(emr, 'emergency_burst', f'Emergency server: {emr.min_match_count} EMR packets at a 5 s cadence'),
        _part(tracking, 'tracking_start', 'Tracking server: SOS start alert (EA,10), then NR packets with SOS = 1'),
        _part(protocol, 'start_protocol', 'SOS start packet (EA,10): protocol fields'),
        {**_part(t43, 'stop_command', f"SOS stop by {ch}: reply 'SOS DISABLED' + EA,11"
                 + (' + reply SMS' if by_sms else '')), 'check_config': stop_cfg},
        _part(t5, 'stop_both_servers', 'SOS stopped on both servers: EA,11 + EPB SEM, NR back to SOS = 0'),
        _part(t31, 'stop_protocol', 'SOS stop packet (EA,11): protocol fields'),
    ]
    t.source_table = 'composite'
    t.category = 'SOS'
    t.regex_pattern = None
    t.min_match_count = 1
    t.max_interval_seconds = None
    t.commands = [stop_cmd]
    t.check_config = {'parts': parts, 'time_limit_seconds': (20 if by_sms else 15) * 60}
    _flags(t, [t, *start_tests, t43, t5, t31])
    t.requires_command = True
    t.name = f'{who} SOS: start on both servers + stop by {ch} command'
    t.description = (f'SOS from the {who.lower()} reaches the emergency and tracking servers, and stops on both '
                     f'with the SOS stop command sent by {ch}; the start and stop packets match the protocol.')
    trigger = 'Press the physical SOS button on the device' if who == 'Physical' else 'Trigger SOS from the mobile app'
    t.procedure = (
        '1. Confirm the device is connected to both servers, then press Start.\n'
        f'2. {trigger}. Wait about one minute: the emergency server must get {emr.min_match_count} EMR packets at a '
        '5-second cadence, and the tracking server the SOS start alert (EA,10) followed by NR packets with SOS = 1.\n'
        f'3. Send "SOS stop" (@SET SOSDIS-1*) by {ch}'
        + (' (choose "Send via SMS")' if by_sms else '') + '. The device replies \'SOS DISABLED\''
        + (' (also by SMS to our number)' if by_sms else '') + ', SOS stops on both servers (EA,11 on tracking, '
        'EPB SEM on emergency) and NR packets return to SOS = 0.\n'
        '4. The SOS start (EA,10) and stop (EA,11) packets are also checked field by field against the protocol.'
    )
    t.expected_result = (
        f'{emr.min_match_count} EMR packets at a 5 s cadence on the emergency server; EA,10 + NR packets with SOS = 1 '
        f"on the tracking server; reply 'SOS DISABLED' to the {ch} stop command"
        + (' (OT,12 source SMS and the reply SMS)' if by_sms else ' (OT,12 source SERVER)')
        + '; EA,11 on tracking and EPB SEM on emergency, NR back to SOS = 0; EA,10 and EA,11 valid against the protocol.'
    )


def _renumber(TestCase):
    """Run order 1..N over the active tests, keeping their current order; inactive tests get none."""
    TestCase.objects.filter(active=False).update(sequence=None)
    active = sorted(TestCase.objects.filter(active=True),
                    key=lambda t: (t.sequence if t.sequence is not None else 10 ** 6, t.serial_no))
    for number, test_case in enumerate(active, 1):
        if test_case.sequence != number:
            test_case.sequence = number
            test_case.save(update_fields=['sequence'])


def forwards(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    t = {x.serial_no: x for x in TestCase.objects.filter(
        serial_no__in=[1, 2, 3, 4, 5, 9, 10, 17, 26, 27, 28, 29, 31, 32, 36, 37, 38, 39, 42, 43, 58])}
    if len(t) < 21:
        return  # catalog not loaded (fresh DB without the test plan)

    _sos_test(t[1], (t[1], t[3], t[28]), t[43], t[5], t[31], 'mqtt', 'Physical')
    # _part(t[1]) above read #1's own settings before they were replaced.
    _sos_test(t[2], (t[2], t[4], t[29]), t[43], t[5], t[31], 'sms', 'App')

    # #9 / #10 / #17 already check #36 / #37 / #32's alert as their trigger.
    for target, retired, alert in ((9, 36, 'Ignition ON alert (IN,07)'), (10, 37, 'Ignition OFF alert (IF,08)'),
                                   (17, 32, 'Main Battery Disconnected alert (BD,03)')):
        x = t[target]
        _flags(x, [x, t[retired]])
        note = f' The {alert} packet is the trigger checked here (it was also test #{retired}).'
        if note.strip() not in (x.expected_result or ''):
            x.expected_result = (x.expected_result or '').rstrip() + note

    # #42 <- #39: the NR packets must carry the new number, per channel.
    x = t[42]
    cfg = dict(x.check_config or {})
    cfg['after_packet'] = {'packet_type': 'NR', 'field': 'vehicle_reg_no', 'equals': '{value}',
                           'label': 'NR packet carrying the new registration number'}
    x.check_config = cfg
    _flags(x, [x, t[39]])
    x.name = 'Vehicle Number (MQTT + SMS) + NR packet shows it'
    x.procedure = (x.procedure or '').rstrip() + (
        '\nAfter each SET, wait for an NR packet: it must carry the number just set (on each channel).')
    x.expected_result = (x.expected_result or '').rstrip() + (
        ' After the SET on each channel, an NR packet carries the new registration number.')

    # #58 <- #38 (login -> health -> NR per channel), #26 / #27 (protocol).
    x = t[58]
    reset_cfg = {k: v for k, v in (x.check_config or {}).items() if k not in PART_DROP_KEYS}
    reset_cfg['after_packet'] = {
        'sequence': [{'kind': 'login', 'label': 'login packet'},
                     {'kind': 'health', 'label': 'health packet'},
                     {'kind': 'tracking', 'packet_type': 'NR', 'label': 'NR packet'}],
        'label': 'login -> health -> NR packets (device restarted)',
        'missing_hint': 'A missing login packet means the device did not actually restart.',
    }
    reset_part = {**_part(x, 'reset', 'DEVRESET on each channel: restart, then login -> health -> NR packets'),
                  'check_config': reset_cfg}
    parts = [
        reset_part,
        _part(t[26], 'login_protocol', 'Login packet: protocol fields + valid location'),
        _part(t[27], 'health_protocol', 'Health packet: protocol fields'),
    ]
    _flags(x, [x, t[38], t[26], t[27]])
    x.source_table = 'composite'
    x.check_config = {'parts': parts, 'time_limit_seconds': (x.check_config or {}).get('time_limit_seconds') or 20 * 60}
    x.name = 'Reset Device (MQTT + SMS) + login / health packet protocol'
    x.description = ('Reset the device with @DEVRESET* over MQTT and by SMS; after each reset it logs in again '
                     '(login -> health -> NR), and the login and health packets match the protocol.')
    x.procedure = (
        '1. Press Start.\n'
        '2. Over MQTT: send @DEVRESET* and wait for the device to restart: login packet, then health packet, then NR.\n'
        '3. By SMS: send @DEVRESET* again ("Send via SMS") and wait for the same login -> health -> NR packets.\n'
        '4. The login packet (with a valid location) and the health packet are checked field by field against '
        'the protocol.'
    )
    x.expected_result = (
        "Reply 'DEV RESET SEQUENCE STARTED', then login -> health -> NR packets after each of the two commands; "
        "the login packet (valid location) and health packet match the protocol. 'DEV RESET SEQUENCE BUSY "
        "(OT PENDING)' means it did not reset -- send it again."
    )

    for serial in RETIRED:
        t[serial].active = False
    for x in t.values():
        x.save()
    _renumber(TestCase)


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0124_sms_onboarding_tagging'),
    ]

    operations = [
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(choices=[('gps', 'GPS Raw Log (GPSDataLog)'), ('gpsem', 'Emergency Raw Log (GPSemDataLog)'), ('ota_command', 'OTA Command History'), ('activation_command', 'Activation Command'), ('firmware_diff', 'Firmware Version Change (GPSDataLog)'), ('voltage_internal', 'Internal Battery Voltage -- 3 Distinct Levels (GPSDataLog)'), ('voltage_external', 'External/Main Voltage -- 3 Distinct Levels (GPSDataLog)'), ('esim_primary_to_secondary', 'eSIM Switch Primary->Secondary -- 2 Distinct Networks (GPSDataLog)'), ('esim_secondary_to_primary', 'eSIM Switch Secondary->Primary -- 2 Distinct Networks, Reversed (GPSDataLog)'), ('vehicle_registration_diff', 'Vehicle Registration Number Changed (GPSDataLog)'), ('reboot_restart_gap', 'Reboot Command -- Connectivity Gap Proves Restart (GPSDataLog)'), ('pvt_packet_drop', 'PVT + Emergency Packet Drop -- 15 min Fixed Window, 2.5-6s Average Gap (GPSDataLog + GPSemDataLog)'), ('packet_sequence', 'Trigger Packet + Before/After State Packets (GPSDataLog)'), ('sos_stop_both', 'SOS Stop on Tracking (EA,11) + Emergency (SEM) Servers'), ('protocol_packet', 'Protocol Field Validation of a Packet Type (GPSDataLog / GPSemDataLog)'), ('speed_accuracy', 'Constant-Speed Stretches at Target Speeds (GPSDataLog)'), ('geofence_crossing', 'Geofence Entry/Exit Distance (GPSDataLog)'), ('history_coverage', 'History (H) Packets Covering the No-Network Period (GPSDataLog)'), ('unique_cell_towers', 'Unique Cell Towers Seen (GPSDataLog)'), ('command_reply', 'Command Echo + Expected Reply in an OT,12 Packet (GPSDataLog)'), ('activation_sms', 'Activation Reply (ACTVR) Received by SMS (AirtelSmsInLog / SmppSmsIn)'), ('sms_fallback', 'Fallback SMS from the Device Received by SMS (AirtelSmsInLog / SmppSmsIn)'), ('composite', 'Combined Checks -- several checks in one test (check_config.parts)'), ('manual', 'Manual / Observed')], default='manual', max_length=30),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
