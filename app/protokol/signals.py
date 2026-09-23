from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from app.protokol.models import ProtocolActivity, Protocol, ProtokolImage


@receiver(post_save, sender=Protocol)
def protocol_created_activity(sender, instance, created, **kwargs):
    if created:
        ProtocolActivity.objects.create(
            company=instance.company,
            protocol=instance,
            type=ProtocolActivity.Type.SYSTEM,
            title="Utworzono protokół",
            description=f"Numer: {instance.number}",
            created_by=instance.pracownik
        )


@receiver(pre_save, sender=Protocol)
def protocol_status_activity(sender, instance, **kwargs):
    if not instance.pk:
        return

    old = Protocol.objects.filter(pk=instance.pk).first()
    if not old:
        return

    if old.status != instance.status:
        ProtocolActivity.objects.create(
            company=instance.company,
            protocol=instance,
            type=ProtocolActivity.Type.STATUS,
            title="Zmiana statusu",
            description=f"{old.get_status_display()} → {instance.get_status_display()}",
            created_by=instance.pracownik
        )


    if not old.signed_by_client and instance.signed_by_client:
        ProtocolActivity.objects.create(
            company=instance.company,
            protocol=instance,
            type=ProtocolActivity.Type.SIGNATURE,
            title="Podpis klienta",
            description="Klient podpisał protokół",
            created_by=instance.pracownik
        )


@receiver(post_save, sender=ProtokolImage)
def protocol_file_added(sender, instance, created, **kwargs):
    if created:
        ProtocolActivity.objects.create(
            company=instance.protokol.company,
            protocol=instance.protokol,
            type=ProtocolActivity.Type.FILE,
            title="Dodano plik",
            description=instance.filename()
        )
