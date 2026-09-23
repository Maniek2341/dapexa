from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from app.urlop.models import LeaveType, LeaveRequest


class LeaveTypeDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/urlop/leave_type_confirm_delete.html"

    def get_object(self, request, pk):
        return get_object_or_404(
            LeaveType,
            pk=pk,
            company=request.user.company,
        )

    def get(self, request, pk, *args, **kwargs):
        leave_type = self.get_object(request, pk)

        is_used = LeaveRequest.objects.filter(
            company=request.user.company,
            leave_type=leave_type,
        ).exists()

        return render(request, self.template_name, {
            "leave_type": leave_type,
            "is_used": is_used,
        })

    def post(self, request, pk, *args, **kwargs):
        leave_type = self.get_object(request, pk)

        is_used = LeaveRequest.objects.filter(
            company=request.user.company,
            leave_type=leave_type,
        ).exists()

        if is_used:
            messages.error(
                request,
                f'Nie można usunąć rodzaju urlopu "{leave_type.name}", ponieważ został już użyty we wnioskach.'
            )
            return redirect("leave_type_list")

        leave_type.delete()
        messages.success(request, f'Rodzaj urlopu "{leave_type.name}" został usunięty.')
        return redirect("leave_type_list")