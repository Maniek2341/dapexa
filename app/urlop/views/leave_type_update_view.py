from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.views import View
from django.shortcuts import render

from app.urlop.forms import LeaveTypeForm
from app.urlop.models import LeaveType


class LeaveTypeUpdateView(LoginRequiredMixin, View):

    template_name = "app/urlop/urlop_type_form.html"

    def get(self, request, pk):
        leave_type = get_object_or_404(
            LeaveType,
            pk=pk,
            company=request.user.company
        )
        form = LeaveTypeForm(instance=leave_type)
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
        form = LeaveTypeForm(request.POST, instance=leave_type)

        if form.is_valid():
            form.save()
            messages.success(request, "Rodzaj urlopu został zaktualizowany.")
            return redirect("leave_type_list")

        return render(request, self.template_name, {
            "form": form,
            "object": leave_type
        })