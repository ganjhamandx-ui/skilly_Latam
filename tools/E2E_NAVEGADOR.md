# Recorridos funcionales de navegador aislado

`e2e_browser_aislado.mjs` controla Edge mediante CDP nativo de Node. No requiere
Playwright ni dependencias adicionales. Usa React, HTTP, Django y PostgreSQL
reales del entorno de ensayo; no ejecuta SonarQube ni instrumentos de cobertura.

## Requisitos y ejecución

El controlador del ensayo debe iniciar previamente una copia aislada con Vite y
Django. Su `contexto.json` externo contiene `run_dir`, `run_id`, `frontend_origin`,
`backend_origin` y `database_port`. El directorio contiene `fixture_privado.json`
con actores sintéticos y control del reloj. Esa fixture permanece fuera de Git;
no se imprime ni se comparte. El servidor debe bloquear correos/pagos reales y
verificar el directorio del clúster, BD, esquema y rol antes de permitir escritura.

El driver exige orígenes loopback con puertos explícitos distintos de los
operativos, rechaza PostgreSQL 5432 y valida `/__isolated/health` contra el contexto.
Antes de leer credenciales exige también que el proxy del frontend responda
`GET /api/__isolated/health` con la misma identidad de entorno y puerto PostgreSQL.
Ese alias pertenece exclusivamente al servidor de ensayo, fuera del producto.
El navegador bloquea las solicitudes hacia otros orígenes. No carga `.env`, no
conecta directamente a PostgreSQL ni inicia o detiene la instancia operativa.

Ejemplo en PowerShell, sustituyendo únicamente la ruta del contexto aislado activo:

```powershell
$contextoEnsayo = 'C:\ruta\externa\del\ensayo\contexto.json'
& 'C:\Program Files\nodejs\node.exe' 'C:\Users\felip\Downloads\skilly\tools\e2e_browser_aislado.mjs' $contextoEnsayo --phase all
& 'C:\Program Files\nodejs\node.exe' 'C:\Users\felip\Downloads\skilly\tools\e2e_browser_aislado.mjs' $contextoEnsayo --phase all --mobile
```

Escritorio usa 1366×1000. `--mobile` emula 390×844 y capacidad táctil en Edge;
no acredita dispositivos físicos ni todos los navegadores móviles. Ambos modos
ejecutan las mismas operaciones y rechazos con los mismos criterios de éxito.
En móvil se despachan taps CDP `touchStart`/`touchEnd`; se resta el desplazamiento
de `visualViewport` a las coordenadas del layout. No se usa `.click()` de JavaScript
para sustituir una interacción que no alcance su botón. Antes del tap se espera
que posición, desplazamiento visual y scroll permanezcan estables; las animaciones
del producto continúan activas.

## Alcance y límites

Las mutaciones de negocio pasan por los formularios, botones y manejadores React:
registro; documento inválido y válido; revisión, rechazo y corrección conservando
historial; entrevista y habilitación; propuesta corregida y publicación;
solicitud empresarial y reserva; autoasignación, asociación, condiciones y contrato;
comprobante sintético y verificación administrativa; reagendamiento con consenso;
avance, entrega adjunta observada, corrección y aceptación; reclamo y resolución;
cierre, retroalimentación privada, liberación con comisión; segunda contratación,
expediente de cancelación revisado, resolución y reversa explícitamente simulada.

CDP acciona los controles y completa campos con sus setters nativos y eventos.
Los adjuntos son PDFs sintéticos creados por el driver. Las respuestas API se
leen en memoria para comprobar estados e identificadores. No se simulan las
respuestas de React, Django o PostgreSQL ni se usa SQL para saltar transiciones.
Las comprobaciones auxiliares HTTP de lectura están etiquetadas por separado:
documentos del propietario, de otro profesional y anónimos; rol administrativo;
retroalimentación privada y prestación ajena. No equivalen a acciones de UI.

La entrevista humana y la confirmación bancaria son sintéticas; el servidor usa
correo local en memoria. La transferencia, liberación y devolución registran el
escenario académico sin mover dinero. Esta herramienta no verifica autorización
de tarjeta, conciliación bancaria, envío de correo ni el ciclo completo de Webpay.

