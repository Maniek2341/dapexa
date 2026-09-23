from django.db import migrations


def sync_role_groups(apps, schema_editor):
    # Użyj tej samej klasy Company, której oczekuje CompanyRoleGroup.
    from app.core.models import Company
    from app.uzytkownik.default_role_groups import ensure_default_role_groups

    for company in Company.objects.all().iterator():
        ensure_default_role_groups(company)


class Migration(migrations.Migration):
    dependencies = [
        ("uzytkownik", "0011_sync_employee_leave_permission"),
        ("serwis", "0016_alter_serviceorder_options_and_more"),
    ]
    operations = [migrations.RunPython(sync_role_groups, migrations.RunPython.noop)]
