import stripe
from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction

from app.core.models import Address, Company, PanelUser, Subscription


def _stripe_dict(resource):
    if isinstance(resource, dict):
        return resource
    converter = getattr(type(resource), "to_dict", None)
    return converter() if callable(converter) else {}


def delete_company_from_stripe(company):
    """Remove the company's Stripe customers, which immediately cancels subscriptions."""
    subscriptions = [
        (subscription_id, customer_id)
        for subscription_id, customer_id in (
            Subscription.objects.filter(company=company)
            .values_list("stripe_subscription_id", "stripe_customer_id")
        )
        if subscription_id or customer_id
    ]
    customer_ids = {
        customer_id
        for _subscription_id, customer_id in subscriptions
        if customer_id
    }
    subscription_ids_without_customer = [
        subscription_id
        for subscription_id, customer_id in subscriptions
        if subscription_id and not customer_id
    ]

    if not customer_ids and not subscriptions:
        return
    if not settings.STRIPE_SECRET_KEY:
        raise ValueError("Brak konfiguracji połączenia ze Stripe.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.api_version = settings.STRIPE_API_VERSION

    for subscription_id, customer_id in subscriptions:
        if customer_id:
            continue
        if not subscription_id:
            continue
        stripe_subscription = _stripe_dict(
            stripe.Subscription.retrieve(subscription_id)
        )
        stripe_customer = stripe_subscription.get("customer")
        if isinstance(stripe_customer, dict):
            stripe_customer = stripe_customer.get("id")
        if stripe_customer:
            customer_ids.add(stripe_customer)
            subscription_ids_without_customer.remove(subscription_id)

    for customer_id in customer_ids:
        customer = _stripe_dict(stripe.Customer.retrieve(customer_id))
        if not customer.get("deleted"):
            # Stripe cancels all active subscriptions when the customer is deleted.
            deleted_customer = _stripe_dict(stripe.Customer.delete(customer_id))
            if not deleted_customer.get("deleted"):
                raise ValueError("Stripe nie potwierdził usunięcia danych klienta.")

    for subscription_id in subscription_ids_without_customer:
        deleted_subscription = _stripe_dict(
            stripe.Subscription.delete(subscription_id)
        )
        if deleted_subscription.get("status") != Subscription.STATUS_CANCELED:
            raise ValueError("Stripe nie potwierdził anulowania subskrypcji.")


def _company_address_ids(company):
    address_ids = set()
    if company.main_address_id:
        address_ids.add(company.main_address_id)

    for model in apps.get_models():
        try:
            model._meta.get_field("company")
        except FieldDoesNotExist:
            continue

        address_fields = [
            field for field in model._meta.fields
            if isinstance(field, models.ForeignKey)
            and field.remote_field.model is Address
        ]
        if not address_fields:
            continue

        rows = model._default_manager.filter(company_id=company.pk)
        for field in address_fields:
            address_ids.update(
                rows.exclude(**{f"{field.name}__isnull": True})
                .values_list(field.attname, flat=True)
            )
    return address_ids


def _delete_unreferenced_addresses(address_ids):
    for address in Address.objects.filter(pk__in=address_ids):
        still_referenced = any(
            relation.related_model._base_manager.filter(
                **{relation.field.name: address.pk}
            ).exists()
            for relation in Address._meta.related_objects
            if relation.one_to_one or relation.one_to_many
        )
        if not still_referenced:
            address.delete()


@transaction.atomic
def delete_company_data(company_id):
    """Permanently remove company records, its users, and unreferenced addresses."""
    company = Company.objects.select_for_update().get(pk=company_id)
    user_ids = list(
        PanelUser.objects.filter(company_id=company_id).values_list("pk", flat=True)
    )
    address_ids = _company_address_ids(company)

    # Company-owned records and uploaded files are removed by Django cascades
    # and the Company pre-delete cleanup signal.
    company.delete()
    PanelUser.objects.filter(pk__in=user_ids).delete()
    _delete_unreferenced_addresses(address_ids)