El reloj exclusivo del servidor aislado permite comprobar el rechazo del
resultado prematuro de entrevista y su resolución posterior. El driver vuelve
a autenticar al avanzar días: conserva la expiración legítima de las sesiones.
Restablece el reloj en `finally`, incluso ante fallos, y registra `clock_reset`.
Solo cierra los contextos y el proceso Edge creados por su ejecución.

## Evidencia y reanudación

Cada ejecución crea `browser_e2e_<identificador>` fuera del repositorio, con:

- `resultado.json`: comprobaciones, estados HTTP, intervenciones sintéticas,
  errores, viewport y resumen de escenarios; sin cuerpos ni credenciales. Cada
  operación UI conserva los eventos pasivos observados de pointer/touch/click y
  submit, sus destinos sanitizados y `isTrusted`, también al navegar a otra página.
- Capturas `desktop_*.png` o `mobile_*.png`, con correos, contraseñas y referencias
  de seguimiento ocultos mediante superposiciones temporales. Conservan el texto
  y su geometría original, y se retiran después del PNG. Permanecen locales fuera
  de Git.
- `*.geometria.json`: dimensiones del documento/viewport y nodos que exceden su
  anchura. Permite distinguir un desbordamiento de la UI de las coordenadas del
  viewport visual del navegador; no modifica CSS ni ajusta el documento para pasar.
- `fuentes_antes.json` y `fuentes_despues.json`: Git HEAD y SHA-256 de fuentes
  rastreadas backend/frontend y de los cinco módulos del driver. Cambiar esas
  fuentes durante el recorrido hace fallar la comprobación de integridad.
- `fixture_privado.json`: credenciales sintéticas y checkpoints para depuración;
  no debe publicarse. Los diagnósticos de fallo excluyen valores de campos,
  cuerpos y segmentos de referencias privadas.

Los fallos iniciales, incluidos JSON privados corruptos, solo imprimen un tipo de
error y una etapa; no imprimen fragmentos del archivo ni stacks. Su regresión
compartida con el driver Webpay se ejecuta sin red con:

```powershell
& 'C:\Program Files\nodejs\node.exe' --test 'C:\Users\felip\Downloads\skilly\tools\tests\harness_privacidad.test.mjs'
```

Una pasada completa requiere `--phase all` sin `--resume`, `completed: true`,
`full_ui_journey: true`, ningún error y reloj restaurado. Los resultados de
ejecuciones parciales de depuración se conservan como antecedentes; no se suman
para presentar una pasada completa ni se declaran como pruebas independientes.

Para continuar una depuración se admite `--resume C:\ruta\externa\fixture_privado.json`
y `--phase professional`, `cycles` o `permissions`. Los checkpoints evitan repetir
operaciones cerradas. La reanudación exige conservar la misma copia aislada,
configuración de firma y almacenamiento privado de los archivos de prueba.
Crear otro servidor con distinto almacenamiento no acredita la descarga de un
archivo anterior: la pasada final debe generar sus propios documentos en el
entorno activo. Ninguna reanudación altera datos ni archivos de la BD original.

## Comprobación visual sin mutaciones de negocio

`--phase layout --mobile --resume C:\ruta\externa\fixture_privado.json` abre
documentos con un PDF sintético seleccionado, propuesta y entregas. El driver
bloquea todos los verbos de escritura salvo el inicio de sesión. No guarda los
formularios. La fixture debe corresponder a un profesional habilitado con una
prestación abierta para poder observar el formulario de nueva entrega.

Sin opciones adicionales compara el producto con estilos efímeros, guardando sus
reglas y geometría. `completed: true` en ese modo solo acredita que el experimento
terminó; no demuestra que una variante haya corregido el problema.

Con `--assert-layout` usa únicamente el producto actual, sin estilos efímeros, y
falla si la página o el modal desbordan el ancho del documento o si un control
sale horizontalmente del diálogo. Registra `layout_assertions: true`; no sustituye
el recorrido funcional completo de `--phase all`.

## Webpay oficial en sandbox

Antes de reanudar un checkout conservado se puede consultar su estado sin iniciar
Django, PostgreSQL ni el navegador:

