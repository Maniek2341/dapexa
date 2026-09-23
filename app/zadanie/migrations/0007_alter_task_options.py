from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zadanie', '0006_alter_task_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='task',
            options={'permissions': [('access_task_list', 'Wyświetlanie listy zadań'), ('access_task_create', 'Dodawanie zadań'), ('access_task_delete', 'Usuwanie zadań')], 'verbose_name': 'Zadanie', 'verbose_name_plural': 'Zadania'},
        ),
    ]
