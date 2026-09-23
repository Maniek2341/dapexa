from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View

from app.klient.models import Client, ClientLocation
from app.serwis.models import ServiceActivity
from app.serwis.forms import ServiceOrderCreateForm
from app.serwis.permissions import can_manage_services
from django.http import JsonResponse

def client_locations_api(request):
        client_id = request.GET.get("client")
        user = request.user

        if not client_id or not user.is_authenticated:
            return JsonResponse([], safe=False)

        try:
            client = Client.objects.get(
                id=client_id,
                company=user.company,
                is_active=True,
            )
        except Client.DoesNotExist:
            return JsonResponse([], safe=False)

        # tylko firmy
        if client.client_type != Client.TYPE_COMPANY:
            return JsonResponse([], safe=False)

        locations = ClientLocation.objects.filter(
            client=client,
            company=user.company,
            is_active=True,
        ).select_related("address")

        data = [
            {
                "id": loc.id,
                "name": loc.name or "Lokalizacja",
            }
            for loc in locations
        ]

        return JsonResponse(data, safe=False)

class SerwisAddView(LoginRequiredMixin, View):
    login_url = reverse_lazy("login")
    template_name = "app/serwis/add.html"
    success_url = reverse_lazy("serwis_nowe")

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_services(request.user):
            raise PermissionDenied("Pracownik nie może dodawać serwisów.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        client_id = request.GET.get("client")
        initial = {}

        if client_id:
            try:
                client = Client.objects.get(
                    pk=client_id,
                    company=request.user.company,
                    is_active=True
                )
                initial["client"] = client.id
            except Client.DoesNotExist:
                pass

        form = ServiceOrderCreateForm(
            user=request.user,
            initial=initial
        )

        if client_id:
            form.fields["client"].widget = forms.HiddenInput()

        return render(request, self.template_name, {"form": form, "client_id": client_id})

    def post(self, request):
        client_id = request.GET.get("client")

        form = ServiceOrderCreateForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        if form.is_valid():
            service = form.save()

            ServiceActivity.objects.create(
                company=service.company,
                service=service,
                type=ServiceActivity.Type.SYSTEM,
                title="Utworzono zgłoszenie",
                description=f"Numer: {service.number}",
                created_by=request.user,
            )

            if service.status == service.Status.OBSLUGA:
                success_message = f"Obsługa {service.number} została dodana."
            else:
                success_message = f"Serwis {service.number} został dodany."
            messages.success(request, success_message)
            return HttpResponseRedirect(self.success_url)

        messages.error(request, "Popraw błędy w formularzu.")
        return render(request, self.template_name, {"form": form})
