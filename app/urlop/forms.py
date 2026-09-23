from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.urlop.services import validate_request_against_allowance
from datetime import timedelta
import holidays

from .models import LeaveRequest, LeaveType

def calculate_working_days(date_from, date_to):
    if not date_from or not date_to:
        return Decimal("0")

    pl_holidays = holidays.country_holidays("PL")

    current = date_from
    working_days = 0

    while current <= date_to:
        # weekday(): 0=pon, 6=niedz
        if current.weekday() < 5 and current not in pl_holidays:
            working_days += 1
        current += timedelta(days=1)

    return Decimal(working_days)

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

        cd["leave_year"] = year
        cd["days_count_calc"] = requested_days

        try:
            validate_request_against_allowance(
                company=self.user.company,
                user=self.user,
                leave_type=lt,
                year=year,
                requested_days=requested_days,
                is_carryover=is_carry,
            )
        except ValueError as e:
            raise ValidationError(str(e))

        return cd


class LeaveTypeForm(forms.ModelForm):

    class Meta:
        model = LeaveType
        fields = [
            "name",
            "code",
            "counts_against_limit",
            "annual_limit_days",
            "is_special",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Np. Wypoczynkowy"
            }),
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

        return cleaned_data