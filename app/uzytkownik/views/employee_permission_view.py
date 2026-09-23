from itertools import groupby
from uuid import uuid4

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Count
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from app.core.auth_backends import DEFAULT_ROLE_PERMISSIONS
from app.core.view_permissions import PUBLIC_VIEW_NAMES
from app.uzytkownik.forms import CompanyRoleGroupForm, EmployeePermissionForm
from app.uzytkownik.models import CompanyRoleGroup

User = get_user_model()

PERMISSION_MODULES = {
    "core": ("Panel i użytkownicy", "bi-people"),
    "dokument": ("Dokumenty", "bi-folder"),
    "gwarancja": ("Gwarancje", "bi-shield-check"),
    "klient": ("Klienci", "bi-person-vcard"),
    "magazyn": ("Magazyn", "bi-box-seam"),
    "obsluga": ("Obsługa cykliczna", "bi-arrow-repeat"),
    "oferta_praca": ("Oferty", "bi-file-earmark-richtext"),
    "pojazd": ("Pojazdy", "bi-truck"),
    "praca": ("Prace", "bi-hammer"),
    "protokol": ("Protokoły", "bi-clipboard-check"),
    "rcp": ("Rejestracja czasu pracy", "bi-clock-history"),
    "serwis": ("Serwis", "bi-tools"),
    "sprzet": ("Sprzęt", "bi-wrench-adjustable"),
    "urlop": ("Urlopy", "bi-calendar2-week"),
    "urzadzenie": ("Urządzenia", "bi-cpu"),
    "zadanie": ("Zadania", "bi-list-check"),
}

OWNER_ONLY_PERMISSION_VIEWS = {
    "employee_permission_list",
    "employee_permission_edit",
    "employee_group_create",
    "employee_group_edit",
    "employee_group_delete",
}

def get_assignable_permissions():
    project_app_labels = [
        config.label
        for config in apps.get_app_configs()
        if config.name.startswith("app.")
    ]
    return (
        Permission.objects
        .filter(
            content_type__app_label__in=project_app_labels,
            codename__startswith="access_",
        )
        .exclude(codename__in=[f"access_{name}" for name in PUBLIC_VIEW_NAMES])
        .exclude(codename__in=[f"access_{name}" for name in OWNER_ONLY_PERMISSION_VIEWS])
        .select_related("content_type")
        .order_by("content_type__app_label", "name")
    )


def get_permission_form_context(form):
    permission_queryset = list(form.fields["permissions"].queryset)
    selected_values = form["permissions"].value() or []
    selected_permission_ids = {
        int(value) for value in selected_values if str(value).isdigit()
    }

    permission_groups = []
    for app_label, permissions in groupby(
        permission_queryset,
        key=lambda permission: permission.content_type.app_label,
    ):
        permissions = list(permissions)
        title, icon = PERMISSION_MODULES.get(
            app_label,
            (app_label.replace("_", " ").title(), "bi-grid"),
        )
        permission_groups.append({
            "app_label": app_label,
            "title": title,
            "icon": icon,
            "permissions": permissions,
        })

    return {
        "selected_permission_ids": selected_permission_ids,
        "permission_groups": permission_groups,
    }


class OwnerPermissionManagementMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.role in {
                User.Role.OWNER,
                User.Role.MANAGER,
                User.Role.BIURO,
            }
            and self.request.user.company_id is not None
        )


class EmployeePermissionListView(OwnerPermissionManagementMixin, ListView):
    model = User
    template_name = "app/pracownik/permissions.html"
    context_object_name = "employees"

    def get_queryset(self):
        permission_queryset = get_assignable_permissions()
        return (
            User.objects
            .filter(company_id=self.request.user.company_id)
            .exclude(role__in=[User.Role.OWNER, User.Role.CLIENT])
            .prefetch_related(
                Prefetch(
                    "user_permissions",
                    queryset=permission_queryset,
                    to_attr="company_permissions",
                ),
                Prefetch(
                    "groups",
                    queryset=Group.objects.filter(
                        company_role_group__company_id=self.request.user.company_id,
                    ).select_related("company_role_group"),
                    to_attr="role_permission_groups",
                ),
            )
            .order_by("last_name", "first_name", "email")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_groups"] = (
            CompanyRoleGroup.objects
            .filter(company_id=self.request.user.company_id)
            .select_related("group")
            .prefetch_related("group__permissions")
            .annotate(member_count=Count("group__user"))
        )
        return context


