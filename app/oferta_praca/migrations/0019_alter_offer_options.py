from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oferta_praca', '0018_offervariant_sale_netto'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='offer',
            options={'ordering': ['-issue_date', '-id'], 'permissions': [('access_offer_create', 'Dostęp do widoku: offer create'), ('access_offer_list', 'Dostęp do widoku: offer list'), ('access_offer_edit', 'Dostęp do widoku: offer edit'), ('access_offer_delete', 'Dostęp do widoku: offer delete'), ('access_offer_forward_to_execution', 'Dostęp do widoku: offer forward to execution'), ('access_offer_detail', 'Dostęp do widoku: offer detail'), ('access_offer_client_locations_api', 'Dostęp do widoku: offer client locations api'), ('access_offer_status_update', 'Dostęp do widoku: offer status update'), ('access_offer_approve', 'Dostęp do widoku: offer approve'), ('access_offer_variant_add', 'Dostęp do widoku: offer variant add'), ('access_offer_variant_edit', 'Dostęp do widoku: offer variant edit'), ('access_offer_variant_delete', 'Dostęp do widoku: offer variant delete'), ('access_offer_variant_toggle_selected', 'Dostęp do widoku: offer variant toggle selected'), ('access_offer_priority_update', 'Dostęp do widoku: offer priority update'), ('access_offer_assign_workers', 'Dostęp do widoku: offer assign workers')], 'verbose_name': 'Oferta', 'verbose_name_plural': 'Oferty'},
        ),
    ]
