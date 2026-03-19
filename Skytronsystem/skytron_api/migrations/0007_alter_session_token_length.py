"""Alter Session.token max_length to 1500 (for longer JWT tokens)

This migration is a simple AlterField to expand the token column to 1500
characters. It is safe to run on the existing data.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0005_add_token_blacklist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='session',
            name='token',
            field=models.CharField(max_length=1500, blank=True, null=True, verbose_name='Token'),
        ),
    ]
