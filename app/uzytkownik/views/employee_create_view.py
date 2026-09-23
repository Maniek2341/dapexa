from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.generic import CreateView, UpdateView

from app.uzytkownik.forms import (
    EmployeeContractForm,
    EmployeeCreateForm,
    EmployeeTrainingForm,
)
from app.uzytkownik.models import EmployeeContract, EmployeeTraining

User = get_user_model()

activation_token = PasswordResetTokenGenerator()


class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = EmployeeCreateForm
    template_name = "app/pracownik/add.html"
    success_url = reverse_lazy("employee_list")

    def dispatch(self, request, *args, **kwargs):
        # tylko właściciel i manager mogą dodawać pracowników
        if request.user.is_authenticated and request.user.role not in [
            User.Role.OWNER,
            User.Role.MANAGER,
        ]:
            messages.error(request, "Nie masz uprawnień do dodawania pracowników.")
            return redirect("dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        employee = form.save(commit=False)

        employee.company = self.request.user.company
        employee.is_staff = True
        employee.is_superuser = False
        employee.is_admin = False
        employee.is_active = False  # aktywacja po kliknięciu linku
        # Konto pracownika pozostaje nieaktywne do chwili ustawienia hasła
        # przez link aktywacyjny. Dzięki temu nie da się zalogować na konto
        # utworzone, ale jeszcze nieaktywowane.
        employee.is_active_employee = False

        employee.save()

        # Wyślij email aktywacyjny z linkiem do ustawienia hasła
        self._send_activation_email(employee)

        messages.success(
            self.request,
            f"Pracownik {employee.first_name} {employee.last_name} został dodany. "
            f"Na adres {employee.email} wysłano link aktywacyjny."
        )

        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Popraw błędy w formularzu."
        )
        return super().form_invalid(form)

    def _send_activation_email(self, employee):
        request = self.request
        site = get_current_site(request)
        uid = urlsafe_base64_encode(force_bytes(employee.pk))
        token = activation_token.make_token(employee)

        activation_link = (
            f"{request.scheme}://{site.domain}"
            + reverse("employee_set_password", kwargs={"uidb64": uid, "token": token})
        )

        subject = "Aktywacja konta – ustaw hasło"
        message = render_to_string(
            "app/pracownik/activation_email.txt",
            {
                "employee": employee,
                "activation_link": activation_link,
                "company": self.request.user.company,
            },
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=None,  # używa DEFAULT_FROM_EMAIL z settings
            recipient_list=[employee.email],
            fail_silently=True,
        )


class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = EmployeeCreateForm
    template_name = "app/pracownik/add.html"
    success_url = reverse_lazy("employee_list")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role not in [
            User.Role.OWNER,
            User.Role.MANAGER,
        ]:
            messages.error(request, "Nie masz uprawnień do edycji pracowników.")
            return redirect("dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            User.objects
            .filter(company=self.request.user.company)
            .exclude(role=User.Role.CLIENT)
        )

        if self.request.user.role == User.Role.MANAGER:
            queryset = queryset.exclude(role=User.Role.OWNER)

        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.user.company
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        context["training_form"] = kwargs.get("training_form") or EmployeeTrainingForm()
        context["trainings"] = (
            EmployeeTraining.objects
            .filter(company=self.request.user.company, employee=self.object)
            .order_by("-completed_at", "-created_at")
        )
        context["contract_form"] = kwargs.get("contract_form") or EmployeeContractForm()
        context["contracts"] = list(
            EmployeeContract.objects
            .filter(company=self.request.user.company, employee=self.object)
            .order_by("-date_from", "-created_at")
        )
        context["contract_edit_forms"] = {
            contract.pk: EmployeeContractForm(instance=contract, prefix=f"contract_{contract.pk}")
            for contract in context["contracts"]
        }
        context["contracts_with_forms"] = [
            {
                "contract": contract,
                "form": context["contract_edit_forms"][contract.pk],
            }
            for contract in context["contracts"]
        ]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("form_action")
        if action == "add_training":
            return self._add_training(request)
        if action == "add_contract":
            return self._add_contract(request)
        if action == "edit_contract":
            return self._edit_contract(request)
        if action == "delete_contract":
            return self._delete_contract(request)
        return super().post(request, *args, **kwargs)

    def _add_training(self, request):
        form = EmployeeTrainingForm(request.POST, request.FILES)
        if form.is_valid():
            training = form.save(commit=False)
            training.company = request.user.company
            training.employee = self.object
            training.save()
            messages.success(request, "Szkolenie pracownika zostało dodane.")
            return redirect("employee_edit", pk=self.object.pk)

        messages.error(request, "Popraw błędy w formularzu szkolenia.")
        context = self.get_context_data(form=self.get_form(), training_form=form)
        return self.render_to_response(context)

    def _get_contract(self, request):
        return EmployeeContract.objects.get(
            pk=request.POST.get("contract_id"),
            company=request.user.company,
            employee=self.object,
        )

    def _add_contract(self, request):
        form = EmployeeContractForm(request.POST, request.FILES)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.company = request.user.company
            contract.employee = self.object
            contract.save()
            messages.success(request, "Umowa pracownika została dodana.")
            return redirect("employee_edit", pk=self.object.pk)

        messages.error(request, "Popraw błędy w formularzu umowy.")
        context = self.get_context_data(form=self.get_form(), contract_form=form)
        return self.render_to_response(context)

    def _edit_contract(self, request):
        contract = self._get_contract(request)
        form = EmployeeContractForm(
            request.POST,
            request.FILES,
            instance=contract,
            prefix=f"contract_{contract.pk}",
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Umowa pracownika została zaktualizowana.")
            return redirect("employee_edit", pk=self.object.pk)

        messages.error(request, "Popraw błędy w formularzu edycji umowy.")
        context = self.get_context_data(form=self.get_form())
        context["contract_edit_forms"][contract.pk] = form
        context["contracts_with_forms"] = [
            {
                "contract": item["contract"],
                "form": form if item["contract"].pk == contract.pk else item["form"],
            }
            for item in context["contracts_with_forms"]
        ]
        return self.render_to_response(context)

    def _delete_contract(self, request):
        contract = self._get_contract(request)
        if contract.contract_image:
            contract.contract_image.delete(save=False)
        contract.delete()
        messages.success(request, "Umowa pracownika została usunięta.")
        return redirect("employee_edit", pk=self.object.pk)

    def form_valid(self, form):
        employee = form.save()
        messages.success(
            self.request,
            f"Dane pracownika {employee.first_name} {employee.last_name} zostały zaktualizowane."
        )
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Popraw błędy w formularzu.")
        return super().form_invalid(form)
