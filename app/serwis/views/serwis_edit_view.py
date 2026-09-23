from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views import View

from app.core.models import PanelUser
from app.serwis.forms import ServiceOrderCreateForm
from app.serwis.models import ServiceOrder, ServiceActivity
from app.serwis.permissions import can_manage_services
from app.serwis.signals import log_service_activity


class SerwisEditView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/serwis/add.html"

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może edytować serwisów.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, request, pk):
        return get_object_or_404(
            ServiceOrder,
            pk=pk,
            company=request.user.company,
        )

    def get_workers(self, request):
        return PanelUser.objects.filter(
            company=request.user.company,
            is_active=True,
        ).order_by("first_name", "last_name")

    def get(self, request, pk):
        service = self.get_object(request, pk)

        form = ServiceOrderCreateForm(
            instance=service,
            user=request.user,
        )

        return render(request, self.template_name, {
            "form": form,
            "service": service,
            "workers": self.get_workers(request),
            "is_edit": True,
        })

    def post(self, request, pk):
        service = self.get_object(request, pk)
        original_client = service.client

        form = ServiceOrderCreateForm(
            data=request.POST,
            files=request.FILES,
            instance=service,
            user=request.user,
        )

        if form.is_valid():
            updated = form.save(commit=False)

            # 🔒 klient zostaje ten sam przy edycji
            updated.client = original_client
            updated.company = request.user.company
            updated.save()

            form.save_m2m()

            try:
                log_service_activity(
                    company=updated.company,
                    service=updated,
                    type=ServiceActivity.Type.OTHER,
                    title="Zaktualizowano zgłoszenie",
                    description=f"{updated.number} – {updated.title}",
                    user=request.user,
                )
            except Exception:
                pass

            messages.success(request, "Serwis został zaktualizowany.")
            return HttpResponseRedirect(
                reverse_lazy("serwis_detail", kwargs={"pk": updated.pk})
            )

        messages.error(request, "Popraw błędy w formularzu.")

        return render(request, self.template_name, {
            "form": form,
            "service": service,
            "workers": self.get_workers(request),
            "is_edit": True,
        })
