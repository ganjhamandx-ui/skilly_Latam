# SKILLY local con puertos alternativos

El launcher y sus verificadores requieren las dependencias de
`requirements-dev.txt` en el entorno Python propio de SKILLY, incluido psutil.

`entorno_local_skilly.py` sirve el backend y frontend reales de este repositorio
sobre la copia PostgreSQL previamente restaurada. Usa los binarios ya instalados;
no instala infraestructura, migra tablas, carga fixtures ni modifica el `.env`.

El host dedicado es `127.0.0.2`: sus cookies quedan separadas de localhost y
127.0.0.1. Los puertos HTTP se eligen comprobando un bind exclusivo y se vuelven a
validar al arrancar; se rechazan 8000, 5173 y 5432. Un conflicto no se resuelve
terminando otro proceso. PostgreSQL conserva el puerto de su configuración de
copia; se comprueban directorio del clúster, base, esquema y rol antes del arranque.

El modo opcional LAN conserva ese host para backend y escritorio y añade un
segundo Vite en una IPv4 privada exacta del PC. No publica PostgreSQL, caché ni
backend en la red. El teléfono accede al origen LAN del frontend; `127.0.0.2`
desde Android apunta al propio teléfono.

## Iniciar y consultar

Desde una terminal local, con rutas absolutas a la configuración **privada**:

```powershell
& 'C:\Users\felip\Downloads\skilly\.venv\Scripts\python.exe' -B 'C:\Users\felip\Downloads\skilly\tools\entorno_local_skilly.py' iniciar --respaldo 'C:\ruta\SKILLY_recuperacion_identificador' --cluster 'C:\ruta\SKILLY_recuperacion_identificador\ensayo_aislado_identificador\cluster' --conexion 'C:\ruta\SKILLY_recuperacion_identificador\conexion_privada.env' --admin 'C:\ruta\SKILLY_recuperacion_identificador\ensayo_aislado_identificador\conexion_aislada.env'
```

La terminal mantiene la supervisión. La salida indica las URLs y la ruta externa
de `contexto.json`; no imprime credenciales. No iniciar otra instancia si ya se
conserva un entorno activo. Para consultar sus identidades y las huellas del
código backend cargado:

```powershell
& 'C:\Users\felip\Downloads\skilly\.venv\Scripts\python.exe' -B 'C:\Users\felip\Downloads\skilly\tools\entorno_local_skilly.py' estado --contexto 'C:\ruta\externa\local_activo_identificador\contexto.json'
```

`product_sources_current` compara los archivos reales con el manifiesto generado
al importar `backend/config/wsgi.py` y abrir el socket. No sustituye una prueba
HTTP ni acredita una versión nueva si después se modifica el backend; en ese
caso se debe cerrar y reabrir únicamente este entorno. Vite transforma los
componentes de `frontend/src` desde el árbol actual.

## Configuración y restricciones

- El launcher pasa `SKILLY_API_PROXY_TARGET` a Vite y `FRONTEND_ORIGIN` a Django.
  El primero no usa prefijo `VITE_` y no se exporta al navegador. Servir Vite sin
  un destino explícito válido falla antes de habilitar el proxy; no hay fallback
  a 8000. Build funciona sin ese parámetro.
- Django confía por CORS/CSRF en su origen configurado. Los retornos y enlaces de
  Webpay se construyen desde ese origen; el cliente académico exige loopback,
  puerto explícito y la ruta exacta. No se desactivan CSRF, TLS ni validaciones
  económicas.
- La configuración local externa apunta solo a la copia verificada. Copia los
  archivos media y privados desde el respaldo, sin sobrescribir originales, y
  verifica sus hashes. Las nuevas cargas se guardan en el directorio del entorno.
- El correo permanece en memoria y las conexiones salientes del backend se
  limitan al PostgreSQL de copia. Esta instancia permite explorar y probar con
  escritura aislada; no envía correo ni crea pagos externos. No acredita pagos,
  conciliación o liquidaciones productivas.
- Las URLs siguen siendo de desarrollo local. No cambian las rutas `/api`,
  contratos, reglas de negocio ni la configuración de otros proyectos.

## Android y dos trabajadores con caché compartida

Estas opciones reutilizan el contexto ya verificado y sus archivos privados:

```powershell
& 'C:\Users\felip\Downloads\skilly\.venv\Scripts\python.exe' -B 'C:\Users\felip\Downloads\skilly\tools\entorno_local_skilly.py' iniciar --respaldo 'C:\ruta\SKILLY_recuperacion_identificador' --cluster 'C:\ruta\SKILLY_recuperacion_identificador\ensayo_aislado_identificador\cluster' --conexion 'C:\ruta\SKILLY_recuperacion_identificador\conexion_privada.env' --admin 'C:\ruta\SKILLY_recuperacion_identificador\ensayo_aislado_identificador\conexion_aislada.env' --reutilizar-contexto 'C:\ruta\SKILLY_recuperacion_identificador\local_activo_anterior\contexto.json' --workers 2 --cache-contexto 'C:\ruta\SKILLY_recuperacion_identificador\cache_activa\conexion_privada.json' --frontend-lan-host 192.168.1.20
```

La IP del ejemplo debe reemplazarse por la interfaz privada exacta del PC,
accesible desde Chrome Android en la misma red. Solo se admiten IPv4 RFC1918;
no se usa `0.0.0.0`. `--frontend-lan-port` permite elegir su puerto libre y
`--backend2-port` el del segundo trabajador. Los puertos por defecto son
efímeros; los orígenes finales aparecen en la salida y en `contexto.json`.
El launcher no cambia el firewall. Si Windows bloquea el acceso, se necesita una
regla limitada al puerto elegido y a la IP del teléfono en el perfil de red
actual; no se debe desactivar el firewall ni abrir un rango global.

