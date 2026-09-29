# app/core/views_stripe.py
import json
import logging
from datetime import UTC, datetime
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

import stripe

from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from app.core.models import Subscription, StripeWebhookEvent
from app.core.subscription_lifecycle import (
    clear_scheduled_cancellation,
    mark_cancellation_scheduled,
    sync_cancellation_state,
)
from app.core.validators import is_valid_polish_nip, normalize_nip

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION

STRIPE_PRICE_IDS = settings.STRIPE_PRICE_IDS

STRIPE_PLAN_BY_PRICE_ID = {
    price_id: (package, billing_period)
    for package, prices in STRIPE_PRICE_IDS.items()
    for billing_period, price_id in prices.items()
}

EXTRA_USER_LOOKUP_PREFIX = "business_manager_extra_user"


def stripe_data(resource):
    """Convert Stripe SDK resources to regular dictionaries for safe `.get()` use."""
    if isinstance(resource, dict):
        return resource
    to_dict = getattr(type(resource), "to_dict", None)
    return resource.to_dict() if callable(to_dict) else resource


def get_extra_user_price_id(billing_period):
    amounts = settings.STRIPE_EXTRA_USER_UNIT_AMOUNTS
    amount = amounts[billing_period]
    interval = "month" if billing_period == Subscription.BILLING_MONTHLY else "year"
    lookup_key = f"{EXTRA_USER_LOOKUP_PREFIX}_{billing_period}_{amount}"

    prices = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1)
    if prices.data:
        return prices.data[0].id

    price = stripe.Price.create(
        currency="pln",
        unit_amount=amount,
        recurring={"interval": interval, "usage_type": "licensed"},
        product_data={
            "name": "Dodatkowy użytkownik Business Manager",
            "unit_label": "użytkownik",
        },
        lookup_key=lookup_key,
        nickname=f"Dodatkowy użytkownik ({billing_period})",
        idempotency_key=lookup_key,
    )
    return price.id


def sync_extra_users_from_stripe(subscription, stripe_subscription):
    stripe_subscription = stripe_data(stripe_subscription)
    main_price_id = None
    extra_quantity = 0
    extra_item_id = ""

    for item in stripe_subscription.get("items", {}).get("data", []):
        price = item.get("price", {}) or {}
        lookup_key = price.get("lookup_key") or ""
        is_extra_item = (
            item.get("id") == subscription.stripe_extra_user_item_id
            or lookup_key.startswith(EXTRA_USER_LOOKUP_PREFIX)
        )
        if is_extra_item:
            extra_quantity = item.get("quantity") or 0
            extra_item_id = item.get("id") or ""
        elif price.get("id") in STRIPE_PLAN_BY_PRICE_ID:
            main_price_id = price.get("id")
        elif not main_price_id:
            main_price_id = price.get("id")

    subscription.stripe_price_id = main_price_id or subscription.stripe_price_id
    plan = STRIPE_PLAN_BY_PRICE_ID.get(main_price_id)
    if plan:
        subscription.package, subscription.billing_period = plan
    subscription.extra_users = extra_quantity
    subscription.stripe_extra_user_item_id = extra_item_id


def company_billing_errors(company):
    errors = []
    if not company.name:
        errors.append("nazwa firmy")
    if not company.nip:
        errors.append("NIP")
    elif not is_valid_polish_nip(company.nip):
        errors.append("prawidłowy NIP")
    address = company.main_address
    if not address or not address.street or not address.postcode or not address.city:
        errors.append("pełny adres firmy")
    return errors


def sync_stripe_customer_billing_data(subscription, company, email):
    nip = normalize_nip(company.nip)
    address = company.main_address
    customer_data = {
        "name": company.name,
        "email": company.email or email,
        "preferred_locales": ["pl"],
        "address": {
            "line1": " ".join(
                part for part in [address.street, address.street_no] if part
            ),
            "postal_code": address.postcode,
            "city": address.city,
            "country": "PL",
        },
        "metadata": {"company_id": str(company.pk), "nip": nip},
    }
    if subscription.stripe_customer_id:
        customer = stripe.Customer.modify(
            subscription.stripe_customer_id,
            **customer_data,
        )
    else:
        customer = stripe.Customer.create(**customer_data)
        subscription.stripe_customer_id = customer.id

    tax_ids = stripe.Customer.list_tax_ids(customer.id, limit=100)
    matching_tax_id = None
    for tax_id in tax_ids.data:
        if tax_id.type != "pl_nip":
            continue
        if normalize_nip(tax_id.value) == nip:
            matching_tax_id = tax_id
        else:
            stripe.Customer.delete_tax_id(customer.id, tax_id.id)
    if not matching_tax_id:
        stripe.Customer.create_tax_id(
            customer.id,
            type="pl_nip",
            value=nip,
        )
    return customer.id


