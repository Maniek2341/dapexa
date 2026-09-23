from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

User = get_user_model()


@method_decorator(csrf_protect, name="dispatch")
class EmployeeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    http_method_names = ["post"]
    permission_required = "core.access_employee_delete"

    def has_permission(self):
        if self.request.user.role not in [User.Role.OWNER, User.Role.MANAGER]:
            return False

        # Właściciel ma pełne uprawnienia w obrębie swojej firmy.
        if self.request.user.role == User.Role.OWNER:
            return True

        # Manager musi dodatkowo otrzymać uprawnienie bezpośrednio lub przez grupę.
        return super().has_permission()

    def post(self, request, pk):
        if pk == request.user.pk:
            messages.error(request, "Nie możesz usunąć własnego konta.")
            return redirect("employee_list")

        if request.user.company_id is None:
            messages.error(request, "Twoje konto nie jest przypisane do firmy.")
            return redirect("employee_list")

        try:
            with transaction.atomic():
                employee = get_object_or_404(
                    User.objects
                    .select_for_update()
                    .exclude(role=User.Role.CLIENT),
                    pk=pk,
                    company_id=request.user.company_id,
                )

                if employee.role == User.Role.OWNER:
                    messages.error(request, "Nie możesz usunąć konta właściciela firmy.")
                    return redirect("employee_list")

                if (
                    request.user.role == User.Role.MANAGER
                    and employee.role == User.Role.MANAGER
                ):
                    messages.error(request, "Manager nie może usunąć innego managera.")
                    return redirect("employee_list")

                if employee.is_superuser or employee.is_admin:
                    messages.error(request, "Nie możesz usunąć konta uprzywilejowanego.")
                    return redirect("employee_list")

                employee_name = (
                    f"{employee.first_name} {employee.last_name}".strip()
                    or employee.email
                )
                employee.delete()
        except ProtectedError:
            messages.error(
                request,
                "Nie można usunąć pracownika, ponieważ jest powiązany z innymi danymi. "
                "Zamiast tego oznacz go jako nieaktywnego.",
            )
            return redirect("employee_list")

        messages.success(request, f"Pracownik {employee_name} został usunięty.")
        return redirect("employee_list")
