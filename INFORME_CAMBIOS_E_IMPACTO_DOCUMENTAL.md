# Informe técnico integral de cambios e impacto documental de SKILLY

**Fecha de cierre:** 12 de noviembre de 2026, zona America/Santiago.

**Proyecto:** `C:\Users\felip\Downloads\skilly`. **Rama:** `refactor/skilly`.

**Base Git:** `f9fdb9e9a8005cc000046b1b1a914825599a86bc`. **Último commit previo a este informe:** `48dd749890a795f73b4f22430031722e8414a582`.

Este informe reconstruye el trabajo completo disponible desde el inicio de las sesiones de Codex, no solo Android. Se contrastaron el historial y los diffs de los 29 commits posteriores a la base, el código actual, `REFACTORIZACION.md` y los resultados conservados. No se ejecutaron nuevamente las pruebas funcionales para redactarlo. El único cambio operativo de este cierre fue el reinicio controlado autorizado de SKILLY y su comprobación mínima.

Las referencias **E01–E44** se resuelven en el catálogo al final de D. Todas sus rutas se comprobaron existentes durante esta reconstrucción. Los resultados, configuraciones privadas y capturas permanecen fuera de Git, bajo **B** = `C:\Users\felip\Downloads\SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b`. Se guardó un índice con hashes en `B/informe_integral_47598b43608a4b67/indice_evidencias_revisado.json`. Publicar este informe no publica esos archivos.

## A. Estado inicial y estado final

### A.1. Qué acredita el estado inicial

El commit `f9fdb9e` del 5 de noviembre es la **primera versión disponible en Git**, con el mensaje `chore: baseline de SKILLY antes de refactorizacion`. No existe en este historial una versión anterior que permita atribuir a Git las etapas previas del desarrollo académico. Las solicitudes iniciales comprendieron acceso al directorio, diagnóstico de `Set-Location`, escritura temporal, exclusiones y recuperación local. El baseline y el respaldo prueban que se obtuvo un punto de recuperación; no se localizó un registro concluyente que permita reconstruir la causa exacta de aquel fallo de `Set-Location`. Se trabajó después con rutas absolutas, directorios explícitos y `git -C`, sin cambiar permisos globales de Windows.

SKILLY ya era una aplicación React/Vite con Django/DRF y PostgreSQL. Ya contenía marketplace, registro y validación profesional, solicitudes, coordinación, seguimiento, entregas, reclamos, pagos y administración. **No se construyeron de cero esos módulos durante la refactorización**. Sus recorridos fueron reparados o reforzados en puntos concretos y verificados con datos aislados.

E01 conserva 121 pruebas backend aprobadas y `django check` sin incidencias al inicio. El chequeo de despliegue, aunque terminó sin error fatal, informó cinco advertencias: HSTS, redirección HTTPS, cookies Secure de sesión/CSRF y DEBUG. No debe describirse ese resultado como aprobación productiva. E02 no registró discrepancias modelo/esquema en su alcance, pero una prueba de despacho con controladores simulados alcanzó operaciones bancarias sin CSRF: POST y PATCH llegaron al handler con 200; el login ya rechazaba la petición sin token con 403. Esto identifica una brecha concreta de cobertura de autenticación, no una ejecución bancaria real inicial.

La revisión posterior encontró respuestas React obsoletas, recuperación que no invalidaba suficientemente sesiones/tokens, ausencia de limitación de intentos, carga JavaScript concentrada, problemas de foco/estados de interfaz, privacidad de antecedentes, una incompatibilidad de autenticación de perfiles y defectos del modal público. Algunos fallos se demostraron después mediante pruebas rojas o integración, no todos en el primer diagnóstico.

### A.2. Alcance y decisiones que cambiaron durante el trabajo

- Inicialmente se autorizó solo preparación y commits locales; después se autorizó publicar código e historial revisados en el GitHub **privado** `ganjhamandx-ui/skilly`, conservando `master` y trabajando en `refactor/skilly`. No se autorizó desplegar, hacer merge, force push ni reescribir historia.
- Las escrituras de pruebas se restringieron a copias PostgreSQL. Se conservaron la BD original, el esquema `skilly_cu040_pruebas`, `.env`, contraseñas/permisos PostgreSQL y archivos privados originales.
- La obligación inicial de conservar puertos habituales fue sustituida expresamente por puertos alternativos de SKILLY. El 8000 pertenece a Voltify: no se usó como destino de las nuevas pruebas ni se modificó Voltify. Las referencias históricas a «servidor original» en 8000 no acreditan que fuera SKILLY.
- SonarQube se investigó y ejecutó localmente en una fase autorizada; posteriormente el usuario lo pospuso. Desde esa decisión no se reanudaron scanners, exportadores, tokens ni consultas autenticadas para aprobar el gate.
- Las confirmaciones manuales del teléfono se conservaron. La instrucción posterior amplió la revisión a Android automatizado; no se pidieron nuevos recorridos manuales para completar el emulador.
- La purga histórica de servicios sintéticos recibió una autorización específica para un trigger dentro de una transacción aislada. No se extendió esa autorización a otros borrados. La limpieza Android posterior no deshabilitó triggers.
- El presente encargo declara terminadas correcciones y pruebas, autoriza una breve interrupción para cargar las vistas pendientes y solicita este informe. No autoriza nuevas auditorías funcionales. Los Word/Excel no se generan ni modifican.

### A.3. Resultado final por tipo de artefacto

| Tipo | Resultado |
| --- | --- |
| Producto | CSRF efectivo, recuperación y sesiones reforzadas, límites de intentos, cuotas Redis atómicas, permisos/privacidad corregidos, carga diferida, estados asíncronos, accesibilidad, adaptación móvil y modal reparados; control bancario ligado a la BD configurada. |
| Herramientas y pruebas | Runners API/UI aislados, fixtures y reloj de ensayo externos al producto, cobertura real, carga limitada, control de procesos, Android/CDP/selector nativo, inventario de IDs y guardias de limpieza. Preparar estas herramientas no se contó como aprobar recorridos. |
| Configuración local | Dos WSGI, Vite desktop/LAN, PostgreSQL de copia y Memurai autenticado en puertos propios. Configuración privada externa; proxy/orígenes explícitos. No se incorporaron cuentas ni mecanismos exclusivos del ensayo al funcionamiento normal del producto. |
| Documentación técnica | Registro de refactorización, guías de herramientas, resultados de calidad y este informe. No equivale a contrastar la rúbrica ni actualizar los 22 Word y 2 Excel. |

El 12 de noviembre quedó resuelta la diferencia de código activo: backends nuevos **33024/70908**, 166 fuentes coincidentes con el árbol actual, incluido `config/identidad_bancaria.py`, y HTTP 200. Frontends nuevos **16868/29312** con proxy correcto. La comprobación verificó hashes sin cambios de `.env` y archivos privados; PostgreSQL y caché no se reiniciaron (E42).

## B. Cambios implementados por módulo

Las rutas de archivos se refieren al repositorio. Los commits cortos identifican unidades verificables del historial; un recorrido de prueba posterior no implica que todas sus funciones se añadieran en ese commit.

### B.1. Acceso, CSRF y sesiones

`SesionSkillyAuthentication` pasó de `BaseAuthentication` a `SessionAuthentication` y aplica `enforce_csrf` después de validar al usuario activo. Se protegió explícitamente el despacho de configuración bancaria y cargos por cancelación. Esto cierra el paso de operaciones autenticadas sin token, conservando las sesiones y permisos existentes. React ya disponía de mecanismos de obtención/envío de CSRF; se verificó su integración con el backend real, cookies de sesión HttpOnly/SameSite, rotación y logout. No se exigió CSRF de sesión a retornos públicos del proveedor como sustituto de sus validaciones específicas.

El restablecimiento bloquea usuario y token en un orden consistente, revalida vigencia/uso dentro de la transacción, invalida los demás tokens pendientes y revoca sesiones DB vigentes del mismo usuario. Las sesiones nuevas se vinculan mediante HMAC a la identidad y contraseña del login para rechazar una sesión guardada tardíamente con la clave anterior. Las antiguas sin marca conservan compatibilidad y se revocan al resetear. No se añadió un modelo de sesiones distinto.

