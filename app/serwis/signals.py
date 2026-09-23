from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from app.serwis.models import ServiceOrder, ServiceActivity
from app.serwis.activity import log_service_activity


def _label(choices, value: str | None) -> str:
    if not value:
        return "—"
    return dict(choices).get(value, value)  # fallback gdy brak w choices


@receiver(pre_save, sender=ServiceOrder)
def serviceorder_capture_old(sender, instance: ServiceOrder, **kwargs):
    if not instance.pk:
        instance._old_status = None
        instance._old_status_zgrania = None
        return

    old = (
        ServiceOrder.objects
        .filter(pk=instance.pk)
        .values("status", "status_zgrania")
        .first()
    )
    instance._old_status = old["status"] if old else None
    instance._old_status_zgrania = old["status_zgrania"] if old else None


@receiver(post_save, sender=ServiceOrder)
def serviceorder_log_changes(sender, instance: ServiceOrder, created: bool, **kwargs):
    # STATUS
    old_status = getattr(instance, "_old_status", None)
    if old_status and instance.status != old_status:
        old_label = _label(ServiceOrder.Status.choices, old_status)
        new_label = _label(ServiceOrder.Status.choices, instance.status)

        log_service_activity(
            company=instance.company,
            service=instance,
            type=ServiceActivity.Type.STATUS,
            title="Zmieniono status",
            description=f"{old_label} → {new_label}",
            user=None,
        )

    # STATUS OBSŁUGI
    old_z = getattr(instance, "_old_status_zgrania", None)
    if old_z and instance.status_zgrania != old_z:
        old_label = _label(ServiceOrder.StatusZgrania.choices, old_z)
        new_label = _label(ServiceOrder.StatusZgrania.choices, instance.status_zgrania)

        log_service_activity(
            company=instance.company,
            service=instance,
            type=ServiceActivity.Type.STATUS,
            title="Zmieniono status obsługi",
            description=f"{old_label} → {new_label}",
            user=None,
        )
