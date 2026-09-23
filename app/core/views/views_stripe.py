# app/core/views_stripe.py
import json
import logging
from datetime import UTC, datetime

import stripe

from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from app.core.models import Company, PanelUser, Address, Subscription
from app.core.subscription_lifecycle import (
    clear_scheduled_cancellation,
    mark_cancellation_scheduled,
    sync_cancellation_state,
)
from app.core.validators import is_valid_polish_nip, normalize_nip

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# price_id z Twojego panelu Stripe
STRIPE_PRICE_IDS = {
    "start": {
        "monthly": "price_1SYlwN2cLveabukasUB1Gfp5",
        "yearly": "price_1SYlwe2cLveabukaBBljR9VM",
    },
    "standard": {
        "monthly": "price_1SYlxI2cLveabukamOy0egY7",
        "yearly": "price_1SYlxR2cLveabuka2atcyWd7",
    },
    "pro": {
        "monthly": "price_1SYlxl2cLveabuka76AEloE3",
        "yearly": "price_1SYlxw2cLveabukaJvYLRrp8",
    },
}

STRIPE_PLAN_BY_PRICE_ID = {
    price_id: (package, billing_period)
    for package, prices in STRIPE_PRICE_IDS.items()
    for billing_period, price_id in prices.items()
}

EXTRA_USER_LOOKUP_PREFIX = "business_manager_extra_user"


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
    )
    return price.id


def sync_extra_users_from_stripe(subscription, stripe_subscription):
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


# --- POMOCNICZE ---

def unix_to_dt(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)


# --- CHECKOUT SESSION (wywoływane z JS) ---

@require_POST
@csrf_exempt  # jeśli chcesz – dodaj X-CSRFToken w fetch i usuń to
def create_checkout_session(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    package = data.get("package")
    billing_period = data.get("billing_period")  # monthly / yearly
    email = data.get("email")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    company_name = data.get("company_name")
    nip = data.get("nip")
    regon = data.get("regon")
    phone = data.get("phone")
    city = data.get("city")
    address = data.get("address")
    postal_code = data.get("postalCode")

    if not is_valid_polish_nip(nip):
        return JsonResponse({"error": "Podaj prawidłowy polski NIP."}, status=400)
    if not all([company_name, city, address, postal_code]):
        return JsonResponse(
            {"error": "Uzupełnij nazwę i pełny adres firmy do faktury."},
            status=400,
        )

    if package not in STRIPE_PRICE_IDS:
        return HttpResponseBadRequest("Unknown package")

    if billing_period not in STRIPE_PRICE_IDS[package]:
        return HttpResponseBadRequest("Unknown billing period")

    price_id = STRIPE_PRICE_IDS[package][billing_period]

    domain_url = getattr(settings, "DOMAIN_URL", None)
    if not domain_url:
        domain_url = request.build_absolute_uri("/").rstrip("/")

    try:
        customer = stripe.Customer.create(
            name=company_name,
            email=email,
            phone=phone or None,
            preferred_locales=["pl"],
            address={
                "line1": address,
                "postal_code": postal_code,
                "city": city,
                "country": "PL",
            },
            tax_id_data=[{
                "type": "pl_nip",
                "value": normalize_nip(nip),
            }],
            metadata={"nip": normalize_nip(nip)},
        )
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            subscription_data={
                "trial_period_days": 14,  # 14 dni okresu próbnego
            },
            success_url=domain_url + reverse("checkout_success") + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=domain_url + reverse("checkout_cancel"),
            customer=customer.id,
            metadata={
                "package": package,
                "billing_period": billing_period,
                "first_name": first_name or "",
                "last_name": last_name or "",
                "company_name": company_name or "",
                "nip": nip or "",
                "regon": regon or "",
                "phone": phone or "",
                "city": city or "",
                "address": address or "",
                "postal_code": postal_code or "",
            },
        )
    except Exception as e:
        logger.exception("Error creating Stripe Checkout Session")
        return JsonResponse({"error": str(e)}, status=400)

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


# --- WEBHOOK STRIPE ---

@csrf_exempt
def stripe_webhook(request):
    logger.info("Stripe webhook RAW body: %s", request.body)
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

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        handle_checkout_session_completed(data_object)

    if event_type == "customer.subscription.updated":
        handle_subscription_updated(data_object)

    if event_type == "customer.subscription.deleted":
        handle_subscription_updated(data_object, deleted=True)

    return JsonResponse({"status": "success"})