**Archivos:** `backend/acceso/authentication.py`, `recuperacion.py`, `sesiones.py`, `views.py`; `backend/backoffice/cuentas_bancarias_api.py`, `configuracion_cargo_cancelacion_e3.py`. **Commits:** `e6c1f36`, `1d0184e`. **Pruebas:** E04–E07, E17, E30 y regresiones del código.

### B.2. Registro, recuperación e intentos abusivos

El registro concurrente del mismo correo deja una cuenta y un perfil: 201/400 controlados, en vez de un 500 por restricción SQL. Un savepoint interior permite clasificar el conflicto sin romper la transacción de cuenta/perfil; otros errores de integridad no se ocultan. Los fallos SMTP registran un evento fijo sin volcar excepción o traceback y revierten el token creado. La respuesta de recuperación sigue siendo genérica. El login inexistente realiza trabajo de hash; no se certifica igualdad exacta de tiempos entre todos los algoritmos y transportes SMTP.

Se añadieron cuotas configurables por IP e identidad+IP, ventanas cortas/largas y respuestas 429 con `Retry-After` para login, solicitud de recuperación y reset. No hay veto permanente ni bloqueo global por correo. Las claves usan HMAC; `X-Forwarded-For` solo se confía con proxies configurados. Fallos de caché producen 503 genérico y no filtran URI/credenciales.

**Archivos:** `backend/acceso/serializers.py`, `views.py`, `intentos.py`, `checks.py`, `apps.py`; `backend/config/settings.py`. **Commits:** `23841cc`, `a3e62a0`. **Pruebas:** E17 y E28; el ensayo LocMem inicial está referenciado en `REFACTORIZACION.md` y no sustituye la verificación multiproceso posterior.

### B.3. Caché compartida y concurrencia

La primera integración Redis detectó una carrera: se admitieron 2 intentos donde correspondían 3. `RedisIntentosCache` actualiza todas las dimensiones de una petición en un único Lua `EVAL`, con reloj del servidor Redis, ventanas fijas y expiración absoluta. Los rechazos no renuevan TTL; no se reintenta un `EVAL` de respuesta perdida que pudiera haber incrementado ya los contadores. Se validan endpoint, driver y timeouts y se conserva el aviso de que LocMem es por proceso.

La instancia de desarrollo usa Memurai 4.1.2, API Redis 7.2.5, autenticación, loopback, 64 MiB, `noeviction` y sin persistencia. Es una dependencia local de desarrollo, no una instalación productiva ni alta disponibilidad; su licencia Developer tiene límites de ejecución. El lanzador comparte namespace entre sus dos workers y no añade un balanceador.

**Archivos:** `backend/acceso/cache.py`, `intentos.py`, `checks.py`; `backend/config/cache_acceso.py`, `settings.py`. **Commit de producto:** `22bb0ee`. **Herramientas:** `24f2c58`, `tools/cache_local_skilly.py`, `verificar_cache_compartida.py`. **Pruebas:** E27–E30.

### B.4. Interfaz, navegación, carga y accesibilidad

Un controlador común cancela consultas y descarta respuestas antiguas incluso si llegan después del aborto. Se separó consultar de aplicar estado en cuentas, reversas, abonos, política de cancelación y reagendamientos. Cambiar de expediente ya no deja datos de la consulta anterior. La aceptación de política deriva de referencia y versión: cerrar no acepta; refrescar la misma versión no vuelve a abrir; cambiar referencia/versión muestra el aviso correspondiente.

Se dividieron pantallas mediante importaciones por ruta, `Suspense` y un límite de errores con recarga manual/regreso al inicio, sin bucle automático. Se conservan normalización, ruta desconocida y alias `/administracion/entregables`. Hay 17 rutas registradas, con un alias que reutiliza una pantalla.

Se mejoraron jerarquía, contraste, espaciado, formularios, tablas y adaptación móvil en acceso/registro, portal, disponibilidad, seguimiento y administración. La navegación administrativa tiene desplazamiento propio y centra el módulo activo. Se añadieron salto al contenido, foco visible, movimiento reducido y gestión compartida de foco de diálogos: Tab/Shift+Tab, Escape condicionado, anidación, retorno de foco y restauración de scroll. Se consolidaron 13 hojas CSS conservando sus valores efectivos. Los helpers de adjuntos y lectores de respuestas se extrajeron sin cambiar prioridades o payloads.

Un correo largo ensanchaba el portal de 390 a 404 px; `overflow-wrap: anywhere` resolvió la causa. Se aclaró «OPINIÓN PRIVADA» en seguimiento. Estos ajustes no constituyen una certificación universal de accesibilidad ni de todos los dispositivos.

**Archivos:** `frontend/src/cargaAsincrona.mjs`, `useCargaAsincrona.js`, `CargaPantalla.jsx`, `PantallaActual.jsx`, `rutasPantalla.mjs`, `main.jsx`, `useDialogoAccesible.js`, `SaltarContenido.jsx`, `index.css` y CSS/componentes de cada módulo. **Commits:** `114cd7e`, `3bb6740`, `29808e5`, `dce7fea`. **Pruebas:** E06, E09, E15–E16, E19, E21–E22, E26 y E36.

### B.5. Marketplace y solicitudes empresariales

El modal público bloquea sus cuatro vías de cierre durante un envío y evita un segundo envío desde el primer evento, sin depender solo del render de React. Conserva la referencia devuelta por POST 201 aunque falle la recarga posterior de catálogo/detalle, informa el problema sin sugerir reenviar a ciegas y devuelve el foco al botón equivalente o buscador si el refresco reemplazó el disparador. Se retiró el texto técnico «Datos obtenidos de Django REST».

Se conserva la regla del catálogo: **precio y nombre del profesional solo en el detalle, no en las tarjetas públicas**. La solicitud mantiene el contrato, disponibilidad y precio publicado; no se añadió edición empresarial del precio ni un login empresarial. No hubo cambios de código en el backend de `solicitudes` o `marketplace` posteriores al baseline; allí se verificaron los flujos existentes.

**Archivos:** `frontend/src/App.jsx`, hook de diálogo compartido. **Commits:** `80d596c`, `4d28b83`. **Herramientas:** `tools/pruebas_marketplace_navegador.mjs`, `harness_marketplace.js`. **Pruebas:** E24, E26, E30–E31, E36.

### B.6. Profesionales y documentos

La creación de un perfil para una cuenta profesional existente sin perfil usaba una autenticación incompatible y rechazaba una sesión legítima con 403. Ahora utiliza `SesionSkillyAuthentication` y `EsProfesional`, conserva bloqueo del usuario y 409 para duplicados. Se mantiene CSRF; no se otorga acceso por poseer un token sin rol.

Registro, documentos, revisión/rechazo/corrección, entrevista y habilitación ya existían. Se comprobaron su secuencia y restricciones mediante API y UI, incluida la negativa a aprobar antes de la entrevista. La entrevista humana se simuló; la habilitación del registro de prueba sí pasó por los endpoints reales. También se verificaron propuesta, correcciones comerciales, versión final, aceptación profesional y publicación.

**Archivos:** `backend/profesionales/views_crear_perfil.py`; `frontend/src/PortalProfesional.jsx`, `PortalProfesional.css`, acceso/registro y componentes de propuestas. **Commit de permiso:** `eb22b8c`; **UX:** `29808e5`, `a87fdc8`, `dce7fea`. **Pruebas:** E08, E18, E20–E22 y E36.

### B.7. Coordinación, administración y reagendamientos

Los recorridos verificaron solicitud, autoasignación administrativa, asociación profesional, condiciones, reserva, contratación y reagendamiento por la plataforma. No se cambió el backend de coordinación ni se inventó un nuevo rol o proceso de aprobación.

En las bandejas de reagendamiento, vacío solo aparece después de una consulta válida; carga/error son estados distintos y accesibles. Actualizar permite reintentar sin perder motivos. Los tres participantes bloquean envíos duplicados desde el primer evento, deshabilitan edición durante escritura y pausan sondeo mientras actúan. Una lectura o CSRF fallidos no permiten continuar el POST. Se valida el formato del listado sin alterar endpoints, payloads o decisiones del acuerdo.

