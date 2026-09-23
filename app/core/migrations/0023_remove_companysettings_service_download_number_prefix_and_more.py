from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_companysettings_protocol_number_digits_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='companysettings',
            name='service_download_number_prefix',
        ),
        migrations.AlterField(
            model_name='companysettings',
            name='service_number_digits',
            field=models.PositiveSmallIntegerField(default=4, verbose_name='Liczba cyfr numeru zgłoszenia'),
        ),
    ]