La conexión privada de caché contiene `host`, `port`, `password` y `prefix`,
preparados localmente por el supervisor de Redis/Memurai. El launcher admite
solo `127.0.0.1` y un puerto alternativo, comprueba PING con timeout y conserva
la contraseña en memoria/entorno de los hijos, sin imprimirla. No inicia,
instala ni detiene el servidor de caché. `--cache-db` selecciona una base entre
0 y15, por defecto15. Cada RUN deriva del prefijo y de su identificador un
namespace de hasta64 caracteres: ambos trabajadores comparten ese namespace,
sin limpiar claves de otras instancias. Se conservan los timeouts del backend
de caché definido por el producto.
Dos trabajadores requieren caché configurada; no se presentan dos LocMem como
una caché compartida real.

Los dos backends tienen procesos, puertos y archivos de identidad distintos.
`backend_workers` enumera sus orígenes/PID/manifiestos; `access_cache` conserva
host, puerto, base y `key_prefix`, sin contraseña ni URI autenticada. Ambos Vite
usan el trabajador principal; el segundo permite verificar HTTP y límites
compartidos por separado. No se añade un balanceador ni se atribuye distribución
automática a los navegadores.

En Windows, el ejecutable del entorno virtual puede ser un launcher que mantiene
un intérprete hijo. El PID del manifiesto corresponde al intérprete que importa
WSGI, no necesariamente al handle Popen del launcher. Se verifica su ascendencia,
fecha de creación, ejecutable, directorio y argumento del runner propio. El cierre
termina primero los intérpretes propios verificados y después sus launchers; si
no se puede comprobar el árbol, el cierre no declara `own_children_closed=true`.

CSRF y CORS permiten exactamente los dos orígenes frontend creados, sin comodines.
Se conservan las cookies HttpOnly y SameSite existentes: Android usa sus propias
cookies del host LAN y no hereda la sesión de escritorio. Los retornos Webpay
siguen limitados a loopback y el proveedor continúa bloqueado en este entorno;
el modo LAN no acredita un nuevo pago ni cambia esa regla.

`--reutilizar-contexto` exige el mismo respaldo, comprueba la identidad de
PostgreSQL y usa el `backend_files` del contexto anterior. No vuelve a copiar
media ni entregas, por lo que conserva las cargas hechas después del primer
arranque. No migra tablas, recrea la base ni cambia estados por SQL.

Para reutilizar un contexto activo se exige que PostgreSQL siga activo. Si su
supervisor inició el clúster, debe permanecer vivo mientras los nuevos procesos
lo utilicen: `cluster_dependency_context` registra esa dependencia.

También se puede hacer un reemplazo controlado: detener primero el contexto
anterior con su marcador, comprobar externamente que sus PID ya terminaron y
verificar `cierre.json`. El launcher solo acepta un contexto cerrado si existen
`stop.flag` y el cierre confirma `own_children_closed=true` sin intervenir otros
procesos. Después puede iniciar el mismo clúster y reutilizar los archivos,
sin restaurar otra BD ni copiar media. `owns_cluster` indica si este nuevo
supervisor inició PostgreSQL y, por tanto, lo cerrará al terminar. El origen de
los archivos se conserva en `reused_context`; no implica dependencia de un
supervisor ya cerrado. No se transfieren propiedades ni se detienen otros
supervisores o Memurai de forma implícita.

## Detener solo este entorno

```powershell
& 'C:\Users\felip\Downloads\skilly\.venv\Scripts\python.exe' -B 'C:\Users\felip\Downloads\skilly\tools\entorno_local_skilly.py' detener --contexto 'C:\ruta\externa\local_activo_identificador\contexto.json'
```

Se crea un marcador exclusivamente en su RUN. El supervisor cierra sus hijos y
detiene el clúster solo si él lo había iniciado. Conserva configuración, copias y
evidencias. No termina procesos por nombre o por puerto. Si el supervisor dejó de
existir, hay que revisar las identidades antes de recuperar el control; no se debe
usar una terminación masiva ni intervenir en Voltify.

## Verificaciones separadas

`verificar_acceso_local_skilly.py --contexto C:\ruta\contexto.json --actores C:\ruta\fixture_privado.json`
verifica ambos frontends y los dos WSGI por HTTP real: catálogo conservado,
sesiones sintéticas, CSRF, CORS y cookies. Comprueba fuentes y propietarios de
los extremos TCP locales antes de enviar solicitudes. Windows puede comunicar
`CONN_NONE` para un TCP bound sin peer: se exige dirección/puerto exactos del
proceso verificado y luego se comprueba HTTP; no se afirma LISTEN en ese caso.
No invoca Webpay, no escribe datos
de negocio y no equivale a una prueba desde Android. Sus dos logins consumen
la cuota normal del actor: ejecutar después de la carga y de su ventana de
acceso, sin aumentar límites para hacer pasar las comprobaciones.

`pruebas_marketplace_navegador.mjs` compara el App anterior obtenido de Git con el
actual: React/DOM reales, respuestas HTTP y eventos sintéticos, Vite efímero sin
proxy, sin Django/BD. `verificar_puertos_skilly.py` comprueba HTTP real, sesiones,
CSRF/CORS y el callback de un checkout sintético **ya aprobado** en la copia. No
contacta al proveedor ni inicia otro pago. Ambos conservan evidencia externa y
no forman parte de los componentes normales de la aplicación.

Los E2E históricos que exigen rutas `/__isolated/` necesitan su servidor de
ensayo dedicado. Este entorno no publica esas rutas ni controles de reloj.
