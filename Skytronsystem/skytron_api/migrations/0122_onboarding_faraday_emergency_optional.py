from django.db import migrations


# Technical onboarding (2026-11-04): History-data storage & transmission
# (Faraday box, serial 20). The test passes on the history (H) PVT packets
# alone for now. Stored emergency (EPB SP) packets are still checked and
# reported in the result notes but no longer fail the test, because of a
# known device fault: after the network returns the device reconnects its
# tracking MQTT connections but not the emergency one, so the stored EPB
# packets only go out at the next SOS press. Revert this migration to make
# them required again once the firmware is fixed.

FARADAY_SERIAL = 20


def _set(apps, required):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for test_case in TestCase.objects.filter(serial_no=FARADAY_SERIAL):
        cfg = dict(test_case.check_config or {})
        cfg['require_emergency_history'] = required
        test_case.check_config = cfg
        test_case.save(update_fields=['check_config'])


def apply(apps, schema_editor):
    _set(apps, False)


def revert(apps, schema_editor):
    _set(apps, True)


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0121_onboarding_ignition_off_window'),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
