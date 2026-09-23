from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('protokol', '0018_alter_protocol_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='protocol',
            name='rodzaj_prac',
            field=models.CharField(choices=[('naprawa', 'Naprawa'), ('rozbudowa', 'Rozbudowa'), ('montaz', 'Montaż'), ('przeglad', 'Przegląd'), ('zgranie', 'Obsługa'), ('praca', 'Praca'), ('dostawa', 'Dostawa')], default='naprawa', max_length=20),
        ),
    ]
