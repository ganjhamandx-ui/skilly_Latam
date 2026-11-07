# Registro de refactorización de SKILLY

Este es el registro técnico de trabajo. La auditoría documental definitiva de los 22 documentos y los 2 Excel no se ha iniciado y queda reservada a confirmación expresa del usuario.

## Prioridad vigente: reparación funcional y seguridad

- SonarQube queda **pospuesto por indicación del usuario** hasta nueva solicitud expresa. No se ejecutan scanners, exportadores, solicitudes de token ni ajustes destinados exclusivamente al Quality Gate. Se preservan herramientas y resultados anteriores; el último gate conocido sigue ERROR, sin aprobación.
- Las menciones posteriores a autenticación, importación y reanálisis describen pendientes históricos, no acciones previstas durante esta etapa. Las vulnerabilidades y errores reales identificados siguen dentro del alcance.
- Se continúa con correcciones, recorridos completos mediante interfaz, permisos, estados de error y adaptación móvil, en la copia aislada. Se conserva `master`, se publican cambios verificados en `refactor/skilly` y no se modifican Word ni Excel.

## Recuperación del trabajo interrumpido (7 de noviembre)

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

## Estado actual y pendientes verificables

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
