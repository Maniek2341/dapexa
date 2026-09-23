from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from app.urlop.services import get_allowance, used_on_demand_days, used_vacation_days
from app.urlop.models import LeaveAllowance, LeavePool, LeaveRequest
def validate_request_against_allowance(company, user, leave_type, year: int, requested_days: Decimal, is_carryover: bool):
    # nielimitowane
    if not leave_type.counts_against_limit:
        return

    # specjalne z własnym limitem, np. rodzicielski 30 dni
    if leave_type.is_special and leave_type.annual_limit_days > 0:
        used = (
            LeaveRequest.objects.filter(
                company=company,
                user=user,
                leave_type=leave_type,
                status=LeaveRequest.Status.APPROVED,
                leave_year=year,
            ).aggregate(s=Sum("days_count"))["s"]
            or Decimal("0")
        )

        if used + requested_days > leave_type.annual_limit_days:
            raise ValueError(
                f"Przekroczono limit dla urlopu {leave_type.name}. "
                f"Limit: {leave_type.annual_limit_days}, wykorzystane: {used}."
            )
        return

    # urlopy z puli vacation
    if leave_type.pool == LeavePool.VACATION:
        allowance = get_allowance(company, user, year)

        if leave_type.code == "na_zadanie":
            used_od = used_on_demand_days(company, user, year)
            if used_od + requested_days > allowance.on_demand_limit:
                raise ValueError(f"Przekroczono limit urlopu na żądanie ({allowance.on_demand_limit} dni).")

        if is_carryover and allowance.carryover_deadline:
            if timezone.now().date() > allowance.carryover_deadline:
                raise ValueError("Minął termin wykorzystania urlopu zaległego.")

        used = used_vacation_days(company, user, year)
        available = allowance.total_vacation_available()

        if used + requested_days > available:
            raise ValueError(
                f"Brak dni urlopu. Dostępne: {available}, wykorzystane: {used}, wniosek: {requested_days}."
            )
        return

    # inne typy limitowane
    used = (
        LeaveRequest.objects.filter(
            company=company,
            user=user,
            leave_type=leave_type,
            status=LeaveRequest.Status.APPROVED,
            leave_year=year,
        ).aggregate(s=Sum("days_count"))["s"]
        or Decimal("0")
    )

    limit_days = leave_type.annual_limit_days or Decimal("0")

    if used + requested_days > limit_days:
        raise ValueError(
            f"Przekroczono limit dla urlopu {leave_type.name}. "
            f"Limit: {limit_days}, wykorzystane: {used}."
        )