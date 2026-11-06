# Resultados locales observados

## JMeter

- Herramienta ejecutada: Apache JMeter 5.6.3, Java Temurin 21.0.12.1.
- Destino verificado: `127.0.0.1:50144`, guardia `continuacion_ec5fd1bf356e455c80591b980d4dbc44`, PostgreSQL aislado en puerto 57647.
- Solo GET públicos de CSRF y marketplace, sin autenticación, escrituras, pagos o envíos.
- Etapas secuenciales de 8 segundos, rampa de 3 segundos, pausa de 1 segundo, máximo cuatro usuarios simultáneos. Tiempo total del ejecutor: **31,03 s**.

| Usuarios | Muestras HTTP | Errores | p95 (ms) | Máximo (ms) |
| --- | --- | --- | --- | --- |
| 1 | 6 | 0 | 33 | 33 |
| 2 | 11 | 0 | 134 | 134 |
| 4 | 21 | 0 | 135 | 157 |

Evidencia externa: `C:\Users\felip\Downloads\SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b\continuacion_ec5fd1bf356e455c80591b980d4dbc44\quality_047b651fb75c4b0ca9be12f7ef0d5d72`. Contiene JTL, logs de cada etapa y `resultado.json`. Los JTL no contienen cuerpos ni cabeceras de petición/respuesta. Los procesos JMeter terminaron.

Hubo un ensayo previo de una etapa que terminó con siete muestras totales y cero errores, pero el wrapper interpretó un código de salida nulo de PowerShell como fallo. Se corrigió el ejecutor y se usó una carpeta nueva para las tres etapas completas. No se sobrescribió ese ensayo.

Estos volúmenes son una comprobación gradual limitada de lectura del entorno aislado. No acreditan capacidad productiva, límites máximos, escrituras concurrentes ni flujos completos de negocio. Con tan pocas muestras, los percentiles son orientativos.

## SonarQube

- Se encontraron SonarQube **26.9.0.129388** y SonarScanner CLI **8.1.0.6389** locales. El scanner respondió correctamente a `--version`.
- SonarQube se inició oculto desde su instalación existente, solicitando enlace de web/búsqueda a loopback mediante opciones de proceso. No se editaron archivos de configuración ni cuentas.
- `/api/system/status` respondió **UP**, versión 26.9.0.129388.
- `/api/authentication/validate` anónimo respondió `valid=false`; `/api/components/show?component=Skilly` respondió **401**. No existe `SONAR_TOKEN` en el entorno del proceso ni configuración activa de token en los archivos consultados.
- El bloqueo inicial de autenticación fue resuelto por el usuario introduciendo un token de forma oculta en su terminal. No se probaron credenciales por defecto ni se envió código a servicios externos.
- El primer análisis terminó y se procesó correctamente, pero su quality gate fue **ERROR**: cobertura recibida 0 %, 425 incidencias nuevas; métricas totales de 1 bug, 2 vulnerabilidades, 620 observaciones de mantenibilidad y 1,6 % de líneas duplicadas. Esto no constituye aprobación de calidad.
- La exportación prioritaria identificó `python:S4830` y `python:S4423` en el cliente TLS Webpay y `javascript:S9011` en el botón de envío bancario. Se hicieron explícitas la verificación de CA/hostname y la versión mínima TLS, y el tipo submit del botón. Tres regresiones TLS nuevas pasan dentro de la suite de 172 pruebas. La clasificación del servidor tras las correcciones requiere repetir el análisis; no se silencian reglas ni se cambian umbrales.
- Evidencia inicial: `sonar_analisis_9d2f489d722040aba1d64de52bdf8316/resultado.json`. Exportación prioritaria del mismo análisis: `sonar_analisis_d0fcb003da31497781e68de7874bbb78/resultado.json`, dentro de la continuación externa.
- Se generaron después informes reales Python Cobertura y Node LCOV, documentados en `COBERTURA.md`. El ejecutor adjunta los informes locales indicados por `.skilly-coverage-result.tmp`; no inventa cobertura de JSX ni del servidor HTTP ya ejecutado sin instrumentación.
- El servicio se mantiene localmente activo para configurar acceso, por instrucción del agente principal. El lanzador iniciado por esta tarea fue PID **57180**; no confundirlo con servidores de la aplicación.
- Evidencia: la carpeta hermana `quality_sonar_5282812b78ee4dd497fecc34d1176c3ba`, con `resultado.json` y logs de inicio. Para cerrar, primero comprobar que el PID sigue correspondiendo al lanzador de esta instancia de SonarQube y detener únicamente ese árbol; nunca terminar todos los procesos Java.

