# Registro de refactorización de SKILLY

Este es el registro técnico de trabajo. La auditoría documental definitiva de los 22 documentos y los 2 Excel no se ha iniciado y queda reservada a confirmación expresa del usuario.

## Prioridad vigente: reparación funcional y seguridad

- SonarQube queda **pospuesto por indicación del usuario** hasta nueva solicitud expresa. No se ejecutan scanners, exportadores, solicitudes de token ni ajustes destinados exclusivamente al Quality Gate. Se preservan herramientas y resultados anteriores; el último gate conocido sigue ERROR, sin aprobación.
- Las menciones posteriores a autenticación, importación y reanálisis describen pendientes históricos, no acciones previstas durante esta etapa. Las vulnerabilidades y errores reales identificados siguen dentro del alcance.
- Se continúa con correcciones, recorridos completos mediante interfaz, permisos, estados de error y adaptación móvil, en la copia aislada. Se conserva `master`, se publican cambios verificados en `refactor/skilly` y no se modifican Word ni Excel.

## Continuación vigente: Android automatizado y reanudación local

- El último encargo amplía la cobertura Android y sustituye el cierre móvil anterior. Se conserva el entorno principal activo y el acceso del teléfono; la regla `SKILLY_Android_88fcc27d` sigue presente. No se interpreta la respuesta que repetía el comando de eliminación como prueba de que se hubiera ejecutado. Las reglas originales de Node eran **Allow**: el diagnóstico anterior que interpretó el valor 2 como bloqueo era incorrecto.
- Se reutilizan sin repetir caché 16/16, carga 1/2/4/8, purga anterior, Webpay sandbox asistido, escritorio/estilos/modal y las confirmaciones del Android físico. Las comprobaciones nuevas usan el AVD existente, Android **17/API 37**, Chrome **156.0.8078.79**, con almacenamiento del AVD de solo lectura y sin guardar snapshots. No son un teléfono físico ni una ventana de escritorio reducida.
- Entorno adicional exclusivo `android_aislado_9e0bf2864c434675b1e7`, creado desde el dump recuperable ya restaurado y verificado. Base nueva con marca propia; frontend/backend propios y salida externa bloqueada. La copia activa del usuario y sus servicios 1 y 2 permanecen separados. Sesiones del navegador independientes por actor; organización usa su referencia privada existente, no una cuenta o dashboard inventados.
- **Recorridos Android terminados por reanudación de la misma fixture**: 161 comprobaciones con nombres distintos, incluidas 74 acciones React → HTTP con activación táctil confiable observada. Las 74 instancias repetidas por reautenticación/reintentos no se cuentan como casos nuevos. Los resultados enlazados están en `android_aislado_9e0bf2864c434675b1e7/cobertura_final_android.json`; 55 PNG auténticos, incluidos fallos y su diagnóstico. Es una cadena de ejecuciones reanudadas, no una única ejecución ininterrumpida. Último resultado de sesión: `browser_e2e_3b8171dd6a01458d8d9b3ebeddfd489a/resultado.json`, sin errores; geometría pendiente completada en `browser_e2e_3e6ee047a31845acbec8a16e80b276fd`.
- Correcciones del arnés Android: seguimiento de peticiones canceladas al cambiar de documento y observación de `fetch` sin sustituir respuestas. La ruta directa CDP de un adjunto daba `NotReadableError` por acceso al archivo; el selector **nativo DocumentsUI** sí permite leer y subir los bytes sintéticos. Se mantiene el filtro del producto: no se altera `accept` para forzar un ejecutable; su rechazo backend/escritorio previo no se presenta como una prueba Android nueva. La entrada de texto se automatiza mediante eventos DOM; no acredita escritura con teclado nativo. Se estabiliza la geometría táctil después de cerrar el IME antes de pulsar.
- Ajuste del lanzador real de desarrollo: `tools/entorno_local_skilly.py --reanudar-tras-reinicio` permite reutilizar los medios actuales tras un reinicio de Windows sin cierre completo. Exige prueba de un nuevo boot y revisa los PID previos/reutilizados sin terminarlos; conserva las guardias de clúster/base/esquema/rol y puertos. No fabrica cierres ni restaura un dump encima. **49 pruebas offline aprobadas**: 15 de reanudación, 25 del lanzador y 9 de identidad. No se reinició el PC ni se sustituyó el entorno activo para probarlo. Instrucciones en `tools/ENTORNO_LOCAL.md`.
- Corrección nueva en el producto real: los cuatro controles de transferencia/configuración bancaria exigían el nombre literal `skilly`, bloqueando con 503 una base distinta expresamente configurada en Django. `backend/config/identidad_bancaria.py` compara la identidad PostgreSQL con `connection.settings_dict['NAME']`, conserva esquema `skilly` y exige tanto rol actual como USER configurado `skilly_app`; configuración vacía, base discordante y usuarios privilegiados fallan cerrados. Se integró en `pagos/views.py`, ambas vistas `transferencia_disponibilidad.py` y `backoffice/cuentas_bancarias_api.py`. No contiene ramas exclusivas del ensayo ni desactiva controles. **33 pruebas backend relacionadas y `check` aprobados**, con cursores/ORM simulados y sin escritura; evidencia `android_aislado_9e0bf2864c434675b1e7/verificacion_identidad_bancaria`. Después se recargó únicamente el runtime Android, conservando la misma base/fixture/puertos. La transferencia sintética mediante UI, su verificación administrativa y contratación ya avanzaron realmente; no se movió dinero. El entorno principal del usuario sigue sin interrupciones.
- SonarQube continúa pospuesto; Word/Excel y auditoría documental sin cambios. No se contactó el puerto 8000 ni se intervino Voltify. Preparar herramientas o arrancar el emulador no equivale a aprobar los recorridos.

### Cobertura Android efectivamente ejecutada

| Participante / rutas reales | Resultados nuevos |
| --- | --- |
| Público: `/`, `/seguimiento` | Solicitud empresarial, política de cancelación, comprobante, seguimiento, reagendamiento, observaciones/aceptación, reclamos y retroalimentación privada mediante referencia. No existe login empresarial independiente. |
| Profesional: `/acceso-profesional`, `/portal-profesional`, `/disponibilidad` | Registro, sesión, documentos/rechazo/corrección, validación, entrevista prematura rechazada y habilitación posterior; propuesta/corrección/aceptación/publicación; disponibilidad, avances y entregas con adjuntos nativos. |
| Administración: `/administracion`, `/administracion/validaciones`, `/administracion/propuestas` | Revisión documental/profesional, agenda de entrevista, propuesta final, autoasignación, asociación, condiciones, contratación, coordinación, pago y liberación. |
| Administración: `/administracion/reclamos`, `/administracion/expedientes-cancelacion`, `/administracion/retroalimentacion` | Reclamo y resolución, cierre, lectura privada de feedback, evaluación de cancelación, cancelación del contrato y reversa simulada. |
| Administración: `/administracion/indicadores`, `/administracion/comision`, `/administracion/cancelaciones`, `/administracion/cuentas-bancarias`, `/administracion/trazabilidad`, `/administracion/entregables` | Lectura real de las seis rutas, menú, filtros, historial bancario, modal de indicadores y retorno desde el alias; no se cambiaron parámetros ni cuentas. |
| Sesiones y permisos | Logout profesional/administrativo, barrera posterior y cookies separadas; límites visibles por rol. Lecturas HTTP auxiliares desde Chrome confirman documentos propios/ajenos/anónimos, pagos/feedback administrativos y prestación ajena: se distinguen de las acciones táctiles. |

- Ciclos completos: contratación con transferencia sintética verificada, reagendamiento acordado por tres actores, avance, entrega observada, nueva versión aceptada, reclamo resuelto, finalización, feedback privado y liberación con comisión; segundo contrato, expediente evaluado, cancelación y reversa con estado explícito `SIMULADA`. Las acciones duplicadas dejan de ofrecerse donde corresponde; se rechazaron aprobación de entrevista prematura y liberaciones con observaciones, reclamo abierto o contrato cancelado.
- Integración real del producto/HTTP/PostgreSQL y selector **DocumentsUI**; recepción bancaria, entrevista humana, liberación contable y devolución **simuladas**, sin dinero ni envío externo. El reloj se controló exclusivamente en el wrapper de ensayo y quedó restituido. Webpay sandbox real asistido anterior se conserva sin repetirlo ni atribuir a la automatización la autenticación bancaria hecha por el usuario.
- Geometría del producto actual sin estilos A/B: documentos y propuesta profesionales, entregas cerradas en consulta y las seis rutas administrativas, incluido modal de indicadores. Los formularios de entrega se usaron durante el ciclo activo; el arnés dejó de intentar crear otra entrega después del cierre. No se certifican todas las combinaciones visuales, teclado nativo automatizado, recuperación/reset nuevos en Android ni un teléfono físico automatizado. Las nueve confirmaciones físicas anteriores siguen siendo manuales y separadas.
- Los ajustes adicionales fueron del arnés, no reparaciones ficticias del producto: espera de campos/agenda asíncronos, selector de sesión correctamente escapado y logout que exige HTTP 200 más barrera privada sin depender de un cuerpo descartado al navegar. `tools/tests/test_sesiones_movil.mjs`: **5/5 offline**. Herramientas Android: **9** guardias del navegador conservadas, **11** del selector, **15** de runtime/reanudación y **7** de inventario aprobadas. La reanudación real también descubrió y corrigió el uso de `obj_description` para una BD compartida: ahora `shobj_description`, con regresiones exactas en reanudación/retirada. Ningún control del producto se desactivó para aprobar pruebas.

### Datos, limpieza y entorno que se deja activo

