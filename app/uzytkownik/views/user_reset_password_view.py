import json

from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.encoding import  force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View

from app.uzytkownik.forms import SettPasswordForm
from app.core.models import PanelUser


class UserResetPasswordView(View):
    reset_token = PasswordResetTokenGenerator()

    def get(self, request, uidb64, token):

        uid = force_str(urlsafe_base64_decode(uidb64))
        user = PanelUser.objects.get(pk=uid)
        if self.reset_token.check_token(user, token):
            context = {
                'reset_form': SettPasswordForm(user),
                'uid': uidb64,
                'token': token
            }
            return render(request, 'app/uzytkownik/reset_password.html', context)
        else:
            messages.error(request, json.dumps(
                {
                    'body': "Link do zmiany hasła wygasł. Skontaktuj sie ze wsparciem klienta, aby zmienić hasło.",
                    'title': "Nie udało sie zmienić hasła!"
                }
            ))
            return HttpResponseRedirect(reverse_lazy("dashboard"))

    def post(self, request, uidb64, token):
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('dashboard'))

        uid = force_str(urlsafe_base64_decode(uidb64))
        user = PanelUser.objects.get(pk=uid)
        reset_form = SettPasswordForm(data=request.POST, user=user)

        context = {
            'reset_form': reset_form,
            'uid': uidb64,
            'token': token
        }

        if self.reset_token.check_token(user, token):
            if reset_form.is_valid():
                reset_form.save()
                messages.info(request, json.dumps(
                    {
                        'body': "Twoje hasło zostało pomyślnie zmienione. Teraz mozesz się zalogować używając "
                                  "nowego hasła.",
                        'title': "Hasło zmienione!"
                    }
                ))
                return HttpResponseRedirect(reverse_lazy("login"))
            else:
                for header, msg_list in reset_form.errors.as_data().items():
                    for error_msg in msg_list:
                        messages.error(request, json.dumps(
                            {
                                'body': str(error_msg.message).capitalize(),
                                'title': "Błąd"
                            }
                        ))
                return render(request, "app/uzytkownik/reset_password.html", context)
        else:
            messages.error(request, json.dumps(
                {
                    'body': "Link do zmiany hasła wygasł. Skontaktuj sie ze wsparciem klienta, aby zmienić hasło.",
                    'title': "Nie udało sie zmienić hasła!"
                }
            ))
            return HttpResponseRedirect(reverse_lazy("dashboard"))