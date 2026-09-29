from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.db import transaction

User = get_user_model()


class EmployeeStatusPermissionMixin(LoginRequiredMixin):
    def get_employee(self, request, pk):
        if (
            request.user.company_id is None
            or request.user.role not in {User.Role.OWNER, User.Role.MANAGER, User.Role.BIURO}
            or (
                request.user.role != User.Role.OWNER
                and not request.user.has_perm("core.access_employee_status_toggle")
            )
        ):
            raise PermissionDenied
        employee = get_object_or_404(
            User.objects.select_for_update().exclude(role=User.Role.CLIENT),
            pk=pk, company_id=request.user.company_id,
        )
        if employee.pk == request.user.pk or employee.role == User.Role.OWNER:
            raise PermissionDenied("Nie można zmienić statusu tego użytkownika.")
        return employee


@method_decorator(csrf_protect, name="dispatch")
class EmployeeStatusToggleView(EmployeeStatusPermissionMixin, View):
    """Toggle an employee's panel access without changing activation password state."""

    http_method_names = ["post"]

    @transaction.atomic
    def post(self, request, pk):
        employee = self.get_employee(request, pk)
        if not employee.is_active_employee and (
            not employee.is_active or not employee.has_usable_password()
        ):
            messages.error(
                request,
                "Nie można aktywować pracownika, ponieważ konto jest nieaktywne lub pracownik nie ustawił jeszcze hasła. "
                "Wyślij ponownie link aktywacyjny.",
            )
            return redirect("employee_list")

        employee.is_active_employee = not employee.is_active_employee
        employee.save(update_fields=["is_active_employee", "updated_at"])
        state = "aktywowano" if employee.is_active_employee else "dezaktywowano"
        messages.success(request, f"Status pracownika {employee.get_full_name() or employee.email}: {state}.")
        return redirect("employee_list")
