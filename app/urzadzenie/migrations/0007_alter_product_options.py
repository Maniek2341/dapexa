from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('urzadzenie', '0006_alter_product_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='product',
            options={'permissions': [('access_product_create', 'Dodawanie urządzeń'), ('access_product_list', 'Wyświetlanie listy urządzeń'), ('access_product_detail', 'Wyświetlanie szczegółów urządzenia'), ('access_product_offer_usage', 'Wyświetlanie użycia urządzenia w ofertach'), ('access_product_protocol_usage', 'Wyświetlanie użycia urządzenia w protokołach'), ('access_product_stock_history', 'Wyświetlanie historii magazynowej urządzenia'), ('access_product_update', 'Edytowanie urządzeń')], 'verbose_name': 'Urzadzenie', 'verbose_name_plural': 'Urzadzenia'},
        ),
    ]
