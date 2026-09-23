from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('magazyn', '0006_alter_stockitem_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='stockitem',
            options={'permissions': [('access_stock_list', 'Wyświetlanie stanów magazynowych'), ('access_stock_item_create', 'Dodawanie pozycji magazynowych'), ('access_stock_in', 'Przyjmowanie towaru na magazyn'), ('access_stock_out', 'Wydawanie towaru z magazynu')], 'verbose_name': 'Przedmiot na magazynie', 'verbose_name_plural': 'Przedmioty na magazynie'},
        ),
    ]
