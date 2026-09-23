import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.views import View

from app.core.models import Subscription
from app.core.views.views_stripe import (
    company_billing_errors,
    get_extra_user_price_id,
    sync_extra_users_from_stripe,
    sync_stripe_customer_billing_data,
)

logger = logging.getLogger(__name__)


class PurchaseExtraUsersView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        if request.user.role != request.user.Role.OWNER:
            raise PermissionDenied("Tylko właściciel może dokupować użytkowników.")

        try:
            quantity = int(request.POST.get("quantity", "0"))
        except (TypeError, ValueError):
            quantity = 0
        if quantity < 1 or quantity > 100:
            messages.error(request, "Wybierz od 1 do 100 dodatkowych użytkowników.")
            return redirect("profile")

        try:
            with transaction.atomic():
                subscription = (
                    Subscription.objects.select_for_update()
                    .filter(company_id=request.user.company_id)
                    .order_by("-created_at")
                    .first()
                )
                if (
                    not subscription
                    or subscription.package == Subscription.Package.TRIAL
                    or subscription.base_max_users is None
                    or subscription.cancel_at_period_end
                    or subscription.status not in {
                        Subscription.STATUS_ACTIVE,
                        Subscription.STATUS_TRIALING,
                    }
                ):
                    messages.error(
                        request,
                        "Dodatkowych użytkowników można dokupić do aktywnego pakietu Start lub Standard.",
                    )
                    return redirect("profile")
                if not subscription.stripe_subscription_id or not subscription.billing_period:
                    messages.error(
                        request,
                        "Subskrypcja nie ma kompletnych danych rozliczeniowych Stripe.",
                    )
                    return redirect("profile")

                billing_errors = company_billing_errors(subscription.company)
                if billing_errors:
                    messages.error(
                        request,
                        "Przed płatnością uzupełnij dane do faktury: "
                        + ", ".join(billing_errors)
                        + ".",
                    )
                    return redirect("company_settings")

                stripe.api_key = settings.STRIPE_SECRET_KEY
                stripe_subscription = stripe.Subscription.retrieve(
                    subscription.stripe_subscription_id,
                    expand=["items.data.price", "latest_invoice.payment_intent"],
                )
                stripe_customer_id = stripe_subscription.get("customer")
                if isinstance(stripe_customer_id, str):
                    subscription.stripe_customer_id = stripe_customer_id
                sync_stripe_customer_billing_data(
                    subscription,
                    subscription.company,
                    request.user.email,
                )
                subscription.save(update_fields=["stripe_customer_id", "updated_at"])
                current_extra_item = None
                for item in stripe_subscription.get("items", {}).get("data", []):
                    price = item.get("price", {}) or {}
                    if (
                        item.get("id") == subscription.stripe_extra_user_item_id
                        or (price.get("lookup_key") or "").startswith(
                            "business_manager_extra_user"
                        )
                    ):
                        current_extra_item = item
                        break

                desired_quantity = quantity + (
                    (current_extra_item.get("quantity") or 0)
                    if current_extra_item else 0
                )
                if current_extra_item:
                    items = [{
                        "id": current_extra_item["id"],
                        "quantity": desired_quantity,
                    }]
                else:
                    items = [{
                        "price": get_extra_user_price_id(subscription.billing_period),
                        "quantity": desired_quantity,
                    }]

                updated_subscription = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    items=items,
                    payment_behavior="pending_if_incomplete",
                    proration_behavior="always_invoice",
                    expand=["items.data.price", "latest_invoice.payment_intent"],
                )
                sync_extra_users_from_stripe(subscription, updated_subscription)
                subscription.save(update_fields=[
                    "stripe_price_id",
                    "stripe_extra_user_item_id",
                    "extra_users",
                    "updated_at",
                ])

                if updated_subscription.get("pending_update"):
                    messages.warning(
                        request,
                        "Zmiana oczekuje na opłacenie faktury. Limit wzrośnie po potwierdzeniu płatności przez Stripe.",
                    )
                    invoice = updated_subscription.get("latest_invoice") or {}
                    hosted_invoice_url = invoice.get("hosted_invoice_url")
                    if hosted_invoice_url:
                        return redirect(hosted_invoice_url)
                    return redirect("profile")

        except stripe.error.StripeError as exc:
            logger.exception("Nie udało się dokupić użytkowników w Stripe")
            messages.error(
                request,
                getattr(exc, "user_message", None)
                or "Stripe odrzucił zmianę subskrypcji. Spróbuj ponownie.",
            )
            return redirect("profile")

        messages.success(
            request,
            f"Dokupiono {quantity} dodatkowych użytkowników.",
        )
        return redirect("profile")
