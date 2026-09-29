from decimal import Decimal

from django.db import migrations
from django.db.models import DecimalField, Exists, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce


def refresh_work_prices(apps, schema_editor):
    WorkOrder = apps.get_model("praca", "WorkOrder")
    OfferVariant = apps.get_model("oferta_praca", "OfferVariant")
    alias = schema_editor.connection.alias
    variants = OfferVariant.objects.using(alias).filter(
        offer_id=OuterRef("offer_id"), company_id=OuterRef("company_id"),
    )
    selected = variants.filter(is_selected=True).order_by().values("offer_id").annotate(
        netto=Sum("total_netto"), brutto=Sum("total_brutto"),
    )
    money = DecimalField(max_digits=12, decimal_places=2)
    zero = Value(Decimal("0"), output_field=money)
    # Preserve legacy amounts when no variants remain to reconstruct the price.
    WorkOrder.objects.using(alias).filter(Exists(variants)).update(
        total_netto=Coalesce(Subquery(selected.values("netto")), zero, output_field=money),
        total_brutto=Coalesce(Subquery(selected.values("brutto")), zero, output_field=money),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("praca", "0006_alter_workorder_options"),
        ("oferta_praca", "0021_offerimage_file_size_offervariantfile_file_size_and_more"),
    ]

    operations = [migrations.RunPython(refresh_work_prices, migrations.RunPython.noop)]
