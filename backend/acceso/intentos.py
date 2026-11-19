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

from .cache import RedisIntentosCache


class IntentosExcesivos(Throttled):
    """Representa un bloqueo temporal con un mensaje de espera no ambiguo."""

    default_detail = "Demasiados intentos. Espera antes de volver a intentarlo."
    extra_detail_singular = "Disponible de nuevo en {wait} segundo."
    extra_detail_plural = "Disponible de nuevo en {wait} segundos."


class ControlIntentosNoDisponible(APIException):
    """Cierra el acceso de forma segura cuando el contador compartido no responde."""

    status_code = 503
    default_detail = "El acceso no esta disponible temporalmente. Vuelve a intentarlo."
    default_code = "access_temporarily_unavailable"
    wait = 30


def _direccion_origen(request):
    """Resuelve el origen sin confiar en cabeceras de proxies no autorizados.

    Args:
        request (Request): Petición con ``REMOTE_ADDR`` y, opcionalmente, XFF.

    Returns:
        str: IP normalizada, o ``sin-direccion`` si el par remoto es inválido.
        Desde un proxy confiable recorre XFF de derecha a izquierda y elige el
        primer salto no confiable. Una cadena inválida, mayor de 2048 caracteres
        o con más de 20 saltos se descarta a favor de la IP del par remoto.

    Raises:
        ValueError: Si una red de ``ACCESO_PROXIES_CONFIABLES`` es inválida.
    """
    remoto = request.META.get("REMOTE_ADDR", "")
    try:
        peer = ipaddress.ip_address(remoto)
    except ValueError:
        return "sin-direccion"

    redes = [ipaddress.ip_network(red) for red in settings.ACCESO_PROXIES_CONFIABLES]
    def confiable(ip):
        """Indica si la dirección pertenece a una red autorizada de su versión IP."""
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
    """Convierte reglas ``intentos/segundos`` en pares numéricos validados.

    Args:
        configuracion (Iterable[str]): Límites entre 1 y 1000000 intentos y
            ventanas entre 1 y 86400 segundos; debe contener al menos una regla.

    Returns:
        list[tuple[int, int]]: Límites y duraciones en el orden de entrada.

    Raises:
        ImproperlyConfigured: Si una regla está mal formada, fuera de rango
            o la colección está vacía.

    Example:
        >>> _reglas(["5/60"])
        [(5, 60)]
    """

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
        """Cuenta el intento por IP y por identidad/IP en todas sus ventanas.

        Args:
            request (Request): Petición con correo, o token al restablecer acceso.
            view (APIView): Vista con ``alcance_intentos`` configurado en settings.

        Returns:
            bool: Si ninguna ventana supera su límite. En caso de rechazo guarda
            en ``espera`` el mayor tiempo restante, redondeado hacia arriba.
            Todos los intentos, incluidos los rechazados, incrementan contadores
            sin desplazar el vencimiento absoluto de la ventana.

        Raises:
            ControlIntentosNoDisponible: Si la caché falla o devuelve contadores
                inválidos; DRF comunica indisponibilidad con HTTP 503.
            ImproperlyConfigured: Si alguna regla de límites no es válida.
            KeyError: Si faltan el alcance o sus dimensiones en la configuración.
        """
        self.espera = None
        alcance = view.alcance_intentos
        configuracion = settings.ACCESO_LIMITES[alcance]
        ip = _direccion_origen(request)
        campo = "token" if alcance == "restablecer" else "correo"
        valor = request.data.get(campo, "") if isinstance(request.data, dict) else ""
        identidad = str(valor).strip().casefold() if campo == "correo" else str(valor)
        try:
            cache = caches[settings.ACCESO_CACHE_ALIAS]
        except Exception:
            raise ControlIntentosNoDisponible() from None
        reglas_cache = []
        for tipo, dato in (("ip", ip), ("identidad_ip", f"{ip}\0{identidad}")):
            huella = salted_hmac(
                f"skilly.acceso.intentos.{alcance}.{tipo}", dato, algorithm="sha256",
            ).hexdigest()
            for limite, ventana in _reglas(configuracion[tipo]):
                clave_base = f"skilly:intentos:{alcance}:{tipo}:{huella}:{ventana}"
                reglas_cache.append((clave_base, limite, ventana))
        esperas = []
        if isinstance(cache, RedisIntentosCache):
            try:
                resultados = cache.incrementar_ventanas([
                    (clave, ventana) for clave, _limite, ventana in reglas_cache
                ])
                for (_clave, limite, _ventana), (cuenta, espera) in zip(reglas_cache, resultados, strict=True):
                    if cuenta > limite:
                        esperas.append(espera)
            except Exception:
                raise ControlIntentosNoDisponible() from None
        else:
            ahora = time.time()
            for clave_base, limite, ventana in reglas_cache:
                cubeta = math.floor(ahora / ventana)
                vence = (cubeta + 1) * ventana
                ttl = max(1, math.ceil(vence - ahora))
                clave = f"{clave_base}:{cubeta}"
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
        """Devuelve los segundos de espera calculados, o ``None`` si se admitió.

        Se consulta después de ``allow_request`` según el ciclo de throttling de DRF.
        """
        return self.espera


class ProteccionIntentosMixin:
    """Aplica el limitador común a vistas públicas sensibles de autenticación."""

    throttle_classes = [LimiteIntentosAcceso]

    def throttled(self, request, wait):
        """Convierte el rechazo del limitador en la excepción HTTP 429 de SKILLY.

        Args:
            request (Request): Petición rechazada; no se inspecciona su contenido.
            wait (int | None): Segundos de espera calculados por el limitador.

        Raises:
            IntentosExcesivos: Siempre, con el tiempo de espera recibido.
        """
        raise IntentosExcesivos(wait=wait)
