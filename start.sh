#!/usr/bin/env sh
# Entry helper for ParsPack / containers: migrate + collectstatic + gunicorn.
# If the panel only runs Gunicorn via app config, run migrate once from console:
#   python manage.py migrate --noinput
#   python manage.py seed_sites
#   python manage.py collectstatic --noinput
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn -c gunicorn.conf.py
