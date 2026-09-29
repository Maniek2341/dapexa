from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from app.urlop.access import LeavePermissionMixin
from app.urlop.models import LeaveRequest
from app.urlop.services import cancel_leave_request, decide_leave_request


class HRLeaveListView(LeavePermissionMixin, View):
    leave_permission = "hr_leave_list"
    template_name = "app/urlop/hr_leave_list.html"

    def get(self, request):
        status = request.GET.get("status")
        valid_statuses = {value for value, _ in LeaveRequest.Status.choices}
        leaves = LeaveRequest.objects.filter(company=request.user.company).select_related(
            "user", "leave_type", "approver",
        ).order_by("-created_at")
        if status in valid_statuses:
            leaves = leaves.filter(status=status)
        elif status:
            status = None
        return render(request, self.template_name, {"leaves": leaves, "active_status": status})


class HRLeaveApproveView(LeavePermissionMixin, View):
    leave_permission = "hr_leave_approve"

    def post(self, request, pk):
        try:
            decide_leave_request(request.user.company, request.user, pk, LeaveRequest.Status.APPROVED)
        except LeaveRequest.DoesNotExist:
            get_object_or_404(LeaveRequest, pk=pk, company=request.user.company)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Wniosek zatwierdzony.")
        return redirect("hr_leave_list")


class HRLeaveRejectView(LeavePermissionMixin, View):
    leave_permission = "hr_leave_reject"

    def post(self, request, pk):
        try:
            decide_leave_request(request.user.company, request.user, pk, LeaveRequest.Status.REJECTED)
        except LeaveRequest.DoesNotExist:
            get_object_or_404(LeaveRequest, pk=pk, company=request.user.company)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.warning(request, "Wniosek odrzucony.")
        return redirect("hr_leave_list")


class HRLeaveCancelView(LeavePermissionMixin, View):
    leave_permission = "hr_leave_cancel"

    def post(self, request, pk):
        try:
            cancel_leave_request(request.user.company, request.user, pk)
        except LeaveRequest.DoesNotExist:
            get_object_or_404(LeaveRequest, pk=pk, company=request.user.company)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Zatwierdzony urlop został anulowany.")
        return redirect("hr_leave_list")
