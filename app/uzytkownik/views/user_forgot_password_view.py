import json

from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views import View

from BusinessManager.settings import DEFAULT_FROM_EMAIL
from app.uzytkownik.forms import ForgotForm
from app.core.models import PanelUser


class UserForgotPasswordView(View):
    reset_token = PasswordResetTokenGenerator()
    title = 'Forgot password'

    def get(self, request):
        context = {
            'title': self.title,
            'forgot_form': ForgotForm()
        }
        return render(request, 'app/uzytkownik/forgotpassword.html', context)

    def post(self, request):
        forgot_form = ForgotForm(request.POST)
        context = {
            'title': self.title,
            'forgot_form': forgot_form
        }

        if forgot_form.is_valid():
            email = forgot_form.cleaned_data["email"]
            qs = PanelUser.objects.filter(email=email)
            site = get_current_site(request)
            if qs.exists():
                for user in qs:
                    if user.is_active:

                        mail_content = {
                            'user': user,
                            'email': email,
                            'domain': site.domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': self.reset_token.make_token(user)
                        }
                        message = render_to_string('app/mail/forgot_password_confirmation.html', mail_content)

                        send_mail(
                                subject="Wiadomość do zmiany hasła",
                                message='',
                                from_email=DEFAULT_FROM_EMAIL,
                                recipient_list=[email],
                                fail_silently=False,
                                html_message=message
                        )
                        print(email)
                        messages.info(request, json.dumps(
                            {
                                'body': "Email zmieniający hasło został wysłany, sprawdz skrzynkę pocztową",
                                'title': "Email wysłany!"
                            }
                        ))
                        return HttpResponseRedirect(reverse_lazy("login"))
                    else:
                        messages.error(request, json.dumps(
                            {
                                'body': "Twoje konto jest nieaktywne! Aktywuj swoje konto i spróbuj ponownie!",
                                'title': "Najpierw aktywuj konto!"
                            }
                        ))
        else:
            messages.warning(request, json.dumps(
                {
                    'body': "Nie możemy znalezć konta należacego do tego adresu e-mail!",
                    'title': "Nie znaleziono konta!"
                }
            ))

        return render(request, "app/uzytkownik/forgotpassword.html", context)