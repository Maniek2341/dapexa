# Instalacja Dapexa na serwerze

Skrypt jest przygotowany dla Ubuntu/Debian i zakłada, że PostgreSQL jest dostępny pod danymi z `.env` (lokalnie albo na osobnym serwerze).

```bash
sudo bash deploy/install.sh
sudo nano /ścieżka/do/projektu/.env
sudo systemctl restart dapexa-gunicorn dapexa-celery dapexa-celery-beat
```

Skrypt instaluje Python, Gunicorn, Nginx, Redis i zależności aplikacji, wykonuje migracje oraz `collectstatic`, a następnie tworzy usługi systemowe.

## DNS i HTTPS

Utwórz rekordy DNS typu `A`:

- `dapexa.com` → adres IP serwera
- `panel.dapexa.com` → adres IP serwera

Po wskazaniu DNS skonfiguruj certyfikat:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d dapexa.com -d panel.dapexa.com
```

Nie umieszczaj `.env` w repozytorium. Zawiera klucz Django, hasło bazy, dane poczty i klucze Stripe.
