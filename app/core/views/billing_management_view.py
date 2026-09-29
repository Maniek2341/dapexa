import json
import logging
from datetime import UTC, datetime

import stripe
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from app.core.models import Subscription
from app.core.views.views_stripe import stripe_data

logger = logging.getLogger(__name__)


def _owner_subscription(request):
    if request.user.role != request.user.Role.OWNER or not request.user.company_id:
        raise PermissionDenied("Tylko właściciel firmy może zarządzać rozliczeniami.")
    return (
        Subscription.objects.filter(company_id=request.user.company_id)
        .order_by("-created_at")
        .first()
    )


@login_required
def billing_management(request):
    subscription = _owner_subscription(request)
    invoices = []
    payment_method = None
    load_error = ""

    if subscription and subscription.stripe_customer_id:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            customer = stripe_data(stripe.Customer.retrieve(
                subscription.stripe_customer_id,
                expand=["invoice_settings.default_payment_method"],
            ))
            default_method = (customer.get("invoice_settings") or {}).get(
                "default_payment_method"
            )
            if isinstance(default_method, str):
                default_method = stripe_data(stripe.PaymentMethod.retrieve(default_method))
            if default_method:
                method_get = getattr(default_method, "get", None)
                card = method_get("card") if method_get else None
                card = card or {}
                payment_method = {
                    "brand": card.get("brand") or "Karta",
                    "last4": card.get("last4") or "",
                    "exp_month": card.get("exp_month"),
                    "exp_year": card.get("exp_year"),
                }
            stripe_invoices = stripe.Invoice.list(
                customer=subscription.stripe_customer_id, limit=50
            ).data
            for invoice in stripe_invoices:
                invoice = stripe_data(invoice)
                created = invoice.get("created") or 0
                try:
                    created = datetime.fromtimestamp(int(created), tz=UTC)
                except (TypeError, ValueError, OSError, OverflowError):
                    created = None
                invoices.append({
                    "id": invoice.get("id"),
                    "number": invoice.get("number") or invoice.get("id"),
                    "created": created,
                    "status": invoice.get("status"),
                    "amount": (invoice.get("total") or 0) / 100,
                    "currency": (invoice.get("currency") or "pln").upper(),
                })
        except Exception as exc:
            logger.exception("Could not load Stripe billing data")
            load_error = (
                getattr(exc, "user_message", None)
                or "Nie udało się pobrać danych rozliczeniowych. Spróbuj ponownie później."
            )

    return render(
        request,
        "app/core/billing_management.html",
        {
            "subscription": subscription,
            "invoices": invoices,
            "payment_method": payment_method,
            "load_error": load_error,
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )


@login_required
def billing_invoice_pdf(request, invoice_id):
    subscription = _owner_subscription(request)
    if not subscription or not subscription.stripe_customer_id:
        raise PermissionDenied("Brak konta rozliczeniowego Stripe dla tej firmy.")
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        invoice = stripe_data(stripe.Invoice.retrieve(invoice_id))
        if invoice.get("customer") != subscription.stripe_customer_id:
            raise PermissionDenied("Ta faktura nie należy do firmy.")
        pdf_url = invoice.get("invoice_pdf")
        if not pdf_url:
            messages.error(request, "Ta faktura nie ma dostępnego pliku PDF.")
            return redirect("billing_management")
        pdf_response = requests.get(pdf_url, timeout=(5, 30))
        pdf_response.raise_for_status()
    except PermissionDenied:
        raise
    except (stripe.error.StripeError, requests.RequestException):
        logger.exception("Could not download Stripe invoice PDF %s", invoice_id)
        messages.error(request, "Nie udało się pobrać faktury. Spróbuj ponownie później.")
        return redirect("billing_management")

    number = "".join(c for c in (invoice.get("number") or invoice_id) if c.isalnum() or c in "-_")
    response = HttpResponse(pdf_response.content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="faktura-{number}.pdf"'
    return response


@login_required
@require_POST
def create_billing_setup_intent(request):
    subscription = _owner_subscription(request)
    if not subscription or not subscription.stripe_customer_id:
        return JsonResponse(
            {"error": "Nie znaleziono klienta Stripe dla tej firmy."}, status=400
        )
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent = stripe.SetupIntent.create(
            customer=subscription.stripe_customer_id,
            payment_method_types=["card"],
            usage="off_session",
        )
    except stripe.error.StripeError as exc:
        logger.exception("Could not create Stripe SetupIntent")
        return JsonResponse(
            {
                "error": getattr(exc, "user_message", None)
                or "Nie udało się przygotować formularza karty."
            },
            status=400,
        )
    return JsonResponse({"client_secret": intent.client_secret})


@login_required
@require_POST
def save_billing_payment_method(request):
    subscription = _owner_subscription(request)
    if not subscription or not subscription.stripe_customer_id:
        return JsonResponse(
            {"error": "Nie znaleziono klienta Stripe dla tej firmy."}, status=400
        )
    try:
        payload = json.loads(request.body.decode("utf-8"))
        setup_intent_id = payload.get("setup_intent_id", "")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest("Nieprawidłowe żądanie.")
    if not setup_intent_id.startswith("seti_"):
        return HttpResponseBadRequest("Nieprawidłowa konfiguracja płatności.")

    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent = stripe_data(stripe.SetupIntent.retrieve(setup_intent_id))
        if (
            intent.get("customer") != subscription.stripe_customer_id
            or intent.get("status") != "succeeded"
            or not intent.get("payment_method")
        ):
            return JsonResponse(
                {"error": "Nie udało się potwierdzić nowej karty."}, status=400
            )
        stripe.Customer.modify(
            subscription.stripe_customer_id,
            invoice_settings={"default_payment_method": intent.get("payment_method")},
        )
        if subscription.stripe_subscription_id:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                default_payment_method=intent.get("payment_method"),
            )
    except stripe.error.StripeError as exc:
        logger.exception("Could not update Stripe default payment method")
        return JsonResponse(
            {
                "error": getattr(exc, "user_message", None)
                or "Nie udało się zapisać nowej karty."
            },
            status=400,
        )
    return JsonResponse({"ok": True})
