#!/usr/bin/env bash
# Install reviewed service files after dependencies, .env and migrations are ready.
set -Eeuo pipefail
if [[ ${EUID} -ne 0 ]]; then
    echo 'Run as root: sudo bash deploy/install.sh domain.example panel.domain.example' >&2
    exit 1
fi
if [[ $# -ne 2 ]]; then
    echo 'Supply the public domain and panel subdomain. See deploy/README.md.' >&2
    exit 1
fi
for domain in "$@"; do
    if [[ ! "$domain" =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]]; then
        echo 'Invalid server name.' >&2
        exit 1
    fi
done
cd /var/www/dapexa
for domain in "$1" "$2"; do
    if [[ ! -r "/etc/letsencrypt/live/$domain/fullchain.pem" || ! -r "/etc/letsencrypt/live/$domain/privkey.pem" ]]; then
        echo "A certificate for $domain is required before installing the HTTPS sites." >&2
        exit 1
    fi
done
runuser -u deploy -- .venv/bin/python manage.py check
runuser -u deploy -- .venv/bin/python manage.py migrate --check
backup_dir="/var/backups/dapexa/$(date -u +%Y%m%dT%H%M%SZ)-services"
install -d -m 0700 "$backup_dir"
for unit in dapexa dapexa-celery dapexa-celery-beat; do
    if [[ -f "/etc/systemd/system/$unit.service" ]]; then
        cp -a "/etc/systemd/system/$unit.service" "$backup_dir/"
    fi
    install -m 0644 "deploy/$unit.service" "/etc/systemd/system/$unit.service"
done
if [[ -f /etc/nginx/sites-available/dapexa ]]; then
    cp -a /etc/nginx/sites-available/dapexa "$backup_dir/nginx-dapexa"
fi
for config in /etc/nginx/conf.d/dapexa-log-format.conf /etc/letsencrypt/renewal-hooks/deploy/10-reload-nginx; do
    if [[ -f "$config" ]]; then
        cp -a "$config" "$backup_dir/$(basename "$config")"
    fi
done
sed -e "s/%PUBLIC_DOMAIN%/$1/g" -e "s/%PANEL_DOMAIN%/$2/g" deploy/nginx-dapexa.conf > /etc/nginx/sites-available/dapexa
install -m 0644 deploy/dapexa-log-format.conf /etc/nginx/conf.d/dapexa-log-format.conf
install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
sed -e "s|%PUBLIC_DOMAIN%|$1|g" -e "s|%PANEL_DOMAIN%|$2|g" deploy/letsencrypt-renew-hook.sh > /etc/letsencrypt/renewal-hooks/deploy/10-reload-nginx
chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/10-reload-nginx
if [[ ! -e /etc/nginx/sites-enabled/dapexa ]]; then
    ln -s /etc/nginx/sites-available/dapexa /etc/nginx/sites-enabled/dapexa
fi
# No reload is permitted unless validation succeeds.
nginx -t
systemctl daemon-reload
systemctl enable postgresql redis-server dapexa nginx
systemctl start postgresql redis-server
systemctl restart dapexa
systemctl is-active --quiet dapexa
curl --fail --silent --output /dev/null --retry 10 --retry-connrefused --retry-delay 1 \
    --unix-socket /run/dapexa/gunicorn.sock http://localhost/uzytkownik/login
systemctl reload nginx
# Beat is intentionally opt-in: review the retention task before enabling it.
echo 'Web service installed. Review Celery retention and integrations before enabling worker/beat.'
