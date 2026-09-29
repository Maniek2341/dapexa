from datetime import date
from decimal import Decimal

from django.db import transaction

from app.core.models import PanelUser
from .models import LeaveAllowance


def vacation_entitlement_days(user, year: int) -> Decimal:
    return user.get_vacation_entitlement(as_of=date(year, 12, 31))


def prorata_for_year(user, year: int, base_days: Decimal) -> Decimal:
    # Kept as a compatibility wrapper; the shared entitlement method includes
    # employment fraction and the hire-date proportion for the requested year.
    return base_days


def ensure_allowance(company, user, year: int, carryover: Decimal = Decimal("0")) -> LeaveAllowance:
    limit = vacation_entitlement_days(user, year)
    with transaction.atomic():
        allowance, created = LeaveAllowance.objects.select_for_update().get_or_create(
            company=company,
            user=user,
            year=year,
            defaults={
                "vacation_limit": limit,
                "carryover_days": carryover,
                "on_demand_limit": Decimal("4"),
                "carryover_deadline": date(year, 9, 30),
            },
        )
        # Generators create missing records only; they never overwrite HR edits,
        # carryover, corrections, limits or locked records on a rerun.
        return allowance


def ensure_employee_year_allowance(company, user, year: int) -> LeaveAllowance:
    """Create a missing yearly entitlement from seniority and prior-year carryover."""
    carryover = calculate_carryover(company, user, year - 1)
    return ensure_allowance(company, user, year, carryover=carryover)


def eligible_leave_users(company):
    return PanelUser.objects.filter(
        company=company,
        is_active=True,
        is_active_employee=True,
    ).exclude(role__in=[PanelUser.Role.CLIENT, PanelUser.Role.PODWYKONAWCA])


def calculate_carryover(company, user, previous_year):
    try:
        previous = LeaveAllowance.objects.get(company=company, user=user, year=previous_year)
    except LeaveAllowance.DoesNotExist:
        return Decimal("0")

    from .services import used_regular_vacation_days

    return max(
        Decimal("0"),
        previous.vacation_limit + previous.adjustment_days
        - used_regular_vacation_days(company, user, previous_year),
    )


def ensure_year_allowances(company, year):
    created = 0
    with transaction.atomic():
        for user in eligible_leave_users(company).order_by("pk"):
            carryover = calculate_carryover(company, user, year - 1)
            _, was_created = LeaveAllowance.objects.get_or_create(
                company=company,
                user=user,
                year=year,
                defaults={
                    "vacation_limit": vacation_entitlement_days(user, year),
                    "carryover_days": carryover,
                    "on_demand_limit": Decimal("4"),
                    "carryover_deadline": date(year, 9, 30),
                },
            )
            created += int(was_created)
    return created
