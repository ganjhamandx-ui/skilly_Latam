// UI real de Portal antes/después, con autenticación y lecturas de la copia.
// El harness separado usa React/DOM reales y respuestas HTTP simuladas.
// Sin scanners, cobertura, servicios externos ni modificaciones del producto.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { randomUUID, createHash } from 'node:crypto'
import { execFile, spawn } from 'node:child_process'
import { promisify } from 'node:util'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const contextPath = process.argv[2]
if (!contextPath || !path.isAbsolute(contextPath)) throw new Error('Se requiere un contexto absoluto aislado')
const beforeRefIndex = process.argv.indexOf('--before-ref')
const beforeRef = beforeRefIndex > 2 ? process.argv[beforeRefIndex + 1] : null
if (!beforeRef || !/^[a-f0-9]{7,40}$/i.test(beforeRef)) throw new Error('Se requiere --before-ref con el SHA del commit anterior al cambio de interfaz')
const git = async args => (await promisify(execFile)('git', ['-C', root, ...args], { encoding: 'utf8', windowsHide: true, maxBuffer: 5 * 1024 * 1024 })).stdout
const beforeCommit = (await git(['rev-parse', '--verify', beforeRef + '^{commit}'])).trim()
if (!/^[a-f0-9]{40}$/i.test(beforeCommit)) throw new Error('El commit anterior no existe localmente')
const ctx = JSON.parse(await fs.readFile(contextPath, 'utf8'))
const runDir = await fs.realpath(ctx.run_dir)
const inside = (base, file) => { const rel = path.relative(base, file); return !!rel && !rel.startsWith('..') && !path.isAbsolute(rel) }
if (inside(root, runDir) || runDir === root || ctx.isolated !== true) throw new Error('La evidencia debe quedar fuera del repositorio')
function localOrigin(value) {
  const u = new URL(value)
  if (u.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(u.hostname) || !u.port ||
      ['8000', '5173', '5432', '9000'].includes(u.port) || u.username || u.password || u.pathname !== '/' || u.search || u.hash) throw new Error('Origen no aislado')
  return u.origin
}
const origin = localOrigin(ctx.frontend_origin), backend = localOrigin(ctx.backend_origin)
if (!Number.isInteger(ctx.database_port) || ctx.database_port === 5432 || ctx.database_port < 1 || ctx.database_port > 65535) throw new Error('PostgreSQL no aislado')
const health = await (await fetch(backend + '/__isolated/health', { redirect: 'error' })).json()
if (health.isolated !== true || health.run_id !== ctx.run_id || health.database_port !== ctx.database_port) throw new Error('Guardia de aislamiento rechazada')
const fixture = JSON.parse(await fs.readFile(path.join(runDir, 'fixture_privado.json'), 'utf8'))
if (localOrigin(fixture.origin) !== origin || !fixture.professional_ui?.email || !fixture.professional_ui?.password) throw new Error('Falta fixture profesional aislada')
const secrets = [fixture.control, fixture.professional_ui.email, fixture.professional_ui.password].filter(Boolean)
function sanitize(value) {
  let result = String(value)
  for (const secret of secrets) result = result.replaceAll(secret, '<oculto>')
  return result.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '<correo>').slice(0, 400)
}
const sourceFiles = ['frontend/src/PortalProfesional.jsx', 'frontend/src/ReagendamientosSkilly.jsx', 'frontend/src/reagendamientosApi.mjs']
const hashes = new Map(await Promise.all(sourceFiles.map(async file => [file, createHash('sha256').update(await fs.readFile(path.join(root, file))).digest('hex')])))
const { transformWithOxc } = await import(pathToFileURL(path.join(root, 'frontend/node_modules/vite/dist/node/index.js')).href)
const beforeFiles = new Map()
const beforeHashes = {}
for (const file of ['PortalProfesional.jsx', 'ReagendamientosSkilly.jsx']) {
  const source = await git(['show', beforeCommit + ':frontend/src/' + file])
  beforeHashes[file] = createHash('sha256').update(source).digest('hex')
  beforeFiles.set('/__ux_before/' + file, (await transformWithOxc(source, file, { jsx: { runtime: 'automatic', importSource: 'react' }, sourcemap: false })).code)
}
const harness = await fs.readFile(path.join(root, 'tools/harness_reagendamientos.js'), 'utf8')
const out = path.join(runDir, 'ux_reagendamientos_' + randomUUID().replaceAll('-', ''))
await fs.mkdir(out)
const checks = [], captures = [], errors = [], blocked = [], javascriptErrors = []
let browser, ws, stage = 'inicio', port, call, evaluate, deps, beforeReadStatus
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(fn, label, timeout = 20000) {
  const start = Date.now()
  while (Date.now() - start < timeout) { if (await fn()) return; await delay(50) }
  throw new Error(label)
}
function check(name, passed) { checks.push({ name, passed: !!passed }); if (!passed) throw new Error(name) }
function compileImports(code) {
  return code
    .replace(/from\s+(["'])\.\/(ReagendamientosSkilly\.jsx)\1/g, 'from "/__ux_before/$2"')
    .replace(/from\s+(["'])\.\/([^"']+)\1/g, 'from "/src/$2"')
    .replace(/import\s+(["'])\.\/([^"']+)\1/g, 'import "/src/$2"')
    .replace(/import\s*\{([^}]+)\}\s*from\s*(["'])(react|react-dom|react\/jsx-runtime)\2\s*;?/g, (_, imported, _quote, name) => {
      const key = name === 'react' ? 'React' : name === 'react-dom' ? 'ReactDOM' : 'JSX'
      const bindings = imported.replace(/\s+as\s+/g, ': ')
      return `import __ux${key} from ${JSON.stringify(deps[name])}; const {${bindings}} = __ux${key};`
    })
}
async function navigate(route) {
  const marker = randomUUID()
  const hook = await call('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__uxMarker=' + JSON.stringify(marker) })
  await call('Page.navigate', { url: origin + route })
  await until(() => evaluate('window.__uxMarker===' + JSON.stringify(marker)), 'navegacion_incompleta')
  await call('Page.removeScriptToEvaluateOnNewDocument', { identifier: hook.identifier })
  await until(() => evaluate("document.readyState==='complete'&&!!document.querySelector('main')"), 'pagina_no_lista')
}
async function fill(selector, value) {
  await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))})()`)
}
async function screenshot(label, scope) {
  await evaluate(`(()=>{const scope=document.querySelector(${JSON.stringify(scope)});const walk=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);const nodes=[];while(walk.nextNode())nodes.push(walk.currentNode);for(const n of nodes){if(['SCRIPT','STYLE'].includes(n.parentElement?.tagName))continue;n.nodeValue=n.nodeValue.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}/g,'[correo]')}window.scrollTo(0,0)})()`)
  const geometry = await evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(scope)});const a=r.querySelector('h1').getBoundingClientRect(),b=r.querySelector('.rea-panel').getBoundingClientRect();return{titulo_top:a.top,avisos_top:b.top,ancho_documento:document.documentElement.scrollWidth,ancho_ventana:innerWidth}})()`)
  const shot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
  await fs.writeFile(path.join(out, label + '.png'), Buffer.from(shot.data, 'base64'), { flag: 'wx' })
  captures.push({ label, ...geometry })
  return geometry
}
try {
  browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-sync', '--disable-extensions', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--user-data-dir=' + path.join(out, 'profile'), 'about:blank'], { stdio: 'ignore', windowsHide: true })
  await until(async () => { try { port = Number((await fs.readFile(path.join(out, 'profile/DevToolsActivePort'), 'utf8')).split('\n')[0]); return !!port } catch { return false } }, 'edge_no_iniciado')
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`, { redirect: 'error' })).json()
  const target = targets.find(t => t.type === 'page')
  if (!target) throw new Error('objetivo_edge_no_disponible')
  ws = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0
  const pending = new Map()
  call = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id
    const timer = setTimeout(() => { pending.delete(n); reject(new Error('cdp_timeout_' + method)) }, 30000)
    pending.set(n, { resolve, reject, timer })
    ws.send(JSON.stringify({ id: n, method, params }))
  })
  ws.addEventListener('message', event => {
    const m = JSON.parse(event.data)
    if (m.id) {
      const p = pending.get(m.id)
      if (p) { pending.delete(m.id); clearTimeout(p.timer); m.error ? p.reject(new Error('cdp_rechazado_' + m.error.code)) : p.resolve(m.result) }
    }
    if (m.method === 'Fetch.requestPaused') {
      let allowed = false, synthetic
      try {
        const u = new URL(m.params.request.url)
        allowed = [origin, backend].includes(u.origin) || ['data:', 'blob:'].includes(u.protocol)
        synthetic = u.origin === origin && beforeFiles.get(u.pathname)
      } catch { /* fail closed */ }
      const promise = synthetic && deps
        ? call('Fetch.fulfillRequest', { requestId: m.params.requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'text/javascript; charset=utf-8' }], body: Buffer.from(compileImports(synthetic)).toString('base64') })
        : allowed ? call('Fetch.continueRequest', { requestId: m.params.requestId })
          : (blocked.push({ stage, kind: 'origen_no_autorizado' }), call('Fetch.failRequest', { requestId: m.params.requestId, errorReason: 'BlockedByClient' }))
      promise.catch(() => {})
    }
    if (m.method === 'Runtime.exceptionThrown') javascriptErrors.push({ stage, kind: 'javascript_exception' })
    if (m.method === 'Network.responseReceived' && stage === 'capturas_antes_fuente_previa') {
      const u = new URL(m.params.response.url)
      if (u.origin === origin && u.pathname === '/api/reagendamientos/profesional/') beforeReadStatus = m.params.response.status
    }
  })
  evaluate = async expression => {
    const r = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error('evaluacion_rechazada: ' + sanitize(r.exceptionDetails.exception?.description || r.exceptionDetails.text))
    return r.result.value
  }
  await call('Runtime.enable'); await call('Page.enable'); await call('Network.enable')
  await call('Fetch.enable', { patterns: [{ urlPattern: '*' }] })
  await call('Emulation.setDeviceMetricsOverride', { width: 1366, height: 1000, deviceScaleFactor: 1, mobile: false })
  stage = 'autenticacion_real'
  await navigate('/acceso-profesional')
  await until(() => evaluate("!!document.querySelector('#ap-correo')"), 'formulario_acceso_no_disponible')
  await fill('#ap-correo', fixture.professional_ui.email)
  await fill('#ap-contrasena', fixture.professional_ui.password)
  await evaluate("document.querySelector('.ap-formulario').requestSubmit()")
  await until(() => evaluate("location.pathname==='/portal-profesional'&&!!document.querySelector('.pp-introduccion h1')"), 'acceso_real_no_completado')
  await until(() => evaluate("!!document.querySelector('.rea-panel[aria-busy=false]')"), 'avisos_reales_no_listos')
  check('sesion_y_lectura_portal_reales', await evaluate("!document.querySelector('.rea-panel [role=alert]')"))
  deps = await evaluate(`(()=>{const names=performance.getEntriesByType('resource').map(r=>r.name);const find=n=>names.find(u=>new URL(u).pathname==='/node_modules/.vite/deps/'+n);const react=find('react.js');return{'react':react,'react-dom':find('react-dom.js'),'react/jsx-runtime':new URL('/node_modules/.vite/deps/react_jsx-runtime.js'+new URL(react).search,location.origin).href}})()`)
  if (!deps.react || !deps['react-dom']) throw new Error('dependencias_reales_no_identificadas')
  stage = 'capturas_antes_fuente_previa'
  await evaluate(`(async()=>{const React=(await import(${JSON.stringify(deps.react)})).default;const files=performance.getEntriesByType('resource').map(r=>r.name);const domUrl=files.find(u=>new URL(u).pathname==='/node_modules/.vite/deps/react-dom_client.js');const dom=await import(domUrl);const before=(await import('/__ux_before/PortalProfesional.jsx')).default;document.getElementById('root').hidden=true;const host=document.createElement('div');host.id='ux-before-host';document.body.appendChild(host);window.__uxBeforeRoot=(dom.createRoot||dom.default.createRoot)(host);window.__uxBeforeRoot.render(React.createElement(before))})()`)
  await until(() => evaluate("!!document.querySelector('#ux-before-host .pp-introduccion h1')&&!document.querySelector('#ux-before-host .rea-panel [role=alert]')&&!!document.querySelector('#ux-before-host .rea-panel p')"), 'portal_previo_no_listo')
  await until(() => beforeReadStatus !== undefined, 'sin_respuesta_real_avisos_previos')
  check('consulta_avisos_fuente_previa_real', beforeReadStatus === 200)
  await delay(300)
  for (const [label, width, height] of [['escritorio', 1366, 1000], ['movil', 390, 844]]) {
    await call('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width === 390 })
    await delay(100)
    const g = await screenshot('portal_antes_' + label, '#ux-before-host')
    check('antes_registra_avisos_precediendo_titulo_' + label, g.avisos_top < g.titulo_top)
    check('antes_sin_desborde_' + label, g.ancho_documento <= g.ancho_ventana)
  }
  await evaluate("window.__uxBeforeRoot.unmount();document.getElementById('ux-before-host').remove();document.getElementById('root').hidden=false")
  stage = 'capturas_despues_portal_real'
  for (const [label, width, height] of [['escritorio', 1366, 1000], ['movil', 390, 844]]) {
    await call('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width === 390 })
    await delay(100)
    const g = await screenshot('portal_despues_' + label, '#root')
    check('despues_titulo_precede_avisos_' + label, g.titulo_top < g.avisos_top)
    check('despues_sin_desborde_' + label, g.ancho_documento <= g.ancho_ventana)
  }
  stage = 'harness_react_respuestas_simuladas'
  const result = await evaluate(harness)
  check('harness_finalizado', result.aprobado === true)
  for (const item of result.checks) check(item.nombre, item.aprobado)
  stage = 'integridad_fuentes'
  for (const [file, hash] of hashes) check('sin_cambios_durante_prueba_' + file, createHash('sha256').update(await fs.readFile(path.join(root, file))).digest('hex') === hash)
  check('sin_excepciones_javascript', javascriptErrors.length === 0)
} catch (error) {
  errors.push({ stage, kind: error.name, diagnostic: sanitize(error.message) })
} finally {
  try { ws?.close() } catch { /* Own connection only. */ }
  if (browser) { browser.kill(); await delay(200) }
  const result = {
    completed: !errors.length, stage, isolated: true, run_id: ctx.run_id,
    checks, passed: checks.filter(c => c.passed).length, failed: checks.filter(c => !c.passed).length,
    captures, errors, javascript_errors: javascriptErrors, blocked_requests: blocked,
    before_commit: beforeCommit, before_source_hashes: beforeHashes,
    real: ['Edge', 'React/DOM', 'login/sesión/GET Django-PostgreSQL aislado', 'capturas con fuente anterior y ruta actual'],
    simulated: ['respuestas del harness de carga/error/reintentos/doble envío'],
    external_services: false, original_database_modified: false, source_files_modified: false,
  }
  await fs.writeFile(path.join(out, 'resultado.json'), JSON.stringify(result, null, 2), { flag: 'wx' })
  console.log(JSON.stringify({ output: out, completed: result.completed, passed: result.passed, failed: result.failed, stage, errors }))
  if (!result.completed) process.exitCode = 1
}
