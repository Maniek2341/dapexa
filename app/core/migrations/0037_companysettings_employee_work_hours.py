from datetime import time

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0036_stripe_webhook_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysettings",
            name="default_employee_work_start_time",
            field=models.TimeField(
                default=time(7, 0),
                verbose_name="Domyślna godzina rozpoczęcia pracy pracownika",
            ),
        ),
        migrations.AddField(
            model_name="companysettings",
            name="default_employee_work_end_time",
            field=models.TimeField(
                default=time(15, 0),
                verbose_name="Domyślna godzina zakończenia pracy pracownika",
            ),
        ),
    ]
