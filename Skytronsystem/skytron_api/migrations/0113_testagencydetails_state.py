from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0112_onboarding_test_plan_sheet'),
    ]

    operations = [
        migrations.AddField(
            model_name='testagencydetails',
            name='state',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='skytron_api.settings_state'),
        ),
    ]
