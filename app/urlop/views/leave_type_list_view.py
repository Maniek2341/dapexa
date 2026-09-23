from django.views import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Count

from app.urlop.models import LeaveType


class LeaveTypeListView(LoginRequiredMixin, View):

    login_url = reverse_lazy("login")
    template_name = "app/urlop/leave_type_list.html"

    def get(self, request):
        leave_types = LeaveType.objects.filter(
            company=request.user.company
        ).annotate(
            usage_count=Count("leaverequest")
        ).order_by("name")

        return render(request, self.template_name, {
            "leave_types": leave_types
        })