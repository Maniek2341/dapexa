from django.db import migrations


def update_view_permission_names(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    database_alias = schema_editor.connection.alias

    for model in apps.get_models():
        for codename, description in model._meta.permissions:
            if not codename.startswith("access_"):
                continue

            Permission.objects.using(database_alias).filter(
                content_type__app_label=model._meta.app_label,
                content_type__model=model._meta.model_name,
                codename=codename,
            ).update(name=description)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_alter_paneluser_options"),
        ("dokument", "0004_alter_document_options"),
        ("gwarancja", "0006_alter_warrantyclaim_options"),
        ("klient", "0013_alter_client_options"),
        ("magazyn", "0007_alter_stockitem_options"),
        ("obsluga", "0008_alter_servicecontract_options"),
        ("oferta_praca", "0020_alter_offer_options"),
        ("pojazd", "0007_alter_vehicle_options"),
        ("praca", "0006_alter_workorder_options"),
        ("protokol", "0018_alter_protocol_options"),
        ("rcp", "0006_alter_timeentry_options"),
        ("serwis", "0011_alter_serviceorder_options"),
        ("sprzet", "0007_alter_tool_options"),
        ("urlop", "0007_alter_leaverequest_options"),
        ("urzadzenie", "0007_alter_product_options"),
        ("zadanie", "0007_alter_task_options"),
    ]

    operations = [
        migrations.RunPython(
            update_view_permission_names,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
