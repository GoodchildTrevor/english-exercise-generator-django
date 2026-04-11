#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting server..."

# Проверка переменных окружения
: "${DJANGO_SETTINGS_MODULE:?Environment variable DJANGO_SETTINGS_MODULE not set}"
: "${ALLOWED_HOSTS:?Environment variable ALLOWED_HOSTS not set}"

exec gunicorn eng_ex_gen.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --timeout 300 \
    --graceful-timeout 30 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info
    