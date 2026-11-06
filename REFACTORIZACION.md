# Registro de refactorización de SKILLY

Este es el registro técnico de trabajo. La auditoría documental definitiva de los 22 documentos y los 2 Excel no se ha iniciado y queda reservada a confirmación expresa del usuario.

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

Se conservan rutas, puertos configurados, contratos de API y reglas de negocio. Todo el trabajo es local; no se publica ni despliega.

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

## Estado de cierre de esta tanda

- CSRF: commit dedicado `e6c1f36`.
- Frontend asíncrono: commit `114cd7e`.
- Recuperación y sesiones: commit `1d0184e`.
- Validación conjunta conservada: **153 pruebas backend**, **40 Node**, **ESLint 0/0**, compilación correcta; no se declara aprobación de pagos reales ni de todos los flujos E2E.
- No se publicaron ni desplegaron cambios. El baseline sigue en el historial; las pruebas con escritura se ejecutaron únicamente en la copia aislada y todos sus servidores temporales quedaron apagados.

## Pendiente y límites

- Revisar límites de intentos de autenticación/recuperación y comportamiento bajo carga antes de introducir controles adicionales.
- Evaluar carga diferida por pantalla: el build aún advierte de un bloque JavaScript superior a 500 kB.
- No se ejecutaron SonarQube ni JMeter. No se declara aprobación de esos controles ni de todos los flujos E2E del proyecto.
- Los 23 casos de navegador cubren el alcance CSRF descrito; no equivalen a una certificación de pagos reales, flujos completos del negocio o compatibilidad visual en todos los dispositivos.
