# Moduł „Klienci”

Dokumentacja opisuje aktualną funkcjonalność modułu klientów w panelu BusinessManager: listę klientów, kartę szczegółów, dane kontaktowe, adresy, lokalizacje, notatki i historię aktywności.

## 1. Przeznaczenie modułu

Moduł służy do:

- prowadzenia kart klientów prywatnych i firm,
- przechowywania danych kontaktowych i NIP-u,
- przypisywania opiekuna klienta,
- obsługi adresu wysyłkowego i rozliczeniowego,
- definiowania wielu lokalizacji klienta,
- przechowywania osób kontaktowych,
- prowadzenia notatek wewnętrznych,
- śledzenia aktywności związanych z klientem,
- szybkiego przechodzenia do serwisów, prac i protokołów klienta.

## 2. Dostęp do modułu

Moduł wymaga zalogowania. Dane są zawsze filtrowane po firmie zalogowanego użytkownika (`company`), dlatego użytkownik nie powinien zobaczyć klientów innej firmy.

Lista i szczegóły klienta są dostępne po zalogowaniu. Operacje modyfikujące korzystają z uprawnień klienta. W interfejsie przyciski zarządzania są prezentowane na podstawie zmiennej `can_manage_clients`.

### Uprawnienia modułu

Uprawnienia są zdefiniowane w `Client.Meta.permissions` i mają nazwy:

| Kod uprawnienia | Znaczenie |
|---|---|
| `access_klient` | dostęp do modułu/listy klientów |
| `access_klient_add` | dodawanie klienta |
| `access_klient_edit` | edycja klienta |
| `access_klient_detail` | szczegóły klienta |
| `access_klient_delete` | trwałe usuwanie klienta |
| `access_klient_deactivate` | przenoszenie klienta do archiwum |
| `access_klient_archive` | lista klientów zarchiwizowanych |
| `access_klient_activate` | przywracanie klienta z archiwum |
| `access_client_note_pin` | przypinanie notatki |
| `access_client_note_delete` | usuwanie notatki |
| `access_contact_person_add` | dodawanie osoby kontaktowej |
| `access_location_add` | dodawanie lokalizacji |
| `access_location_edit` | edycja lokalizacji |
| `access_location_delete` | usuwanie lokalizacji |

> Implementacja `can_manage_clients()` traktuje posiadanie co najmniej jednego uprawnienia zarządzającego jako dostęp do operacji zarządzania. Jeśli potrzebna jest pełna separacja (np. osobne sprawdzanie `add`, `edit` i `delete` w każdym widoku), należy rozdzielić ten helper na osobne kontrole.

## 3. Adresy URL

| URL | Nazwa widoku | Funkcja |
|---|---|---|
| `/klienci/` | `klient` | lista aktywnych klientów i wyszukiwanie |
| `/klienci/add` | `klient_add` | dodanie klienta |
| `/klienci/edit/<id>/` | `klient_edit` | edycja klienta |
| `/klienci/detail/<id>/` | `klient_detail` | karta szczegółów |
| `/klienci/delete/<id>/` | `klient_delete` | potwierdzenie i usunięcie |
| `/klienci/deactivate/<id>/` | `klient_deactivate` | przeniesienie do archiwum |
| `/klienci/archive` | `klient_archive` | lista nieaktywnych klientów |
| `/klienci/activate/<id>/` | `klient_activate` | przywrócenie klienta |
| `/klienci/note/toggle-pin/<id>/` | `client_note_pin` | przypięcie/odpięcie notatki |
| `/klienci/note/delete/<id>/` | `client_note_delete` | usunięcie notatki |
| `/klienci/contact-person/add/<client_id>/` | `contact_person_add` | dodanie osoby kontaktowej |
| `/klienci/klient/<client_id>/lokalizacja/dodaj/` | `location_add` | dodanie lokalizacji |
| `/klienci/lokalizacja/<id>/edytuj/` | `location_edit` | edycja lokalizacji |
| `/klienci/lokalizacja/<id>/usun/` | `location_delete` | usunięcie lokalizacji |