- `inventario_datos_android_338480fb08c24a0c862e447cd99eb107.json`: consultas de solo lectura, **120 filas relacionadas en 35 tablas**, con IDs/PK/FK y anclas de las fixtures. No contiene credenciales ni referencias privadas y no se presenta como un delta completo inicial/final. Identifica usuarios auxiliares, profesional 22, servicio 11 y solicitudes/prestaciones 23/24, entre otras relaciones.
- Retirada **una sola vez** de la base nueva marcada `skilly_android_9e0bf2864c434675b1e7` después de cerrar sus procesos y generar `datos_android_antes_retirada.dump` (SHA256 `880d8d610531ae1c986728df6a14a8766ed9086c4df3c55f1604928cd5b7ac2d`). Catálogo del archivo legible; **este snapshot nuevo no se restauró**. Se conserva el respaldo principal anterior realmente restaurado y verificado (116 tablas/2.220 filas), con su hash comprobado al cierre. No se repitió la purga anterior ni se deshabilitaron triggers. Servicios reales 1/2 conservados por hash antes de retirar la nueva copia; catálogo principal final `[1,2]`.
- Limpieza de archivos confirmada en `plan_limpieza_cierre.json` y `limpieza_archivos_cierre.json`: **21 copias privadas redundantes del ensayo cerrado y 15 auxiliares obsoletos**, 1.390.676 bytes. Originales retenidos o copia exacta archivada y hashes verificados antes/después. Se retiraron también auxiliares antiguos que aún contenían suposiciones de puertos incorrectas; no se ejecutaron. Un error de agregación de bytes de PowerShell se corrigió reconstruyendo el informe mediante verificación independiente, sin repetir borrados. Se conservan documentos sintéticos nuevos vinculados al snapshot, resultados, capturas y respaldos únicos; no se borran respaldos por edad/nombre.
- AVD de ensayo cerrado sin guardar cambios; solo sus forward/reverse registrados retirados, sin `kill-server`, sin afectar otros dispositivos. Se mantienen Node dedicado, firewall, frontend/backend principal, caché y PostgreSQL de copia porque sostienen el acceso del usuario. **PC http://127.0.0.2:57741/**; **teléfono http://192.168.100.19:57742/**. HTTP 200 y catálogos 1/2 en ambos; identidad de procesos/cwd/código de este proyecto y PING autenticado de Memurai comprobados en `entorno_principal_conservado.json`.
- **Límite de actualización en memoria:** los backends principales PID 42432/48784 permanecen activos con las cuatro vistas bancarias anteriores en memoria; no se reiniciaron para evitar interrumpir al usuario. La corrección publicada se cargó y verificó realmente en el runtime Android. En la configuración principal, cuyo nombre es `skilly`, ambas versiones conservan la misma autorización; la nueva versión se cargará al reiniciar con el procedimiento siguiente. Vite sirve el frontend real sin cambios nuevos de lógica/estilos. No se afirma que esos dos procesos ya hayan recargado el commit nuevo.
- Publicaciones verificadas: `957b752` (recuperación del lanzador), `0f50220` (identidad bancaria) y `851d6ea` (herramientas Android, recorridos y retirada verificados). Revisión explícita de archivos, Gitleaks staged sin hallazgos y SHA remoto comprobado en cada unidad; ninguna dependencia, BD, fixture, archivo privado ni evidencia visual se incorporó a Git. Rama `refactor/skilly`; `master` conserva `f9fdb9e9a8005cc000046b1b1a914825599a86bc`, primera versión disponible del historial. Esta etapa Android queda cerrada con las limitaciones observadas, sin pedir más pruebas manuales ni agregar otras etapas. SonarQube sigue pospuesto. La carga del nuevo guard bancario en los dos procesos principales se conserva para el próximo arranque, sin presentarla como ya realizada.

### Volver a iniciar después de reiniciar Windows

No ejecutar mientras esté activo SKILLY. Después del reinicio, abrir PowerShell y usar las rutas locales ya existentes; no se introduce ninguna contraseña en el comando ni se restaura la BD. La terminal final mantiene el supervisor abierto:

```powershell
$R = 'C:\Users\felip\Downloads\skilly'
$B = 'C:\Users\felip\Downloads\SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b'
$P = "$R\.venv\Scripts\python.exe"
$ultimo = Get-Content -Raw -LiteralPath "$R\.skilly-local-activo.tmp" | ConvertFrom-Json
$anterior = Join-Path $ultimo.run_dir 'contexto.json'
$cache = & $P -B "$R\tools\cache_local_skilly.py" iniciar --respaldo $B --binario "$B\cache_memurai_4_1_2\extraido\Memurai\memurai.exe" --sha256 c9d6f5e5a4c34b772d2e1b1f9a7c346562e16155d1adc9e5469c96d19d400629 --puerto 52893 | ConvertFrom-Json
if (-not $cache.completed) { throw 'Cache no disponible; conservar los procesos ajenos.' }
& $P -B "$R\tools\entorno_local_skilly.py" iniciar --respaldo $B --cluster "$B\ensayo_aislado_4cc39c7e659a40ca8f0778eb51a72e0d\cluster" --conexion "$B\integracion_real_461dea855d9a4a148112a9ba0ba90941\conexion_privada.env" --admin "$B\ensayo_aislado_4cc39c7e659a40ca8f0778eb51a72e0d\conexion_aislada.env" --reutilizar-contexto $anterior --reanudar-tras-reinicio --workers 2 --cache-contexto $cache.context --cache-db 15 --backend-port 57739 --backend2-port 57740 --frontend-port 57741 --frontend-lan-host 192.168.100.19 --frontend-lan-port 57742 --node "$B\node_aislado_android\node.exe"
```

Antes de iniciar, comprobar que la IP del PC siga siendo `192.168.100.19` y la del teléfono `192.168.100.4`; la regla de acceso queda limitada a esas direcciones y al puerto 57742. El lanzador comprueba puertos libres, identidades y origen/proxy; si hay conflicto falla sin terminar procesos. No usar 8000 ni cambiar reglas ajenas. Si cambió la red, no reutilizar direcciones ni ampliar el firewall a ciegas. La caché nueva pierde contadores volátiles, no datos de PostgreSQL. Se conservan los medios más recientes mediante `$anterior`; no omitir ese parámetro. No hace falta iniciar el emulador para abrir el sitio en PC o teléfono. El reinicio físico del equipo no se ejecutó durante esta sesión; la recuperación está validada mediante pruebas offline.

## Cierre anterior del 11 de noviembre (alcance ampliado posteriormente)

- Cerrada esta etapa acotada: caché **16/16 integración real**, acceso desktop/LAN **36/36 HTTP real**, **228 pruebas backend** y **62 de herramientas** verificadas; Android/Chrome comprobado manualmente por el usuario en acceso, catálogo/detalle, formularios y sesión. Las 65 pruebas frontend, lint y build anteriores se conservan: no hubo cambios posteriores del frontend que justificaran repetirlos. No se confunden unitarias/simulaciones con integraciones reales o intervención manual.
- Publicados `22bb0ee` (producto Redis) y `24f2c58` (herramientas verificadas). GitHub privado y SHA remoto comprobados; `master` conserva la referencia inicial. El commit inicial sigue siendo la primera versión disponible en Git, sin atribuirle etapas previas.
- **Limpieza ejecutada una sola vez:** 60 perfiles de navegador de ensayos cerrados y cuatro auxiliares obsoletos con copia exacta conservada. **2.448.655.678 bytes lógicos (~2,28 GiB)** retirados. Se verificaron procesos, rutas/ausencia de enlaces y hashes antes de cada borrado; se conservaron 63 resultados y 586 archivos hermanos por hash. Detalle de rutas/motivos/bytes en `limpieza_perfiles_cce400dd1daf49ba975c0924d3c7d5c9/acciones.jsonl` y `resultado.json`. No repetir el plan: sus objetivos ya no existen. Los seis perfiles con checkpoints y respaldos/auxiliares de dependencia o recuperabilidad ambigua se conservaron.
- Punto de recuperación **actual posterior a purga y carga**: `recuperacion_reciente_361a5de6db674c5d86cae8d51200d418`. Bundle Git verificado de `24f2c58` (producto y herramientas completos); dump consistente mediante snapshot exportado, **restaurado realmente en una base temporal nueva: 116 tablas/2.220 filas, todos los hashes iguales**. Se retiró exclusivamente esa base temporal. El manifiesto privado enlaza `.env` y 21 archivos privados ya respaldados, sin duplicar carpetas completas. Debe conservarse junto con esos archivos y las conexiones privadas externas; no es un dump aislado autosuficiente. Se mantienen los respaldos únicos original y previo a purga.
- Verificación posterior a limpieza: ambos frontends devuelven 200, ambos catálogos contienen IDs 1 y 2, los 165 archivos backend de ambos procesos coinciden con el código real actual, caché autenticada y limitada a 64 MiB, bundle/dump/22 archivos privados retenidos por hash (`local_activo_88fcc27dc54c4fd8/cierre_20261111.json`). El `.env` y los 21 archivos originales siguen iguales, sin ausencias ni extras (`preservacion_datos_707bda18f6f44e71b11af75344459b53`). Se dejan servidores activos; no se hicieron solicitudes HTTP al 8000 ni acciones sobre Voltify. La ausencia de pruebas sobre Voltify no acredita su salud funcional.
- Pendientes delimitados: SonarQube pospuesto; no se certifican alta disponibilidad de la caché, capacidad productiva/máxima ni todos los ciclos de negocio en el teléfono. Android/modelo y versión exactos de Chrome no informados; confirmaciones manuales registradas en `android_fisico.json`, sin capturas inspeccionables disponibles. Webpay sandbox asistido previo se conserva sin repetirlo; no acredita pagos ni liquidaciones reales. Word/Excel y auditoría documental siguen reservados. No se declara el sistema libre de errores ni listo para producción.
- La copia PostgreSQL ya estaba activa al iniciar el nuevo supervisor (`owns_cluster=false`); permanece en ejecución. El supervisor antiguo había salido; sus tres procesos de aplicación restantes se retiraron por identidad después del reemplazo. El contexto antiguo conserva los archivos privados reutilizados y evidencia, no debe eliminarse ni tratarse como un supervisor vivo.

## Trabajo de esta continuación: caché, teléfono, carga y limpieza

- Nueva autorización: completar caché compartida real, acceso físico Android/Chrome en la misma Wi-Fi, carga gradual aislada y limpieza de residuos confirmados. Se conserva el entorno activo y sus dependencias hasta terminar las tareas que los necesiten. Los pendientes históricos de SonarQube siguen pospuestos.
- Retirado del producto real únicamente el texto «Datos obtenidos de Django REST» (`frontend/src/App.jsx`). No se añadió un filtro del catálogo ni se cambiaron los textos, precios o profesionales de las tarjetas/detalles.
- Verificación de esta retirada: frontend **65/65**, lint **0/0**, compilación correcta (`verificacion_frontend_14086ba2f8384a43937ef7c6bcf60691`); Edge contra React/HTTP/PostgreSQL de copia **7/7**, sin mocks ni escrituras (`ui_local_c1d07c2961514328b01b929ea02137fc`). Esta ventana de navegador no acredita la prueba en teléfono físico.
- Los resultados que siguen documentan caché, carga, teléfono y limpieza; instalar una dependencia o preparar una herramienta no acredita por sí solo su cierre.
- Publicada la retirada del texto en `4d28b830d22bfacd3ee9885173d0e302190916a7`, con secretos revisados y SHA remoto comprobado.
- **Purga aislada terminada; no repetir**: se retiraron los servicios sintéticos 3–10 y 333 filas dependientes, conservando los servicios 1 y 2 y todos los datos supervivientes por hash en las 116 tablas. Un primer intento revirtió íntegramente ante el trigger de inmutabilidad bancaria. Tras autorización expresa del usuario se deshabilitó/restableció solo ese trigger dentro de la transacción de mantenimiento; se verificó su definición y estado antes de confirmar. La comprobación posterior al retomar confirma IDs `[1,2]` y trigger habilitado. Sin cambios persistentes del esquema, sin borrar archivos ni conectar a la BD original. Evidencia: `catalogo_limpieza_08d3524278a04468b96b6ac41f8ac968`, con snapshot privado de las filas retiradas.
- Recuperación previa a esa purga: `recuperacion_reciente_2f14f36b29f143f09c7655f7f9fcd41d/postgresql_copia_antes_limpieza.dump`. **Respaldo generado y restauración real verificada** en una base nueva temporal del clúster de copia: 116 tablas/2.443 filas y todos sus hashes iguales; base temporal retirada, copia activa intacta. `.env` y los 21 archivos privados siguen conservados en el respaldo externo existente, sin duplicarlos indiscriminadamente.
- La primera integración real de caché descubrió una carrera entre cuotas IP/cuenta: 2 admitidos y 28 bloqueados en vez de 3/27. Se conserva el fallo (`cache_compartida_1c892aec09864ed2`); el producto ahora actualiza todas las cuotas de una solicitud en un único EVAL y con reloj Redis. Regresión backend **228/228**, sin red/BD (`validacion_modulos_7703c40db5ef4998800e0d02523d95bb`). La repetición real corregida se registra a continuación.
- **Integración real de caché corregida cerrada: 16/16** (`cache_compartida_bf96d730b7d7430a`). Dos procesos HTTP independientes importan el WSGI del producto real; PostgreSQL de copia y Memurai/Redis reales, sin mocks. Cuota compartida, 30 intentos concurrentes con exactamente **3 admitidos/27 bloqueados**, rechazo sin renovación de TTL, expiración, recuperación uniforme para cuentas existentes/inexistentes, reset inválido, login/logout y sesión entre procesos. Caída de la instancia dedicada: login/recuperación/reset devuelven **503** y Retry-After; reinicio autenticado y login posterior correctos. Cuotas privadas de ensayo 3/5 s y namespace exclusivo; los límites normales del producto no se alteraron. Correo locmem, sin cambiar contraseñas ni pagos reales. Los dos procesos de prueba se cerraron y Memurai quedó restituido. La configuración local de caché es volátil: reiniciarla elimina contadores, no los datos PostgreSQL; no acredita alta disponibilidad ni producción.

