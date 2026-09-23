from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_companysettings_default_work_end_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='protocol_number_digits',
            field=models.PositiveSmallIntegerField(default=5, verbose_name='Liczba cyfr numeru protokołu'),
        ),
        migrations.AddField(
            model_name='companysettings',
            name='protocol_number_prefix',
            field=models.CharField(default='PROT', max_length=12, verbose_name='Prefiks numeru protokołu'),
        ),
        migrations.AddField(
            model_name='companysettings',
            name='service_download_number_prefix',
            field=models.CharField(default='ZGR', max_length=12, verbose_name='Prefiks numeru zgrania'),
        ),
        migrations.AddField(
            model_name='companysettings',
            name='service_number_digits',
            field=models.PositiveSmallIntegerField(default=4, verbose_name='Liczba cyfr numeru serwisu i zgrania'),
        ),
        migrations.AddField(
            model_name='companysettings',
            name='service_number_prefix',
            field=models.CharField(default='SER', max_length=12, verbose_name='Prefiks numeru serwisu'),
        ),
    ]
