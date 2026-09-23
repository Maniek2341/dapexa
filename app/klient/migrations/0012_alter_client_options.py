from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('klient', '0011_remove_clientlocation_email_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='client',
            options={'permissions': [('access_klient', 'Dostęp do widoku: klient'), ('access_klient_add', 'Dostęp do widoku: klient add'), ('access_klient_edit', 'Dostęp do widoku: klient edit'), ('access_klient_detail', 'Dostęp do widoku: klient detail'), ('access_klient_delete', 'Dostęp do widoku: klient delete'), ('access_klient_deactivate', 'Dostęp do widoku: klient deactivate'), ('access_klient_archive', 'Dostęp do widoku: klient archive'), ('access_klient_activate', 'Dostęp do widoku: klient activate'), ('access_client_note_pin', 'Dostęp do widoku: client note pin'), ('access_client_note_delete', 'Dostęp do widoku: client note delete'), ('access_contact_person_add', 'Dostęp do widoku: contact person add'), ('access_location_add', 'Dostęp do widoku: location add'), ('access_location_edit', 'Dostęp do widoku: location edit'), ('access_location_delete', 'Dostęp do widoku: location delete')], 'verbose_name': 'Klient', 'verbose_name_plural': 'Klienci'},
        ),
    ]
