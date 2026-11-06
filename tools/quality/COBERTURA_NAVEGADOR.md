# Cobertura de navegador con fuentes originales

`cobertura_navegador.mjs` recoge contadores reales del motor V8 de Edge mediante CDP `Profiler.startPreciseCoverage` (funciones y bloques). Obtiene los scripts ejecutados mediante `Debugger.getScriptSource` y convierte sus contadores con `v8-to-istanbul`, `istanbul-lib-coverage`, `istanbul-lib-report` e `istanbul-reports`. Esas dependencias son herramientas de desarrollo del frontend, no dependencias de producción.

Versiones instaladas y observadas: `v8-to-istanbul` 9.3.0, `istanbul-lib-coverage` 3.2.2, `istanbul-lib-report` 3.0.1, `istanbul-reports` 3.2.0 y `convert-source-map` 2.0.0. Esta última se declara explícitamente aunque ya estuviera instalada como dependencia transitiva. La instalación se realizó con scripts npm desactivados.

## Guardias y ejecución

```powershell
& 'C:\Program Files\nodejs\node.exe' 'C:\Users\felip\Downloads\skilly\tools\quality\cobertura_navegador.mjs' 'C:\Users\felip\Downloads\skilly\.skilly-active-context.tmp'
```

El contexto debe identificar la instancia aislada, su carpeta externa de evidencias, React, Django y un puerto PostgreSQL distinto de 5432. Se comprueba `/__isolated/health` antes de lanzar Edge. Las peticiones del navegador solo pueden ir a los dos orígenes loopback exactos del contexto; no se siguen redirecciones en la comprobación inicial. La fixture privada se lee únicamente en memoria. El perfil y los informes se escriben en una carpeta nueva fuera del repositorio.

Se recorren las pantallas públicas, las once pantallas administrativas y el portal profesional con login/logout de React y Django reales. También se verifica espera de módulo, fallo de importación inyectado, recuperación manual, semántica del botón de contraseña y foco de modales. Un harness React temporal, creado únicamente en el DOM del ensayo, ejercita el hook real `useDialogoAccesible`: foco inicial, Tab/Shift+Tab, controles ocultos/deshabilitados, control añadido dinámicamente, Escape bloqueado, ventanas anidadas, retorno de foco, restauración de scroll y panel sin controles. El harness no modifica archivos ni reglas del producto.

## Correspondencia de cobertura

- Se recoge cobertura antes de cada navegación, sin atribuir contadores de otro proceso o de Node al navegador.
- Se conserva la fuente desde `Debugger.scriptParsed`, antes de que V8 pueda descartarla al cambiar de documento. Una comprobación final de hashes impide aprobar un recorrido si cambian las fuentes durante su ejecución.
- Solo se convierten scripts de `frontend/src`. Se descartan dependencias, evaluaciones del harness y código interno del navegador. Esto no excluye fuentes productivas del análisis SonarQube: las que no se ejecuten seguirán sin cobertura en ese análisis.
- Cada transformación debe tener un sourcemap de una sola fuente cuyo `sourcesContent` coincida con el archivo local. Si no hay mapa, solo se acepta código idéntico al archivo original. Las conversiones no verificables se registran en `skipped`, sin inventar contadores.
- Se normaliza únicamente la referencia de archivo del sourcemap a su ruta local. No se cambian `mappings`, rangos, cantidades de ejecuciones ni porcentajes.
- Se valida que el archivo convertido sea el esperado y que sus declaraciones queden dentro del número real de líneas. Se conservan lotes V8, hashes de fuente, metadatos de conversión, JSON Istanbul, resumen y LCOV.

El reporte mide los módulos ejecutados por estos recorridos. No acredita cada transición de negocio desde la UI, compatibilidad entre navegadores ni una certificación de accesibilidad. El fallo de importación y el harness del hook son pruebas controladas; la autenticación y las consultas de las pantallas utilizan la instancia Django/PostgreSQL aislada real.

`--hook-only` permite diagnosticar solo los once casos del hook real en el harness temporal. Ese resultado declara `harness_only=true` y no se presenta como el recorrido de autenticación o de pantallas completas. El harness importa la misma instancia y versión de React que cargó Vite, para evitar falsos fallos por duplicar React.

Para importar en SonarQube se puede proporcionar este `lcov.info` junto con el LCOV de Node mediante `sonar.javascript.lcov.reportPaths` (rutas separadas por coma). No se debe reemplazar cobertura ausente por contadores ficticios ni excluir código válido para aumentar el porcentaje.

## Ejecución verificada

El recorrido final, con JavaScript congelado, aprobó **44 de 44 comprobaciones** y produjo LCOV de **57 archivos fuente, incluidos 49 JSX**. La comprobación de hashes encontró cero archivos modificados durante el recorrido; no hubo pérdidas de fuentes por descarte de contextos CDP, rutas LCOV inválidas ni archivos de `node_modules` en el informe.

En esos 57 archivos ejecutados se midieron **10046/21995 líneas (45,67 %)**, **423/668 ramas (63,32 %)** y **88/519 funciones (16,95 %)**. Estos porcentajes pertenecen a ese conjunto de archivos y recorridos; no son el porcentaje de todo React ni el de código nuevo que calculará SonarQube.

Evidencia externa: `continuacion_ec5fd1bf356e455c80591b980d4dbc44/coverage_browser_8a599de9e53044518574486561c23592`, bajo el respaldo indicado en `REFACTORIZACION.md`. Contiene `resultado.json`, `lcov.info`, JSON Istanbul, resumen, 23 lotes V8, metadatos de hashes/conversión y una copia exacta del ejecutor. No se sobrescribió ningún ensayo anterior.

La única fuente no convertida fue `frontend/src/rutasPantalla.mjs`: Vite entregó un sourcemap cuya fuente ya contiene reescrituras de imports dinámicos y no coincide con el archivo original. Sus 23 registros se omiten explícitamente, por lo que `coverage_conversion_complete=false`; no se fabricó otro mapa ni se editaron contadores para aprobar la comprobación. El LCOV independiente de Node cubre ese helper y se importa junto al informe de navegador. No se excluye el archivo del análisis SonarQube.

Los primeros ensayos detectaron errores del harness (exportación CommonJS de `createRoot` y una segunda instancia React al omitir la versión de Vite), no fallos del producto. Se corrigieron únicamente las importaciones del harness. Otro ensayo mostró registros CDP de scripts ya descartados al navegar; la caché temprana de fuentes corrigió esa pérdida. Todos los resultados parciales se conservaron aparte y no se suman a las 44 comprobaciones finales. Este reporte no constituye por sí solo aprobación del Quality Gate.

## Referencias primarias

- [CDP: Profiler y precise coverage](https://chromedevtools.github.io/devtools-protocol/tot/Profiler/)
- [v8-to-istanbul: conversión oficial](https://github.com/istanbuljs/v8-to-istanbul)
- [Istanbul: combinación de mapas](https://github.com/istanbuljs/istanbuljs/tree/main/packages/istanbul-lib-coverage)
- [Istanbul: generación de reportes](https://github.com/istanbuljs/istanbuljs/tree/main/packages/istanbul-lib-report)
