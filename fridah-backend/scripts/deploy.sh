#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "==> Pulling latest images"
$COMPOSE pull

echo "==> Building backend image"
$COMPOSE build backend celery_worker celery_beat

echo "==> Running migrations"
$COMPOSE run --rm backend python manage.py migrate

echo "==> Collecting static files"
$COMPOSE run --rm backend python manage.py collectstatic --noinput

echo "==> Restarting services"
$COMPOSE up -d --remove-orphans

echo "==> Pruning unused images"
docker image prune -f

echo "==> Waiting for backend to report healthy..."
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/healthz > /dev/null; then
    echo "==> Deploy complete - backend is healthy."
    exit 0
  fi
  sleep 2
done
echo "WARNING: backend didn't report healthy within 30s after restart - check 'docker compose logs backend'."
exit 1
