from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View

from app.urlop.models import LeaveType, LeaveRequest
from app.urlop.access import LeavePermissionMixin


class LeaveTypeDeleteView(LeavePermissionMixin, View):
    leave_permission = "leave_type_delete"
    login_url = reverse_lazy("login")

    def get_object(self, request, pk):
        return get_object_or_404(
            LeaveType,
            pk=pk,
            company=request.user.company,
        )

    def get(self, request, pk, *args, **kwargs):
        self.get_object(request, pk)
        return redirect("leave_type_list")

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
