from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q

from app.protokol.models import Protocol
from app.protokol.permissions import can_manage_protocols


class ProtokolNoweView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    template_name = "app/protokol/nowe.html"

    def get(self, request):

        status = request.GET.get("status")
        q = request.GET.get("q", "").strip()

        protocols = (
            Protocol.objects
            .filter(
                company=request.user.company,
                is_active=True,
            )
            .select_related("client")
            .order_by("-end_time")
        )

        if status and status != "all":
            protocols = protocols.filter(status=status)

        if q:
            protocols = protocols.filter(
                Q(title__icontains=q) |
                Q(number__icontains=q) |
                Q(rodzaj_prac__icontains=q) |
                Q(client__name__icontains=q) |
                Q(client__first_name__icontains=q) |
                Q(client__last_name__icontains=q)
            ).distinct()

        context = {
            "protocols": protocols,
            "active_status": status or "new",
            "q": q,
            "can_manage_protocols": can_manage_protocols(request.user),

            "do_zafakturowania_count": Protocol.objects.filter(
                company=request.user.company,
                is_active=True,
                status="do_zafakturowania",
            ).count(),

            "sent_count": Protocol.objects.filter(
                company=request.user.company,
                is_active=True,
                status="sent",
            ).count(),
        }

        return render(request, self.template_name, context)
