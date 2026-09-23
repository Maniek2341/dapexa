# app/sprzet/views/tool_detail_view.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from app.sprzet.forms import ToolEventForm
from app.sprzet.models import Tool
from app.sprzet.permissions import can_edit_tool, can_delete_tool


class ToolDetailView(LoginRequiredMixin, DetailView):
    model = Tool
    template_name = "app/sprzet/detail.html"
    context_object_name = "tool"

    def get_queryset(self):
        return (
            Tool.objects
            .filter(company=self.request.user.company)
            .select_related(
                "current_holder",
                "created_by",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["assignments"] = (
            self.object.assignments
            .select_related(
                "user",
                "assigned_by",
            )
            .order_by("-assigned_at")[:10]
        )

        context["events"] = (
            self.object.events
            .select_related("created_by")
            .prefetch_related("media")
            .order_by("-event_date", "-created_at")
        )

        context["history"] = (
            self.object.history
            .select_related("created_by")
            .order_by("-created_at")
        )

        context["event_form"] = ToolEventForm()
        context["can_edit_tool"] = can_edit_tool(self.request.user)
        context["can_delete_tool"] = can_delete_tool(self.request.user)

        return context
