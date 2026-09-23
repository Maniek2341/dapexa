from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.core.models import CompanySettings

from .models import TimeEntry, TimeEntryStatus, WorkMode


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = [
            "date",
            "start_time",
            "end_time",
            "work_mode",
        ]
        widgets = {
            "date": forms.TextInput(attrs={
                "class": "form-control datepicker",
            }),
            "start_time": forms.TextInput(attrs={
                "class": "form-control timepicker",
            }),
            "end_time": forms.TextInput(attrs={
                "class": "form-control timepicker",
            }),
            "work_mode": forms.Select(attrs={
                "class": "form-select",
            }),
        }
        labels = {
            "date": "Data",
            "start_time": "Godzina od",
            "end_time": "Godzina do",
            "work_mode": "Tryb pracy",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        self.fields["date"].input_formats = ["%Y-%m-%d"]
        self.fields["start_time"].input_formats = ["%H:%M"]
        self.fields["end_time"].input_formats = ["%H:%M"]

        if not self.instance.pk:
            default_start_time = "07:00"
            default_end_time = "15:00"

            user = getattr(self.request, "user", None)
            if user and user.is_authenticated and user.company_id:
                company_settings = (
                    CompanySettings.objects
                    .filter(company_id=user.company_id)
                    .only("default_work_start_time", "default_work_end_time")
                    .first()
                )
                if company_settings:
                    default_start_time = company_settings.default_work_start_time.strftime("%H:%M")
                    default_end_time = company_settings.default_work_end_time.strftime("%H:%M")

            if not self.initial.get("date"):
                self.fields["date"].initial = timezone.localdate()

            if not self.initial.get("work_mode"):
                self.fields["work_mode"].initial = WorkMode.OFFICE

            if not self.initial.get("start_time"):
                self.fields["start_time"].initial = default_start_time

            if not self.initial.get("end_time"):
                self.fields["end_time"].initial = default_end_time

    def clean_date(self):
        work_date = self.cleaned_data["date"]
        today = timezone.localdate()

        if work_date > today:
            raise ValidationError("Nie można dodać wpisu na przyszłą datę.")

        if work_date.weekday() >= 5:
            raise ValidationError("Nie można dodać wpisu w weekend.")

        return work_date

    def clean(self):
        cleaned_data = super().clean()

        work_date = cleaned_data.get("date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if work_date and self.request and self.request.user.is_authenticated:
            from app.urlop.models import LeaveRequest

            approved_leave = LeaveRequest.objects.filter(
                company=self.request.user.company,
                user=self.request.user,
                status=LeaveRequest.Status.APPROVED,
                date_from__lte=work_date,
                date_to__gte=work_date,
            ).exists()
            if approved_leave:
                self.add_error(
                    "date",
                    "Nie można dodać czasu pracy w dniu zatwierdzonego urlopu.",
                )

            qs = TimeEntry.objects.filter(
                company=self.request.user.company,
                user=self.request.user,
                date=work_date,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error("date", "Dla tej daty masz już dodane godziny pracy.")

        if start_time and end_time and start_time >= end_time:
            self.add_error("start_time", "Godzina od musi być wcześniejsza niż godzina do.")
            self.add_error("end_time", "Godzina do musi być późniejsza niż godzina od.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.request and self.request.user.is_authenticated:
            instance.user = self.request.user
            if not instance.company_id:
                instance.company = self.request.user.company
            instance.status = TimeEntryStatus.APPROVED
            instance.approved_at = timezone.now()
            instance.approved_by = self.request.user

        if commit:
            instance.save()

        return instance


class MissingHoursRequestForm(forms.Form):
    date = forms.DateField(
        label="Data",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control",
        })
    )
    reason = forms.CharField(
        label="Powód",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = ["%Y-%m-%d"]
        self.fields["date"].initial = timezone.localdate()

    def clean_date(self):
        req_date = self.cleaned_data["date"]
        today = timezone.localdate()

        if req_date > today:
            raise ValidationError("Nie możesz wysłać prośby dla przyszłej daty.")

        return req_date


class EditHoursRequestForm(forms.Form):
    entry = forms.ModelChoiceField(
        label="Wpis do edycji",
        queryset=TimeEntry.objects.none(),
        widget=forms.Select(attrs={
            "class": "form-select",
        })
    )

    new_start_time = forms.TimeField(
        label="Nowa godzina rozpoczęcia",
        widget=forms.TimeInput(attrs={
            "type": "time",
            "class": "form-control",
        })
    )

    new_end_time = forms.TimeField(
        label="Nowa godzina zakończenia",
        widget=forms.TimeInput(attrs={
            "type": "time",
            "class": "form-control",
        })
    )

    reason = forms.CharField(
        label="Powód edycji",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
        })
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        self.fields["new_start_time"].input_formats = ["%H:%M"]
        self.fields["new_end_time"].input_formats = ["%H:%M"]

        self.fields["entry"].queryset = TimeEntry.objects.filter(
            company=user.company,
            user=user
        ).order_by("-date", "-created_at")

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("new_start_time")
        end = cleaned.get("new_end_time")

        if start and end and end <= start:
            raise forms.ValidationError(
                "Godzina zakończenia musi być późniejsza niż rozpoczęcia."
            )

        return cleaned


class SingleEntryEditRequestForm(forms.Form):
    new_start_time = forms.TimeField(
        label="Nowa godzina rozpoczęcia",
        widget=forms.TimeInput(attrs={
            "type": "time",
            "class": "form-control",
        })
    )

    new_end_time = forms.TimeField(
        label="Nowa godzina zakończenia",
        widget=forms.TimeInput(attrs={
            "type": "time",
            "class": "form-control",
        })
    )

    reason = forms.CharField(
        label="Powód edycji",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_start_time"].input_formats = ["%H:%M"]
        self.fields["new_end_time"].input_formats = ["%H:%M"]

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("new_start_time")
        end = cleaned.get("new_end_time")

        if start and end and end <= start:
            raise forms.ValidationError(
                "Godzina zakończenia musi być późniejsza niż rozpoczęcia."
            )

        return cleaned


class RejectTimeEntryRequestForm(forms.Form):
    reason = forms.CharField(
        label="Powód odrzucenia",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Podaj powód odrzucenia",
        })
    )
