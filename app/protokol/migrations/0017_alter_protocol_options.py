from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('protokol', '0016_protokolimage_folder'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='protocol',
            options={'permissions': [('access_protokol_nowe', 'Dostęp do widoku: protokol nowe'), ('access_protokol_add', 'Dostęp do widoku: protokol add'), ('access_protokol_detail', 'Dostęp do widoku: protokol detail'), ('access_protocol_change_status', 'Dostęp do widoku: protocol change status'), ('access_protocol_media_delete', 'Dostęp do widoku: protocol media delete'), ('access_protocol_delete', 'Dostęp do widoku: protocol delete'), ('access_protocol_edit', 'Dostęp do widoku: protocol edit'), ('access_protocol_from_service', 'Dostęp do widoku: protocol from service'), ('access_protocol_pdf', 'Dostęp do widoku: protocol pdf'), ('access_protocol_from_work', 'Dostęp do widoku: protocol from work')], 'verbose_name': 'Protokol', 'verbose_name_plural': 'Protokoly'},
        ),
    ]
