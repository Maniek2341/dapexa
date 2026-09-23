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
from app.core.subscription_lifecycle import mark_cancellation_scheduled
from app.core.views.views_stripe import unix_to_dt


logger = logging.getLogger(__name__)


class CancelSubscriptionView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        if request.user.role != request.user.Role.OWNER:
            raise PermissionDenied("Tylko właściciel może anulować subskrypcję.")

        try:
            with transaction.atomic():
                subscription = (
                    Subscription.objects.select_for_update()
                    .filter(company_id=request.user.company_id)
                    .order_by("-created_at")
                    .first()
                )
                if not subscription or not subscription.stripe_subscription_id:
                    messages.error(request, "Brak aktywnej subskrypcji do anulowania.")
                    return redirect("profile")
                if subscription.cancel_at_period_end:
                    messages.info(request, "Subskrypcja jest już zaplanowana do anulowania.")
                    return redirect("profile")

                stripe.api_key = settings.STRIPE_SECRET_KEY
                stripe_subscription = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True,
                )
                period_end = unix_to_dt(stripe_subscription.get("current_period_end"))
                mark_cancellation_scheduled(subscription, period_end=period_end)
                subscription.status = stripe_subscription.get(
                    "status", subscription.status
                )
                subscription.save()
        except stripe.error.StripeError as exc:
            logger.exception("Stripe rejected subscription cancellation")
            messages.error(
                request,
                getattr(exc, "user_message", None)
                or "Nie udało się anulować subskrypcji. Spróbuj ponownie.",
            )
            return redirect("profile")

        messages.success(
            request,
            "Subskrypcja została anulowana na koniec bieżącego okresu rozliczeniowego.",
        )
        return redirect("profile")
