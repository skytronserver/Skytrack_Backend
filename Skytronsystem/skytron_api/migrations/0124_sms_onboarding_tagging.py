from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# SMS in technical onboarding and tagging (2026-11-05).
#
# Onboarding tests:
#   * #41 activation: ACTV,<6-digit code>,<our VMN 9181016496> by SMS; the
#     device SMSes back ACTVR,<code>,<vendor>,<fw>,<imei>,...
#   * #42-#58 OT parameter tests: every command (SET and its GET read-back)
#     is sent over MQTT AND by SMS. Each channel passes on the device's OT,12
#     reply with the matching source (SERVER / SMS) and the expected text; on
#     SMS the device's reply SMS must also reach us.
#   * #24 / #25 eSIM switch also need a health check by SMS on each profile:
#     SENDHCHK -> HCHKR by SMS on the old profile, SETPROF-n, then SENDHCHK ->
#     HCHKR on the new one (check_config.health_sms). #59 (health packet on
#     request) is retired: the eSIM tests cover it.
#   * #60 SMS fallback: wrong emergency IP + SOS -> fallback SMS
#     <IMEI>,<lat>,N,<lon>,E,<A|V>,<speed>,<cellid>,<lac>,<ddmmyyyyhhmmss>
#     from the device's msisdn1 / msisdn2.
# Tagging step 4: DeviceTaggingSmsCommand + DeviceStockMaster.sms_checks.

OT_TIME_LIMIT = 20 * 60          # 2 commands x 2 channels, SMS replies take minutes

# serial -> (code, SET expected reply, GET expected reply)
PARAM_TESTS = {
    42: ('REGNO', ['SET SUCCESSFULLY REGNO-{value}'], ['REGNO-']),
    44: ('HBT', ['SET SUCCESSFULLY HBT-{value}'], ['HBT-']),
    45: ('HAT', ['SET SUCCESSFULLY HAT-{value}'], ['HAT-']),
    46: ('RTT', ['SET SUCCESSFULLY RTT-{value}'], ['RTT-']),
    47: ('OTT', ['SET SUCCESSFULLY OTT-{value}'], ['OTT-']),
    48: ('URION', ['SET SUCCESSFULLY URION-{value}'], ['URION-']),
    49: ('URIOFF', ['SET SUCCESSFULLY URIOFF-{value}'], ['URIOFF-']),
    50: ('EMCR', ['SET SUCCESSFULLY EMCR-{value}'], ['EMCR-']),
    51: ('URHP', ['SET SUCCESSFULLY URHP-{value}'], ['URHP-']),
    52: ('IP1', ['SET SUCCESSFULLY IP1-{value}'], ['IP1-']),
    53: ('EIP', ['SET SUCCESSFULLY EIP-{value}'], ['EIP-']),
    54: ('ESCN', ['SET SUCCESSFULLY ESCN-{value}'], ['ESCN-']),
    # The device answers its own APN (e.g. APN-xsim), not always the value sent.
    55: ('APN', ['SET SUCCESSFULLY APN-'], ['APN-']),
}

BOTH_CHANNELS_NOTE = (
    'Each command must be sent twice: once over MQTT and once by SMS (pick the channel next to the command). '
    'Over MQTT the device answers with an OT,12 packet (source SERVER); by SMS it answers with an OT,12 packet '
    '(source SMS) and an SMS reply to our number, which can take a few minutes.'
)


def _param_update(test, code, set_reply, get_reply):
    commands = list(test.commands or [])
    set_cmd = next((c for c in commands if c.get('key', '').startswith('set_')), None)
    get_cmd = next((c for c in commands if c.get('key', '').startswith('get_')), None)
    if not set_cmd:
        return
    keys = [set_cmd['key']]
    if get_cmd:
        get_cmd['expected_reply'] = get_reply
        keys.append(get_cmd['key'])
    set_framed = '@' + set_cmd['command'].replace('{value}', '<value>') + '*'
    get_framed = ('@' + get_cmd['command'] + '*') if get_cmd else None
    cfg = dict(test.check_config or {})
    cfg.update({
        'command_key': set_cmd['key'],
        'expected_reply': set_reply,
        'required_commands': keys,
        'channels': ['mqtt', 'sms'],
        'time_limit_seconds': OT_TIME_LIMIT,
    })
    test.commands = commands
    test.check_config = cfg
    test.requires_command = True
    warning = ''
    if code in ('IP1', 'EIP', 'APN'):
        warning = ('\n   Use the value the device must keep (read it first with GET): a wrong value disconnects '
                   'the device from the server.')
    steps = [
        '1. Press Start.',
        f'2. Over MQTT: send {set_framed} (e.g. {set_cmd.get("value_hint", "")}) and wait for the reply.{warning}',
    ]
    if get_framed:
        steps.append(f'3. Over MQTT: send {get_framed} and wait for the reply.')
    steps.append(f'{len(steps) + 1}. By SMS: send the same command{"s" if get_framed else ""} again, choosing "Send via SMS", '
                 f'and wait for the device\'s SMS reply.')
    test.procedure = '\n'.join(steps) + '\n' + BOTH_CHANNELS_NOTE
    expected = [f"SET: {' + '.join(set_reply).replace('{value}', '<value>') or 'command echo'}"]
    if get_framed:
        expected.append(f"GET: {' + '.join(get_reply)}<value>")
    test.expected_result = (
        f"On MQTT and on SMS: OT,12 reply echoing each command ({'; '.join(expected)}); "
        f"on SMS also the device's reply SMS."
    )


