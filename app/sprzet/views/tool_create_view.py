# app/sprzet/views/tool_create_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView

from app.sprzet.forms import ToolCreateForm
from app.sprzet.models import (
    Tool,
    ToolStatus,
    ToolHistory,
    ToolHistoryType,
)


class ToolCreateView(LoginRequiredMixin, CreateView):
    model = Tool
    form_class = ToolCreateForm
    template_name = "app/sprzet/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        form.instance.created_by = self.request.user

        if form.instance.current_holder:
            form.instance.status = ToolStatus.IN_USE

        response = super().form_valid(form)

        ToolHistory.objects.create(
            company=self.request.user.company,
            tool=self.object,
            type=ToolHistoryType.CREATED,
            title="Dodano sprzęt",
            description=f"Utworzono sprzęt: {self.object.name}.",
            created_by=self.request.user,
        )

        messages.success(
            self.request,
            "Sprzęt został dodany."
        )

        return response

    def get_success_url(self):
        return redirect("tool_list").url