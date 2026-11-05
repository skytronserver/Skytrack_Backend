from django.db import migrations


# Technical onboarding (2026-11-04): Ignition OFF status (#10).
# Devices report every 10s with the ignition OFF, so the IF,08 alert plus 8
# ignition-OFF packets cannot all arrive within 60s (only 7 fit). The window
# for the 8 after-packets is widened to 120s. The procedure now tells the
# tester to press Start while the ignition is still ON, because an IF,08 sent
# before Start is not counted.

IGNITION_OFF_SERIAL = 10

OLD = {
    'within_seconds': 60,
    'procedure': (
        '1. Keep the device ignition input in the ON state (wire connected to 12V).\n'
        '2. Disconnect the ignition wire from 12V.\n'
        '3. Observe the data packets for one minute.'
    ),
    'expected_result': (
        '10 data packets within one minute:\n'
        'Packet 1 = last ignition-ON packet\n'
        'Packet 2 = Ignition OFF alert\n'
        'Packets 3-10 = ignition-OFF status packets.'
    ),
}

NEW = {
    'within_seconds': 120,
    'procedure': (
        '1. Connect the device ignition wire to 12V (ignition ON) and wait until the live status shows Ignition ON.\n'
        '2. Press Start while the ignition is still ON. Do not switch the ignition OFF before pressing Start: '
        'an Ignition OFF alert sent before Start is not counted.\n'
        '3. Wait for at least one ignition-ON packet after Start (about 10 seconds).\n'
        '4. Disconnect the ignition wire from 12V once and leave it disconnected. Do not reconnect it during the test.\n'
        '5. Wait 2 minutes. The device sends the Ignition OFF alert (IF,08) and then ignition-OFF packets every 10 seconds.\n'
        '6. The test passes automatically once the alert and 8 ignition-OFF packets are received.\n'
        'If the test fails or times out, reconnect the ignition wire, wait for ignition ON, and run the test again from step 1.'
    ),
    'expected_result': (
        '10 data packets within two minutes of the Ignition OFF alert:\n'
        'Packet 1 = last ignition-ON packet\n'
        'Packet 2 = Ignition OFF alert (IF,08)\n'
        'Packets 3-10 = ignition-OFF status packets (ignition = 0).'
    ),
}


def _apply(apps, values):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for test_case in TestCase.objects.filter(serial_no=IGNITION_OFF_SERIAL):
        cfg = dict(test_case.check_config or {})
        cfg['within_seconds'] = values['within_seconds']
        test_case.check_config = cfg
        test_case.procedure = values['procedure']
        test_case.expected_result = values['expected_result']
        test_case.save(update_fields=['check_config', 'procedure', 'expected_result'])


def apply(apps, schema_editor):
    _apply(apps, NEW)


def revert(apps, schema_editor):
    _apply(apps, OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0120_onboarding_pvt_drop_gap_band'),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
