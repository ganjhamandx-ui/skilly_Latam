
"""Configura Django desde variables de entorno seguras y explícitas."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from .origenes import normalizar_origen_frontend, ORIGEN_FRONTEND_POR_DEFECTO
from .cache_acceso import configurar_cache_acceso


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# La configuración privada se lee desde la raíz del proyecto; nunca va al repositorio.
load_dotenv(PROJECT_ROOT / ".env")


def obtener_booleano(nombre, valor_por_defecto=False):
    """Lee una variable y reconoce como verdaderas las formas afirmativas admitidas."""

    valor = os.getenv(nombre)

    if valor is None:
        return valor_por_defecto

    return valor.strip().lower() in {
        "1",
        "true",
        "yes",
        "si",
        "sí",
        "on",
    }


def obtener_lista(nombre, valor_por_defecto=""):
    """Convierte una variable separada por comas en valores no vacíos."""

    valor = os.getenv(nombre, valor_por_defecto)

    return [
        elemento.strip()
        for elemento in valor.split(",")
        if elemento.strip()
    ]


# Impedir el arranque sin clave protege las sesiones y los tokens firmados.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "Falta DJANGO_SECRET_KEY en el archivo .env."
    )


DEBUG = obtener_booleano(
    "DJANGO_DEBUG",
    True,
)


ALLOWED_HOSTS = obtener_lista(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,127.0.0.2",
)


INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.sessions",

    "corsheaders",
    "rest_framework",
    "django_filters",

    "acceso",
    "profesionales",
    "marketplace",
    "solicitudes",
    "coordinacion",
    "reagendamientos",
    "pagos",
    "seguimiento",
    "retroalimentacion",
    "backoffice",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
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
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

if not POSTGRES_PASSWORD:
    raise RuntimeError(
        "Falta POSTGRES_PASSWORD en el archivo .env."
    )


POSTGRES_SCHEMA = os.getenv(
    "POSTGRES_SCHEMA",
    "skilly",
)


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv(
            "POSTGRES_DB",
            "skilly",
        ),
        "USER": os.getenv(
            "POSTGRES_USER",
            "skilly_app",
        ),
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": os.getenv(
            "POSTGRES_HOST",
            "127.0.0.1",
        ),
        "PORT": os.getenv(
            "POSTGRES_PORT",
            "5432",
        ),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "options": (
                f"-c search_path={POSTGRES_SCHEMA},public"
            ),
        },
    },
}


MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://127.0.0.1:27017",
)

MONGODB_DB = os.getenv(
    "MONGODB_DB",
    "skilly_documental",
)


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 15,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]


LANGUAGE_CODE = "es-cl"

TIME_ZONE = "America/Santiago"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


try:
    FRONTEND_ORIGIN = normalizar_origen_frontend(os.getenv(
        "FRONTEND_ORIGIN", ORIGEN_FRONTEND_POR_DEFECTO,
    ))
except ValueError:
    raise ImproperlyConfigured(
        "FRONTEND_ORIGIN debe ser un origen HTTP(S), sin credenciales ni ruta."
    ) from None


RECUPERACION_MINUTOS = int(
    os.getenv(
        "RECUPERACION_MINUTOS",
        "10",
    )
)


# Cache separada: LocMem es local a un proceso. Para varios trabajadores,
# configurar un backend atomico compartido (Redis o Memcached y su driver).
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "acceso_intentos": configurar_cache_acceso(os.environ),
}
ACCESO_CACHE_ALIAS = "acceso_intentos"
ACCESO_PROXIES_CONFIABLES = obtener_lista("ACCESO_PROXIES_CONFIABLES")


def limites_acceso(nombre, defecto):
    """Expone una lista de ventanas de limitación para el control de acceso."""

    return obtener_lista(nombre, defecto)


ACCESO_LIMITES = {
    "iniciar_sesion": {
        "ip": limites_acceso("ACCESO_LOGIN_IP", "30/60,300/3600"),
        "identidad_ip": limites_acceso("ACCESO_LOGIN_IDENTIDAD_IP", "8/60,40/3600"),
    },
    "recuperar": {
        "ip": limites_acceso("ACCESO_RECUPERAR_IP", "8/600,40/3600"),
        "identidad_ip": limites_acceso("ACCESO_RECUPERAR_IDENTIDAD_IP", "3/600,10/3600"),
    },
    "restablecer": {
        "ip": limites_acceso("ACCESO_RESTABLECER_IP", "20/300,100/3600"),
        "identidad_ip": limites_acceso("ACCESO_RESTABLECER_IDENTIDAD_IP", "8/300,20/3600"),
    },
}


CORS_ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
]

CORS_ALLOW_CREDENTIALS = True


CSRF_TRUSTED_ORIGINS = [
    FRONTEND_ORIGIN,
]


SESSION_ENGINE = "django.contrib.sessions.backends.db"

SESSION_COOKIE_NAME = "skilly_session"

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = "Lax"

SESSION_COOKIE_SECURE = not DEBUG


CSRF_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = not DEBUG


SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"


SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


if DEBUG:
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],

    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],

    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],

    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],

    "UNAUTHENTICATED_USER": None,
}
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "SKILLY <no-reply@skilly.local>"
