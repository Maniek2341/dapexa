from celery import shared_task

from app.core.subscription_lifecycle import (
    purge_expired_subscriptions,
    send_cancellation_reminders,
)


@shared_task
def process_subscription_lifecycle():
    return {
        "reminders_sent": send_cancellation_reminders(),
        "companies_purged": purge_expired_subscriptions(),
    }
