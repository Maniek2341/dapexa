from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.oferta_praca.models import Offer, OfferActivity

User = get_user_model()


class OfferPriorityUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        offer = get_object_or_404(
            Offer,
            pk=pk,
            company=request.user.company,
        )

        priority = request.POST.get("priority")
        allowed = dict(Offer.Priority.choices)

        if priority not in allowed:
            messages.error(request, "Nieprawidłowy priorytet.")
            return redirect("offer_detail", pk=offer.pk)

        old_priority = offer.priority

        offer.priority = priority
        offer.save(update_fields=["priority"])

        OfferActivity.objects.create(
            company=offer.company,
            offer=offer,
            type=OfferActivity.Type.PRIORITY,
            title="Zmieniono priorytet",
            description=f"{allowed.get(old_priority, old_priority)} → {allowed[priority]}",
            created_by=request.user,
        )

        messages.success(request, f"Priorytet zmieniony na: {allowed[priority]}.")
        return redirect("offer_detail", pk=offer.pk)