from django import forms

from .models import SupportReply, SupportTicket


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["title", "module", "priority", "description"]
        labels = {
            "title": "Temat zgłoszenia",
            "module": "Dotyczący modułu",
            "priority": "Priorytet",
            "description": "Opis problemu",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Krótki temat zgłoszenia"}),
            "module": forms.TextInput(attrs={"class": "form-control", "placeholder": "Np. Serwisy, RCP, logowanie"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 7, "placeholder": "Opisz problem i kroki jego odtworzenia..."}),
        }


class SupportReplyForm(forms.ModelForm):
    class Meta:
        model = SupportReply
        fields = ["content"]
        labels = {"content": "Treść odpowiedzi"}
        widgets = {"content": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Treść odpowiedzi..."})}
