"""
Django settings for the CSRMS backend.

Everything that changes between machines (secret key, allowed hosts, CORS
origins, sensor thresholds) is read from the environment so the same code
runs in development and on a deployed server without edits. A small loader
below reads backend/.env when present, so developers do not have to export
variables by hand.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path):
    """Populate os.environ from a KEY=VALUE file without overriding existing values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file(BASE_DIR / ".env")


def env_str(name, default=""):
    return os.getenv(name, default)


def env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in env_str(name, default).split(",") if item.strip()]


def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


SECRET_KEY = env_str("DJANGO_SECRET_KEY", "development-only-key-do-not-use-in-production")
DEBUG = env_bool("DJANGO_DEBUG", True)

if not DEBUG and SECRET_KEY.startswith("development-only"):
    raise RuntimeError(
        "DJANGO_SECRET_KEY must be set to a strong value when DEBUG is false."
    )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    # CSRMS services
    "apps.core",
    "apps.accounts",
    "apps.requests",
    "apps.telemetry",
    "apps.dashboard",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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

# Database
# SQLite keeps local development simple; switch the engine to MySQL for
# deployment by setting the environment variables below.

DATABASES = {
    "default": {
        "ENGINE": env_str("DJANGO_DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": env_str("DJANGO_DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": env_str("DJANGO_DB_USER", ""),
        "PASSWORD": env_str("DJANGO_DB_PASSWORD", ""),
        "HOST": env_str("DJANGO_DB_HOST", ""),
        "PORT": env_str("DJANGO_DB_PORT", ""),
    }
}

# Custom user model carrying the STUDENT / STAFF / ADMIN role.

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalisation

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cross-origin requests from the React frontend.

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

# Django REST Framework configuration.
# JWT is the default authentication and every endpoint is denied by default;
# public views opt in explicitly with AllowAny.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_RATES": {
        "auth": "30/min",
    },
}

# JSON Web Token lifetimes. Access tokens are short lived; logout blacklists
# the refresh token so a stolen pair cannot be used indefinitely.

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# IoT auto-request thresholds. Devices post readings to the telemetry
# endpoints; when a rule below trips, CSRMS raises a SYSTEM request using the
# same workflow as any student report.

NETWORK_FAILURE_COUNT = env_int("CSRMS_NETWORK_FAILURE_COUNT", 3)
WATER_MOISTURE_THRESHOLD = env_float("CSRMS_WATER_MOISTURE_THRESHOLD", 60.0)
FIRE_SMOKE_THRESHOLD = env_float("CSRMS_FIRE_SMOKE_THRESHOLD", 40.0)
FIRE_TEMPERATURE_THRESHOLD = env_float("CSRMS_FIRE_TEMPERATURE_THRESHOLD", 50.0)
