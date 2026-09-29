from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from app.core.models import PanelUser
from app.urlop.calendar import calculate_working_days
from app.urlop.models import LeaveAllowance, LeavePool, LeaveRequest, LeaveType

ACTIVE_REQUEST_STATUSES = (LeaveRequest.Status.SUBMITTED, LeaveRequest.Status.APPROVED)


def can_access_leave(user, permission):
    if (
        user.is_authenticated
        and user.company_id is not None
        and user.role == PanelUser.Role.EMPLOYEE
        and permission == "urlop_add"
    ):
        # Każdy pracownik może złożyć własny wniosek. To podstawowa funkcja
        # pracownika, niezależna od konfiguracji grupy uprawnień firmy.
        return True

    return (
        user.is_authenticated
        and user.company_id is not None
        and user.role not in {PanelUser.Role.CLIENT, PanelUser.Role.PODWYKONAWCA}
        and user.has_perm(f"urlop.access_{permission}")
    )


def require_leave_permission(user, permission):
    if not can_access_leave(user, permission):
        raise PermissionDenied("Nie masz uprawnień do tej operacji urlopowej.")


def get_allowance(company, user, year: int) -> LeaveAllowance:
    return LeaveAllowance.objects.get(company=company, user=user, year=year)


def days_in_year(leave, year):
    start = max(leave.date_from, date(year, 1, 1))
    end = min(leave.date_to, date(year, 12, 31))
    return calculate_working_days(start, end) if start <= end else Decimal("0")


def pending_leave_days(company, user, year):
    return sum(
        (days_in_year(leave, year) for leave in _requests_for_year(
            company, user, year, statuses=(LeaveRequest.Status.SUBMITTED,),
        ) if leave.leave_type.counts_against_limit),
        Decimal("0"),
    )


def _requests_for_year(company, user, year, *, exclude_pk=None, statuses=None):
    queryset = LeaveRequest.objects.filter(
        company=company,
        user=user,
        date_from__lte=date(year, 12, 31),
        date_to__gte=date(year, 1, 1),
    ).select_related("leave_type")
    if statuses is not None:
        queryset = queryset.filter(status__in=statuses)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset


def used_vacation_days(company, user, year, *, exclude_pk=None, include_pending=False):
    statuses = ACTIVE_REQUEST_STATUSES if include_pending else (LeaveRequest.Status.APPROVED,)
    return sum(
        (days_in_year(leave, year) for leave in _requests_for_year(
            company, user, year, exclude_pk=exclude_pk, statuses=statuses,
        ) if leave.leave_type.pool == LeavePool.VACATION and leave.leave_type.counts_against_limit),
        Decimal("0"),
    )


def used_regular_vacation_days(company, user, year):
    return sum(
        (days_in_year(leave, year) for leave in _requests_for_year(
            company, user, year, statuses=(LeaveRequest.Status.APPROVED,),
        ) if not leave.is_carryover and leave.leave_type.pool == LeavePool.VACATION
        and leave.leave_type.counts_against_limit),
        Decimal("0"),
    )


def used_on_demand_days(company, user, year, *, exclude_pk=None, include_pending=False):
    statuses = ACTIVE_REQUEST_STATUSES if include_pending else (LeaveRequest.Status.APPROVED,)
    return sum(
        (days_in_year(leave, year) for leave in _requests_for_year(
            company, user, year, exclude_pk=exclude_pk, statuses=statuses,
        ) if leave.leave_type.code == "na_zadanie" and leave.leave_type.counts_against_limit),
        Decimal("0"),
    )


def used_leave_type_days(company, user, leave_type, year, *, exclude_pk=None, include_pending=False):
    statuses = ACTIVE_REQUEST_STATUSES if include_pending else (LeaveRequest.Status.APPROVED,)
    return sum(
        (days_in_year(leave, year) for leave in _requests_for_year(
            company, user, year, exclude_pk=exclude_pk, statuses=statuses,
        ) if leave.leave_type_id == leave_type.pk),
        Decimal("0"),
    )


def validate_no_overlap(company, user, date_from, date_to, *, exclude_pk=None):
    conflicts = LeaveRequest.objects.filter(
        company=company, user=user,
        status__in=ACTIVE_REQUEST_STATUSES,
        date_from__lte=date_to, date_to__gte=date_from,
    )
    if exclude_pk is not None:
        conflicts = conflicts.exclude(pk=exclude_pk)
    if conflicts.exists():
        raise ValueError("Okres nakłada się na inny oczekujący lub zatwierdzony wniosek.")


