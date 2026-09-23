from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('klient', '0012_alter_client_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='client',
            options={'permissions': [('access_klient', 'Wyświetlanie listy klientów'), ('access_klient_add', 'Dodawanie klientów'), ('access_klient_edit', 'Edytowanie danych klientów'), ('access_klient_detail', 'Wyświetlanie szczegółów klienta'), ('access_klient_delete', 'Usuwanie klientów'), ('access_klient_deactivate', 'Dezaktywowanie klientów'), ('access_klient_archive', 'Wyświetlanie archiwum klientów'), ('access_klient_activate', 'Ponowne aktywowanie klientów'), ('access_client_note_pin', 'Przypinanie i odpinanie notatek klienta'), ('access_client_note_delete', 'Usuwanie notatek klienta'), ('access_contact_person_add', 'Dodawanie osób kontaktowych klienta'), ('access_location_add', 'Dodawanie lokalizacji klienta'), ('access_location_edit', 'Edytowanie lokalizacji klienta'), ('access_location_delete', 'Usuwanie lokalizacji klienta')], 'verbose_name': 'Klient', 'verbose_name_plural': 'Klienci'},
        ),
    ]
