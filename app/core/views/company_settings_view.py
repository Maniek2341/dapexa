from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from app.core.forms import (
    CompanyAddressSettingsForm,
    CompanyNotificationSettingsForm,
    CompanyOperationalSettingsForm,
    CompanyProfileSettingsForm,
)
from app.core.models import Address, CompanySettings, PanelUser, Subscription


class CompanySettingsView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
    View,
):
    login_url = reverse_lazy("login")
    permission_required = "core.access_company_settings"
    raise_exception = True
    template_name = "app/core/company_settings.html"
    allowed_roles = {
        PanelUser.Role.OWNER,
        PanelUser.Role.MANAGER,
        PanelUser.Role.BIURO,
    }

    def test_func(self):
        user = self.request.user
        return user.role in self.allowed_roles and user.company_id is not None

    def _instances(self):
        company = self.request.user.company
        settings, _ = CompanySettings.objects.get_or_create(company=company)
        address = company.main_address or Address(country="Polska")
        return company, address, settings

    def _current_subscription(self):
        subscription = getattr(self.request, "current_subscription", None)
        if subscription is not None:
            return subscription
        company = self.request.user.company
        return company.subscriptions.order_by("-created_at").first()

    def _can_change_logo(self):
        subscription = self._current_subscription()
        return bool(subscription and subscription.package == Subscription.Package.PRO)

    def _forms(self, data=None, files=None):
        company, address, settings = self._instances()
        return (
            CompanyProfileSettingsForm(
                data,
                files,
                instance=company,
                prefix="company",
                can_change_logo=self._can_change_logo(),
            ),
            CompanyAddressSettingsForm(data, instance=address, prefix="address"),
            CompanyOperationalSettingsForm(data, instance=settings, prefix="settings"),
            CompanyNotificationSettingsForm(data, instance=settings, prefix="notifications"),
        )

    def _render(self, company_form, address_form, settings_form, notification_form):
        subscription = self._current_subscription()
        return render(
            self.request,
            self.template_name,
            {
                "company_form": company_form,
                "address_form": address_form,
                "settings_form": settings_form,
                "notification_form": notification_form,
                "can_change_company_logo": self._can_change_logo(),
                "current_company_subscription": subscription,
                "highest_package_name": Subscription.Package.PRO.label,
            },
        )

    def get(self, request):
        return self._render(*self._forms())

    def post(self, request):
        company_form, address_form, settings_form, notification_form = self._forms(
            request.POST,
            request.FILES,
        )
        forms = (company_form, address_form, settings_form, notification_form)

        validation_results = [form.is_valid() for form in forms]
        if not all(validation_results):
            return self._render(*forms)

        try:
            with transaction.atomic():
                company = company_form.save()

                if company.main_address_id or address_form.has_address_data:
                    address = address_form.save()
                    if company.main_address_id != address.pk:
                        company.main_address = address
                        company.save(update_fields=["main_address", "updated_at"])

                settings_form.save()
                notification_form.save()
        except ValidationError as error:
            address_form.add_error(None, error)
            return self._render(*forms)

        messages.success(request, "Ustawienia firmy zostały zapisane.")
        return redirect("company_settings")
