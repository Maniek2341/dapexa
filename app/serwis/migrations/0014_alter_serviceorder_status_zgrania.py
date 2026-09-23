from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serwis', '0013_alter_serviceorder_options_alter_serviceorder_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='serviceorder',
            name='status_zgrania',
            field=models.CharField(blank=True, choices=[('new', 'Nowa'), ('nothind', 'Brak materiału'), ('done', 'Zakończona'), ('in_progress', 'W trakcie'), ('send', 'Zakończona i przekazana')], default='new', max_length=20, verbose_name='Status obsługi'),
        ),
    ]
