from django.db import migrations


def sync_role_groups(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    from app.uzytkownik.default_role_groups import ensure_default_role_groups

    for company in Company.objects.all().iterator():
        ensure_default_role_groups(company)


class Migration(migrations.Migration):
    dependencies = [("uzytkownik", "0009_remove_employee_product_detail_permission")]
    operations = [migrations.RunPython(sync_role_groups, migrations.RunPython.noop)]
