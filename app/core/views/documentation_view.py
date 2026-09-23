from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import Http404

from app.core.documentation_catalog import MODULES, MODULE_META, MODULE_PURPOSES


def _module_with_details(module):
    purpose = MODULE_PURPOSES.get(module["slug"])
    sections = [section for section in module.get("sections", []) if section[0] != "Cel modułu"]
    if purpose:
        sections.insert(0, ("Cel modułu", [purpose]))
    return {**module, **MODULE_META.get(module["slug"], {}), "sections": sections}


class DocumentationIndexView(LoginRequiredMixin, TemplateView):
    template_name = "app/core/documentation_index.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documentation_modules"] = [_module_with_details(module) for module in MODULES]
        return context


class DocumentationModuleView(LoginRequiredMixin, TemplateView):
    template_name = "app/core/documentation_module.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = kwargs.get("slug")
        module = next((item for item in MODULES if item["slug"] == slug), None)
        if module is None:
            raise Http404("Nie znaleziono dokumentacji modułu.")
        context["module"] = _module_with_details(module)
        context["documentation_modules"] = [_module_with_details(item) for item in MODULES]
        return context


class ClientDocumentationView(LoginRequiredMixin, TemplateView):
    """Strona pomocy dla użytkowników panelu – moduł Klienci."""

    template_name = "app/core/documentation_clients.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documentation_modules"] = [
            {"name": "Strona główna", "anchor": "module-dashboard", "icon": "bi-speedometer2", "description": "Panel podsumowania firmy, aktywności, zadań, terminów oraz przypisanych realizacji.", "features": "KPI, ostatnia aktywność, dzisiejsze wydarzenia, serwisy i prace, zadania, alerty."},
            {"name": "Protokoły", "anchor": "module-protocols", "icon": "bi-file-earmark-text", "description": "Tworzenie i obsługa protokołów potwierdzających wykonanie usług lub prac.", "features": "Dane klienta, urządzenia, koszty, podpisy, statusy, fakturowanie i PDF."},
            {"name": "Oferty", "anchor": "module-offers", "icon": "bi-file-earmark-richtext", "description": "Przygotowywanie ofert pracy z wariantami i pozycjami kosztowymi.", "features": "Warianty, materiały, akcesoria, usługi, załączniki, wybór wariantu i przekazanie do realizacji."},
            {"name": "Prace", "anchor": "module-works", "icon": "bi-hammer", "description": "Planowanie oraz realizacja prac przypisanych do klientów i pracowników.", "features": "Terminy, pracownicy, statusy, zamówiony sprzęt, warianty, historia i podsumowania."},
            {"name": "Obsługa", "anchor": "module-contracts", "icon": "bi-gear-wide-connected", "description": "Zarządzanie umowami obsługi oraz urządzeniami objętymi stałą opieką.", "features": "Umowy, urządzenia, parametry, terminy, elementy i historia obsługi."},
            {"name": "Gwarancje", "anchor": "module-warranty", "icon": "bi-shield-check", "description": "Rejestrowanie i prowadzenie zgłoszeń gwarancyjnych do dostawców.", "features": "Klient, urządzenie, hurtownia, lokalizacja, opis usterki, zdjęcia, status i historia."},
            {"name": "Zadania", "anchor": "module-tasks", "icon": "bi-check2-square", "description": "Tworzenie zadań indywidualnych, grupowych i firmowych.", "features": "Termin, przypisanie osoby lub roli, status, oznaczenie po terminie i wykonanie."},
            {"name": "Pojazdy", "anchor": "module-vehicles", "icon": "bi-truck", "description": "Ewidencja pojazdów firmowych i ich zdarzeń.", "features": "Rejestracja, VIN, przebieg, OC, przeglądy, zdjęcia, zdarzenia i historia zmian."},
            {"name": "Sprzęt", "anchor": "module-tools", "icon": "bi-wrench-adjustable", "description": "Ewidencja sprzętu wykorzystywanego w firmie i realizacjach.", "features": "Dane sprzętu, zdjęcia, dokumenty, zdarzenia oraz historia zmian."},
            {"name": "Urządzenia", "anchor": "module-products", "icon": "bi-cpu", "description": "Katalog urządzeń klientów i urządzeń używanych w ofertach oraz serwisach.", "features": "Dane techniczne, numer seryjny, klient, lokalizacja i wyszukiwanie w formularzach."},
            {"name": "Magazyn", "anchor": "module-stock", "icon": "bi-box-seam", "description": "Kontrola stanów magazynowych i ruchów materiałowych.", "features": "Magazyny, przyjęcia, wydania, korekty, ilości, dokumenty i historia ruchów."},
            {"name": "RCP", "anchor": "module-time", "icon": "bi-clock-history", "description": "Rejestrowanie czasu pracy oraz obsługa wniosków o korektę wpisów.", "features": "Start i koniec pracy, zaległe godziny, akceptacja, status zatwierdzenia i raport PDF."},
            {"name": "Kalendarz", "anchor": "module-calendar", "icon": "bi-calendar3", "description": "Kalendarz serwisów, prac, urlopów i własnych wydarzeń użytkownika.", "features": "Widok dnia, tygodnia i miesiąca, wydarzenia całodniowe, planowanie i usuwanie własnych wpisów."},
            {"name": "Urlopy", "anchor": "module-leave", "icon": "bi-calendar-plus", "description": "Składanie, zatwierdzanie i rozliczanie wniosków urlopowych.", "features": "Rodzaje urlopów, limity, akceptacja, anulowanie zatwierdzonego urlopu i kalendarz."},
            {"name": "Pracownicy", "anchor": "module-employees", "icon": "bi-person-badge", "description": "Zarządzanie kontami pracowników, rolami, grupami, umowami i szkoleniami.", "features": "Konta, uprawnienia, role, grupy, 2FA, umowy, szkolenia i przekazanie własności firmy."},
            {"name": "Ustawienia firmy", "anchor": "module-settings", "icon": "bi-building-gear", "description": "Konfiguracja danych firmy i wartości używanych w całym systemie.", "features": "Dane firmy, adres, logo, RCP, rozliczenia, numeracja, serwisy i powiadomienia."},
            {"name": "Dokumenty", "anchor": "module-documents", "icon": "bi-folder", "description": "Porządkowanie dokumentów firmowych w folderach i powiązaniach z rekordami.", "features": "Foldery, pliki, zdjęcia, rozmiary plików, podgląd i kontrola limitu pamięci."},
            {"name": "Faktury", "anchor": "module-invoices", "icon": "bi-receipt", "description": "Rejestrowanie dokumentów sprzedażowych i fakturowanie protokołów.", "features": "Pozycje, kwoty netto/brutto, statusy, numeracja i powiązanie z protokołem."},
        ]
        return context
