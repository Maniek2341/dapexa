from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('praca', '0004_alter_workorder_planned_end_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='workorder',
            options={'ordering': ['-id'], 'permissions': [('access_workorder_list', 'Dostęp do widoku: workorder list'), ('access_work_detail', 'Dostęp do widoku: work detail'), ('access_work_assign_workers', 'Dostęp do widoku: work assign workers'), ('access_work_schedule_update', 'Dostęp do widoku: work schedule update'), ('access_work_mark_ordered', 'Dostęp do widoku: work mark ordered'), ('access_work_status_update', 'Dostęp do widoku: work status update'), ('access_work_finish', 'Dostęp do widoku: work finish')], 'verbose_name': 'Praca', 'verbose_name_plural': 'Prace'},
        ),
    ]
