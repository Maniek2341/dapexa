from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from app.oferta_praca.models import OfferVariant
from app.praca.models import WorkOrder


@receiver(post_save, sender=OfferVariant)
@receiver(post_delete, sender=OfferVariant)
def sync_work_prices(sender, instance, using, **kwargs):
    if kwargs.get("raw"):
        return

    with transaction.atomic(using=using):
        # Serialize recalculations for the same work, including edits to
        # different variants. Sum persisted values, not a cached offer relation.
        work = WorkOrder.objects.using(using).select_for_update().filter(
            offer_id=instance.offer_id, company_id=instance.company_id,
        ).first()
        if work is None:
            return

        totals = OfferVariant.objects.using(using).filter(
            offer_id=instance.offer_id, company_id=instance.company_id,
            is_selected=True,
        ).aggregate(netto=Sum("total_netto"), brutto=Sum("total_brutto"))
        WorkOrder.objects.using(using).filter(pk=work.pk).update(
            total_netto=totals["netto"] or Decimal("0"),
            total_brutto=totals["brutto"] or Decimal("0"),
        )
