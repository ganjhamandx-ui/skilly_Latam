# Recorrido API aislado de SKILLY

`e2e_api_aislado.py` ejecuta un recorrido completo por la API, con actores HTTP separados y CSRF real. No es una automatización de todas las pantallas. `e2e_ciclo_aislado.py` contiene los escenarios de contratación/cierre y cancelación/reversa usados por el runner.

## Precondiciones

- Restaurar y verificar un respaldo en un cluster PostgreSQL independiente. El servidor de prueba debe comprobar su `data_directory`, base, esquema, usuario y puerto antes de aceptar peticiones; una respuesta de health por sí sola no prueba el aislamiento de un servidor ajeno.
- Servir Django con archivos privados y correo de prueba, bloqueando cualquier transporte externo de pagos y envíos. El runner no sustituye esas guardias del proceso servidor.
- Preparar fuera del repositorio un contexto JSON con `run_dir`, `run_id`, `backend_origin` y `database_port`. El origen debe ser loopback con puerto explícito y distinto de 8000/5432; PostgreSQL tampoco puede usar 5432.
- En `run_dir`, conservar `fixture_privado.json` con las cuentas sintéticas `admin` (`email`, `password`), el `origin` de React y el control privado `control`. No usar cuentas o contraseñas operativas ni incorporar esa fixture a Git.
- El servidor temporal debe ofrecer `/__isolated/health` con `isolated=true`, `run_id` y `database_port`, y `/__isolated/clock` mediante `X-Isolated-Control`. Esas rutas pertenecen al harness externo, no a las rutas del producto.

El harness y su configuración privada del ensayo realizado se conservaron en el respaldo externo. Estos scripts no crean automáticamente un servidor ni eligen una base de datos a partir del `.env` operativo.

## Ejecución y evidencia

Desde el Python del entorno virtual, ejecutar con rutas absolutas:

```powershell
& 'C:\Users\felip\Downloads\skilly\.venv\Scripts\python.exe' 'C:\Users\felip\Downloads\skilly\tools\e2e_api_aislado.py' --context 'C:\ruta-externa\contexto.json'
```

La cuenta profesional se crea con identidad sintética y contraseña aleatoria; su fixture queda únicamente en una carpeta externa nueva. El runner no sigue redirecciones ni usa proxies. Guarda etiquetas, estados, identificadores y resultados, sin cuerpos de respuesta, cabeceras, referencias firmadas ni credenciales. Restablece el reloj en `finally`; no declara éxito si ese restablecimiento falla.

La ejecución observada aprobó **116 comprobaciones**. Incluye revisión/corrección documental y comercial, publicación, solicitud empresarial, autoasignación, contratación, pago por transferencia con comprobante sintético, reagendamiento por consenso, entrega observada/corregida/aceptada, reclamo, cierre, retroalimentación privada, liberación y otro contrato cancelado con reversa explícitamente simulada. Se conservan las restricciones temporales de entrevista mediante un reloj de prueba; no se acredita una entrevista humana.

Evidencia: `continuacion_ec5fd1bf356e455c80591b980d4dbc44/api_e2e_7d09f243c08e407cb9cddbc5df71ce1e/resultado.json`, bajo el respaldo externo indicado en `REFACTORIZACION.md`. No hubo pagos, transferencias, reembolsos ni correos reales. El sandbox de Transbank y las comprobaciones de navegador se registran por separado.
