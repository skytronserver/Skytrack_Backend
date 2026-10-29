from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0113_testagencydetails_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='devicemodel',
            name='closed_box_image',
            field=models.FileField(blank=True, null=True, upload_to='device_model_images/'),
        ),
        migrations.AddField(
            model_name='devicemodel',
            name='pcb_top_image',
            field=models.FileField(blank=True, null=True, upload_to='device_model_images/'),
        ),
        migrations.AddField(
            model_name='devicemodel',
            name='pcb_bottom_image',
            field=models.FileField(blank=True, null=True, upload_to='device_model_images/'),
        ),
    ]
