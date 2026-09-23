from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zadanie', '0005_alter_task_assigned_role'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='task',
            options={'permissions': [('access_task_list', 'Dostęp do widoku: task list'), ('access_task_create', 'Dostęp do widoku: task create'), ('access_task_delete', 'Dostęp do widoku: task delete')], 'verbose_name': 'Zadanie', 'verbose_name_plural': 'Zadania'},
        ),
    ]
