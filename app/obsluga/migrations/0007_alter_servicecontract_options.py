from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('obsluga', '0006_servicecontractmedia_folder'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='servicecontract',
            options={'ordering': ['-created_at'], 'permissions': [('access_service_contract_list', 'Dostęp do widoku: service contract list'), ('access_service_contract_add', 'Dostęp do widoku: service contract add'), ('access_service_contract_detail', 'Dostęp do widoku: service contract detail'), ('access_service_contract_asset_add', 'Dostęp do widoku: service contract asset add'), ('access_service_contract_asset_update', 'Dostęp do widoku: service contract asset update'), ('access_service_contract_asset_delete', 'Dostęp do widoku: service contract asset delete'), ('access_service_contract_parameter_add', 'Dostęp do widoku: service contract parameter add'), ('access_service_contract_update', 'Dostęp do widoku: service contract update'), ('access_service_contract_parameter_update', 'Dostęp do widoku: service contract parameter update'), ('access_service_contract_parameter_delete', 'Dostęp do widoku: service contract parameter delete'), ('access_service_visit_confirm_period', 'Dostęp do widoku: service visit confirm period'), ('access_service_contract_delete', 'Dostęp do widoku: service contract delete')], 'verbose_name': 'Obsługa', 'verbose_name_plural': 'Obsługi'},
        ),
    ]
