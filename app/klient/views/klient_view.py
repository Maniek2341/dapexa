# app/clients/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.db.models import Q

from app.klient.models import Client
from app.klient.permissions import can_manage_clients


class KlientView(LoginRequiredMixin, View):
    login_url = reverse_lazy('login')

    def get(self, request):
        user = request.user

        # jeśli user nie ma przypisanej firmy – możesz np. przekierować:
        if not hasattr(user, "company") or user.company is None:
            return redirect("dashboard")  # albo inny widok

        q = request.GET.get("q", "").strip()

        clients = (
            Client.objects
            .filter(company=user.company, is_active=True)
        )

        if q:
            clients = clients.filter(
                Q(name__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q) |
                Q(phone__icontains=q) |
                Q(nip__icontains=q)
            )

        clients = clients.order_by(
            "client_type",
            "name",
            "last_name",
            "first_name",
            "pk",
        )

        company_count = clients.filter(client_type="company").count()
        private_count = clients.filter(client_type="private").count()
        paginator = Paginator(clients, 30)
        page_obj = paginator.get_page(request.GET.get("page"))
        query_params = request.GET.copy()
        query_params.pop("page", None)
        page_numbers = range(
            max(1, page_obj.number - 2),
            min(paginator.num_pages, page_obj.number + 2) + 1,
        )

        context = {
            "clients": page_obj.object_list,
            "page_obj": page_obj,
            "page_numbers": page_numbers,
            "pagination_query": query_params.urlencode(),
            "is_paginated": paginator.num_pages > 1,
            "total_count": paginator.count,
            "company_count": company_count,
            "private_count": private_count,
            "q": q,
            "can_manage_clients": can_manage_clients(user),
        }
        return render(request, "app/klient/klienci.html", context)
