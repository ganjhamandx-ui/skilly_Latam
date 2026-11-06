"""Validacion local de limites; nunca abre conexiones al backend de cache."""
import ipaddress

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
from django.core.exceptions import ImproperlyConfigured

from .intentos import _reglas


ATOMICO_COMPARTIDO = {
    "django.core.cache.backends.redis.RedisCache",
    "django.core.cache.backends.memcached.PyMemcacheCache",
    "django.core.cache.backends.memcached.PyLibMCCache",
}
LOCAL = "django.core.cache.backends.locmem.LocMemCache"


@register(Tags.security)
def configuracion_limites_acceso(app_configs, **kwargs):
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
            hint="Usar LocMem solo localmente, o Redis/Memcached compartido.",
            id="acceso.E002",
        ))
    return errores


@register(Tags.security, deploy=True)
def cache_acceso_compartida(app_configs, **kwargs):
    configuracion = settings.CACHES.get(settings.ACCESO_CACHE_ALIAS, {})
    if configuracion.get("BACKEND") not in ATOMICO_COMPARTIDO:
        return [Warning(
            "Los limites de acceso usan memoria local y no se comparten entre procesos.",
            hint="Configurar Redis o Memcached compartido y su driver antes de varios trabajadores.",
            id="acceso.W001",
        )]
    return []
