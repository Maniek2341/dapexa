# Dapexa — produkcja na /var/www/dapexa

Użytkownik: `deploy`, grupa usług: `www-data`. Python 3.14, Django 6.0.
WSGI: `BusinessManager.wsgi:application`; Celery: `BusinessManager`.

## Konfiguracja

`BusinessManager/settings.py` ładuje `.env` przez django-environ, bez nadpisywania
zmiennych procesu. Systemd używa tego samego pliku jako `EnvironmentFile`.
Plik musi należeć do `deploy`, mieć tryb 0600 i pozostać poza Git.
Przed zmianą istniejącej konfiguracji wykonaj kopię w katalogu dostępnym tylko root.
Nie wyświetlaj zawartości `.env` w logach ani nie używaj `set -x`.

Zmienne odczytywane przez aplikację:

- `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` (silny klucz, minimum 50 znaków).
- `PUBLIC_DOMAIN`, `PANEL_DOMAIN`, `DOMAIN_URL`.
- `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` (listy rozdzielone przecinkami).
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`.
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.
- `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
- `STRIPE_PRICE_START_MONTHLY`, `STRIPE_PRICE_START_YEARLY`,
  `STRIPE_PRICE_STANDARD_MONTHLY`, `STRIPE_PRICE_STANDARD_YEARLY`,
  `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_YEARLY`.
- `STRIPE_AMOUNT_*` values in the currency's smallest unit; Price IDs and
  amounts must match each other and use the same Stripe mode as the API key.
- `EMAIL_USE_SSL`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`.
- `ORS_API_KEY`, `GOOGLE_API_KEY`.

`DEBUG` i `SECRET_KEY` nie są nazwami zmiennych środowiskowych tego projektu.
Brak zewnętrznych sekretów nie blokuje `manage.py check`, ale integracje wymagają
ich uzupełnienia przed użyciem. Żądania API Stripe używają wersji
`2024-09-30.acacia`; sześć Price ID i kwot podanych w `.env` musi odpowiadać
cenom na koncie Stripe w tym samym trybie.
Konfiguracja kont Google/Facebook w allauth wymaga osobnego uzupełnienia.

## Kontrole i migracje

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py migrate --plan
# Dopiero po przeglądzie planu i backupie istniejącej bazy:
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py migrate --check
.venv/bin/python manage.py collectstatic --noinput
```

Testy działają w SQLite in-memory, z tymczasowymi media, lokalnym backendem poczty
i bez produkcyjnych kluczy integracji. Jawne wskazanie modułów jest konieczne,
ponieważ standardowe discovery w tym repozytorium pomija istniejące testy:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import subprocess
labels = ['.'.join(p.with_suffix('').parts) for p in Path('app').glob('*/test*.py')]
raise SystemExit(subprocess.call(['.venv/bin/python', 'manage.py', 'test', *labels,
                                 '--settings=BusinessManager.test_settings', '--noinput']))
PY
```

## Pliki i PDF

STATIC_ROOT: `/var/www/dapexa/static`, URL `/static/`. Zbierane są wyłącznie zasoby
`templates/assets` i static z zainstalowanych aplikacji, nie szablony widoków.
MEDIA_ROOT: `/var/www/dapexa/files`, URL `/files/` zawsze obsługuje Django.
Django sprawdza sesję, firmę, uprawnienie modułu oraz pakiet i zwraca
`X-Accel-Redirect: /_protected_media/...`. Nginx ma dla tego prefiksu `internal`.
Nie dodawaj publicznego aliasu do `files`. Nowe FileField wymagają jawnej polityki
w `app/core/private_media.py`; test sprawdza kompletność tej listy.

Katalogi danych należą do `deploy:www-data`, tryb 2750; pliki 0640.
Nginx musi mieć odczyt static i media, ale nie `.env`.

PDF używa `/usr/local/bin/wkhtmltopdf` (0.12.6.1 z patched Qt).
Na Ubuntu 26 nie ma pakietu w repozytorium. Na tym VPS zainstalowano oficjalny
pakiet `wkhtmltox_0.12.6.1-3.jammy_amd64.deb` z GitHub wkhtmltopdf/packaging,
po sprawdzeniu zależności. Jest to stary renderer; migracja do utrzymywanego
silnika PDF jest osobnym zadaniem. Nie renderuj w nim dowolnego HTML użytkownika.
Logo jest osadzane jako PNG data URI, JavaScript i lokalny odczyt plików są wyłączone.

## Usługi

Po potwierdzeniu domen i przygotowaniu powyższych kroków:

```bash
sudo bash deploy/install.sh domena-glowna subdomena-panelu
```

Wymagane są osobne certyfikaty Let's Encrypt dla obu hostów. Domena główna
serwuje stronę `deploy/landing/index.html`, a panel Django działa wyłącznie
pod subdomeną panelu. Skrypt tworzy backup nadpisywanych konfiguracji. Nie instaluje zależności,
nie wykonuje migracji i nie uruchamia Beat. Nie usuwa innych witryn Nginx.
Gunicorn: `/run/dapexa/gunicorn.sock`, utworzony przez usługę `dapexa.service`
z `RuntimeDirectory=dapexa`. Usługi działają jako deploy, nie root.

```bash
sudo systemctl status dapexa postgresql redis-server nginx
sudo nginx -t && sudo systemctl reload nginx
sudo journalctl -u dapexa -n 50 --no-pager
```

Worker i Beat mają oddzielne jednostki. Redis nasłuchuje lokalnie, ma protected-mode
i trwałość AOF; broker używa DB 0, wyniki DB 1. Harmonogram Beat jest w
`/var/lib/dapexa-celery-beat/schedule`, poza repozytorium.

**Nie włączaj Beat przed decyzją dotyczącą retencji:** aktualne zadanie
`process_subscription_lifecycle` przypomina o anulowaniu subskrypcji oraz usuwa
firmy i ich pliki po okresie retencji. Nie uruchamiaj go ręcznie jako testu.
Do testu workera użyj `.venv/bin/celery -A BusinessManager inspect ping`.

## HTTPS i uruchomienie publiczne

Szablon Nginx wymaga wcześniej wydanego certyfikatu Let’s Encrypt pod
`/etc/letsencrypt/live/<pierwsza-domena>/`. Przekierowuje HTTP do HTTPS,
ustawia `X-Forwarded-Proto` od połączenia i włącza HSTS. Access logi celowo
nie zawierają ścieżek ani query stringów, żeby nie zapisywać tokenów z URL.
W tym VPS certyfikat `dapexa.com` odnawia się przez DNS-01 OVH, a chronione dane
OVH są w `/etc/letsencrypt/ovh.ini` (root, 0600). Hook odnowienia wykonuje
`nginx -t` przed reloadem. Użytkownik i hasło e-mail, Stripe, ORS i Google
pozostają wymagane do uruchomienia tych integracji; nie są generowane lokalnie.

Skrypt instalacyjny najpierw sprawdza certyfikat, wykonuje `nginx -t` przed
reloadem, a następnie uruchamia usługi. Dla tego hosta produkcyjna konfiguracja
Nginx nasłuchuje po IPv4. Nie włączaj Celery Beat dopóki właściciel aplikacji
nie zaakceptuje skutków zadania retencji.

Backup konfiguracji nie zastępuje regularnego backupu PostgreSQL i prywatnych plików.
Przed przyjęciem danych produkcyjnych ustal miejsce kopii poza VPS i przetestuj odtworzenie.
Po zakończeniu prac usuń tymczasową regułę sudo `/etc/sudoers.d/99-deploy-session`.
