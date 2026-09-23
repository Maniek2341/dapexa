from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sprzet', '0005_tool_folder_tooleventmedia_folder'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tool',
            options={'ordering': ['name', 'manufacturer', 'model'], 'permissions': [('access_tool_list', 'Dostęp do widoku: tool list'), ('access_tool_create', 'Dostęp do widoku: tool create'), ('access_tool_detail', 'Dostęp do widoku: tool detail'), ('access_tool_event_add', 'Dostęp do widoku: tool event add'), ('access_tool_update', 'Dostęp do widoku: tool update'), ('access_tool_delete', 'Dostęp do widoku: tool delete')], 'verbose_name': 'Narzędzie', 'verbose_name_plural': 'Narzędzia'},
        ),
    ]
