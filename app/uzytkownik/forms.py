from django import forms
from django.contrib.auth.models import Permission
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm, PasswordChangeForm, \
    PasswordResetForm
from app.core.models import PanelUser
from app.core.notification_preferences import NOTIFICATION_MODULE_CHOICES
from app.uzytkownik.models import CompanyRoleGroup, EmployeeContract, EmployeeTraining
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


class UserNotificationPreferencesForm(forms.ModelForm):
    email_notification_modules = forms.MultipleChoiceField(
        label="Powiadomienia z modułów",
        choices=NOTIFICATION_MODULE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = PanelUser
        fields = ["email_notification_modules"]


class UserSecuritySettingsForm(forms.ModelForm):
    class Meta:
        model = PanelUser
        fields = ["two_factor_enabled"]
        labels = {
            "two_factor_enabled": "Weryfikacja dwuetapowa przy logowaniu",
        }
        widgets = {
            "two_factor_enabled": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }


class UserPrivateDataForm(forms.ModelForm):
    class Meta:
        model = PanelUser
        fields = [
            "first_name",
            "last_name",
            "phone_priv",
            "phone",
            "birthday",
            "avatar",
        ]
        labels = {
            "first_name": "Imię",
            "last_name": "Nazwisko",
            "phone_priv": "Telefon prywatny",
            "phone": "Telefon firmowy",
            "birthday": "Data urodzenia",
            "avatar": "Zdjęcie profilowe",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Imię",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nazwisko",
            }),
            "phone_priv": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Telefon prywatny",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Telefon firmowy",
            }),
            "birthday": forms.DateInput(format="%Y-%m-%d", attrs={
                "class": "form-control",
                "type": "date",
            }),
            "avatar": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/png,image/jpeg,image/webp",
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar or not hasattr(avatar, "content_type"):
            return avatar

        allowed_types = {"image/png", "image/jpeg", "image/webp"}
        if avatar.content_type not in allowed_types:
            raise forms.ValidationError("Zdjęcie profilowe musi być plikiem PNG, JPG albo WEBP.")
        return avatar


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "E-mail",
                "class": "form-control",
                "autocomplete": "email"
            }
        ))
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Hasło",
                "class": "form-control",
                "autocomplete": "current-password"
            }
        ))


class LoginTwoFactorForm(forms.Form):
    code = forms.CharField(
        label="Kod weryfikacyjny",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Kod z e-maila",
                "class": "form-control",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": r"\d{6}",
            }
        ),
    )

    def clean_code(self):
        code = (self.cleaned_data.get("code") or "").strip()
        if not code.isdigit():
            raise forms.ValidationError("Kod musi składać się z 6 cyfr.")
        return code

class ForgotForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email",
                "class": "form-control",
                "type": "email",
                "autocomplete": "email"
            }
        ))

    class Meta:
        model = PanelUser
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            PanelUser.objects.get(email=email)
        except PanelUser.DoesNotExist:
            raise forms.ValidationError('Taki e-mail nie istnieje')

        return email

class SettPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Hasło",
                "class": "form-control",
                'type': 'password',
                'autocomplete': 'new-password'
            }
        ),
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Potwierdz hasło",
                "class": "form-control",
                'type': 'password',
                'autocomplete': 'new-password'
            }
        )
    )

    class Meta:
        model = PanelUser
        fields = ('password1', 'password2')

    def clean(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 != password2:
            raise forms.ValidationError('Hasła nie są takie same')

User = get_user_model()


class EmployeePermissionChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, permission):
        module_name = permission.content_type.app_label.replace("_", " ").title()
        return f"{module_name} — {permission.name}"


