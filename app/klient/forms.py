# app/klient/forms.py
import re
from django import forms

from app.klient.models import Client, ClientActivity, ClientLocation, ClientNote, ContactPerson
from app.core.models import Address, PanelUser
from app.core.geocoding import GeocodingService


class ClientForm(forms.ModelForm):
    """
    Formularz dodawania/edycji klienta:

    - Osoba prywatna:
        * first_name, last_name wymagane
        * name opcjonalne (auto-uzupełnimy przy save jeśli puste)
        * nip opcjonalny
    - Firma:
        * name + nip wymagane
        * first_name/last_name NIE są wymagane (osoba kontaktowa jest w contact_*)
    - Adresy:
        * shipping_* zawsze wymagane
        * billing_other=True -> billing_* wymagane
        * billing_other=False -> billing_address = shipping_address
    """

    # --- ADRES SERWISOWY (shipping) ---
    shipping_street = forms.CharField(
        label="Ulica",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "np. Prosta"}),
    )
    shipping_street_no = forms.CharField(
        label="Nr domu / lokalu",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "np. 12/4"}),
    )
    shipping_zip = forms.CharField(
        label="Kod pocztowy",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "np. 00-000"}),
    )
    shipping_city = forms.CharField(
        label="Miejscowość",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "np. Warszawa"}),
    )
    shipping_country = forms.CharField(
        label="Kraj",
        required=True,
        initial="Polska",
        widget=forms.TextInput(attrs={"placeholder": "np. Polska"}),
    )

    # --- CHECKBOX: inny adres rozliczeniowy ---
    billing_other = forms.BooleanField(
        label="Inny adres rozliczeniowy",
        required=False,
        widget=forms.CheckboxInput(),
    )

    # --- ADRES ROZLICZENIOWY (billing) ---
    billing_street = forms.CharField(
        label="Ulica (rozliczeniowy)",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "np. Prosta"}),
    )
    billing_street_no = forms.CharField(
        label="Nr domu / lokalu (rozliczeniowy)",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "np. 12/4"}),
    )
    billing_zip = forms.CharField(
        label="Kod pocztowy (rozliczeniowy)",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "np. 00-000"}),
    )
    billing_city = forms.CharField(
        label="Miejscowość (rozliczeniowy)",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "np. Warszawa"}),
    )
    billing_country = forms.CharField(
        label="Kraj (rozliczeniowy)",
        required=False,
        initial="Polska",
        widget=forms.TextInput(attrs={"placeholder": "np. Polska"}),
    )

    # --- OSOBA KONTAKTOWA (dla firmy) - pola z template ---
    contact_first_name = forms.CharField(required=False)
    contact_last_name = forms.CharField(required=False)
    contact_email = forms.EmailField(required=False)
    contact_phone = forms.CharField(required=False)

    class Meta:
        model = Client
        fields = [
            "client_type",
            "first_name",
            "last_name",
            "name",
            "nip",
            "email",
            "phone",
            "caretaker",
            "notes",
        ]
        widgets = {
            "client_type": forms.Select(),
            "first_name": forms.TextInput(attrs={"placeholder": "np. Jan", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "np. Kowalski", "autocomplete": "family-name"}),
            "name": forms.TextInput(attrs={"placeholder": "np. ACME Sp. z o.o."}),
            "nip": forms.TextInput(attrs={"placeholder": "np. 5250000000", "inputmode": "numeric"}),
            "email": forms.EmailInput(attrs={"placeholder": "np. kontakt@firma.pl", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "np. +48 600 000 000", "autocomplete": "tel"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Wewnętrzne informacje o kliencie..."}),
            "caretaker": forms.Select(),
        }

    # ----------------------------
    # WALIDACJE
    # ----------------------------

    def clean_first_name(self):
        first_name = (self.cleaned_data.get("first_name") or "").strip()
        client_type = self.cleaned_data.get("client_type")

        # ✅ tylko osoba prywatna wymaga first/last
        if client_type == Client.TYPE_PRIVATE:
            if not first_name:
                raise forms.ValidationError("Imię jest wymagane.")
            if len(first_name) < 2:
                raise forms.ValidationError("Imię musi mieć co najmniej 2 znaki.")
            if not first_name.replace(" ", "").isalpha():
                raise forms.ValidationError("Imię może zawierać tylko litery i spacje.")
        return first_name

    def clean_last_name(self):
        last_name = (self.cleaned_data.get("last_name") or "").strip()
        client_type = self.cleaned_data.get("client_type")

        if client_type == Client.TYPE_PRIVATE:
            if not last_name:
                raise forms.ValidationError("Nazwisko jest wymagane.")
            if len(last_name) < 2:
                raise forms.ValidationError("Nazwisko musi mieć co najmniej 2 znaki.")
            if not last_name.replace(" ", "").isalpha():
                raise forms.ValidationError("Nazwisko może zawierać tylko litery i spacje.")
        return last_name

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        client_type = self.cleaned_data.get("client_type")

        if client_type == Client.TYPE_COMPANY:
            if not name:
                raise forms.ValidationError("Nazwa firmy jest wymagana dla typu 'Firma'.")
            if len(name) < 2:
                raise forms.ValidationError("Nazwa firmy musi mieć co najmniej 2 znaki.")
        return name

    def clean_nip(self):
        nip = (self.cleaned_data.get("nip") or "").replace(" ", "").replace("-", "")
        client_type = self.cleaned_data.get("client_type")

        if client_type == Client.TYPE_COMPANY:
            if not nip:
                raise forms.ValidationError("NIP jest wymagany dla typu 'Firma'.")
            if len(nip) != 10 or not nip.isdigit():
                raise forms.ValidationError("NIP musi mieć dokładnie 10 cyfr.")
        else:
            if nip and (len(nip) != 10 or not nip.isdigit()):
                raise forms.ValidationError("NIP musi mieć dokładnie 10 cyfr.")
        return nip

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""
        if not re.match(r"^[0-9+\-\s]{7,}$", phone):
            raise forms.ValidationError("Podaj poprawny numer telefonu.")
        return phone

    def clean_shipping_zip(self):
        zip_code = (self.cleaned_data.get("shipping_zip") or "").strip()
        if not re.match(r"^\d{2}-\d{3}$", zip_code):
            raise forms.ValidationError("Kod pocztowy musi być w formacie 00-000.")
        return zip_code

    def clean_shipping_city(self):
        city = (self.cleaned_data.get("shipping_city") or "").strip()
        if len(city) < 2:
            raise forms.ValidationError("Miejscowość musi mieć co najmniej 2 znaki.")
        if not all(ch.isalpha() or ch.isspace() for ch in city):
            raise forms.ValidationError("Miejscowość może zawierać tylko litery i spacje.")
        return city

    def clean(self):
        cleaned = super().clean()

        # billing wymagany tylko gdy zaznaczone
        if cleaned.get("billing_other"):
            b_street = (cleaned.get("billing_street") or "").strip()
            b_no = (cleaned.get("billing_street_no") or "").strip()
            b_zip = (cleaned.get("billing_zip") or "").strip()
            b_city = (cleaned.get("billing_city") or "").strip()

            if not (b_street and b_no and b_zip and b_city):
                raise forms.ValidationError(
                    "Przy zaznaczeniu 'Inny adres rozliczeniowy' wszystkie pola adresu rozliczeniowego są wymagane."
                )

            if not re.match(r"^\d{2}-\d{3}$", b_zip):
                self.add_error("billing_zip", "Kod pocztowy musi być w formacie 00-000.")
            if len(b_city) < 2 or not all(ch.isalpha() or ch.isspace() for ch in b_city):
                self.add_error("billing_city", "Miejscowość może zawierać tylko litery i spacje i mieć min. 2 znaki.")

        # Kontakt dla firmy – opcjonalny, ale jak coś wpisano to waliduj spójnie (bez wymuszania)
        if cleaned.get("client_type") == Client.TYPE_COMPANY:
            c_email = (cleaned.get("contact_email") or "").strip()
            c_phone = (cleaned.get("contact_phone") or "").strip()
            if c_phone and not re.match(r"^[0-9+\-\s]{7,}$", c_phone):
                self.add_error("contact_phone", "Podaj poprawny numer telefonu osoby kontaktowej.")
            if c_email and "@" not in c_email:
                self.add_error("contact_email", "Podaj poprawny e-mail osoby kontaktowej.")

        # ===============================
        # 🔥 WALIDACJA ISTNIENIA ADRESU (GEOCODING)
        # ===============================

        street = (cleaned.get("shipping_street") or "").strip()
        street_no = (cleaned.get("shipping_street_no") or "").strip()
        zip_code = (cleaned.get("shipping_zip") or "").strip()
        city = (cleaned.get("shipping_city") or "").strip()
        country = (cleaned.get("shipping_country") or "Polska").strip()

        full_street = f"{street} {street_no}".strip()

        if full_street and city and zip_code:
            try:
                lat, lng = GeocodingService.get_coordinates(
                    street=full_street,
                    city=city,
                    postcode=zip_code,
                )
            except Exception:
                lat, lng = None, None

            if lat is None or lng is None:
                self.add_error(
                    "shipping_city",
                    "Nie można znaleźć podanego adresu. Sprawdź czy dane są poprawne."
                )
            else:
                cleaned["_shipping_lat"] = lat
                cleaned["_shipping_lng"] = lng

        return cleaned

    # ----------------------------
    # ZAPIS
    # ----------------------------

    def save(self, commit=True, company=None):
        """
        Zapisuje Client + tworzy/aktualizuje Address dla shipping i billing.
        """

        instance: Client = super().save(commit=False)

        if company is not None:
            instance.company = company

        # 🔹 auto-name dla osoby prywatnej
        if instance.client_type == Client.TYPE_PRIVATE and not (instance.name or "").strip():
            full_name = f"{(instance.first_name or '').strip()} {(instance.last_name or '').strip()}".strip()
            instance.name = full_name

        if commit:
            instance.save()

        # ===============================
        # 🔹 SHIPPING ADDRESS
        # ===============================
        ship_street = (self.cleaned_data.get("shipping_street") or "").strip()
        ship_street_no = (self.cleaned_data.get("shipping_street_no") or "").strip()

        if instance.pk and instance.shipping_address:
            shipping_addr = instance.shipping_address
            shipping_addr.street = ship_street
            shipping_addr.street_no = ship_street_no
            shipping_addr.postcode = (self.cleaned_data.get("shipping_zip") or "").strip()
            shipping_addr.city = (self.cleaned_data.get("shipping_city") or "").strip()
            shipping_addr.country = (self.cleaned_data.get("shipping_country") or "Polska").strip() or "Polska"
            shipping_addr.save()
        else:
            shipping_addr = Address.objects.create(
                street=ship_street,
                street_no=ship_street_no,
                postcode=(self.cleaned_data.get("shipping_zip") or "").strip(),
                city=(self.cleaned_data.get("shipping_city") or "").strip(),
                country=(self.cleaned_data.get("shipping_country") or "Polska").strip() or "Polska",
                latitude=self.cleaned_data.get("_shipping_lat"),
                longitude=self.cleaned_data.get("_shipping_lng"),
            )

        instance.shipping_address = shipping_addr

        # ===============================
        # 🔹 BILLING ADDRESS
        # ===============================
        if self.cleaned_data.get("billing_other"):

            bill_street = (self.cleaned_data.get("billing_street") or "").strip()
            bill_street_no = (self.cleaned_data.get("billing_street_no") or "").strip()

            if instance.pk and instance.billing_address and instance.billing_address != instance.shipping_address:
                billing_addr = instance.billing_address
                billing_addr.street = bill_street
                billing_addr.street_no = bill_street_no
                billing_addr.postcode = (self.cleaned_data.get("billing_zip") or "").strip()
                billing_addr.city = (self.cleaned_data.get("billing_city") or "").strip()
                billing_addr.country = (self.cleaned_data.get("billing_country") or "Polska").strip() or "Polska"
                billing_addr.save()
            else:
                billing_addr = Address.objects.create(
                    street=bill_street,
                    street_no=bill_street_no,
                    postcode=(self.cleaned_data.get("billing_zip") or "").strip(),
                    city=(self.cleaned_data.get("billing_city") or "").strip(),
                    country=(self.cleaned_data.get("billing_country") or "Polska").strip() or "Polska",
                )

            instance.billing_address = billing_addr

        else:
            instance.billing_address = shipping_addr

        if commit:
            instance.save()

        return instance

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # caretaker tylko z firmy
        qs = PanelUser.objects.all()
        if user and getattr(user, "company_id", None):
            qs = qs.filter(company=user.company)
        self.fields["caretaker"].queryset = qs.order_by("first_name", "last_name")

        # klasy bootstrap
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = (existing + " form-check-input").strip()
            else:
                field.widget.attrs["class"] = (existing + " form-control").strip()


class ClientQuickNoteForm(forms.ModelForm):
    class Meta:
        model = ClientActivity
        fields = ["description"]
        widgets = {
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Treść notatki...",
            })
        }

