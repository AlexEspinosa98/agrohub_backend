import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key-change-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

# Prefijo con el que nginx monta esta app (ej. /api/agrohub) — hace que Django
# genere URLs (reverse(), admin, drf-spectacular) con el prefijo correcto.
FORCE_SCRIPT_NAME = os.getenv("DJANGO_FORCE_SCRIPT_NAME") or None

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "apps.user_activity",
    "apps.data_characterization",
    "apps.hub_cgsm",
    "apps.encuesta_nutricional",
    "apps.riego_iot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.user_activity.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — MySQL. Same connection style as the previous FastAPI backend
# (single primary DB shared by every app), pointed at the new deployment host.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "NAME": os.getenv("DB_NAME", "agrohub"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", "password"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    },
    # apps.riego_iot (gateways de riego IoT) vive en Postgres, no MySQL — es la misma base
    # 'agrohub_mqtt' que ya llena el daemon de ingesta del repo mqtt_agrohub (proceso Python
    # aparte, corriendo 24/7 en este servidor, suscrito por MQTT a los gateways). Sus modelos son
    # managed=False (ver apps/riego_iot/models.py) y config/db_routers.py enruta todo lo de esa
    # app aquí — nunca se corre `migrate` sobre esta base, las tablas ya existen.
    "mqtt": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.getenv("MQTT_DB_HOST", "localhost"),
        "PORT": os.getenv("MQTT_DB_PORT", "5434"),
        "NAME": os.getenv("MQTT_DB_NAME", "agrohub_mqtt"),
        "USER": os.getenv("MQTT_DB_USER", "agrohub_mqtt"),
        "PASSWORD": os.getenv("MQTT_DB_PASSWORD", ""),
    },
}
DATABASE_ROUTERS = ["config.db_routers.RiegoIotRouter"]

AUTH_PASSWORD_VALIDATORS = []

# API auth does not use django.contrib.auth's User model at all — see
# apps.user_activity.authentication. contrib.auth/admin stay installed only
# so the Django admin site works for support/debugging.

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = os.getenv("DJANGO_STATIC_URL", "static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = os.getenv("DJANGO_MEDIA_URL", "media/")
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# ---------------------------------------------------------------------------
# CORS — open, mirrors the previous FastAPI CORSMiddleware(allow_origins=["*"]).
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "config.exceptions.agrohub_exception_handler",
    "DEFAULT_PAGINATION_CLASS": None,
    "UNAUTHENTICATED_USER": "apps.user_activity.authentication.AnonymousUser",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ---------------------------------------------------------------------------
# drf-spectacular — schema OpenAPI para /docs/. Varias vistas son @api_view planas (no
# ViewSets/generics), así que el autodetect no siempre infiere bien: se van agregando
# @extend_schema explícitos por vista para que el body/response queden completos.
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "AgroHub API",
    "DESCRIPTION": (
        "API del backend AgroHub (Universidad del Magdalena): encuestas de caracterización, "
        "HUB CGSM, actividad de usuarios/autenticación, encuesta nutricional y administración "
        "de gateways de riego IoT."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20MB, for survey photo uploads

# ---------------------------------------------------------------------------
# Application env vars (unchanged names from the FastAPI .env)
# ---------------------------------------------------------------------------
SUPERADMIN_TOKEN = os.getenv("SUPERADMIN_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

MAIL_HOST = os.getenv("MAIL_HOST")
MAIL_PORT = int(os.getenv("MAIL_PORT", "465"))
MAIL_USER = os.getenv("MAIL_USER")
MAIL_P = os.getenv("MAIL_P")
MAIL_SECURE = os.getenv("MAIL_SECURE", "true").lower() == "true"
MAIL_FROM = os.getenv("MAIL_FROM", MAIL_USER)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "AgroHub")

ENABLE_TRANSCRIBE = os.getenv("ENABLE_TRANSCRIBE", "false").lower() == "true"
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "tiny")

# ---------------------------------------------------------------------------
# apps.riego_iot — administración de gateways AgroHub (riego IoT) y credenciales de Mosquitto.
# Ver apps/riego_iot/mosquitto_admin.py y el README de mqtt_agrohub, sección "Permisos que
# necesita" (grupo mosquitto-admin + regla de sudoers para "systemctl reload mosquitto").
# ---------------------------------------------------------------------------
RIEGO_IOT_API_KEY = os.getenv("RIEGO_IOT_API_KEY")
RIEGO_IOT_MOSQUITTO_PASSWD_FILE = os.getenv("RIEGO_IOT_MOSQUITTO_PASSWD_FILE", "/etc/mosquitto/passwd")
RIEGO_IOT_MOSQUITTO_ACL_FILE = os.getenv("RIEGO_IOT_MOSQUITTO_ACL_FILE", "/etc/mosquitto/acl.conf")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
