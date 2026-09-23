# app/core/views/ajax_select.py

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q


class AjaxSelectView(LoginRequiredMixin, View):
    model = None
    search_fields = []
    label_fields = ["name"]
    per_page = 20
    company_field = "company"

    def get_queryset(self):
        qs = self.model.objects.all()

        if self.company_field:
            qs = qs.filter(**{
                self.company_field: self.request.user.company
            })

        return qs

    def get_label(self, obj):
        values = []

        for field in self.label_fields:
            value = getattr(obj, field, None)
            if value:
                values.append(str(value))

        return " • ".join(values) if values else str(obj)

    def get(self, request):
        query = request.GET.get("q", "").strip()
        page = request.GET.get("page", 1)

        qs = self.get_queryset()

        if query and self.search_fields:
            search_query = Q()

            for field in self.search_fields:
                search_query |= Q(**{
                    f"{field}__icontains": query
                })

            qs = qs.filter(search_query)

        qs = qs.order_by("id")

        paginator = Paginator(qs, self.per_page)
        current_page = paginator.get_page(page)

        results = [
            {
                "id": obj.pk,
                "text": self.get_label(obj),
            }
            for obj in current_page
        ]

        return JsonResponse({
            "results": results,
            "has_next": current_page.has_next(),
        })