### Continuación del 11 de noviembre: entorno real actualizado y teléfono

- Producto Redis publicado en `22bb0ee79e46c227e08c92aa16790b55ee78f132`; repositorio privado, Gitleaks sin hallazgos y SHA remoto comprobados. La pausa para diagnosticar Codex no modificó SKILLY; se reanudó sin repetir purga ni Webpay.
- Entorno actual: `local_activo_88fcc27dc54c4fd8/contexto.json` bajo el respaldo externo. Frontend desktop **http://127.0.0.2:57741/**; backends **http://127.0.0.2:57739/** y **http://127.0.0.2:57740/**, con 165 fuentes backend reales y sus hashes actuales en ambos manifiestos. La URL LAN, la regla y la IP del teléfono permanecen en configuración privada. Ambos Vite sirven el frontend real y hacen proxy al backend propio. PostgreSQL de copia conserva 57647; los archivos privados se reutilizan sin otra copia completa ni cambios del `.env`.
- Correcciones de herramientas: identificación del intérprete hijo del launcher venv/alias Windows Store por imagen real, ascendencia, fecha, cwd y runner; cierre exclusivo de hijos y wrappers propios. **9** regresiones de identidad y **25** del launcher pasaron. El arranque fallido `local_activo_bdcf19726baf4ff4` se conserva; no alteró datos. Los procesos anteriores de SKILLY se retiraron después del reemplazo; PostgreSQL siguió activo (`retiro_anterior.json`).
- El verificador conserva propiedad del extremo TCP y manifiesto completo. Windows comunica `NONE` para ciertos sockets que sirven HTTP; se admite solo Windows/TCP IPv4 exacto sin peer, seguido de HTTP real. **8** pruebas offline y **36/36 HTTP reales** desktop/LAN correctas (`verificacion_acceso_14251a45ee994755a839820d4d1e394e`): catálogo/detalles/App actuales, sesiones entre procesos, cookies, CSRF faltante/incorrecto/origen ajeno rechazados, CORS exacto y logout. No usa el checkout purgado ni contacta Webpay.
- **Android/Chrome físico confirmado por el usuario**: misma Wi-Fi, portada y dos servicios; tarjetas sin precio/nombre profesional y detalle con ambos, desplazamiento/cierre del modal, teclado/validación de campos vacíos, regreso al catálogo; login con cuenta ficticia, disponibilidad/servicios propios, logout y restricción posterior de pantallas privadas. Son observaciones manuales del usuario, no emulación ni automatización. No hubo imágenes inspeccionables en las rutas disponibles; modelo y versión exactos de Chrome no informados. No se certifican todos los ciclos de negocio en ese teléfono. Sin pagos ni envíos reales.
- Acceso LAN con un Node dedicado, de la misma versión instalada, firma y hash verificados. El usuario creó la regla exacta de SKILLY con elevación administrativa. **Corrección del diagnóstico:** el valor numérico 2 de NetSecurity significa `Allow`, no bloqueo; las reglas originales de Node ya permitían conexiones y se conservaron. La copia dedicada se conserva para delimitar las reglas de SKILLY. No se desactivó firewall ni se modificaron reglas ajenas.

### Carga acotada e integridad

