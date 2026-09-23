import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_alter_paneluser_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='default_work_end_time',
            field=models.TimeField(default=datetime.time(15, 0), verbose_name='Domyślna godzina zakończenia pracy'),
        ),
        migrations.AddField(
            model_name='companysettings',
            name='default_work_start_time',
            field=models.TimeField(default=datetime.time(7, 0), verbose_name='Domyślna godzina rozpoczęcia pracy'),
        ),
    ]
