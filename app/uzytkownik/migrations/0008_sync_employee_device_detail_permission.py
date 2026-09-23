from django.db import migrations


def sync_default_role_groups(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    # Importing the project helper keeps the system-group rules in one place.
    from app.uzytkownik.default_role_groups import ensure_default_role_groups

    for company in Company.objects.all().iterator():
        ensure_default_role_groups(company)


class Migration(migrations.Migration):
    dependencies = [
        ("uzytkownik", "0007_employeecontract"),
    ]

    operations = [migrations.RunPython(sync_default_role_groups, migrations.RunPython.noop)]
