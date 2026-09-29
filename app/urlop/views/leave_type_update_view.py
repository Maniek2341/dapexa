from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.shortcuts import render

from app.urlop.forms import LeaveTypeForm
from app.urlop.models import LeaveType
from app.urlop.access import LeavePermissionMixin


class LeaveTypeUpdateView(LeavePermissionMixin, View):
    leave_permission = "leave_type_edit"

    template_name = "app/urlop/urlop_type_form.html"

    def get(self, request, pk):
        leave_type = get_object_or_404(
            LeaveType,
            pk=pk,
            company=request.user.company
        )
        form = LeaveTypeForm(instance=leave_type, company=request.user.company)
        return render(request, self.template_name, {
            "form": form,
            "object": leave_type
        })

    def post(self, request, pk):
        leave_type = get_object_or_404(
            LeaveType,
            pk=pk,
            company=request.user.company
        )
        form = LeaveTypeForm(request.POST, instance=leave_type, company=request.user.company)

        if form.is_valid():
            form.save()
            messages.success(request, "Rodzaj urlopu został zaktualizowany.")
            return redirect("leave_type_list")

        return render(request, self.template_name, {
            "form": form,
            "object": leave_type
        })
