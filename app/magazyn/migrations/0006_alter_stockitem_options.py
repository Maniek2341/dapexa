from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magazyn', '0005_stockitem_min_quantity_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='stockitem',
            options={'permissions': [('access_stock_list', 'Dostęp do widoku: stock list'), ('access_stock_item_create', 'Dostęp do widoku: stock item create'), ('access_stock_in', 'Dostęp do widoku: stock in'), ('access_stock_out', 'Dostęp do widoku: stock out')], 'verbose_name': 'Przedmiot na magazynie', 'verbose_name_plural': 'Przedmioty na magazynie'},
        ),
    ]
