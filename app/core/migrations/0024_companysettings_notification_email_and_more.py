import app.core.notification_preferences
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_remove_companysettings_service_download_number_prefix_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='companysettings',
            name='notification_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Firmowy adres powiadomień'),
        ),
        migrations.AddField(
            model_name='companysettings',
            name='notification_modules',
            field=models.JSONField(blank=True, default=app.core.notification_preferences.default_notification_modules, verbose_name='Moduły wysyłające powiadomienia firmowe'),
        ),
        migrations.AddField(
            model_name='paneluser',
            name='email_notification_modules',
            field=models.JSONField(blank=True, default=app.core.notification_preferences.default_notification_modules, verbose_name='Powiadomienia e-mail z modułów'),
        ),
    ]
