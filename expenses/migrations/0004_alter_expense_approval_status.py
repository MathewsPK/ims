from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='approval_status',
            field=models.CharField(choices=[('PENDING', 'Pending Review'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('PAID', 'Paid')], default='PENDING', max_length=20),
        ),
    ]
