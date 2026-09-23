# app/clients/views.py
import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from app.protokol.models import Protocol
from app.praca.models import WorkOrder

from app.klient.forms import ClientNoteForm, ContactPersonCreateForm
from app.klient.models import (
    Client,
    ClientActivity,
    ClientLocation,
    ClientNote,
    ContactPerson,
)
from app.klient.permissions import can_manage_clients
from app.serwis.models import ServiceOrder


class KlientDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/klient/detail.html"

    def get_client(self, request, pk):
        return get_object_or_404(
            Client,
            pk=pk,
            company=request.user.company,
            is_active=True,
        )

    def get_context_data(self, request, client, note_form=None):
        today = timezone.localdate()
        yesterday = today - datetime.timedelta(days=1)

        activities = (
            ClientActivity.objects
            .filter(company=request.user.company, client=client)
            .select_related("created_by")
            .order_by("-is_pinned", "-created_at")[:50]
        )

        notes = (
            ClientNote.objects
            .filter(company=request.user.company, client=client)
            .select_related("author")
            .order_by("-is_pinned", "-created_at")[:50]
        )

        contact_people = (
            ContactPerson.objects
            .filter(company=request.user.company, client=client)
            .order_by("last_name", "first_name")
        )

        locations = (
            ClientLocation.objects
            .filter(
                company=request.user.company,
                client=client,
                is_active=True,
            )
            .select_related("address", "contact_person")
            .order_by("-is_default", "name")
        )

        services = (
            ServiceOrder.objects
            .filter(
                company=request.user.company,
                client=client,
            )
            .select_related("client")
            .prefetch_related("assigned_to")
            .order_by("-created_at")
        )

        protocols = (
            Protocol.objects
            .filter(
                company=request.user.company,
                client=client,
            )
            .select_related("client", "service")
            .order_by("-created_at")
        )

        works = (
            WorkOrder.objects
            .filter(
                company=request.user.company,
                client=client,
            )
            .select_related("client")
            .order_by("-created_at")
        )

        return {
            "client": client,
            "today": today,
            "today_key": today.strftime("%Y-%m-%d"),
            "yesterday_key": yesterday.strftime("%Y-%m-%d"),

            "activities": activities,
            "activities_count": ClientActivity.objects.filter(
                company=request.user.company,
                client=client,
            ).count(),

            "notes": notes,
            "note_form": note_form or ClientNoteForm(),

            "contact_people": contact_people,
            "contact_form": ContactPersonCreateForm(),

            "locations": locations,

            "services": services,
            "services_count": services.count(),

            "protocols": protocols,
            "protocols_count": protocols.count(),

            "works": works,
            "works_count": works.count(),
            "can_manage_clients": can_manage_clients(request.user),
        }

    def get(self, request, pk):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        client = self.get_client(request, pk)
        context = self.get_context_data(request, client)

        return render(request, self.template_name, context)

    def post(self, request, pk):
        if not hasattr(request.user, "company") or request.user.company is None:
            messages.error(request, "Brak przypisania do firmy.")
            return redirect("klient")

        if not can_manage_clients(request.user):
            messages.error(request, "Pracownik nie może dodawać notatek do klienta.")
            return redirect("klient_detail", pk=pk)

        client = self.get_client(request, pk)

        form = ClientNoteForm(request.POST)

        if not form.is_valid():
            context = self.get_context_data(request, client, note_form=form)
            context["open_note_modal"] = True

            messages.error(request, "Popraw błędy w formularzu notatki.")
            return render(request, self.template_name, context)

        note = form.save(commit=False)
        note.company = request.user.company
        note.client = client
        note.author = request.user
        note.save()

        ClientActivity.objects.create(
            company=request.user.company,
            client=client,
            created_by=request.user,
            type=ClientActivity.Type.NOTE,
            title="Dodano notatkę",
            description=note.content,
        )

        messages.success(request, "Notatka została zapisana i dodana do historii.")
        return redirect("klient_detail", pk=client.pk)