class ClientNoteForm(forms.ModelForm):
    class Meta:
        model = ClientNote
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Treść notatki...",
                "required": True,
            })
        }



class ContactPersonCreateForm(forms.ModelForm):
    class Meta:
        model = ContactPerson
        fields = ["first_name", "last_name", "email", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "np. Anna"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "np. Nowak"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "np. anna@firma.pl"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "np. +48 700 000 000"}),
        }

# app/klient/forms.py - poprawione formularze lokalizacji

class ClientLocationForm(forms.ModelForm):
    street = forms.CharField(
        label="Ulica",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control location-input",
            "placeholder": "np. Prosta",
        })
    )

    street_no = forms.CharField(
        label="Nr domu / lokalu",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control location-input",
            "placeholder": "np. 12/4",
        })
    )

    zip_code = forms.CharField(
        label="Kod pocztowy",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control location-input",
            "placeholder": "np. 00-000",
        })
    )

    city = forms.CharField(
        label="Miasto",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control location-input",
            "placeholder": "np. Warszawa",
        })
    )

    country = forms.CharField(
        label="Kraj",
        required=False,
        initial="Polska",
        widget=forms.TextInput(attrs={
            "class": "form-control location-input",
            "placeholder": "np. Polska",
        })
    )

    class Meta:
        model = ClientLocation
        fields = [
            "name",
            "code",
            "contact_person",
            "notes",
            "is_default",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control location-input",
                "placeholder": "np. Siedziba główna",
            }),
            "code": forms.TextInput(attrs={
                "class": "form-control location-input",
                "placeholder": "np. LOC-001",
            }),
            "contact_person": forms.Select(attrs={
                "class": "form-select location-input",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control location-input",
                "rows": 4,
                "placeholder": "Dodatkowe informacje...",
            }),
            "is_default": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop("client", None)
        self.company = kwargs.pop("company", None)

        super().__init__(*args, **kwargs)

        if self.client:
            self.fields["contact_person"].queryset = ContactPerson.objects.filter(
                client=self.client,
                company=self.company,
            )
        else:
            self.fields["contact_person"].queryset = ContactPerson.objects.none()

        self.fields["contact_person"].required = False
        self.fields["contact_person"].empty_label = "— wybierz —"

        if self.instance and self.instance.pk and self.instance.address:
            address = self.instance.address

            self.fields["street"].initial = address.street
            self.fields["street_no"].initial = getattr(address, "street_no", "")
            self.fields["zip_code"].initial = address.postcode
            self.fields["city"].initial = address.city
            self.fields["country"].initial = address.country or "Polska"

    def clean_zip_code(self):
        zip_code = (self.cleaned_data.get("zip_code") or "").strip()

        if zip_code:
            import re
            if not re.match(r"^\d{2}-\d{3}$", zip_code):
                raise forms.ValidationError("Kod pocztowy musi być w formacie 00-000.")

        return zip_code

    def clean_city(self):
        city = (self.cleaned_data.get("city") or "").strip()

        if city:
            if len(city) < 2:
                raise forms.ValidationError("Miasto musi mieć co najmniej 2 znaki.")

            if not all(ch.isalpha() or ch.isspace() or ch == "-" for ch in city):
                raise forms.ValidationError("Miasto może zawierać tylko litery, spacje i myślniki.")

        return city

    def clean(self):
        cleaned_data = super().clean()

        street = (cleaned_data.get("street") or "").strip()
        street_no = (cleaned_data.get("street_no") or "").strip()
        zip_code = (cleaned_data.get("zip_code") or "").strip()
        city = (cleaned_data.get("city") or "").strip()
        country = (cleaned_data.get("country") or "Polska").strip()

        if street or street_no or zip_code or city:
            if not street:
                self.add_error("street", "Podaj ulicę.")
            if not street_no:
                self.add_error("street_no", "Podaj nr domu / lokalu.")
            if not zip_code:
                self.add_error("zip_code", "Podaj kod pocztowy.")
            if not city:
                self.add_error("city", "Podaj miasto.")

        cleaned_data["_address_data"] = {
            "street": street,
            "street_no": street_no,
            "postcode": zip_code,
            "city": city,
            "country": country,
        }

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.client:
            instance.client = self.client

        if self.company:
            instance.company = self.company

        address_data = self.cleaned_data.get("_address_data", {})

        street = address_data.get("street", "")
        street_no = address_data.get("street_no", "")
        postcode = address_data.get("postcode", "")
        city = address_data.get("city", "")
        country = address_data.get("country", "Polska")

        if street or street_no or postcode or city:
            if instance.address:
                address = instance.address
            else:
                address = Address()

            address.street = street
            address.street_no = street_no
            address.postcode = postcode
            address.city = city
            address.country = country

            address.save()

            instance.address = address

        if commit:
            instance.save()

        return instance


