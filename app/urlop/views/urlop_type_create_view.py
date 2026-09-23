from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy

from app.urlop.models import LeaveType
from app.urlop.forms import LeaveTypeForm


class LeaveTypeCreateView(LoginRequiredMixin, View):

    template_name = "app/urlop/urlop_type_form.html"

    def get(self, request):
        form = LeaveTypeForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = LeaveTypeForm(request.POST)

        if form.is_valid():
            leave_type = form.save(commit=False)
            leave_type.company = request.user.company
            leave_type.save()

            messages.success(request, "Rodzaj urlopu został dodany.")
            return redirect("leave_type_list")

        return render(request, self.template_name, {"form": form})


