from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('obsluga', '0007_alter_servicecontract_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='servicecontract',
            options={'ordering': ['-created_at'], 'permissions': [('access_service_contract_list', 'Wyświetlanie listy umów serwisowych'), ('access_service_contract_add', 'Dodawanie umów serwisowych'), ('access_service_contract_detail', 'Wyświetlanie szczegółów umowy serwisowej'), ('access_service_contract_asset_add', 'Dodawanie urządzeń do umowy serwisowej'), ('access_service_contract_asset_update', 'Edytowanie urządzeń w umowie serwisowej'), ('access_service_contract_asset_delete', 'Usuwanie urządzeń z umowy serwisowej'), ('access_service_contract_parameter_add', 'Dodawanie parametrów umowy serwisowej'), ('access_service_contract_update', 'Edytowanie umów serwisowych'), ('access_service_contract_parameter_update', 'Edytowanie parametrów umowy serwisowej'), ('access_service_contract_parameter_delete', 'Usuwanie parametrów umowy serwisowej'), ('access_service_visit_confirm_period', 'Potwierdzanie okresu wizyt serwisowych'), ('access_service_contract_delete', 'Usuwanie umów serwisowych')], 'verbose_name': 'Obsługa', 'verbose_name_plural': 'Obsługi'},
        ),
    ]
