"""Configuracion de contadores de acceso; no abre conexiones ni imprime ubicaciones."""
import math
import re
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

LOCAL = 'django.core.cache.backends.locmem.LocMemCache'
REDIS_DJANGO = 'django.core.cache.backends.redis.RedisCache'
REDIS_ATOMICO = 'acceso.cache.RedisIntentosCache'


def ubicacion_redis_valida(value):
    """Valida la forma de un único endpoint Redis, sin abrir conexiones.

    Args:
        value (str): URI redis/rediss con host y puerto explícito; puede contener
            credenciales y una base numérica de hasta tres dígitos en la ruta.

    Returns:
        bool: Si cumple la forma admitida, sin consulta, fragmento ni separadores
        de múltiples endpoints. No restringe el host a loopback ni verifica alcance.
    """

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
    """Convierte un timeout Redis a segundos dentro del rango admitido.

    Args:
        value (str | int | float): Valor numérico convertible, excluidos booleanos.

    Returns:
        float: Tiempo finito entre 0.1 y 5 segundos, incluidos los extremos.

    Raises:
        ImproperlyConfigured: Si no puede convertirse o queda fuera del rango.

    Example:
        >>> timeout_redis("1.5")
        1.5
    """

    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ImproperlyConfigured('El timeout de cache debe ser un numero entre 0.1 y 5 segundos.') from None
    if isinstance(value, bool) or not math.isfinite(result) or not 0.1 <= result <= 5:
        raise ImproperlyConfigured('El timeout de cache debe ser un numero entre 0.1 y 5 segundos.')
    return result


def configurar_cache_acceso(environment):
    """Construye la configuración de caché de intentos desde el entorno recibido.

    Args:
        environment (Mapping): Variables ACCESO_CACHE_BACKEND, LOCATION, KEY_PREFIX
            y TIMEOUT; no consulta el entorno global ni modifica el argumento.

    Returns:
        dict: Configuración Django con LocMem por defecto. RedisCache oficial se
        sustituye por RedisIntentosCache y recibe timeouts acotados. La selección
        de otros backends queda sujeta a las comprobaciones de acceso.checks.

    Raises:
        ImproperlyConfigured: Si el prefijo, la URL Redis o el timeout son inválidos.
            Los mensajes no incluyen el endpoint ni posibles credenciales.
    """

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
