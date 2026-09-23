# Aktualizacja Django 6 / Python 3.14

Stan weryfikacji: 2026-09-23. Interpreter `.venv/bin/python`: Python 3.14.4.

## Zmiany

- Zainstalowano Django 6.0.8 oraz zależności z `requirements.txt` w `.venv`.
- Dodano brakujące `django-allauth[socialaccount]`, `holidays`, `pdfkit`.
- Pozostawiono jeden sterownik PostgreSQL: `psycopg[binary]` 3.3.6.
- Zaktualizowano Pillow, Celery, Stripe, requests, Gunicorn i pozostałe używane pakiety.
- Przypięto Kombu 5.6.2 i redis 6.4.0, ponieważ dodatek Redis w Kombu wymaga redis < 6.5.
- Usunięto niewykorzystane zależności: django-environ, python-dotenv, django-filter,
  django-crispy-forms, crispy-bootstrap5, django-cors-headers, DRF, SimpleJWT,
  reportlab, xhtml2pdf, channels i channels-redis. Nie były aktywne w konfiguracji
  ani używane przez kod. Konfiguracja nadal korzysta z os.getenv i środowiska procesu.
- Naprawiono dwa wywołania format_html() bez argumentów w ToolAssignmentAdmin.
- Usunięto nieaktywne ustawienie USE_L10N.
- Przy aktualizacji stripe-python z 11.1.0 do 15.6.1 zachowano wersję API
  2024-09-30.acacia, domyślną dla starego SDK. Zachowuje to obecny format
  current_period_start/current_period_end oraz rozwijanie latest_invoice.payment_intent.
  Nie zmieniono reguł subskrypcji, płatności ani konfiguracji webhooków w Stripe.
- Dodano test faktycznego nagłówka Stripe-Version z atrapą transportu HTTP.
- Dodano BusinessManager.test_settings: SQLite w pamięci, tymczasowe media,
  poczta w pamięci i broker Celery w pamięci, bez produkcyjnych kluczy integracji.

## Wyniki wykonanych kontroli

| Kontrola | Wynik |
| --- | --- |
| python -m pip install -r requirements.txt | Sukces |
| python -m pip check | No broken requirements found |
| python manage.py check | System check identified no issues |
| python manage.py makemigrations --check --dry-run | No changes detected; ostrzeżenie o braku hasła PostgreSQL |
| Ten sam dry-run z --settings=BusinessManager.test_settings | No changes detected, bez ostrzeżenia bazy |
| Wszystkie 18 istniejących modułów tests.py, jawne etykiety | 28 testów, OK |
| Nowy StripeCompatibilityTests, osobny przebieg | 1 test, OK |
| git diff --check | Bez błędów |

Testy używały rzeczywistych migracji, ale wyłącznie w testowej bazie SQLite w pamięci.
Baza testowa została usunięta przez runner. Nie wykonano migracji na PostgreSQL,
nie utworzono nowych plików migracji i nie zmieniono modeli.

## Wszystkie problemy i ograniczenia znalezione podczas weryfikacji

1. Zwykłe `manage.py test` wykrywa 0 testów: katalogi aplikacji korzystają
   z pakietów przestrzeni nazw bez __init__.py. Testy uruchomiono przez jawne
   nazwy wszystkich modułów, a nie uznano pustego przebiegu za sukces.
2. Produkcyjny dry-run nie mógł odczytać historii migracji PostgreSQL:
   `fe_sendauth: no password supplied`. Bieżący proces nie ładuje automatycznie
   .env. Nie zmieniano tego zachowania ani konfiguracji bazy. Brak zmian modeli
   nie potwierdza zgodności historii migracji istniejącej bazy.
3. Brak wkhtmltopdf zarówno w PATH, jak i pod /usr/local/bin/wkhtmltopdf.
   PDF nie będzie działać bez tego programu; nie instalowano pakietów systemowych.
   pdfkit 1.0.0 instaluje się, ale generowania PDF nie zweryfikowano.
4. Testy SQLite nie potwierdzają zachowania PostgreSQL (w tym blokad wierszy).
   Przed wdrożeniem trzeba potwierdzić PostgreSQL >= 14 oraz sprawdzić testy
   i migracje na oddzielnej bazie PostgreSQL.
5. Nie uruchamiano produkcyjnego Celery ani beat. Nie wykonano testu komunikacji
   z rzeczywistym Redis, restartów workera/prefork ani testu produkcyjnego Gunicorna.
   Instalacja i zgodność zależności nie zastępują tych testów integracyjnych.
6. Testy Stripe korzystają z atrap HTTP/SDK. Potwierdzono zachowanie nagłówka
   starego API, ale nie wykonano płatności ani połączeń z kontem Stripe.
   Wersja webhooków musi odpowiadać formatowi obsługiwanemu przez aplikację.
   Migracja API Stripe do Basil/Dahlia wymaga oddzielnego dostosowania kodu.
7. Pierwszy test nowego nagłówka Stripe miał błąd w samej asercji (KeyError:
   headers), ponieważ SDK przekazuje headers pozycyjnie. Test poprawiono
   i ponownie uruchomiono z wynikiem OK.
8. Pierwsza konfiguracja testowa emitowała ResourceWarning przy automatycznym
   sprzątaniu TemporaryDirectory. Dodano jawne sprzątanie przez atexit;
   późniejszy przebieg z -Wd nie zgłosił tego ostrzeżenia.

Nie zmieniono Nginx, systemd ani skryptów wdrożeniowych. Nie restartowano usług.
Nie zmieniano logiki biznesowej; zakres zmian wykonawczych to zgodność frameworka
oraz zachowanie dotychczasowego kontraktu Stripe przy aktualizacji SDK.

## Ponowne uruchomienie wszystkich testów

Poniższe polecenie obejmuje także nowy test Stripe (łącznie 29 testów):

```bash
.venv/bin/python - <<'PYTEST'
from pathlib import Path
import subprocess
import sys

labels = [
    str(path.with_suffix('')).replace('/', '.')
    for path in sorted(Path('app').glob('*/tests.py'))
]
raise SystemExit(subprocess.call([
    sys.executable, '-Wd', 'manage.py', 'test', *labels,
    '--settings=BusinessManager.test_settings', '--noinput', '--verbosity=2',
]))
PYTEST
```

Kontrole bez stosowania migracji:

```bash
.venv/bin/python -m pip check
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```
