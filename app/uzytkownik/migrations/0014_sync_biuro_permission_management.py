from django.db import migrations


def sync_role_groups(apps, schema_editor):
    from app.core.models import Company
    from app.uzytkownik.default_role_groups import ensure_default_role_groups

    for company in Company.objects.all().iterator():
        ensure_default_role_groups(company)


class Migration(migrations.Migration):
    dependencies = [("uzytkownik", "0013_sync_biuro_create_permissions")]
    operations = [migrations.RunPython(sync_role_groups, migrations.RunPython.noop)]