Administración recibió las mejoras de navegación/foco/estilo, carga asíncrona de cuentas y expedientes y un `type="submit"` explícito en el formulario bancario. Las seis pantallas administrativas complementarias se comprobaron en Android por lectura, filtros, historial, modal y retorno del alias; no se modificaron sus parámetros en esa fase.

**Archivos:** `frontend/src/ReagendamientosSkilly.jsx`, `reagendamientosApi.mjs`, `PortalProfesional.jsx`, `AdminNavegacion.*`, `CuentasBancariasAdministracion.jsx`, `ExpedientesCancelacionAdministracionE3.jsx`. **Commits:** `114cd7e`, `4beb4d7`, `29808e5`, `a87fdc8`. **Pruebas:** E19–E21, E30, E36.

### B.8. Ejecución, entregas, reclamos y privacidad

El seguimiento empresarial filtraba antecedentes internos de cancelación con estado histórico `INCIDENCIA_PROFESIONAL`. La exclusión ahora comprende ese estado y `INCIDENCIA_REPORTADA`; profesional y administración conservan el registro. Es una corrección de visibilidad sobre estados existentes, no un estado nuevo ni una eliminación de antecedentes.

Los helpers frontend conservan límites de adjuntos y prioridades de formatos de API. Se comprobaron avances, versiones de entregas, observaciones, correcciones, aceptación y bloqueo de acciones incompatibles, reclamos, resolución, finalización y feedback privado. El backend de esos procesos ya existía salvo el filtro de privacidad citado. No se creó una evaluación pública ni un ranking profesional.

**Archivos:** `backend/seguimiento/politicas_reportes_profesional.py`, `views.py`; `frontend/src/entregasProfesional.mjs`, `serviciosCoordinadosApi.mjs`, `PortalProfesional.jsx`, `Seguimiento.jsx`. **Commits:** `eb22b8c`, `29808e5`, `dce7fea`. **Pruebas:** E18, E20–E22 y E36.

### B.9. Pagos, comprobantes y Webpay

Los comprobantes administrativos rechazan barras Windows, NUL, segmentos ambiguos, rutas fuera de su carpeta y flujos NTFS; una desaparición entre `exists` y `open` devuelve 404. Se sirven con `private, no-store`, `nosniff` y `no-referrer`. La revisión no demostró un IDOR remoto en esa ruta; sí justificó endurecer las referencias y el almacenamiento existentes.

La liberación exige además estado de verificación `VERIFICADO`, coherente con el flujo existente que deja el pago RETENIDO y VERIFICADO conjuntamente. Datos inconsistentes reciben 409 sin movimiento; se mantienen entrega aceptada, bloqueos por reclamo/reversa, comisión y comportamiento idempotente.

El cliente Webpay ya usaba `ssl.create_default_context`; se hicieron explícitos CA obligatoria, validación de hostname y TLS mínimo 1.2. No se demostró que el contexto por defecto anterior desactivara TLS. Los retornos/redirecciones derivan del origen frontend validado; el transporte académico exige loopback, puerto explícito y ruta de retorno exacta. Se mantienen validaciones de identidad, importe y estado del pago. Los callbacks legítimos no se hicieron depender de una cookie CSRF ajena al proveedor.

Durante Android, cuatro controles exigían literalmente una BD llamada `skilly` y bloqueaban una copia configurada correctamente con otro nombre. El helper común exige coincidencia con `connection.settings_dict['NAME']`, esquema `skilly` y rol actual/USER configurado `skilly_app`. Rechaza configuración vacía, base discordante y roles privilegiados; no contiene excepciones por prefijos de prueba. Esta corrección ya está cargada en los dos backends principales (E42).

**Archivos:** `backend/pagos/comprobantes_api.py`, `views.py`, `webpay_cliente_e3.py`, `webpay_empresa_e3.py`, ambas `transferencia_disponibilidad.py`; `backend/config/identidad_bancaria.py`, `backoffice/cuentas_bancarias_api.py`. **Commits:** `4beb4d7`, `eb22b8c`, `f2736b8`, `0f50220`. **Pruebas:** E18, E23, E25, E36–E37, E42. La autorización sandbox real asistida se conserva separada de las transferencias y liquidaciones simuladas.

### B.10. Arranque, puertos y herramientas de trabajo

Vite requiere `SKILLY_API_PROXY_TARGET` explícito y validado para servir `/api`; no tiene fallback a Voltify/8000. `FRONTEND_ORIGIN` se valida estructuralmente y alimenta CORS/CSRF y retornos, sin comodines. Se prefieren parámetros y configuración local; el frontend no recibe la URI privada de caché ni credenciales PostgreSQL.

El lanzador verifica clúster, BD/esquema/rol, puertos libres, ejecutables, ascendencia y fechas de procesos. Reutiliza los medios más recientes y distingue propiedad de PostgreSQL de una dependencia externa; no termina procesos por nombre/puerto. Un cierre controlado permite reiniciar conservando datos. El modo posterior a reinicio de Windows exige un boot nuevo y no termina PID reutilizados ni fabrica `cierre.json`. El reinicio de este cierre usó el camino controlado, sin reiniciar Windows ni PostgreSQL/caché.

Las herramientas Android validan AVD/serial/CDP y seleccionan documentos por el selector nativo con archivos sintéticos identificados. Los runners separan sesiones, congelan hashes de fuente y guardan checkpoints. Se corrigieron supuestos del driver —peticiones abortadas, geometría durante cierre del IME, esperas asíncronas, lectura de cuerpos descartados al navegar— sin desactivar controles del producto. La consulta de comentario de BD compartida usa `shobj_description`; las herramientas no fuerzan borrados si la identidad no coincide.

**Archivos:** `frontend/config/proxyApiLocal.mjs`, `vite.config.js`; `backend/config/origenes.py`, `settings.py`; `tools/entorno_local_skilly.py`, `cache_local_skilly.py`, `entorno_android_skilly.py`, `android_navegador_skilly.py`, `android_selector_archivo.py`, runners E2E y guías. **Commits:** `f2736b8`, `24f2c58`, `957b752`, `851d6ea`. Estas herramientas no forman parte de los endpoints normales del producto.

### B.11. Calidad y documentación técnica

Se conservaron runners, JMeter, cobertura Python/Node/navegador, exportador Sonar local y resultados sanitizados. El detector UTF-8 dejó de tratar todo `?` entre letras como corrupción; sigue detectando mojibake, reemplazo Unicode y bytes inválidos. La consolidación CSS y extracción de helpers atendió problemas verificables sin rebajar gate ni excluir código productivo para ocultarlos.

**Commits:** `6cc2cf7`, `688b30f`, `98321fe`, `29808e5`, `93b527d`, `5fc9e12`, `d41dcda`, `6fe7870`, `34a2834`, `7a1606e`, `48dd749`. Un commit `test` o `docs` no acredita por sí solo una ejecución; los resultados concretos son los de D.

## C. Reglas de negocio y datos

### C.1. Cambios y compatibilidad

El diff base→estado previo al informe no contiene modificaciones de modelos, migraciones, SQL fuente ni rutas backend. Se conservaron entidades, relaciones, tablas, estados persistentes y contratos principales. Tampoco se modificó el esquema original `skilly_cu040_pruebas`. Los servicios de reserva/contratación, entrega/corrección, cancelación, reclamo, comisión y pago ya estaban presentes en la base.

