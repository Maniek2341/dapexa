import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views import View

from app.core.models import Subscription
from app.uzytkownik.models import OwnershipTransfer

User = get_user_model()
logger = logging.getLogger(__name__)


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class EmployeeOwnershipTransferView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        if request.user.role != User.Role.OWNER:
            raise PermissionDenied("Tylko aktualny właściciel może przekazać firmę.")
        if request.user.company_id is None:
            messages.error(request, "Twoje konto nie jest przypisane do firmy.")
            return redirect("employee_list")

        new_owner = get_object_or_404(
            User.objects.filter(role__in=[User.Role.MANAGER, User.Role.BIURO]),
            pk=pk,
            company_id=request.user.company_id,
            is_active=True,
            is_active_employee=True,
        )

        raw_token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)

        try:
            with transaction.atomic():
                current_owner = User.objects.select_for_update().get(pk=request.user.pk)
                if current_owner.role != User.Role.OWNER:
                    raise PermissionDenied("Nie jesteś już właścicielem tej firmy.")

                OwnershipTransfer.objects.filter(
                    company_id=current_owner.company_id,
                    status__in=[
                        OwnershipTransfer.Status.OWNER_PENDING,
                        OwnershipTransfer.Status.RECIPIENT_PENDING,
                    ],
                ).update(status=OwnershipTransfer.Status.CANCELLED)

                transfer = OwnershipTransfer.objects.create(
                    company_id=current_owner.company_id,
                    current_owner=current_owner,
                    new_owner=new_owner,
                    token_hash=_hash_token(raw_token),
                    expires_at=expires_at,
                )
                confirmation_url = request.build_absolute_uri(
                    reverse(
                        "employee_ownership_transfer_confirm",
                        kwargs={"transfer_id": transfer.pk, "token": raw_token},
                    )
                )
                message = render_to_string(
                    "app/pracownik/ownership_transfer_owner_email.txt",
                    {
                        "transfer": transfer,
                        "confirmation_url": confirmation_url,
                        "expires_at": expires_at,
                    },
                )
                send_mail(
                    subject=f"Potwierdź przekazanie firmy {current_owner.company.name}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[current_owner.email],
                    fail_silently=False,
                )
        except PermissionDenied:
            raise
        except Exception:
            logger.exception("Nie udało się utworzyć żądania przekazania właściciela")
            messages.error(
                request,
                "Nie udało się wysłać wiadomości potwierdzającej. Spróbuj ponownie.",
            )
            return redirect("employee_list")

        messages.success(
            request,
            f"Wysłano wiadomość zabezpieczającą na Twój adres {request.user.email}. "
            "Dopiero po jej potwierdzeniu przyszły właściciel otrzyma własny link.",
        )
        return redirect("employee_list")


