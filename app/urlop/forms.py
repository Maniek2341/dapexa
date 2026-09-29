from types import SimpleNamespace

from django import forms
from django.core.exceptions import ValidationError
from app.urlop.calendar import calculate_working_days
from app.urlop.services import days_in_year, validate_request_against_allowance, validate_no_overlap

from .models import LeaveRequest, LeaveType, LeavePool

class LeaveRequestForm(forms.ModelForm):
    is_carryover = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "id_is_carryover",
            }
        ),
    )

    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "date_from", "date_to", "reason", "is_carryover"]
        widgets = {
            "leave_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "date_from": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "date_to": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Powód (opcjonalnie)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user and getattr(self.user, "company", None):
            leave_types = LeaveType.objects.filter(company=self.user.company)
            if not leave_types.filter(pool=LeavePool.VACATION).exists():
                code = "vacation"
                suffix = 1
                while leave_types.filter(code=code).exists():
                    suffix += 1
                    code = f"vacation_{suffix}"
                LeaveType.objects.get_or_create(
                    company=self.user.company,
                    code=code,
                    defaults={
                        "name": "Wypoczynkowy (limit stażowy)",
                        "pool": LeavePool.VACATION,
                        "counts_against_limit": True,
                        # The actual employee limit comes from LeaveAllowance.
                        "annual_limit_days": 26,
                    },
                )
            self.fields["leave_type"].queryset = LeaveType.objects.filter(
                company=self.user.company
            ).order_by("name")
        else:
            self.fields["leave_type"].queryset = LeaveType.objects.none()

    def clean(self):
        cd = super().clean()

        lt = cd.get("leave_type")
        df = cd.get("date_from")
        dt = cd.get("date_to")
        is_carry = bool(cd.get("is_carryover"))

        if not self.user:
            raise ValidationError("Brak użytkownika formularza.")

        if not lt or not df or not dt:
            return cd

        if df > dt:
            raise ValidationError(
                "Data zakończenia nie może być wcześniejsza niż rozpoczęcia."
            )

        requested_days = calculate_working_days(df, dt)
        year = df.year

        if requested_days <= 0:
            raise ValidationError("Wniosek musi obejmować co najmniej 1 dzień roboczy.")
        if is_carry and df.year != dt.year:
            raise ValidationError("Urlop zaległy musi mieścić się w jednym roku kalendarzowym.")
        if is_carry and lt.pool != "vacation":
            raise ValidationError("Urlop zaległy może dotyczyć tylko puli wypoczynkowej.")

        try:
            validate_no_overlap(
                self.user.company, self.user, df, dt,
                exclude_pk=self.instance.pk if self.instance.pk else None,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))

        cd["leave_year"] = year
        cd["days_count_calc"] = requested_days

        try:
            for request_year in range(df.year, dt.year + 1):
                days = days_in_year(SimpleNamespace(date_from=df, date_to=dt), request_year)
                if days:
                    from app.urlop.allowance_generator import ensure_employee_year_allowance
                    ensure_employee_year_allowance(self.user.company, self.user, request_year)
                    validate_request_against_allowance(
                        company=self.user.company,
                        user=self.user,
                        leave_type=lt,
                        year=request_year,
                        requested_days=days,
                        is_carryover=is_carry,
                        date_from=df,
                        date_to=dt,
                        exclude_pk=self.instance.pk if self.instance.pk else None,
                    )
        except ValueError as e:
            raise ValidationError(str(e))

        return cd


class LeaveTypeForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = LeaveType
        fields = [
            "name",
            "code",
            "pool",
            "counts_against_limit",
            "annual_limit_days",
            "is_special",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Wypoczynkowy"
            }),
            "pool": forms.Select(attrs={"class": "form-select"}),
            "code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "np. WYPOCZ"
            }),
            "counts_against_limit": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
            "annual_limit_days": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.5",
                "min": "0"
            }),
            "is_special": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        counts_against_limit = cleaned_data.get("counts_against_limit")
        annual_limit_days = cleaned_data.get("annual_limit_days")

        if not counts_against_limit:
            cleaned_data["annual_limit_days"] = 0

        if counts_against_limit and (annual_limit_days is None or annual_limit_days <= 0):
            raise ValidationError(
                "Jeżeli urlop liczy się do limitu, musi mieć określoną liczbę dni."
            )

        code = (cleaned_data.get("code") or "").strip().lower()
        if code:
            company_id = self.company.pk if self.company else self.instance.company_id
            queryset = LeaveType.objects.filter(company_id=company_id, code=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if company_id and queryset.exists():
                self.add_error("code", "Ten kod jest już używany w tej firmie.")
            if self.instance.pk and any(
                self.instance.__dict__.get(field) != cleaned_data.get(field)
                for field in ("code", "pool", "counts_against_limit", "annual_limit_days", "is_special")
            ) and self.instance.leaverequest_set.exists():
                raise ValidationError("Nie można zmieniać zasad typu użytego w istniejących wnioskach.")
            cleaned_data["code"] = code

        return cleaned_data
