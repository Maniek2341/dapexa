from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serwis', '0012_alter_serviceorder_number_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='serviceorder',
            options={'permissions': [('access_serwis_nowe', 'Wyświetlanie listy zgłoszeń serwisowych'), ('access_serwis_add', 'Dodawanie zgłoszeń serwisowych'), ('access_serwis_detail', 'Wyświetlanie szczegółów zgłoszenia serwisowego'), ('access_service_note_add', 'Dodawanie notatek serwisowych'), ('access_service_note_pin', 'Przypinanie i odpinanie notatek serwisowych'), ('access_service_note_delete', 'Usuwanie notatek serwisowych'), ('access_serwis_edit', 'Edytowanie zgłoszeń serwisowych'), ('access_serwis_delete', 'Usuwanie zgłoszeń serwisowych'), ('access_serwis_status_update', 'Zmienianie statusu zgłoszenia serwisowego'), ('access_serwis_schedule_update', 'Zmienianie terminu zgłoszenia serwisowego'), ('access_serwis_assign_workers', 'Przypisywanie pracowników do zgłoszenia serwisowego'), ('access_service_media_delete', 'Usuwanie załączników zgłoszenia serwisowego'), ('access_serwis_priority_update', 'Zmienianie priorytetu zgłoszenia serwisowego'), ('access_serwis_status_zgrania_update', 'Zmienianie statusu obsługi'), ('access_client_locations_api', 'Pobieranie lokalizacji klienta w serwisie')], 'verbose_name': 'Zgłoszenie serwisowe', 'verbose_name_plural': 'Zgłoszenia serwisowe'},
        ),
        migrations.AlterField(
            model_name='serviceorder',
            name='status',
            field=models.CharField(choices=[('new', 'Nowe'), ('forgoted', 'Zapomniane'), ('in_progress', 'W trakcie'), ('done', 'Zakończone'), ('zgrania', 'Obsługa'), ('cancelled', 'Anulowane')], default='new', max_length=20),
        ),
        migrations.AlterField(
            model_name='serviceorder',
            name='status_zgrania',
            field=models.CharField(blank=True, choices=[('new', 'Nowa'), ('nothind', 'Brak materiału'), ('done', 'Zakończona'), ('in_progress', 'W trakcie'), ('send', 'Zakończona i przekazana')], default='new', max_length=20),
        ),
    ]
