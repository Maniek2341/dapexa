from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('protokol', '0017_alter_protocol_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='protocol',
            options={'permissions': [('access_protokol_nowe', 'Wyświetlanie listy protokołów'), ('access_protokol_add', 'Dodawanie protokołów'), ('access_protokol_detail', 'Wyświetlanie szczegółów protokołu'), ('access_protocol_change_status', 'Zmienianie statusu protokołu'), ('access_protocol_media_delete', 'Usuwanie załączników protokołu'), ('access_protocol_delete', 'Usuwanie protokołów'), ('access_protocol_edit', 'Edytowanie protokołów'), ('access_protocol_from_service', 'Tworzenie protokołu ze zgłoszenia serwisowego'), ('access_protocol_pdf', 'Generowanie protokołu w formacie PDF'), ('access_protocol_from_work', 'Tworzenie protokołu z pracy')], 'verbose_name': 'Protokol', 'verbose_name_plural': 'Protokoly'},
        ),
    ]
