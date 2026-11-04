from importlib import import_module

from django.db import migrations, models


# Technical onboarding (2026-11-03): the PVT packet drop test (#40) accepts an
# average gap of 2.5-6s instead of 4-6s. Devices such as AS01AA0005 report
# PVT and EPB every 3s while emergency is ON, and that is accepted. The check
# itself reads the band from technical_onboarding_testing_views; this only
# updates the tester-facing text and the source_table label.

PVT_DROP_SERIAL = 40
OLD_LABEL = 'PVT + Emergency Packet Drop -- 15 min Fixed Window, 4-6s Average Gap (GPSDataLog + GPSemDataLog)'
NEW_LABEL = 'PVT + Emergency Packet Drop -- 15 min Fixed Window, 2.5-6s Average Gap (GPSDataLog + GPSemDataLog)'

SOURCE_CHOICES = [
    (value, NEW_LABEL if label == OLD_LABEL else label)
    for value, label in import_module('skytron_api.migrations.0119_onboarding_sequence_sms_tests').SOURCE_CHOICES
]

TEXT_CHANGES = {
    'description': ('within 4-6 seconds', 'within 2.5-6 seconds'),
    'expected_result': ('Average packet gap 4-6 s', 'Average packet gap 2.5-6 s'),
}


def _rewrite(apps, forward):
    TestCase = apps.get_model('skytron_api', 'TechnicalOnboardingTestCase')
    for test_case in TestCase.objects.filter(serial_no=PVT_DROP_SERIAL):
        changed = []
        for field, (old, new) in TEXT_CHANGES.items():
            if not forward:
                old, new = new, old
            value = getattr(test_case, field) or ''
            if old in value:
                setattr(test_case, field, value.replace(old, new))
                changed.append(field)
        if changed:
            test_case.save(update_fields=changed)


def apply(apps, schema_editor):
    _rewrite(apps, forward=True)


def revert(apps, schema_editor):
    _rewrite(apps, forward=False)


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0119_onboarding_sequence_sms_tests'),
    ]

    operations = [
        migrations.AlterField(
            model_name='technicalonboardingtestcase',
            name='source_table',
            field=models.CharField(choices=SOURCE_CHOICES, default='manual', max_length=30),
        ),
        migrations.RunPython(apply, revert),
    ]
