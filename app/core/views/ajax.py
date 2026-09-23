# app/urzadzenie/views/ajax.py

from app.core.views.ajax_select import AjaxSelectView
from app.urzadzenie.models import Product
from app.klient.models import Client
from app.serwis.models import ServiceOrder


class ProductAjaxSelectView(AjaxSelectView):
    model = Product
    search_fields = ["name"]
    label_fields = ["name"]


class ClientAjaxSelectView(AjaxSelectView):
    model = Client
    search_fields = ["name", "first_name", "last_name", "email", "phone"]
    label_fields = ["name", "first_name", "last_name"]


class ServiceAjaxSelectView(AjaxSelectView):
    model = ServiceOrder
    search_fields = ["number", "title"]
    label_fields = ["number", "title"]