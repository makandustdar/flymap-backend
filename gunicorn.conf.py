"""Gunicorn config (WSGI).

Listens on PORT (default 8000) inside the container.
Docker Compose maps host 8786 → container 8000; host nginx proxies to :8786.
Also used as ParsPack «app config» when deploying there.
"""

import multiprocessing
import os

# Container-internal bind; external exposure is via compose ports (8786:8000).
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
