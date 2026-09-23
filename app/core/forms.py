# app/uzytkownik/forms.py
import re
from django import forms
from django.contrib.auth import get_user_model

from app.core.models import Address, Company, CompanySettings, PanelUser, Subscription
from app.core.notification_preferences import NOTIFICATION_MODULE_CHOICES
from app.core.validators import validate_polish_nip
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class CompanyProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "nip", "regon", "krs", "email", "phone", "logo"]
        labels = {
            "name": "Nazwa firmy",
            "nip": "NIP",
            "regon": "REGON",
            "krs": "KRS",
            "email": "E-mail firmowy",
            "phone": "Telefon firmowy",
            "logo": "Logo firmy",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Nazwa firmy"}),
            "nip": forms.TextInput(attrs={"placeholder": "10 cyfr", "inputmode": "numeric"}),
            "regon": forms.TextInput(attrs={"placeholder": "9 lub 14 cyfr", "inputmode": "numeric"}),
            "krs": forms.TextInput(attrs={"placeholder": "10 cyfr", "inputmode": "numeric"}),
            "email": forms.EmailInput(attrs={"placeholder": "firma@example.pl"}),
            "phone": forms.TextInput(attrs={"placeholder": "+48 000 000 000", "autocomplete": "tel"}),
            "logo": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp,image/svg+xml"}),
        }

    def __init__(self, *args, can_change_logo=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_change_logo = can_change_logo
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["logo"].help_text = (
            "Dostępne tylko w pakiecie Pro. Zalecane PNG, JPG, WEBP albo SVG."
        )
        if not can_change_logo:
            self.fields["logo"].disabled = True

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and not self.can_change_logo:
            raise forms.ValidationError("Zmiana loga firmy jest dostępna tylko w pakiecie Pro.")
        if logo and hasattr(logo, "content_type"):
            allowed_types = {
                "image/png",
                "image/jpeg",
                "image/webp",
                "image/svg+xml",
            }
            if logo.content_type not in allowed_types:
                raise forms.ValidationError("Logo musi być plikiem PNG, JPG, WEBP albo SVG.")
        return logo

    def _clean_number(self, field_name, lengths):
        value = (self.cleaned_data.get(field_name) or "").replace(" ", "").replace("-", "")
        if value and (not value.isdigit() or len(value) not in lengths):
            expected = " lub ".join(str(length) for length in lengths)
            raise forms.ValidationError(f"Pole musi zawierać {expected} cyfr.")
        return value

    def clean_nip(self):
        nip = self._clean_number("nip", (10,))
        if nip:
            validate_polish_nip(nip)
        return nip

    def clean_regon(self):
        return self._clean_number("regon", (9, 14))

    def clean_krs(self):
        return self._clean_number("krs", (10,))


class CompanyAddressSettingsForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["street", "street_no", "postcode", "city", "country"]
        labels = {
            "street": "Ulica",
            "street_no": "Numer budynku / lokalu",
            "postcode": "Kod pocztowy",
            "city": "Miasto",
            "country": "Kraj",
        }
        widgets = {
            "street": forms.TextInput(attrs={"placeholder": "Ulica"}),
            "street_no": forms.TextInput(attrs={"placeholder": "np. 12A/4"}),
            "postcode": forms.TextInput(attrs={"placeholder": "00-000"}),
            "city": forms.TextInput(attrs={"placeholder": "Miasto"}),
            "country": forms.TextInput(attrs={"placeholder": "Polska"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        address_fields = ("street", "street_no", "postcode", "city")
        values = [cleaned_data.get(field) for field in address_fields]
        if any(values):
            for field in ("street", "postcode", "city"):
                if not cleaned_data.get(field):
                    self.add_error(field, "To pole jest wymagane po rozpoczęciu uzupełniania adresu.")
        postcode = cleaned_data.get("postcode") or ""
        if postcode and not re.match(r"^\d{2}-\d{3}$", postcode):
            self.add_error("postcode", "Kod pocztowy musi mieć format 00-000.")
        return cleaned_data

    @property
    def has_address_data(self):
        return any(self.cleaned_data.get(field) for field in ("street", "street_no", "postcode", "city"))


class CompanyOperationalSettingsForm(forms.ModelForm):
    monetary_fields = (
        "travel_cost_per_km",
        "labor_price_1_worker",
        "labor_price_2_workers",
        "labor_price_3_workers",
        "default_vat",
    )

    class Meta:
        model = CompanySettings
        fields = [
            "travel_cost_per_km", "labor_price_1_worker",
            "labor_price_2_workers", "labor_price_3_workers", "default_vat",
            "default_protocol_valid_days", "default_work_start_time",
            "default_work_end_time", "protocol_number_prefix",
            "protocol_number_digits", "service_number_prefix",
            "service_number_digits", "maintenance_number_prefix",
        ]
        labels = {
            "travel_cost_per_km": "Koszt dojazdu za 1 km",
            "labor_price_1_worker": "Cena pracy — 1 pracownik",
            "labor_price_2_workers": "Cena pracy — 2 pracowników",
            "labor_price_3_workers": "Cena pracy — 3 pracowników",
            "default_vat": "Domyślna stawka VAT",
            "default_protocol_valid_days": "Domyślna ważność protokołu (dni)",
            "default_work_start_time": "Domyślna godzina rozpoczęcia pracy",
            "default_work_end_time": "Domyślna godzina zakończenia pracy",
            "protocol_number_prefix": "Prefiks numeru protokołu",
            "protocol_number_digits": "Liczba cyfr numeru protokołu",
            "service_number_prefix": "Prefiks numeru zgłoszenia",
            "service_number_digits": "Liczba cyfr numeru zgłoszenia",
            "maintenance_number_prefix": "Prefiks numeru obsługi",
        }
        widgets = {
            "travel_cost_per_km": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "labor_price_1_worker": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "labor_price_2_workers": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "labor_price_3_workers": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "default_vat": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "99.99"}),
            "default_protocol_valid_days": forms.NumberInput(attrs={"step": "1", "min": "1"}),
            "default_work_start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "default_work_end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "protocol_number_prefix": forms.TextInput(attrs={"placeholder": "PROT", "maxlength": "12"}),
            "protocol_number_digits": forms.NumberInput(attrs={"min": "2", "max": "8"}),
            "service_number_prefix": forms.TextInput(attrs={"placeholder": "SER", "maxlength": "12"}),
            "service_number_digits": forms.NumberInput(attrs={"min": "2", "max": "8"}),
            "maintenance_number_prefix": forms.TextInput(attrs={"placeholder": "OBS", "maxlength": "12"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self.monetary_fields:
            value = cleaned_data.get(field_name)
            if value is not None and value < 0:
                self.add_error(field_name, "Wartość nie może być ujemna.")

        start_time = cleaned_data.get("default_work_start_time")
        end_time = cleaned_data.get("default_work_end_time")
        if start_time and end_time and start_time >= end_time:
            self.add_error(
                "default_work_start_time",
                "Godzina rozpoczęcia musi być wcześniejsza niż godzina zakończenia.",
            )
            self.add_error(
                "default_work_end_time",
                "Godzina zakończenia musi być późniejsza niż godzina rozpoczęcia.",
            )

        for field_name in ("protocol_number_digits", "service_number_digits"):
            value = cleaned_data.get(field_name)
            if value is not None and not 2 <= value <= 8:
                self.add_error(field_name, "Liczba cyfr musi mieścić się w zakresie od 2 do 8.")

        return cleaned_data

    def _clean_number_prefix(self, field_name):
        value = (self.cleaned_data.get(field_name) or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9-]+", value):
            raise forms.ValidationError(
                "Prefiks może zawierać wyłącznie litery A-Z, cyfry i myślnik."
            )
        return value

    def clean_protocol_number_prefix(self):
        return self._clean_number_prefix("protocol_number_prefix")

    def clean_service_number_prefix(self):
        return self._clean_number_prefix("service_number_prefix")

    def clean_default_protocol_valid_days(self):
        value = self.cleaned_data["default_protocol_valid_days"]
        if value < 1:
            raise forms.ValidationError("Liczba dni musi być większa od zera.")
        return value


class CompanyNotificationSettingsForm(forms.ModelForm):
    notification_modules = forms.MultipleChoiceField(
        label="Moduły",
        choices=NOTIFICATION_MODULE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = CompanySettings
        fields = ["notification_email", "notification_modules"]
        labels = {
            "notification_email": "Adres e-mail dla powiadomień firmowych",
        }
        widgets = {
            "notification_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "powiadomienia@firma.pl",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("notification_modules") and not cleaned_data.get("notification_email"):
            self.add_error(
                "notification_email",
                "Podaj adres e-mail albo odznacz wszystkie moduły.",
            )
        return cleaned_data


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email",
                "class": "form-control",
                "autocomplete": "email"
            }
        ),
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Imię",
                "class": "form-control",
                "autocomplete": "given-name"
            }
        ),
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nazwisko",
                "class": "form-control",
                "autocomplete": "family-name"
            }
        ),
    )
    password1 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Hasło",
                "class": "form-control",
                "autocomplete": "new-password",
                "aria-describedby":"passwordHelpBlock"
            }
        ),
    )
    password2 = forms.CharField(
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Powtórz hasło",
                "class": "form-control",
                "autocomplete": "new-password"
            }
        ),
    )
    two_factor_enabled = forms.BooleanField(
        required=False,
        initial=True,
        label="Włącz weryfikację dwuetapową przy logowaniu",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )

    class Meta:
        model = PanelUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
            "two_factor_enabled",
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('Adres e-mail jest wymagany.')
        if PanelUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Ten adres e-mail jest już używany.')
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise forms.ValidationError('Imię jest wymagane.')
        if len(first_name.strip()) < 2:
            raise forms.ValidationError('Imię musi mieć co najmniej 2 znaki.')
        # Tylko litery (w tym akcentowane)
        if not first_name.isalpha():
            raise forms.ValidationError('Imię może zawierać tylko litery, bez spacji i znaków specjalnych.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise forms.ValidationError('Nazwisko jest wymagane.')
        if len(last_name.strip()) < 2:
            raise forms.ValidationError('Nazwisko musi mieć co najmniej 2 znaki.')
        # Tylko litery (w tym akcentowane)
        if not last_name.isalpha():
            raise forms.ValidationError('Nazwisko może zawierać tylko litery, bez spacji i znaków specjalnych.')
        return last_name

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not password1:
            raise forms.ValidationError('Hasło jest wymagane.')
        if len(password1) < 8:
            raise forms.ValidationError('Hasło musi mieć co najmniej 8 znaków.')
        if not re.search(r'[a-z]', password1):
            raise forms.ValidationError('Hasło musi zawierać przynajmniej jedną małą literę.')
        if not re.search(r'[A-Z]', password1):
            raise forms.ValidationError('Hasło musi zawierać przynajmniej jedną wielką literę.')
        if not re.search(r'[0-9]', password1):
            raise forms.ValidationError('Hasło musi zawierać przynajmniej jedną cyfrę.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
            raise forms.ValidationError('Hasło musi zawierać przynajmniej jeden znak specjalny.')
        return password1

    def clean_password2(self):
        password2 = self.cleaned_data.get('password2')
        if not password2:
            raise forms.ValidationError('Powtórzenie hasła jest wymagane.')
        return password2
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Hasła nie są takie same.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].capitalize()
        user.last_name = self.cleaned_data["last_name"].capitalize()
        user.email = self.cleaned_data["email"]
        user.two_factor_enabled = self.cleaned_data.get("two_factor_enabled", False)
        user.is_staff = False
        user.is_superuser = False
        user.is_active = False
        if commit:
            user.save()
        return user


class CompanyForm(forms.ModelForm):
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nazwa firmy",
                "class": "form-control",
            }
        )
    )
    phone = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Telefon",
                "class": "form-control",
                "autocomplete": "tel"
            }
        ),
    )
    """
    Company ma main_address = Address, więc adres rozbijamy na pola formularza,
    a Address tworzymy ręcznie w widoku.
    """
    street = forms.CharField(label="Ulica i nr", required=False)
    postcode = forms.CharField(label="Kod pocztowy", required=False)
    city = forms.CharField(label="Miasto", required=False)

    class Meta:
        model = Company
        fields = ["name", "email", "phone"]

    def clean_phone(self):
        telefon = self.cleaned_data.get('phone')
        if not telefon:
            raise forms.ValidationError("Numer telefonu jest wymagany.")
        if telefon:
            if telefon < 100000000 or telefon > 999999999:
                raise forms.ValidationError('Podaj prawidłowy 9-cyfrowy numer telefonu.')
        return telefon
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("Nazwa firmy jest wymagana.")
        return name

    def clean_postcode(self):
        postcode = (self.cleaned_data.get("postcode") or "").strip()
        if not postcode:
            raise forms.ValidationError("Kod pocztowy jest wymagany.")
        if not re.match(r"^\d{2}-\d{3}$", postcode):
            raise forms.ValidationError("Kod pocztowy musi być w formacie 00-000.")
        return postcode

    def clean_city(self):
        city = (self.cleaned_data.get("city") or "").strip()
        if not city:
            raise forms.ValidationError("Miasto jest wymagane.")
        if len(city) < 2:
            raise forms.ValidationError("Miasto musi mieć co najmniej 2 znaki.")
        # litery + spacje
        if not all(ch.isalpha() or ch.isspace() for ch in city):
            raise forms.ValidationError("Miasto może zawierać tylko litery i spacje.")
        return city

    def clean_street(self):
        street = (self.cleaned_data.get("street") or "").strip()
        if not street:
            raise forms.ValidationError("Ulica i numer są wymagane.")
        if len(street) < 3:
            raise forms.ValidationError("Ulica i numer muszą mieć co najmniej 3 znaki.")
        return street


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing_classes + " form-control").strip()
