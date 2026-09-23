from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rcp', '0004_alter_timeentry_work_mode_timeentryrequest'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='timeentry',
            options={'ordering': ['-date', '-created_at'], 'permissions': [('access_time_entry_create', 'Dostęp do widoku: time entry create'), ('access_time_entry_list', 'Dostęp do widoku: time entry list'), ('access_time_entry_update', 'Dostęp do widoku: time entry update'), ('access_time_entry_delete', 'Dostęp do widoku: time entry delete'), ('access_time_entry_request_edit', 'Dostęp do widoku: time entry request edit'), ('access_time_entry_request_missing', 'Dostęp do widoku: time entry request missing'), ('access_time_entry_request_edit_single', 'Dostęp do widoku: time entry request edit single'), ('access_time_entry_request_approve', 'Dostęp do widoku: time entry request approve'), ('access_time_entry_request_reject', 'Dostęp do widoku: time entry request reject'), ('access_time_entry_request_list', 'Dostęp do widoku: time entry request list'), ('access_time_entry_pdf', 'Dostęp do widoku: time entry pdf')], 'verbose_name': 'Rejestracja czasu pracy', 'verbose_name_plural': 'Rejestracja czasu pracy'},
        ),
    ]
