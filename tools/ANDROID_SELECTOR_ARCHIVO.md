# Selector de adjuntos del Android aislado

`android_selector_archivo.py` automatiza exclusivamente el selector nativo de
archivos de un AVD de ensayo validado por `android_navegador_skilly.py`. No acepta
teléfonos físicos ni concede permisos de cámara, micrófono o almacenamiento.

Primero el controlador E2E debe copiar su PDF sintético a `/sdcard/Download/` con
un nombre único que empiece por `skilly_` y pulsar el `input[type=file]` real de la
aplicación. Después:

```powershell
python tools/android_selector_archivo.py --contextoAndroid '<ruta absoluta a contexto_android.json>' --archivo 'skilly_<nombre_sintetico>.pdf'
```

El helper permite hasta 25 segundos, navega por Files/Archivos y Downloads/Descargas,
y selecciona el nombre exacto. Solo responde «no permitir» en diálogos conocidos
de cámara/micrófono. Un permiso distinto, un nombre ambiguo o una identidad de
emulador no válida detiene la operación. No usa `appops`, cambios de permisos
globales ni rutas directas en el campo de archivo.

Si rechazar cámara cierra el selector, devuelve `retry_file_input_required: true`;
el controlador debe volver a pulsar el mismo input real y repetir el helper.
El helper no cambia el atributo `accept` ni pulsa controles de la aplicación.

El XML se procesa en memoria y nunca se imprime. El único XML remoto temporal
lleva un UUID propio y se retira por su ruta exacta al terminar. No borra adjuntos.
La salida sanitizada distingue selección nativa de subida: `upload_verified`
permanece `false`. El controlador E2E debe verificar por separado que Chrome puede
leer el archivo y que React/Django completan la petición real.

Las pruebas offline están en `tools/tests/test_android_selector_archivo.py`; no
requieren Android, ADB, red ni base de datos.