| Cambio observado | Clasificación e impacto real |
| --- | --- |
| CSRF, permisos de perfil/objeto y descarga | Corrección de autorización. Peticiones inválidas dejan de alcanzar operaciones; una sesión profesional legítima vuelve a poder crear el perfil faltante. |
| Invalidación de tokens/sesiones y cuotas | Nuevas garantías de seguridad observables; 429/`Retry-After` y 503 por caché deben documentarse. No cambian roles, precios o condiciones comerciales. |
| Conflicto concurrente de registro | Un error SQL no controlado pasa a respuesta 400 prevista para duplicado; cuenta/perfil siguen siendo una unidad transaccional. |
| Antecedentes `INCIDENCIA_PROFESIONAL` | Se corrige divulgación empresarial de un estado ya existente; no se añade un estado al modelo. |
| Liberación requiere VERIFICADO | Se explicita una precondición existente del flujo correcto; filas inconsistentes se rechazan con 409. No se cambia comisión ni cálculo económico. |
| Nombre de BD bancaria configurable | Corrección de instalación/portabilidad. Se conserva esquema/rol autorizado; no otorga privilegios PostgreSQL adicionales. |
| Estados React, modal y accesibilidad | Correcciones de interacción, reintento y presentación; no nuevas transiciones persistentes ni payloads. |
| Puertos/orígenes | Cambio local autorizado posterior; rutas `/api` y rutas frontend conservadas. Requiere actualizar instrucciones de ejecución, no el modelo de negocio. |

Se mantuvieron precio/nombre profesional en detalle, precio no editable por la organización, aceptación/corrección de propuesta antes de publicar, restricciones temporales de entrevista, disponibilidad/reserva, acuerdo de reagendamiento y preservación de la reserva si no se confirma, versionado de entregas, feedback privado y bloqueos de liberación. Esta lista describe reglas ejercitadas, no una revisión exhaustiva de todos los requisitos académicos.

### C.2. Bases, fixtures y conservación

El respaldo inicial se generó con la configuración local disponible, sin exponer contraseña. Su manifiesto registró lectura del archivo y catálogo correctos, pero **restauración inicialmente bloqueada por falta de CREATEDB del rol** (E03). Esa condición no se ocultó ni se resolvió concediendo permisos al usuario original: se preparó después un clúster independiente y se verificaron restauraciones en bases nuevas. Las 116 tablas y 1.388 filas de la restauración inicial se acreditan en E44; los respaldos posteriores tienen otros conteos y no son el mismo snapshot.

La copia de trabajo mantiene PostgreSQL en 57647, base/esquema `skilly` y rol `skilly_app`, con archivos privados externos. Los wrappers de ensayo limitaron red saliente y usaron correo en memoria y reloj controlado. Los mocks o controles de ensayo permanecen en herramientas/RUN externas, no en la lógica ordinaria del producto. Las escrituras sintéticas no se ejecutaron sobre la BD original. La copia de desarrollo no se presenta como una réplica actualmente idéntica y sin fixtures del origen.

La purga histórica eliminó servicios sintéticos 3–10 y 333 filas dependientes. El primer intento revirtió completamente por el trigger bancario; tras autorización específica se deshabilitó/restituyó únicamente ese trigger dentro de la transacción de mantenimiento, verificando definición y habilitación antes de confirmar. Los supervivientes se contrastaron por hash (E32). La autorización no se reutilizó para Android.

Los dos servicios conservados son:

1. ID **1**: «Capacitación práctica en Excel y herramientas digitales».
2. ID **2**: «Desarrollo de páginas web para pequeñas empresas».

Después de la carga se retiraron exclusivamente sus 15 disponibilidades nuevas, con snapshot e integridad (E29). Para Android se creó otra BD marcada `skilly_android_9e0bf2864c434675b1e7`, restaurada del respaldo verificado, separada de la copia que utilizaba el usuario. Las anclas incluyen profesional 22, servicio 11 y solicitudes/prestaciones 23/24. Se conservaron IDs y relaciones; E40 describe **120 filas relacionadas en 35 tablas**, no un delta completo de filas creadas. Tras el snapshot se retiró exclusivamente esa nueva BD, sin deshabilitar triggers; la copia principal y servicios 1/2 no se borraron (E38).

## D. Verificación y evidencias

### D.1. Método de lectura de resultados

Los conteos siguientes pertenecen a sus ejecuciones y objetivos. **No se suman** 133+153+169+172+198+214+228: son versiones sucesivas, ampliamente solapadas, de suites backend. Tampoco se suman las pasadas API 116/117, UI 129/130 y Android 161 como si fueran casos funcionales únicos. E36 ya elimina por nombre las repeticiones de la cadena Android; 74 instancias repetidas no se añaden a las 161 distintas. «Aprobado» significa únicamente que las aserciones de esa evidencia pasaron.

Las pruebas unitarias con ORM/SMTP/transporte simulados no se presentan como PostgreSQL o proveedor reales. «Interfaz real» puede convivir con `fetch` simulado; esa distinción aparece expresamente. Un `check` sin errores no certifica seguridad productiva. Este cierre no volvió a ejecutar esas suites.

| Objetivo y evidencia | Entorno y resultado conservado | Alcance y vigencia |
| --- | --- | --- |
| Línea inicial, E01–E03 | 121 backend; check correcto; cinco advertencias de despliegue; prueba CSRF con handlers simulados; respaldo inicial con restauración aún bloqueada. | Diagnóstico histórico, no estado final ni aprobación productiva. |
| CSRF, E04–E05 | Suite 133 sin BD/red; 23 comprobaciones Edge/React/Vite→Django HTTP→PostgreSQL restaurado, con formularios y escrituras bancarias de copia. | Incluye token ausente/incorrecto/origen, login/logout y cookies. E30 amplía la comprobación a orígenes actuales. |
| Respuestas asíncronas, E06 | 11 comprobaciones React real con fetch simulado, sin PostgreSQL. | Respuestas fuera de orden y política por versión/referencia. Son pruebas de interfaz, no negocio E2E. |
| Reset y revocación, E07 | 18 comprobaciones Django/PostgreSQL reales y 3 rollback con fallo inyectado; total 21 del registro. | No SMTP real. Tokens, sesiones y atomicidad; luego E17 amplía registro concurrente. |
| Registro/errores, E17 | 18 comprobaciones in-process con middleware/API y PostgreSQL reales; barrera concurrente y fallos de perfil/SMTP inyectados. | No navegador; cuenta/perfil únicos, rollback y privacidad. |
| Permisos y archivos, E18 | 51 comprobaciones Django/middleware/PostgreSQL/archivos reales; actores y fixtures de copia. | Rol/objeto, descargas, privacidad, liberación/reversa e idempotencia. Unitarias complementarias usan ORM simulado. |
| Recorrido API, E08 | 116 comprobaciones HTTP/sesiones/CSRF/PostgreSQL reales; un ensayo instrumentado posterior registró 117 incluyendo un 409 previsto de agenda ocupada. | No es un recorrido de todos los botones. Entrevista, recepción bancaria y dinero sintéticos; no sumar ambos. |
| Carga por rutas, E09 | 9 comprobaciones de navegador, incluyendo fallo de importación inyectado y recuperación manual. | Demuestra lazy loading/error boundary, no caída real de infraestructura. |
| UX visual, E15–E16 | 32 capturas finales de 16 pantallas desktop/móvil; 76 comparaciones de consolidación CSS sin diferencias en las propiedades/geometrías medidas. Registro de 15 comprobaciones de teclado finales. | Capturas anteriores conservadas. No certifica todos los estados, WCAG completo ni dispositivo físico. |
| Reagendamientos, E19 | 35 comprobaciones Edge: sesiones/lecturas reales y harness React separado con respuestas simuladas para carga/error/vacío/retry/doble envío. | Transiciones PostgreSQL completas verificadas por E20/E21/E36, no por los mocks. |
| UI escritorio, E20 | 129/129, sin checks heredados, nueve capturas y reloj restaurado. 82 operaciones UI, 33 aserciones, 6 consultas de estado y 8 de permisos. | React/HTTP/Django/PostgreSQL reales; actividad económica y entrevista simuladas. |
| Pantalla móvil Edge, E21–E22 | 130/130 en 390 px y, aparte, 11/11 de layout secuencial; fuente congelada y tres paneles sin recorte. | Emulación de viewport/táctil de escritorio, **no Android**. Las capturas antiguas que acortaban correos no acreditan el desborde por identificadores largos; las posteriores usan superposiciones sin cambiar geometría. |
| Modal marketplace, E24 | 102 aserciones internas y 7 guardias; cuatro pasadas antes/después en 1366/390 px; React/DOM reales, HTTP/datos/eventos sintéticos, sin API real. | POST 201 seguido de GET 503, cierres durante envío, duplicados, foco, error/reintento. La referencia bajo el pliegue se acredita por DOM, no por la captura. |
| Frontend final, E26 | 65/65 Node, ESLint 0 errores/0 advertencias, build correcto. | Sigue vigente: después no hubo nuevos cambios del producto frontend. No se repitió durante este informe. |
| Backend reciente, E27/E37 | Suite 228 sin BD/red antes del guard bancario; después 33 pruebas relacionadas y check correctos para ese guard, con ORM/cursores simulados. | No se afirma una suite global nueva de 261 ni cobertura total de la versión final; la corrección además pasó integración Android y recarga mínima E42. |
| Caché multiproceso, E28 | 16/16 reales, dos WSGI, PostgreSQL y Memurai. 30 concurrentes: 3 admitidos/27 bloqueados; TTL, expiración, caída segura 503, recuperación y sesión entre workers. | Sustituye el fallo de carrera previo, que se conserva. No acredita HA o persistencia productiva. |
| Desktop/LAN, E30 | 36/36 HTTP reales, sin Webpay: identidad de procesos, catálogo, sesiones, CSRF, CORS y cookies. | No teléfono físico. E42 confirma después del reinicio solo carga/HTTP/proxy, sin repetir las 36. |
| Teléfono físico, E31 | Nueve confirmaciones manuales del usuario: portada/catálogo/detalle, tarjetas sin precio/nombre, desplazamiento/cierre, teclado/validación vacía, navegación, login, pantallas propias y logout/restricción. | Android/Chrome, misma Wi-Fi. Sin modelo/versión exactos ni capturas inspeccionables disponibles; no se atribuye automatización ni ciclo completo físico. |
| Android emulador, E36 | Android 17/API 37, Chrome 156.0.8078.79, viewport nativo; 161 nombres de comprobación distintos, 74 acciones UI con activación táctil confiable y HTTP; 55 PNG, incluidos fallos. | Cadena reanudada, no única pasada. Negocio, permisos, 17 rutas, sesiones y geometrías seleccionadas. Texto mediante DOM/eventos; selector DocumentsUI nativo con bytes legibles. No prueba de escritura con IME ni reset/recuperación nuevos en Android. |
| Webpay sandbox asistido, E23 | 10/10; autorización AUTHORIZED, retorno y callback duplicado sin segundo commit; POST=1/PUT=1. HTTPS/proveedor de integración reales. | Usuario completó la autenticación bancaria del simulador. No pagos/liquidaciones reales. Intentos previos INITIALIZED/Error 21 y parciales no se suman ni se declaran autorizados. No se repitió al cerrar Android o redactar el informe. |
| Reinicio autorizado, E42 | Dos backends nuevos, 166 hashes actuales por proceso, helper bancario presente, HTTP 200; frontends/proxy con catálogo 1/2; `.env`/privados iguales. | Única comprobación operativa nueva de este cierre. Sin suites funcionales, pagos ni Android. |