Wszystkie operacje zapisu powinny być wykonywane metodą `POST` z tokenem CSRF.

## 4. Typy klienta

Klient może być zapisany jako:

- **Osoba prywatna** – wymagane jest imię i nazwisko; nazwa klienta jest automatycznie uzupełniana na podstawie tych pól, jeśli pozostawiono ją pustą.
- **Firma** – wymagana jest nazwa firmy i poprawny NIP składający się z 10 cyfr. Opcjonalnie można od razu podać pierwszą osobę kontaktową.

Wspólne dane kontaktowe to e-mail i telefon. Telefon jest walidowany pod kątem znaków i minimalnej długości.

## 5. Dodawanie i edycja klienta

Formularz `ClientForm` obsługuje jednocześnie dane klienta, adres wysyłkowy, opcjonalny adres rozliczeniowy oraz osobę kontaktową firmy.

### Dane podstawowe

- typ klienta,
- imię i nazwisko albo nazwa firmy,
- NIP,
- e-mail,
- telefon,
- opiekun klienta,
- notatka ogólna.

### Adres wysyłkowy

Ulica, numer lokalu, kod pocztowy, miejscowość i kraj są wymagane. Kod pocztowy musi mieć format `00-000`, a miejscowość musi zawierać minimum dwa znaki.

Adres jest geokodowany przez `GeocodingService`. Jeżeli nie uda się znaleźć adresu, formularz zwraca błąd przy miejscowości i nie zapisuje klienta.

### Adres rozliczeniowy

Domyślnie adres rozliczeniowy jest taki sam jak wysyłkowy. Po zaznaczeniu „Inny adres rozliczeniowy” wszystkie pola adresu rozliczeniowego stają się wymagane.

Podczas edycji formularz aktualizuje istniejące obiekty `Address`, a nie tworzy ich bez potrzeby.

## 6. Lista klientów

Lista pokazuje tylko aktywnych klientów. Dostępne jest wyszukiwanie po:

- nazwie,
- imieniu,
- nazwisku,
- adresie e-mail,
- numerze telefonu,
- NIP-ie.

Lista udostępnia także podsumowanie liczby klientów firmowych i prywatnych. Klientów nie usuwa się z listy przez zwykłe ukrycie — do tego służy archiwizacja albo trwałe usunięcie.

## 7. Archiwizacja i usuwanie

### Archiwizacja

Dezaktywacja ustawia `is_active=False` i przenosi klienta do archiwum. Powiązane osoby kontaktowe są dezaktywowane. Operacja zapisuje wpis w historii klienta.

Przywrócenie klienta ustawia `is_active=True` i również zapisuje aktywność.

### Trwałe usunięcie

Usunięcie:

1. usuwa osoby kontaktowe klienta,
2. usuwa klienta,
3. usuwa nieużywane adresy klienta.

Adres nie jest usuwany, jeśli nadal jest używany przez innego klienta. Przed usunięciem użytkownik przechodzi przez osobny ekran potwierdzenia.

## 8. Karta szczegółów klienta

Karta szczegółów agreguje dane klienta i powiązane rekordy:

- informacje podstawowe i kontaktowe,
- opiekuna klienta,
- adresy,
- osoby kontaktowe,
- lokalizacje,
- notatki,
- historię aktywności,
- serwisy klienta,
- prace klienta,
- protokoły klienta.

Serwisy, prace i protokoły są pobierane wyłącznie dla bieżącej firmy i danego klienta.

## 9. Osoby kontaktowe

Osobę kontaktową można dodać tylko do klienta typu **Firma**. Formularz obejmuje:

- imię,
- nazwisko,
- e-mail,
- telefon.

Osoba kontaktowa jest przypisana do klienta oraz firmy. Dodanie zapisuje aktywność „Dodano osobę kontaktową”.

## 10. Lokalizacje klienta

Klient może mieć wiele lokalizacji, np. oddział, magazyn lub miejsce realizacji usługi. Lokalizacja zawiera:

