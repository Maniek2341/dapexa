import logging

import stripe
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views import View

from app.core.company_deletion import (
    delete_company_data,
    delete_company_from_stripe,
)
from app.core.models import PanelUser

logger = logging.getLogger(__name__)


class DeleteCompanyAccountView(LoginRequiredMixin, View):
    template_name = "app/core/delete_company_account.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != PanelUser.Role.OWNER or not request.user.company_id:
            raise PermissionDenied("Tylko właściciel firmy może usunąć konto firmy.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {
            "company": request.user.company,
        })

    def post(self, request):
        company = request.user.company
        if request.POST.get("confirm_delete") != "yes":
            messages.error(request, "Zaznacz potwierdzenie usunięcia konta firmy.")
            return redirect("delete_company_account")

        confirmed_name = (request.POST.get("company_name_confirmation") or "").strip()
        if confirmed_name.casefold() != company.name.strip().casefold():
            messages.error(request, "Wpisana nazwa firmy nie zgadza się z nazwą konta.")
            return redirect("delete_company_account")

        if not request.user.check_password(request.POST.get("password") or ""):
            messages.error(request, "Podane hasło jest nieprawidłowe.")
            return redirect("delete_company_account")

        company_id = company.pk
        try:
            delete_company_from_stripe(company)
        except stripe.error.StripeError:
            logger.exception(
                "Nie udało się usunąć klienta Stripe firmy %s", company_id
            )
            messages.error(
                request,
                "Stripe nie potwierdził usunięcia danych płatniczych. Konto i dane firmy pozostają bez zmian; spróbuj ponownie później.",
            )
            return redirect("delete_company_account")
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("delete_company_account")

        try:
            delete_company_data(company_id)
        except Exception:
            logger.exception(
                "Stripe usunięty, ale nie udało się usunąć danych firmy %s",
                company_id,
            )
            messages.error(
                request,
                "Stripe usunął dane płatnicze, ale aplikacja nie zakończyła usuwania danych firmy. Skontaktuj się z pomocą techniczną.",
            )
            return redirect("delete_company_account")

        logout(request)
        messages.success(request, "Konto firmy i powiązane dane zostały usunięte.")
        return redirect("login")
