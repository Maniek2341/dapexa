import calendar
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import FieldDoesNotExist
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from app.core.models import Company, PanelUser, Subscription


REMINDER_DAYS = 3
RETENTION_MONTHS = 6


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def mark_cancellation_scheduled(subscription, period_end=None, requested_at=None):
    requested_at = requested_at or timezone.now()
    was_scheduled = subscription.cancel_at_period_end
    previous_period_end = subscription.current_period_end
    if period_end:
        subscription.current_period_end = period_end
    subscription.cancel_at_period_end = True
    subscription.cancellation_requested_at = (
        subscription.cancellation_requested_at or requested_at
    )
    if not was_scheduled or (period_end and period_end != previous_period_end):
        subscription.cancellation_reminder_sent_at = None
    if subscription.current_period_end:
        subscription.data_retention_until = add_months(
            subscription.current_period_end, RETENTION_MONTHS
        )


def clear_scheduled_cancellation(subscription):
    subscription.cancel_at_period_end = False
    subscription.cancellation_requested_at = None
    subscription.cancellation_reminder_sent_at = None
    subscription.data_retention_until = None


def sync_cancellation_state(subscription, cancel_at_period_end, period_end=None):
    if cancel_at_period_end:
        mark_cancellation_scheduled(subscription, period_end=period_end)
    elif subscription.cancel_at_period_end:
        clear_scheduled_cancellation(subscription)


def send_cancellation_reminders(now=None):
    """Send one reminder during the final three days of a canceled period."""
    now = now or timezone.now()
    deadline = now + timedelta(days=REMINDER_DAYS)
    subscriptions = (
        Subscription.objects.select_related("owner", "company")
        .filter(
            cancel_at_period_end=True,
            cancellation_reminder_sent_at__isnull=True,
            current_period_end__gt=now,
            current_period_end__lte=deadline,
        )
        .order_by("current_period_end")
    )
    sent = 0
    for subscription in subscriptions:
        owner = subscription.owner
        if not owner or not owner.email:
            continue
        body = render_to_string(
            "app/core/subscription_cancellation_reminder_email.txt",
            {"subscription": subscription, "owner": owner},
        )
        send_mail(
            "Subskrypcja wygaśnie za 3 dni",
            body,
            settings.DEFAULT_FROM_EMAIL,
            [owner.email],
            fail_silently=False,
        )
        subscription.cancellation_reminder_sent_at = now
        subscription.save(
            update_fields=["cancellation_reminder_sent_at", "updated_at"]
        )
        sent += 1
    return sent


def _delete_company_files(company):
    if getattr(company, "_company_files_deleted", False):
        return
    for field in [
        field for field in company._meta.fields
        if isinstance(field, models.FileField)
    ]:
        filename = getattr(company, field.name)
        if filename:
            field.storage.delete(filename.name)

    for model in apps.get_models():
        try:
            model._meta.get_field("company")
        except FieldDoesNotExist:
            continue
        file_fields = [
            field for field in model._meta.fields
            if isinstance(field, models.FileField)
        ]
        if not file_fields:
            continue
        queryset = model._default_manager.filter(company_id=company.pk)
        for field in file_fields:
            for filename in queryset.exclude(**{field.name: ""}).values_list(
                field.name, flat=True
            ):
                if filename:
                    field.storage.delete(filename)

    company._company_files_deleted = True


@transaction.atomic
def purge_company_after_retention(company):
    """Remove company data only after the six-month retention window."""
    address = company.main_address
    _delete_company_files(company)
    PanelUser.objects.filter(company=company).update(is_active=False)
    company.delete()
    if address:
        address.delete()


def purge_expired_subscriptions(now=None, dry_run=False):
    now = now or timezone.now()
    subscriptions = list(
        Subscription.objects.select_related("company", "company__main_address")
        .filter(
            cancel_at_period_end=True,
            data_retention_until__isnull=False,
            data_retention_until__lte=now,
        )
    )
    if dry_run:
        return len({sub.company_id for sub in subscriptions if sub.company_id})
    purged = 0
    processed_company_ids = set()
    for subscription in subscriptions:
        if not subscription.company_id or subscription.company_id in processed_company_ids:
            continue
        processed_company_ids.add(subscription.company_id)
        purge_company_after_retention(subscription.company)
        purged += 1
    return purged
