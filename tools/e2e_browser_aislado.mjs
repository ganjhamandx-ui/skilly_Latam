// Recorridos funcionales React -> HTTP -> Django/PostgreSQL en copia aislada.
// No ejecuta scanners/cobertura; no llama proveedores externos ni carga .env.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID, randomBytes, createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { homedir } from 'node:os'
import { onboarding, publicacion } from './e2e_browser_profesional.mjs'
import { ciclos } from './e2e_browser_ciclos.mjs'
import { seguridad } from './e2e_browser_seguridad.mjs'
import { layout } from './e2e_browser_layout.mjs'
import { adminMovil } from './e2e_browser_admin_movil.mjs'
import { sesionesMoviles } from './e2e_browser_sesiones_movil.mjs'

async function main() {
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const contextPath = process.argv[2]
if (!contextPath || !path.isAbsolute(contextPath)) throw new Error('Falta contexto absoluto aislado')
const ctx = JSON.parse(await fs.readFile(contextPath, 'utf8'))
const runDir = await fs.realpath(ctx.run_dir)
const relative = path.relative(root, runDir)
if (!relative.startsWith('..') || !ctx.isolated && ctx.isolated !== undefined) throw new Error('La evidencia debe permanecer fuera del repositorio')
function localOrigin(value) {
  const u = new URL(value)
  if (u.protocol !== 'http:' || !['localhost', '127.0.0.1', '[::1]'].includes(u.hostname) || !u.port ||
      ['8000', '5173', '5432', '9000'].includes(u.port) || u.username || u.password || u.pathname !== '/' || u.search || u.hash) throw new Error('Origen no autorizado')
  return u.origin
}
const origin = localOrigin(ctx.frontend_origin), backend = localOrigin(ctx.backend_origin)
if (!Number.isInteger(ctx.database_port) || ctx.database_port === 5432 || ctx.database_port < 1 || ctx.database_port > 65535) throw new Error('Puerto PostgreSQL no aislado')
const health = await (await fetch(backend + '/__isolated/health', { redirect: 'error' })).json()
if (health.isolated !== true || health.run_id !== ctx.run_id || health.database_port !== ctx.database_port) throw new Error('Guardia de aislamiento fallida')
// Verificar el proxy real ANTES de leer credenciales o enviar cualquier POST desde React.
const proxyResponse = await fetch(origin + '/api/__isolated/health', { redirect: 'error', headers: { Accept: 'application/json' } })
if (proxyResponse.status !== 200) throw new Error('Guardia del proxy frontend no disponible')
const proxyHealth = await proxyResponse.json()
if (proxyHealth.isolated !== true || proxyHealth.run_id !== health.run_id || proxyHealth.database_port !== health.database_port) throw new Error('El proxy frontend no pertenece al entorno aislado')
const fixture = JSON.parse(await fs.readFile(path.join(runDir, 'fixture_privado.json'), 'utf8'))
if (localOrigin(fixture.origin) !== origin || typeof fixture.control !== 'string' || !fixture.control) throw new Error('Fixture aislada incompatible')
const out = path.join(runDir, 'browser_e2e_' + randomUUID().replaceAll('-', ''))
await fs.mkdir(out)
const androidIndex = process.argv.indexOf('--android-context')
let android = null
if (androidIndex >= 0) {
  const descriptor = process.argv[androidIndex + 1]
  if (!descriptor || !path.isAbsolute(descriptor) || path.basename(descriptor) !== 'contexto_android.json') throw new Error('contexto_android_invalido')
  const file = await fs.realpath(descriptor), backup = await fs.realpath(path.dirname(runDir))
  const descriptorRelative = path.relative(backup, file)
  if (!descriptorRelative || descriptorRelative.startsWith('..') || path.isAbsolute(descriptorRelative) || (await fs.stat(file)).size > 65536) throw new Error('contexto_android_fuera_del_respaldo')
  const candidate = JSON.parse(await fs.readFile(file, 'utf8'))
  const androidRun = await fs.realpath(candidate.run_dir)
  const adb = await fs.realpath(candidate.adb)
  const sdk = await fs.realpath(path.join(homedir(), 'AppData', 'Local', 'Android', 'Sdk'))
  const adbRelative = path.relative(sdk, adb)
  if (path.dirname(file) !== androidRun || !path.basename(androidRun).startsWith('android_ejecucion_') ||
      candidate.read_only_avd !== true || !/^emulator-[0-9]+$/.test(candidate.serial || '') ||
      !Number.isInteger(candidate.cdp_port) || candidate.cdp_port < 1024 || candidate.cdp_port > 65535 ||
      [8000, 5173, 5432, 9000, ctx.database_port].includes(candidate.cdp_port) ||
      !adbRelative || adbRelative.startsWith('..') || path.isAbsolute(adbRelative) ||
      path.basename(adb).toLowerCase() !== 'adb.exe' || path.basename(path.dirname(adb)) !== 'platform-tools') throw new Error('identidad_android_rechazada')
  android = { ...candidate, run_dir: androidRun, adb, context_path: file }
}
const mobile = !!android || process.argv.includes('--mobile')
// En Android no se inventan dimensiones, DPR ni capacidad tactil. Se registran
// las metricas efectivas de cada pagina tras cargar su viewport meta real.
let viewport = android ? { native: true, mobile: true } : mobile ? { width: 390, height: 844, deviceScaleFactor: 1, mobile: true } : { width: 1366, height: 1000, deviceScaleFactor: 1, mobile: false }
async function gitRead(args) {
  return new Promise((resolve, reject) => {
    const processGit = spawn('git', ['-C', root, ...args], { stdio: ['ignore', 'pipe', 'ignore'], windowsHide: true })
    const chunks = []
    processGit.stdout.on('data', chunk => chunks.push(chunk))
    processGit.once('error', () => reject(new Error('metadatos_git_no_disponibles')))
    processGit.once('close', code => code === 0 ? resolve(Buffer.concat(chunks).toString('utf8')) : reject(new Error('metadatos_git_rechazados')))
  })
}
async function sourceSnapshot() {
  const gitHead = (await gitRead(['rev-parse', 'HEAD'])).trim()
  if (!/^[a-f0-9]{40}$/.test(gitHead)) throw new Error('identidad_commit_invalida')
  const tracked = (await gitRead(['ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', 'backend', 'frontend'])).split('\0').filter(name =>
    (name.startsWith('backend/') || name.startsWith('frontend/src/') || ['frontend/package.json', 'frontend/package-lock.json', 'frontend/index.html', 'frontend/vite.config.js'].includes(name)) && /\.(?:py|mjs|js|jsx|css|json|html|sql)$/.test(name)).sort()
  const harness = ['tools/e2e_browser_aislado.mjs', 'tools/e2e_browser_profesional.mjs', 'tools/e2e_browser_ciclos.mjs', 'tools/e2e_browser_seguridad.mjs', 'tools/e2e_browser_layout.mjs', 'tools/e2e_browser_admin_movil.mjs', 'tools/e2e_browser_sesiones_movil.mjs', 'tools/android_selector_archivo.py']
  const files = []
  for (const name of [...tracked, ...harness].sort()) {
    const file = await fs.realpath(path.join(root, name))
    const relativeFile = path.relative(root, file)
    if (!relativeFile || relativeFile.startsWith('..') || path.isAbsolute(relativeFile)) throw new Error('fuente_fuera_del_repositorio')
    files.push({ path: name, sha256: createHash('sha256').update(await fs.readFile(file)).digest('hex'), kind: name.startsWith('tools/') ? 'harness' : 'producto' })
  }
  return { git_head: gitHead, files }
}
const sourcesBefore = await sourceSnapshot()
await fs.writeFile(path.join(out, 'fuentes_antes.json'), JSON.stringify(sourcesBefore, null, 2), { flag: 'wx' })
const checks = [], interventions = [], errors = []
const secrets = new Set([fixture.control, fixture.admin.email, fixture.admin.password, fixture.professional_ui?.email, fixture.professional_ui?.password])
const phaseIndex = process.argv.indexOf('--phase')
const phase = phaseIndex >= 0 ? process.argv[phaseIndex + 1] : 'professional'
if (!['professional', 'cycles', 'permissions', 'layout', 'mobile-extra', 'all'].includes(phase)) throw new Error('Fase de recorrido invalida')
if (phase === 'mobile-extra' && !android) throw new Error('Fase exclusiva de Android')
const assertLayout = process.argv.includes('--assert-layout') || !!android && ['layout', 'all'].includes(phase)
if (assertLayout && phase !== 'layout' && !(android && phase === 'all')) throw new Error('Las aserciones de layout requieren su fase de lectura')
const resumeIndex = process.argv.indexOf('--resume')
const resumePath = resumeIndex >= 0 ? process.argv[resumeIndex + 1] : null
let state = { professional: { email: 'ui-' + randomUUID().replaceAll('-', '') + '@example.invalid', password: randomBytes(32).toString('base64url') } }
let previousEvidence = null, previousChecks = []
if (resumePath) {
  if (!path.isAbsolute(resumePath) || path.basename(resumePath) !== 'fixture_privado.json') throw new Error('Fixture de reanudacion invalida')
  const realResume = await fs.realpath(resumePath), backupParent = await fs.realpath(path.dirname(runDir))
  const resumeRelative = path.relative(backupParent, realResume)
  if (!resumeRelative || resumeRelative.startsWith('..') || path.isAbsolute(resumeRelative)) throw new Error('Fixture fuera del respaldo aislado')
  state = JSON.parse(await fs.readFile(realResume, 'utf8'))
  const previous = JSON.parse(await fs.readFile(path.join(path.dirname(realResume), 'resultado.json'), 'utf8'))
  if (previous.isolated !== true || !state.professional?.email?.endsWith('@example.invalid') || !state.professional?.password) throw new Error('Reanudacion no sintetica')
  previousEvidence = path.join(path.dirname(realResume), 'resultado.json')
  previousChecks = [...(previous.inherited_checks || []), ...previous.checks].filter(c => c.passed)
}
secrets.add(state.professional.email); secrets.add(state.professional.password)
await fs.writeFile(path.join(out, 'fixture_privado.json'), JSON.stringify(state), { flag: 'wx' })
const pdf = path.join(out, 'documento-sintetico.pdf')
await fs.writeFile(pdf, '%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n', { flag: 'wx' })
const badFile = path.join(out, 'documento-rechazable.exe')
await fs.writeFile(badFile, 'synthetic-invalid-upload', { flag: 'wx' })
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
const inside = (base, candidate) => { const rel = path.relative(base, candidate); return rel && !rel.startsWith('..') && !path.isAbsolute(rel) }
const androidRemoteFiles = new Map()
const androidEnvironment = android ? { kind: 'android_emulator', physical_device: false, viewport_emulated: false, serial: android.serial } : null
function adbCall(args) {
  if (!android) throw new Error('adb_fuera_de_android')
  return new Promise((resolve, reject) => {
    const command = spawn(android.adb, ['-s', android.serial, ...args], { stdio: ['ignore', 'pipe', 'ignore'], windowsHide: true })
    const chunks = []; let bytes = 0
    const timer = setTimeout(() => { command.kill(); reject(new Error('adb_android_timeout')) }, 25000)
    command.stdout.on('data', chunk => { bytes += chunk.length; if (bytes > 65536) { command.kill(); reject(new Error('adb_android_respuesta_excesiva')) } else chunks.push(chunk) })
    command.once('error', () => { clearTimeout(timer); reject(new Error('adb_android_no_disponible')) })
    command.once('close', code => { clearTimeout(timer); code === 0 ? resolve(Buffer.concat(chunks).toString('utf8')) : reject(new Error('adb_android_operacion_rechazada')) })
  })
}
function checkedBrowserSocket(value) {
  const url = new URL(value)
  if (url.protocol !== 'ws:' || !['127.0.0.1', 'localhost'].includes(url.hostname) || Number(url.port) !== port || url.username || url.password || url.search || url.hash || !url.pathname.startsWith('/devtools/')) throw new Error('socket_cdp_fuera_del_puerto_propio')
  return url.href
}
function clean(value) { let result = String(value); for (const secret of secrets) if (secret) result = result.replaceAll(secret, '<redacted>'); return result.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '<correo>') }
async function until(fn, code, timeout = 25000) {
  const start = Date.now()
  while (Date.now() - start < timeout) { if (await fn()) return; await delay(80) }
  throw new Error(code || 'espera_agotada')
}
function check(name, passed, extra = {}) {
  checks.push({ name, passed: !!passed, ...extra })
  if (!passed) throw new Error(name)
}
async function persist() { await fs.writeFile(path.join(out, 'fixture_privado.json'), JSON.stringify(state)); }
async function clock(now) {
  interventions.push({ kind: 'reloj_sintetico', now: now ? 'futuro' : 'real_restaurado' })
  const response = await fetch(backend + '/__isolated/clock', { method: 'POST', redirect: 'error', headers: { 'Content-Type': 'application/json', 'X-Isolated-Control': fixture.control }, body: JSON.stringify({ now }) })
  if (response.status !== 200) throw new Error('reloj_aislado_rechazado')
}
let browser, port, stage = 'inicio', clockReset = false
const actors = [], ownedContexts = []
async function actor(name) {
  // Un contexto nuevo por actor conserva cookies/CSRF separados.
  const browserTarget = await (await fetch(`http://127.0.0.1:${port}/json/version`, { redirect: 'error' })).json()
  if (android && (!/^Chrome\//.test(browserTarget.Browser || '') || !/Android.*Mobile/.test(browserTarget['User-Agent'] || ''))) throw new Error('chrome_android_no_acreditado')
  const browserWs = new WebSocket(checkedBrowserSocket(browserTarget.webSocketDebuggerUrl))
  await new Promise((resolve, reject) => { browserWs.addEventListener('open', resolve, { once: true }); browserWs.addEventListener('error', reject, { once: true }) })
  let bid = 0
  const bp = new Map()
  browserWs.addEventListener('message', event => { const m = JSON.parse(event.data); const p = bp.get(m.id); if (p) { bp.delete(m.id); clearTimeout(p.timer); m.error ? p.reject(new Error('cdp_browser')) : p.resolve(m.result) } })
  const bc = (method, params = {}) => new Promise((resolve, reject) => { const id = ++bid; const timer = setTimeout(() => reject(new Error('cdp_browser_timeout')), 15000); bp.set(id, { resolve, reject, timer }); browserWs.send(JSON.stringify({ id, method, params })) })
  let browserContextId
  try { ({ browserContextId } = await bc('Target.createBrowserContext', android ? { disposeOnDetach: true } : {})) }
  catch { browserWs.close(); throw new Error(android ? 'android_no_admite_sesiones_separadas_por_rol' : 'contexto_browser_no_disponible') }
  if (!browserContextId) { browserWs.close(); throw new Error('contexto_browser_sin_identidad') }
  ownedContexts.push({ browserContextId, bc, browserWs })
  const { targetId } = await bc('Target.createTarget', { url: 'about:blank', browserContextId })
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`, { redirect: 'error' })).json()
  const target = targets.find(t => t.id === targetId)
  if (!target) throw new Error('objetivo_cdp_no_disponible')
  const ws = new WebSocket(checkedBrowserSocket(target.webSocketDebuggerUrl))
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0, dialogs = 0, inputSequence = 0
  const inputRecords = []
  const pending = new Map(), requests = new Map(), responses = [], network = new Set()
  const call = (method, params = {}) => new Promise((resolve, reject) => { const n = ++id; const timer = setTimeout(() => { pending.delete(n); reject(new Error('cdp_timeout')) }, 15000); pending.set(n, { resolve, reject, timer }); ws.send(JSON.stringify({ id: n, method, params })) })
  ws.addEventListener('message', event => {
    const m = JSON.parse(event.data)
    if (m.id) { const p = pending.get(m.id); if (p) { pending.delete(m.id); clearTimeout(p.timer); m.error ? p.reject(new Error('cdp_rechazado')) : p.resolve(m.result) } }
    if (m.method === 'Fetch.requestPaused') {
      let allowed = false
      try {
        const u = new URL(m.params.request.url)
        allowed = [origin, backend].includes(u.origin) || ['data:', 'blob:'].includes(u.protocol)
        if (phase === 'layout' && !['GET', 'HEAD', 'OPTIONS'].includes(m.params.request.method) &&
            !(u.pathname === '/api/acceso/iniciar-sesion/' && m.params.request.method === 'POST')) allowed = false
      } catch { /* fail closed */ }
      const op = allowed ? call('Fetch.continueRequest', { requestId: m.params.requestId }) : call('Fetch.failRequest', { requestId: m.params.requestId, errorReason: 'BlockedByClient' })
      op.catch(() => {})
    }
    if (m.method === 'Page.javascriptDialogOpening') { dialogs++; call('Page.handleJavaScriptDialog', { accept: true }).catch(() => {}) }
    if (m.method === 'Runtime.bindingCalled' && m.params.name === '__skillyRecordInput') {
      try { inputRecords.push({ ...JSON.parse(m.params.payload), sequence: ++inputSequence }) } catch { /* Ignore invalid observer messages. */ }
    }
    if (m.method === 'Runtime.exceptionThrown') errors.push({ actor: name, stage, kind: 'javascript_exception' })
    if (m.method === 'Network.requestWillBeSent') { const r = m.params.request; requests.set(m.params.requestId, { method: r.method, url: r.url }); if (/\/api\//.test(r.url)) network.add(m.params.requestId) }
    if (m.method === 'Network.responseReceived') {
      const r = requests.get(m.params.requestId), response = m.params.response
      if (r && new URL(response.url).origin === origin && new URL(response.url).pathname.startsWith('/api/')) {
        const entry = { method: r.method, path: new URL(response.url).pathname, status: response.status, requestId: m.params.requestId, body: undefined }
        responses.push(entry)
      }
    }
    if (['Network.loadingFinished', 'Network.loadingFailed'].includes(m.method)) {
      network.delete(m.params.requestId)
      const entry = responses.findLast(r => r.requestId === m.params.requestId)
      if (entry && m.method === 'Network.loadingFinished') call('Network.getResponseBody', { requestId: m.params.requestId }).then(r => { try { entry.body = JSON.parse(r.base64Encoded ? Buffer.from(r.body, 'base64').toString('utf8') : r.body) } catch { entry.body = null } }).catch(() => { entry.body = null })
    }
  })
  await call('Runtime.enable'); await call('Runtime.addBinding', { name: '__skillyRecordInput' }); await call('Page.enable'); await call('Network.enable'); await call('Fetch.enable', { patterns: [{ urlPattern: '*' }] })
  // Observar la vida real de fetch, incluidos AbortError de StrictMode. CDP
  // Android puede conservar un requestId interceptado ya abortado sin emitir
  // loadingFailed. No se sustituyen respuestas ni se omiten solicitudes.
  await call('Page.addScriptToEvaluateOnNewDocument', { source: `(()=>{const original=window.fetch;const state=window.__skillyFetchState={pending:0,settled:0,aborted:0};window.fetch=function(...args){state.pending++;let result;try{result=Reflect.apply(original,this,args)}catch(e){state.pending--;state.settled++;throw e}return result.then(r=>{state.pending--;state.settled++;return r},e=>{state.pending--;state.settled++;if(e?.name==='AbortError')state.aborted++;throw e})}})()` })
  if (!android) {
    await call('Emulation.setDeviceMetricsOverride', viewport)
    if (mobile) await call('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 })
  }
  const evaluate = async expression => { const r = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error('evaluacion_ui_rechazada'); return r.result.value }
  const a = { name, call, evaluate, responses, inputRecords, browserWs, ws, bc, browserContextId, dialogCount: () => dialogs }
  const foreground = () => android ? call('Page.bringToFront') : Promise.resolve()
  async function pointerAt(selector) {
    await foreground()
    if (android) {
      const blurred = await evaluate("(()=>{const e=document.activeElement;if(e&&['INPUT','TEXTAREA','SELECT'].includes(e.tagName)){e.blur();return true}return false})()")
      // Dejar terminar la animacion del IME antes de medir: de lo contrario
      // touchStart y touchEnd pueden caer en coordenadas visuales distintas.
      if (blurred) await delay(500)
    }
    let previous = null, current = null, stable = 0
    await until(async () => {
      current = await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.disabled||!e.getClientRects().length)return null;const r=e.getBoundingClientRect(),p={x:r.x+r.width/2,y:r.y+r.height/2};const top=document.elementFromPoint(p.x,p.y);if(!top||!(e===top||e.contains(top))){e.scrollIntoView({block:'center',behavior:'instant'});return null}return{...p,offset_x:window.visualViewport?.offsetLeft||0,offset_y:window.visualViewport?.offsetTop||0,scroll_y:window.scrollY}})()`)
      if (current && previous && Object.keys(current).every(key => Math.abs(current[key] - previous[key]) < 0.5)) stable++
      else stable = 0
      previous = current
      return stable >= 2
    }, 'objetivo_ui_no_estable')
    const layoutPoint = { x: current.x, y: current.y }, view = { x: current.offset_x, y: current.offset_y }
    const point = { x: layoutPoint.x - view.x, y: layoutPoint.y - view.y }
    a.lastClick = { ...a.lastClick, layout_point: layoutPoint, input_point: point, visual_offset: view, pointer_type: mobile ? 'touch' : 'mouse', stable_geometry: true }
    // Observadores pasivos: acreditan el destino real, sin disparar ni cancelar eventos.
    await evaluate(`(()=>{if(window.__skillyInputEvents)return;window.__skillyInputEvents=[];for(const type of ['pointerdown','mousedown','mouseup','touchstart','touchend','click','submit','invalid'])document.addEventListener(type,e=>{const n=e.target,b=n.closest?.('button'),t=e.changedTouches?.[0];const record={event:type,trusted:e.isTrusted,tag:n.tagName,id:n.id||'',type:n.type||'',label:b?.innerText?.slice(0,150)||'',form_class:n.closest?.('form')?.className||'',client_x:e.clientX??t?.clientX??null,client_y:e.clientY??t?.clientY??null,visual_offset_top:window.visualViewport?.offsetTop||0};window.__skillyInputEvents.push(record);if(typeof window.__skillyRecordInput==='function')window.__skillyRecordInput(JSON.stringify(record));if(window.__skillyInputEvents.length>30)window.__skillyInputEvents.shift()},{capture:true,passive:true})})()`)
    if (mobile) {
      await call('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ ...point, radiusX: 1, radiusY: 1, force: 1 }] })
      await delay(50)
      await call('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
    } else {
      await call('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', clickCount: 1 })
      await call('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', clickCount: 1 })
    }
  }
  a.ready = async () => {
    try {
      await until(async () => await evaluate("document.readyState==='complete'&&!!document.querySelector('main,header')&&!document.querySelector('[aria-busy=true]')&&window.__skillyFetchState?.pending===0"), 'ui_no_preparada')
    } catch (error) {
      a.readinessFailure = { pending: [...network].map(id => { const r = requests.get(id); return r ? { method: r.method, path: new URL(r.url).pathname } : { unknown: true } }), ui: await evaluate("({ready:document.readyState,visibility:document.visibilityState,fetch:window.__skillyFetchState,busy:[...document.querySelectorAll('[aria-busy=true]')].map(e=>({tag:e.tagName,class:e.className}))})") }
      throw error
    }
    await delay(140)
    if (android) {
      a.nativeViewport = await evaluate('({width:innerWidth,height:innerHeight,deviceScaleFactor:devicePixelRatio,screen_width:screen.width,screen_height:screen.height,max_touch_points:navigator.maxTouchPoints,visual_viewport:window.visualViewport?{width:visualViewport.width,height:visualViewport.height,scale:visualViewport.scale}:null})')
      viewport = { ...a.nativeViewport, mobile: true, native: true }
    }
  }
  a.navigate = async route => {
    if (!route.startsWith('/') || route.startsWith('//')) throw new Error('ruta_no_local')
    await foreground()
    // Una navegacion completa reemplaza el documento. Chrome Android puede
    // omitir loadingFailed de fetch abortados al destruir el anterior; no son
    // trabajo pendiente de la pagina nueva. Los nuevos IDs se observan abajo.
    network.clear()
    const marker = randomUUID(), hook = await call('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__skillyJourney=' + JSON.stringify(marker) })
    await call('Page.navigate', { url: origin + route })
    await until(() => evaluate('window.__skillyJourney===' + JSON.stringify(marker)), 'navegacion_no_completada')
    await call('Page.removeScriptToEvaluateOnNewDocument', { identifier: hook.identifier }); await a.ready()
  }
  a.wait = (expr, code, timeout) => until(() => evaluate(expr), code, timeout)
  a.fill = async (selector, value) => {
    await foreground()
    await a.wait(`!!document.querySelector(${JSON.stringify(selector)})&&!document.querySelector(${JSON.stringify(selector)}).disabled`, 'campo_no_disponible')
    await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.focus();const p=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(String(value))});e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))})()`)
  }
  a.fillLabel = async (label, value, scope = 'body') => {
    let selector
    await until(async () => {
      selector = await evaluate(`(()=>{const n=s=>s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().replace(/\\s+/g,' ').trim();const e=[...document.querySelectorAll(${JSON.stringify(scope)}+' label')].find(l=>n(l.innerText).startsWith(n(${JSON.stringify(label)})));const f=e&&(e.control||e.querySelector('input,textarea,select'));if(!f)return null;f.dataset.e2eField=${JSON.stringify(randomUUID())};return '[data-e2e-field="'+f.dataset.e2eField+'"]'})()`)
      return !!selector
    }, 'etiqueta_no_disponible')
    await a.fill(selector, value)
  }
  a.click = async (text, scope = 'body', exact = true) => {
    let point
    const marker = randomUUID()
    await until(async () => {
      point = await evaluate(`(()=>{const n=s=>s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().replace(/\\s+/g,' ').trim();const wanted=n(${JSON.stringify(text)});const e=[...document.querySelectorAll(${JSON.stringify(scope)}+' button,'+${JSON.stringify(scope)}+' a,'+${JSON.stringify(scope)}+' summary')].find(e=>e.getClientRects().length&&!e.disabled&&(${exact ? 'n(e.innerText)===wanted' : 'n(e.innerText).includes(wanted)'}));if(!e)return null;e.scrollIntoView({block:'center',behavior:'instant'});const r=e.getBoundingClientRect();const p={x:r.x+r.width/2,y:r.y+r.height/2};const top=document.elementFromPoint(p.x,p.y);if(!top||!(e===top||e.contains(top)))return null;e.dataset.e2eClick=${JSON.stringify(marker)};return p})()`)
      return !!point
    }, 'accion_ui_no_disponible_' + text.replace(/[^a-z0-9]/gi, '_').slice(0, 60))
    a.lastClick = { kind: 'texto', label: clean(text) }
    await pointerAt('[data-e2e-click="' + marker + '"]'); await delay(140)
  }
  a.clickSelector = async selector => {
    await a.wait(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});return e&&!e.disabled&&e.getClientRects().length})()`, 'selector_ui_no_disponible')
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center',behavior:'instant'})`)
    a.lastClick = { kind: 'selector', selector }
    await pointerAt(selector); await delay(140)
  }
  a.file = async (selector, files) => {
    await foreground()
    const localFiles = []
    for (const f of files) {
      const local = await fs.realpath(f)
      if (!inside(out, local)) throw new Error('adjunto_fuera_de_fixture')
      localFiles.push(local)
    }
    let browserFiles = localFiles
    if (android) {
      browserFiles = []
      for (const local of localFiles) {
        if (!androidRemoteFiles.has(local)) {
          const data = await fs.readFile(local), digest = createHash('sha256').update(data).digest('hex')
          const filename = path.basename(local).replace(/[^a-zA-Z0-9._-]/g, '_')
          const remote = '/sdcard/Download/skilly_' + path.basename(out).slice(-32) + '_' + digest.slice(0, 12) + '_' + filename
          if (!/^\/sdcard\/Download\/skilly_[a-zA-Z0-9._-]+$/.test(remote)) throw new Error('ruta_adjunto_android_rechazada')
          await adbCall(['push', local, remote])
          androidRemoteFiles.set(local, { remote, sha256: digest, bytes: data.length })
          interventions.push({ kind: 'adjunto_sintetico_copiado_a_android', filename, sha256: digest, bytes: data.length })
        }
        browserFiles.push(androidRemoteFiles.get(local).remote)
      }
    }
    if (android) {
      if (browserFiles.length !== 1) throw new Error('selector_android_solo_un_adjunto')
      let selectedNative
      for (let attempt = 0; attempt < 2; attempt++) {
      await a.clickSelector(selector)
      selectedNative = await new Promise((resolve, reject) => {
        const child = spawn(path.join(root, '.venv', 'Scripts', 'python.exe'), ['-B', path.join(root, 'tools', 'android_selector_archivo.py'), '--contexto-android', android.context_path, '--archivo', path.posix.basename(browserFiles[0])], { stdio: ['ignore', 'pipe', 'ignore'], windowsHide: true })
        let output = ''; const timer = setTimeout(() => { child.kill(); reject(new Error('selector_android_timeout')) }, 40000)
        child.stdout.on('data', chunk => { output += chunk; if (output.length > 16000) child.kill() })
        child.once('error', () => { clearTimeout(timer); reject(new Error('selector_android_no_disponible')) })
        child.once('close', code => { clearTimeout(timer); try { const result = JSON.parse(output); code === 0 && (result.completed || result.retry_file_input_required) ? resolve(result) : reject(new Error('selector_android_no_completado')) } catch { reject(new Error('selector_android_respuesta_invalida')) } })
      })
      if (selectedNative.completed) break
      interventions.push({ kind: 'selector_cerrado_al_denegar_camara', actor: name, native_picker_automated: true })
      }
      if (!selectedNative?.completed) throw new Error('selector_android_no_completado')
      interventions.push({ kind: 'selector_archivos_nativo_android', actor: name, ...selectedNative })
      const selected = await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});return e?[...e.files].map(f=>({name:f.name,size:f.size})):[]})()`)
      if (selected.length !== browserFiles.length || selected.some((file, i) => file.name !== path.posix.basename(browserFiles[i]) || file.size !== androidRemoteFiles.get(localFiles[i]).bytes)) throw new Error('adjunto_android_no_accesible_por_chrome')
      const readable = await evaluate(`(async()=>{try{return (await document.querySelector(${JSON.stringify(selector)}).files[0].arrayBuffer()).byteLength}catch{return -1}})()`)
      if (readable !== selected[0].size) throw new Error('adjunto_android_no_legible')
    } else {
      const { root: document } = await call('DOM.getDocument'); const { nodeId } = await call('DOM.querySelector', { nodeId: document.nodeId, selector })
      if (!nodeId) throw new Error('archivo_input_no_disponible')
      try { await call('DOM.setFileInputFiles', { nodeId, files: browserFiles }) }
      catch { throw new Error('adjunto_cdp_rechazado') }
    }
    await delay(120)
  }
  a.action = async (nameCheck, run, endpoint, method = 'POST', expected = [200, 201], { readBody = true } = {}) => {
    const start = responses.length
    const inputStart = inputSequence
    await run()
    let entry
    await until(() => { entry = responses.slice(start).find(r => decodeURIComponent(r.path) === endpoint && r.method === method && (!readBody || r.body !== undefined)); return !!entry }, 'sin_respuesta_' + nameCheck)
    const events = JSON.parse(clean(JSON.stringify(inputRecords.filter(e => e.sequence > inputStart))))
    check(nameCheck, expected.includes(entry.status), { source: 'interfaz_react_http_real', status: entry.status, expected,
      pointer_type: mobile ? 'touch' : 'mouse', trusted_activation_observed: events.some(e => e.trusted && ['click', 'submit'].includes(e.event)), input_events: events })
    await a.ready(); return entry.body
  }
  a.api = async (nameCheck, method, endpoint, body, reason = 'confirmacion_estado') => {
    interventions.push({ kind: reason, actor: name, operation: nameCheck })
    if (!endpoint.startsWith('/api/') || endpoint.includes('?')) throw new Error('confirmacion_api_no_permitida')
    const result = await evaluate(`(async()=>{const path=${JSON.stringify(endpoint)},method=${JSON.stringify(method)},body=${JSON.stringify(body)};const headers={Accept:'application/json'};if(method!=='GET'){const c=await(await fetch('/api/acceso/csrf/',{credentials:'same-origin',cache:'no-store'})).json();headers['X-CSRFToken']=c.csrfToken;headers['Content-Type']='application/json'}const r=await fetch(path,{method,credentials:'same-origin',redirect:'error',headers,...(body===undefined?{}:{body:JSON.stringify(body)})});return{status:r.status,body:await r.json().catch(()=>null)}})()`)
    check(nameCheck, result.status >= 200 && result.status < 300, { source: reason, status: result.status }); return result.body
  }
  a.measureLayout = () => evaluate("(()=>{const width=document.documentElement.clientWidth;const overflow=[...document.querySelectorAll('body *')].map(e=>({e,r:e.getBoundingClientRect()})).filter(x=>x.r.width>0&&(x.r.right>width+1||x.r.left< -1));return{document_client_width:width,document_scroll_width:document.documentElement.scrollWidth,body_scroll_width:document.body.scrollWidth,body_overflow:document.body.style.overflow,html_computed_width:getComputedStyle(document.documentElement).width,body_computed_width:getComputedStyle(document.body).width,innerWidth,innerHeight,visual_viewport:window.visualViewport?{width:visualViewport.width,height:visualViewport.height,scale:visualViewport.scale,offset_left:visualViewport.offsetLeft,offset_top:visualViewport.offsetTop}:null,document_horizontal_overflow:document.documentElement.scrollWidth>width+1,overflow_elements:overflow.slice(0,25).map(({e,r})=>({tag:e.tagName,id:e.id,class:typeof e.className==='string'?e.className:'',computed:{width:getComputedStyle(e).width,min_width:getComputedStyle(e).minWidth,max_width:getComputedStyle(e).maxWidth,position:getComputedStyle(e).position},rect:{x:r.x,y:r.y,width:r.width,height:r.height}}))}})()")
  a.screenshot = async label => {
    await foreground()
    const geometry = await a.measureLayout()
    await fs.writeFile(path.join(out, (mobile ? 'mobile_' : 'desktop_') + label + '.geometria.json'), JSON.stringify(geometry, null, 2))
    // Superponer redacciones sin acortar texto ni alterar el ajuste del documento.
    await evaluate(`(()=>{const hidden=[];for(const e of document.querySelectorAll('input,textarea'))if(e.type==='password'||e.type==='email'||/referencia|clave|token|correo/i.test(e.id+' '+e.name)){hidden.push([e,e.style.visibility]);e.style.visibility='hidden'}const layer=document.createElement('div');layer.id='skilly-e2e-redactions';layer.setAttribute('aria-hidden','true');layer.style.cssText='position:fixed;top:0;left:0;width:0;height:0;pointer-events:none;z-index:2147483647';const secrets=${JSON.stringify([...secrets])}.filter(s=>typeof s==='string'&&s.length>0),walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT),nodes=[];while(walk.nextNode())nodes.push(walk.currentNode);for(const n of nodes){if(['SCRIPT','STYLE'].includes(n.parentElement?.tagName))continue;const text=n.nodeValue,spans=[];for(const s of secrets){let start=0,index;while((index=text.indexOf(s,start))!==-1){spans.push([index,index+s.length]);start=index+s.length}}for(const m of text.matchAll(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}/g))spans.push([m.index,m.index+m[0].length]);for(const [start,end]of spans){const r=document.createRange();r.setStart(n,start);r.setEnd(n,end);for(const b of r.getClientRects()){if(b.width<=0||b.height<=0||b.bottom<0||b.top>innerHeight)continue;const mask=document.createElement('span');mask.style.cssText='position:fixed;background:#20382f;border-radius:2px;pointer-events:none;left:'+b.left+'px;top:'+b.top+'px;width:'+b.width+'px;height:'+b.height+'px';layer.appendChild(mask)}}}document.body.appendChild(layer);window.__skillyRestoreRedactions=()=>{layer.remove();for(const[e,v]of hidden)e.style.visibility=v;delete window.__skillyRestoreRedactions}})()`)
    try {
      const shot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      await fs.writeFile(path.join(out, (mobile ? 'mobile_' : 'desktop_') + label + '.png'), Buffer.from(shot.data, 'base64'))
    } finally { await evaluate('window.__skillyRestoreRedactions?.()') }
    return geometry
  }
  actors.push(a); return a
}
const h = { ctx, fixture, state, out, origin, backend, pdf, badFile, check, interventions, secrets, clock, persist, delay, actor,
  assertLayout, android: !!android,
  completed: name => [...previousChecks, ...checks].some(c => c.name === name && c.passed),
  stage: value => { stage = value; console.log(JSON.stringify({ stage, android: !!android })) } }
try {
  await clock(null)
  if (android) {
    stage = 'conexion_chrome_android'
    const qemu = (await adbCall(['shell', 'getprop', 'ro.kernel.qemu'])).trim()
    if (qemu !== '1') throw new Error('dispositivo_android_no_es_emulador_propio')
    androidEnvironment.android_release = (await adbCall(['shell', 'getprop', 'ro.build.version.release'])).trim()
    androidEnvironment.android_api = (await adbCall(['shell', 'getprop', 'ro.build.version.sdk'])).trim()
    androidEnvironment.android_model = (await adbCall(['shell', 'getprop', 'ro.product.model'])).trim()
    if (!androidEnvironment.android_release || !/^[0-9]+$/.test(androidEnvironment.android_api)) throw new Error('version_android_no_acreditada')
    port = android.cdp_port
    const version = await (await fetch(`http://127.0.0.1:${port}/json/version`, { redirect: 'error' })).json()
    checkedBrowserSocket(version.webSocketDebuggerUrl)
    if (!/^Chrome\//.test(version.Browser || '') || !/Android.*Mobile/.test(version['User-Agent'] || '')) throw new Error('chrome_android_no_acreditado')
    androidEnvironment.browser = version.Browser
    androidEnvironment.user_agent = version['User-Agent']
    androidEnvironment.protocol_version = version['Protocol-Version']
    androidEnvironment.input_strategy = 'CDP native touch activation; DOM value setter plus input/change for fields'
    androidEnvironment.native_keyboard_automated = false
    androidEnvironment.native_file_picker_automated = true
    await fs.writeFile(path.join(out, 'entorno_android.json'), JSON.stringify(androidEnvironment, null, 2), { flag: 'wx' })
  } else {
    browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-sync', '--disable-extensions', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--user-data-dir=' + path.join(out, 'profile'), 'about:blank'], { stdio: 'ignore', windowsHide: true })
    await until(async () => { try { port = Number((await fs.readFile(path.join(out, 'profile/DevToolsActivePort'), 'utf8')).split('\n')[0]); return !!port } catch { return false } }, 'edge_no_iniciado')
  }
  const admin = await actor('administracion'), professional = await actor('profesional'), company = await actor('organizacion')
  h.admin = admin; h.professional = professional; h.company = company
  if (['professional', 'all'].includes(phase)) {
    await onboarding(h)
    await publicacion(h)
  } else {
    if (!state.onboarding_complete || !state.publication_complete) throw new Error('La fase ciclos necesita una fixture profesional publicada')
    const { login } = await import('./e2e_browser_profesional.mjs')
    await login(professional, state.professional, h); await login(admin, fixture.admin, h)
  }
  if (['cycles', 'all'].includes(phase)) await ciclos(h)
  if (['permissions', 'all'].includes(phase)) await seguridad(h)
  if (phase === 'layout' || android && phase === 'all') await layout(h)
  if (phase === 'mobile-extra') {
    await adminMovil(h)
    await sesionesMoviles(h)
  }
} catch (error) {
  errors.push({ stage, kind: error.name, diagnostic: clean(error.message).slice(0, 250) })
  for (const a of actors) {
    try {
      const controls = await a.evaluate("[...document.querySelectorAll('input,textarea,select,button[type=submit]')].filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return{tag:e.tagName,type:e.type,id:e.id,name:e.name,required:e.required,disabled:e.disabled,valid:e.validity?e.validity.valid:null,value_missing:e.validity?e.validity.valueMissing:null,type_mismatch:e.validity?e.validity.typeMismatch:null,too_short:e.validity?e.validity.tooShort:null,rect:{x:r.x,y:r.y,width:r.width,height:r.height}}})")
      const display = await a.evaluate("({innerWidth,innerHeight,devicePixelRatio,document_client_width:document.documentElement.clientWidth,document_scroll_width:document.documentElement.scrollWidth,body_scroll_width:document.body.scrollWidth,visualViewport:window.visualViewport?{width:visualViewport.width,height:visualViewport.height,scale:visualViewport.scale,offsetLeft:visualViewport.offsetLeft,offsetTop:visualViewport.offsetTop,pageLeft:visualViewport.pageLeft,pageTop:visualViewport.pageTop}:null,focus:{id:document.activeElement?.id,type:document.activeElement?.type,tag:document.activeElement?.tagName},overflow_elements:[...document.querySelectorAll('body *')].map(e=>({tag:e.tagName,id:e.id,class:e.className,rect:e.getBoundingClientRect()})).filter(e=>e.rect.width>0&&(e.rect.right>document.documentElement.clientWidth+1||e.rect.left< -1)).slice(0,20).map(e=>({tag:e.tag,id:e.id,class:typeof e.class==='string'?e.class:'',rect:{x:e.rect.x,y:e.rect.y,width:e.rect.width,height:e.rect.height}})),alert_indicators:[...document.querySelectorAll('[role=alert]')].map(e=>({blocked_upload:/carga.*bloqueada/i.test(e.textContent),csrf:/csrf/i.test(e.textContent),file_validation:/archivo|formato|tama.o/i.test(e.textContent),http_error:/HTTP\\s+[45][0-9]{2}/.test(e.textContent)}))})")
      const inputEvents = a.inputRecords.slice(-30)
      const network = a.responses.map(r => ({ method: r.method, path: r.path.split('/').map(segment => segment.length > 24 ? '<referencia>' : segment).join('/'), status: r.status, parsed: r.body !== undefined }))
      await fs.writeFile(path.join(out, 'diagnostico_' + a.name + '.json'), clean(JSON.stringify({ controls, display, readiness: a.readinessFailure, last_click: a.lastClick, input_events: inputEvents, network }, null, 2)), { flag: 'wx' })
      await a.screenshot('fallo_' + a.name)
    } catch { /* Diagnostics never block clock restoration. */ }
  }
} finally {
  try { await clock(null); clockReset = true } catch { errors.push({ stage: 'cierre', kind: 'reloj_no_restaurado' }) }
  for (const a of actors) a.ws.close()
  for (const context of ownedContexts) { try { await context.bc('Target.disposeBrowserContext', { browserContextId: context.browserContextId }) } catch { /* Own context only. */ } context.browserWs.close() }
  if (browser) { browser.kill(); await delay(200) }
  if (android) {
    for (const { remote } of androidRemoteFiles.values()) {
      try {
        if (!/^\/sdcard\/Download\/skilly_[a-zA-Z0-9._-]+$/.test(remote)) throw new Error('ruta_android_no_propia')
        await adbCall(['shell', 'rm', '-f', '--', remote])
        interventions.push({ kind: 'adjunto_sintetico_android_retirado' })
      } catch { errors.push({ stage: 'cierre_android', kind: 'adjunto_android_no_retirado' }) }
    }
    await fs.writeFile(path.join(out, 'adjuntos_android.json'), JSON.stringify({ mechanism: 'ADB push synthetic file + native Android DocumentsUI exact file selection; readable bytes verified', files: [...androidRemoteFiles.values()], cleanup_attempted: true }, null, 2), { flag: 'wx' })
  }
  await persist()
  let sourceIntegrity = { unchanged: false, git_head_before: sourcesBefore.git_head, git_head_after: null, changed_files: [] }
  try {
    const sourcesAfter = await sourceSnapshot()
    await fs.writeFile(path.join(out, 'fuentes_despues.json'), JSON.stringify(sourcesAfter, null, 2), { flag: 'wx' })
    const before = new Map(sourcesBefore.files.map(f => [f.path, f.sha256])), after = new Map(sourcesAfter.files.map(f => [f.path, f.sha256]))
    const changed = [...new Set([...before.keys(), ...after.keys()])].filter(name => before.get(name) !== after.get(name))
    sourceIntegrity = { unchanged: changed.length === 0, git_head_before: sourcesBefore.git_head, git_head_after: sourcesAfter.git_head, changed_files: changed }
    checks.push({ name: 'fuentes_producto_y_harness_sin_cambios_durante_recorrido', passed: changed.length === 0, source: 'manifiestos_sha256_antes_despues' })
    if (changed.length) errors.push({ stage: 'cierre', kind: 'fuentes_cambiaron_durante_prueba' })
  } catch { errors.push({ stage: 'cierre', kind: 'integridad_fuentes_no_verificada' }) }
  const result = { completed: !errors.length, full_ui_journey: phase === 'all' && !resumePath && state.onboarding_complete === true && state.publication_complete === true && state.cycles_complete === true && state.permissions_complete === true && !errors.length,
    scenario_state: { professional_enabled: state.onboarding_complete === true, service_published: state.publication_complete === true, service_closed: state.cierre?.closed === true, payment_released: state.cierre?.complete === true, cancellation_reversal_simulated: state.cancelacion?.complete === true, object_role_permissions_verified: state.permissions_complete === true },
    stage, phase, viewport, browser_environment: androidEnvironment || { kind: mobile ? 'desktop_mobile_viewport_emulation' : 'desktop_browser', browser: 'Edge', physical_device: false, viewport_emulated: mobile },
    native_viewports_by_actor: android ? actors.map(a => ({ actor: a.name, metrics: a.nativeViewport || null })) : undefined,
    proxy_guard_verified: true, layout_assertions: assertLayout, layout_experiment: h.layoutResults || null, source_integrity: sourceIntegrity, isolated: true, run_id: ctx.run_id, checks, inherited_checks: previousChecks, previous_evidence: previousEvidence, passed: checks.filter(c => c.passed).length, failed: checks.filter(c => !c.passed).length, interventions, errors, clock_reset: clockReset, external_services: { email: 'locmem_sin_envio', payments: 'transferencia_sintetica_sin_dinero', interview: 'confirmacion_humana_simulada', browser: android ? 'Chrome_Android_emulador_React_HTTP_Django_PostgreSQL' : 'Edge_real_React_HTTP_Django_PostgreSQL' } }
  await fs.writeFile(path.join(out, 'resultado.json'), JSON.stringify(result, null, 2), { flag: 'wx' })
  console.log(JSON.stringify({ output: out, completed: result.completed, passed: result.passed, failed: result.failed, stage, errors: result.errors, clock_reset: clockReset }))
  if (!result.completed) process.exitCode = 1
}
}

main().catch(error => {
  // JSON corrupto o errores de setup nunca deben imprimir fragmentos privados ni stacks.
  const errorType = ['Error', 'TypeError', 'SyntaxError', 'RangeError', 'ReferenceError', 'URIError'].includes(error?.name) ? error.name : 'Error'
  console.log(JSON.stringify({ completed: false, stage: 'setup', error_type: errorType }))
  process.exitCode = 1
})