class EmployeeOwnershipTransferConfirmView(View):
    http_method_names = ["get", "post"]
    template_name = "app/pracownik/ownership_transfer_confirm.html"

    active_statuses = {
        OwnershipTransfer.Status.OWNER_PENDING,
        OwnershipTransfer.Status.RECIPIENT_PENDING,
    }

    def _validate(self, transfer, token):
        if transfer.status not in self.active_statuses:
            return "To przekazanie zostało już wykorzystane albo anulowane."
        if transfer.expires_at <= timezone.now():
            return "Link potwierdzający wygasł. Poproś właściciela o wysłanie nowego."
        if not constant_time_compare(transfer.token_hash, _hash_token(token)):
            return "Link potwierdzający jest nieprawidłowy."
        if (
            transfer.current_owner.company_id != transfer.company_id
            or transfer.current_owner.role != User.Role.OWNER
            or transfer.new_owner.company_id != transfer.company_id
            or transfer.new_owner.role not in [User.Role.MANAGER, User.Role.BIURO]
            or not transfer.new_owner.is_active
            or not transfer.new_owner.is_active_employee
        ):
            return "Nie można już wykonać tego przekazania."
        return None

    def get(self, request, transfer_id, token):
        transfer = get_object_or_404(
            OwnershipTransfer.objects.select_related(
                "company", "current_owner", "new_owner"
            ),
            pk=transfer_id,
        )
        error = self._validate(transfer, token)
        return render(
            request,
            self.template_name,
            {
                "transfer": transfer,
                "token": token,
                "error": error,
                "is_owner_confirmation": (
                    transfer.status == OwnershipTransfer.Status.OWNER_PENDING
                ),
            },
        )

    def post(self, request, transfer_id, token):
        with transaction.atomic():
            transfer = get_object_or_404(
                OwnershipTransfer.objects.select_for_update().select_related(
                    "company", "current_owner", "new_owner"
                ),
                pk=transfer_id,
            )
            error = self._validate(transfer, token)
            if error:
                if (
                    transfer.status in self.active_statuses
                    and transfer.expires_at <= timezone.now()
                ):
                    transfer.status = OwnershipTransfer.Status.EXPIRED
                    transfer.save(update_fields=["status"])
                return render(
                    request,
                    self.template_name,
                    {"transfer": transfer, "token": token, "error": error},
                    status=400,
                )

            owners = list(
                User.objects.select_for_update().filter(
                    company_id=transfer.company_id,
                    role=User.Role.OWNER,
                )
            )
            if len(owners) != 1 or owners[0].pk != transfer.current_owner_id:
                return render(
                    request,
                    self.template_name,
                    {
                        "transfer": transfer,
                        "token": token,
                        "error": "Zmienił się właściciel firmy. Ten link nie może zostać użyty.",
                    },
                    status=409,
                )

            current_owner = owners[0]
            new_owner = User.objects.select_for_update().get(pk=transfer.new_owner_id)

            if transfer.status == OwnershipTransfer.Status.OWNER_PENDING:
                recipient_token = secrets.token_urlsafe(32)
                recipient_expires_at = timezone.now() + timedelta(hours=24)
                confirmation_url = request.build_absolute_uri(
                    reverse(
                        "employee_ownership_transfer_confirm",
                        kwargs={
                            "transfer_id": transfer.pk,
                            "token": recipient_token,
                        },
                    )
                )
                message = render_to_string(
                    "app/pracownik/ownership_transfer_email.txt",
                    {
                        "transfer": transfer,
                        "confirmation_url": confirmation_url,
                        "expires_at": recipient_expires_at,
                    },
                )
                try:
                    send_mail(
                        subject=f"Potwierdź przejęcie firmy {transfer.company.name}",
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[new_owner.email],
                        fail_silently=False,
                    )
                except Exception:
                    logger.exception(
                        "Nie udało się wysłać potwierdzenia przyszłemu właścicielowi"
                    )
                    transaction.set_rollback(True)
                    return render(
                        request,
                        self.template_name,
                        {
                            "transfer": transfer,
                            "token": token,
                            "error": "Nie udało się wysłać wiadomości przyszłemu właścicielowi. Spróbuj ponownie.",
                        },
                        status=503,
                    )

                transfer.status = OwnershipTransfer.Status.RECIPIENT_PENDING
                transfer.token_hash = _hash_token(recipient_token)
                transfer.expires_at = recipient_expires_at
                transfer.save(update_fields=["status", "token_hash", "expires_at"])
                return render(
                    request,
                    self.template_name,
                    {
                        "transfer": transfer,
                        "success": (
                            f"Potwierdzenie właściciela zostało zapisane. "
                            f"Wiadomość wysłano na adres {new_owner.email}."
                        ),
                    },
                )

            current_owner.role = User.Role.MANAGER
            current_owner.save(update_fields=["role", "updated_at"])
            new_owner.role = User.Role.OWNER
            new_owner.save(update_fields=["role", "updated_at"])

            Subscription.objects.filter(company_id=transfer.company_id).update(
                owner=new_owner
            )
            transfer.status = OwnershipTransfer.Status.CONFIRMED
            transfer.confirmed_at = timezone.now()
            transfer.save(update_fields=["status", "confirmed_at"])
            OwnershipTransfer.objects.filter(
                company_id=transfer.company_id,
                status__in=[
                    OwnershipTransfer.Status.OWNER_PENDING,
                    OwnershipTransfer.Status.RECIPIENT_PENDING,
                ],
            ).exclude(pk=transfer.pk).update(status=OwnershipTransfer.Status.CANCELLED)

        messages.success(request, "Przejęcie własności firmy zostało potwierdzone.")
        if request.user.is_authenticated:
            return redirect("dashboard")
        return redirect("login")
