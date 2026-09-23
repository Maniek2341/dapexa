from django.db import migrations


def remove_employee_detail_permission(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    permission = Permission.objects.filter(
        content_type__app_label="urzadzenie",
        codename="access_product_detail",
    ).first()
    if not permission:
        return
    for group in Group.objects.filter(name__startswith="system-company-role:"):
        if group.name.endswith(":employee"):
            group.permissions.remove(permission)


class Migration(migrations.Migration):
    dependencies = [("uzytkownik", "0008_sync_employee_device_detail_permission")]
    operations = [migrations.RunPython(remove_employee_detail_permission, migrations.RunPython.noop)]
