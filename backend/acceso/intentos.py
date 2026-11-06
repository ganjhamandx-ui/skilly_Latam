"""Limites temporales de acceso, independientes de la existencia de una cuenta."""
import ipaddress
import math
import time

from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import APIException, Throttled
from rest_framework.throttling import BaseThrottle


class IntentosExcesivos(Throttled):
    default_detail = "Demasiados intentos. Espera antes de volver a intentarlo."
    extra_detail_singular = "Disponible de nuevo en {wait} segundo."
    extra_detail_plural = "Disponible de nuevo en {wait} segundos."


class ControlIntentosNoDisponible(APIException):
    status_code = 503
    default_detail = "El acceso no esta disponible temporalmente. Vuelve a intentarlo."
    default_code = "access_temporarily_unavailable"
    wait = 30


def _direccion_origen(request):
    """Solo un proxy explicitamente confiable puede aportar la cadena XFF."""
    remoto = request.META.get("REMOTE_ADDR", "")
    try:
        peer = ipaddress.ip_address(remoto)
    except ValueError:
        return "sin-direccion"

    redes = [ipaddress.ip_network(red) for red in settings.ACCESO_PROXIES_CONFIABLES]
    def confiable(ip):
        return any(ip.version == red.version and ip in red for red in redes)
    if not confiable(peer):
        return peer.compressed

    cabecera = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not cabecera or len(cabecera) > 2048:
        return peer.compressed
    cadena = cabecera.split(",")
    if len(cadena) > 20:
        return peer.compressed
    try:
        direcciones = [ipaddress.ip_address(valor.strip()) for valor in cadena]
    except ValueError:
        return peer.compressed
    # Recorrer desde el proxy mas cercano impide confiar en un prefijo inyectado.
    for direccion in reversed(direcciones):
        if not confiable(direccion):
            return direccion.compressed
    return direcciones[0].compressed


def _reglas(configuracion):
    reglas = []
    for valor in configuracion:
        try:
            numero, ventana = (int(parte) for parte in valor.split("/"))
        except (AttributeError, TypeError, ValueError):
            raise ImproperlyConfigured("Los limites de acceso deben usar intentos/segundos.") from None
        if not 1 <= numero <= 1000000 or not 1 <= ventana <= 86400:
            raise ImproperlyConfigured("Los limites de acceso deben ser positivos y acotados.")
        reglas.append((numero, ventana))
    if not reglas:
        raise ImproperlyConfigured("Debe existir al menos una ventana de proteccion de acceso.")
    return reglas


class LimiteIntentosAcceso(BaseThrottle):
    """Contadores atomicos en cache; la clave de ventana siempre deja de bloquear.

    LocMem es adecuado solo para un proceso local. En varios trabajadores debe
    configurarse Redis o Memcached para compartir contadores atomicos. Ni las IP,
    ni los correos ni los tokens se guardan en claro en las claves de cache.
    """

    def allow_request(self, request, view):
        self.espera = None
        alcance = view.alcance_intentos
        configuracion = settings.ACCESO_LIMITES[alcance]
        ip = _direccion_origen(request)
        campo = "token" if alcance == "restablecer" else "correo"
        valor = request.data.get(campo, "") if isinstance(request.data, dict) else ""
        identidad = str(valor).strip().casefold() if campo == "correo" else str(valor)
        ahora = time.time()
        try:
            cache = caches[settings.ACCESO_CACHE_ALIAS]
        except Exception:
            raise ControlIntentosNoDisponible() from None
        esperas = []
        for tipo, dato in (("ip", ip), ("identidad_ip", f"{ip}\0{identidad}")):
            huella = salted_hmac(
                f"skilly.acceso.intentos.{alcance}.{tipo}", dato, algorithm="sha256",
            ).hexdigest()
            for limite, ventana in _reglas(configuracion[tipo]):
                cubeta = math.floor(ahora / ventana)
                vence = (cubeta + 1) * ventana
                ttl = max(1, math.ceil(vence - ahora))
                clave = f"skilly:intentos:{alcance}:{tipo}:{huella}:{ventana}:{cubeta}"
                try:
                    if cache.add(clave, 1, timeout=ttl):
                        cuenta = 1
                    else:
                        try:
                            cuenta = cache.incr(clave)
                        except ValueError:
                            # Otra solicitud o el TTL pudieron expirar la clave.
                            if cache.add(clave, 1, timeout=ttl):
                                cuenta = 1
                            else:
                                cuenta = cache.incr(clave)
                        # Redis puede recrear una clave entre exists/incr; limitar
                        # su retencion. La cubeta absoluta evita un veto deslizante.
                        cache.touch(clave, timeout=ttl)
                except Exception:
                    # No registrar el error del backend: puede contener su URI.
                    raise ControlIntentosNoDisponible() from None
                if cuenta > limite:
                    esperas.append(vence - ahora)
        if esperas:
            self.espera = max(1, math.ceil(max(esperas)))
            return False
        return True

    def wait(self):
        return self.espera


class ProteccionIntentosMixin:
    throttle_classes = [LimiteIntentosAcceso]

    def throttled(self, request, wait):
        raise IntentosExcesivos(wait=wait)
