from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import Supplier


@receiver(post_migrate)
def ensure_builtin_suppliers(sender, **kwargs):
    if sender.name != "app.dostawcy":
        return
    for slug, name in (("hurton", "Hurton"), ("onninen", "Onninen")):
        Supplier.objects.get_or_create(slug=slug, defaults={"name": name})
