from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('urlop', '0006_alter_leaverequest_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='leaverequest',
            options={'permissions': [('access_urlop_add', 'Składanie wniosków urlopowych'), ('access_leave_type_add', 'Dodawanie rodzajów urlopu'), ('access_leave_type_edit', 'Edytowanie rodzajów urlopu'), ('access_leave_type_delete', 'Usuwanie rodzajów urlopu'), ('access_leave_type_list', 'Wyświetlanie rodzajów urlopu'), ('access_leave_allowance_list', 'Wyświetlanie limitów urlopowych'), ('access_generate_leave_allowances', 'Generowanie limitów urlopowych'), ('access_hr_leave_list', 'Wyświetlanie wniosków urlopowych pracowników'), ('access_hr_leave_approve', 'Zatwierdzanie wniosków urlopowych'), ('access_hr_leave_reject', 'Odrzucanie wniosków urlopowych'), ('access_hr_leave_pdf', 'Generowanie wniosku urlopowego w formacie PDF')]},
        ),
    ]
