#!/usr/bin/env bash
# Run this ONCE, after your first `docker compose up -d --build` and after DNS for
# api.fridah.co.ke is already pointing at this server's IP (propagation can take a
# few minutes to a few hours - verify with `dig api.fridah.co.ke` before running this).
#
# What it does:
#   1. Swaps nginx to a plain-HTTP bootstrap config (the real nginx.conf can't start
#      yet - it references a cert file that doesn't exist on a brand-new server).
#   2. Asks Let's Encrypt for a real certificate via the HTTP-01 challenge.
#   3. Swaps nginx back to the real config (nginx.conf, with SSL) and reloads it.
#
# Safe to re-run if it fails partway (e.g. DNS wasn't ready yet) - just fix the
# problem and run it again.
set -euo pipefail
cd "$(dirname "$0")/.."

DOMAIN="${1:-api.fridah.co.ke}"
EMAIL="${2:-}"

if [ -z "$EMAIL" ]; then
  echo "Usage: $0 <domain> <email-for-Lets-Encrypt-renewal-notices>"
  echo "Example: $0 api.fridah.co.ke ops@fridah.co.ke"
  exit 1
fi

echo "==> Checking DNS for $DOMAIN..."
RESOLVED_IP=$(dig +short "$DOMAIN" | tail -n1)
SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)
if [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
  echo "WARNING: $DOMAIN resolves to '$RESOLVED_IP' but this server's public IP is '$SERVER_IP'."
  echo "Let's Encrypt will fail the HTTP-01 challenge until DNS actually points here."
  read -p "Continue anyway? [y/N] " -n 1 -r; echo
  [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

echo "==> Step 1/3: starting nginx with the plain-HTTP bootstrap config..."
cp nginx/nginx.conf nginx/nginx.conf.bak
cp nginx/nginx.bootstrap.conf nginx/nginx.conf
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx

echo "==> Step 2/3: requesting the certificate from Let's Encrypt..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm \
  -v certbot_webroot:/var/www/certbot -v certbot_certs:/etc/letsencrypt \
  certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email --non-interactive

echo "==> Step 3/3: switching nginx to the real HTTPS config..."
mv nginx/nginx.conf.bak nginx/nginx.conf
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx

echo ""
echo "Done. https://$DOMAIN should now be serving over SSL."
echo "The certbot service (already running via docker-compose.prod.yml) will renew it automatically."
