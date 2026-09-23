from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('urlop', '0005_alter_leaverequest_options_alter_leavetype_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='leaverequest',
            options={'permissions': [('access_urlop_add', 'Dostęp do widoku: urlop add'), ('access_leave_type_add', 'Dostęp do widoku: leave type add'), ('access_leave_type_edit', 'Dostęp do widoku: leave type edit'), ('access_leave_type_delete', 'Dostęp do widoku: leave type delete'), ('access_leave_type_list', 'Dostęp do widoku: leave type list'), ('access_leave_allowance_list', 'Dostęp do widoku: leave allowance list'), ('access_generate_leave_allowances', 'Dostęp do widoku: generate leave allowances'), ('access_hr_leave_list', 'Dostęp do widoku: hr leave list'), ('access_hr_leave_approve', 'Dostęp do widoku: hr leave approve'), ('access_hr_leave_reject', 'Dostęp do widoku: hr leave reject'), ('access_hr_leave_pdf', 'Dostęp do widoku: hr leave pdf')]},
        ),
    ]
