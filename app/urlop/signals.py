from datetime import date

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from app.core.models import PanelUser


SENIORITY_FIELDS = (
    "employment_start_date",
    "previous_employment_years",
    "employment_fraction",
)


@receiver(pre_save, sender=PanelUser)
def remember_leave_entitlement_inputs(sender, instance, update_fields=None, **kwargs):
    instance._leave_entitlement_inputs_changed = False
    instance._leave_entitlement_previous_limits = {}
    if not instance.pk:
        return
    if update_fields is not None and not set(SENIORITY_FIELDS).intersection(update_fields):
        return

    previous_user = sender.objects.filter(pk=instance.pk).first()
    if previous_user is None:
        return
    instance._leave_entitlement_inputs_changed = any(
        getattr(previous_user, field) != getattr(instance, field)
        for field in SENIORITY_FIELDS
    )
    if not instance._leave_entitlement_inputs_changed:
        return

    from app.urlop.models import LeaveAllowance

    current_year = timezone.localdate().year
    instance._leave_entitlement_previous_limits = {
        allowance["pk"]: (
            allowance["year"],
            previous_user.get_vacation_entitlement(
                as_of=date(allowance["year"], 12, 31),
            ),
        )
        for allowance in LeaveAllowance.objects.filter(
            company_id=previous_user.company_id,
            user=instance,
            year__gte=current_year,
            is_locked=False,
        ).values("pk", "year")
    }


@receiver(post_save, sender=PanelUser)
def refresh_unlocked_leave_entitlements(sender, instance, **kwargs):
    if not getattr(instance, "_leave_entitlement_inputs_changed", False):
        return

    from app.urlop.allowance_generator import vacation_entitlement_days
    from app.urlop.models import LeaveAllowance

    allowances = LeaveAllowance.objects.filter(
        pk__in=instance._leave_entitlement_previous_limits,
        is_locked=False,
    ).only("pk", "year", "vacation_limit")

    for allowance in allowances:
        previous_year, previous_calculated_limit = instance._leave_entitlement_previous_limits[allowance.pk]
        if allowance.year != previous_year or allowance.vacation_limit != previous_calculated_limit:
            continue
        new_limit = vacation_entitlement_days(instance, allowance.year)
        if allowance.vacation_limit != new_limit:
            LeaveAllowance.objects.filter(pk=allowance.pk).update(vacation_limit=new_limit)
