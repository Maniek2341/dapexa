from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.oferta_praca.models import Offer, OfferActivity

User = get_user_model()


class OfferAssignWorkersView(LoginRequiredMixin, View):
    def post(self, request, pk):
        offer = get_object_or_404(
            Offer,
            pk=pk,
            company=request.user.company,
        )

        # 🔥 zapis starych pracowników
        old_workers = list(offer.assigned_employees.all())

        workers_ids = request.POST.getlist("workers")
        assigned_employees = []

        for worker_id in workers_ids:
            try:
                worker = User.objects.get(
                    pk=worker_id,
                    company=request.user.company
                )
                assigned_employees.append(worker)
            except User.DoesNotExist:
                continue

        offer.assigned_employees.set(assigned_employees)

        # 🔥 opis zmian (before → after)
        old_names = ", ".join(
            w.get_full_name() or w.email for w in old_workers
        ) or "brak"

        new_names = ", ".join(
            w.get_full_name() or w.email for w in assigned_employees
        ) or "brak"

        OfferActivity.objects.create(
            company=offer.company,
            offer=offer,
            type=OfferActivity.Type.WORKERS,
            title="Zmieniono pracowników",
            description=f"{old_names} → {new_names}",
            created_by=request.user,
        )

        messages.success(request, "Pracownicy zostali przypisani do oferty.")
        return redirect("offer_detail", pk=offer.pk)