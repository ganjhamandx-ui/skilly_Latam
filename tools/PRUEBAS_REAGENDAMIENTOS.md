# Pruebas de interfaz de reagendamientos

`pruebas_reagendamientos_navegador.mjs` ejecuta Edge headless por CDP contra
un contexto temporal ya iniciado. Requiere Node, Edge, las dependencias del
frontend y una copia PostgreSQL aislada con las guardias y la fixture privada
del entorno de pruebas. No inicia ni cambia la base operativa.

Ejemplo desde PowerShell, con rutas absolutas:

```powershell
& 'C:\Program Files\nodejs\node.exe' `
  'C:\Users\felip\Downloads\skilly\tools\pruebas_reagendamientos_navegador.mjs' `
  'C:\Users\felip\Downloads\skilly\.skilly-active-context.tmp' `
  --before-ref eb22b8c
```

El argumento `--before-ref` es obligatorio y acepta un SHA Git local, de 7 a
40 caracteres, anterior al cambio que se quiere comparar. `eb22b8c` conserva
la interfaz anterior a las correcciones de reagendamiento de esta tanda.
Se leen exclusivamente los dos JSX necesarios mediante `git show`, sin
checkout, archivos temporales de producto ni modificación del árbol de trabajo.
Vite/OXC compila esa fuente en memoria; el navegador la recibe en dos rutas
sintéticas de la prueba. Sus restantes componentes y estilos se resuelven
desde la fuente actual: las capturas comparan estos dos componentes, no
reconstruyen el frontend completo de otra revisión.

La sesión y la lectura del portal usan React, Django y PostgreSQL reales de
la copia. Se guardan cuatro capturas, antes/después en 1366 y 390 px, junto
con posiciones de título y avisos, medidas de desbordamiento y hashes de la
fuente anterior. Las credenciales de la fixture solo se leen en memoria y
los correos visibles se ocultan antes de capturar.

`harness_reagendamientos.js` se ejecuta por separado dentro de ese navegador.
Usa los componentes React y DOM reales con `fetch` simulado para comprobar
carga, error, vacío confirmado, recuperación, conservación de motivos,
acciones con datos pendientes y doble envío en los tres roles. Esas
comprobaciones no acreditan transiciones reales en PostgreSQL.

El resultado y las capturas quedan en una carpeta única dentro de `run_dir`,
fuera del repositorio. El driver bloquea solicitudes ajenas a los dos orígenes
locales del contexto, comprueba su identidad/puerto PostgreSQL y verifica que
los archivos de producto no cambiaron durante el ensayo. No realiza pagos,
envíos, scanners ni mediciones de cobertura. Un fallo conserva el resultado
y devuelve un código de salida distinto de cero.