### D.2. JavaScript, cobertura y calidad: cifras con su denominador

La comparación de build previa al rediseño midió bloque principal **636.302→225.647 bytes**, gzip **159.420→70.154**. El JavaScript inicial completo entonces era 253.813 bytes; acceso 240.051, administración 309.848 y portal 357.474. No se elevó el umbral para ocultar el aviso. Una medición posterior de consolidación registró 226.064/gzip 70.329 con Node/zlib; el último log E26 presenta **226,06 kB/gzip 71,07 kB con Vite**. Son registros de momentos/métodos distintos, no una cifra única intercambiable. Las métricas históricas por ruta se conservan con el commit `3bb6740` y la evidencia de la continuación.

Se produjo cobertura ejecutada, sin inventar contadores:

- Python unitario inicial: 3.218/7.059 líneas y 200/1.870 ramas, 139 fuentes. Después, datos unitarios + servidor HTTP instrumentado: **4.690/7.059 líneas y 683/1.870 ramas** (E12). No se atribuye al servidor cobertura tomada del cliente.
- Navegador: 44 comprobaciones; LCOV de **57 módulos, 49 JSX**, 10.046/21.995 líneas, 423/668 ramas y 88/519 funciones de ese conjunto (E13). El sourcemap intermedio no verificable de rutas se omitió de esa conversión; Node cubre el helper, sin excluirlo de Sonar.
- Node50: siete helpers, **97,58 % líneas/92,86 % ramas** (E14). La medición anterior de cinco módulos/43 pruebas fue 97,33 %/91,58 %. Ninguna cifra representa todo React.

Estas coberturas son históricas y no se recalcularon tras todos los cambios posteriores. No prueban 80 % del código nuevo actual ni importación efectiva en Sonar. E11 conserva gate **ERROR**: cobertura nueva 0 frente a mínimo 80; 425 incidencias nuevas frente a máximo 0; duplicación nueva 1,63251 frente a máximo 3 estaba OK. La exportación guardada contiene una muestra de 100 de 623 incidencias y un filtro prioritario de tres, no una clasificación completa.

Se atendieron los puntos TLS `python:S4830`/`S4423`, envío bancario `javascript:S9011` y causas verificables de mantenibilidad/accesibilidad. No se rebajó gate ni referencia de código nuevo, ni se excluyó código válido para conseguir aprobación. Se corrigió la paginación del exportador y pasó 11 comprobaciones con API simulada. **Sonar está pospuesto**: advertencias exactas, clasificación completa, definición efectiva de código nuevo e importación/reanálisis no quedaron acreditados. La clave de configuración es `Skilly`; el nombre visual «Habilidoso» no quedó confirmado por la exportación disponible. No se creó otro proyecto ni se cambió la clave.

### D.3. Carga medida, sin extrapolación productiva

| Ensayo conservado | Plan y resultado | Límite de interpretación |
| --- | --- | --- |
| JMeter 5.6.3, E10 | Solo GET de CSRF/marketplace, 1/2/4 usuarios, 8 s por etapa, rampa 3 s y pausa 1 s. 6/11/21 muestras: **38 HTTP, 0 errores**, p95 33/134/135 ms. | Lectura pequeña, sin autenticación/escrituras. No capacidad productiva ni concurrencia económica. |
| Carga local autenticada, E29 | Dos WSGI, sesiones/CSRF/PostgreSQL reales. Calentamiento 2 s; 1/2/4/8 clientes, 10 s cada etapa. 27/56/107/217 = **407 solicitudes medidas**, todas 200/201; p95 115/143/152/146 ms. En 8 clientes: **21,69 solicitudes/s**. | Circuito acotado de desarrollo local, no máximo sostenible, SLA ni ensayo productivo. Login/logout/calentamiento se registraron aparte. |

El segundo plan fijó pausas y hasta 64 escrituras por etapa y paradas por CPU >70 % en tres muestras, RAM <2 GiB, 5xx >1 %, cinco 5xx seguidos o p95 >3 s. Ninguna se activó. CPU máxima registrada 16,8 %, RAM mínima disponible 12.614.062.080 bytes. Las 15 disponibilidades creadas se verificaron y retiraron; cero duplicados observados. Los 27 rechazos 429 de la prueba de caché no son errores de la carga ni se mezclan con ella.

### D.4. Catálogo local de evidencias

Las rutas siguientes son relativas a B. Son ubicaciones de consulta local; no se incorporan a Git. El índice privado conserva SHA256 de los archivos leídos. Las carpetas pueden contener configuración privada y no deben subirse completas. Los informes de herramientas cuyos resultados solo constan en el registro y salida de sesión se distinguen de un JSON independiente: por ejemplo, las regresiones offline del lanzador/Android se documentaron como 49 (15+25+9), 9/11/15/7 y 5 Node respectivamente; no se inventa un nuevo archivo de resultados ni una ejecución global para ellas.

