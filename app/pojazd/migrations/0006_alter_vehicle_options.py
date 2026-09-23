from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pojazd', '0005_vehicle_photo_folder_vehicleevent_folder'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='vehicle',
            options={'permissions': [('access_vehicle_create', 'Dostęp do widoku: vehicle create'), ('access_vehicle_detail', 'Dostęp do widoku: vehicle detail'), ('access_vehicle_list', 'Dostęp do widoku: vehicle list'), ('access_vehicle_update', 'Dostęp do widoku: vehicle update'), ('access_vehicle_delete', 'Dostęp do widoku: vehicle delete'), ('access_vehicle_event_create', 'Dostęp do widoku: vehicle event create'), ('access_vehicle_event_delete', 'Dostęp do widoku: vehicle event delete'), ('access_vehicle_event_update', 'Dostęp do widoku: vehicle event update')], 'verbose_name': 'Pojazd', 'verbose_name_plural': 'Pojazdy'},
        ),
    ]
