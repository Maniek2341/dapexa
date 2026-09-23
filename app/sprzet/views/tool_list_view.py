# app/sprzet/views/tool_list_view.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from app.sprzet.models import Tool, ToolStatus
from app.sprzet.forms import ToolEventForm
from app.sprzet.permissions import can_edit_tool, can_delete_tool

class ToolListView(LoginRequiredMixin, ListView):
    model = Tool
    template_name = "app/sprzet/list.html"
    context_object_name = "tools"
    paginate_by = 24

    def get_queryset(self):
        queryset = (
            Tool.objects
            .filter(company=self.request.user.company)
            .select_related("current_holder")
            .order_by("name")
        )

        search = self.request.GET.get("q")
        status = self.request.GET.get("status")
        category = self.request.GET.get("category")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(manufacturer__icontains=search)
                | Q(model__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(inventory_number__icontains=search)
            )

        if status:
            queryset = queryset.filter(status=status)

        if category:
            queryset = queryset.filter(category=category)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["statuses"] = ToolStatus.choices
        context["categories"] = Tool._meta.get_field("category").choices

        context["current_q"] = self.request.GET.get("q", "")
        context["current_status"] = self.request.GET.get("status", "")
        context["current_category"] = self.request.GET.get("category", "")

        context["event_form"] = ToolEventForm()
        context["can_edit_tool"] = can_edit_tool(self.request.user)
        context["can_delete_tool"] = can_delete_tool(self.request.user)

        context["stats"] = {
            "all": Tool.objects.filter(
                company=self.request.user.company
            ).count(),

            "available": Tool.objects.filter(
                company=self.request.user.company,
                status=ToolStatus.AVAILABLE
            ).count(),

            "in_use": Tool.objects.filter(
                company=self.request.user.company,
                status=ToolStatus.IN_USE
            ).count(),

            "service": Tool.objects.filter(
                company=self.request.user.company,
                status=ToolStatus.SERVICE
            ).count(),
        }

        return context
