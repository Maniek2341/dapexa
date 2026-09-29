import json
from decimal import Decimal

from django import forms

from .models import SupplierIntegration


class SupplierIntegrationForm(forms.ModelForm):
    feed_url = forms.CharField(
        label="URL feedu XML/CSV",
        required=False,
        widget=forms.URLInput(attrs={"class": "form-control", "autocomplete": "new-password", "placeholder": "https://… (dane poufne)"}),
        help_text="Adres jest szyfrowany w bazie. Przy edycji zostaw puste, aby zachować zapisany adres.",
    )
    mapping_json = forms.CharField(
        label="Mapowanie pól feedu (JSON)", required=False,
        widget=forms.Textarea(attrs={"class": "form-control font-monospace", "rows": 6}),
        help_text="Opcjonalne nadpisanie mapowania. Przykład: {\"item_tag\": \"item\", \"sku\": \"symbol\"}.",
    )

    class Meta:
        model = SupplierIntegration
        fields = (
            "name", "feed_url", "feed_type", "is_active", "sync_catalog",
            "sync_prices", "default_markup", "sync_stock",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "feed_type": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sync_catalog": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sync_prices": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sync_stock": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "default_markup": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._submitted_feed_url = self.data.get(self.add_prefix("feed_url"), "") if self.is_bound else ""
        if self.is_bound and hasattr(self.data, "copy"):
            # Keep the value for server-side validation, but never echo tokens in an HTML response.
            sanitized_data = self.data.copy()
            sanitized_data[self.add_prefix("feed_url")] = ""
            self.data = sanitized_data
        for field_name, label in {
            "name": "Nazwa integracji",
            "feed_type": "Format feedu",
            "is_active": "Integracja aktywna",
            "sync_catalog": "Synchronizuj katalog",
            "sync_prices": "Synchronizuj ceny",
            "default_markup": "Domyślny narzut (%)",
            "sync_stock": "Synchronizuj stany",
        }.items():
            self.fields[field_name].label = label
        if self.instance.pk:
            # Never render a possibly signed URL/token back into the page.
            self.fields["feed_url"].initial = ""
            self.initial["feed_url"] = ""
        self.fields["mapping_json"].initial = json.dumps(
            (self.instance.settings or {}).get("mapping", {}), ensure_ascii=False, indent=2
        ) if self.instance.pk else ""

    def clean_feed_url(self):
        value = self._submitted_feed_url.strip()
        if not value and not self.instance.pk:
            raise forms.ValidationError("Podaj URL feedu.")
        if not value and self.instance.pk:
            return self.instance.feed_url
        if not value.lower().startswith(("https://", "http://")):
            raise forms.ValidationError("Adres feedu musi zaczynać się od http:// lub https://.")
        return value

    def clean_mapping_json(self):
        value = self.cleaned_data.get("mapping_json", "").strip()
        if not value:
            return {}
        try:
            mapping = json.loads(value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("Mapowanie musi być poprawnym JSON-em.") from exc
        if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()):
            raise forms.ValidationError("Mapowanie musi być słownikiem tekstowych nazw pól.")
        return mapping

    def clean_default_markup(self):
        value = self.cleaned_data.get("default_markup")
        if value is not None and value < Decimal("0"):
            raise forms.ValidationError("Narzut nie może być ujemny.")
        return value

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.settings = {**(instance.settings or {}), "mapping": self.cleaned_data["mapping_json"]}
        if commit:
            instance.save()
        return instance