| ID | Ubicación relativa a B | Consulta de cierre |
| --- | --- | --- |
| E01 | `checks.json` | Archivo existente; SHA256 441481b6e402… |
| E02 | `audit.json` | Archivo existente; SHA256 9b5ca0adbcfd… |
| E03 | `manifest.json` | Archivo existente; SHA256 858fe183443c… |
| E04 | `validacion_csrf_f6e7e0fccd1f47c885ebbf09fade9353/resultado.json` | Archivo existente; SHA256 995ae7e89206… |
| E05 | `integracion_real_ca0377f060c14b02b631053609d48d10/browser_result.json` | Archivo existente; SHA256 c82429920a10… |
| E06 | `navegador_ux_4b74d4e92c5d42abb715cf97523c6dda/resultado.json` | Archivo existente; SHA256 78b1e84c16cb… |
| E07 | `integracion_recuperacion_f0b144ac4d014d6587198ec447327f26/resultado.json` | Archivo existente; SHA256 0ec4e8eb712e… |
| E08 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/api_e2e_7d09f243c08e407cb9cddbc5df71ce1e/resultado.json` | Archivo existente; SHA256 7e8f1ff0b95a… |
| E09 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/carga_rutas_1793930378949/resultado.json` | Archivo existente; SHA256 3f296e61820f… |
| E10 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/quality_047b651fb75c4b0ca9be12f7ef0d5d72` | Carpeta existente con resultados conservados |
| E11 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/sonar_analisis_d0fcb003da31497781e68de7874bbb78/resultado.json` | Archivo existente; SHA256 e76de173c3f1… |
| E12 | `continuacion_c2998d287c4d4dd6a1900e8b0fdfad71/coverage_combined/coverage.xml` | Archivo existente; SHA256 752fd0903dd3… |
| E13 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/coverage_browser_8a599de9e53044518574486561c23592/lcov.info` | Archivo existente; SHA256 abab16a54cfe… |
| E14 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/coverage_node_final_1f159d0de4e748f19ad1c8b10a851139/lcov.info` | Archivo existente; SHA256 4c309cae91ae… |
| E15 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/capturas_final_1793987841409` | Carpeta existente con resultados conservados |
| E16 | `continuacion_ec5fd1bf356e455c80591b980d4dbc44/capturas_css_comparacion_1793987797863` | Carpeta existente con resultados conservados |
| E17 | `continuacion_62fc2e44c9a5492c94d0206afe58cade/acceso_integracion_1f18f178baad436ea1b23c27daa134ee/resultado.json` | Archivo existente; SHA256 a52afc856cc3… |
| E18 | `continuacion_c90c757328c546d5b46f34c9fe95b882/objetos_integracion_b404d356e0b54e55927e5beaa800e84e/resultado.json` | Archivo existente; SHA256 936bf3d8e407… |
| E19 | `continuacion_c90c757328c546d5b46f34c9fe95b882/ux_reagendamientos_4a2dac900e964580a2bb9170dc751c01/resultado.json` | Archivo existente; SHA256 9d8e19d454d7… |
| E20 | `continuacion_c90c757328c546d5b46f34c9fe95b882/browser_e2e_ffae488af5514fd28606dd308fa29aeb/resultado.json` | Archivo existente; SHA256 26855f53d60a… |
| E21 | `continuacion_fc46b8bbcf6b4328a391a66a0af00cda/browser_e2e_a4d1054504154a7186323f07718d88af/resultado.json` | Archivo existente; SHA256 c15cfbe7cd60… |
| E22 | `continuacion_fc46b8bbcf6b4328a391a66a0af00cda/browser_e2e_3afeaa3be9464d1fa5fe5b3fc43c1519/resultado.json` | Archivo existente; SHA256 adf9e82508a0… |
| E23 | `continuacion_7104ca3157d44bc1be9be634da7ce20e/sandbox_runtime_1e4edcbc8c684f3e941508c5de5c1c40/sandbox_browser_69549c8d3dd44700b82de68aef8b0ef3/resultado.json` | Archivo existente; SHA256 c50ce88c57df… |
| E24 | `marketplace_modal_c2c25346a4cb40d590ba9872c77ac861` | Carpeta existente con resultados conservados |
| E25 | `validacion_modulos_b858ca0650414d00810fc3afbc27140c` | Carpeta existente con resultados conservados |
| E26 | `verificacion_frontend_14086ba2f8384a43937ef7c6bcf60691` | Carpeta existente con resultados conservados |
| E27 | `validacion_modulos_7703c40db5ef4998800e0d02523d95bb` | Carpeta existente con resultados conservados |
| E28 | `cache_compartida_bf96d730b7d7430a` | Carpeta existente con resultados conservados |
| E29 | `carga_real_20261111_88fcc27d` | Carpeta existente con resultados conservados |
| E30 | `local_activo_88fcc27dc54c4fd8/verificacion_acceso_14251a45ee994755a839820d4d1e394e` | Carpeta existente con resultados conservados |
| E31 | `local_activo_88fcc27dc54c4fd8/android_fisico.json` | Archivo existente; SHA256 fd1c19692f19… |
| E32 | `catalogo_limpieza_08d3524278a04468b96b6ac41f8ac968` | Carpeta existente con resultados conservados |
| E33 | `recuperacion_reciente_2f14f36b29f143f09c7655f7f9fcd41d` | Carpeta existente con resultados conservados |
| E34 | `recuperacion_reciente_361a5de6db674c5d86cae8d51200d418/resultado.json` | Archivo existente; SHA256 7d913da333e2… |
| E35 | `limpieza_perfiles_cce400dd1daf49ba975c0924d3c7d5c9/resultado.json` | Archivo existente; SHA256 892b9c8e71fc… |
| E36 | `android_aislado_9e0bf2864c434675b1e7/cobertura_final_android.json` | Archivo existente; SHA256 a760736836a4… |
| E37 | `android_aislado_9e0bf2864c434675b1e7/verificacion_identidad_bancaria/resultado.json` | Archivo existente; SHA256 53714b58ac9f… |
| E38 | `android_aislado_9e0bf2864c434675b1e7/limpieza.json` | Archivo existente; SHA256 1987960a4f64… |
| E39 | `android_aislado_9e0bf2864c434675b1e7/limpieza_archivos_cierre.json` | Archivo existente; SHA256 8365f3f2a28f… |
| E40 | `android_aislado_9e0bf2864c434675b1e7/inventario_datos_android_338480fb08c24a0c862e447cd99eb107.json` | Archivo existente; SHA256 30ec3d4eef0c… |
| E41 | `android_aislado_9e0bf2864c434675b1e7/cierre_publicacion_recuperacion.json` | Archivo existente; SHA256 5e6add9a931b… |
| E42 | `informe_integral_47598b43608a4b67/reinicio_verificado.json` | Archivo existente; SHA256 3f1247053f29… |
| E43 | `auditoria_final_1fc1754d1ee94cfead177eb0eb303519/resultado.json` | Archivo existente; SHA256 e4f555401864… |
| E44 | `ensayo_aislado_4cc39c7e659a40ca8f0778eb51a72e0d/resultado.json` | Archivo existente; SHA256 8d00baa88dc2… |

## E. Limpieza, respaldos y funcionamiento actual

### E.1. Retiradas y recuperación

- Purga de servicios sintéticos 3–10 y 333 filas dependientes, con primer intento revertido y autorización específica posterior; IDs 1/2 y trigger protegido conservados (E32). No se repitió en este cierre.
- Quince disponibilidades de la carga retiradas con snapshot e integridad (E29).
- Sesenta perfiles de navegador de ensayos cerrados y cuatro auxiliares obsoletos retirados: **2.448.655.678 bytes lógicos**, manteniendo 63 resultados y 586 archivos hermanos por hash (E35). Se conservaron seis perfiles con checkpoints y respaldos de dependencia/recuperación ambigua; no se borraron por antigüedad.
- Tras Android: retirada de su BD nueva marcada, con inventario y snapshot; sin deshabilitar triggers. AVD y solo sus túneles registrados cerrados, sin guardar el AVD ni terminar ADB global/otros dispositivos (E38/E40).
- Veintiuna copias privadas redundantes del ensayo cerrado y quince auxiliares archivados retirados: **36 archivos, 1.390.676 bytes**, originales o copia exacta retenidos. El error de suma del informe PowerShell se corrigió comprobando ausencia/hashes, sin repetir borrados (E39). Los documentos sintéticos vinculados al snapshot y las capturas útiles se conservaron.

| Respaldo conservado | Estado de verificación |
| --- | --- |
| Respaldo original y manifiesto E03 | Dump generado, catálogo/lectura verificados; restauración inicialmente bloqueada. Restauraciones aisladas posteriores se acreditan por sus resultados propios, sin alterar retrospectivamente aquel manifiesto. |
| E33, anterior a purga | Dump restaurado realmente en BD temporal nueva: 116 tablas/2.443 filas y hashes iguales; base temporal retirada. |
| E34, posterior a purga/carga | Dump consistente mediante snapshot exportado, **restauración real de 116 tablas/2.220 filas y todos los hashes iguales**; base temporal retirada. SHA256 del dump `4cb4153631465c43b745749f8994ea1b9bc1084ba07906ec0edb127c679e8be7`. |
| Android `datos_android_antes_retirada.dump` | Generado, hash `880d8d610531ae1c986728df6a14a8766ed9086c4df3c55f1604928cd5b7ac2d` y catálogo legible; **no restaurado**. No confundir con E34. |
| E41 `codigo_publicado.bundle` | Bundle Git verificado de `48dd749`, con ramas master/refactor y registro/documentación de esa etapa; no incluye este informe nuevo. El historial remoto/local publicado conserva la continuación documental. |

El dump no es por sí solo una recuperación completa de archivos privados/configuración. Deben conservarse también el manifiesto `recuperacion_reciente_361a5de6db674c5d86cae8d51200d418/recuperacion_completa_privada.json`, `.env` respaldado, 18 media, 3 entregas privadas y las conexiones externas indicadas allí. El funcionamiento usa los medios más recientes de `local_activo_bea5799c5ccc4e2c/backend_files`, no una nueva copia del respaldo antiguo. Ni credenciales ni esos contenidos forman parte del repositorio.

### E.2. Resolución del código activo y recursos que permanecen

Antes del reinicio se identificaron supervisor 63740, backends 42432/48784 y Vite 47744/66372, por ejecutable, argumentos, cwd y fecha. El contexto `local_activo_88fcc27dc54c4fd8` no era propietario del clúster (`owns_cluster=false`). Se usó `entorno_local_skilly.py detener`, se confirmó el cierre de sus hijos y `other_processes_touched=false`, y se inició el mismo entorno con `--reutilizar-contexto`, mismos puertos, mismo Node y mismo contexto de caché. **No se usó `--reanudar-tras-reinicio`**, reservado a un boot nuevo de Windows; este fue un reemplazo controlado.

Contexto vigente: `B/local_activo_83e731c2000a4b9c/contexto.json`; el puntero local ignorado `.skilly-local-activo.tmp` se actualizó. E42 verifica:

| Recurso | Estado final |
| --- | --- |
| Backend 1 | PID **33024**, `http://127.0.0.2:57739`, WSGI de este proyecto, 166 hashes actuales y helper bancario presente, catálogo HTTP 200. |
| Backend 2 | PID **70908**, `http://127.0.0.2:57740`, mismas verificaciones. |
| Frontend PC | PID **16868**, **http://127.0.0.2:57741/**, HTTP 200 y proxy `/api` con catálogo 1/2. |
| Frontend teléfono | PID **29312**, **http://192.168.100.19:57742/**, HTTP 200 y proxy con catálogo 1/2. Verificación desde el PC del origen LAN; no se repitió el recorrido físico. |
| PostgreSQL de copia | Mismo clúster en 57647, no reiniciado ni restaurado, misma base/esquema/rol y datos. |
| Caché | Memurai PID **45880**, loopback 52893, autenticación y límite 64 MiB conservados. Proceso no reiniciado; cada RUN usa namespace propio, sin flush global. |
| Archivos privados y `.env` | Reutilizados; hashes antes/después iguales. No se cambiaron contraseñas, permisos globales o firewall. |