def forwards(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    tests = {t.serial_no: t for t in TestCase.objects.filter(serial_no__in=[24, 25] + list(range(41, 61)))}

    for serial, (code, set_reply, get_reply) in PARAM_TESTS.items():
        if serial in tests:
            _param_update(tests[serial], code, set_reply, get_reply)

    # #43 SOS off: one leg per channel, SOS must be active before each.
    t = tests.get(43)
    if t:
        cfg = dict(t.check_config or {})
        cfg.update({'channels': ['mqtt', 'sms'], 'required_commands': ['sos_stop'], 'time_limit_seconds': OT_TIME_LIMIT})
        t.check_config = cfg
        t.requires_command = True
        t.procedure = (
            '1. Trigger SOS on the device, then press Start.\n'
            '2. Over MQTT: send @SET SOSDIS-1* and wait for the reply and the SOS stop alert.\n'
            '3. Trigger SOS again.\n'
            '4. By SMS: send @SET SOSDIS-1* again ("Send via SMS") and wait for the SMS reply and the SOS stop alert.\n'
            + BOTH_CHANNELS_NOTE
        )
        t.expected_result = "On MQTT and on SMS: reply 'SOS DISABLED' followed by the SOS stop alert (EA,11); on SMS also the reply SMS."

    # #56 GET INFO, #57 GETLOC: both channels.
    for serial, framed in ((56, '@GET INFO*'), (57, '@GETLOC*')):
        t = tests.get(serial)
        if not t:
            continue
        cfg = dict(t.check_config or {})
        cfg.update({'channels': ['mqtt', 'sms'], 'time_limit_seconds': OT_TIME_LIMIT})
        t.check_config = cfg
        t.requires_command = True
        t.procedure = (
            '1. Press Start.\n'
            f'2. Over MQTT: send {framed} and wait for the reply.\n'
            f'3. By SMS: send {framed} again ("Send via SMS") and wait for the SMS reply.\n'
            + BOTH_CHANNELS_NOTE
        )

    # #58 DEVRESET: restart proven per channel by a login packet.
    t = tests.get(58)
    if t:
        cfg = dict(t.check_config or {})
        cfg.update({'channels': ['mqtt', 'sms'], 'expected_reply': ['DEV RESET'], 'reply_required': False,
                    'time_limit_seconds': OT_TIME_LIMIT})
        t.check_config = cfg
        t.requires_command = True
        t.procedure = (
            '1. Press Start.\n'
            '2. Over MQTT: send @DEVRESET* and wait for the device to restart and log in again.\n'
            '3. By SMS: send @DEVRESET* again ("Send via SMS") and wait for the device to restart and log in again.'
        )
        t.expected_result = ("Reply 'DEV RESET SEQUENCE STARTED', then a login packet after each of the two commands. "
                             "'DEV RESET SEQUENCE BUSY (OT PENDING)' means it did not reset -- send it again.")

    # #41 activation: reply number is our VMN.
    t = tests.get(41)
    if t:
        commands = list(t.commands or [])
        for c in commands:
            if c.get('key') == 'activation':
                c['command'] = 'ACTV,{value},{reply_number}'
                c['channel'] = 'sms'
                c['frame'] = False
        t.commands = commands
        cfg = dict(t.check_config or {})
        cfg.update({'command_key': 'activation', 'time_limit_seconds': 15 * 60})
        t.check_config = cfg
        t.requires_command = True
        t.procedure = (
            '1. Press Start.\n'
            '2. Send the activation command by SMS (ACTV,<6-digit code>,9181016496; leave the value blank for a random code).\n'
            '3. Wait for the device to SMS back ACTVR,<same code>,<vendor>,<fw>,<imei>,1,<lat>,N,<lon>,E,... '
            '(can take a few minutes).'
        )
        t.expected_result = 'ACTVR SMS from the device with the same code and its IMEI.'

    # #24 / #25 eSIM switch: health check by SMS on each profile -- before
    # the switch on the old profile, after it on the new one.
    for serial, old_p, new_p in ((24, 1, 2), (25, 2, 1)):
        t = tests.get(serial)
        if not t:
            continue
        old_name = 'primary' if old_p == 1 else 'secondary'
        new_name = 'primary' if new_p == 1 else 'secondary'
        t.requires_command = True
        t.commands = [
            {'key': f'set_profile_{new_p}', 'label': f'Switch to {new_name} profile', 'command': f'SETPROF-{new_p}',
             'profile': new_p},
            {'key': 'send_health', 'label': 'Request health check (HCHKR reply by SMS)', 'command': 'SET SENDHCHK-1',
             'channel': 'sms'},
        ]
        cfg = dict(t.check_config or {})
        cfg.update({
            'health_sms': {'command_key': 'send_health', 'profiles': [old_p, new_p], 'start_profile': old_p},
            'time_limit_seconds': 30 * 60,
        })
        t.check_config = cfg
        t.procedure = (
            f'1. Confirm the device is on the {old_name} profile (profile {old_p}), then press Start.\n'
            f'2. Send "Request health check" by SMS (goes to msisdn{old_p}) and wait for the HCHKR SMS reply.\n'
            f'3. Send the switch command ({old_name} -> {new_name}, SETPROF-{new_p}) and wait 2-5 minutes for the '
            f'device to register on the {new_name} network.\n'
            f'4. Send "Request health check" by SMS again (goes to msisdn{new_p}) and wait for the HCHKR SMS reply.'
        )
        t.expected_result = (
            f'Last 2 packets on the {old_name} cell, followed by the next 2 packets on the {new_name} cell; '
            f'an HCHKR,000000,<vendor>,<fw>,<imei>,... SMS reply to the health check on profile {old_p} and on '
            f'profile {new_p}.'
        )

    # #59 health packet request: covered by the eSIM switch tests now.
    t = tests.get(59)
    if t:
        t.active = False

    # #60 SMS fallback.
    t = tests.get(60)
    if t:
        t.name = 'SOS SMS Fallback (emergency server unreachable)'
        t.description = ('With the emergency IP set to a wrong address, an SOS must go out by SMS from the '
                         "device's primary or secondary number.")
        t.requires_command = True
        t.commands = [
            {'key': 'get_eip', 'label': 'Read the emergency IP (note it to restore later)', 'command': 'GETEIP'},
            {'key': 'set_escn', 'label': 'Set emergency SMS centre number to ours', 'command': 'SETESCN-{sms_number}'},
            {'key': 'set_eip_wrong', 'label': 'Set a wrong emergency IP', 'command': 'SETEIP-{value}',
             'value_hint': '1.1.1.1', 'value_regex': r'^\d{1,3}(\.\d{1,3}){3}$'},
            {'key': 'restore_eip', 'label': 'Restore the emergency IP', 'command': 'SETEIP-{value}',
             'value_hint': 'the IP read at the start', 'value_regex': r'^\d{1,3}(\.\d{1,3}){3}$'},
            {'key': 'sos_stop', 'label': 'SOS stop', 'command': 'SET SOSDIS-1'},
        ]
        t.check_config = {'require_sender_match': True, 'time_limit_seconds': 20 * 60}
        t.procedure = (
            '1. Press Start. Read the emergency IP (GETEIP) and note it.\n'
            '2. Set the emergency SMS centre number to ours (SETESCN).\n'
            '3. Trigger SOS and check it reaches the emergency server; stop it (SOS stop).\n'
            '4. Set a wrong emergency IP (e.g. 1.1.1.1) and trigger SOS again.\n'
            "5. Wait for the fallback SMS from the device's primary or secondary number.\n"
            '6. Stop SOS and restore the emergency IP.'
        )
        t.expected_result = ('SMS from msisdn1 or msisdn2: <IMEI>,<lat>,<N|S>,<lon>,<E|W>,<A|V>,<speed>,<cellid>,<lac>,'
                             '<ddmmyyyyhhmmss>, carrying this device\'s IMEI.')

    for t in tests.values():
        t.save()
    _assign_sequence(TestCase)


def _assign_sequence(TestCase):
    """Run order 1..N over the active tests, keeping their current order; inactive tests get none."""
    TestCase.objects.filter(active=False).update(sequence=None)
    active = sorted(TestCase.objects.filter(active=True),
                    key=lambda t: (t.sequence if t.sequence is not None else 10 ** 6, t.serial_no))
    for number, test_case in enumerate(active, 1):
        if test_case.sequence != number:
            test_case.sequence = number
            test_case.save(update_fields=['sequence'])


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0123_smpp_gateway_api'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='technicalonboardingcommanddispatch',
            name='sms_to',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='technicalonboardingcommanddispatch',
            name='sms_via',
            field=models.CharField(blank=True, default='', max_length=15),
        ),
        migrations.AddField(
            model_name='technicalonboardingcommanddispatch',
            name='sms_ref',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='devicestockmaster',
            name='sms_checks',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='DeviceTaggingSmsCommand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imei', models.CharField(db_index=True, max_length=55)),
                ('kind', models.CharField(choices=[('set_profile', 'Set profile'), ('health', 'Health check request'), ('activation', 'Activation command')], max_length=15)),
                ('profile', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('value', models.CharField(blank=True, default='', max_length=20)),
                ('command_sent', models.CharField(max_length=255)),
                ('sms_to', models.CharField(blank=True, default='', max_length=30)),
                ('sms_via', models.CharField(blank=True, default='', max_length=15)),
                ('sms_ref', models.CharField(blank=True, default='', max_length=64)),
                ('send_status', models.CharField(choices=[('queued', 'Queued'), ('failed', 'Failed')], default='queued', max_length=10)),
                ('error', models.CharField(blank=True, default='', max_length=255)),
                ('sent_at', models.DateTimeField()),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sms_commands', to='skytron_api.devicestockmaster')),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'device_tagging_sms_command',
                'ordering': ['-sent_at'],
                'indexes': [models.Index(fields=['record', 'kind', 'sent_at'], name='tagsms_record_kind_idx')],
            },
        ),
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(choices=[('gps', 'GPS Raw Log (GPSDataLog)'), ('gpsem', 'Emergency Raw Log (GPSemDataLog)'), ('ota_command', 'OTA Command History'), ('activation_command', 'Activation Command'), ('firmware_diff', 'Firmware Version Change (GPSDataLog)'), ('voltage_internal', 'Internal Battery Voltage -- 3 Distinct Levels (GPSDataLog)'), ('voltage_external', 'External/Main Voltage -- 3 Distinct Levels (GPSDataLog)'), ('esim_primary_to_secondary', 'eSIM Switch Primary->Secondary -- 2 Distinct Networks (GPSDataLog)'), ('esim_secondary_to_primary', 'eSIM Switch Secondary->Primary -- 2 Distinct Networks, Reversed (GPSDataLog)'), ('vehicle_registration_diff', 'Vehicle Registration Number Changed (GPSDataLog)'), ('reboot_restart_gap', 'Reboot Command -- Connectivity Gap Proves Restart (GPSDataLog)'), ('pvt_packet_drop', 'PVT + Emergency Packet Drop -- 15 min Fixed Window, 2.5-6s Average Gap (GPSDataLog + GPSemDataLog)'), ('packet_sequence', 'Trigger Packet + Before/After State Packets (GPSDataLog)'), ('sos_stop_both', 'SOS Stop on Tracking (EA,11) + Emergency (SEM) Servers'), ('protocol_packet', 'Protocol Field Validation of a Packet Type (GPSDataLog / GPSemDataLog)'), ('speed_accuracy', 'Constant-Speed Stretches at Target Speeds (GPSDataLog)'), ('geofence_crossing', 'Geofence Entry/Exit Distance (GPSDataLog)'), ('history_coverage', 'History (H) Packets Covering the No-Network Period (GPSDataLog)'), ('unique_cell_towers', 'Unique Cell Towers Seen (GPSDataLog)'), ('command_reply', 'Command Echo + Expected Reply in an OT,12 Packet (GPSDataLog)'), ('activation_sms', 'Activation Reply (ACTVR) Received by SMS (AirtelSmsInLog / SmppSmsIn)'), ('sms_fallback', 'Fallback SMS from the Device Received by SMS (AirtelSmsInLog / SmppSmsIn)'), ('manual', 'Manual / Observed')], default='manual', max_length=30),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
