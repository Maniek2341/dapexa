from datetime import timedelta
import pdfkit
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.conf import settings

from app.protokol.models import Protocol
from app.core.models import CompanySettings
from app.core.pdf_utils import get_company_logo_url


class ProtocolPDFView(LoginRequiredMixin, View):

    def get(self, request, pk):

        protocol = get_object_or_404(
            Protocol,
            pk=pk,
            company=request.user.company
        )

        company = request.user.company

        end_time = protocol.end_time
        start_time_calculated = None

        if end_time and protocol.robocizna:
            hours = float(protocol.robocizna)
            start_time_calculated = end_time - timedelta(hours=float(protocol.robocizna))

        html = render_to_string(
            "app/pdf/protokol.html",
            {
                "protocol": protocol,
                "company": company,
                "start_time_calculated": start_time_calculated,
                "request": request,
                "STATIC_ROOT": settings.STATIC_ROOT,
                "company_logo_url": get_company_logo_url(request, company),
            }
        )

        config = pdfkit.configuration(
            wkhtmltopdf=settings.WKHTMLTOPDF_CMD
        )

        options = {
            "page-size": "A4",
            "margin-top": "15mm",
            "margin-bottom": "15mm",
            "margin-left": "15mm",
            "margin-right": "15mm",
            "encoding": "UTF-8",
            "enable-local-file-access": "",
        }

        pdf = pdfkit.from_string(
            html,
            False,
            configuration=config,
            options=options
        )

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Protokol_{protocol.number}.pdf"'
        )

        return response
