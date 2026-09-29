"""Render server-owned PDF templates without public access to private media."""
import base64
from io import BytesIO
from pathlib import Path

import pdfkit
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.contrib.staticfiles import finders


def get_company_logo_url(request, company):
    """Embed a rasterized logo: wkhtmltopdf has no authenticated browser session."""
    logo = getattr(company, 'logo', None)
    source = None
    if logo:
        root = Path(settings.MEDIA_ROOT).resolve()
        candidate = Path(logo.path).resolve()
        if candidate.is_relative_to(root):
            source = candidate
    if source is None or not source.is_file():
        source = finders.find('assets/img/logo.png')
    if not source:
        return ''
    try:
        with Image.open(source) as img:
            img.thumbnail((1200, 1200))
            output = BytesIO()
            img.convert('RGBA').save(output, format='PNG')
        return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode('ascii')
    except (OSError, ValueError, UnidentifiedImageError):
        return ''


def render_pdf(html, options=None):
    """Use one explicit renderer configuration for all three PDF views."""
    pdf_options = dict(options or {})
    pdf_options.pop('enable-local-file-access', None)
    pdf_options.update({
        'disable-local-file-access': '',
        'disable-javascript': '',
        'encoding': 'UTF-8',
        'quiet': '',
    })
    return pdfkit.from_string(
        html, False,
        configuration=pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_CMD),
        options=pdf_options,
    )
