import pdfkit
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from app.urlop.models import LeaveRequest
from app.core.pdf_utils import get_company_logo_url


class HRLeavePDFView(LoginRequiredMixin, View):

    def get(self, request, pk):

        leave = get_object_or_404(
            LeaveRequest,
            pk=pk,
            company=request.user.company
        )

        if request.user.role not in ["owner", "manager"]:
            return redirect("dashboard")

        html = render_to_string(
            "app/pdf/leave_request_pdf.html",
            {
                "leave": leave,
                "company": request.user.company,
                "company_logo_url": get_company_logo_url(request, request.user.company),
            },
            request=request,
        )

        pdf = pdfkit.from_string(html, False)

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="wniosek_urlopowy_{leave.id}.pdf"'

        return response
