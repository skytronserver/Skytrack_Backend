from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0101_company_pan_card_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='whitelistrequest',
            name='device_model',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='whitelist_requests', to='skytron_api.devicemodel'),
        ),
        migrations.AlterField(
            model_name='whitelistrequest',
            name='device_stocks',
            field=models.ManyToManyField(blank=True, related_name='whitelist_requests', to='skytron_api.devicestock'),
        ),
        migrations.AddField(
            model_name='activewhitelist',
            name='device_model',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='active_whitelists', to='skytron_api.devicemodel'),
        ),
        migrations.AlterField(
            model_name='activewhitelist',
            name='device_stock',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='active_whitelists', to='skytron_api.devicestock'),
        ),
    ]