def validate_request_against_allowance(
    company, user, leave_type, year: int, requested_days: Decimal,
    is_carryover: bool, *, exclude_pk=None, include_pending=True,
    date_from=None, date_to=None,
):
    if not leave_type.counts_against_limit:
        return

    if leave_type.company_id != company.pk or user.company_id != company.pk:
        raise ValueError("Rodzaj urlopu i pracownik muszą należeć do tej samej firmy.")

    if leave_type.is_special and leave_type.annual_limit_days > 0 and leave_type.pool != LeavePool.VACATION:
        used = used_leave_type_days(
            company, user, leave_type, year, exclude_pk=exclude_pk,
            include_pending=include_pending,
        )
        if used + requested_days > leave_type.annual_limit_days:
            raise ValueError(f"Przekroczono limit dla urlopu {leave_type.name}.")
        return

    if leave_type.pool == LeavePool.VACATION:
        try:
            allowance = LeaveAllowance.objects.get(company=company, user=user, year=year)
        except LeaveAllowance.DoesNotExist as exc:
            raise ValueError("Nie wygenerowano limitu urlopowego dla wybranego roku.") from exc

        if is_carryover:
            if not allowance.carryover_days:
                raise ValueError("Brak dostępnego urlopu zaległego.")
            if allowance.carryover_deadline and date_to and date_to > allowance.carryover_deadline:
                raise ValueError("Urlop zaległy musi zostać wykorzystany przed upływem terminu.")
            used_carry = used_vacation_days(
                company, user, year, exclude_pk=exclude_pk, include_pending=include_pending,
            )
            carry_requests = _requests_for_year(
                company, user, year, exclude_pk=exclude_pk,
                statuses=ACTIVE_REQUEST_STATUSES if include_pending else (LeaveRequest.Status.APPROVED,),
            ).filter(is_carryover=True)
            used_carry = sum(
                (days_in_year(item, year) for item in carry_requests
                 if item.leave_type.pool == LeavePool.VACATION and item.leave_type.counts_against_limit),
                Decimal("0"),
            )
            if used_carry + requested_days > allowance.carryover_days:
                raise ValueError("Wniosek przekracza dostępny urlop zaległy.")
        else:
            used_regular = _requests_for_year(
                company, user, year, exclude_pk=exclude_pk,
                statuses=ACTIVE_REQUEST_STATUSES if include_pending else (LeaveRequest.Status.APPROVED,),
            ).filter(is_carryover=False)
            used_regular_days = sum(
                (days_in_year(item, year) for item in used_regular
                 if item.leave_type.pool == LeavePool.VACATION and item.leave_type.counts_against_limit),
                Decimal("0"),
            )
            regular_limit = allowance.vacation_limit + allowance.adjustment_days
            if used_regular_days + requested_days > regular_limit:
                raise ValueError("Wniosek przekracza podstawowy limit urlopowy.")

        used_total = used_vacation_days(
            company, user, year, exclude_pk=exclude_pk, include_pending=include_pending,
        )
        if used_total + requested_days > allowance.total_vacation_available():
            raise ValueError(
                f"Brak dni urlopu. Dostępne: {allowance.total_vacation_available()}, "
                f"wykorzystane/zarezerwowane: {used_total}, wniosek: {requested_days}."
            )

        if leave_type.code == "na_zadanie":
            used_on_demand = used_on_demand_days(
                company, user, year, exclude_pk=exclude_pk, include_pending=include_pending,
            )
            if used_on_demand + requested_days > allowance.on_demand_limit:
                raise ValueError(f"Przekroczono limit urlopu na żądanie ({allowance.on_demand_limit} dni).")
        elif leave_type.is_special and used_leave_type_days(
            company, user, leave_type, year, exclude_pk=exclude_pk,
            include_pending=include_pending,
        ) + requested_days > leave_type.annual_limit_days:
            raise ValueError(f"Przekroczono limit dla urlopu {leave_type.name}.")
        return

    used = used_leave_type_days(
        company, user, leave_type, year, exclude_pk=exclude_pk,
        include_pending=include_pending,
    )
    if used + requested_days > leave_type.annual_limit_days:
        raise ValueError(f"Przekroczono limit dla urlopu {leave_type.name}.")


def validate_leave_request(leave, *, exclude_pk=None, include_pending=True):
    if leave.date_from > leave.date_to:
        raise ValueError("Data zakończenia nie może być wcześniejsza niż rozpoczęcia.")
    validate_no_overlap(leave.company, leave.user, leave.date_from, leave.date_to, exclude_pk=exclude_pk)
    for year in range(leave.date_from.year, leave.date_to.year + 1):
        requested_days = days_in_year(leave, year)
        if requested_days:
            validate_request_against_allowance(
                leave.company, leave.user, leave.leave_type, year, requested_days,
                leave.is_carryover, exclude_pk=exclude_pk,
                include_pending=include_pending, date_from=leave.date_from, date_to=leave.date_to,
            )


