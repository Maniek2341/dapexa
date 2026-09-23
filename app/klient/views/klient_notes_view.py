from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View

from app.klient.models import Client, ClientActivity, ClientNote
from app.klient.permissions import can_manage_clients


class ClientNoteTogglePinView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może przypinać notatek klienta.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk):
        note = get_object_or_404(
            ClientNote,
            pk=pk,
            company=request.user.company,
        )
        # bezpieczeństwo: notatka musi należeć do klienta z tej firmy
        if note.client.company_id != request.user.company_id:
            messages.error(request, "Brak dostępu.")
            return redirect("klient")

        note.is_pinned = not note.is_pinned
        note.save(update_fields=["is_pinned"])

        messages.success(request, "Zaktualizowano przypięcie notatki.")
        return redirect("klient_detail", pk=note.client_id)


class ClientNoteDeleteView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_clients(request.user):
            raise PermissionDenied("Pracownik nie może usuwać notatek klienta.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        note = get_object_or_404(
            ClientNote,
            pk=pk,
            company=request.user.company,
        )

        if note.client.company_id != request.user.company_id:
            messages.error(request, "Brak dostępu.")
            return redirect("klient")

        return render(
            request,
            "app/klient/note_delete.html",
            {"note": note, "client": note.client},
        )

    def post(self, request, pk):
        note = get_object_or_404(
            ClientNote,
            pk=pk,
            company=request.user.company,
        )

        if note.client.company_id != request.user.company_id:
            messages.error(request, "Brak dostępu.")
            return redirect("klient")

        client = note.client

        # ✅ zapis treści przed usunięciem
        content = (note.content or "").strip()

        # opcjonalnie skróć bardzo długie notatki
        preview = content[:500]
        if len(content) > 500:
            preview += "\n\n[...]"

        if not preview:
            preview = "(pusta notatka)"

        # ✅ wpis do historii
        ClientActivity.objects.create(
            company=request.user.company,
            client=client,
            created_by=request.user,
            updated_by=request.user,
            type=ClientActivity.Type.NOTE,
            title="Usunięto notatkę",
            description=f"Treść usuniętej notatki:\n{preview}",
        )

        # ✅ usuwamy notatkę
        note.delete()

        messages.success(request, "Notatka została usunięta.")
        return redirect("klient_detail", pk=client.pk)
