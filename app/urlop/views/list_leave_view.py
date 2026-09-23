from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages

from app.urlop.models import LeaveRequest


class HRLeaveListView(LoginRequiredMixin, View):

    template_name = "app/urlop/hr_leave_list.html"

    def get(self, request):

        if request.user.role not in ["owner", "manager"]:
            return redirect("dashboard")

        status = request.GET.get("status")

        leaves = LeaveRequest.objects.filter(
            company=request.user.company
        ).select_related("user", "leave_type").order_by("-created_at")

        if status:
            leaves = leaves.filter(status=status)

        return render(request, self.template_name, {
            "leaves": leaves,
            "active_status": status
        })

class HRLeaveApproveView(LoginRequiredMixin, View):

    def get(self, request, pk):
        leave = get_object_or_404(
            LeaveRequest,
            pk=pk,
            company=request.user.company
        )

        if request.user.role not in ["owner", "manager"]:
            return redirect("dashboard")

        leave.status = LeaveRequest.Status.APPROVED
        leave.approver = request.user
        leave.save()

        messages.success(request, "Wniosek zatwierdzony.")
        return redirect("hr_leave_list")


class HRLeaveRejectView(LoginRequiredMixin, View):

    def get(self, request, pk):
        leave = get_object_or_404(
            LeaveRequest,
            pk=pk,
            company=request.user.company
        )

        if request.user.role not in ["owner", "manager"]:
            return redirect("dashboard")

        leave.status = LeaveRequest.Status.REJECTED
        leave.approver = request.user
        leave.save()

        messages.warning(request, "Wniosek odrzucony.")
        return redirect("hr_leave_list")


class HRLeaveCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        leave = get_object_or_404(
            LeaveRequest, pk=pk, company=request.user.company
        )
        if request.user.role not in ["owner", "manager"]:
            return redirect("dashboard")
        if leave.status != LeaveRequest.Status.APPROVED:
            messages.error(request, "Można anulować tylko zatwierdzony urlop.")
            return redirect("hr_leave_list")

        leave.status = LeaveRequest.Status.CANCELLED
        leave.save(update_fields=["status", "days_count", "updated_at"])
        messages.success(request, "Zatwierdzony urlop został anulowany.")
        return redirect("hr_leave_list")
