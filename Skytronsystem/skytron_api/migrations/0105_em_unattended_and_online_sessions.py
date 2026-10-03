from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0104_gpsdata_tag_fix_id_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='EMExUnattendedTime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('duration_seconds', models.PositiveIntegerField()),
                ('reason', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ex', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unattended_times', to='skytron_api.em_ex')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='em_unattended_times', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [models.Index(fields=['ex', 'start_time'], name='em_unattended_ex_start_idx')],
            },
        ),
        migrations.CreateModel(
            name='EMExOnlineSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('last_seen', models.DateTimeField()),
                ('ex', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='online_sessions', to='skytron_api.em_ex')),
            ],
            options={
                'indexes': [models.Index(fields=['ex', 'last_seen'], name='em_online_ex_last_seen_idx')],
            },
        ),
    ]
