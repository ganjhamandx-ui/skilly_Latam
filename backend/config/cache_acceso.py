"""Configuracion de contadores de acceso; no abre conexiones ni imprime ubicaciones."""
import math
import re
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

LOCAL = 'django.core.cache.backends.locmem.LocMemCache'
REDIS_DJANGO = 'django.core.cache.backends.redis.RedisCache'
REDIS_ATOMICO = 'acceso.cache.RedisIntentosCache'


def ubicacion_redis_valida(value):
    if not isinstance(value, str) or not value or value.strip() != value or any(c in value for c in '\r\n\t;,'):
        return False
    try:
        url = urlsplit(value)
        return (url.scheme in ('redis', 'rediss') and bool(url.hostname)
                and url.port is not None and 1 <= url.port <= 65535
                and not url.query and not url.fragment and '?' not in value and '#' not in value
                and (url.path in ('', '/') or re.fullmatch(r'/[0-9]{1,3}', url.path) is not None))
    except ValueError:
        return False


def timeout_redis(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ImproperlyConfigured('El timeout de cache debe ser un numero entre 0.1 y 5 segundos.') from None
    if isinstance(value, bool) or not math.isfinite(result) or not 0.1 <= result <= 5:
        raise ImproperlyConfigured('El timeout de cache debe ser un numero entre 0.1 y 5 segundos.')
    return result


def configurar_cache_acceso(environment):
    backend = environment.get('ACCESO_CACHE_BACKEND', LOCAL)
    if backend == REDIS_DJANGO:
        # Mantener compatible la seleccion anterior, pero garantizar el comando
        # atomico de ventana; el subclass conserva el backend oficial Django.
        backend = REDIS_ATOMICO
    result = {
        'BACKEND': backend,
        'LOCATION': environment.get('ACCESO_CACHE_LOCATION', 'skilly-acceso-local'),
        'KEY_PREFIX': environment.get('ACCESO_CACHE_KEY_PREFIX', 'skilly-acceso'),
    }
    if not isinstance(result['KEY_PREFIX'], str) or re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', result['KEY_PREFIX']) is None:
        raise ImproperlyConfigured('El prefijo de cache de acceso debe ser corto y alfanumerico.')
    if backend == REDIS_ATOMICO:
        if not ubicacion_redis_valida(result['LOCATION']):
            raise ImproperlyConfigured('La cache Redis de acceso requiere una URL unica con puerto y sin parametros.')
        timeout = timeout_redis(environment.get('ACCESO_CACHE_TIMEOUT', '1'))
        result['OPTIONS'] = {'socket_connect_timeout': timeout, 'socket_timeout': timeout}
    return result
