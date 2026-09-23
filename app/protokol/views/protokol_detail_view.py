from django.shortcuts import get_object_or_404, render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy

from app.protokol.models import Protocol
from app.protokol.permissions import can_manage_protocols


class ProtokolDetailView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    template_name = "app/protokol/detail.html"

    def get(self, request, pk):

        protocol = get_object_or_404(
            Protocol.objects
            .select_related("client", "company", "pracownik")
            .prefetch_related(
                "protokolurz__urzadzenia",
                "protokolimg",
                "activities"
            ),
            pk=pk,
            company=request.user.company,
            is_active=True
        )

        return render(
            request,
            self.template_name,
            {
                "protocol": protocol,
                "can_manage_protocols": can_manage_protocols(request.user),
            }
        )