El usuario puede introducir un token de SonarQube **en su terminal local** mediante `tools/quality/sonar_local.ps1 -SolicitarToken`. Usa entrada oculta, verifica autenticación antes del scanner, transmite el token por entorno temporal y sanea su salida. No pegarlo en el chat, argumentos, `.env` operativo ni Git.

`-SoloResultados` exporta el análisis existente sin repetir el scanner. Los informes guardan únicamente metadatos, métricas y ubicaciones; no incluyen fragmentos de código ni valores de credenciales. Los resultados posteriores quedan en carpetas nuevas y no sobrescriben la evidencia previa.

### Auditoría del exportador y alcance disponible

La última exportación disponible corresponde al mismo análisis inicial: gate ERROR por `new_coverage=0` (mínimo80) y `new_violations=425` (máximo0); `new_duplicated_lines_density=1.63251` pasa el máximo3. El exportador anterior conservó solo las primeras100 de623 incidencias. Las cifras siguientes describen **esa muestra**, no el total:

| Regla | Cantidad en las100 |
| --- | ---: |
| css:S4666 | 77 |
| javascript:S6819 | 13 |
| javascript:S7718 | 4 |
| javascript:S3776 | 2 |
| javascript:S3358 / S7786 / S6772 / S6848 | 1 cada una |

La muestra contiene93 MAJOR,5 MINOR y2 CRITICAL; estas dos últimas son observaciones de complejidad. Las dos vulnerabilidades CRITICAL y el bug MAJOR se consultaron mediante el filtro prioritario independiente, no están incluidos en esta clasificación de100. Los77S4666 de la muestra corresponden a Administracion(22), PortalProfesional(18), AccesoProfesional(16), CuentasBancariasAdministracion(9), Disponibilidad(8) y AvisoPoliticaCancelacionE3(4).

Se corrigió el exportador: identidad verificada, gate vinculado a analysisId, contexto permitido, advertencias, definición de código nuevo, paginación y clasificación completa. **11 pruebas con API simulada aprobadas**. La API real anónima sigue respondiendo401 en componentes/incidencias/código nuevo; el usuario indicó que ahora no puede repetir la exportación con entrada oculta. Por ello siguen pendientes las advertencias exactas, la definición efectiva de código nuevo y la clasificación de las623. No se infieren ni se cambian estos valores. El nombre visible «Habilidoso» tampoco se ha vinculado por API a la clave `Skilly`.

La clasificación correcta de pruebas en `sonar.tests`/`sonar.test.inclusions` separa las 29 fuentes backend de pruebas y las pruebas frontend de producción; se comprobó que los patrones actuales no incluyen otros archivos productivos. Las exclusiones de `.env`, claves y cargas privadas evitan enviar secretos al analizador local. No se añadió `sonar.coverage.exclusions`, ni se movió la referencia de código nuevo ni se rebajó el gate. Los informes de cobertura posteriores aún necesitan un nuevo análisis autenticado para comprobar su importación efectiva.

### Informes preparados después del análisis fallido

- Python: datos de172 unitarias y117 comprobaciones HTTP del servidor instrumentado, combinados con coverage.py:4690/7059 líneas y683/1870 ramas, sin cambiar139 archivos del denominador.
- Node:50 pruebas aprobadas, siete helpers,97,58 % líneas y92,86 % ramas de esos módulos.
- Navegador:44comprobaciones aprobadas,57 fuentes(49 JSX),10046/21995 líneas y423/668 ramas de ese conjunto. Solo el sourcemap intermedio de rutasPantalla se omite; se conserva su cobertura Node sin excluir el archivo de Sonar.

Las rutas XML y LCOV reales quedaron en `.skilly-coverage-result.tmp`. El scanner recibirá el XML combinado y ambos LCOV mediante la propiedad estándar. **La importación efectiva y las nuevas condiciones del gate siguen bloqueadas por autenticación**, no se han observado todavía. `COBERTURA.md` y `COBERTURA_NAVEGADOR.md` conservan detalle, fuentes, evidencias y limitaciones.
