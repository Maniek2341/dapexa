from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from app.urlop.access import LeavePermissionMixin

from app.urlop.models import LeaveRequest
from app.core.pdf_utils import get_company_logo_url, render_pdf


class HRLeavePDFView(LeavePermissionMixin, View):
    leave_permission = "hr_leave_pdf"

    def get(self, request, pk):

        leave = get_object_or_404(
            LeaveRequest,
            pk=pk,
            company=request.user.company
        )

        html = render_to_string(
            "app/pdf/leave_request_pdf.html",
            {
                "leave": leave,
                "company": request.user.company,
                "company_logo_url": get_company_logo_url(request, request.user.company),
            },
            request=request,
        )

        pdf = render_pdf(html)

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="wniosek_urlopowy_{leave.id}.pdf"'

        return response
