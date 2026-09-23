from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('serwis', '0009_serviceordermedia_folder'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='serviceorder',
            options={'permissions': [('access_serwis_nowe', 'Dostęp do widoku: serwis nowe'), ('access_serwis_add', 'Dostęp do widoku: serwis add'), ('access_serwis_detail', 'Dostęp do widoku: serwis detail'), ('access_zgranie_add', 'Dostęp do widoku: zgranie add'), ('access_service_note_add', 'Dostęp do widoku: service note add'), ('access_service_note_pin', 'Dostęp do widoku: service note pin'), ('access_service_note_delete', 'Dostęp do widoku: service note delete'), ('access_serwis_edit', 'Dostęp do widoku: serwis edit'), ('access_serwis_delete', 'Dostęp do widoku: serwis delete'), ('access_serwis_status_update', 'Dostęp do widoku: serwis status update'), ('access_serwis_schedule_update', 'Dostęp do widoku: serwis schedule update'), ('access_serwis_assign_workers', 'Dostęp do widoku: serwis assign workers'), ('access_service_media_delete', 'Dostęp do widoku: service media delete'), ('access_serwis_priority_update', 'Dostęp do widoku: serwis priority update'), ('access_serwis_status_zgrania_update', 'Dostęp do widoku: serwis status zgrania update'), ('access_client_locations_api', 'Dostęp do widoku: client locations api')], 'verbose_name': 'Zgłoszenie serwisowe', 'verbose_name_plural': 'Zgłoszenia serwisowe'},
        ),
    ]
