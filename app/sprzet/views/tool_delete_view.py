# app/sprzet/views/tool_delete_view.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View
from django.core.exceptions import PermissionDenied
from app.sprzet.permissions import can_delete_tool

from app.sprzet.models import Tool


class ToolDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not can_delete_tool(request.user):
            raise PermissionDenied
        tool = (
            Tool.objects
            .filter(pk=pk, company=request.user.company)
            .first()
        )

        if not tool:
            messages.error(request, "Nie znaleziono sprzętu.")
            return redirect("tool_list")

        name = str(tool)
        tool.delete()

        messages.success(request, f"Sprzęt „{name}” został usunięty.")
        return redirect("tool_list")
