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
#   * #59 health check by SMS on both SIM profiles: SETPROF-1 -> SENDHCHK ->
#     HCHKR by SMS, SETPROF-2 -> SENDHCHK -> HCHKR by SMS (mode health_sms).
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
    tests = {t.serial_no: t for t in TestCase.objects.filter(serial_no__gte=41, serial_no__lte=60)}

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

    # #59 health check by SMS on both profiles.
    t = tests.get(59)
    if t:
        t.name = 'Health Check by SMS on Both Profiles'
        t.description = ('Request a health check with @SET SENDHCHK-1* by SMS on SIM profile 1 and on profile 2; '
                         'the device replies by SMS with HCHKR each time.')
        t.source_table = 'health_sms'
        t.requires_command = True
        t.commands = [
            {'key': 'set_profile_1', 'label': 'Switch to profile 1 (primary network)', 'command': 'SETPROF-1', 'profile': 1},
            {'key': 'set_profile_2', 'label': 'Switch to profile 2 (secondary network)', 'command': 'SETPROF-2', 'profile': 2},
            {'key': 'send_health', 'label': 'Request health check (HCHKR reply by SMS)', 'command': 'SET SENDHCHK-1',
             'channel': 'sms'},
        ]
        t.check_config = {'command_key': 'send_health', 'profiles': [1, 2], 'time_limit_seconds': 30 * 60}
        t.procedure = (
            '1. Press Start.\n'
            '2. Send "Switch to profile 1" and wait 2-5 minutes for the device to register on the primary network '
            '(skip if it is already on profile 1).\n'
            '3. Send "Request health check" by SMS (goes to msisdn1) and wait for the HCHKR SMS reply.\n'
            '4. Send "Switch to profile 2" and wait 2-5 minutes for the device to register on the secondary network.\n'
            '5. Send "Request health check" by SMS again (goes to msisdn2) and wait for the HCHKR SMS reply.\n'
            '6. Switch back to profile 1.'
        )
        t.expected_result = ('HCHKR,000000,<vendor>,<fw>,<imei>,1,<lat>,N,<lon>,E,<fix>,<date time>,<heading>,<speed>,'
                             '<csq>,<mcc>,<mnc>,<lac>,<mainpwr>,<ign>,<vin>,<frame>,<mode> by SMS, once on each profile.')

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
            field=models.CharField(choices=[('gps', 'GPS Raw Log (GPSDataLog)'), ('gpsem', 'Emergency Raw Log (GPSemDataLog)'), ('ota_command', 'OTA Command History'), ('activation_command', 'Activation Command'), ('firmware_diff', 'Firmware Version Change (GPSDataLog)'), ('voltage_internal', 'Internal Battery Voltage -- 3 Distinct Levels (GPSDataLog)'), ('voltage_external', 'External/Main Voltage -- 3 Distinct Levels (GPSDataLog)'), ('esim_primary_to_secondary', 'eSIM Switch Primary->Secondary -- 2 Distinct Networks (GPSDataLog)'), ('esim_secondary_to_primary', 'eSIM Switch Secondary->Primary -- 2 Distinct Networks, Reversed (GPSDataLog)'), ('vehicle_registration_diff', 'Vehicle Registration Number Changed (GPSDataLog)'), ('reboot_restart_gap', 'Reboot Command -- Connectivity Gap Proves Restart (GPSDataLog)'), ('pvt_packet_drop', 'PVT + Emergency Packet Drop -- 15 min Fixed Window, 2.5-6s Average Gap (GPSDataLog + GPSemDataLog)'), ('packet_sequence', 'Trigger Packet + Before/After State Packets (GPSDataLog)'), ('sos_stop_both', 'SOS Stop on Tracking (EA,11) + Emergency (SEM) Servers'), ('protocol_packet', 'Protocol Field Validation of a Packet Type (GPSDataLog / GPSemDataLog)'), ('speed_accuracy', 'Constant-Speed Stretches at Target Speeds (GPSDataLog)'), ('geofence_crossing', 'Geofence Entry/Exit Distance (GPSDataLog)'), ('history_coverage', 'History (H) Packets Covering the No-Network Period (GPSDataLog)'), ('unique_cell_towers', 'Unique Cell Towers Seen (GPSDataLog)'), ('command_reply', 'Command Echo + Expected Reply in an OT,12 Packet (GPSDataLog)'), ('activation_sms', 'Activation Reply (ACTVR) Received by SMS (AirtelSmsInLog / SmppSmsIn)'), ('sms_fallback', 'Fallback SMS from the Device Received by SMS (AirtelSmsInLog / SmppSmsIn)'), ('health_sms', 'Health Check Reply (HCHKR) by SMS on Profile 1 and Profile 2 (AirtelSmsInLog / SmppSmsIn)'), ('manual', 'Manual / Observed')], default='manual', max_length=30),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
