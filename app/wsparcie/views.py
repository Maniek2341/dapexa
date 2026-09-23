from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import SupportReplyForm, SupportTicketForm
from .models import SupportReply, SupportTicket


class SupportAccessMixin:
    """The technical support panel is reserved for management/program owner."""
    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, "role", None) == "employee":
            raise PermissionDenied("Pracownik nie ma dostępu do modułu wsparcia technicznego.")
        return super().dispatch(request, *args, **kwargs)


def _can(request, name):
    """Owners and clients retain panel access; other roles use explicit grants."""
    role = getattr(request.user, "role", None)
    if role in {request.user.Role.OWNER, request.user.Role.CLIENT}:
        return True
    return request.user.has_perm(f"wsparcie.access_{name}")


class SupportTicketListView(SupportAccessMixin, LoginRequiredMixin, View):
    def get(self, request):
        queryset = SupportTicket.objects.all() if request.user.is_superuser else SupportTicket.objects.filter(company=request.user.company)
        tickets = queryset.select_related("created_by", "assigned_to")
        return render(request, "app/wsparcie/list.html", {
            "tickets": tickets,
            "ticket_count": queryset.count(),
            "new_count": queryset.filter(status=SupportTicket.Status.NEW).count(),
            "active_count": queryset.filter(status=SupportTicket.Status.IN_PROGRESS).count(),
            "resolved_count": queryset.filter(status=SupportTicket.Status.RESOLVED).count(),
        })


class SupportTicketCreateView(SupportAccessMixin, LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "app/wsparcie/form.html", {"form": SupportTicketForm()})

    def post(self, request):
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.company = request.user.company
            ticket.created_by = request.user
            ticket.save()
            messages.success(request, "Zgłoszenie zostało wysłane do wsparcia.")
            return redirect("support_detail", pk=ticket.pk)
        return render(request, "app/wsparcie/form.html", {"form": form})


class SupportTicketDetailView(SupportAccessMixin, LoginRequiredMixin, View):
    def get(self, request, pk):
        queryset = SupportTicket.objects.select_related("created_by", "assigned_to")
        if not request.user.is_superuser:
            queryset = queryset.filter(company=request.user.company)
        ticket = get_object_or_404(queryset, pk=pk)
        return render(request, "app/wsparcie/detail.html", {"ticket": ticket, "reply_form": SupportReplyForm(), "status_choices": SupportTicket.Status.choices})

    def post(self, request, pk):
        if not _can(request, "support_reply"):
            raise PermissionDenied
        ticket = get_object_or_404(SupportTicket, pk=pk, company=request.user.company)
        form = SupportReplyForm(request.POST)
        if not form.is_valid():
            return render(request, "app/wsparcie/detail.html", {"ticket": ticket, "reply_form": form, "status_choices": SupportTicket.Status.choices})
        reply = form.save(commit=False)
        reply.company = request.user.company
        reply.ticket = ticket
        reply.author = request.user
        reply.save()
        if ticket.status == SupportTicket.Status.NEW:
            ticket.status = SupportTicket.Status.IN_PROGRESS
            ticket.save(update_fields=["status", "updated_at"])
        messages.success(request, "Odpowiedź została dodana.")
        return redirect("support_detail", pk=ticket.pk)


class SupportTicketStatusView(SupportAccessMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        # Status może zmieniać wyłącznie właściciel programu (konto superusera),
        # niezależnie od firmy, której dotyczy zgłoszenie.
        if not request.user.is_superuser:
            raise PermissionDenied("Tylko właściciel programu może zmieniać status zgłoszenia.")
        ticket = get_object_or_404(SupportTicket, pk=pk)
        status = request.POST.get("status")
        if status not in dict(SupportTicket.Status.choices):
            raise PermissionDenied("Nieprawidłowy status zgłoszenia.")
        ticket.status = status
        ticket.save(update_fields=["status", "updated_at"])
        messages.success(request, "Status zgłoszenia został zmieniony.")
        return redirect("support_detail", pk=ticket.pk)
