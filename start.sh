#!/usr/bin/env sh
# Docker / container entry: migrate + collectstatic + gunicorn.
# Optional one-shot after first boot:
#   docker compose exec web python manage.py seed_sites
#   docker compose exec web python manage.py createsuperuser
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn -c gunicorn.conf.py
