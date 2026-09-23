from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('urzadzenie', '0005_productactivity'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='product',
            options={'permissions': [('access_product_create', 'Dostęp do widoku: product create'), ('access_product_list', 'Dostęp do widoku: product list'), ('access_product_detail', 'Dostęp do widoku: product detail'), ('access_product_offer_usage', 'Dostęp do widoku: product offer usage'), ('access_product_protocol_usage', 'Dostęp do widoku: product protocol usage'), ('access_product_stock_history', 'Dostęp do widoku: product stock history'), ('access_product_update', 'Dostęp do widoku: product update')], 'verbose_name': 'Urzadzenie', 'verbose_name_plural': 'Urzadzenia'},
        ),
    ]
