#!/bin/sh
set -eu
if [ "${CERTBOT_RENEWED_LINEAGE:-}" = "/etc/letsencrypt/live/%PUBLIC_DOMAIN%" ] \
    || [ "${CERTBOT_RENEWED_LINEAGE:-}" = "/etc/letsencrypt/live/%PANEL_DOMAIN%" ]; then
    /usr/sbin/nginx -t
    /usr/bin/systemctl reload nginx
fi
