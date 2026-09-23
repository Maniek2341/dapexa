from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from app.sprzet.forms import ToolEventForm
from app.sprzet.models import (
    Tool,
    ToolEventMedia,
    ToolHistory,
    ToolHistoryType,
)


class ToolEventAddView(LoginRequiredMixin, View):
    def post(self, request, pk):
        tool = get_object_or_404(
            Tool,
            pk=pk,
            company=request.user.company,
        )

        form = ToolEventForm(request.POST, request.FILES)

        if form.is_valid():
            event = form.save(commit=False)
            event.company = request.user.company
            event.tool = tool
            event.created_by = request.user
            event.save()

            images_count = 0

            for image in request.FILES.getlist("images"):
                ToolEventMedia.objects.create(
                    company=request.user.company,
                    event=event,
                    image=image,
                    uploaded_by=request.user,
                )
                images_count += 1

            ToolHistory.objects.create(
                company=request.user.company,
                tool=tool,
                type=ToolHistoryType.OTHER,
                title="Dodano zdarzenie",
                description=(
                    f"Typ zdarzenia: {event.get_type_display()}\n"
                    f"Opis: {event.description or 'Brak'}\n"
                    f"Liczba zdjęć: {images_count}"
                ),
                created_by=request.user,
            )

            messages.success(request, "Zdarzenie zostało dodane.")
        else:
            messages.error(request, "Nie udało się dodać zdarzenia.")

        return redirect("tool_detail", pk=tool.pk)