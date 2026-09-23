# app/leaves/services.py
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from app.urlop.models import LeaveRequest, LeaveAllowance, LeavePool, LeaveType

def get_allowance(company, user, year: int) -> LeaveAllowance:
    return LeaveAllowance.objects.get(company=company, user=user, year=year)

def used_vacation_days(company, user, year):
    return (
        LeaveRequest.objects.filter(
            company=company,
            user=user,
            leave_year=year,
            status=LeaveRequest.Status.APPROVED,
            leave_type__pool=LeavePool.VACATION,
        ).aggregate(total=Sum("days_count"))["total"]
        or Decimal("0")
    )

def used_on_demand_days(company, user, year: int) -> Decimal:
    total = (LeaveRequest.objects
        .filter(
            company=company,
            user=user,
            leave_year=year,
            status=LeaveRequest.Status.APPROVED,
            leave_type__code="na_zadanie",  # albo inny kod w Twojej konfiguracji
        )
        .aggregate(s=Sum("days_count"))["s"]
    )
    return total or Decimal("0")

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
                leave_year=year,
                status=LeaveRequest.Status.APPROVED,
            ).aggregate(s=Sum("days_count"))["s"]
            or Decimal("0")
        )

        if used + requested_days > leave_type.annual_limit_days:
            raise ValueError(
                f"Przekroczono limit dla urlopu {leave_type.name}. "
                f"Limit: {leave_type.annual_limit_days}, wykorzystane: {used}."
            )
        return

    # wypoczynkowy / na żądanie
    if leave_type.pool == LeavePool.VACATION:
        allowance = get_allowance(company, user, year)

        if leave_type.code == "na_zadanie":
            used_od = used_on_demand_days(company, user, year)
            if used_od + requested_days > allowance.on_demand_limit:
                raise ValueError(
                    f"Przekroczono limit urlopu na żądanie ({allowance.on_demand_limit} dni)."
                )

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

    # inne typy limitowane, np. opiekuńczy itp.
    used = (
        LeaveRequest.objects.filter(
            company=company,
            user=user,
            leave_type=leave_type,
            leave_year=year,
            status=LeaveRequest.Status.APPROVED,
        ).aggregate(s=Sum("days_count"))["s"]
        or Decimal("0")
    )

    limit_days = leave_type.annual_limit_days or Decimal("0")

    if used + requested_days > limit_days:
        raise ValueError(
            f"Przekroczono limit dla urlopu {leave_type.name}. "
            f"Limit: {limit_days}, wykorzystane: {used}."
        )

def get_remaining_days(company, user, year):
    try:
        allowance = LeaveAllowance.objects.get(
            company=company,
            user=user,
            year=year
        )
    except LeaveAllowance.DoesNotExist:
        return Decimal("0")

    used = used_vacation_days(company, user, year)
    remaining = allowance.total_vacation_available() - used

    if remaining < 0:
        return Decimal("0")

    return remaining

def get_leave_type_usage(company, user, leave_type, year=None):
    if year is None:
        year = timezone.now().year

    used = (
        LeaveRequest.objects.filter(
            company=company,
            user=user,
            leave_type=leave_type,
            leave_year=year,
            status=LeaveRequest.Status.APPROVED,
        ).aggregate(total=Sum("days_count"))["total"]
        or Decimal("0")
    )

    limit_days = leave_type.annual_limit_days or Decimal("0")
    remaining = limit_days - used

    if remaining < 0:
        remaining = Decimal("0")

    return {
        "limit": limit_days,
        "used": used,
        "remaining": remaining,
    }

def get_leave_limits_for_user(company, user, year: int):
    leave_types = LeaveType.objects.filter(
        company=company,
        counts_against_limit=True,
    ).order_by("name")

    results = []

    for leave_type in leave_types:
        # klasyczny wypoczynkowy liczony z LeaveAllowance
        if leave_type.pool == LeavePool.VACATION and not leave_type.is_special:
            try:
                allowance = LeaveAllowance.objects.get(
                    company=company,
                    user=user,
                    year=year,
                )
                used = used_vacation_days(company, user, year)
                limit_days = allowance.total_vacation_available()
                remaining = limit_days - used

                if remaining < 0:
                    remaining = Decimal("0")

            except LeaveAllowance.DoesNotExist:
                limit_days = Decimal("0")
                used = Decimal("0")
                remaining = Decimal("0")

        else:
            usage = get_leave_type_usage(company, user, leave_type, year)
            limit_days = usage["limit"]
            used = usage["used"]
            remaining = usage["remaining"]

        results.append({
            "leave_type": leave_type,
            "limit": limit_days,
            "used": used,
            "remaining": remaining,
        })

    return results