class EmployeePermissionForm(forms.ModelForm):
    user_permissions = EmployeePermissionChoiceField(
        queryset=Permission.objects.none(),
        required=False,
        label="Uprawnienia pracownika",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = ["user_permissions"]

    def __init__(self, *args, permission_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if permission_queryset is not None:
            self.fields["user_permissions"].queryset = permission_queryset

    def _save_m2m(self):
        assignable_queryset = self.fields["user_permissions"].queryset
        assignable_ids = assignable_queryset.values_list("pk", flat=True)
        preserved_permissions = self.instance.user_permissions.exclude(
            pk__in=assignable_ids
        )
        selected_permissions = self.cleaned_data["user_permissions"]

        self.instance.user_permissions.set(
            [*preserved_permissions, *selected_permissions]
        )


class CompanyRoleGroupForm(forms.ModelForm):
    permissions = EmployeePermissionChoiceField(
        queryset=Permission.objects.none(),
        required=False,
        label="Uprawnienia grupy",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = CompanyRoleGroup
        fields = ["name", "role"]
        labels = {
            "name": "Nazwa grupy",
            "role": "Rola pracowników",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "np. Managerowie serwisu",
            }),
            "role": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, company=None, permission_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields["role"].choices = [
            choice
            for choice in PanelUser.Role.choices
            if choice[0] not in [PanelUser.Role.OWNER, PanelUser.Role.CLIENT]
        ]
        if permission_queryset is not None:
            self.fields["permissions"].queryset = permission_queryset
        if self.instance.pk:
            self.initial["permissions"] = self.instance.group.permissions.all()
            if self.instance.is_system:
                self.fields["name"].disabled = True
                self.fields["role"].disabled = True

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        existing_groups = CompanyRoleGroup.objects.filter(
            company=self.company,
            name__iexact=name,
        )
        if self.instance.pk:
            existing_groups = existing_groups.exclude(pk=self.instance.pk)
        if existing_groups.exists():
            raise forms.ValidationError("Grupa o tej nazwie już istnieje w firmie.")
        return name

    def _save_m2m(self):
        self.instance.group.permissions.set(self.cleaned_data["permissions"])


class EmployeeCreateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "gender",
            "birthday",
            "role",
            "wyksztalcenie",
            "phone_priv",
            "phone",
            "position",
            "is_active_employee",
            "employment_start_date",
            "previous_employment_years",
            "employment_fraction",
        ]

        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Imię",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nazwisko",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "email@firma.pl",
            }),
            "gender": forms.Select(attrs={
                "class": "form-select",
            }),
            "birthday": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "role": forms.Select(attrs={
                "class": "form-select",
            }),
            "wyksztalcenie": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "np. średnie, wyższe, zawodowe",
            }),
            "phone_priv": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Telefon prywatny",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Telefon firmowy",
            }),
            "position": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Stanowisko",
            }),
            "employment_start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "previous_employment_years": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.1",
                "placeholder": "np. 3.5",
            }),
            "employment_fraction": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "max": "1.00",
                "step": "0.01",
                "placeholder": "np. 1.00 lub 0.50",
            }),
            "is_active_employee": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

        labels = {
            "first_name": "Imię",
            "last_name": "Nazwisko",
            "email": "Adres e-mail",
            "gender": "Płeć",
            "birthday": "Data urodzenia",
            "role": "Rola",
            "wyksztalcenie": "Wykształcenie",
            "phone_priv": "Telefon prywatny",
            "phone": "Telefon firmowy",
            "position": "Stanowisko",
            "is_active_employee": "Aktywny pracownik",
            "employment_start_date": "Data rozpoczęcia pracy w firmie",
            "previous_employment_years": "Staż z poprzednich miejsc pracy (lata)",
            "employment_fraction": "Wymiar etatu",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company

        self.fields["is_active_employee"].initial = True

        excluded_roles = [User.Role.CLIENT]
        if not self.instance.pk or self.instance.role != User.Role.OWNER:
            excluded_roles.append(User.Role.OWNER)

        self.fields["role"].choices = [
            choice for choice in self.fields["role"].choices
            if choice[0] not in excluded_roles
        ]

        # Rola właściciela nie może zostać odebrana z formularza pracownika.
        if self.instance.pk and self.instance.role == User.Role.OWNER:
            self.fields["role"].disabled = True

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()

        users_with_email = User.objects.filter(email=email)
        if self.instance.pk:
            users_with_email = users_with_email.exclude(pk=self.instance.pk)

        if users_with_email.exists():
            raise forms.ValidationError("Użytkownik z takim adresem e-mail już istnieje.")

        return email

    def save(self, commit=True):
        is_creating = self.instance._state.adding
        user = super().save(commit=False)

        user.company = self.company
        user.username = None
        user.email = user.email.lower().strip()

        if is_creating:
            user.set_unusable_password()  # hasło zostanie ustawione przez link aktywacyjny
            user.is_staff = True
            user.is_active = False  # konto aktywne dopiero po ustawieniu hasła
            user.is_superuser = False
            user.is_admin = False

        if commit:
            user.save()

        return user


class EmployeeTrainingForm(forms.ModelForm):
    class Meta:
        model = EmployeeTraining
        fields = [
            "name",
            "organizer",
            "completed_at",
            "valid_until",
            "certificate_number",
            "certificate_image",
            "notes",
        ]
        labels = {
            "name": "Nazwa szkolenia",
            "organizer": "Organizator",
            "completed_at": "Data ukończenia",
            "valid_until": "Ważne do",
            "certificate_number": "Numer certyfikatu",
            "certificate_image": "Zdjęcie certyfikatu",
            "notes": "Notatki",
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "np. BHP, SEP, pierwsza pomoc",
            }),
            "organizer": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Organizator szkolenia",
            }),
            "completed_at": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "valid_until": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "certificate_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Numer certyfikatu / zaświadczenia",
            }),
            "certificate_image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/png,image/jpeg,image/webp",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Dodatkowe informacje",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        completed_at = cleaned_data.get("completed_at")
        valid_until = cleaned_data.get("valid_until")
        if completed_at and valid_until and valid_until < completed_at:
            self.add_error("valid_until", "Data ważności nie może być wcześniejsza niż data ukończenia.")
        return cleaned_data

    def clean_certificate_image(self):
        certificate_image = self.cleaned_data.get("certificate_image")
        if not certificate_image or not hasattr(certificate_image, "content_type"):
            return certificate_image

        allowed_types = {"image/png", "image/jpeg", "image/webp"}
        if certificate_image.content_type not in allowed_types:
            raise forms.ValidationError("Certyfikat musi być zdjęciem PNG, JPG albo WEBP.")
        return certificate_image


class EmployeeContractForm(forms.ModelForm):
    class Meta:
        model = EmployeeContract
        fields = [
            "contract_type",
            "date_from",
            "date_to",
            "contract_image",
            "notes",
        ]
        labels = {
            "contract_type": "Rodzaj umowy",
            "date_from": "Data od",
            "date_to": "Data do",
            "contract_image": "Zdjęcie umowy",
            "notes": "Notatki",
        }
        widgets = {
            "contract_type": forms.Select(attrs={
                "class": "form-select",
            }),
            "date_from": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "date_to": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "contract_image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": "image/png,image/jpeg,image/webp",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Dodatkowe informacje o umowie",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from and date_to and date_to < date_from:
            self.add_error("date_to", "Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.")
        return cleaned_data

    def clean_contract_image(self):
        contract_image = self.cleaned_data.get("contract_image")
        if not contract_image or not hasattr(contract_image, "content_type"):
            return contract_image

        allowed_types = {"image/png", "image/jpeg", "image/webp"}
        if contract_image.content_type not in allowed_types:
            raise forms.ValidationError("Umowa musi być zdjęciem PNG, JPG albo WEBP.")
        return contract_image
