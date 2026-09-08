"""
Django settings for the ARRISE Solutions Portal demo.

This is a stateless MVP: no database is configured or required. Business
data lives in ``mock_data`` (Python/JSON) and per-tab mutations live in the
browser's ``sessionStorage``. See ``docs/implementation-notes.md`` for the
full rationale.

DEVELOPMENT / DEMO ONLY. Not hardened for production use.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# SECURITY WARNING: this fallback key is public (it ships in the repo) and is
# only safe for a local, offline demo. Never reuse it outside this exercise.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "insecure-demo-key-arrise-solutions-portal-do-not-use-in-production",
)

DEBUG = _env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# No database: this demo is intentionally stateless on the server side.
DATABASES = {}

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "core",
    "dashboard",
    "solutions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "core.context_processors.brand",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# No contrib.auth / contrib.sessions installed, so the default password
# validators and auth backends are irrelevant here.
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CSRF: cookie-based, no session backend required.
CSRF_COOKIE_NAME = "arrise_csrftoken"
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG

# ---------------------------------------------------------------------------
# ARRISE Solutions Portal demo configuration
# ---------------------------------------------------------------------------

# Reference date the demo dataset is generated against. Overridable via env
# for reproducible screenshots/tests. Format: YYYY-MM-DD.
DEMO_REFERENCE_DATE = os.environ.get("DEMO_REFERENCE_DATE", "2026-09-08")

# Seed for the deterministic mock data generator.
DEMO_SEED = int(os.environ.get("DEMO_SEED", "20260908"))

# Maximum accepted size (bytes) / nesting depth for state payloads posted by
# the browser to local operation endpoints. The browser-held state is only a
# simulation aid and is never treated as a trust boundary.
DEMO_STATE_MAX_BYTES = 200_000
DEMO_STATE_MAX_DEPTH = 12
