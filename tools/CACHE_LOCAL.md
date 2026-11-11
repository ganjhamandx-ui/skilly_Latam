# Caché local compartida para acceso

El producto usa `acceso.cache.RedisIntentosCache`, un subclass del backend oficial
RedisCache de Django. Un único EVAL procesa todas las cuotas de la solicitud,
sus ventanas y su caducidad;
utiliza el reloj del servidor y una fecha absoluta. Los rechazos no prolongan el
bloqueo. Una indisponibilidad produce 503 genérico y Retry-After, sin revelar la
URI ni omitir la protección. LocMem continúa siendo el default para un proceso.

Variables de proceso —sin modificar el `.env` operativo—:

- `ACCESO_CACHE_BACKEND=acceso.cache.RedisIntentosCache`; el nombre anterior
  `django.core.cache.backends.redis.RedisCache` se normaliza al subclass.
- `ACCESO_CACHE_LOCATION`: un endpoint redis/rediss con puerto explícito; admite
  credenciales privadas, pero no listas, query ni fragmentos.
- `ACCESO_CACHE_KEY_PREFIX`: namespace alfanumérico de hasta 64 caracteres.
- `ACCESO_CACHE_TIMEOUT`: segundos entre 0.1 y 5; default 1, sin reintentos automáticos.

Los límites existentes `ACCESO_LOGIN_*`, `ACCESO_RECUPERAR_*` y
`ACCESO_RESTABLECER_*` conservan el formato `intentos/segundos` y sus reglas. Todos
los trabajadores deben compartir endpoint, prefijo e identidad de firma del
proyecto. No se almacenan correos/IP/tokens legibles en las claves.

## Memurai Developer aislado

`cache_local_skilly.py` usa únicamente el binario previamente extraído y
verificado por el operador. **No descarga, instala ni registra servicios.**
Memurai Developer se utiliza solo para desarrollo/pruebas y se detiene tras
10 días continuos: [condiciones oficiales](https://www.memurai.com/faq).
No constituye una solución productiva certificada.

Requiere dependencias de `requirements-dev.txt`: Redis y psutil. El directorio de
respaldo debe estar fuera del repositorio y llamarse `SKILLY_recuperacion_*`.

```powershell
python -B tools/cache_local_skilly.py iniciar --respaldo 'C:\ruta\SKILLY_recuperacion_identificador' --binario 'C:\ruta\SKILLY_recuperacion_identificador\Memurai\memurai.exe' --sha256 'HUELLA_SHA256_VERIFICADA_DEL_BINARIO'
python -B tools/cache_local_skilly.py estado --contexto 'C:\ruta\externa\cache_activa_identificador\conexion_privada.json'
python -B tools/cache_local_skilly.py detener --contexto 'C:\ruta\externa\cache_activa_identificador\conexion_privada.json'
```

El inicio selecciona mediante bind exclusivo un puerto libre en127.0.0.1,
excluyendo8000/5173/5432/9000. `--puerto` permite uno explícito; si está ocupado,
falla sin desplazar servicios ni elegir otro silenciosamente. Cada inicio nuevo
crea otro RUN, contraseña y contexto, sin sobrescribir anteriores. Con
`iniciar ... --contexto <contexto existente>` verifica y reutiliza esa instancia
sin cambiar credenciales ni reiniciarla.

Configura AUTH, protected-mode,64MiB, noeviction y persistencia desactivada. La
contraseña aparece únicamente en configuración/contexto privados dentro del RUN;
nunca debe copiarse a comandos, chat, Git o reportes. No se modifica el firewall,
la configuración global de Windows ni otros servidores.

Estado/cierre verifican directorio, hash del ejecutable, PID, hora de creación,
línea de ejecución, PING autenticado y PID informado por el servidor. Rechazan
contextos ajenos o PID reutilizados. No ejecutan FLUSHDB/FLUSHALL ni borrado de
claves. Detener o reiniciar esta caché volátil elimina sus contadores: el acceso
falla cerrado mientras no esté disponible, y al arrancar se crean ventanas
nuevas. No usar este procedimiento de pruebas sobre infraestructura productiva.

## Integración de dos trabajadores

`verificar_cache_compartida.py` inicia dos procesos HTTP con los endpoints reales
de Django y PostgreSQL de copia. No modifica el servidor normal. Exige una
instancia Redis/Memurai dedicada y vacía; el namespace de verificación es único.

```powershell
python -B tools/verificar_cache_compartida.py --contexto 'C:\ruta\externa\local_activo_identificador\contexto.json' --cache-contexto 'C:\ruta\externa\cache_activa_identificador\conexion_privada.json' --actores 'C:\ruta\externa\fixture_privado.json' --conexion 'C:\ruta\externa\conexion_privada.env'
```

Comprueba cuota compartida, 30 intentos concurrentes, recuperación al expirar,
respuesta uniforme de recuperación, reset inválido, login/sesión/logout reales,
TTL sin prolongación y fail-closed durante una parada/reinicio controlados.
Antes de parar revisa todas las DB y rechaza datos de otros namespaces. El
reinicio reutiliza solamente su binario/configuración verificados y actualiza
atómicamente el PID del contexto privado; los workers propios se cierran al
terminar. No se declara aprobada esta integración por instalar el driver ni por
sus pruebas offline: debe conservarse su `resultado.json` exitoso.
