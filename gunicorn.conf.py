"""Gunicorn config for ParsPack PaaS (WSGI).

Panel «app config» path: gunicorn.conf.py
Default listen port must be 8000 — see:
https://docs.parspack.com/paas/deploy/programming-languages/django/
"""

import multiprocessing
import os

# ParsPack routes traffic to this port; do not change unless panel port matches.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Keep workers modest for small PaaS plans; override with WEB_CONCURRENCY.
workers = int(os.environ.get("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count())))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))
worker_class = "gthread"

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

preload_app = True
wsgi_app = "config.wsgi:application"
