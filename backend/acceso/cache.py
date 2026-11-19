"""RedisCache con una operacion atomica de contador, ventana y caducidad."""
from django.core.cache.backends.redis import RedisCache
from django.core.exceptions import ImproperlyConfigured

from config.cache_acceso import timeout_redis, ubicacion_redis_valida


CONTAR_VENTANA = '''
local moment = redis.call('TIME')
local seconds = tonumber(moment[1])
local micros = tonumber(moment[2])
local result = {}
for index, base in ipairs(KEYS) do
    local window = tonumber(ARGV[index])
    local bucket = math.floor(seconds / window)
    local deadline = (bucket + 1) * window
    local key = base .. ':' .. tostring(bucket)
    local count = redis.call('INCR', key)
    local remaining = (deadline - seconds) * 1000 - math.floor(micros / 1000)
    local ttl = redis.call('PTTL', key)
    if ttl < 0 or ttl > remaining then
        redis.call('EXPIREAT', key, deadline)
    end
    table.insert(result, count)
    table.insert(result, deadline - seconds)
end
return result
'''


class RedisIntentosCache(RedisCache):
    """Usa el reloj de Redis primario, no relojes divergentes de los workers.

    La caducidad es una fecha absoluta de la ventana: los intentos rechazados
    no la renuevan. No se reintenta EVAL ante una respuesta perdida, que podria
    haber incrementado ya el contador. Su error se convierte en 503 en el limiter.
    """

    def __init__(self, server, params):
        """Configura un único Redis con tiempos acotados y sin reintentos.

        Args:
            server (str): URL Redis admitida por ``ubicacion_redis_valida``.
            params (dict): Parámetros de caché de Django; se copian junto con
                ``OPTIONS`` antes de ajustar la política de conexión.

        Raises:
            ImproperlyConfigured: Si el endpoint o los tiempos son inválidos,
                o si el driver Redis no está instalado.
        """
        if not ubicacion_redis_valida(server):
            raise ImproperlyConfigured('Redis de acceso requiere un unico endpoint valido.')
        try:
            from redis.backoff import NoBackoff
            from redis.retry import Retry
        except ImportError:
            raise ImproperlyConfigured('El backend Redis de acceso requiere instalar su driver.') from None
        params = dict(params)
        options = dict(params.get('OPTIONS', {}))
        for name in ('socket_timeout', 'socket_connect_timeout'):
            options[name] = timeout_redis(options.get(name, 1))
        options.update(retry=Retry(NoBackoff(), 0), retry_on_timeout=False, retry_on_error=[])
        params['OPTIONS'] = options
        super().__init__(server, params)

    def incrementar_ventana(self, clave_base, ventana, version=None):
        """Incrementa una ventana usando la misma operación atómica del lote.

        Args:
            clave_base (str): Clave lógica, sin sufijo de intervalo temporal.
            ventana (int): Duración entre 1 y 86400 segundos.
            version (int | None): Versión de claves de Django; ``None`` usa la actual.

        Returns:
            tuple[int, int]: Contador actualizado y segundos hasta su vencimiento.

        Raises:
            ValueError: Si la duración o la respuesta de Redis es inválida.
        """
        return self.incrementar_ventanas([(clave_base, ventana)], version=version)[0]

    def incrementar_ventanas(self, ventanas, version=None):
        """Incrementa las dimensiones de una petición en una sola ejecución Lua.

        Args:
            ventanas (list | tuple): Pares de clave base y duración entera entre
                1 y 86400 segundos. La colección debe ser no vacía.
            version (int | None): Versión opcional aplicada a las claves de Django.

        Returns:
            list[tuple[int, int]]: Contador y segundos restantes de cada ventana,
            en el orden recibido, calculados con el reloj del Redis primario.

        Raises:
            ValueError: Si la entrada o los pares devueltos tienen forma o valores
                inválidos. Los errores del cliente Redis se propagan al limitador.

        Note:
            La validación de una respuesta fallida no revierte incrementos que
            Redis ya haya aplicado. Por eso esta operación no reintenta EVAL.
        """
        if not isinstance(ventanas, (list, tuple)) or not ventanas:
            raise ValueError('Ventanas de acceso invalidas.')
        keys, durations = [], []
        for item in ventanas:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError('Ventanas de acceso invalidas.')
            clave_base, ventana = item
            if type(ventana) is not int or not 1 <= ventana <= 86400:
                raise ValueError('Ventana de acceso invalida.')
            keys.append(self.make_and_validate_key(clave_base, version=version))
            durations.append(ventana)
        # La adaptacion al cliente del backend oficial queda aislada aqui. Es
        # siempre el primario; no se consultan replicas para decidir el limite.
        client = self._cache.get_client(keys[0], write=True)
        result = client.eval(CONTAR_VENTANA, len(keys), *keys, *durations)
        if not isinstance(result, (list, tuple)) or len(result) != 2 * len(keys):
            raise ValueError('Respuesta invalida del contador de acceso.')
        counters = []
        for index, ventana in enumerate(durations):
            count, wait = result[index * 2:index * 2 + 2]
            if (type(count) is not int or count < 1
                    or type(wait) is not int or not 1 <= wait <= ventana):
                raise ValueError('Respuesta invalida del contador de acceso.')
            counters.append((count, wait))
        return counters
