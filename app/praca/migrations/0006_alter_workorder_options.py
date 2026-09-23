from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('praca', '0005_alter_workorder_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='workorder',
            options={'ordering': ['-id'], 'permissions': [('access_workorder_list', 'Wyświetlanie listy prac'), ('access_work_detail', 'Wyświetlanie szczegółów pracy'), ('access_work_assign_workers', 'Przypisywanie pracowników do pracy'), ('access_work_schedule_update', 'Zmienianie terminu realizacji pracy'), ('access_work_mark_ordered', 'Oznaczanie pracy jako zamówionej'), ('access_work_status_update', 'Zmienianie statusu pracy'), ('access_work_finish', 'Kończenie pracy i tworzenie protokołu')], 'verbose_name': 'Praca', 'verbose_name_plural': 'Prace'},
        ),
    ]
