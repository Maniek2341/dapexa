from django.urls import path

from app.urlop.views import (LeaveRequestCreateView, LeaveTypeCreateView, LeaveTypeUpdateView, LeaveTypeListView, LeaveAllowanceListView, 
GenerateLeaveAllowancesView, HRLeaveListView, HRLeaveApproveView, HRLeaveRejectView, HRLeaveCancelView, HRLeavePDFView, LeaveTypeUpdateView, LeaveTypeDeleteView)

urlpatterns = [
    path("add/", LeaveRequestCreateView.as_view(), name="urlop_add"),
    path("types/add/", LeaveTypeCreateView.as_view(), name="leave_type_add"),
    path("types/<int:pk>/edit/", LeaveTypeUpdateView.as_view(), name="leave_type_edit"),
    path("types/<int:pk>/delete/", LeaveTypeDeleteView.as_view(), name="leave_type_delete"),
    path("types/", LeaveTypeListView.as_view(), name="leave_type_list"),
    path("allowances/", LeaveAllowanceListView.as_view(), name="leave_allowance_list"),
    path("allowances/generate/", GenerateLeaveAllowancesView.as_view(), name="generate_leave_allowances"),
    path("hr/leaves/", HRLeaveListView.as_view(), name="hr_leave_list"),
    path("hr/leaves/<int:pk>/approve/", HRLeaveApproveView.as_view(), name="hr_leave_approve"),
    path("hr/leaves/<int:pk>/reject/", HRLeaveRejectView.as_view(), name="hr_leave_reject"),
    path("hr/leaves/<int:pk>/cancel/", HRLeaveCancelView.as_view(), name="hr_leave_cancel"),
    path("hr/leaves/<int:pk>/pdf/", HRLeavePDFView.as_view(), name="hr_leave_pdf"),
]
