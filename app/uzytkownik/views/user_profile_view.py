from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from decimal import Decimal

from app.core.auth_backends import DEFAULT_ROLE_PERMISSIONS
from app.core.subscription_limits import (
    BYTES_PER_GB,
    FEATURE_LABELS,
    get_cached_company_storage_used_bytes,
)
from app.klient.models import Client
from app.protokol.models import Protocol
from app.rcp.models import TimeEntry, TimeEntryRequest
from app.urlop.models import LeaveAllowance, LeavePool, LeaveRequest
from app.uzytkownik.models import CompanyRoleGroup, EmployeeContract, EmployeeTraining
from app.uzytkownik.forms import (
    EmployeeContractForm, EmployeeTrainingForm,
    UserNotificationPreferencesForm,
    UserPrivateDataForm,
    UserSecuritySettingsForm,
)

User = get_user_model()


class UserProfileView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    @staticmethod
    def _usage_item(label, used, limit, icon, used_display=None, limit_display=None):
        percent = 0 if limit in (None, 0) else min(100, round((used / limit) * 100, 1))
        return {
            "label": label,
            "used": used_display if used_display is not None else used,
            "limit": (
                limit_display
                if limit_display is not None
                else ("Bez limitu" if limit is None else limit)
            ),
            "percent": percent,
            "warning": limit is not None and percent >= 80,
            "icon": icon,
        }

    def _get_subscription_summary(self, user, subscription=None):
        if user.role not in [user.Role.OWNER, user.Role.MANAGER] or not user.company_id:
            return None

        if subscription is None:
            subscription = (
                user.company.subscriptions.order_by("-created_at").first()
            )
        if not subscription:
            return None

        users_used = User.objects.filter(company_id=user.company_id).exclude(
            role=user.Role.CLIENT
        ).count()
        clients_used = Client.objects.filter(company_id=user.company_id).count()
        protocols_used = Protocol.objects.filter(company_id=user.company_id).count()
        storage_used_bytes = get_cached_company_storage_used_bytes(user.company_id)
        storage_used_gb = storage_used_bytes / BYTES_PER_GB

        features = [
            {
                "code": code,
                "name": label,
                "enabled": subscription.has_feature(code),
            }
            for code, label in FEATURE_LABELS.items()
        ]
        unit_amount = settings.STRIPE_EXTRA_USER_UNIT_AMOUNTS.get(
            subscription.billing_period or "",
            0,
        )

        return {
            "subscription": subscription,
            "usage": [
                self._usage_item(
                    "Użytkownicy", users_used, subscription.max_users, "bi-people"
                ),
                self._usage_item(
                    "Klienci", clients_used, subscription.max_clients, "bi-buildings"
                ),
                self._usage_item(
                    "Protokoły", protocols_used, subscription.max_protocols, "bi-file-earmark-check"
                ),
                self._usage_item(
                    "Przestrzeń",
                    storage_used_bytes,
                    subscription.max_storage_bytes,
                    "bi-device-ssd",
                    used_display=f"{storage_used_gb:.2f} GB",
                    limit_display=(
                        "Bez limitu"
                        if subscription.max_storage_gb is None
                        else f"{subscription.max_storage_gb} GB"
                    ),
                ),
            ],
            "features": features,
            "enabled_features": sum(feature["enabled"] for feature in features),
            "can_purchase_extra_users": (
                user.role == user.Role.OWNER
                and subscription.package != subscription.Package.TRIAL
                and subscription.base_max_users is not None
                and bool(subscription.stripe_subscription_id)
                and bool(subscription.billing_period)
                and not subscription.cancel_at_period_end
            ),
            "extra_user_unit_price": unit_amount / 100,
        }

    def _get_context(self, request, notification_form=None, security_form=None, private_form=None):
        user = request.user
        company_id = user.company_id
        leave_queryset = (
            LeaveRequest.objects
            .filter(
                company_id=company_id,
                user=user
            )
            .select_related("leave_type", "approver")
            .order_by("-date_from")
        )

        leave_stats = leave_queryset.aggregate(
            approved_days=Sum(
                "days_count",
                filter=Q(
                    status=LeaveRequest.Status.APPROVED,
                    leave_type__pool=LeavePool.VACATION,
                ),
            ),
            pending_days=Sum(
                "days_count",
                filter=Q(status=LeaveRequest.Status.SUBMITTED),
            ),
        )
        approved_days = leave_stats["approved_days"] or Decimal("0")
        pending_days = leave_stats["pending_days"] or Decimal("0")
        leave_requests = list(leave_queryset[:10])

        time_entry_request_queryset = TimeEntryRequest.objects.filter(
            company_id=company_id,
            user=user,
        )
        time_entry_request_stats = time_entry_request_queryset.aggregate(
            total=Count("pk"),
            pending=Count("pk", filter=Q(status="pending")),
        )
        time_entry_requests = list(
            time_entry_request_queryset.order_by("-created_at")[:6]
        )

        recent_time_entries = list(
            TimeEntry.objects
            .filter(company_id=company_id, user=user)
            .order_by("-date", "-created_at")[:6]
        )
        trainings = list(
            EmployeeTraining.objects
            .filter(company_id=company_id, employee=user)
            .order_by("-completed_at", "-created_at")
        )
        contracts = list(
            EmployeeContract.objects
            .filter(company_id=company_id, employee=user)
            .order_by("-date_from", "-created_at")
        )
        can_manage_contracts = user.role in {
            user.Role.OWNER,
            user.Role.MANAGER,
            user.Role.BIURO,
        }
        contract_employees = (
            User.objects.filter(company_id=company_id, is_active=True)
            .exclude(role__in=[user.Role.OWNER, user.Role.CLIENT])
            .order_by("first_name", "last_name", "email")
            if can_manage_contracts else User.objects.none()
        )
        active_training_count = sum(
            1 for training in trainings if not training.is_expired
        )
        active_contract_count = sum(
            1 for contract in contracts if not contract.is_finished
        )

        role_groups = list(
            CompanyRoleGroup.objects
            .filter(company_id=company_id, group__user=user)
            .values_list("name", flat=True)
        )

        if user.role == user.Role.OWNER:
            access_permission_count = Permission.objects.filter(
                codename__startswith="access_"
            ).count()
        else:
            direct_permissions = set(
                user.user_permissions
                .filter(codename__startswith="access_")
                .values_list("content_type__app_label", "codename")
            )
            group_permissions = set(
                Permission.objects
                .filter(group__user=user, codename__startswith="access_")
                .values_list("content_type__app_label", "codename")
            )
            default_permissions = {
                tuple(permission.split(".", 1))
                for permission in DEFAULT_ROLE_PERMISSIONS.get(user.role, set())
            }
            access_permission_count = len(
                direct_permissions | group_permissions | default_permissions
            )

        current_allowance = LeaveAllowance.objects.filter(
            company_id=company_id,
            user=user,
            year=timezone.localdate().year,
        ).first()

        context = {
            "user": user,
            "leave_requests": leave_requests,
            "approved_days": approved_days,
            "pending_days": pending_days,
            "time_entry_requests": time_entry_requests,
            "recent_time_entries": recent_time_entries,
            "trainings": trainings,
            "training_count": len(trainings),
            "active_training_count": active_training_count,
            "expired_training_count": len(trainings) - active_training_count,
            "contracts": contracts,
            "contract_count": len(contracts),
            "active_contract_count": active_contract_count,
            "finished_contract_count": len(contracts) - active_contract_count,
            "can_manage_contracts": can_manage_contracts,
            "contract_form": getattr(self, "_contract_form", None) or EmployeeContractForm(),
            "contract_employees": contract_employees,
            "training_form": getattr(self, "_training_form", None) or EmployeeTrainingForm(),
            "training_employees": contract_employees,
            "pending_time_entry_requests": time_entry_request_stats["pending"],
            "time_entry_request_count": time_entry_request_stats["total"],
            "protocol_count": Protocol.objects.filter(
                company_id=company_id,
                pracownik=user,
            ).count(),
            "role_groups": role_groups,
            "access_permission_count": access_permission_count,
            "current_allowance": current_allowance,
            "total_seniority": user.get_total_seniority_years(),
            "notification_form": notification_form or UserNotificationPreferencesForm(instance=user),
            "security_form": security_form or UserSecuritySettingsForm(instance=user),
            "private_form": private_form or UserPrivateDataForm(instance=user),
            "subscription_summary": self._get_subscription_summary(
                user,
                subscription=getattr(request, "current_subscription", None),
            ),
        }
        return context

    def get(self, request):
        return render(
            request,
            "app/uzytkownik/profile.html",
            self._get_context(request),
        )

    def post(self, request):
        if request.POST.get("form_action") == "add_training":
            if request.user.role not in {User.Role.OWNER, User.Role.MANAGER, User.Role.BIURO}:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Nie masz uprawnień do dodawania szkoleń pracowników.")
            training_form = EmployeeTrainingForm(request.POST, request.FILES)
            employee = User.objects.filter(
                pk=request.POST.get("employee_id"),
                company_id=request.user.company_id,
                is_active=True,
            ).exclude(role__in=[User.Role.OWNER, User.Role.CLIENT]).first()
            if not employee:
                training_form.add_error(None, "Wybierz prawidłowego pracownika.")
            if training_form.is_valid() and employee:
                training = training_form.save(commit=False)
                training.company = request.user.company
                training.employee = employee
                training.save()
                messages.success(request, "Szkolenie pracownika zostało dodane.")
                return redirect("profile")
            messages.error(request, "Popraw dane szkolenia pracownika.")
            self._training_form = training_form
            return render(request, "app/uzytkownik/profile.html", self._get_context(request))

        if request.POST.get("form_action") == "add_contract":
            if request.user.role not in {User.Role.OWNER, User.Role.MANAGER, User.Role.BIURO}:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Nie masz uprawnień do dodawania umów pracowników.")
            contract_form = EmployeeContractForm(request.POST, request.FILES)
            employee = User.objects.filter(
                pk=request.POST.get("employee_id"),
                company_id=request.user.company_id,
                is_active=True,
            ).exclude(role__in=[User.Role.OWNER, User.Role.CLIENT]).first()
            if not employee:
                contract_form.add_error(None, "Wybierz prawidłowego pracownika.")
            if contract_form.is_valid() and employee:
                contract = contract_form.save(commit=False)
                contract.company = request.user.company
                contract.employee = employee
                contract.save()
                messages.success(request, "Umowa pracownika została dodana.")
                return redirect("profile")
            messages.error(request, "Popraw dane umowy pracownika.")
            self._contract_form = contract_form
            return render(request, "app/uzytkownik/profile.html", self._get_context(request))

        if request.POST.get("form_action") == "private_data":
            form = UserPrivateDataForm(
                request.POST,
                request.FILES,
                instance=request.user,
            )
            if form.is_valid():
                form.save()
                messages.success(request, "Dane prywatne zostały zapisane.")
                return redirect("profile")

            messages.error(request, "Popraw dane prywatne.")
            return render(
                request,
                "app/uzytkownik/profile.html",
                self._get_context(request, private_form=form),
            )

        if request.POST.get("form_action") == "security_settings":
            form = UserSecuritySettingsForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Ustawienia bezpieczeństwa zostały zapisane.")
                return redirect("profile")

            messages.error(request, "Popraw ustawienia bezpieczeństwa.")
            return render(
                request,
                "app/uzytkownik/profile.html",
                self._get_context(request, security_form=form),
            )

        form = UserNotificationPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferencje powiadomień zostały zapisane.")
            return redirect("profile")

        messages.error(request, "Popraw ustawienia powiadomień.")
        return render(
            request,
            "app/uzytkownik/profile.html",
            self._get_context(request, notification_form=form),
        )
