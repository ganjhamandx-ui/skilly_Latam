# SKILLY local con puertos alternativos

`entorno_local_skilly.py` sirve el backend y frontend reales de este repositorio
sobre la copia PostgreSQL previamente restaurada. Usa los binarios ya instalados;
no instala infraestructura, migra tablas, carga fixtures ni modifica el `.env`.

El host dedicado es `127.0.0.2`: sus cookies quedan separadas de localhost y
127.0.0.1. Los puertos HTTP se eligen comprobando un bind exclusivo y se vuelven a
validar al arrancar; se rechazan 8000, 5173 y 5432. Un conflicto no se resuelve
terminando otro proceso. PostgreSQL conserva el puerto de su configuración de
copia; se comprueban directorio del clúster, base, esquema y rol antes del arranque.

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

`pruebas_marketplace_navegador.mjs` compara el App anterior obtenido de Git con el
actual: React/DOM reales, respuestas HTTP y eventos sintéticos, Vite efímero sin
proxy, sin Django/BD. `verificar_puertos_skilly.py` comprueba HTTP real, sesiones,
CSRF/CORS y el callback de un checkout sintético **ya aprobado** en la copia. No
contacta al proveedor ni inicia otro pago. Ambos conservan evidencia externa y
no forman parte de los componentes normales de la aplicación.

Los E2E históricos que exigen rutas `/__isolated/` necesitan su servidor de
ensayo dedicado. Este entorno no publica esas rutas ni controles de reloj.
