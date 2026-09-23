from django.core.management.base import BaseCommand

from app.core.subscription_lifecycle import (
    purge_expired_subscriptions,
    send_cancellation_reminders,
)


class Command(BaseCommand):
    help = "Wysyła przypomnienia o anulowaniu i usuwa dane po okresie retencji."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nie usuwa danych; podaje liczbę firm po okresie retencji.",
        )

    def handle(self, *args, **options):
        reminders = send_cancellation_reminders()
        purged = purge_expired_subscriptions(dry_run=options["dry_run"])
        action = "do usunięcia" if options["dry_run"] else "usunięto"
        self.stdout.write(
            self.style.SUCCESS(
                f"Wysłane przypomnienia: {reminders}; firmy {action}: {purged}."
            )
        )
