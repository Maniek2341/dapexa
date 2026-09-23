from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rcp', '0005_alter_timeentry_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='timeentry',
            options={'ordering': ['-date', '-created_at'], 'permissions': [('access_time_entry_create', 'Dodawanie wpisów czasu pracy'), ('access_time_entry_list', 'Wyświetlanie ewidencji czasu pracy'), ('access_time_entry_update', 'Edytowanie wpisów czasu pracy'), ('access_time_entry_delete', 'Usuwanie wpisów czasu pracy'), ('access_time_entry_request_edit', 'Składanie wniosku o zmianę czasu pracy'), ('access_time_entry_request_missing', 'Zgłaszanie brakującego wpisu czasu pracy'), ('access_time_entry_request_edit_single', 'Edytowanie wniosku dotyczącego czasu pracy'), ('access_time_entry_request_approve', 'Zatwierdzanie wniosków dotyczących czasu pracy'), ('access_time_entry_request_reject', 'Odrzucanie wniosków dotyczących czasu pracy'), ('access_time_entry_request_list', 'Wyświetlanie wniosków dotyczących czasu pracy'), ('access_time_entry_pdf', 'Generowanie ewidencji czasu pracy w formacie PDF')], 'verbose_name': 'Rejestracja czasu pracy', 'verbose_name_plural': 'Rejestracja czasu pracy'},
        ),
    ]