- `carga_real_20261111_88fcc27d`: dos procesos reales, PostgreSQL de copia, sesiones/CSRF reales y datos sintéticos; sin mocks ni proveedores. Plan persistido antes de ejecutar: calentamiento 2 s, etapas **1/2/4/8 clientes, 10 s cada una**, una iteración/s/cliente y máximo 64 escrituras por etapa. Parada por CPU global >70 % en tres muestras, RAM disponible <2 GiB, 5xx >1 %, cinco 5xx consecutivos o p95 >3 s. Ninguna condición se activó.
- **27/56/107/217 solicitudes** por etapa: 2,70/5,60/10,69/**21,69 solicitudes/s**, p95 115/143/152/**146 ms**. Las 407 solicitudes medidas devolvieron 200/201; calentamiento, ocho logins y logout se registran aparte. Sin errores de transporte ni 429 durante carga; los 27 rechazos 429 esperados son del ensayo específico de caché. CPU global máxima **16,8 %**, RAM disponible mínima **12.614.062.080 bytes**, RSS máximo por backend **83.234.816 bytes**. Es un circuito limitado en WSGI de ensayo local, no capacidad máxima ni garantía productiva.
- SQL posterior: 15 bloques nuevos, un evento de creación por bloque, **cero duplicados** y disponibilidad previa intacta. Snapshot privado y retirada exclusiva de esos 15 bloques sin reservas (`integridad_y_limpieza.json`); no se repitió la purga de servicios. **15** pruebas offline del plan de carga y **5** del controlador de caché pasaron.

## Cierre anterior verificado: producto real y puertos alternativos

- Ruta `C:\Users\felip\Downloads\skilly`, rama `refactor/skilly`. Al retomar, HEAD era `34a2834`; se conservaron App.jsx y los dos harness pendientes, sin descartar archivos. La auditoría inicial contrastó los 298 archivos del producto del manifiesto móvil con backend/frontend reales: ninguno faltaba ni difería antes de estas reparaciones nuevas. No se encontraron parches de producto olvidados en copias temporales ni controles de laboratorio infiltrados en la aplicación.
- El puerto 8000 pertenece a Voltify, no a SKILLY. La mención histórica a «servidor original del puerto 8000» acreditaba su conservación, no la identidad de SKILLY. Por la nueva autorización se seleccionaron puertos libres alternativos; no se enviaron pruebas al 8000 ni se modificaron procesos, configuración, archivos o BD de Voltify. Sus cuatro PID de referencia conservan sus tiempos de creación.

### Cambios del producto

- `frontend/src/App.jsx` impide los cuatro cierres del modal mientras se envía la solicitud, conserva la referencia aun si falla el refresco posterior y bloquea envíos duplicados inmediatos. Integra el hook real de foco compartido, deshabilita los cierres durante escritura y corrige el mensaje con acentos perdidos.
- La lectura del catálogo real detectó otro caso: al volver a la ventana, el refresco puede reemplazar el disparador del modal. App devuelve ahora el foco a su botón equivalente o al buscador estable mientras carga, sin desactivar el refresco ni robar un foco válido. El hook compartido y las reglas de solicitudes se conservan.
- `frontend/vite.config.js` y `frontend/config/proxyApiLocal.mjs` exigen `SKILLY_API_PROXY_TARGET` explícito para servir `/api`, solo HTTP loopback canónico con puerto válido distinto de 8000. No existe fallback que envíe tráfico a Voltify. Build no necesita la variable; esta no se exporta al cliente.
- `backend/config/settings.py`, `config/origenes.py` y los dos módulos Webpay usan `FRONTEND_ORIGIN` estructuralmente válido. CORS/CSRF confían en el origen configurado; retornos y redirecciones se calculan desde él. El cliente académico conserva TLS/DEBUG y exige loopback, puerto explícito y ruta exacta para el retorno. No se alteraron endpoints, contratos ni reglas económicas.

### Ejecución actual verificada

- Frontend: **http://127.0.0.2:53009/**. Backend: **http://127.0.0.2:53008/**; catálogo API en `/api/marketplace/servicios/`. El host separado conserva el nombre de cookie CSRF requerido por Disponibilidad sin compartir cookies con localhost/127.0.0.1.
- `tools/entorno_local_skilly.py` comprobó la disponibilidad mediante bind y el arranque estricto. Backend PID **37200**, Vite PID **42184**. El WSGI importado es `backend/config/wsgi.py` de esta raíz; su manifiesto coincide con las fuentes actuales. Vite ejecuta el módulo instalado en `frontend/node_modules` y sirve el App real actualizado. No son las copias compiladas del harness.
- Instancia de desarrollo sobre PostgreSQL **de copia**, puerto 57647, con directorio de clúster/base/esquema/rol verificados antes de usarlo. Configuración privada y 21 copias de archivos con hashes comprobados permanecen fuera de Git. Las cargas van al RUN; correo en memoria y salidas del backend limitadas al PostgreSQL de copia. La BD original, `skilly_cu040_pruebas`, `.env` operativo y archivos privados originales no se modificaron.
- Contexto privado actual: `local_activo_bea5799c5ccc4e2c/contexto.json` bajo el respaldo externo ya identificado. Los procesos se dejan activos para abrir SKILLY. `tools/ENTORNO_LOCAL.md` documenta inicio, estado y cierre exclusivo; no instala infraestructura ni detiene servicios por puerto/nombre.

### Pruebas de esta unidad y alcance

- Backend: **214/214**, Django check correcto, 294 archivos de fuente sin corrupción; red y BD bloqueadas durante esas unitarias. Incluye 16 pruebas nuevas de configuración, CORS/CSRF, retornos y transporte simulado. Evidencia: `validacion_modulos_b858ca0650414d00810fc3afbc27140c`.
- Frontend final: **65/65**, ESLint 0 errores/0 advertencias y build correcto. Incluye siete pruebas del proxy local. Evidencia: `verificacion_frontend_1bbcc1c5435a4895b5cb7ccc5b04b506`.
- Modal: cuatro pasadas antes/después en 1366/390 px, **102/102 comprobaciones internas y siete guardias**, fuentes congeladas y cero API real. React/DOM reales, HTTP/datos/eventos sintéticos; no es E2E PostgreSQL ni teléfono físico. Casos: envío diferido y cuatro cierres, referencia tras POST201/GET503, doble envío, error/reintento, foco y catálogo reemplazado. Evidencia: `marketplace_modal_c2c25346a4cb40d590ba9872c77ac861`. Las capturas no muestran la referencia bajo el pliegue; esa conservación se acredita con DOM.
- Navegador contra el producto activo: **7/7**, catálogo/detalle por proxy y PostgreSQL reales, Tab/Escape y retorno de foco, 390 px sin desborde; solo GET, sin mocks ni escrituras. Evidencia: `ui_local_da4f9b6e40d24d8b968b92e3d0a7d9f9`. Los intentos previos se conservan; distinguieron un selector del probe incorrecto del defecto real de foco posteriormente reparado.
- Integración HTTP de puertos: **19/19**, login/logout y cookie de sesión reales en la copia, token ausente/incorrecto/origen ajeno rechazados, CORS exacto y App actual servido por Vite. Dos callbacks del checkout ya aprobado devolvieron 302 al nuevo frontend y conservaron el estado RETENIDO; no se creó otro pago ni se contactó al proveedor. Evidencia: `local_activo_bea5799c5ccc4e2c/verificacion_http_0a971cd40f6a46e39848961d8c94ba36`.
- Herramientas: **15/15** pruebas offline del arrancador y **14/14** del consultor GET, sin arrancar otros servicios ni contactar proveedor/BD. La compilación por AST y el arranque real confirmaron que los generadores funcionan. Los harness, snapshots y ajustes privados permanecen separados del producto; no hay mocks ni rutas de control añadidas al funcionamiento normal.
- Se conserva la evidencia Webpay anterior: **integración real sandbox asistida por el usuario en el banco**, 10/10, POST1/PUT1 y GET AUTHORIZED. No se repitió la compra: solo se verificó el callback ya confirmado por el cambio relacionado de puertos. Esto no acredita dinero, correo ni liquidaciones productivos.

### Pendientes delimitados

- Caché compartida: falta servidor y driver; no se instala infraestructura adicional por esta etapa.
- Dispositivos físicos y capacidad productiva no certificados. SonarQube sigue pospuesto, sin scanner/exportador/token. Word/Excel y su auditoría documental siguen reservados.
- Las pruebas previas no relacionadas se conservan. No se declara el sistema libre de defectos ni listo para producción.

### Publicación y conservación de esta unidad

- Modal y regresiones publicados en `80d596c11e508479d858e595beb2b6323056d51e`; el push se comprobó contra GitHub privado, con Gitleaks sin hallazgos. Evidencia: `commit_revisado_72500f4d06464aae8467e99e54743bdf`.
- Auditoría de historial y 402 candidatos: cero hallazgos; comparación de valores operativos en memoria: cero coincidencias en candidatos y 438 blobs históricos; ningún archivo privado, dependencia o BD entre candidatos. Evidencia: `auditoria_publicacion_77f6173599a44d71b01d5183c1ad065c`. Cada selección vuelve a examinarse antes del commit.
- Comprobación por hash del `.env` y de los 21 archivos privados originales: sin diferencias, ausencias ni archivos adicionales, sin conexión a la BD original. Evidencia: `preservacion_datos_a12b535155f14577a0c9c5d076e54598`.
- Identidades finales, fuentes backend actuales y continuidad pasiva de los cuatro procesos de Voltify verificadas; seis auxiliares conservados por hash. SKILLY se deja en ejecución y no se sondearon servicios ajenos. Evidencia: `cierre_puertos_e5dc420e386148c8b2b1f16f311c3a78`.

## Continuación del 9 y 10 de noviembre (histórico)

- Revisión inicial: árbol limpio, sin archivos ni commits pendientes de publicación. Verificados los SHA contra GitHub: `refactor/skilly` en `d41dcdaa0aece469c0fa80871b3850503e1da2a0`, que ya incluye las herramientas del 7 de noviembre; `master` conserva `f9fdb9e9a8005cc000046b1b1a914825599a86bc`. Repositorio privado, no archivado y con permiso de push.
- Se conserva el checkout anterior. Una consulta **GET HTTPS real** al sandbox, sin Django/BD ni POST/PUT, devolvió **HTTP 200 / INITIALIZED**. No confirma autorización ni demuestra expiración. Evidencia externa: checkout original `sandbox_browser_e1cdd302db8a4f589890e0199b8f4d46/estado_sandbox_f713ab6a154945d8933dc23edfd5b4b3/resultado.json`, bajo el runtime ya registrado.
- Se inspeccionó el mismo checkout con una copia única del perfil Edge original: página del proveedor con **Error 21**, sin formulario. No se ingresaron datos ni se crearon/confirmaron pagos durante esa inspección; el perfil original no se modificó. No se deduce una causa específica del código visual. Captura saneada y metadatos: `inspeccion_webpay_7ca70c0961d04f59b32309e76669ab1d` en el respaldo externo.
- Nueva herramienta `tools/webpay_estado_sandbox.py`: consulta exclusivamente GET, TLS verificado, sin proxies ni redirecciones, lectura acotada y salida de metadatos. No carga `.env`, no conecta a BD ni imprime el cuerpo del proveedor. Resuelve las rutas largas locales por operación, sin cambiar permisos o políticas de Windows. **14 pruebas offline aprobadas**, con cliente/transporte simulados y canarios de privacidad; no se presentan como 14 peticiones reales.
- Se conservan las verificaciones anteriores de negocio, seguridad y UX. Sonar sigue pospuesto. El inventario de caché compartida no encontró servidor Redis/Memcached, drivers Python, Docker ni WSL instalado: sigue pendiente una prueba real entre trabajadores; no se sustituye por una simulación para declararla aprobada.
- Publicado `6fe78705a54b8ff50858aa89923ba45e638b13cd`: consulta GET, 14 pruebas offline y documentación, después de Gitleaks sin hallazgos y comprobación del remoto. Evidencia: `commit_revisado_d4d91d0b874c4ce89bfe57919fb5e786`.

### Webpay cerrado: integración real asistida, sin dinero real

- El checkout conservado del 7 de noviembre no se autorizó ni se alteró. Se guardaron por lectura estado, verificación, hash del token e historial y se compararon al finalizar: **sin diferencias**. Su diagnóstico sigue siendo GET INITIALIZED y pantalla Error 21; no se le atribuye el éxito del ensayo nuevo.
- Se prepararon prestaciones sintéticas independientes únicamente en el clúster de copia verificado. El primer ensayo nuevo llegó a Webpay, pero el driver perdió el cuerpo 201 durante la navegación; se conservó con POST=1/PUT=0. La reanudación de su última ruta respondió 404, sin ingresar tarjeta. Estos intentos parciales no se suman a la pasada exitosa.
- Se reparó la captura del token real del formulario saliente, condicionada al inicio local 201, con checkpoint privado inmediato y validación estricta. Se añadió selección del paso Tarjetas, reanudación por copia de perfil y modo visible de una sola sesión. Se conservaron orígenes, rutas, CSRF y reglas del producto; no se cambió lógica del backend/frontend para hacer pasar el ensayo.
- **Pasada continua nueva: 10/10, completed=true y authorization_verified=true**, con React, Django HTTP, PostgreSQL de copia y Webpay oficial de integración reales, sin respuestas simuladas. Creación POST=1 y confirmación PUT=1. El callback real dejó el pago RETENIDO en la prestación correcta; repetir el callback produjo 302 sin otro PUT. Una consulta GET independiente posterior devolvió **HTTP 200 / AUTHORIZED**.
- El usuario confirmó que completó RUT y clave ficticios en el simulador bancario de la ventana visible. Se clasifica **integración real asistida por el usuario**, no automatización completa. Se conservan `bank_credentials_entered=false` y `bank_submitted=false`, porque el driver no realizó esas acciones. La asistencia automatizada adicional no llegó a ejecutarse. No hubo desafíos humanos observados, tarjetas/credenciales bancarias reales, cargos reales ni correo externo.
- Evidencia de éxito: `continuacion_7104ca3157d44bc1be9be634da7ce20e/sandbox_runtime_1e4edcbc8c684f3e941508c5de5c1c40/sandbox_browser_69549c8d3dd44700b82de68aef8b0ef3/resultado.json`; GET posterior en su subdirectorio `estado_sandbox_ae454e0148824cafa6e06d94dc419198`. Incluye dos capturas locales; los archivos privados y perfiles permanecen fuera de Git.
- Preservación del pago antiguo: `continuacion_7104ca3157d44bc1be9be634da7ce20e/preservacion_webpay_a0a0b8995991/antes.json` y `despues_a793fff23746.json`. Herramientas finales: **17/17 Node y 14/14 Python offline**, ocho módulos con sintaxis válida, fuentes conservadas por hash en `verificacion_herramientas_269ad69143a94703a574ffc3d61e60a3`. Las 31 pruebas offline no equivalen a 31 pagos ni sustituyen las 10 comprobaciones reales.

### Pendientes actuales

- SonarQube continúa pospuesto, sin scanner/exportador/API ni cambios destinados al gate.
- Caché compartida entre trabajadores: falta servidor y driver local; LocMem y sus pruebas anteriores no acreditan ese alcance.
- Dispositivos físicos y capacidad productiva siguen sin certificarse. Los recorridos generales anteriores de 129/130, las 198 pruebas backend, 58 frontend y lint/build se conservan; no se repitieron por estos cambios de herramientas.
- Automatizar el paso bancario humano es opcional y no se presenta como cerrado. Tampoco se acreditan pagos, reversas, conciliación o liquidaciones productivas. Los checkouts parciales anteriores permanecen como evidencia, sin forzar sus estados.
- La auditoría de Word/Excel sigue reservada; no se modificaron esos documentos ni se desplegó.

### Conservación y cierre de esta continuación

- `.env` operativo y 21 archivos privados originales conservan sus hashes: 18 media y tres entregas, sin ausencias, diferencias ni archivos adicionales. No se conectó a la BD original. Evidencia: `preservacion_datos_62385601e7264b79860965bd51d16b87/resultado.json`.
- El sandbox exitoso cerró con POST=1/PUT=1; se preservó su guardia en `cierre_sandbox_fab7662725104fba8313b471fa87af1c`. Se cerraron padre, backends/Vite y PostgreSQL de copia tras verificar el directorio del clúster. El servidor original del puerto 8000 estaba activo antes y después, sin intervención sobre él.
- Se preservaron por hash 14 auxiliares locales fuera de Git, sin borrar archivos ni tocar el listener IPv6 ajeno. Evidencia de cierre: `cierre_webpay_ef0a8f3b4dec47d5abf3c7247a795856/resultado.json`.
- Revisión previa a publicación: Gitleaks sin hallazgos en historial y 391 candidatos; comparación en memoria sin coincidencias operativas en candidatos y 430 blobs históricos; ningún archivo prohibido. Evidencia: `auditoria_publicacion_dab7f58f8d0f4afd841ff40c950ae2d1/resultado.json`. Se vuelve a revisar la selección exacta antes de cada commit.

## Recuperación del trabajo interrumpido (7 de noviembre, histórico)

- Confirmados en GitHub privado los commits `a3e62a0` (registro/recuperación), `eb22b8c` (permisos/privacidad) y `a87fdc8` (reagendamientos). El SHA remoto de `refactor/skilly` coincide con el último; `master` sigue en `f9fdb9e`. Los siete archivos pendientes al retomar eran un texto de Seguimiento y seis archivos de pruebas, sin cambios descartados.
- Escritorio: una pasada nueva completa **129/129**, sin resultados heredados ni errores, con reloj restaurado. Incluye registro/documentos/corrección, entrevista sintética, propuesta/publicación, dos contratos, transferencia sintética, reagendamiento, avance, entrega observada/corregida/aceptada, reclamo/resolución, cierre, feedback privado, comisión/liberación y cancelación/reversa simulada. Son 82 operaciones verificadas desde React/HTTP, 33 aserciones, seis consultas auxiliares de estado y ocho de permisos; no se atribuyen las consultas auxiliares a clics de interfaz.
- Evidencia escritorio: `continuacion_c90c757328c546d5b46f34c9fe95b882/browser_e2e_ffae488af5514fd28606dd308fa29aeb/resultado.json`, con nueve capturas. Los ensayos parciales fallidos se conservan y no se suman a la pasada completa.
- Móvil: pasada nueva completa **130/130**, sin resultados heredados ni errores, con reloj restaurado. Las 82 operaciones UI registraron activación confiable y eventos táctiles; se distinguen 33 aserciones, seis consultas de estado, ocho de permisos y una comprobación de integridad. Los 303 hashes de fuentes antes/después coinciden. No se simularon React, Django ni PostgreSQL; entrevista humana, confirmación bancaria y movimientos económicos siguen siendo sintéticos, con correo en memoria.
- Evidencia móvil: `continuacion_fc46b8bbcf6b4328a391a66a0af00cda/browser_e2e_a4d1054504154a7186323f07718d88af/resultado.json`. Sus nueve capturas y geometrías tienen ancho cliente/contenido de 390/390 px. Edge emula capacidad táctil; no acredita teléfonos físicos. Los fallos previos de coordenadas CDP y desplazamiento durante el tap se corrigieron en el driver, conservando las animaciones y controles del producto.
- Los CLIs capturan errores de JSON privado sin fragmentos ni stack: **2/2 pruebas negativas aprobadas** con canarios aleatorios, sin red. Webpay se ensaya por separado y no se atribuye autorización de tarjeta al recorrido general. El primer intento actualizado se detuvo antes del checkout por formulario no disponible; la identidad aislada se verificó y no se declara autorización aprobada.
- El .env original, los 18 archivos media y las tres entregas privadas coinciden por hash con sus respaldos, sin archivos adicionales ni conexión a la BD original. Evidencia: `preservacion_datos_83f28093af9d4ab8acf34013bb9593cb/resultado.json`. Al retomar no había listener en el puerto original 8000; no se lo inició ni detuvo.
- Frontend final tras el ajuste CSS: **58/58**, ESLint 0 errores/0 advertencias y build correcto. Evidencia: `verificacion_frontend_44cb2dcebdf54924972a617fb5aecc64/resultado.json`. El texto «OPINIÓN PRIVADA» evita numerar Opinión como el bloque 04 de Pago, sin cambiar su grupo, anclas ni comportamiento.

## Verificado: portal móvil con identificadores largos

- Un correo largo sin puntos de corte ensanchaba la introducción del portal de 390 a 404 px; también afectaba el viewport de sus diálogos. Se añadió únicamente `overflow-wrap: anywhere` al párrafo de introducción. No se cambiaron rutas, acciones ni reglas de negocio.
- La comparación A/B midió documentos, propuesta y entregas: **404 → 390 px**, con cliente de 390 px y sin controles recortados. Evidencia: `continuacion_c90c757328c546d5b46f34c9fe95b882/browser_e2e_edb188e6c69b47a8b5b7131d94545207/resultado.json`. Las hipótesis de ancho mínimo del diálogo y ancho de backdrop no corrigieron la causa y no se incorporaron.
- Después del recorrido móvil completo se ejecutó, de forma secuencial, `--phase layout --mobile --assert-layout`: **11/11**, fuente sin cambios, reloj restaurado, documento y tres formularios a 390/390 px y sin recortes. No se guardan formularios ni se aplican estilos efímeros en ese modo. Evidencia: `continuacion_fc46b8bbcf6b4328a391a66a0af00cda/browser_e2e_3afeaa3be9464d1fa5fe5b3fc43c1519/resultado.json`.
- Las capturas actuales ocultan datos mediante superposiciones sin sustituir el texto ni cambiar su geometría. El saneamiento anterior acortaba correos en el DOM: aquellas capturas no acreditaban el caso de identificadores largos, aunque se conservan sus resultados históricos. Se preservan las evidencias y los ensayos fallidos fuera de Git.

## Herramientas y revisión de publicación de esta continuación

- El ajuste móvil y la aclaración de Opinión privada se publicaron en `dce7fea3b47fa90255766865f578b18640ae50aa`, tras revisión del diff, comprobación frontend, recorrido móvil completo, layout secuencial y Gitleaks sin hallazgos. Evidencia del commit/push: `commit_revisado_0b3b53bb215c4d658c054079d98a78a8`.
- Se conserva el recorrido de navegador en cinco módulos y `tools/E2E_NAVEGADOR.md`, con guardias del backend/proxy, capturas sin alterar geometría, manifiestos de fuentes, checkpoints, reloj restablecido y diferenciación entre operaciones UI, consultas auxiliares y actividades sintéticas.
- Herramientas finales: **ocho módulos con sintaxis válida y 10/10 pruebas offline**. Incluyen JSON privado corrupto con canarios, párrafos oficiales multilínea, rechazo de datos de otra sección, formularios de tarjeta por etapas y diagnóstico limitado a metadatos. Evidencia: `verificacion_herramientas_0f7570f91d19424eab9a0881b1d4a863`.
- Auditoría de todas las referencias Git y 389 archivos candidatos: **0 hallazgos**; comparación en memoria con secretos operativos: **0 coincidencias** en candidatos y 424 blobs históricos; **0 candidatos prohibidos**. El `.env` coincide con su respaldo. No se imprimieron valores ni se incorporaron informes privados. Evidencia: `auditoria_publicacion_dd97cef9158848b3b2af75ffaf4a3d45/resultado.json`; cada commit vuelve a examinar su selección con Gitleaks.

## Webpay: integración parcial del 7 de noviembre (histórico)

El recorrido real asistido posterior, registrado arriba, cierra la comprobación de autorización, retorno e idempotencia; se conservan a continuación los límites y evidencias del ensayo anterior.

- Contexto dedicado con Django/React/PostgreSQL de copia, identidad backend/proxy/navegador verificada, TLS obligatorio y salida limitada al proveedor de integración. El conflicto de resolución IPv6 se evitó solo en el perfil temporal de Edge y en el transporte del ensayo; no se cambiaron DNS global, puertos del producto ni procesos ajenos.
- Se corrigieron únicamente supuestos del driver: pulsar «Consultar estado» después de precargar la referencia, reconocer el párrafo oficial multilínea y seguir el formulario de tarjeta por etapas. No se modificaron controles del producto ni validaciones de pago.
- Una creación HTTPS real de checkout, **POST=1, PUT=0**; los reintentos reutilizaron el mismo token privado. El primer checkout mostró el campo de número de tarjeta. En el último intento, antes de ingresar datos, el proveedor respondió HTTP 200 con página completa de 112 caracteres, cero controles visibles y cero iframes. No hubo fallos de red del origen oficial registrados; solo se bloquearon recursos externos de fuentes/analítica.
- Ninguno de los seis indicadores confirmó expiración, rechazo, desafío humano o causa específica. No se atribuye el bloqueo a SKILLY ni se afirma que el token caducó. El último ensayo no envió PAN, CVV ni credenciales bancarias. Se conservan metadatos, etapas booleanas, categorías/estados de red y el checkout privado, sin cuerpos ni URL con token en el diagnóstico.
- **No aprobados:** autorización sandbox, callback completo e idempotencia posterior a una confirmación real. La creación del checkout y las pruebas offline no equivalen a esos resultados. Queda por inspeccionar localmente la página del proveedor y determinar el estado de ese checkout antes de preparar otra prueba dedicada; no se crea otra transacción para ocultar el fallo.
- Evidencia definitiva: `continuacion_c90c757328c546d5b46f34c9fe95b882/sandbox_runtime_1dc4a896c913400381b0234f1b27b045/sandbox_browser_fdefe880fbdc4c66b9fedd7a490bf34f/resultado.json`, `pagina_proveedor_metadatos.json`; checkout original en `sandbox_browser_e1cdd302db8a4f589890e0199b8f4d46/checkout_privado.json`. Todo permanece fuera de Git. No se realizaron pagos ni envíos reales.

## Pendientes al 7 de noviembre (histórico)

- SonarQube **pospuesto expresamente**, con resultados y herramientas conservados; no se ejecutó durante esta continuación y no se declara gate aprobado.
- Webpay: cerrar la autorización y el retorno sandbox descritos arriba. La transferencia/verificación, liberación y reversa de los recorridos generales son sintéticas; no acreditan operaciones bancarias ni liquidaciones reales.
- Backend de límites compartido entre varios trabajadores no ejecutado; LocMem cubre un proceso y se conserva el aviso de despliegue. Faltan validación humana y dispositivos físicos adicionales; Edge móvil es emulación. La carga pequeña de lectura de JMeter registrada anteriormente no certifica capacidad productiva.
- No quedan fallos abiertos en las pasadas completas de negocio registradas: escritorio 129/129 y móvil 130/130. Esto no constituye una garantía de ausencia de otros defectos ni de preparación productiva.
- La auditoría documental de los 22 Word y los 2 Excel continúa reservada a la indicación expresa del usuario. Esos archivos no se modificaron; no se desplegó ni se hizo merge a `master`.

## Conservación y cierre de los ensayos del 7 de noviembre

- Comprobación final por hash: `.env` original idéntico al respaldo, 18 archivos media y tres entregas privadas sin diferencias, ausencias ni archivos adicionales. No se conectó a la BD original. Evidencia: `preservacion_datos_4a6842de0e9a4ba28e278568389c41c9/resultado.json`.
- El cierre por marcador no terminó los procesos huérfanos de la sesión interrumpida. Se identificaron nuevamente por sus rutas completas de script y se cerraron solo esos procesos. Después se verificaron por conexión de administrador el `data_directory` y puerto 57647 del clúster de copia antes de detenerlo. No se modificaron contraseñas, permisos globales ni el esquema operativo.
- Comprobados cerrados los backends/Vite propios y PostgreSQL aislado; el puerto original 8000 estaba sin listener antes y después. El listener IPv6 ajeno no se tocó. Los auxiliares se copiaron fuera de Git y verificaron por hash, sin borrar archivos. Evidencia: `cierre_verificado_4279e11f4af848778083d16f1408b30b/resultado.json`.

## Verificado: registros concurrentes y errores de recuperación

- Dos registros simultáneos para el mismo correo conservan una cuenta y un perfil: 201/400 con el error de correo existente, en lugar de propagar la restricción SQL como 500. Un savepoint interior permite consultar el conflicto sin romper la transacción conjunta de cuenta/perfil; otros errores de integridad siguen propagándose.
- Los fallos SMTP registran únicamente un evento fijo, sin contenido de la excepción ni traceback. La respuesta de recuperación sigue siendo genérica y el fallo revierte el token creado.
- Cinco pruebas unitarias nuevas con ORM/SMTP simulados y **18 comprobaciones de integración Django/PostgreSQL reales dentro del proceso**, pasando por middleware/API. Incluyen concurrencia sincronizada, rollback de perfil y de token, restablecimiento de un solo uso, revocación de sesión, claves anterior/nueva, CSRF y cierre de sesión.
- El correo exitoso usa memoria; se inyectan solo la barrera concurrente, el fallo de perfil y el fallo SMTP. No se atribuye esta prueba a navegador ni SMTP real. El rol de aplicación no permite leer `data_directory`; se verificó con el administrador de la copia, sin conceder permisos.
- Evidencia: `continuacion_62fc2e44c9a5492c94d0206afe58cade/acceso_integracion_1f18f178baad436ea1b23c27daa134ee/resultado.json`; suite offline de 188 pruebas aprobada antes de añadir las siguientes regresiones de pagos/privacidad. El entorno operativo y la base original se conservan.

## Verificado: permisos por objeto y privacidad de expedientes

- Reparada la creación de perfil para cuentas profesionales existentes sin perfil: autenticación de sesión SKILLY y permiso de profesional, manteniendo URL, bloqueo de usuario y 409 para duplicados. La prueba roja reproducía 403 ante una sesión legítima.
- Los comprobantes administrativos se entregan con `private, no-store`, `nosniff` y `no-referrer`; se rechazan separadores Windows, rutas ambiguas y flujos NTFS. La desaparición del archivo al abrir produce 404. No se demostró un IDOR remoto en esta ruta; se endurecen referencias heredadas y almacenamiento.
- Los antecedentes internos `INCIDENCIA_PROFESIONAL` de cancelación ya no se filtran al enlace empresarial de avances; profesional y administración conservan el registro. La prueba roja demostraba la publicación del tercer avance interno.
- Liberar exige también `VERIFICADO`, coherente con los flujos existentes que registran RETENIDO y VERIFICADO juntos. Estados inconsistentes o heredados reciben 409 sin movimiento. Se conservan entrega aceptada, bloqueos por reclamo/reversa, comisión y reintento idempotente.
- **198 pruebas unitarias aprobadas** y comprobación Django correcta, con red/BD bloqueadas. Las nuevas pruebas de despacho DRF/ficheros usan ORM simulado; no se presentan como integración PostgreSQL.
- **51 comprobaciones adicionales con Django/middleware/PostgreSQL y archivos reales**, dentro del proceso: perfil faltante, CSRF/roles, propietario/ajeno/anónimo, firma empresarial/otra solicitud, integridad y cabeceras privadas, cancelación/aviso internos, liberación/reversa inválidas y un único historial tras reintento. Fixtures nuevas por ORM únicamente en la copia, sin cambios de esquema, dinero ni correo externos.
- Evidencia: `validacion_modulos_43463018b9c248d9a038692b0d37525b/backend_resultado.json` y `continuacion_c90c757328c546d5b46f34c9fe95b882/objetos_integracion_b404d356e0b54e55927e5beaa800e84e/resultado.json`. El contexto anterior se cerró normalmente y el nuevo servidor aislado incorpora estas correcciones.

## Verificado: estados y reintentos de reagendamiento

- Administración y profesional muestran vacío únicamente después de una consulta válida; carga y error tienen estados accesibles distintos. «Actualizar» permite recuperarse sin perder motivos escritos. Las acciones quedan bloqueadas cuando la lectura está pendiente o ha fallado.
- Los tres roles impiden un segundo envío desde el primer evento, conservan CSRF y deshabilitan edición durante escritura; el sondeo se pausa durante la acción. Se valida el formato de listados y no se envía POST si la obtención de CSRF falla, aunque la respuesta contenga un token.
- La introducción del portal precede a las notificaciones, especialmente útil en móvil. Se inspeccionaron capturas reales de escritorio y móvil; no hubo desborde en esas vistas. No se cambiaron endpoints, payloads ni decisiones de reagendamiento.
- **58/58 pruebas Node**, ESLint completo 0/0 y compilación correctos. **35 comprobaciones en Edge aprobadas**, con fuente congelada: sesión y lecturas reales más un harness separado React/DOM con respuestas simuladas para carga/error/vacío/retry/doble envío en tres roles. Esas simulaciones no acreditan por sí mismas transiciones de negocio en PostgreSQL.
- Cuatro capturas antes/después a 1366/390 px. El driver reproducible lee los dos componentes anteriores desde Git (`eb22b8c`) y los compila en memoria; sus dependencias y estilos son actuales. No sustituye archivos del árbol de trabajo ni pretende reconstruir todo el frontend histórico.
- Evidencia: `continuacion_c90c757328c546d5b46f34c9fe95b882/ux_reagendamientos_4a2dac900e964580a2bb9170dc751c01/resultado.json`; la primera ejecución de 35 checks y las fuentes previas también se conservan. Los recorridos UI completos de negocio se verifican por separado.

## Continuación y control de versiones

- Destino comprobado mediante Git y conector GitHub: `https://github.com/ganjhamandx-ui/skilly`, privado y con permisos de publicación. La autenticación Git y los SHA de ambas ramas se verificaron contra el servidor.
- `master` conserva `f9fdb9e9a8005cc000046b1b1a914825599a86bc`; el desarrollo continúa en `refactor/skilly`. No se hace merge a master, force push ni reescritura.
- El commit inicial es la primera versión disponible en este historial; Git no aporta evidencia de etapas anteriores.
- Gitleaks **8.30.1** instalado por WinGet, fuera de PATH. Auditoría de todas las referencias y archivos candidatos: **0 hallazgos**. Comparación con secretos operativos: **0 coincidencias**; sin archivos prohibidos entre candidatos. Solo se conservaron metadatos sanitizados.
- Ambas ramas ya estaban publicadas al verificar; el push autorizado confirmó sus SHA, sin incorporar trabajo pendiente no verificado.
- Evidencia: `auditoria_git_e674fe3601e149d587a0e4d3aba22945/resultado.json` y `publicacion_revisada_8cc4525075b046c199ff960c3c157fa1/resultado.json`, bajo el respaldo externo indicado más abajo.

## Completado: límites de intentos

- Límites configurables por IP y por identidad+IP para inicio, solicitud de recuperación y restablecimiento. Ventanas cortas/largas fijas, 429 y Retry-After; las solicitudes rechazadas no prolongan indefinidamente el bloqueo.
- No hay veto global por correo. Se usan HMAC para claves y REMOTE_ADDR; XFF se acepta solo a través de proxies expresamente confiables.
- La recuperación conserva mensajes y secuencias de estados independientes de la existencia de la cuenta. Login inexistente realiza trabajo de hash; no se afirma igualdad exacta de tiempos SMTP o de todos los algoritmos heredados.
- Fallos al inicializar/usar caché producen 503 genérico sin filtrar sus URI. LocMem cubre un proceso local; `check --deploy` emite `acceso.W001` hasta configurar un backend compartido para múltiples trabajadores. Redis/Memcached compartido no se ha ejecutado.
- **169 pruebas backend aprobadas**, incluidas 16 nuevas de límites. Conexiones bloqueadas durante las unitarias.
- **12 comprobaciones HTTP reales** en proceso aislado con LocMem propio y ventanas de prueba de 2/30 segundos: bloqueo, recuperación tras TTL, comportamiento homogéneo por existencia y validación de reset recuperada. Los límites operativos no se cambiaron.
- Evidencias: `validacion_modulos_3f26bd7afe46432299e6b9d164f4fd98/backend_resultado.json` y `continuacion_ec5fd1bf356e455c80591b980d4dbc44/api_e2e_7030fc8998a348d394e315015578f882/limites_http.json`.

## Completado: carga diferida por ruta

- Las rutas y su normalización se conservan, incluidos el alias de entregables y el destino inicial para rutas desconocidas. Cada pantalla se importa cuando se necesita.
- Suspense ofrece estado accesible de carga; el límite de errores ofrece recarga manual y regreso al inicio, sin bucles de reintento automático.
- Comparación medida del build antes del rediseño visual: bloque principal **636302 → 225647 bytes**; gzip **159420 → 70154 bytes**. El JavaScript de inicio completo pasa a **253813 bytes**, acceso **240051**, administración **309848** y portal **357474**. No se oculta una advertencia subiendo el umbral; ya no hay bloques de más de 500 kB.
- **43 pruebas Node aprobadas**, ESLint 0/0 y compilación correcta. Las métricas por chunk y dependencias se conservan en la evidencia del commit.
- **9 comprobaciones de navegador aprobadas**: solicitud diferida, espera accesible, fallo de módulo inyectado, recuperación manual, ausencia de bucle, alias y ruta desconocida. Una lectura inicial del DOM anterior se corrigió en el test esperando la ruta nueva; no se modificó el producto para eludir la comprobación.
- Evidencia: `continuacion_ec5fd1bf356e455c80591b980d4dbc44/carga_rutas_1793930378949/resultado.json`. Las capturas previas también recorrieron las 16 pantallas con módulos reales.

## Hallazgos prioritarios del análisis local

- El usuario ejecutó SonarQube local con autenticación oculta. El procesamiento terminó, pero el gate inicial fue **ERROR**, no aprobado: cobertura recibida 0 %, 425 incidencias nuevas; métricas totales 1 bug, 2 vulnerabilidades y 620 observaciones de mantenibilidad.
- La exportación prioritaria identificó `python:S4830` y `python:S4423` en el contexto TLS de Webpay, y `javascript:S9011` en el botón de envío bancario. No son hallazgos de secretos del repositorio.
- El cliente ya usaba `ssl.create_default_context`; se hicieron explícitos CA obligatoria, comprobación de hostname y mínimo TLS 1.2. Tres pruebas nuevas comprueban el contexto real, su entrega al transporte simulado y que un fallo de certificado no se reintenta sin verificación. El código de peticiones, endpoint y validación económica se conservan.
- El botón bancario declara explícitamente `type="submit"`, conservando su operación de registro/edición.
- **172 pruebas backend aprobadas**. Además, una petición HTTPS real creó un checkout en el sandbox oficial con la política TLS actual, sin enviar tarjetas ni autorizar dinero. No equivale a un pago completo ni a una prueba productiva.
- La clasificación de Sonar tras las correcciones queda pendiente de repetir el análisis; no se silencian reglas ni se alteran umbrales para declarar aprobación.
- Evidencias: `validacion_modulos_edd3995318814b3782475e7ec981da41/backend_resultado.json`, `continuacion_ec5fd1bf356e455c80591b980d4dbc44/sonar_analisis_d0fcb003da31497781e68de7874bbb78/resultado.json` y `sandbox_webpay_fc05c5c8d8a945238d3dec3d97b110ca/resultado.json`.
- Referencia de política TLS: [documentación oficial de Python](https://docs.python.org/3.13/library/ssl.html#ssl.create_default_context).

Se conservan rutas, puertos configurados, contratos de API y reglas de negocio. Los commits revisados se publican únicamente en el repositorio privado GitHub autorizado; no se despliega.

## Completado: CSRF y recuperación aislada

- Baseline conservado: `f9fdb9e9a8005cc000046b1b1a914825599a86bc`, rama `refactor/skilly`.
- `SesionSkillyAuthentication` hereda la comprobación estándar CSRF de DRF y la aplica tras validar al usuario activo.
- Protección explícita de `dispatch` en cuentas bancarias y configuración de cancelaciones. Se conservan permisos, sesiones y respuestas legítimas.
- Dos módulos nuevos con 12 pruebas de regresión. Estas pruebas usan usuarios/controladores simulados, sin PostgreSQL.
- Suite backend: **133 aprobadas**, Django check correcto, con conexiones/red bloqueadas y correo en memoria.
- Integración real: navegador Edge headless, React servido por Vite, Django HTTP y PostgreSQL restaurado en un cluster independiente. **23 comprobaciones aprobadas**, sin simular autenticación, controladores o base de datos.
- Se verificaron login/logout desde la interfaz, cookies HttpOnly/SameSite, rotación CSRF, invalidación de sesión, rechazos por token ausente/incorrecto/origen no permitido y escrituras bancarias reales verificadas en la copia.
- Marketplace y validación de solicitud pública conservaron su comportamiento. Retorno Webpay sin token y con token desconocido devolvió 400/404 reales; no se contactó con Transbank ni se hicieron pagos. Las respuestas de proveedor autorizadas se prueban solo con mocks en la suite existente.
- El puerto 8000 estaba ocupado. La integración utilizó puertos temporales solo en procesos de prueba, sin alterar la configuración ni detener el servidor existente.
- El dump se restauró y verificó previamente: 116 tablas y 1388 filas. Para integración bancaria se creó, únicamente en ese cluster independiente, una base `skilly` y rol `skilly_app` que satisfacen la guardia existente.
- Instancia de pruebas apagada; `.env`, credenciales, permisos y datos del servidor operativo intactos.

Evidencias locales fuera de Git, bajo `C:\Users\felip\Downloads\SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b`:

- `integracion_real_461dea855d9a4a148112a9ba0ba90941/browser_result.json`, `resultado.json`, captura tras logout y scripts del ensayo.
- `validacion_csrf_f6e7e0fccd1f47c885ebbf09fade9353/resultado.json` y `tests.log`.
- Los directorios de evidencia contienen configuración privada de pruebas; no se incorporan al repositorio.

## Completado: cargas asíncronas y estados de interfaz

- Se separaron consultas de aplicación de estado con un controlador que cancela e invalida solicitudes anteriores, incluso si la respuesta llega después del aborto.
- Se corrigieron cargas de cuentas, reversas, abonos y reagendamientos. Liquidación y conciliación quedan vinculadas al expediente y revisión vigentes.
- El aviso de política deriva de referencia y versión: cerrar no acepta, refrescar la misma versión no reabre, y cambiar versión o referencia presenta el aviso que corresponde.
- No se modificaron CSS, endpoints, cuerpos de solicitudes ni reglas de pago/consentimiento.
- ESLint: **0 errores y 0 advertencias**. Node: **40 pruebas aprobadas**, incluidas cuatro de respuestas fuera de orden/cancelación. Build correcto; permanece la advertencia de tamaño.
- Navegador React real con **fetch simulado**, sin BD: **11 comprobaciones aprobadas** sobre respuestas obsoletas, cierre/reapertura, aceptación, versión y referencia. No son integración con PostgreSQL ni E2E de negocio.
- La integración real React/Django/PostgreSQL se repitió con los formularios React de creación y edición bancaria: **23 comprobaciones aprobadas** con el backend actualizado y escrituras comprobadas en la copia. Un ensayo intermedio recibió el 409 de negocio por porcentaje sin cambios; se corrigió el dato del ensayo, sin eludir esa regla.

Evidencias adicionales en el mismo respaldo externo:

- `navegador_ux_4b74d4e92c5d42abb715cf97523c6dda/resultado.json`, captura y harness conservado.
- `integracion_real_ca0377f060c14b02b631053609d48d10/browser_result.json` y `resultado.json`.
- `validacion_modulos_83fb3a47278a415aa0b49b5250e05590/`: resultados de suite, ESLint, Node, codificación fuente y build.

## Completado: recuperación de acceso y sesiones

- Restablecer contraseña bloquea primero el usuario y vuelve a validar el token antes del cambio, conservando expiración, mensajes y contrato del endpoint.
- Se invalidan todos sus tokens pendientes y se revocan sus sesiones DB vigentes, sin afectar otros usuarios. Los cambios quedan en una única transacción.
- Las sesiones nuevas se vinculan mediante HMAC a la identidad y contraseña que autorizó el login. Una sesión guardada tardíamente con la contraseña anterior se rechaza en la siguiente solicitud.
- Las sesiones antiguas sin marca siguen admitidas por compatibilidad y se revocan mediante el escaneo al restablecer. El escaneo tiene coste proporcional a las sesiones vigentes; no se añadió ningún esquema ni índice.
- Se añadieron **16 pruebas unitarias**. La suite conjunta, incluido el detector, terminó con **153 aprobadas** y sin acceso a BD real durante las unitarias.
- Integración contra la copia aislada: **18 comprobaciones reales** de identidad, login, reset, revocación, expiración y preservación de otro usuario; **3 comprobaciones de rollback con fallo inyectado** sobre transacciones PostgreSQL reales. Se distinguen esas tres del resto: usan un hook simulado para provocar el fallo.
- No se enviaron correos, no se modificó el `.env` ni las credenciales/contraseña/permisos del usuario PostgreSQL operativo. La instancia aislada quedó apagada.

Evidencia: `integracion_recuperacion_f0b144ac4d014d6587198ec447327f26/resultado.json` y script conservado, dentro del respaldo externo ya indicado.

## Completado: detector de codificación

- El signo ASCII `?` deja de tratarse como corrupción por estar entre letras: es sintaxis válida en expresiones regulares, ternarios y URLs.
- Se conserva la detección de secuencias de mojibake, carácter Unicode de reemplazo y bytes UTF-8 inválidos al leer archivos. Un `?` ASCII aislado no permite inferir automáticamente que hubo pérdida de texto.
- Cuatro pruebas nuevas cubren ambos falsos positivos, mojibake, reemplazo Unicode, UTF-8 inválido, acentos y BOM.
- Revisión fuente: **264 archivos**, sin sospechosos ni inválidos. El chequeo no imprimió datos privados de PostgreSQL; las pruebas nuevas son offline.

## Estado histórico de la tanda anterior

- CSRF: commit dedicado `e6c1f36`.
- Frontend asíncrono: commit `114cd7e`.
- Recuperación y sesiones: commit `1d0184e`.
- Validación conjunta conservada: **153 pruebas backend**, **40 Node**, **ESLint 0/0**, compilación correcta; no se declara aprobación de pagos reales ni de todos los flujos E2E.
- En esa tanda no se publicaron ni desplegaron cambios. El baseline sigue en el historial; las pruebas con escritura se ejecutaron únicamente en la copia aislada y los servidores de aquellos ensayos quedaron apagados. La continuación posterior usa otra instancia temporal independiente.

## Completado: recorrido API de negocio aislado

- `tools/e2e_api_aislado.py` y `tools/e2e_ciclo_aislado.py` conservan un recorrido repetible de **116 comprobaciones aprobadas** mediante HTTP, sesiones, CSRF y PostgreSQL reales de la copia. No se parchean controladores ni modelos de negocio.
- Incluye registro y validación profesional; documento inválido, descarga privada, rechazo y corrección; reserva de entrevista y rechazo de aprobación prematura; propuesta, corrección comercial, aceptación y publicación; solicitud empresarial, autoasignación y rechazo del duplicado; asociación, condiciones, contratación, reagendamiento, entregas observadas/corregidas/aceptadas, reclamo, cierre, retroalimentación privada y liberación. Un segundo contrato verifica cancelación y reversa.
- Se usa un PDF sintético como comprobante de transferencia y verificación administrativa. La actividad económica y entrevista son simuladas; el reloj del servidor de prueba se adelanta para respetar las restricciones temporales y se restablece al finalizar. La reversa conserva el estado de negocio `SIMULADA`. No acredita transferencias, entrevistas humanas, reembolsos o envíos reales.
- El runner exige origen loopback, puertos ajenos a 8000/5432, evidencia fuera del repositorio y guardia de instancia/puerto. No usa proxies ni sigue redirecciones. El servidor temporal valida además el directorio del cluster restaurado y bloquea red saliente, salvo su PostgreSQL independiente.
- No es un recorrido completo de todas las acciones a través de la interfaz. Las verificaciones de navegador, CSRF, carga y teclado se registran por separado; no se presentan como cobertura visual de cada transición de negocio.
- Evidencia: `continuacion_ec5fd1bf356e455c80591b980d4dbc44/api_e2e_7d09f243c08e407cb9cddbc5df71ce1e/resultado.json`. Los ensayos de desarrollo de 25 y 94 comprobaciones se conservan aparte y no se suman al recorrido repetible.

## Completado: carga gradual y cobertura local

- JMeter **5.6.3** ejecutado contra la copia: etapas de 1, 2 y 4 usuarios durante 8 segundos, con rampa de 3 segundos y pausa de 1 segundo. **38 muestras HTTP, 0 errores**; p95 por etapa: 33/134/135 ms. Solo GET de CSRF y marketplace, sin autenticación ni escrituras. Son muestras pequeñas de lectura, no una medición de capacidad productiva ni de concurrencia económica.
- Evidencia JMeter: `continuacion_ec5fd1bf356e455c80591b980d4dbc44/quality_047b651fb75c4b0ca9be12f7ef0d5d72`, con JTL sin cuerpos/cabeceras, logs y resumen.
- Cobertura Python real de las 172 pruebas unitarias: **3218/7059 líneas y 200/1870 ramas**, 139 archivos fuente; no incluye pruebas, migraciones ni archivos privados. El servidor HTTP de los recorridos previos no estaba instrumentado y no se le atribuye esa cobertura.
- LCOV nativo de las 43 pruebas Node: cinco módulos de helpers/rutas, **97,33 % líneas y 91,58 % ramas de esos cinco módulos**. No representa toda la aplicación React ni cobertura JSX del navegador.
- Informes externos: `coverage_python_unit_1e5e3e2d4ea84477a3fe5615c3ed079d/coverage.xml` y `coverage_node_root_final_a0edbb17c6bb4a168c3a9a11a080c7f8/lcov.info`, dentro de la continuación. `tools/quality/COBERTURA.md` explica su alcance y reproducción.
- SonarQube sí se ejecutó localmente; el resultado inicial fue ERROR. El reanálisis de las correcciones y los informes nuevos sigue pendiente; no se declara un gate aprobado.

## Estado de la tanda anterior (conservado)

El estado vigente y las evidencias posteriores se registran al inicio de este documento; los pendientes de esta tanda no sustituyen esos resultados.

- Publicados en `refactor/skilly`: límites (`23841cc`), carga por ruta (`3bb6740`), política TLS/formulario (`4beb4d7`) y recorrido API aislado (`688b30f`), además de los commits anteriores. `master` conserva la referencia inicial.
- Verificadas las mejoras visuales, de navegación y foco descritas en el cierre de interfaz más abajo. Se conservan capturas antes/después y pruebas de navegador fuera de Git.
- Falta reanalizar el código actual con SonarQube y distinguir los hallazgos resueltos de la deuda restante. No se reducirá el umbral ni se suprimirán reglas para obtener aprobación.
- Pendientes de cobertura: backend compartido de límites en varios trabajadores, recorrido completo de negocio mediante UI y validación humana/dispositivos adicionales. El recorrido API y los casos de navegador enumerados no acreditan esos alcances.
- React/Django y PostgreSQL temporales quedaron cerrados tras los ensayos. Se comprobó que el servidor original del puerto8000 seguía activo; no se solicitó detenerlo ni se escribió en su base. SonarQube local se conserva activo para el próximo análisis autenticado.
- La auditoría definitiva de los 22 documentos y los 2 Excel continúa reservada a confirmación expresa del usuario.

## Exportación de Sonar y bloqueo autenticado actual

- Se volvió a leer la última exportación sanitizada. Gate **ERROR**: cobertura nueva0/mínimo80 e incidencias nuevas425/máximo0; duplicación nueva1,63251/máximo3 está OK. La muestra guardada es de100 sobre623, más un filtro prioritario independiente de3 hallazgos. No se presenta esa muestra como clasificación total.
- El exportador se corrigió para paginar, clasificar, consultar advertencias/alcance/código nuevo e identificar el proyecto por API. El gate se solicita por `analysisId`; se registra si las medidas actuales pertenecen al mismo snapshot. No guarda contexto bruto ni secretos y rechaza tareas de otra clave. **11 comprobaciones con API simulada aprobadas**, sin atribuirlas a Sonar real.
- La clave configurada y el informe del scanner son `Skilly`. El nombre «Habilidoso» no figura en la exportación disponible y aún no se ha confirmado mediante API; no se creó otro proyecto ni se cambió la clave.
- La API local responde UP, pero componentes/incidencias/código nuevo requieren autenticación(401). El usuario indicó que ahora no puede ejecutar la exportación completa con entrada oculta. Quedan bloqueadas únicamente la clasificación de las623, las advertencias exactas, la definición efectiva de código nuevo y la importación/reanálisis autenticados. El resto del trabajo continúa.
- Se separaron pruebas de producción en el alcance de Sonar y se excluyeron secretos/cargas privadas; no se añadió ninguna exclusión de cobertura de código productivo. Los patrones de pruebas se contrastaron con los29 archivos de pruebas backend existentes. No se cambió el gate ni la referencia de código nuevo.
- `tools/quality/RESULTADOS_LOCALES.md` conserva condiciones, clasificación parcial y límites; `README.md` describe el exportador y los informes reales. Ninguno constituye la auditoría documental final reservada.

## Completado: interfaz y correcciones de mantenibilidad verificables

- Mejorada la jerarquía, contraste, espaciado y adaptación móvil en acceso/registro, portal, disponibilidad, seguimiento y módulos administrativos. La navegación administrativa móvil se desplaza dentro de su fila y centra el módulo activo. Se mantienen rutas, textos de negocio y acciones HTTP.
- Enlace para saltar al contenido; estados de contraseña explícitos; foco visible y movimiento reducido. Los diálogos comparten gestión de foco inicial, Tab/Shift+Tab, Escape bloqueado cuando corresponde, ventanas anidadas, retorno de foco y restauración de scroll.
- Se consolidaron las **13 hojas CSS** modificadas: PostCSS encuentra **0 selectores repetidos por contexto**. Se conservaron unidades, expresiones, media queries, especificidad y valores efectivos; no se renombraron selectores ni silenciaron reglas para esconder duplicados.
- Comparación real contra el backup del diseño anterior a la consolidación: **76 combinaciones**, con 390/650/768/1366 px, registro/recuperación y modales administrativos/profesionales: **0 diferencias** en los estilos y geometrías medidos. No es una certificación de todos los estados o dispositivos.
- Capturas finales de **16 pantallas en escritorio y móvil(32 imágenes)**: ningún desborde de página ni campo visible sin etiqueta en esas vistas. Se conservan las32 capturas originales previas al rediseño. **15 comprobaciones finales de teclado aprobadas**; otras 11 del hook real dentro de un harness React se incluyen en las 44 del navegador instrumentado.
- S7718: nombres de errores normalizados; S7786: TypeError cuando la API entrega observaciones con tipo incorrecto; S6772: separación JSX explícita. Los estados usan output nativo dentro de sus contenedores. Los fondos decorativos de Portal se declaran de presentación, con Escape y cierre explícito accesibles. Los diálogos ARIA se conservan; no se declara resuelta toda S6819 sin revisión y reanálisis.
- Se extrajeron límites de adjuntos y lectores de formatos API sin cambiar confirmación, prioridades, endpoints, payloads o mensajes. **7 pruebas nuevas** verifican límites exactos y un byte por encima, cero archivos, formatos, listas vacías y prioridad de respuesta. Las funciones complejas quedan simplificadas; su clasificación S3776 pendiente depende del reanálisis.
- **50/50 pruebas Node**, ESLint completo 0/0 y compilación correcta. El bloque principal final mide **226064 bytes(gzip70329 con Node/zlib)** frente a636302/gzip159420 iniciales. No hay bloques JS mayores de500 kB; las métricas de inicio por ruta anteriores al rediseño se conservan en su evidencia original.
- Evidencia: `capturas_antes_1793929744325`, `capturas_final_1793987841409`, `capturas_css_comparacion_1793987797863`, `capturas_css_intermedio_1793987870599` y `capturas_teclado_1793987865781`, dentro de la continuación externa original. Los intentos de comparación anteriores se conservan: se corrigió la espera del test y se seleccionó Todas para abrir un expediente existente en la copia; no se cambiaron datos para hacerlos pasar.

## Completado: cobertura ampliada real, importación pendiente

- Nuevo Django instrumentado en otro puerto temporal, con verificación de `data_directory`, base/esquema/rol/puerto, red restringida y archivos/reloj propios. **117 comprobaciones API aprobadas**: incluye un409 previsto por bloque de entrevista ocupado y el intento siguiente válido. Reloj restablecido y servidor cerrado normalmente(código0); se mantuvo separado del de50144 y del original.
- `coverage.py combine` unió los datos unitarios y de ese servidor: **4690/7059 líneas y683/1870 ramas**, los mismos139 archivos productivos en el denominador. No se midió al cliente para atribuirle ejecución del servidor.
- Navegador: **44/44 comprobaciones**, fuentes congeladas, LCOV estándar de **57 módulos(49 JSX)**: **10046/21995 líneas,423/668 ramas y88/519 funciones** de ese conjunto. Sin dependencias, rutas inválidas, cambios de hashes ni pérdidas CDP. Se omitió únicamente el sourcemap intermedio no verificable de rutasPantalla; el LCOV Node lo cubre, sin excluirlo del análisis.
- Node50 produce LCOV de7 helpers:97,58 % líneas y92,86 % ramas en esos módulos. No se atribuyen esas cifras a todo React. Se adjuntan Node y navegador como dos rutas LCOV estándar, sin inventar ni modificar contadores.
- Informes activos en `.skilly-coverage-result.tmp`: XML combinado `continuacion_c2998d287c4d4dd6a1900e8b0fdfad71/coverage_combined/coverage.xml`; Node `coverage_node_final_1f159d0de4e748f19ad1c8b10a851139/lcov.info`; navegador `coverage_browser_8a599de9e53044518574486561c23592/lcov.info`, estos dos últimos dentro de la continuación original.
- **Pendiente por autenticación:** importar los informes mediante otro scanner y comprobar en API advertencias, alcance y cobertura efectiva. El gate conocido sigue ERROR; estos informes no acreditan80% de código nuevo ni aprobación de SonarQube. El ejecutor local está preparado para ello cuando el usuario pueda introducir su token oculto.

## Cierre operativo de esta continuación

- Publicaciones verificadas adicionales: recorrido API `688b30f`, herramientas de calidad/exportación `98321fe` e interfaz/mantenibilidad `29808e5`, siempre en el repositorio privado y en `refactor/skilly`, con auditoría staged sin hallazgos. No hubo merge ni reescritura de master.
- Cerrados y comprobados los puertos propios 50144/50145/57647. El proceso Django instrumentado 62565 ya había terminado normalmente. Puerto original 8000 activo antes y después. Evidencia: `continuacion_ec5fd1bf356e455c80591b980d4dbc44/cierre_verificado_caf66a91b11f44ff8bc4d383d20011e2.json`.
- Se conserva SonarQube local 9000, los informes y los punteros ignorados necesarios para analizar después. No se retiene token en esos archivos. La configuración operativa y los archivos privados se recuperan desde el respaldo externo, no desde Git.
- No se certifican pagos reales, entrevista humana, capacidad productiva, todos los recorridos mediante UI ni un gate verde. El intento de autorización independiente del proveedor sandbox quedó preparado sin ejecución confirmada; el checkout HTTPS sin tarjeta y las simulaciones/mocks ya descritos se distinguen de un pago autorizado.
- Los 22 Word y 2 Excel siguen sin modificación; la auditoría documental final no se ha iniciado.

### Auditoría final del repositorio y respaldos técnicos

- Sobre `93b527d`, Gitleaks8.30.1 revisó todas las referencias y candidatos: **0 hallazgos**; comparación con secretos operativos: **0 coincidencias**; **0 archivos prohibidos**. Git limpio y SHA de master/refactor verificados contra GitHub.
- `.env` operativo coincide con el respaldo; **18 archivos media y3entregas privadas** coinciden por hash. El dump fue leído completamente por pg_restore sin conectarse a una base; se conserva la restauración aislada comprobada anteriormente. No se alteró la base original.
- Auxiliares y resultados se preservaron fuera del repositorio antes de retirar únicamente los temporales propios. La copia se adaptó a rutas largas de Windows sin cambiar permisos ni configuración global; el intento parcial también se conserva.
- Evidencia sanitizada: `auditoria_final_1fc1754d1ee94cfead177eb0eb303519/resultado.json` bajo el respaldo externo. Los auxiliares del primer intento quedaron en `auditoria_final_ecb615766962494ea39af18cf78d2964/helpers_preservados`; los originales de la evidencia no se sobrescribieron.
- Esta es la auditoría técnica del código y sus respaldos; no es la auditoría documental reservada de Word/Excel. El análisis autenticado de Sonar y sus hallazgos restantes siguen pendientes en los términos descritos.