def create_plan_checkout_session(request, subscription, package, billing_period):
    """Reuse an open Checkout Session and serialize creations per subscription."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    target_price_id = STRIPE_PRICE_IDS[package][billing_period]
    if subscription.stripe_checkout_session_id:
        existing = stripe.checkout.Session.retrieve(
            subscription.stripe_checkout_session_id
        )
        existing_data = stripe_data(existing)
        if existing_data.get("status") == "open":
            metadata = existing_data.get("metadata", {}) or {}
            if (
                metadata.get("package") == package
                and metadata.get("billing_period") == billing_period
            ):
                return existing
            stripe.checkout.Session.expire(existing.id)
        elif existing_data.get("status") == "complete":
            return existing

    domain_url = getattr(settings, "DOMAIN_URL", None) or request.build_absolute_uri("/").rstrip("/")
    params = {
        "mode": "subscription",
        "line_items": [{"price": target_price_id, "quantity": 1}],
        "success_url": domain_url + reverse("checkout_success") + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": domain_url + reverse("checkout_cancel"),
        "client_reference_id": str(subscription.pk),
        "metadata": {
            "package": package,
            "billing_period": billing_period,
            "local_subscription_id": str(subscription.pk),
        },
    }
    if subscription.stripe_customer_id:
        params["customer"] = subscription.stripe_customer_id
    else:
        params["customer_email"] = request.user.email

    attempt = subscription.stripe_checkout_attempt + 1
    session = stripe.checkout.Session.create(
        **params,
        idempotency_key=f"plan-checkout-{subscription.pk}-{attempt}",
    )
    subscription.stripe_checkout_session_id = session.id
    subscription.stripe_checkout_attempt = attempt
    subscription.save(update_fields=[
        "stripe_checkout_session_id",
        "stripe_checkout_attempt",
        "updated_at",
    ])
    return session


# --- POMOCNICZE ---

def unix_to_dt(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)


# --- CHECKOUT SESSION ---

@require_POST
@login_required
def create_checkout_session(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    package = data.get("package")
    billing_period = data.get("billing_period")  # monthly / yearly
    if request.user.role != request.user.Role.OWNER or not request.user.company_id:
        return JsonResponse({"error": "Tylko właściciel firmy może rozpocząć płatność."}, status=403)

    if package not in STRIPE_PRICE_IDS:
        return HttpResponseBadRequest("Unknown package")

    if billing_period not in STRIPE_PRICE_IDS[package]:
        return HttpResponseBadRequest("Unknown billing period")

    try:
        with transaction.atomic():
            subscription = (
                Subscription.objects.select_for_update()
                .filter(company_id=request.user.company_id)
                .order_by("-created_at")
                .first()
            )
            if not subscription or subscription.cancel_at_period_end:
                return JsonResponse({"error": "Nie znaleziono subskrypcji do zmiany."}, status=400)
            if subscription.stripe_subscription_id:
                return JsonResponse(
                    {"error": "Subskrypcja ma już powiązanie ze Stripe. Użyj zmiany pakietu."},
                    status=409,
                )
            billing_errors = company_billing_errors(subscription.company)
            if billing_errors:
                return JsonResponse({"error": "Uzupełnij dane do faktury: " + ", ".join(billing_errors)}, status=400)
            stripe_customer_id = sync_stripe_customer_billing_data(
                subscription, subscription.company, request.user.email
            )
            subscription.stripe_customer_id = stripe_customer_id
            subscription.save(update_fields=["stripe_customer_id", "updated_at"])
            checkout_session = create_plan_checkout_session(
                request, subscription, package, billing_period
            )
    except stripe.error.StripeError as e:
        logger.exception("Error creating Stripe Checkout Session")
        return JsonResponse({"error": getattr(e, "user_message", None) or "Nie udało się rozpocząć płatności."}, status=400)

    return JsonResponse({"session_id": checkout_session.id})



def checkout_success(request):
    """
    DEV: ogarniamy wszystko bez webhooka – na podstawie session_id z URL.
    PROD: dalej możesz używać webhooka, a tutaj tylko prosty ekran OK.
    """
    session_id = request.GET.get("session_id")

    if settings.DEBUG and session_id:
        try:
            # Pobieramy pełną sesję wraz z subskrypcją
            session = stripe.checkout.Session.retrieve(session_id)
            # Używamy tej samej logiki, co w webhooku:
            handle_checkout_session_completed(session)
        except Exception as e:
            # na dev po prostu wyświetlimy błąd w szablonie
            return render(
                request,
                "app/payments/success.html",
                {"error": f"Błąd przy przetwarzaniu sesji Stripe: {e}"},
            )

    # Nawet jeśli jesteśmy na produkcji (DEBUG=False) – po prostu pokazujemy sukces.
    return render(request, "app/payments/success.html")

def checkout_cancel(request):
    return render(request, "app/payments/cancel.html")


@require_POST
@login_required
def create_billing_portal_session(request):
    if request.user.role != request.user.Role.OWNER or not request.user.company_id:
        raise PermissionDenied("Tylko właściciel firmy może zarządzać rozliczeniami.")
    return redirect("billing_management")


# --- WEBHOOK STRIPE ---

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    if not endpoint_secret:
        return HttpResponseBadRequest("Missing STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret,
        )
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError:
        return HttpResponseBadRequest("Invalid signature")

    event = stripe_data(event)
    event_id = event.get("id")
    event_type = event.get("type")
    event_created = event.get("created")
    data_object = event.get("data", {}).get("object", {})
    if not event_id or not event_type:
        return HttpResponseBadRequest("Invalid event")

    with transaction.atomic():
        webhook_event, _ = StripeWebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "event_created": event_created or 0,
            },
        )
        webhook_event = StripeWebhookEvent.objects.select_for_update().get(pk=webhook_event.pk)
        if webhook_event.processed_at:
            return JsonResponse({"status": "duplicate"})

        if event_type == "checkout.session.completed":
            handle_checkout_session_completed(data_object, event_created=event_created)
        elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            handle_subscription_updated(data_object, event_created=event_created)
        elif event_type == "customer.subscription.deleted":
            handle_subscription_updated(data_object, deleted=True, event_created=event_created)
        elif event_type in {
            "invoice.paid",
            "invoice.payment_failed",
            "invoice.payment_action_required",
        }:
            handle_invoice_event(
                data_object,
                payment_failed=event_type == "invoice.payment_failed",
                payment_action_required=(
                    event_type == "invoice.payment_action_required"
                ),
            )

        webhook_event.processed_at = datetime.now(tz=UTC)
        webhook_event.save(update_fields=["processed_at"])

    return JsonResponse({"status": "success"})


def handle_checkout_session_completed(session, event_created=None):
    """
    Tworzy/aktualizuje Subscription, Company, PanelUser na podstawie checkout.session.completed
    """
    session = stripe_data(session)
    logger.info("Handling checkout.session.completed for session: %s", session.get("id"))
    if session.get("mode") != "subscription" or session.get("status") != "complete":
        logger.warning("Ignoring incomplete or non-subscription Checkout Session %s", session.get("id"))
        return
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    metadata = session.get("metadata", {}) or {}

    local_subscription_id = metadata.get("local_subscription_id")
    if not local_subscription_id or not subscription_id:
        logger.error("Checkout Session %s has no local subscription reference", session.get("id"))
        return
    try:
        sub_obj = Subscription.objects.select_for_update().get(pk=local_subscription_id)
    except (Subscription.DoesNotExist, ValueError):
        logger.error("Unknown local subscription: %s", local_subscription_id)
        return
    if sub_obj.stripe_customer_id and customer_id != sub_obj.stripe_customer_id:
        logger.error("Checkout Session %s has an unexpected customer", session.get("id"))
        return
    if (
        sub_obj.stripe_checkout_session_id
        and sub_obj.stripe_checkout_session_id != session.get("id")
    ):
        logger.error("Checkout Session %s is not the current session for this subscription", session.get("id"))
        return
    if Subscription.objects.exclude(pk=sub_obj.pk).filter(stripe_subscription_id=subscription_id).exists():
        logger.error("Stripe subscription %s is already linked to another local record", subscription_id)
        return
    try:
        stripe_sub = stripe.Subscription.retrieve(
            subscription_id, expand=["items.data.price"]
        )
    except stripe.error.StripeError:
        logger.exception("Could not retrieve Checkout subscription %s", subscription_id)
        raise
    stripe_sub = stripe_data(stripe_sub)

    sync_extra_users_from_stripe(sub_obj, stripe_sub)
    if sub_obj.stripe_price_id not in STRIPE_PLAN_BY_PRICE_ID:
        logger.error("Checkout subscription %s has an unrecognized Price", subscription_id)
        return
    sub_obj.stripe_subscription_id = subscription_id
    sub_obj.stripe_customer_id = customer_id or sub_obj.stripe_customer_id
    sub_obj.stripe_checkout_session_id = ""
    sub_obj.status = stripe_sub.get("status", sub_obj.status)
    sub_obj.current_period_start = unix_to_dt(stripe_sub.get("current_period_start"))
    sub_obj.current_period_end = unix_to_dt(stripe_sub.get("current_period_end"))
    sync_cancellation_state(
        sub_obj,
        stripe_sub.get("cancel_at_period_end", False),
        sub_obj.current_period_end,
    )
    if event_created:
        sub_obj.stripe_event_created = max(sub_obj.stripe_event_created or 0, event_created)
    sub_obj.save()


def handle_subscription_updated(stripe_sub, deleted=False, event_created=None):
    stripe_sub = stripe_data(stripe_sub)
    subscription_id = stripe_sub.get("id")
    try:
        sub_obj = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        return

    if event_created and sub_obj.stripe_event_created and event_created < sub_obj.stripe_event_created:
        logger.info("Ignoring stale Stripe event for subscription %s", subscription_id)
        return

    sync_extra_users_from_stripe(sub_obj, stripe_sub)
    sub_obj.status = stripe_sub.get("status", sub_obj.status)
    sub_obj.current_period_start = unix_to_dt(stripe_sub.get("current_period_start"))
    period_end = unix_to_dt(stripe_sub.get("current_period_end"))
    sub_obj.current_period_end = period_end or sub_obj.current_period_end
    cancellation_scheduled = deleted or stripe_sub.get("cancel_at_period_end", False)
    if cancellation_scheduled:
        mark_cancellation_scheduled(sub_obj, period_end=sub_obj.current_period_end)
    elif sub_obj.cancel_at_period_end:
        clear_scheduled_cancellation(sub_obj)
    if event_created:
        sub_obj.stripe_event_created = event_created
    sub_obj.save()


def handle_invoice_event(
    invoice, payment_failed=False, payment_action_required=False
):
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        parent = invoice.get("parent", {}) or {}
        details = parent.get("subscription_details", {}) or {}
        subscription_id = details.get("subscription")
    if isinstance(subscription_id, dict):
        subscription_id = subscription_id.get("id")
    if not subscription_id:
        return
    try:
        sub_obj = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
        logger.info("Ignoring invoice for unknown Stripe subscription %s", subscription_id)
        return
    try:
        stripe_sub = stripe.Subscription.retrieve(
            subscription_id, expand=["items.data.price"]
        )
    except stripe.error.StripeError:
        logger.exception("Could not refresh subscription after invoice event")
        raise
    handle_subscription_updated(stripe_sub)
    if (payment_failed or payment_action_required) and sub_obj.owner_id and sub_obj.owner.email:
        hosted_url = invoice.get("hosted_invoice_url")
        if payment_action_required:
            body = "Płatność za subskrypcję wymaga dodatkowego potwierdzenia. Dokończ płatność w Stripe."
        else:
            body = "Płatność za subskrypcję nie powiodła się. Zaktualizuj metodę płatności."
        if hosted_url:
            body += f"\n\nSzczegóły faktury: {hosted_url}"
        try:
            from django.core.mail import send_mail

            send_mail(
                "Problem z płatnością za subskrypcję",
                body,
                settings.DEFAULT_FROM_EMAIL,
                [sub_obj.owner.email],
                fail_silently=True,
            )
        except Exception:
            logger.exception("Could not notify subscription owner about failed invoice")
