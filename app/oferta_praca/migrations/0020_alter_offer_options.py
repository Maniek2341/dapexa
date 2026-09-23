from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oferta_praca', '0019_alter_offer_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='offer',
            options={'ordering': ['-issue_date', '-id'], 'permissions': [('access_offer_create', 'Tworzenie ofert'), ('access_offer_list', 'Wyświetlanie listy ofert'), ('access_offer_edit', 'Edytowanie ofert'), ('access_offer_delete', 'Usuwanie ofert'), ('access_offer_forward_to_execution', 'Przekazywanie ofert do realizacji'), ('access_offer_detail', 'Wyświetlanie szczegółów oferty'), ('access_offer_client_locations_api', 'Pobieranie lokalizacji klienta podczas tworzenia oferty'), ('access_offer_status_update', 'Zmienianie statusu oferty'), ('access_offer_approve', 'Zatwierdzanie ofert'), ('access_offer_variant_add', 'Dodawanie wariantów oferty'), ('access_offer_variant_edit', 'Edytowanie wariantów oferty'), ('access_offer_variant_delete', 'Usuwanie wariantów oferty'), ('access_offer_variant_toggle_selected', 'Wybieranie wariantu oferty'), ('access_offer_priority_update', 'Zmienianie priorytetu oferty'), ('access_offer_assign_workers', 'Przypisywanie pracowników do oferty')], 'verbose_name': 'Oferta', 'verbose_name_plural': 'Oferty'},
        ),
    ]
