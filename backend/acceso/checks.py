"""Validacion local de limites; nunca abre conexiones al backend de cache."""
import ipaddress
from importlib.util import find_spec

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
from django.core.exceptions import ImproperlyConfigured

from .intentos import _reglas
from config.cache_acceso import LOCAL, REDIS_ATOMICO, timeout_redis, ubicacion_redis_valida


ATOMICO_COMPARTIDO = {
    REDIS_ATOMICO,
    "django.core.cache.backends.memcached.PyMemcacheCache",
    "django.core.cache.backends.memcached.PyLibMCCache",
}


@register(Tags.security)
def configuracion_limites_acceso(app_configs, **kwargs):
    """Valida que todas las ventanas de limitación tengan formato y valores seguros."""

    errores = []
    try:
        for alcance in ("iniciar_sesion", "recuperar", "restablecer"):
            for tipo in ("ip", "identidad_ip"):
                _reglas(settings.ACCESO_LIMITES[alcance][tipo])
        for red in settings.ACCESO_PROXIES_CONFIABLES:
            ipaddress.ip_network(red)
    except (ImproperlyConfigured, KeyError, TypeError, ValueError):
        errores.append(Error(
            "Configuracion invalida de limites o proxies de acceso.",
            hint="Usar limites positivos intentos/segundos y proxies en formato CIDR.",
            id="acceso.E001",
        ))
    configuracion = settings.CACHES.get(settings.ACCESO_CACHE_ALIAS, {})
    if configuracion.get("BACKEND") not in ATOMICO_COMPARTIDO | {LOCAL}:
        errores.append(Error(
            "El control de acceso necesita un backend con add/incr atomicos.",
            hint="Usar LocMem localmente, RedisIntentosCache o Memcached compartido.",
            id="acceso.E002",
        ))
    if configuracion.get('BACKEND') == REDIS_ATOMICO:
        try:
            opciones = configuracion.get('OPTIONS', {})
            if not ubicacion_redis_valida(configuracion.get('LOCATION')):
                raise ImproperlyConfigured('Endpoint invalido.')
            for nombre in ('socket_timeout', 'socket_connect_timeout'):
                timeout_redis(opciones.get(nombre, 1))
        except (ImproperlyConfigured, TypeError, AttributeError):
            errores.append(Error(
                'Configuracion invalida del contador Redis de acceso.',
                hint='Usar un endpoint unico y timeouts acotados; no incluir opciones en la URL.',
                id='acceso.E003',
            ))
        if find_spec('redis') is None:
            errores.append(Error(
                'Falta el driver del backend Redis de acceso.',
                hint='Instalar las dependencias declaradas antes de habilitar Redis.',
                id='acceso.E004',
            ))
    return errores


@register(Tags.security, deploy=True)
def cache_acceso_compartida(app_configs, **kwargs):
    """Advierte cuando varios procesos usarían un contador de intentos no compartido."""

    configuracion = settings.CACHES.get(settings.ACCESO_CACHE_ALIAS, {})
    if configuracion.get("BACKEND") not in ATOMICO_COMPARTIDO:
        return [Warning(
            "Los limites de acceso no tienen un backend compartido validado.",
            hint="Configurar Redis o Memcached compartido y su driver antes de varios trabajadores.",
            id="acceso.W001",
        )]
    return []