def handle_checkout_session_completed(session):
    """
    Tworzy/aktualizuje Subscription, Company, PanelUser na podstawie checkout.session.completed
    """
    logger.info("Handling checkout.session.completed for session: %s", session.get("id"))
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    metadata = session.get("metadata", {}) or {}

    package = metadata.get("package")
    billing_period = metadata.get("billing_period") or Subscription.BILLING_MONTHLY

    local_subscription_id = metadata.get("local_subscription_id")
    if local_subscription_id:
        try:
            sub_obj = Subscription.objects.get(pk=local_subscription_id)
        except (Subscription.DoesNotExist, ValueError):
            logger.error("Unknown local subscription: %s", local_subscription_id)
            return

        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
        except Exception:
            logger.exception("Could not retrieve changed Stripe subscription")
            return

        sub_obj.stripe_subscription_id = subscription_id
        sub_obj.stripe_customer_id = customer_id or sub_obj.stripe_customer_id
        sub_obj.package = package or sub_obj.package
        sub_obj.billing_period = billing_period
        sync_extra_users_from_stripe(sub_obj, stripe_sub)
        sub_obj.status = stripe_sub.get("status", sub_obj.status)
        sub_obj.current_period_start = unix_to_dt(stripe_sub.get("current_period_start"))
        sub_obj.current_period_end = unix_to_dt(stripe_sub.get("current_period_end"))
        sync_cancellation_state(
            sub_obj,
            stripe_sub.get("cancel_at_period_end", False),
            sub_obj.current_period_end,
        )
        sub_obj.save()
        return

    # znajdź lub utwórz Subscription
    sub_obj, created = Subscription.objects.get_or_create(
        stripe_subscription_id=subscription_id,
        defaults={
            "stripe_customer_id": customer_id or "",
            "package": package or "",
            "billing_period": billing_period,
        },
    )

    # dociągamy pełną subskrypcję ze Stripe
    try:
        stripe_sub = stripe.Subscription.retrieve(subscription_id)
    except Exception:
        stripe_sub = None

    if stripe_sub:
        sub_obj.stripe_customer_id = customer_id or sub_obj.stripe_customer_id
        sync_extra_users_from_stripe(sub_obj, stripe_sub)
        sub_obj.status = stripe_sub.get("status", sub_obj.status)
        sub_obj.current_period_start = unix_to_dt(stripe_sub.get("current_period_start"))
        sub_obj.current_period_end = unix_to_dt(stripe_sub.get("current_period_end"))
        sync_cancellation_state(
            sub_obj,
            stripe_sub.get("cancel_at_period_end", False),
            sub_obj.current_period_end,
        )

    # Dane do stworzenia firmy i ownera
    email = session.get("customer_details", {}).get("email") or session.get("customer_email")

    first_name = metadata.get("first_name")
    last_name = metadata.get("last_name")
    company_name = metadata.get("company_name") or "Firma bez nazwy"
    nip = metadata.get("nip") or ""
    regon = metadata.get("regon") or ""
    phone = metadata.get("phone") or ""
    city = metadata.get("city") or ""
    street = metadata.get("address") or ""
    postal_code = metadata.get("postal_code") or ""

    # 1. Tworzymy lub znajdujemy użytkownika (owner)
    owner, owner_created = PanelUser.objects.get_or_create(
        email=email,
        defaults={
            "first_name": first_name or "",
            "last_name": last_name or "",
            "role": PanelUser.Role.OWNER,
            "is_active": True,
            "is_staff": True,
            "is_admin": False,
            "is_superuser": False,
        },
    )
    # if owner_created:
    #     owner.set_password(PanelUser.objects.make_random_password())
    #     owner.save()

    # 2. Firma – idempotentnie (żeby webhook retry nie tworzył duplikatów)
    if nip:
        company = Company.objects.filter(nip=nip).first()
    else:
        company = Company.objects.filter(name=company_name, email=email).first()

    company_created = False
    main_address = None

    if not company:
        main_address = Address.objects.create(
            street=street,
            postcode=postal_code,
            city=city,
            country="Polska",
        )
        if nip:
            company = Company.objects.create(
                name=company_name,
                nip=nip,
                regon=regon,
                phone=phone,
                email=email,
                main_address=main_address,
            )
        else:
            company = Company.objects.create(
                name=company_name,
                regon=regon,
                phone=phone,
                email=email,
                main_address=main_address,
            )
        company_created = True
    else:
        if not company.main_address and (street or postal_code or city):
            main_address = Address.objects.create(
                street=street,
                postcode=postal_code,
                city=city,
                country="Polska",
            )
            company.main_address = main_address
            company.save(update_fields=["main_address"])

    logger.info("Company %s (created=%s)", company.id, company_created)

    # 3. Podpinamy ownera do firmy
    if owner.company_id != company.id:
        owner.company = company
        owner.save(update_fields=["company"])

    # 4. Podpinamy firmę i ownera do subskrypcji
    sub_obj.company = company
    sub_obj.owner = owner
    sub_obj.save()
    if not company_billing_errors(company):
        try:
            sync_stripe_customer_billing_data(sub_obj, company, owner.email)
            sub_obj.save(update_fields=["stripe_customer_id", "updated_at"])
        except stripe.error.StripeError:
            logger.exception("Could not synchronize invoice data after Checkout")


def handle_subscription_updated(stripe_sub, deleted=False):
    subscription_id = stripe_sub.get("id")
    try:
        sub_obj = Subscription.objects.get(stripe_subscription_id=subscription_id)
    except Subscription.DoesNotExist:
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
    sub_obj.save()
