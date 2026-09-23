# app/leaves/allowance_generator.py
from decimal import Decimal
from django.utils import timezone
from datetime import date
import calendar
from .models import LeaveAllowance

def vacation_entitlement_days(user, year: int) -> Decimal:
    # 20/26 wg stażu (>=10 lat => 26)
    seniority = user.get_total_seniority_years()  # Decimal
    base = Decimal("26") if seniority >= 10 else Decimal("20")
    return base

def prorata_for_year(user, year: int, base_days: Decimal) -> Decimal:
    # PROSTA wersja: jeśli zatrudnienie w trakcie roku => proporcjonalnie do dni zatrudnienia w roku
    if not getattr(user, "employment_start_date", None):
        return base_days

    start = user.employment_start_date
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    if start <= year_start:
        return base_days

    if start > year_end:
        return Decimal("0")

    days_in_year = Decimal(str(366 if calendar.isleap(year) else 365))
    employed_days = Decimal(str((year_end - start).days + 1))
    return (base_days * employed_days / days_in_year).quantize(Decimal("0.01"))

def ensure_allowance(company, user, year: int, carryover: Decimal = Decimal("0")) -> LeaveAllowance:
    base = vacation_entitlement_days(user, year)
    limit = prorata_for_year(user, year, base)

    obj, _ = LeaveAllowance.objects.update_or_create(
        company=company,
        user=user,
        year=year,
        defaults={
            "vacation_limit": limit,
            "carryover_days": carryover,
            "on_demand_limit": Decimal("4"),
            "carryover_deadline": date(year, 9, 30),  # przykładowo
        }
    )
    return obj