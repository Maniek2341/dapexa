"""Wspólne dane firmowe wykorzystywane podczas generowania dokumentów PDF."""

from django.templatetags.static import static


def get_company_logo_url(request, company):
    """Zwraca absolutny adres logo firmy albo domyślnego logo aplikacji.

    Wkhtmltopdf renderuje dokument poza kontekstem przeglądarki, dlatego adres
    musi być absolutny. Dzięki fallbackowi każdy dokument zachowuje logo nawet
    wtedy, gdy firma nie ma jeszcze własnego pliku.
    """
    logo_url = None
    if company is not None:
        logo = getattr(company, "logo", None)
        if logo:
            try:
                logo_url = logo.url
            except (ValueError, AttributeError):
                logo_url = None

    return request.build_absolute_uri(logo_url or static("assets/img/logo.png"))