def submit_leave_request(leave):
    with transaction.atomic():
        PanelUser.objects.select_for_update().get(pk=leave.user_id)
        validate_leave_request(leave)
        leave.status = LeaveRequest.Status.SUBMITTED
        leave.save()
        return leave


def decide_leave_request(company, request_user, leave_id, decision):
    if decision not in {LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED}:
        raise ValueError("Nieprawidłowa decyzja.")
    require_leave_permission(
        request_user,
        "hr_leave_approve" if decision == LeaveRequest.Status.APPROVED else "hr_leave_reject",
    )
    with transaction.atomic():
        leave = LeaveRequest.objects.select_related("user", "leave_type").get(
            pk=leave_id, company=company,
        )
        PanelUser.objects.select_for_update().get(pk=leave.user_id)
        leave = LeaveRequest.objects.select_for_update().select_related(
            "user", "leave_type",
        ).get(pk=leave_id, company=company)
        if leave.status != LeaveRequest.Status.SUBMITTED:
            raise ValueError("Tylko oczekujący wniosek może zostać rozpatrzony.")
        if leave.user_id == request_user.pk and not (
            request_user.role == PanelUser.Role.OWNER
            and decision == LeaveRequest.Status.APPROVED
        ):
            raise ValueError("Nie można zatwierdzić ani odrzucić własnego wniosku.")
        if decision == LeaveRequest.Status.APPROVED:
            validate_leave_request(leave, exclude_pk=leave.pk, include_pending=True)
            leave.approver = request_user
            leave.approved_at = timezone.now()
        else:
            leave.approver = request_user
            leave.approved_at = None
        leave.status = decision
        leave.save()
        return leave


def cancel_leave_request(company, request_user, leave_id):
    require_leave_permission(request_user, "hr_leave_cancel")
    with transaction.atomic():
        initial = LeaveRequest.objects.only("user_id").get(pk=leave_id, company=company)
        PanelUser.objects.select_for_update().get(pk=initial.user_id)
        leave = LeaveRequest.objects.select_for_update().get(pk=leave_id, company=company)
        if leave.status != LeaveRequest.Status.APPROVED:
            raise ValueError("Można anulować tylko zatwierdzony urlop.")
        leave.status = LeaveRequest.Status.CANCELLED
        leave.save()
        return leave


def get_remaining_days(company, user, year):
    try:
        allowance = get_allowance(company, user, year)
    except LeaveAllowance.DoesNotExist:
        return Decimal("0")
    return allowance.total_vacation_available() - used_vacation_days(company, user, year)


def get_leave_type_usage(company, user, leave_type, year=None):
    year = year or timezone.localdate().year
    used = used_leave_type_days(company, user, leave_type, year)
    limit = leave_type.annual_limit_days or Decimal("0")
    return {"limit": limit, "used": used, "remaining": limit - used}


def get_leave_limits_for_user(company, user, year: int):
    results = []
    for leave_type in LeaveType.objects.filter(company=company, counts_against_limit=True).order_by("name"):
        if leave_type.pool == LeavePool.VACATION:
            try:
                allowance = get_allowance(company, user, year)
                used = used_vacation_days(company, user, year)
                limit = allowance.total_vacation_available()
                remaining = limit - used
                if leave_type.code == "na_zadanie":
                    on_demand_used = used_on_demand_days(company, user, year)
                    remaining = min(
                        allowance.total_vacation_available() - used,
                        allowance.on_demand_limit - on_demand_used,
                    )
            except LeaveAllowance.DoesNotExist:
                limit = used = remaining = Decimal("0")
        else:
            usage = get_leave_type_usage(company, user, leave_type, year)
            limit, used, remaining = usage["limit"], usage["used"], usage["remaining"]
        carryover_remaining = Decimal("0")
        if leave_type.pool == LeavePool.VACATION and leave_type.counts_against_limit:
            try:
                allowance = get_allowance(company, user, year)
                carry_requests = _requests_for_year(
                    company, user, year, statuses=(LeaveRequest.Status.APPROVED,),
                ).filter(is_carryover=True)
                carry_used = sum(
                    (days_in_year(item, year) for item in carry_requests
                     if item.leave_type.pool == LeavePool.VACATION and item.leave_type.counts_against_limit),
                    Decimal("0"),
                )
                carryover_remaining = max(Decimal("0"), allowance.carryover_days - carry_used)
            except LeaveAllowance.DoesNotExist:
                pass
        results.append({
            "leave_type": leave_type, "limit": limit, "used": used,
            "remaining": remaining, "carryover_remaining": carryover_remaining,
        })
    return results
