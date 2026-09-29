from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from app.core.emails import send_employee_activation_email
from .employee_status_toggle_view import EmployeeStatusPermissionMixin


@method_decorator(csrf_protect, name="dispatch")
class EmployeeResendActivationView(EmployeeStatusPermissionMixin, View):
    http_method_names = ["post"]

    @transaction.atomic
    def post(self, request, pk):
        employee = self.get_employee(request, pk)
        if employee.has_usable_password():
            messages.error(request, "Pracownik ma już ustawione hasło.")
            return redirect("employee_list")
        try:
            send_employee_activation_email(employee)
        except Exception:
            messages.error(request, "Nie udało się wysłać linku aktywacyjnego. Spróbuj ponownie za chwilę.")
            return redirect("employee_list")
        messages.success(request, f"Link aktywacyjny został ponownie wysłany na adres {employee.email}.")
        return redirect("employee_list")
