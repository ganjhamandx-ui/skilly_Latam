# Calidad local y lectura gradual aislada

`ejecutar_lectura_aislada.ps1` ejecuta JMeter local sin autenticación ni escrituras. Rechaza puertos operativos, exige la guardia `/__isolated/health` y un identificador de ejecución esperado. Cada etapa vuelve a verificar la guardia; el propio plan también la comprueba antes de enviar solicitudes.

El plan usa 1, 2 y 4 usuarios en etapas secuenciales de 8 segundos, rampa de 3 segundos y pausas de 1 segundo por muestra. Solo solicita CSRF público y marketplace. No guarda cuerpos ni cabeceras de petición/respuesta. Se detiene ante errores y limita el tiempo de las etapas nuevas. No representa una prueba de capacidad, concurrencia de negocio o pagos.

Las rutas de herramientas son instalaciones locales observadas en este equipo. La salida debe ser una carpeta nueva dentro del respaldo externo de SKILLY; no se sobrescriben evidencias existentes. Revisar el JSON/JTL generado antes de declarar una ejecución correcta.

SonarQube está configurado para `http://localhost:9000`. Su instalación y la del scanner se detectaron localmente, pero su disponibilidad/autorización debe comprobarse antes de analizar. Este recurso no envía código a servicios externos ni contiene tokens.

`sonar_local.ps1` fija el destino en `127.0.0.1:9000`, exige estado `UP` y usa `SONAR_TOKEN` solo mediante el entorno del proceso. Si falta, puede ejecutarse con `-SolicitarToken` en una terminal propia para introducir el token con entrada oculta; no debe pegarse en el chat, en argumentos ni en archivos de Git. El script restaura la variable previa y libera el búfer de entrada al terminar. La presencia del scanner o una ejecución `--version` no constituye un análisis SonarQube aprobado.

La clave existente sigue siendo `Skilly`: se contrasta con `sonar-project.properties`, `/api/components/show` y la tarea del scanner. El nombre visible se obtiene de la API; no se deduce de su traducción en la interfaz. El script no crea proyectos ni cambia claves, referencias de código nuevo o umbrales.

`-SoloResultados` consulta la tarea indicada por `report-task.txt` y el gate mediante su `analysisId`. Exporta todas las incidencias sin resolver con paginación (hasta 10000 y marca de integridad), clasificación por regla/gravedad/archivo, incidencias nuevas por separado, advertencias, alcance permitido del contexto del scanner, definición de código nuevo y medidas por archivo. No guarda contexto bruto, cuerpos de error ni fragmentos de fuente. Si no coincide la tarea con el proyecto, se detiene. Las medidas e incidencias son el estado actual de la API; se registra si el último análisis coincide con la tarea para evitar atribuirle otro snapshot.

`test_sonar_exportacion.ps1` verifica el exportador con API completamente simulada y salidas dentro de un backup temporal: paginación de 623 incidencias, 425 nuevas, vínculo del gate, identidad, saneamiento, restauración de entorno y rechazo de clave distinta/tarea fallida. Sus 11 comprobaciones no equivalen a un análisis real de SonarQube.

El scanner incorpora únicamente informes que existen: Cobertura Python y LCOV de Node/navegador indicados por `.skilly-coverage-result.tmp`. Generar esos informes no modifica por sí solo la cobertura registrada en Sonar: hace falta ejecutar y procesar otro análisis autenticado.
