#!/usr/bin/env bash
set -Eeuo pipefail

# Instalacja Dapexa na Ubuntu/Debian. Uruchom jako root z katalogu projektu:
#   sudo bash deploy/install.sh

if [[ "${EUID}" -ne 0 ]]; then
  echo "Uruchom skrypt jako root: sudo bash deploy/install.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
APP_USER="${APP_USER:-dapexa}"
APP_GROUP="${APP_GROUP:-www-data}"
ENV_FILE="${APP_DIR}/.env"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-dev build-essential nginx redis-server openssl

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_GROUP}" "${APP_DIR}/files" "${APP_DIR}/static"

if [[ ! -f "${ENV_FILE}" ]]; then
  DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$(openssl rand -hex 48)}"
  cat > "${ENV_FILE}" <<EOF
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:-dapexa.com,panel.dapexa.com}
DJANGO_CSRF_TRUSTED_ORIGINS=${DJANGO_CSRF_TRUSTED_ORIGINS:-https://dapexa.com,https://panel.dapexa.com}
PUBLIC_DOMAIN=${PUBLIC_DOMAIN:-dapexa.com}
PANEL_DOMAIN=${PANEL_DOMAIN:-panel.dapexa.com}
DOMAIN_URL=${DOMAIN_URL:-https://panel.dapexa.com}
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DB_NAME=${DB_NAME:-${APP_DIR}/db.sqlite3}
CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://127.0.0.1:6379/0}
CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://127.0.0.1:6379/0}
EOF
  chmod 600 "${ENV_FILE}"
  chown "${APP_USER}:${APP_GROUP}" "${ENV_FILE}"
  echo "Utworzono ${ENV_FILE}. Uzupełnij dane poczty, Stripe i pozostałych usług przed uruchomieniem produkcyjnym."
fi

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip wheel
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

set -a
source "${ENV_FILE}"
set +a
cd "${APP_DIR}"
"${APP_DIR}/.venv/bin/python" manage.py check
"${APP_DIR}/.venv/bin/python" manage.py migrate --noinput
"${APP_DIR}/.venv/bin/python" manage.py collectstatic --noinput

chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}/files" "${APP_DIR}/static"

for service in dapexa-gunicorn dapexa-celery dapexa-celery-beat; do
  sed -e "s|%APP_DIR%|${APP_DIR}|g" -e "s|%APP_USER%|${APP_USER}|g" \
    "${SCRIPT_DIR}/${service}.service" > "/etc/systemd/system/${service}.service"
done

sed "s|%APP_DIR%|${APP_DIR}|g" "${SCRIPT_DIR}/nginx-dapexa.conf" > /etc/nginx/sites-available/dapexa.conf
ln -sfn /etc/nginx/sites-available/dapexa.conf /etc/nginx/sites-enabled/dapexa.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable --now redis-server
systemctl enable --now dapexa-gunicorn dapexa-celery dapexa-celery-beat nginx
systemctl restart dapexa-gunicorn dapexa-celery dapexa-celery-beat nginx

echo
echo "Instalacja zakończona. Sprawdź: systemctl status dapexa-gunicorn"
echo "Przed ruchem produkcyjnym skonfiguruj DNS i certyfikat SSL (np. certbot)."
