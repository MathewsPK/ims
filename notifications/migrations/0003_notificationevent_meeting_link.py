from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationevent',
            name='meeting_link',
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text='Google Meet, Teams, Zoom or any video call link',
            ),
        ),
    ]
