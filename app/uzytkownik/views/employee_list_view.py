from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from app.core.utils import get_employee_completion

User = get_user_model()


class EmployeeListView(LoginRequiredMixin, ListView):
    model = User
    template_name = "app/pracownik/list.html"
    context_object_name = "employees"

    def get_queryset(self):
        return (
            User.objects
            .filter(company=self.request.user.company)
            .exclude(role=User.Role.CLIENT)
            .order_by("last_name", "first_name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        employees = context["employees"]
        for employee in employees:
            employee.completion = get_employee_completion(employee)

        context["active_count"] = employees.filter(is_active=True, is_active_employee=True).count()
        context["can_manage_employee_status"] = (
            self.request.user.company_id is not None
            and self.request.user.role in {User.Role.OWNER, User.Role.MANAGER, User.Role.BIURO}
            and (
                self.request.user.role == User.Role.OWNER
                or self.request.user.has_perm("core.access_employee_status_toggle")
            )
        )
        context["manager_count"] = employees.filter(role=User.Role.MANAGER).count()

        return context