- nazwę,
- kod wewnętrzny,
- adres,
- osobę kontaktową,
- notatki,
- flagę lokalizacji domyślnej,
- status aktywności.

W obrębie jednego klienta może istnieć tylko jedna lokalizacja domyślna. Ustawienie nowej domyślnej automatycznie odznacza poprzednią.

Usunięcie lokalizacji usuwa również jej adres. Powiązane serwisy nie są usuwane: sygnał `post_delete` czyści lokalizację serwisu i próbuje ustawić jako adres serwisu adres wysyłkowy lub rozliczeniowy klienta.

## 11. Notatki i historia aktywności

`ClientNote` przechowuje treść, autora, datę utworzenia oraz informację o przypięciu. Notatki są sortowane tak, aby przypięte pojawiały się na początku.

`ClientActivity` jest historią zdarzeń klienta. Może zawierać m.in.:

- dodanie lub zmianę klienta,
- zmianę statusu,
- notatkę,
- rozmowę,
- e-mail,
- zadanie,
- serwis,
- ofertę,
- fakturę,
- plik,
- inne zdarzenie.

Aktywność wskazuje autora, czas, opis oraz opcjonalnie powiązaną aplikację, model i identyfikator rekordu. Usunięcie notatki zachowuje jej skróconą treść w historii.

## 12. Relacje z innymi modułami

| Moduł | Powiązanie |
|---|---|
| Serwisy | `ServiceOrder.client` oraz opcjonalna lokalizacja klienta |
| Prace | `WorkOrder.client` |
| Protokoły | `Protocol.client` |
| Użytkownicy | opiekun klienta (`Client.caretaker`) |
| Adresy | adres wysyłkowy, rozliczeniowy i adresy lokalizacji |

Dzięki temu karta klienta działa jako centrum informacji o wszystkich realizacjach dla danego klienta.

## 13. Najczęstsze procesy

### Dodanie firmy z adresem

1. Otwórz **Klienci → Dodaj klienta**.
2. Wybierz typ „Firma”.
3. Uzupełnij nazwę i 10-cyfrowy NIP.
4. Wpisz dane kontaktowe i adres wysyłkowy.
5. Opcjonalnie dodaj osobę kontaktową i osobny adres rozliczeniowy.
6. Zapisz formularz.

### Dodanie oddziału klienta

1. Otwórz szczegóły klienta.
2. Wybierz sekcję **Lokalizacje**.
3. Dodaj nazwę, adres i opcjonalną osobę kontaktową.
4. Zaznacz „Domyślna”, jeśli lokalizacja ma być używana domyślnie.

### Przeniesienie klienta do archiwum

1. Otwórz listę klientów.
2. Wybierz akcję archiwizacji.
3. Potwierdź operację.
4. Klient będzie dostępny w **Archiwum klientów** i będzie można go przywrócić.

## 14. Ważne zasady bezpieczeństwa i danych

- Każdy widok filtruje rekord po firmie użytkownika.
- Formularze POST wymagają tokena CSRF.
- Szczegóły dotyczą wyłącznie aktywnych klientów.
- Adresy są współdzielone tylko wtedy, gdy formularz ustawi adres rozliczeniowy taki sam jak wysyłkowy.
- Nie należy usuwać adresów ręcznie z poziomu bazy bez sprawdzenia relacji do klientów i lokalizacji.
- Historia aktywności powinna być tworzona przy operacjach biznesowych, aby karta klienta zachowała pełny ślad zmian.

## 15. Pliki implementacji

- Modele: `app/klient/models.py`
- Formularze i walidacja: `app/klient/forms.py`
- Uprawnienia pomocnicze: `app/klient/permissions.py`
- Adresy URL: `app/klient/urls.py`
- Widoki: `app/klient/views/`
- Szablony: `templates/app/klient/`
- Panel administracyjny: `app/klient/admin.py`
- Automatyczna obsługa usunięcia lokalizacji: `app/klient/signals.py`
