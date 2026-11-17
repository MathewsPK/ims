from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0003_add_installation_date_to_equipment'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='amc_end_date',
            field=models.DateField(blank=True, null=True, help_text='Equipment-specific AMC end date'),
        ),
        migrations.AddField(
            model_name='equipment',
            name='invoice_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='equipment',
            name='invoice_no',
            field=models.CharField(blank=True, max_length=100, verbose_name='Invoice No.'),
        ),
        migrations.AddField(
            model_name='equipment',
            name='location',
            field=models.CharField(blank=True, max_length=200, help_text='Physical location of equipment (e.g. Gallery 1, Reception)'),
        ),
        migrations.AddField(
            model_name='equipment',
            name='win_license',
            field=models.CharField(blank=True, max_length=200, verbose_name='Windows License Key'),
        ),
    ]
