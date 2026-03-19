# Generated migration for TokenBlacklist model

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0004_alter_session_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='TokenBlacklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=512, unique=True, verbose_name='Token')),
                ('jti', models.CharField(db_index=True, max_length=255, verbose_name='JWT ID')),
                ('user_id', models.IntegerField(db_index=True, verbose_name='User ID')),
                ('blacklisted_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Blacklisted At')),
                ('reason', models.CharField(choices=[('logout', 'User Logout'), ('expired', 'Token Expired'), ('security', 'Security Violation'), ('admin', 'Admin Action')], default='logout', max_length=20, verbose_name='Reason')),
                ('expires_at', models.DateTimeField(verbose_name='Token Expires At')),
            ],
            options={
                'verbose_name': 'Token Blacklist',
                'verbose_name_plural': 'Token Blacklists',
                'db_table': 'token_blacklist',
                'indexes': [
                    models.Index(fields=['token'], name='token_idx'),
                    models.Index(fields=['jti'], name='jti_idx'),
                    models.Index(fields=['user_id'], name='user_id_idx'),
                ],
            },
        ),
    ]
