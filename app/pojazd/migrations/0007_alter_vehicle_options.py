from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pojazd', '0006_alter_vehicle_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='vehicle',
            options={'permissions': [('access_vehicle_create', 'Dodawanie pojazdów'), ('access_vehicle_detail', 'Wyświetlanie szczegółów pojazdu'), ('access_vehicle_list', 'Wyświetlanie listy pojazdów'), ('access_vehicle_update', 'Edytowanie pojazdów'), ('access_vehicle_delete', 'Usuwanie pojazdów'), ('access_vehicle_event_create', 'Dodawanie zdarzeń pojazdu'), ('access_vehicle_event_delete', 'Usuwanie zdarzeń pojazdu'), ('access_vehicle_event_update', 'Edytowanie zdarzeń pojazdu')], 'verbose_name': 'Pojazd', 'verbose_name_plural': 'Pojazdy'},
        ),
    ]
