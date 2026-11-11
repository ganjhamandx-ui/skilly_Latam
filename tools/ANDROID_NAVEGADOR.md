# Chrome sobre el emulador Android existente

`android_navegador_skilly.py` controla solo el AVD de ensayo descrito por su
contexto privado. No instala Android Studio, SDK, APK ni otro navegador. No crea
una aplicación nativa ni modifica SKILLY, su base de datos o los servicios activos.
Requiere Python y psutil del entorno de desarrollo de SKILLY.

## Arranque después de reiniciar el equipo

```powershell
python -B tools/android_navegador_skilly.py iniciar --respaldo 'C:\ruta\SKILLY_recuperacion_identificador' --sdk 'C:\Users\usuario\AppData\Local\Android\Sdk' --avd Medium_Phone_API_37.0
```

Se comprueba un par de puertos libres para el AVD y se limita a 2 núcleos/2048 MiB,
sin ventana, sin guardar/cargar snapshots y con AVD de solo lectura. Un contexto
propio que siga vivo se reutiliza. Si el PID fue reutilizado por un proceso ajeno,
se rechaza la operación; no se termina ese proceso. El arranque no acredita que
Android haya finalizado de iniciar: consultar `estado` hasta `boot_completed`.
El SDK y el AVD deben existir previamente y ser compatibles con el equipo.

El archivo `contexto_android.json` y sus registros se guardan fuera de Git en
`android_ejecucion_*`; el puntero local `.skilly-android-actual.tmp` es ignorado.

## Estado, conexión y captura

```powershell
python -B tools/android_navegador_skilly.py estado --contexto 'C:\ruta\android_ejecucion_identificador\contexto_android.json'
python -B tools/android_navegador_skilly.py conectar --contexto 'C:\ruta\android_ejecucion_identificador\contexto_android.json' --abrir-chrome
python -B tools/android_navegador_skilly.py capacidades --contexto 'C:\ruta\android_ejecucion_identificador\contexto_android.json'
python -B tools/android_navegador_skilly.py captura --contexto 'C:\ruta\android_ejecucion_identificador\contexto_android.json'
```

`conectar` reutiliza el forward de `chrome_devtools_remote` si existe; no cambia
la página activa. Solo abre Chrome en `about:blank` si todavía no está ejecutándose
y se proporcionó `--abrir-chrome`. No completa pantallas de bienvenida ni accede
a cuentas Google. Nunca muestra XML de pantalla, credenciales o salida ADB cruda.

Las capturas usan los bytes PNG de `adb exec-out screencap -p`, sin redirección
de PowerShell. Se conservan en `capturas_privadas` del RUN y se devuelve ruta,
dimensiones y SHA256. Pueden contener datos de la pantalla: no incorporarlas a
Git ni publicarlas sin una revisión específica.

`capacidades` consulta únicamente los métodos declarados por el protocolo CDP.
Eso **no acredita su ejecución**: Chrome Android puede rechazar, por ejemplo,
contextos de navegador aunque el método figure en el esquema. El driver E2E debe
registrar los métodos y recorridos realmente ejecutados.

## Recargar el backend y frontend del ensayo sin duplicar datos

El contexto de servicios `android_aislado_*/contexto.json` es distinto del contexto
del emulador `android_ejecucion_*/contexto_android.json`. Para cargar una corrección
del producto en la misma copia Android, cerrar únicamente sus servicios propios:

```powershell
python -B tools/entorno_android_skilly.py cerrar --contexto 'C:\ruta\android_aislado_identificador\contexto.json'
```

Esperar a que el supervisor termine y registre `own_children_closed: true` en
`cierre.json`. Después, en una terminal que permanecerá abierta:

```powershell
python -B tools/entorno_android_skilly.py reanudar --contexto 'C:\ruta\android_aislado_identificador\contexto.json'
```

`reanudar` conserva la misma BD nueva, usuarios y fixture, documentos, medios,
puertos y URLs. No ejecuta seed, restore, migraciones ni creación de BD. Verifica
el clúster, el comentario propio de la BD mediante `shobj_description`, la tupla
BD/esquema/rol/puerto y los hashes de los servicios 1 y 2. Rechaza PIDs anteriores
vivos, puertos ocupados, un contexto distinto o una BD ya retirada.

Archiva el contexto y los marcadores anteriores en un directorio UUID sin
sobrescribirlos. El nuevo `backend_ready.json` registra PID, WSGI, puerto, BD y
hashes de los archivos Python reales del producto. El supervisor debe seguir
ejecutándose mientras se utiliza ese ensayo. Este procedimiento no cierra el
AVD, no vuelve a registrar profesionales y no interviene el entorno principal
de SKILLY, Voltify ni la BD original.

## Cierre exclusivo del AVD de ensayo

```powershell
python -B tools/android_navegador_skilly.py cerrar --contexto 'C:\ruta\android_ejecucion_identificador\contexto_android.json'
```

Comprueba serial de emulador, AVD, ejecutable, argumentos, PID y fecha antes de
usar `emu kill`. Retira solo el forward CDP y los reverse ports expresamente
registrados en ese contexto. No usa `kill-server`, `remove-all`, `wipe-data`,
no detiene otros emuladores y no toca frontend/backend/caché de SKILLY. Ejecutar
solo al terminar los recorridos que dependan del AVD. El resultado distingue
emulador Android de dispositivo físico y de un navegador de escritorio estrecho.
