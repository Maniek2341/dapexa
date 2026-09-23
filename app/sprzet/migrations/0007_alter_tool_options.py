from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sprzet', '0006_alter_tool_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tool',
            options={'ordering': ['name', 'manufacturer', 'model'], 'permissions': [('access_tool_list', 'Wyświetlanie listy narzędzi i sprzętu'), ('access_tool_create', 'Dodawanie narzędzi i sprzętu'), ('access_tool_detail', 'Wyświetlanie szczegółów narzędzia'), ('access_tool_event_add', 'Dodawanie zdarzeń narzędzia'), ('access_tool_update', 'Edytowanie narzędzi i sprzętu'), ('access_tool_delete', 'Usuwanie narzędzi i sprzętu')], 'verbose_name': 'Narzędzie', 'verbose_name_plural': 'Narzędzia'},
        ),
    ]
