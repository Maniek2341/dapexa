# app/praca/views.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from django.db.models import Prefetch
from django.contrib.auth import get_user_model

from app.praca.models import WorkOrder
from app.praca.permissions import has_work_permission
from app.core.models import CompanySettings


User = get_user_model()


class WorkDetailView(LoginRequiredMixin, DetailView):
    model = WorkOrder
    template_name = "app/praca/work_detail.html"
    context_object_name = "work"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        work = context["work"]

        if work.offer:
            selected_variants = work.offer.variants.filter(is_selected=True)
        else:
            selected_variants = []

        context["selected_variants"] = selected_variants
        context["can_work_schedule_update"] = has_work_permission(self.request.user, "work_schedule_update")
        context["can_work_assign_workers"] = has_work_permission(self.request.user, "work_assign_workers")
        context["can_work_mark_ordered"] = has_work_permission(self.request.user, "work_mark_ordered")
        context["can_work_status"] = has_work_permission(self.request.user, "work_status_update")
        context["can_work_actions"] = any(
            (context["can_work_schedule_update"], context["can_work_assign_workers"], context["can_work_mark_ordered"])
        )
        context["can_view_work_prices"] = getattr(self.request.user, "role", None) not in {
            self.request.user.Role.EMPLOYEE,
            self.request.user.Role.PODWYKONAWCA,
        }
        context["can_view_work_attachments"] = getattr(self.request.user, "role", None) not in {
            self.request.user.Role.EMPLOYEE,
            self.request.user.Role.PODWYKONAWCA,
        }
        context["can_view_work_offer"] = getattr(self.request.user, "role", None) != self.request.user.Role.EMPLOYEE

        context["workers"] = User.objects.filter(
            company=self.request.user.company,
            is_active=True,
        ).order_by("first_name", "last_name", "email")
        company_settings = CompanySettings.objects.filter(company=self.request.user.company).only("default_work_start_time", "default_work_end_time").first()
        context["workday_start_time"] = company_settings.default_work_start_time.strftime("%H:%M") if company_settings else "07:00"
        context["workday_end_time"] = company_settings.default_work_end_time.strftime("%H:%M") if company_settings else "15:00"

        return context

    def get_queryset(self):
        return (
            WorkOrder.objects
            .filter(company=self.request.user.company)
            .select_related("client", "location", "created_by")
            .prefetch_related(
                "assigned_employees",
                "activities",
            )
        )
