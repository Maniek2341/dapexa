import logging

from celery import shared_task
from django.utils import timezone

from app.core.models import Company
from .allowance_generator import ensure_year_allowances

logger = logging.getLogger(__name__)


@shared_task
def generate_leave_allowances_for_year(year: int = None):
    year = year or timezone.localdate().year
    created = 0
    for company in Company.objects.iterator():
        try:
            created += ensure_year_allowances(company, year)
        except Exception:
            logger.exception("Nie udało się wygenerować limitów urlopowych dla firmy %s, rok %s", company.pk, year)
            raise
    return created