**La diferencia entre vistas bancarias guardadas y activas queda resuelta.** No queda pendiente aquella recarga. El supervisor del nuevo contexto permanece ejecutándose para mantener los accesos; cerrar esta etapa no significó apagar el sitio. La regla `SKILLY_Android_88fcc27d` y el Node dedicado se conservan: el teléfono confirmado era `192.168.100.4`. La interpretación anterior del valor 2 de NetSecurity como bloqueo fue errónea: significa `Allow`. La comprobación histórica se corrigió y no se ejecutó una eliminación de regla solo porque el usuario hubiera repetido su texto.

El procedimiento después de reiniciar Windows sigue en `tools/ENTORNO_LOCAL.md` y `REFACTORIZACION.md`: leer el contexto más reciente, preservar `private_root`, iniciar una nueva RUN de caché si el proceso anterior ya no existe, verificar IP/puertos y usar el modo de recuperación solo cuando corresponda. El reinicio físico no se ensayó aquí. No se requiere AVD, SonarQube ni JMeter para abrir SKILLY.

## F. Impacto documental

### F.1. Disponibilidad y criterio

No se identificó en el proyecto ni en el respaldo revisado el conjunto académico de **22 Word y 2 Excel**. Los DOCX/XLSX encontrados bajo media/entregas privadas son cargas de la aplicación; no se abrieron ni se equipararon a esos documentos. No hay evidencia suficiente para inventar títulos, números, hojas, requisitos o secciones exactas de los documentos académicos. **Todas las correspondencias siguientes requieren contraste con el archivo correspondiente.** La matriz enumera temas, no una asignación uno-a-uno a 22 documentos.

No se generó ni modificó Word/Excel. Esta base permite decidir después qué texto/diagramas/modelos actualizar. «Revisar» indica impacto a contrastar, no una obligación académica nueva ya acordada.

