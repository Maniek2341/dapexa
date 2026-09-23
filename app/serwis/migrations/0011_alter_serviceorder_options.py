from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('serwis', '0010_alter_serviceorder_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='serviceorder',
            options={'permissions': [('access_serwis_nowe', 'Wyświetlanie listy zgłoszeń serwisowych'), ('access_serwis_add', 'Dodawanie zgłoszeń serwisowych'), ('access_serwis_detail', 'Wyświetlanie szczegółów zgłoszenia serwisowego'), ('access_zgranie_add', 'Dodawanie zgrania ze zgłoszenia serwisowego'), ('access_service_note_add', 'Dodawanie notatek serwisowych'), ('access_service_note_pin', 'Przypinanie i odpinanie notatek serwisowych'), ('access_service_note_delete', 'Usuwanie notatek serwisowych'), ('access_serwis_edit', 'Edytowanie zgłoszeń serwisowych'), ('access_serwis_delete', 'Usuwanie zgłoszeń serwisowych'), ('access_serwis_status_update', 'Zmienianie statusu zgłoszenia serwisowego'), ('access_serwis_schedule_update', 'Zmienianie terminu zgłoszenia serwisowego'), ('access_serwis_assign_workers', 'Przypisywanie pracowników do zgłoszenia serwisowego'), ('access_service_media_delete', 'Usuwanie załączników zgłoszenia serwisowego'), ('access_serwis_priority_update', 'Zmienianie priorytetu zgłoszenia serwisowego'), ('access_serwis_status_zgrania_update', 'Zmienianie statusu zgrania serwisowego'), ('access_client_locations_api', 'Pobieranie lokalizacji klienta w serwisie')], 'verbose_name': 'Zgłoszenie serwisowe', 'verbose_name_plural': 'Zgłoszenia serwisowe'},
        ),
    ]
