import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View

from app.core.models import Subscription
from app.core.subscription_lifecycle import clear_scheduled_cancellation
from app.core.subscription_limits import get_company_storage_used_bytes
from app.core.views.views_stripe import (
    EXTRA_USER_LOOKUP_PREFIX,
    STRIPE_PRICE_IDS,
    company_billing_errors,
    create_plan_checkout_session,
    get_extra_user_price_id,
    sync_extra_users_from_stripe,
    sync_stripe_customer_billing_data,
    stripe_data,
)
from app.klient.models import Client
from app.protokol.models import Protocol

logger = logging.getLogger(__name__)
User = get_user_model()


class ChangePackageView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def _validate_usage(self, subscription, target_package):
        limits = Subscription.PACKAGE_LIMITS[target_package]
        company_id = subscription.company_id
        users = User.objects.filter(company_id=company_id).exclude(
            role=User.Role.CLIENT
        ).count()
        clients = Client.objects.filter(company_id=company_id).count()
        protocols = Protocol.objects.filter(company_id=company_id).count()
        storage = get_company_storage_used_bytes(company_id)

        effective_users_limit = limits["max_users"]
        if effective_users_limit is not None:
            effective_users_limit += subscription.extra_users
        checks = [
            ("użytkowników", users, effective_users_limit),
            ("klientów", clients, limits["max_clients"]),
            ("protokołów", protocols, limits["max_protocols"]),
            (
                "przestrzeni na pliki",
                storage,
                limits["max_storage_gb"] * (1024 ** 3),
            ),
        ]
        exceeded = [
            f"{name}: {used}/{limit}"
            for name, used, limit in checks
            if limit is not None and used > limit
        ]
        return exceeded

    def _create_checkout(self, request, subscription, package, billing_period):
        session = create_plan_checkout_session(
            request, subscription, package, billing_period
        )
        if session.url:
            return redirect(session.url)
        messages.info(
            request,
            "Płatność została już wysłana do Stripe. Oczekuje na synchronizację.",
        )
        return redirect("profile")

    def post(self, request):
        if request.user.role != request.user.Role.OWNER:
            raise PermissionDenied("Tylko właściciel może zmieniać pakiet.")

        package = request.POST.get("package")
        billing_period = request.POST.get("billing_period")
        if package not in STRIPE_PRICE_IDS or billing_period not in {
            Subscription.BILLING_MONTHLY,
            Subscription.BILLING_YEARLY,
        }:
            messages.error(request, "Wybrano nieprawidłowy pakiet lub okres rozliczeniowy.")
            return redirect("select_plan")

        try:
            with transaction.atomic():
                subscription = (
                    Subscription.objects.select_for_update()
                    .filter(company_id=request.user.company_id)
                    .order_by("-created_at")
                    .first()
                )
                if not subscription:
                    messages.error(request, "Nie znaleziono subskrypcji firmy.")
                    return redirect("select_plan")
                cancellation_period_finished = (
                    subscription.status == Subscription.STATUS_CANCELED
                    and subscription.current_period_end
                    and subscription.current_period_end <= timezone.now()
                )
                if subscription.cancel_at_period_end and not cancellation_period_finished:
                    messages.error(
                        request,
                        "Nie można zmienić pakietu subskrypcji zaplanowanej do anulowania.",
                    )
                    return redirect("profile")
                if cancellation_period_finished:
                    clear_scheduled_cancellation(subscription)
                if (
                    subscription.package == package
                    and subscription.billing_period == billing_period
                ):
                    messages.info(request, "Ten pakiet jest już aktywny.")
                    return redirect("select_plan")

                billing_errors = company_billing_errors(subscription.company)
                if billing_errors:
                    messages.error(
                        request,
                        "Przed płatnością uzupełnij dane do faktury: "
                        + ", ".join(billing_errors)
                        + ".",
                    )
                    return redirect("company_settings")

                exceeded = (
                    self._validate_usage(subscription, package)
                    if package != subscription.package
                    else []
                )
                if exceeded:
                    messages.error(
                        request,
                        "Nie można wybrać niższego pakietu. Przekroczone limity: "
                        + ", ".join(exceeded),
                    )
                    return redirect("select_plan")

                stripe.api_key = settings.STRIPE_SECRET_KEY
                if not subscription.stripe_subscription_id:
                    sync_stripe_customer_billing_data(
                        subscription,
                        subscription.company,
                        request.user.email,
                    )
                    subscription.save(update_fields=["stripe_customer_id", "updated_at"])
                    return self._create_checkout(
                        request, subscription, package, billing_period
                    )

                stripe_subscription = stripe_data(stripe.Subscription.retrieve(
                    subscription.stripe_subscription_id,
                    expand=["items.data.price", "latest_invoice.payment_intent"],
                ))
                remote_status = stripe_subscription.get("status")
                if remote_status == Subscription.STATUS_CANCELED:
                    subscription.status = Subscription.STATUS_CANCELED
                    clear_scheduled_cancellation(subscription)
                    stripe_customer_id = stripe_subscription.get("customer")
                    if isinstance(stripe_customer_id, str):
                        subscription.stripe_customer_id = stripe_customer_id
                    sync_stripe_customer_billing_data(
                        subscription,
                        subscription.company,
                        request.user.email,
                    )
                    subscription.save()
                    return self._create_checkout(
                        request, subscription, package, billing_period
                    )
                if remote_status not in {
                    Subscription.STATUS_ACTIVE,
                    Subscription.STATUS_TRIALING,
                }:
                    messages.error(
                        request,
                        "Najpierw ureguluj zaległą płatność w panelu rozliczeń Stripe.",
                    )
                    return redirect("profile")
                stripe_customer_id = stripe_subscription.get("customer")
                if isinstance(stripe_customer_id, str):
                    subscription.stripe_customer_id = stripe_customer_id
                sync_stripe_customer_billing_data(
                    subscription,
                    subscription.company,
                    request.user.email,
                )
                subscription.save(update_fields=["stripe_customer_id", "updated_at"])
                main_item = None
                extra_item = None
                for item in stripe_subscription.get("items", {}).get("data", []):
                    lookup_key = (item.get("price", {}) or {}).get("lookup_key") or ""
                    if (
                        item.get("id") == subscription.stripe_extra_user_item_id
                        or lookup_key.startswith(EXTRA_USER_LOOKUP_PREFIX)
                    ):
                        extra_item = item
                    else:
                        main_item = main_item or item
                if not main_item:
                    messages.error(request, "Nie znaleziono głównej pozycji subskrypcji Stripe.")
                    return redirect("select_plan")

                items = [{
                    "id": main_item["id"],
                    "price": STRIPE_PRICE_IDS[package][billing_period],
                    "quantity": 1,
                }]
                if extra_item:
                    extra_quantity = 0 if package == Subscription.Package.PRO else (
                        extra_item.get("quantity") or 0
                    )
                    items.append({
                        "id": extra_item["id"],
                        "price": get_extra_user_price_id(billing_period),
                        "quantity": extra_quantity,
                    })

                updated = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    items=items,
                    payment_behavior="pending_if_incomplete",
                    proration_behavior="always_invoice",
                    expand=["items.data.price", "latest_invoice.payment_intent"],
                )
                updated = stripe_data(updated)
                sync_extra_users_from_stripe(subscription, updated)
                subscription.status = updated.get("status", subscription.status)
                subscription.save()

                if updated.get("pending_update"):
                    messages.warning(
                        request,
                        "Zmiana pakietu oczekuje na płatność. Zostanie aktywowana po potwierdzeniu przez Stripe.",
                    )
                    invoice = updated.get("latest_invoice") or {}
                    if invoice.get("hosted_invoice_url"):
                        return redirect(invoice["hosted_invoice_url"])
                    return redirect("profile")

        except stripe.error.StripeError as exc:
            logger.exception("Stripe rejected package change")
            messages.error(
                request,
                getattr(exc, "user_message", None)
                or "Stripe odrzucił zmianę pakietu. Spróbuj ponownie.",
            )
            return redirect("select_plan")

        messages.success(request, "Pakiet został zmieniony.")
        return redirect("profile")