class EmployeePermissionUpdateView(OwnerPermissionManagementMixin, UpdateView):
    model = User
    form_class = EmployeePermissionForm
    template_name = "app/pracownik/permissions_edit.html"
    context_object_name = "employee"
    success_url = reverse_lazy("employee_permission_list")

    def get_queryset(self):
        return (
            User.objects
            .filter(company_id=self.request.user.company_id)
            .exclude(role__in=[User.Role.OWNER, User.Role.CLIENT])
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["permission_queryset"] = get_assignable_permissions()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        permission_queryset = list(form.fields["user_permissions"].queryset)

        selected_values = form["user_permissions"].value() or []
        context["selected_permission_ids"] = {
            int(value) for value in selected_values if str(value).isdigit()
        }

        inherited_permissions = {}
        role_groups = (
            CompanyRoleGroup.objects
            .filter(
                company_id=self.request.user.company_id,
                group__user=self.object,
            )
            .select_related("group")
            .prefetch_related(
                Prefetch(
                    "group__permissions",
                    queryset=get_assignable_permissions(),
                    to_attr="assignable_permissions",
                )
            )
        )
        for role_group in role_groups:
            for permission in role_group.group.assignable_permissions:
                inherited_permissions.setdefault(permission.pk, []).append(
                    role_group.name
                )

        default_permissions = DEFAULT_ROLE_PERMISSIONS.get(self.object.role, set())
        for permission in permission_queryset:
            permission.inherited_group_names = inherited_permissions.get(
                permission.pk,
                [],
            )
            permission.is_role_default = (
                f"{permission.content_type.app_label}.{permission.codename}"
                in default_permissions
            )

        permission_groups = []
        for app_label, permissions in groupby(
            permission_queryset,
            key=lambda permission: permission.content_type.app_label,
        ):
            permissions = list(permissions)
            title, icon = PERMISSION_MODULES.get(
                app_label,
                (app_label.replace("_", " ").title(), "bi-grid"),
            )
            permission_groups.append({
                "app_label": app_label,
                "title": title,
                "icon": icon,
                "permissions": permissions,
            })

        context["permission_groups"] = permission_groups
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Uprawnienia pracownika {self.object.get_full_name() or self.object.email} zostały zapisane.",
        )
        return response


class RoleGroupFormContextMixin:
    template_name = "app/pracownik/permission_group_form.html"
    form_class = CompanyRoleGroupForm
    success_url = reverse_lazy("employee_permission_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.user.company
        kwargs["permission_queryset"] = get_assignable_permissions()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_permission_form_context(context["form"]))
        return context


class CompanyRoleGroupCreateView(
    OwnerPermissionManagementMixin,
    RoleGroupFormContextMixin,
    CreateView,
):
    model = CompanyRoleGroup

    def form_valid(self, form):
        with transaction.atomic():
            auth_group = Group.objects.create(
                name=f"company-role:{self.request.user.company_id}:{uuid4().hex}"
            )
            role_group = form.save(commit=False)
            role_group.company = self.request.user.company
            role_group.group = auth_group
            role_group.save()
            form.save_m2m()

        messages.success(self.request, f"Grupa {role_group.name} została utworzona.")
        return redirect(self.success_url)


class CompanyRoleGroupUpdateView(
    OwnerPermissionManagementMixin,
    RoleGroupFormContextMixin,
    UpdateView,
):
    model = CompanyRoleGroup
    context_object_name = "role_group"

    def get_queryset(self):
        return CompanyRoleGroup.objects.filter(
            company_id=self.request.user.company_id,
        ).select_related("group")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Grupa {self.object.name} została zaktualizowana.")
        return response


class CompanyRoleGroupDeleteView(OwnerPermissionManagementMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        role_group = get_object_or_404(
            CompanyRoleGroup.objects.select_related("group"),
            pk=pk,
            company_id=request.user.company_id,
        )
        group_name = role_group.name
        if role_group.is_system:
            messages.error(request, "Domyślnej grupy roli nie można usunąć.")
            return redirect("employee_permission_list")
        role_group.delete()
        messages.success(request, f"Grupa {group_name} została usunięta.")
        return redirect("employee_permission_list")
