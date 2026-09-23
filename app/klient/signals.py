from django.db.models.signals import post_delete
from django.dispatch import receiver

from app.klient.models import ClientLocation
from app.serwis.models import ServiceOrder


@receiver(post_delete, sender=ClientLocation)
def update_services_after_location_delete(sender, instance, **kwargs):
    services = ServiceOrder.objects.filter(location=instance)

    for service in services:
        service.location = None

        # 🔥 fallback adresu
        if service.client.shipping_address:
            service.address = service.client.shipping_address
        elif service.client.billing_address:
            service.address = service.client.billing_address
        else:
            service.address = None

        service.save(update_fields=["location", "address"])