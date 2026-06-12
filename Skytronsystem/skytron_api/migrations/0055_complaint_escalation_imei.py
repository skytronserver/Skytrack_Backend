"""
Add escalation fields and device stock linkage to ComplaintTicket.
Add 'escalation' action type to TicketActivity.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0054_gpsdata_tag_id_asc_index'),
    ]

    operations = [
        # Add escalated_to (nullable enum: teamlead / sosadmin / manufacturer)
        migrations.AddField(
            model_name='complaintticket',
            name='escalated_to',
            field=models.CharField(
                blank=True,
                choices=[
                    ('teamlead',     'Team Lead'),
                    ('sosadmin',     'SOS Admin'),
                    ('manufacturer', 'Manufacturer'),
                ],
                db_index=True,
                max_length=20,
                null=True,
            ),
        ),
        # Add FK to Manufacturer (nullable — set when escalated to manufacturer)
        migrations.AddField(
            model_name='complaintticket',
            name='escalated_to_manufacturer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='escalated_complaint_tickets',
                to='skytron_api.manufacturer',
            ),
        ),
        # Add FK to DeviceStock (nullable — linked by IMEI on ticket creation)
        migrations.AddField(
            model_name='complaintticket',
            name='device_stock',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='complaint_tickets',
                to='skytron_api.devicestock',
            ),
        ),
        # Extend TicketActivity.action_type max_length (was 20, keep at 20 — 'escalation' fits)
        # No length change needed: 'escalation' = 10 chars
    ]
