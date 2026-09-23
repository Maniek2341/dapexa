# app/sprzet/views/tool_update_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import UpdateView

from app.sprzet.forms import ToolCreateForm
from app.sprzet.models import (
    Tool,
    ToolStatus,
    ToolHistory,
    ToolHistoryType,
)
from django.core.exceptions import PermissionDenied
from app.sprzet.permissions import can_edit_tool


class ToolUpdateView(LoginRequiredMixin, UpdateView):
    model = Tool
    form_class = ToolCreateForm
    template_name = "app/sprzet/form.html"
    context_object_name = "tool"

    def get_queryset(self):
        if not can_edit_tool(self.request.user):
            raise PermissionDenied
        return Tool.objects.filter(
            company=self.request.user.company,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_tool = Tool.objects.get(pk=self.object.pk)

        old_status = old_tool.status
        old_holder = old_tool.current_holder

        if form.instance.current_holder:
            form.instance.status = ToolStatus.IN_USE

        response = super().form_valid(form)

        changes = []

        if old_status != self.object.status:
            changes.append(
                f"Status: {old_tool.get_status_display()} → {self.object.get_status_display()}"
            )

        if old_holder != self.object.current_holder:
            old_holder_name = old_holder or "Brak"
            new_holder_name = self.object.current_holder or "Brak"

            changes.append(
                f"Przypisanie: {old_holder_name} → {new_holder_name}"
            )

        if form.changed_data:
            changes.append(
                "Zmienione pola: " + ", ".join(form.changed_data)
            )

        ToolHistory.objects.create(
            company=self.request.user.company,
            tool=self.object,
            type=ToolHistoryType.UPDATED,
            title="Zaktualizowano sprzęt",
            description="\n".join(changes) if changes else "Zapisano formularz edycji.",
            created_by=self.request.user,
        )

        messages.success(
            self.request,
            "Sprzęt został zaktualizowany."
        )

        return response

    def get_success_url(self):
        return reverse("tool_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context
