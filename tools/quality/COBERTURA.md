# Cobertura medida, no inferida del número de pruebas

Los informes se generan ejecutando las pruebas con instrumentación real. Su existencia no aprueba un quality gate ni convierte pruebas de helpers en cobertura de toda la interfaz.

## Python

La dependencia de desarrollo está fijada en `requirements-dev.txt`: coverage.py **7.17.2**, instalada solamente en `.venv`. No se cambian las dependencias de producción.

Ejecutar `tools/quality/cobertura_python.py unitarias --output <carpeta-absoluta-nueva>` desde el Python del entorno virtual. La carpeta debe quedar bajo el respaldo externo de SKILLY. El ejecutor bloquea sockets, psycopg y conexiones Django, usa base dummy, correo en memoria y archivos temporales. Descubre las apps locales y los módulos `pruebas/test*.py` del checkout actual.

Produce `.coverage`, `coverage.xml` compatible con Cobertura, `coverage.json`, `tests.log` saneado y `resultado.json`. Mide líneas y ramas del backend, omitiendo pruebas, migraciones y documentos cargados; los archivos de producción no ejecutados permanecen en el denominador. No excluye líneas para elevar artificialmente la métrica.

Ejecución observada: **172 pruebas aprobadas**, **3218/7059 líneas** y **200/1870 ramas**, 139 archivos. Evidencia: carpeta `coverage_python_unit_1e5e3e2d4ea84477a3fe5615c3ed079d` bajo la continuación externa `continuacion_ec5fd1bf356e455c80591b980d4dbc44`.

Para importar: `sonar.python.coverage.reportPaths` debe apuntar al `coverage.xml` generado. El XML declara `backend` como fuente y los nombres de clase relativos a esa carpeta. Clasificar las pruebas como pruebas en Sonar evita tratarlas erróneamente como código de producción; no debe eliminarse código productivo de cobertura para obtener un gate verde.

### API E2E y servidor existente

Instrumentar el **cliente** `e2e_api_aislado.py` no mide el código Django ejecutado por otro proceso. El servidor ya activo en 50144 no se instrumentó ni reinició durante esta tarea.

El modo `servidor --context <contexto> --script <script-externo> --output <carpeta-nueva>` instrumenta un proceso nuevo. Exige contexto y script bajo el respaldo, fuera del repositorio, origen loopback y PostgreSQL diferente de 5432 que coincida con el entorno del proceso. El script de arranque sigue siendo responsable de verificar el cluster real y bloquear pagos/correos antes de abrir HTTP.

Se guarda un checkpoint cada segundo. Tras las solicitudes, esperar un checkpoint y cerrar el proceso de forma controlada; un cierre forzado puede perder el último segundo. `informes --output <carpeta-existente>` convierte únicamente los datos registrados por ese proceso a XML/JSON. No añade cobertura de otros procesos, del cliente ni de respuestas simuladas. No se ha ejecutado ni acreditado todavía cobertura E2E de servidor con ese modo.

## JavaScript

El Node **24.11.1** instalado ya incluye el reporter oficial `node:test/reporters.lcov`. No fue necesario instalar c8 ni convertir contadores V8 manualmente.

Ejecutar `node tools/quality/cobertura_node.mjs <carpeta-absoluta-nueva>`. Usa `--experimental-test-coverage` y el reporter LCOV nativo, además de `spec` para conservar los resultados. Se ejecuta desde la raíz para que las rutas del LCOV comiencen en `frontend/src`.

Ejecución observada: **43 pruebas aprobadas**, ocho archivos de prueba y cinco módulos fuente instrumentados: aviso de política, control de consultas, condiciones, agenda y rutas. El reporte nativo mostró **97,33% de líneas y 91,58% de ramas en esos cinco módulos**; esos porcentajes no representan todo el frontend. No se cubrieron JSX ni rutas dinámicas no cargadas por estas pruebas.

Evidencia final compatible con la raíz del proyecto: carpeta `coverage_node_root_final_a0edbb17c6bb4a168c3a9a11a080c7f8`, con `lcov.info`, log y resultado (43 pruebas, 43 aprobadas). `sonar.javascript.lcov.reportPaths` debe apuntar a ese LCOV. El primer ensayo `coverage_node_3fcd0e2142c346c3a4ebc1c969ca7229` se conserva, pero sus rutas estaban referidas a `frontend`; no se alteraron sus contadores para reutilizarlo.

## Referencias primarias

- [coverage.py: ejecución y ramas](https://coverage.readthedocs.io/en/7.11.3/commands/cmd_run.html)
- [coverage.py: XML compatible con Cobertura](https://coverage.readthedocs.io/en/7.12.0/commands/cmd_xml.html)
- [Node: cobertura del test runner y reporter LCOV](https://nodejs.org/download/release/latest-jod/docs/api/test.html#coverage-reporters)
- [SonarQube: parámetros de cobertura Python y JavaScript](https://docs.sonarsource.com/sonarqube-community-build/analyzing-source-code/test-coverage/test-coverage-parameters)
