"""
Django settings for config project — flymap paragliding forecast backend.

Configured for local development and ParsPack PaaS (WSGI + Gunicorn).
Docs: https://docs.parspack.com/paas/deploy/programming-languages/django/
"""

from pathlib import Path
import os

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
    return default


def env_bool(*names: str, default: bool = False) -> bool:
    for name in names:
        raw = os.environ.get(name)
        if raw is None or raw == "":
            continue
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return default


# ParsPack panel field is django_secret_key; also accept DJANGO_SECRET_KEY.
SECRET_KEY = env_first(
    "DJANGO_SECRET_KEY",
    "django_secret_key",
    default="django-insecure-%rsh21855vt4-las1i$9p4^#86rgk8fe(0q6_ck#c*b$@!j=_0",
)

# Production on PaaS: set DEBUG=False (or DJANGO_DEBUG=0) in Env Vars.
DEBUG = env_bool("DEBUG", "DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = [
    h.strip()
    for h in env_first(
        "DJANGO_ALLOWED_HOSTS",
        "ALLOWED_HOSTS",
        default="localhost,127.0.0.1,testserver",
    ).split(",")
    if h.strip()
]
if DEBUG and "*" not in ALLOWED_HOSTS:
    # Convenience for local; never rely on this in production.
    for host in ("localhost", "127.0.0.1", "testserver"):
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in env_first("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sites.apps.SitesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database: DATABASE_URL (Postgres on PaaS) or SQLite locally.
_database_url = env_first("DATABASE_URL", "database_url")
if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            ssl_require=env_bool("DATABASE_SSL_REQUIRE", default=False),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if DEBUG:
    _static_backend = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    _static_backend = "whitenoise.storage.CompressedStaticFilesStorage"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": _static_backend,
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Behind ParsPack / reverse proxy TLS termination.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Windy Point Forecast (production). If empty, node.windy.com detail is used.
WINDY_POINT_FORECAST_KEY = env_first("WINDY_POINT_FORECAST_KEY", default="")

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
