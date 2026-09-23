from django.db import migrations


def sync_role_groups(apps, schema_editor):
    # ensure_default_role_groups korzysta z bieżących modeli relacyjnych,
    # dlatego nie przekazujemy mu historycznego obiektu z apps.get_model().
    from app.core.models import Company
    from app.uzytkownik.default_role_groups import ensure_default_role_groups

    for company in Company.objects.all().iterator():
        ensure_default_role_groups(company)


class Migration(migrations.Migration):
    dependencies = [("uzytkownik", "0010_sync_protocol_service_permission")]
    operations = [migrations.RunPython(sync_role_groups, migrations.RunPython.noop)]