```powershell
& 'C:\Users\felip\Downloads\skilly\.venv\Scripts\python.exe' -B 'C:\Users\felip\Downloads\skilly\tools\webpay_estado_sandbox.py' 'C:\ruta\externa\checkout_privado.json'
```

La herramienta permite únicamente GET al endpoint oficial de integración, usa
el contexto TLS verificado del cliente y bloquea proxies/redirecciones. No lee
`.env` ni conecta a BD. Recibe el archivo privado, nunca el token por CLI. Guarda
estado HTTP, estado de transacción reconocido y hash de respuesta; no conserva
el cuerpo, identificadores de compra ni datos de tarjeta. Soporta rutas largas
locales de Windows sin cambiar políticas globales y rechaza rutas de red.

`INITIALIZED` no demuestra expiración ni autorización. Incluso un GET que devuelva
`AUTHORIZED` no verifica por sí solo monto, orden, sesión o retorno de SKILLY.
La [consulta de estado oficial](https://proyecto-ejemplo-node.transbankdevelopers.cl/api-reference/webpay-plus)
es distinta del callback del comercio: **no usar `/api/pagos/webpay/retorno/`
como diagnóstico de lectura**, porque ese endpoint puede confirmar mediante PUT.

Sus pruebas offline se ejecutan con `python -B -m unittest discover -s tools/tests
-p test_webpay_estado_sandbox.py -v`; el transporte está simulado. No se suman
a las pruebas de integración real con Webpay.

`e2e_webpay_sandbox_aislado.mjs` es un recorrido independiente. Requiere un
contexto dedicado preparado fuera de Git; no inicia servidores ni crea fixtures.
Comprueba `isolated: true`, `sandbox_transport: true`, PostgreSQL de copia en
57647, frontend lógico `http://localhost:5173` y backend loopback distinto de
8000. Verifica identidad del backend, del proxy y del navegador antes de utilizar
una referencia privada. El servidor de ensayo debe impedir salidas excepto su
PostgreSQL y el endpoint HTTPS oficial de integración con TLS verificado.

El transporte local usa IPv4 con Host localhost. Edge resuelve localhost a
127.0.0.1 solo dentro de su perfil temporal; no cambia DNS global, puertos del
producto ni procesos ajenos. El navegador bloquea los demás orígenes. Las
acciones de este driver invocan controles DOM; no se les atribuye la evidencia
de eventos táctiles confiables del recorrido general.

Obtiene los ejemplos sintéticos desde la documentación oficial de Transbank.
La evidencia sanitizada contiene origen, estado HTTP, hash y banderas de parseo;
los valores permanecen en memoria y archivos privados externos. Nunca se deben
utilizar tarjetas reales ni publicar `datos_sandbox_privados.json`,
`checkout_privado.json` o las fixtures.

Para un primer intento se pasa la ruta absoluta del contexto dedicado. Si existe
un checkout pendiente, se reutiliza con `--resume-checkout`:

```powershell
& 'C:\Program Files\nodejs\node.exe' 'C:\Users\felip\Downloads\skilly\tools\e2e_webpay_sandbox_aislado.mjs' 'C:\ruta\externa\contexto.json' --resume-checkout 'C:\ruta\externa\checkout_privado.json'
```

La reanudación exige un POST previo y ninguna confirmación PUT. No debe repetirse
el inicio para sortear un fallo de UI. Solo `completed: true` junto con
`authorization_verified: true` acredita el escenario: retorno real del proveedor,
pago RETENIDO en la copia, un POST y un PUT HTTPS, y callback duplicado sin una
segunda confirmación. Un checkout creado o una prueba de parser no acreditan
autorización. Un desafío humano o destino no permitido detiene el recorrido.

Las pruebas offline de privacidad, parseo y reconocimiento de formularios usan
datos ficticios y metadatos; se ejecutan con `node --test tools/tests/*.test.mjs`
(en PowerShell se pueden pasar explícitamente los tres archivos). No equivalen
a integración con Webpay. El escenario sandbox tampoco acredita pagos, reversas,
conciliación o liquidaciones productivos.
