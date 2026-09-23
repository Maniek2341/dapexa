from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dokument', '0003_alter_document_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='document',
            options={'permissions': [('access_document_add', 'Dodawanie dokumentów'), ('access_documents_list', 'Wyświetlanie listy dokumentów'), ('access_document_delete', 'Usuwanie dokumentów'), ('access_document_edit', 'Edytowanie dokumentów')], 'verbose_name': 'Dokument', 'verbose_name_plural': 'Dokumenty'},
        ),
    ]
