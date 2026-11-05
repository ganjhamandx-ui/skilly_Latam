# Registro de refactorización de SKILLY

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

## En verificación

- Cargas asíncronas React: cancelación de respuestas obsoletas, estado por expediente/revisión y política por referencia/versión.
- Detector de codificación: eliminar falsos positivos de sintaxis sin perder detección de mojibake real.

## Pendiente y límites

- Revisar revocación de otras sesiones/tokens tras restablecer contraseña y límites de intentos, con pruebas aisladas antes de cualquier cambio persistente.
- Evaluar carga diferida por pantalla: el build aún advierte de un bloque JavaScript superior a 500 kB.
- No se ejecutaron SonarQube ni JMeter. No se declara aprobación de esos controles ni de todos los flujos E2E del proyecto.
- Los 23 casos de navegador cubren el alcance CSRF descrito; no equivalen a una certificación de pagos reales, flujos completos del negocio o compatibilidad visual en todos los dispositivos.