| Cambio técnico o funcional | Documento o sección temática por contrastar | Contenido a corregir o incorporar | Evidencia | Diagramas/modelos/requisitos/casos/pruebas/manuales/plan |
| --- | --- | --- | --- | --- |
| Baseline y alcance real | Historia del proyecto / alcance del desarrollo | Separar módulos preexistentes de correcciones Codex; primera evidencia Git `f9fdb9e`, sin atribuir etapas anteriores al repositorio. | Git, E01–E03 | Revisar cronología, alcance y trazabilidad; no inventar hitos anteriores. |
| CSRF en sesión SKILLY | Requisitos de seguridad / diseño de autenticación | Token, cookie, rotación y envío React→Django; operaciones protegidas y callbacks públicos con validación propia. | `e6c1f36`, E04–E05/E30 | Secuencia login/escritura/logout; requisitos y pruebas negativas. |
| Reset y revocación | Recuperación de acceso / gestión de sesiones | Token de un uso, expiración, invalidación conjunta, sesiones revocadas y preservación de otros usuarios; compatibilidad de sesiones antiguas. | `1d0184e`, E07/E17 | Secuencia/transacción, casos de uso, pruebas de rollback; ERD sin nuevas entidades. |
| Intentos abusivos | Requisitos no funcionales / controles de acceso | Cuotas IP e identidad+IP, HMAC, 429/Retry-After, no bloqueo permanente ni enumeración por mensajes; 503 por fallo de caché. | `23841cc`, E28 | Estados/errores API, requisitos, plan de seguridad y manual de operación. |
| Registro concurrente | Registro profesional / validación de entradas | Atomicidad cuenta/perfil, respuesta 400 por duplicado concurrente y rollback ante fallo. | `a3e62a0`, E17 | Secuencia, caso alternativo y pruebas de concurrencia; sin relación ERD nueva. |
| Perfil profesional y permisos | Matriz de roles / creación de perfil | Sesión profesional legítima, rol requerido, duplicado 409, CSRF. | `eb22b8c`, E18 | Matriz de permisos, caso de uso y pruebas propietario/ajeno/anónimo. |
| Documentos y comprobantes privados | Seguridad de archivos / manual administrativo | Acceso por objeto, cabeceras privadas, rutas inválidas y archivo desaparecido; no afirmar un IDOR remoto no demostrado. | `eb22b8c`, E18 | Flujo de descarga, controles, pruebas negativas y manual; no afirmar cifrado nuevo. |
| Carga diferida | Arquitectura frontend / rendimiento | Pantallas por ruta, chunk inicial, Suspense/error boundary, recuperación manual y alias conservado. | `3bb6740`, E09/E26 | Diagrama de componentes/carga, requisito de rendimiento y pruebas; sin endpoints nuevos. |
| Consultas asíncronas | Diseño de interfaz / manejo de errores | Cancelación, respuestas obsoletas, referencia/versión y coherencia entre expediente/consulta. | `114cd7e`, E06 | Secuencias UI, estados de carga/error/vacío y casos de reintento. |
| Accesibilidad y CSS | Diseño UX/UI / manuales de usuario | Jerarquía, etiquetas, foco, teclado, scroll, modales anidados, navegación móvil y movimiento reducido; límites de validación. | `29808e5`, E15–E16 | Wireframes/capturas, criterios de accesibilidad y pruebas; no certificar WCAG completo. |
| Modal marketplace | Solicitud empresarial / manual de catálogo | Conservar referencia tras fallo de refresco, no duplicar solicitud, cierres bloqueados mientras envía y retorno del foco. | `80d596c`, E24/E36 | Caso principal/alternativos, diagrama de interacción y manual; no cambiar regla comercial. |
| Tarjetas y detalle | Diseño de marketplace / manual público | Precio/nombre profesional en detalle únicamente; retirar texto técnico del catálogo. | `4d28b83`, E31/E36 | Capturas y requisitos de presentación; no inventar filtros o precios. |
| Validación y publicación profesional | Casos de uso / manuales profesional y admin | Secuencia documentos→revisión/corrección→entrevista→habilitación; propuesta→revisión→aceptación→publicación, aclarando qué ya existía. | E08/E20/E36 | Diagramas de actividad/estado y evidencias; entrevista probada sintéticamente. |
| Solicitud, autoasignación y contratación | Coordinación / manual administrativo | Responsables, asociación, condiciones, reserva y precondición de pago; organización mediante referencia privada. | E08/E20/E36 | Casos de uso/actividad y pruebas; no agregar login empresarial. |
| Reagendamientos | Coordinación / comunicaciones internas | Acuerdo por plataforma, carga/error/reintento, bloqueo de duplicados y preservación de reserva si no se confirma. | `a87fdc8`, E19/E36 | Estados/secuencia por tres participantes, manual y pruebas. |
| Ejecución y entregas | Seguimiento / aceptación del servicio | Avance, versiones, observación, corrección y aceptación; formularios cerrados no forzados por el test. | E18/E20/E36 | Actividad/estados, casos alternativos, pruebas y manuales; modelos existentes. |
| Antecedentes internos | Privacidad / reclamos y cancelaciones | `INCIDENCIA_PROFESIONAL` e `INCIDENCIA_REPORTADA` no visibles mediante enlace empresarial; historial interno conservado. | `eb22b8c`, E18 | Matriz de visibilidad, flujos de datos y pruebas; no estado persistente nuevo. |
| Liberación de pago | Reglas económicas / manual financiero | Exigir VERIFICADO, entrega aceptada y ausencia de bloqueos; 409 coherente e idempotencia, comisión sin cambio. | `eb22b8c`, E18/E36 | Estado de pago/precondiciones, caso de uso y pruebas; no liquidación real acreditada. |
| Webpay TLS/orígenes | Integración externa / seguridad | TLS verificado explícito, origen configurable, retorno y validación de identidad/importe; sandbox asistido separado de mocks. | `4beb4d7`, `f2736b8`, E23 | Secuencia proveedor/retorno/reintento, configuración, pruebas y manual técnico. |
| Identidad bancaria configurada | Instalación / arquitectura de datos | BD real coincide con NAME configurado; esquema/rol restringidos; cuatro vistas actuales ya cargadas. | `0f50220`, E37/E42 | Despliegue/configuración, restricciones y pruebas; ERD sin modificación. |
| Cancelación, reclamo y reversa | Reglas de negocio / manuales | Evaluación, resolución, contrato cancelado y devolución SIMULADA; distinguir registros de movimientos bancarios reales. | E20/E23/E36 | Estados, casos alternativos, manual financiero y alcance de pruebas. |
| Caché entre procesos | Arquitectura / operación / plan de mejora | Redis EVAL conjunto, reloj/TTL, fallo seguro, dos workers y LocMem limitado; dependencia de desarrollo sin HA. | `22bb0ee`, E28 | Componentes/despliegue, requisito de seguridad, pruebas de concurrencia y operación. |
| Puertos y reinicio | Manual de instalación y operación | URLs propias, proxy explícito, CORS/CSRF exactos, Node/firewall limitados, contexto más reciente y cierre por identidad. | `f2736b8`, `957b752`, E30/E42 | Diagrama de despliegue y manual; no cambiar contratos ni infraestructura de Voltify. |
| Datos y recuperación | Modelo de datos / respaldo y mantenimiento | Ausencia de migraciones nuevas, copias aisladas, trigger/purga autorizada, dos servicios conservados, dumps restaurados frente a solo generados. | E03/E32–E34/E38–E40 | ERD: contrastar, no redibujar relaciones como si hubieran cambiado; procedimientos y pruebas de restauración. |
| Evidencias y clasificación | Plan de pruebas / hojas de resultados | Separar unitarias, API, UI real/mock, Edge móvil, Android emulado, confirmaciones físicas y sandbox asistido; deduplicar ejecuciones. | D y E04–E42 | Matriz de pruebas y trazabilidad; actualizar hojas solo tras ver su estructura. |
| Rendimiento y cobertura | Requisitos no funcionales / evaluación de calidad | Tamaños antes/después, denominadores de cobertura, 38 lecturas JMeter y 407 solicitudes limitadas; no extrapolar capacidad. | E09–E14/E26/E29 | Tablas/gráficos y resultados de pruebas; no nuevo SLA ni porcentaje global inventado. |
| SonarQube pospuesto | Plan de mejora / deuda técnica | Gate ERROR y muestra incompleta, causas corregidas, importación/validación no acreditadas; no declarar aprobación. | E11, `tools/quality/RESULTADOS_LOCALES.md` | Plan de mejora y trazabilidad de hallazgos; sin requisito de ejecutar ahora. |
| Repositorio y secretos | Gestión de configuración / entrega técnica | Rama, baseline, commits/push revisados, exclusiones y recuperación externa; no credenciales, dependencias o dumps en Git. | E41/E43, historial | Procedimiento de versiones y entrega; no atribuir a Git fases anteriores. |

## G. Cierre y límites

**Completado:** correcciones y verificaciones descritas del producto, herramientas y limpieza; conservación de datos/recuperación; carga de vistas bancarias nuevas en ambos backends; accesos PC/LAN nuevamente activos; informe integral y actualización del registro. La recarga que figuraba pendiente al terminar Android queda expresamente sustituida por E42.

**Excluido o pospuesto por decisión del usuario:** despliegue/publicación fuera del GitHub privado autorizado, cambios de visibilidad, merge/force push/historia, pagos o envíos reales, nuevas auditorías funcionales o repetición de recorridos aprobados, SonarQube hasta nueva solicitud, generación/modificación de Word/Excel. La matriz F no supone haber auditado sus contenidos.

**Límites reales que permanecen:** gate Sonar no aprobado y exportación completa/importación no acreditadas; documentos académicos y rúbrica no contrastados; ausencia de certificación productiva, alta disponibilidad de caché, capacidad máxima, SMTP/liquidación reales y todos los dispositivos/estados visuales. El snapshot Android generado no se presenta como restaurado. La automatización Android no acredita teclado físico ni una pasada integral en el teléfono del usuario. Estos límites no se convierten en tareas nuevas de esta etapa.

No se declara el sistema libre de errores, completamente seguro, listo para producción ni conforme a toda la rúbrica. Tampoco se atribuye salud funcional a Voltify: no se lo probó ni intervino. Se conserva `master` como referencia inicial; esta continuación publica únicamente el informe y el cierre documental en `refactor/skilly`, revisados para excluir secretos y evidencias privadas.
