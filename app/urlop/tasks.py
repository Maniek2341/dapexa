# app/leaves/tasks.py
from celery import shared_task
from django.utils import timezone
from app.core.models import Company, PanelUser  # dostosuj importy
from .allowance_generator import ensure_allowance
from .carryover import compute_carryover

@shared_task
def generate_leave_allowances_for_year(year: int = None):
    if year is None:
        year = timezone.now().year

    for company in Company.objects.all():
        users = PanelUser.objects.filter(company=company, is_active=True)

        for u in users:
            # carryover z poprzedniego roku
            carry = 0
            prev_year = year - 1
            try:
                carry = compute_carryover(company, u, prev_year)
            except Exception:
                carry = 0

            ensure_allowance(company, u, year, carryover=carry)