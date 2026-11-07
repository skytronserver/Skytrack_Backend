import re

from django.db import migrations


# Every device command in technical onboarding runs on BOTH MQTT and SMS
# (user decision, 2026-11-07). The only SMS-only commands are the
# activation command (#41) and the health-check SMS inside the eSIM tests
# (#24 / #25); those are untouched.
#
# - #1 physical SOS was stopped by MQTT only and #2 app SOS by SMS only.
#   Both now need the SOS stop on each channel: trigger SOS, stop it by
#   MQTT, trigger it again, stop it by SMS. The stop command loses its fixed
#   channel so the tester picks MQTT / SMS in the command dialog.
# - The OT parameter tests (#44-#57) already check both channels but were
#   still named "... (SMS)"; renamed "... (MQTT + SMS)".

SOS = {1: 'Physical', 2: 'App'}
SMS_SUFFIX = re.compile(r'\s*\(SMS\)\s*$')


def _sos_texts(t, who):
    trigger = 'Press the physical SOS button on the device' if who == 'Physical' else 'Trigger SOS from the mobile app'
    t.name = f'{who} SOS: start on both servers + stop by MQTT and SMS'
    t.description = (f'SOS from the {who.lower()} reaches the emergency and tracking servers, and stops on both '
                     'with the SOS stop command, sent once by MQTT and once by SMS; the start and stop packets '
                     'match the protocol.')
    t.procedure = (
        '1. Confirm the device is connected to both servers, then press Start.\n'
        f'2. {trigger}. Wait about one minute: the emergency server must get the EMR packets at a 5-second cadence, '
        'and the tracking server the SOS start alert (EA,10) followed by NR packets with SOS = 1.\n'
        '3. Send "SOS stop" (@SET SOSDIS-1*) via MQTT. The device replies \'SOS DISABLED\', SOS stops on both '
        'servers (EA,11 on tracking, EPB SEM on emergency) and NR packets return to SOS = 0.\n'
        f'4. {trigger} again, wait for SOS = 1, then send "SOS stop" via SMS (choose "Send via SMS"). The device '
        'replies \'SOS DISABLED\' (also by SMS to our number) and SOS stops again (EA,11).\n'
        '5. The SOS start (EA,10) and stop (EA,11) packets are also checked field by field against the protocol.'
    )
    t.expected_result = (
        'EMR packets at a 5 s cadence on the emergency server; EA,10 + NR packets with SOS = 1 on the tracking '
        "server; reply 'SOS DISABLED' to the stop command on each channel (OT,12 source SERVER over MQTT; OT,12 "
        'source SMS and the reply SMS over SMS), each followed by EA,11; EPB SEM on emergency, NR back to SOS = 0; '
        'EA,10 and EA,11 valid against the protocol.'
    )


def forwards(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')

    for serial, who in SOS.items():
        t = TestCase.objects.filter(serial_no=serial, source_table='composite').first()
        if not t:
            continue
        commands = []
        for c in t.commands or []:
            c = dict(c)
            if c.get('key') == 'sos_stop':
                c.pop('channel', None)
            commands.append(c)
        t.commands = commands
        cfg = dict(t.check_config or {})
        parts = []
        for p in cfg.get('parts') or []:
            p = dict(p)
            if p.get('key') == 'stop_command':
                pcfg = dict(p.get('check_config') or {})
                pcfg['channels'] = ['mqtt', 'sms']
                p['check_config'] = pcfg
                p['label'] = "SOS stop by MQTT and by SMS: reply 'SOS DISABLED' + EA,11 on each (+ reply SMS)"
            parts.append(p)
        cfg['parts'] = parts
        cfg['time_limit_seconds'] = 25 * 60   # two SOS cycles
        t.check_config = cfg
        _sos_texts(t, who)
        t.save()

    for t in TestCase.objects.filter(source_table='command_reply', active=True):
        if SMS_SUFFIX.search(t.name or ''):
            t.name = SMS_SUFFIX.sub(' (MQTT + SMS)', t.name)
            t.save(update_fields=['name'])


def backwards(apps, schema_editor):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for serial, (channel, minutes) in {1: ('mqtt', 15), 2: ('sms', 20)}.items():
        t = TestCase.objects.filter(serial_no=serial, source_table='composite').first()
        if not t:
            continue
        t.commands = [dict(c, channel=channel) if c.get('key') == 'sos_stop' else c for c in t.commands or []]
        cfg = dict(t.check_config or {})
        for p in cfg.get('parts') or []:
            if p.get('key') == 'stop_command':
                p['check_config'] = dict(p.get('check_config') or {}, channels=[channel])
        cfg['time_limit_seconds'] = minutes * 60
        t.check_config = cfg
        t.name = f"{SOS[serial]} SOS: start on both servers + stop by {channel.upper()} command"
        t.save()
    for t in TestCase.objects.filter(source_table='command_reply', name__endswith=' (MQTT + SMS)'):
        if t.serial_no == 42:
            continue   # was already named "(MQTT + SMS)" before this migration
        t.name = t.name[:-len(' (MQTT + SMS)')] + ' (SMS)'
        t.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0125_onboarding_merge_duplicate_tests'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
