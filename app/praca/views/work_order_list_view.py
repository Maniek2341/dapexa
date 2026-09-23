from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models import Sum

from app.praca.models import WorkOrder
from app.praca.permissions import has_work_permission
from app.oferta_praca.models import OfferVariant
from app.core.models import CompanySettings


User = get_user_model()


class WorkOrderListView(LoginRequiredMixin, ListView):
    model = WorkOrder
    template_name = "app/praca/workorder_list.html"
    context_object_name = "works"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            WorkOrder.objects
            .filter(company=self.request.user.company)
            .select_related("client", "location", "offer")
            .prefetch_related("assigned_employees")
            .order_by("-id")
        )

        self.q = self.request.GET.get("q", "").strip()
        self.active_status = self.request.GET.get("status", "all")

        allowed = {
            "new": WorkOrder.Status.NEW,
            "in_progress": WorkOrder.Status.IN_PROGRESS,
            "done": WorkOrder.Status.DONE,
            "cancelled": WorkOrder.Status.CANCELLED,
        }

        if self.active_status in allowed:
            qs = qs.filter(status=allowed[self.active_status])

        if self.q:
            qs = qs.filter(
                Q(number__icontains=self.q) |
                Q(title__icontains=self.q) |
                Q(client__name__icontains=self.q) |
                Q(client__first_name__icontains=self.q) |
                Q(client__last_name__icontains=self.q) |
                Q(location__name__icontains=self.q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["workers"] = User.objects.filter(
            company=self.request.user.company,
            is_active=True,
        ).order_by("first_name", "last_name", "email")

        context["q"] = getattr(self, "q", "")
        context["active_status"] = getattr(self, "active_status", "all")
        for action in (
            "work_schedule_update", "work_assign_workers", "work_mark_ordered",
        ):
            context[f"can_{action}"] = has_work_permission(self.request.user, action)
        context["can_work_actions"] = any(
            context[f"can_{action}"]
            for action in ("work_schedule_update", "work_assign_workers", "work_mark_ordered")
        )
        visible_works = self.object_list
        offer_ids = list(visible_works.values_list("offer_id", flat=True))
        selected_variants = OfferVariant.objects.filter(
            offer_id__in=offer_ids, is_selected=True
        )
        variant_totals = selected_variants.aggregate(
            total=Sum("total_netto"),
            materials=Sum("materials_netto"),
            accessories=Sum("accessories_netto"),
        )
        # Jeżeli oferta ma warianty, jej suma musi wynikać wyłącznie z
        # aktualnie zaznaczonych wariantów. Nie wolno wracać wtedy do
        # zapisanej w pracy kwoty, bo ta mogła powstać przed odznaczeniem
        # wariantu. Zapisana kwota jest fallbackiem tylko dla ofert bez
        # żadnych wariantów.
        offers_with_variants = OfferVariant.objects.filter(
            offer_id__in=offer_ids
        ).values_list("offer_id", flat=True)
        fallback_total = visible_works.exclude(
            offer_id__in=offers_with_variants
        ).aggregate(total=Sum("total_netto"))["total"] or 0
        total_netto = (variant_totals["total"] or 0) + fallback_total
        materials = variant_totals["materials"] or 0
        accessories = variant_totals["accessories"] or 0
        context["work_summary"] = {
            "total_netto": total_netto,
            "materials": materials,
            "accessories": accessories,
            "profit": total_netto - materials - accessories,
        }
        context["can_view_work_prices"] = getattr(self.request.user, "role", None) not in {
            self.request.user.Role.EMPLOYEE,
            self.request.user.Role.PODWYKONAWCA,
        }
        company_settings = CompanySettings.objects.filter(
            company=self.request.user.company
        ).only("default_work_start_time", "default_work_end_time").first()
        context["workday_start_time"] = company_settings.default_work_start_time.strftime("%H:%M") if company_settings else "07:00"
        context["workday_end_time"] = company_settings.default_work_end_time.strftime("%H:%M") if company_settings else "15:00"
        return context
