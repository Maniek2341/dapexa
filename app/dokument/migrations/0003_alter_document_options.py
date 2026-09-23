from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dokument', '0002_alter_document_options_alter_documentfolder_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='document',
            options={'permissions': [('access_document_add', 'Dostęp do widoku: document add'), ('access_documents_list', 'Dostęp do widoku: documents list'), ('access_document_delete', 'Dostęp do widoku: document delete'), ('access_document_edit', 'Dostęp do widoku: document edit')], 'verbose_name': 'Dokument', 'verbose_name_plural': 'Dokumenty'},
        ),
    ]
