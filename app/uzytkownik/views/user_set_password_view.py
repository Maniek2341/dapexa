import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views import View




class UserSetPasswordView(View):

    def get(self, request):
        context = {

        }
        return render(request, 'app/uzytkownik/set_password.html', context)


    def post(self, request):
        context = {

        }

        return render(request, "app/uzytkownik/set_password.html", context)

