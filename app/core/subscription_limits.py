from django.apps import apps
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save, pre_save


BYTES_PER_GB = 1024 ** 3
STORAGE_USAGE_CACHE_TIMEOUT = 300

FEATURE_LABELS = {
    "faktury": "Faktury",
    "magazyn": "Magazyn",
    "urzadzenia": "Urządzenia",
    "gwarancje": "Gwarancje",
    "protokoly": "Protokoły",
    "serwisy": "Serwisy",
    "klienci": "Klienci",
    "zadania": "Zadania",
    "pojazdy": "Pojazdy",
    "obsluga": "Obsługa",
    "sprzet": "Sprzęt",
    "dokumenty": "Dokumenty",
    "prace": "Prace",
    "oferty": "Oferty",
    "rcp": "RCP",
    "kalendarz": "Kalendarz",
    "rcp_adv": "Zaawansowane RCP",
    "client_app": "Aplikacja klienta",
}


class SubscriptionLimitExceeded(ValidationError):
    pass


FILE_COMPANY_LOOKUPS = {
    "gwarancja.warrantyclaimattachment": "claim__company_id",
    "obsluga.servicecontractmedia": "contract__company_id",
    "protokol.protokolimage": "protokol__company_id",
    "serwis.serviceordermedia": "service__company_id",
}


def get_current_subscription(company_id):
    if not company_id:
        return None
    Subscription = apps.get_model("core", "Subscription")
    return (
        Subscription.objects.filter(company_id=company_id)
        .order_by("-created_at")
        .first()
    )


def get_instance_company_id(instance):
    if instance._meta.label_lower == "core.company":
        return instance.pk

    company_id = getattr(instance, "company_id", None)
    if company_id:
        return company_id

    relation_name = {
        "gwarancja.warrantyclaimattachment": "claim",
        "obsluga.servicecontractmedia": "contract",
        "protokol.protokolimage": "protokol",
        "serwis.serviceordermedia": "service",
    }.get(instance._meta.label_lower)
    if not relation_name:
        return None
    relation = getattr(instance, relation_name, None)
    return getattr(relation, "company_id", None)


def get_company_storage_used_bytes(company_id):
    total = 0
    for model in apps.get_models():
        tracked_fields = [
            field
            for field in model._meta.fields
            if getattr(field, "is_tracked_file_size", False)
        ]
        if not tracked_fields:
            continue

        lookup = FILE_COMPANY_LOOKUPS.get(model._meta.label_lower)
        if lookup is None:
            if model._meta.label_lower == "core.company":
                lookup = "pk"
            else:
                try:
                    model._meta.get_field("company")
                except Exception:
                    continue
                lookup = "company_id"

        queryset = model._default_manager.filter(**{lookup: company_id})
        for file_field in tracked_fields:
            size_field_name = f"{file_field.name}_size"
            missing_sizes = (
                queryset.filter(**{size_field_name: 0})
                .exclude(**{file_field.name: ""})
                .exclude(**{f"{file_field.name}__isnull": True})
                .only("pk", file_field.name, size_field_name)
            )
            for instance in missing_sizes.iterator():
                try:
                    actual_size = getattr(instance, file_field.name).size
                except (FileNotFoundError, OSError, ValueError):
                    continue
                if actual_size:
                    model._default_manager.filter(pk=instance.pk).update(
                        **{size_field_name: actual_size}
                    )

        size_fields = [f"{field.name}_size" for field in tracked_fields]
        values = queryset.aggregate(
            **{f"total_{name}": Sum(name) for name in size_fields}
        )
        total += sum(value or 0 for value in values.values())
    return total


def _storage_usage_cache_key(company_id):
    return f"company:{company_id}:storage-usage"


def get_cached_company_storage_used_bytes(company_id):
    if not company_id:
        return 0
    key = _storage_usage_cache_key(company_id)
    cached_value = cache.get(key)
    if cached_value is not None:
        return cached_value
    total = get_company_storage_used_bytes(company_id)
    cache.set(key, total, STORAGE_USAGE_CACHE_TIMEOUT)
    return total


def invalidate_company_storage_cache(sender, instance, **kwargs):
    company_id = get_instance_company_id(instance)
    if company_id:
        cache.delete(_storage_usage_cache_key(company_id))


def enforce_storage_limit(instance, size_field_name, new_size):
    company_id = get_instance_company_id(instance)
    subscription = get_current_subscription(company_id)
    if not subscription or subscription.max_storage_bytes is None:
        return

    current_usage = get_company_storage_used_bytes(company_id)
    old_size = 0
    if instance.pk:
        old_size = (
            type(instance)._default_manager.filter(pk=instance.pk)
            .values_list(size_field_name, flat=True)
            .first()
            or 0
        )

    delta = new_size - old_size
    pending_delta = getattr(instance, "_pending_storage_delta", 0)
    projected_usage = current_usage + pending_delta + delta
    if projected_usage > subscription.max_storage_bytes:
        used_gb = current_usage / BYTES_PER_GB
        raise SubscriptionLimitExceeded(
            f"Limit przestrzeni pakietu został przekroczony. "
            f"Wykorzystano {used_gb:.2f} GB z {subscription.max_storage_gb} GB."
        )
    instance._pending_storage_delta = pending_delta + delta


COUNT_LIMITS = {
    "core.paneluser": ("max_users", "użytkowników"),
    "klient.client": ("max_clients", "klientów"),
    "protokol.protocol": ("max_protocols", "protokołów"),
}


def enforce_count_limit(sender, instance, raw=False, **kwargs):
    if raw or not instance._state.adding:
        return

    limit_config = COUNT_LIMITS.get(sender._meta.label_lower)
    if not limit_config:
        return
    if (
        sender._meta.label_lower == "core.paneluser"
        and instance.role == instance.Role.CLIENT
    ):
        return

    company_id = getattr(instance, "company_id", None)
    subscription = get_current_subscription(company_id)
    if not subscription:
        return

    limit_name, resource_name = limit_config
    limit = getattr(subscription, limit_name)
    if limit is None:
        return

    queryset = sender._default_manager.filter(company_id=company_id)
    if sender._meta.label_lower == "core.paneluser":
        queryset = queryset.exclude(role=instance.Role.CLIENT)
    if queryset.count() >= limit:
        raise SubscriptionLimitExceeded(
            f"Pakiet {subscription.get_package_display()} pozwala maksymalnie na "
            f"{limit} {resource_name}."
        )


def register_subscription_limit_signals():
    for model_label in COUNT_LIMITS:
        model = apps.get_model(model_label)
        pre_save.connect(
            enforce_count_limit,
            sender=model,
            dispatch_uid=f"subscription_count_limit_{model_label}",
        )

    for model in apps.get_models():
        if not any(
            getattr(field, "is_tracked_file_size", False)
            for field in model._meta.fields
        ):
            continue
        post_save.connect(
            invalidate_company_storage_cache,
            sender=model,
            dispatch_uid=f"subscription_storage_cache_save_{model._meta.label_lower}",
        )
        post_delete.connect(
            invalidate_company_storage_cache,
            sender=model,
            dispatch_uid=f"subscription_storage_cache_delete_{model._meta.label_lower}",
        )
