from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_companysettings_protocol_number_digits_and_more'),
        ('klient', '0013_alter_client_options'),
        ('serwis', '0011_alter_serviceorder_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='serviceorder',
            name='number',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddConstraint(
            model_name='serviceorder',
            constraint=models.UniqueConstraint(fields=('company', 'number'), name='unique_service_number_per_company'),
        ),
    ]
