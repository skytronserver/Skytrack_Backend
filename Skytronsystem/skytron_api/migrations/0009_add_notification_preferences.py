# Generated manually to add notification preference fields to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0007_alter_session_token_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='nf_popup',
            field=models.BooleanField(default=True, verbose_name='Notification Popup'),
        ),
        migrations.AddField(
            model_name='user',
            name='nf_sms',
            field=models.BooleanField(default=True, verbose_name='Notification SMS'),
        ),
        migrations.AddField(
            model_name='user',
            name='nf_email',
            field=models.BooleanField(default=True, verbose_name='Notification Email'),
        ),
    ]
