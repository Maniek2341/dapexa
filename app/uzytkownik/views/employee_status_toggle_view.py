from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views import View

User = get_user_model()


class EmployeeStatusToggleView(LoginRequiredMixin, View):
    """Toggle an employee's panel access without changing activation password state."""

    def post(self, request, pk):
        if request.user.role not in {User.Role.OWNER, User.Role.MANAGER, User.Role.BIURO}:
            raise PermissionDenied

        employee = get_object_or_404(
            User,
            pk=pk,
            company_id=request.user.company_id,
        )
        if employee.pk == request.user.pk or employee.role == User.Role.OWNER:
            raise PermissionDenied("Nie można zmienić statusu tego użytkownika.")

        employee.is_active_employee = not employee.is_active_employee
        employee.save(update_fields=["is_active_employee", "updated_at"])
        state = "aktywowano" if employee.is_active_employee else "dezaktywowano"
        messages.success(request, f"Konto pracownika {employee.get_full_name() or employee.email} zostało {state}.")
        return redirect("employee_list")