class ClientLocationQuickForm(forms.ModelForm):

    street = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    street_no = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    zip_code = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    city = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    country = forms.CharField(
        required=False,
        initial="Polska",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = ClientLocation

        fields = (
            "name",
            "code",
            "contact_person",
            "notes",
            "is_default",
            "is_active",
        )

        widgets = {

            "name": forms.TextInput(attrs={"class": "form-control"}),

            "code": forms.TextInput(attrs={"class": "form-control"}),

            "contact_person": forms.Select(attrs={"class": "form-select"}),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2
            }),

            "is_default": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

        }

    # ------------------------------------------------
    # INIT (KLUCZOWE dla EDIT)
    # ------------------------------------------------

    def __init__(self, *args, **kwargs):

        self.client = kwargs.pop("client", None)
        self.company = kwargs.pop("company", None)

        super().__init__(*args, **kwargs)

        # FILTR CONTACT PERSON
        if self.client:
            self.fields["contact_person"].queryset = ContactPerson.objects.filter(
                client=self.client,
                company=self.company
            )

        # INITIAL is_active (NAPRAWIA reset na False)
        if self.instance and self.instance.pk:

            self.fields["is_active"].initial = self.instance.is_active
            self.fields["is_default"].initial = self.instance.is_default

            if self.instance.address:

                addr = self.instance.address

                if addr.street:

                    parts = addr.street.rsplit(" ", 1)

                    if len(parts) == 2:
                        self.fields["street"].initial = parts[0]
                        self.fields["street_no"].initial = parts[1]
                    else:
                        self.fields["street"].initial = addr.street

                self.fields["zip_code"].initial = addr.postcode
                self.fields["city"].initial = addr.city
                self.fields["country"].initial = addr.country

    # ------------------------------------------------
    # SAVE
    # ------------------------------------------------

    def save(self, commit=True):

        instance = super().save(commit=False)

        instance.client = self.client
        instance.company = self.company

        # NAPRAWIA is_active reset
        instance.is_active = self.cleaned_data.get(
            "is_active",
            instance.is_active
        )

        instance.is_default = self.cleaned_data.get(
            "is_default",
            instance.is_default
        )

        street = self.cleaned_data["street"]
        street_no = self.cleaned_data["street_no"]

        postcode = self.cleaned_data["zip_code"]
        city = self.cleaned_data["city"]
        country = self.cleaned_data.get("country") or "Polska"

        street_full = f"{street} {street_no}"

        # UPDATE or CREATE address

        if instance.address:

            addr = instance.address

            addr.street = street_full
            addr.postcode = postcode
            addr.city = city
            addr.country = country

            addr.save()

        else:

            addr = Address.objects.create(
                street=street_full,
                postcode=postcode,
                city=city,
                country=country
            )

            instance.address = addr

        if commit:
            instance.save()

        return instance