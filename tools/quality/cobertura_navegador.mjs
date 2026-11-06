// Cobertura real de Edge/CDP. V8 -> Istanbul usa librerias oficiales y sourcemaps.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
import { createHash, randomUUID } from 'node:crypto'
import { spawn } from 'node:child_process'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const frontend = path.join(root, 'frontend')
const requireFrontend = createRequire(path.join(frontend, 'package.json'))
const v8toIstanbul = requireFrontend('v8-to-istanbul')
const { createCoverageMap } = requireFrontend('istanbul-lib-coverage')
const { createContext } = requireFrontend('istanbul-lib-report')
const reports = requireFrontend('istanbul-reports')
const convertSourceMap = requireFrontend('convert-source-map')
const contextPath = process.argv[2]
const harnessOnly = process.argv.includes('--hook-only')
if (!contextPath || !path.isAbsolute(contextPath)) throw new Error('Se requiere contexto absoluto externo')
const ctx = JSON.parse(await fs.readFile(contextPath, 'utf8'))
const runDir = await fs.realpath(ctx.run_dir)
const backup = await fs.realpath(path.resolve(root, '..', 'SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b'))
const inside = (base, candidate) => {
  const relative = path.relative(base, candidate)
  return relative !== '' && !relative.startsWith('..') && !path.isAbsolute(relative)
}
if (!inside(backup, runDir) || inside(root, runDir)) throw new Error('El contexto debe pertenecer al respaldo externo')
function localOrigin(value) {
  let url
  try { url = new URL(value) } catch { throw new Error('Origen de pruebas invalido') }
  if (!['http:', 'https:'].includes(url.protocol) || !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) ||
      !url.port || ['8000', '5173', '5432', '9000'].includes(url.port) || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash) throw new Error('Origen de pruebas no permitido')
  return url.origin
}
const origin = localOrigin(ctx.frontend_origin)
const backend = localOrigin(ctx.backend_origin)
if (ctx.database_port === 5432 || !Number.isInteger(ctx.database_port) || ctx.database_port < 1 || ctx.database_port > 65535) throw new Error('PostgreSQL operativo no permitido')
const health = await (await fetch(backend + '/__isolated/health', { redirect: 'error' })).json()
if (health.isolated !== true || health.run_id !== ctx.run_id || health.database_port !== ctx.database_port) throw new Error('Guardia de entorno fallida')
const fixture = JSON.parse(await fs.readFile(path.join(runDir, 'fixture_privado.json'), 'utf8'))
if (localOrigin(fixture.origin) !== origin) throw new Error('La fixture no coincide con el origen aislado')
function safeDiagnostic(error) {
  let message = String(error.message || '')
  for (const value of [fixture.control, fixture.admin?.email, fixture.admin?.password, fixture.professional_ui?.email, fixture.professional_ui?.password]) {
    if (typeof value === 'string' && value.length >= 4) message = message.replaceAll(value, '<redacted>')
  }
  return message.replace(/(password|token|secret|authorization)\s*[=:]\s*[^\s]+/gi, '$1=<redacted>').slice(0, 500)
}
const out = path.join(runDir, 'coverage_browser_' + randomUUID().replaceAll('-', ''))
await fs.mkdir(out)
const map = createCoverageMap({})
const scripts = new Map()
const scriptSources = new Map()
const originalHashes = new Map()
const unstableSources = new Set()
const checks = [], skipped = [], conversions = []
let browser, ws, call, evaluate, stage = 'inicio', mode = 'allow', held = [], failedRequests = 0
let rawBatches = 0
let lastBrowserError = null
const waits = new Set()
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(fn, timeout = 20000) {
  const start = Date.now()
  while (Date.now() - start < timeout) { if (await fn()) return; await delay(60) }
  throw new Error('Tiempo de espera agotado')
}
function check(name, passed) { checks.push({ name, passed: !!passed }); if (!passed) throw new Error('Comprobacion fallida') }
function sourcePath(url) {
  try {
    const parsed = new URL(url)
    if (parsed.origin !== origin || !parsed.pathname.startsWith('/src/') || !/\.(jsx?|mjs)$/.test(parsed.pathname)) return null
    const candidate = path.resolve(frontend, '.' + decodeURIComponent(parsed.pathname))
    return inside(path.join(frontend, 'src'), candidate) ? candidate : null
  } catch { return null }
}
async function flushCoverage() {
  const snapshot = await call('Profiler.takePreciseCoverage')
  const raw = []
  for (const entry of snapshot.result) {
    const originalPath = sourcePath(entry.url)
    if (!originalPath) continue
    const relative = path.relative(root, originalPath).replaceAll('\\', '/')
    try {
      const cached = await scriptSources.get(entry.scriptId)
      const source = cached ?? (await call('Debugger.getScriptSource', { scriptId: entry.scriptId })).scriptSource
      const original = await fs.readFile(originalPath, 'utf8')
      const originalHash = createHash('sha256').update(original).digest('hex')
      if (originalHashes.has(originalPath) && originalHashes.get(originalPath) !== originalHash) {
        unstableSources.add(relative)
        throw new Error('La fuente cambio durante el recorrido')
      }
      originalHashes.set(originalPath, originalHash)
      let sourceMap = convertSourceMap.fromSource(source)?.toObject()
      if (!sourceMap && scripts.get(entry.scriptId)?.sourceMapURL?.startsWith('data:')) {
        sourceMap = convertSourceMap.fromComment('//# sourceMappingURL=' + scripts.get(entry.scriptId).sourceMapURL)?.toObject()
      }
      if (sourceMap) {
        if (sourceMap.sources?.length !== 1 || sourceMap.sourcesContent?.length !== 1 ||
            sourceMap.sourcesContent[0].replaceAll('\r\n', '\n') !== original.replaceAll('\r\n', '\n')) {
          throw new Error('El sourcemap no coincide con una fuente local unica')
        }
        // Solo normalizar la referencia de archivo; mappings/contadores intactos.
        sourceMap.sources = [originalPath]
        sourceMap.sourceRoot = ''
      } else if (source !== original) {
        throw new Error('Transformacion sin sourcemap verificable')
      }
      const converter = v8toIstanbul(originalPath, 0, { source, originalSource: original,
        ...(sourceMap ? { sourceMap: { sourcemap: sourceMap } } : {}) }, candidate => !inside(path.join(frontend, 'src'), path.resolve(candidate)))
      await converter.load()
      converter.applyCoverage(entry.functions)
      const converted = converter.toIstanbul()
      const files = Object.keys(converted)
      if (files.length !== 1 || path.resolve(files[0]).toLowerCase() !== path.resolve(originalPath).toLowerCase()) throw new Error('Fuente remapeada inesperada')
      const lineCount = original.split('\n').length
      if (Object.values(converted[files[0]].statementMap).some(loc => loc.start.line < 1 || loc.end.line > lineCount)) throw new Error('Rango fuera del archivo original')
      map.merge(converted)
      raw.push({ source_file: relative, functions: entry.functions })
      conversions.push({ source_file: relative, sourcemap: !!sourceMap,
        original_sha256: originalHash, functions: entry.functions.length })
    } catch (error) { skipped.push({ source_file: relative, error_type: error.name, diagnostic: safeDiagnostic(error), reason: error.message.startsWith('El sourcemap') ? 'source_map_mismatch' : error.message.startsWith('Transformacion') ? 'missing_source_map' : 'conversion_failed' }) }
  }
  if (raw.length) await fs.writeFile(path.join(out, 'v8_' + (++rawBatches) + '.json'), JSON.stringify(raw))
}

try {
  browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', [
    '--headless=new', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-sync', '--disable-extensions',
    '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--user-data-dir=' + path.join(out, 'profile'), 'about:blank',
  ], { stdio: 'ignore', windowsHide: true })
  let port
  await until(async () => { try { port = Number((await fs.readFile(path.join(out, 'profile/DevToolsActivePort'), 'utf8')).split('\n')[0]); return !!port } catch { return false } })
  const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT', redirect: 'error' })).json()
  ws = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0
  const pending = new Map()
  call = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id
    const timer = setTimeout(() => { pending.delete(n); reject(new Error('CDP timeout')) }, 10000)
    pending.set(n, { resolve, reject, timer }); ws.send(JSON.stringify({ id: n, method, params }))
  })
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.id) {
      const item = pending.get(message.id)
      if (item) { pending.delete(message.id); clearTimeout(item.timer); message.error ? item.reject(new Error('CDP fallo')) : item.resolve(message.result) }
    }
    if (message.method === 'Debugger.scriptParsed') {
      scripts.set(message.params.scriptId, message.params)
      // Guardar la fuente mientras el contexto sigue vivo; V8 puede descartarla al navegar.
      if (sourcePath(message.params.url)) scriptSources.set(message.params.scriptId,
        call('Debugger.getScriptSource', { scriptId: message.params.scriptId }).then(result => result.scriptSource).catch(() => null))
    }
    if (message.method === 'Runtime.exceptionThrown') {
      lastBrowserError = safeDiagnostic({ message: message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text })
    }
    if (message.method === 'Fetch.requestPaused') {
      const request = message.params
      let allowed = false, pathname = ''
      try { const url = new URL(request.request.url); allowed = [origin, backend].includes(url.origin); pathname = url.pathname } catch { /* fail closed */ }
      let operation
      if (!allowed) operation = call('Fetch.failRequest', { requestId: request.requestId, errorReason: 'BlockedByClient' })
      else if (mode === 'hold-access' && pathname.endsWith('/AccesoProfesional.jsx')) { held.push(request.requestId); return }
      else if (mode === 'fail-followup' && pathname.endsWith('/Seguimiento.jsx')) { failedRequests++; operation = call('Fetch.failRequest', { requestId: request.requestId, errorReason: 'Failed' }) }
      else operation = call('Fetch.continueRequest', { requestId: request.requestId })
      waits.add(operation); operation.finally(() => waits.delete(operation)).catch(() => {})
    }
  })
  await call('Runtime.enable'); await call('Page.enable'); await call('Debugger.enable'); await call('Network.enable')
  await call('Network.setCacheDisabled', { cacheDisabled: true }); await call('Fetch.enable', { patterns: [{ urlPattern: '*' }] })
  await call('Profiler.enable'); await call('Profiler.startPreciseCoverage', { callCount: true, detailed: true })
  evaluate = async expression => {
    const result = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (result.exceptionDetails) {
      lastBrowserError = safeDiagnostic({ message: result.exceptionDetails.exception?.description || result.exceptionDetails.text })
      throw new Error('Evaluacion de navegador fallo')
    }
    return result.result.value
  }
  async function startNavigation(route) {
    await flushCoverage()
    const marker = randomUUID()
    const preload = await call('Page.addScriptToEvaluateOnNewDocument', { source: 'window.__skillyQualityNavigation=' + JSON.stringify(marker) })
    await call('Page.navigate', { url: origin + route })
    await until(() => evaluate('window.__skillyQualityNavigation===' + JSON.stringify(marker) + "&&document.readyState==='complete'"))
    await call('Page.removeScriptToEvaluateOnNewDocument', { identifier: preload.identifier })
  }
  async function navigate(route) { await startNavigation(route); await until(() => evaluate("!!document.querySelector('main,header')&&!document.querySelector('[aria-busy=true]')")); await delay(180) }
  async function key(name, code, shift = false) {
    await call('Input.dispatchKeyEvent', { type: 'keyDown', key: name, code: name, windowsVirtualKeyCode: code, modifiers: shift ? 8 : 0 })
    await call('Input.dispatchKeyEvent', { type: 'keyUp', key: name, code: name, windowsVirtualKeyCode: code, modifiers: shift ? 8 : 0 })
  }
  async function login(actor) {
    await navigate('/acceso-profesional'); await until(() => evaluate("!!document.querySelector('#ap-correo')"))
    for (const [name, value] of [['ap-correo', actor.email], ['ap-contrasena', actor.password]]) {
      await evaluate(`(()=>{const e=document.getElementById(${JSON.stringify(name)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}))})()`)
    }
    await evaluate("document.querySelector('form.ap-formulario').requestSubmit()")
    await until(() => evaluate("location.pathname!=='/acceso-profesional'&&!!document.querySelector('main,header')&&!document.querySelector('[aria-busy=true]')"))
    check('inicio_sesion_interfaz_real', true)
  }
  stage = 'rutas_publicas'
  await call('Emulation.setDeviceMetricsOverride', { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false })
  if (!harnessOnly) {
  for (const route of ['/', '/acceso-profesional', '/seguimiento', '/disponibilidad']) { await navigate(route); check('carga_real_' + route, true) }
  stage = 'espera_y_error_de_carga'
  mode = 'hold-access'; await startNavigation('/acceso-profesional')
  await until(() => evaluate("!!document.querySelector('[role=status][aria-busy=true]')")); check('espera_accesible_modulo', held.length > 0)
  mode = 'allow'; for (const requestId of held) await call('Fetch.continueRequest', { requestId }); held = []
  await until(() => evaluate("!!document.querySelector('#ap-correo')")); check('modulo_demorado_recuperado', true)
  await key('Tab', 9); check('saltar_contenido_primero', await evaluate("document.activeElement.classList.contains('sk-salto-contenido')"))
  await key('Enter', 13); check('saltar_contenido_enfoca_main', await evaluate("document.activeElement.tagName==='MAIN'"))
  await evaluate("document.querySelector('.ap-mostrar').click()")
  check('mostrar_contrasena_semantico', await evaluate("document.querySelector('.ap-mostrar').getAttribute('aria-pressed')==='true'&&document.querySelector('#ap-contrasena').type==='text'"))
  await evaluate("document.querySelector('.ap-mostrar').click()")
  mode = 'fail-followup'; await startNavigation('/seguimiento')
  await until(() => evaluate("!!document.querySelector('[role=alert] button')")); check('error_de_modulo_accesible', true)
  await delay(400); check('sin_bucle_recarga_automatica', failedRequests === 1)
  await flushCoverage(); mode = 'allow'; await evaluate("document.querySelector('[role=alert] button').click()")
  await until(() => evaluate("location.pathname==='/seguimiento'&&!!document.querySelector('main,header')&&!document.querySelector('[role=alert] button')&&!document.querySelector('[aria-busy=true]')")); check('recarga_manual_recupera', true)
  stage = 'rutas_administrativas'
  await login(fixture.admin)
  for (const route of ['/administracion', '/administracion/validaciones', '/administracion/propuestas', '/administracion/indicadores', '/administracion/comision', '/administracion/cancelaciones', '/administracion/expedientes-cancelacion', '/administracion/cuentas-bancarias', '/administracion/trazabilidad', '/administracion/reclamos', '/administracion/retroalimentacion']) {
    await navigate(route); check('carga_real_' + route, true)
  }
  await navigate('/administracion/indicadores'); await until(() => evaluate("!!document.querySelector('.adm-resumen button')"))
  await evaluate("window.__qualityTrigger=document.querySelector('.adm-resumen button');window.__qualityTrigger.focus();window.__qualityTrigger.click()")
  await until(() => evaluate("!!document.querySelector('[role=dialog]')&&document.querySelector('[role=dialog]').contains(document.activeElement)")); check('dialogo_admin_foco_inicial', true)
  await key('Escape', 27); await until(() => evaluate("!document.querySelector('[role=dialog]')")); check('dialogo_admin_retorno_foco', await evaluate('document.activeElement===window.__qualityTrigger'))
  await evaluate("(async()=>{const d=await(await fetch('/api/acceso/csrf/')).json();await fetch('/api/acceso/cerrar-sesion/',{method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':d.csrfToken}})})()")
  stage = 'portal_profesional'
  await login(fixture.professional_ui); await navigate('/portal-profesional')
  await until(() => evaluate("!!document.querySelector('.pp-opcion-seccion')")); check('portal_profesional_real', true)
  await evaluate("window.__qualityTrigger=document.querySelector('.pp-opcion-seccion');window.__qualityTrigger.focus();window.__qualityTrigger.click()")
  await until(() => evaluate("!!document.querySelector('[role=dialog]')&&document.querySelector('[role=dialog]').contains(document.activeElement)")); check('portal_foco_inicial', true)
  await key('Escape', 27); await until(() => evaluate("!document.querySelector('[role=dialog]')")); check('portal_retorno_foco', await evaluate('document.activeElement===window.__qualityTrigger'))
  }
  stage = 'hook_dialogos_sinteticos'
  await navigate('/acceso-profesional')
  const dependencyUrl = name => [...scripts.values()].reverse().find(script => {
    try { const url = new URL(script.url); return url.origin === origin && url.pathname === '/node_modules/.vite/deps/' + name && url.searchParams.has('v') } catch { return false }
  })?.url
  const reactUrl = dependencyUrl('react.js'), reactDomUrl = dependencyUrl('react-dom_client.js')
  if (!reactUrl || !reactDomUrl) throw new Error('No se encontro la instancia React cargada por Vite')
  await evaluate(`(async()=>{
    const React=(await import(${JSON.stringify(reactUrl)})).default;
    const ReactDOMClient=await import(${JSON.stringify(reactDomUrl)});
    const createRoot=ReactDOMClient.createRoot||ReactDOMClient.default?.createRoot;
    const useDialogo=(await import('/src/useDialogoAccesible.js')).default;
    const h=React.createElement; const original=document.getElementById('root');original.hidden=true;
    window.__qualityOverflow=document.body.style.overflow;document.body.style.overflow='auto';
    const host=document.createElement('div');document.body.append(host);
    function Inner(){const [open,setOpen]=React.useState(false);const ref=React.useRef(null);useDialogo(open,ref,()=>setOpen(false));return h(React.Fragment,null,h('button',{id:'q-inner-trigger',onClick:()=>setOpen(true)},'Abrir interior'),open&&h('section',{ref,tabIndex:-1,id:'q-inner',role:'dialog'},h('button',{id:'q-inner-first','data-dialogo-foco-inicial':true,onClick:()=>setOpen(false)},'Cerrar interior'),h('button',{id:'q-inner-last'},'Ultimo interior')))}
    function Demo(){const [open,setOpen]=React.useState(false),[blocked,setBlocked]=React.useState(false),[extra,setExtra]=React.useState(false),[empty,setEmpty]=React.useState(false);const ref=React.useRef(null),emptyRef=React.useRef(null);useDialogo(open,ref,()=>setOpen(false),blocked);useDialogo(empty,emptyRef,()=>setEmpty(false));window.__qualitySetBlocked=setBlocked;return h(React.Fragment,null,h('button',{id:'q-open',onClick:()=>setOpen(true)},'Abrir exterior'),h('button',{id:'q-outside'},'Fuera'),h('button',{id:'q-empty-open',onClick:()=>setEmpty(true)},'Abrir vacio'),open&&h('section',{ref,tabIndex:-1,id:'q-parent',role:'dialog'},h('button',{id:'q-first','data-dialogo-foco-inicial':true,onClick:()=>setOpen(false)},'Cerrar'),h('button',{disabled:true},'Deshabilitado'),h('input',{type:'hidden'}),h('div',{hidden:true},h('button',null,'Oculto')),h('div',{'aria-hidden':true},h('button',null,'Aria oculto')),h('div',{inert:true},h('button',null,'Inerte')),h('div',{tabIndex:-1},'No tabulable'),h(Inner),h('button',{id:'q-extra-toggle',onClick:()=>setExtra(true)},'Agregar control'),h('button',{id:'q-last'},'Ultimo'),extra&&h('button',{id:'q-extra'},'Dinamico')),empty&&h('section',{ref:emptyRef,tabIndex:-1,id:'q-empty',role:'dialog'},h('button',{disabled:true},'No disponible')))}
    window.__qualityRoot=createRoot(host);window.__qualityRoot.render(h(React.StrictMode,null,h(Demo)));window.__qualityHost=host;
  })()`)
  await until(() => evaluate("!!document.querySelector('#q-open')"))
  await evaluate("document.querySelector('#q-open').focus();document.querySelector('#q-open').click()")
  await until(() => evaluate("document.activeElement.id==='q-first'")); check('hook_foco_inicial_designado', true)
  await evaluate("document.querySelector('#q-last').focus()")
  await key('Tab', 9); check('hook_tab_envuelve_y_omite_ocultos', await evaluate("document.activeElement.id==='q-first'"))
  await key('Tab', 9, true); check('hook_shift_tab_envuelve', await evaluate("document.activeElement.id==='q-last'"))
  await evaluate("document.querySelector('#q-outside').focus()")
  await key('Tab', 9); check('hook_recupera_foco_externo', await evaluate("document.activeElement.id==='q-first'"))
  await evaluate("document.querySelector('#q-extra-toggle').click()")
  await until(() => evaluate("!!document.querySelector('#q-extra')")); await evaluate("document.querySelector('#q-extra').focus()")
  await key('Tab', 9); check('hook_controles_dinamicos', await evaluate("document.activeElement.id==='q-first'"))
  await evaluate("window.__qualitySetBlocked(true)"); await delay(60); await key('Escape', 27)
  check('hook_escape_bloqueado', await evaluate("!!document.querySelector('#q-parent')"))
  await evaluate("window.__qualitySetBlocked(false)"); await delay(60)
  await evaluate("document.querySelector('#q-inner-trigger').focus();document.querySelector('#q-inner-trigger').click()")
  await until(() => evaluate("document.activeElement.id==='q-inner-first'")); check('hook_dialogo_anidado_foco', true)
  await evaluate("document.querySelector('#q-inner-last').focus()"); await key('Tab', 9)
  check('hook_solo_superior_responde_tab', await evaluate("document.activeElement.id==='q-inner-first'"))
  await key('Escape', 27); await until(() => evaluate("!document.querySelector('#q-inner')"))
  check('hook_escape_cierra_solo_superior', await evaluate("!!document.querySelector('#q-parent')&&document.body.style.overflow==='hidden'&&document.activeElement.id==='q-inner-trigger'"))
  await key('Escape', 27); await until(() => evaluate("!document.querySelector('#q-parent')"))
  check('hook_restaura_disparador_y_scroll', await evaluate("document.activeElement.id==='q-open'&&document.body.style.overflow==='auto'"))
  await evaluate("document.querySelector('#q-empty-open').focus();document.querySelector('#q-empty-open').click()")
  await until(() => evaluate("document.activeElement.id==='q-empty'")); await key('Tab', 9)
  check('hook_panel_sin_controles', await evaluate("document.activeElement.id==='q-empty'")); await key('Escape', 27)
  await until(() => evaluate("!document.querySelector('#q-empty')"))
  await evaluate("window.__qualityRoot.unmount();window.__qualityHost.remove();document.getElementById('root').hidden=false;document.body.style.overflow=window.__qualityOverflow")
  await flushCoverage()
  await call('Profiler.stopPreciseCoverage')
  stage = 'informes'
  for (const [file, hash] of originalHashes) {
    if (createHash('sha256').update(await fs.readFile(file)).digest('hex') !== hash) unstableSources.add(path.relative(root, file).replaceAll('\\', '/'))
  }
  check('fuentes_no_cambiaron_durante_recorrido', unstableSources.size === 0)
  check('cobertura_incluye_jsx_real', map.files().filter(file => file.endsWith('.jsx')).length >= 5)
  check('cobertura_solo_fuente_local', map.files().every(file => inside(path.join(frontend, 'src'), file)))
  const reporting = createContext({ dir: out, coverageMap: map })
  reports.create('lcovonly', { projectRoot: root }).execute(reporting)
  reports.create('json').execute(reporting)
  reports.create('json-summary').execute(reporting)
  const summary = map.getCoverageSummary().toJSON()
  await fs.writeFile(path.join(out, 'resultado.json'), JSON.stringify({ passed: checks.every(item => item.passed), checks,
    real_browser: true, real_django: !harnessOnly, real_isolated_postgresql: !harnessOnly, financial_or_email_calls: false,
    harness_only: harnessOnly,
    synthetic_hook_harness: true, network_fault_injected: true, complete_business_ui_journey: false,
    source_modules: map.files().length, sources: map.files().map(file => path.relative(root, file).replaceAll('\\', '/')),
    summary, conversions, skipped, unstable_sources: [...unstableSources], coverage_conversion_complete: skipped.length === 0,
    raw_batches: rawBatches, report: path.join(out, 'lcov.info'),
    limitation: 'Cobertura de los modulos ejecutados en estos recorridos y del hook real en harness sintetico; no certifica todas las acciones del negocio ni navegadores/dispositivos.' }, null, 2))
  console.log('BROWSER_COVERAGE_CHECKS', checks.length, 'SOURCE_MODULES', map.files().length)
} catch (error) {
  await fs.writeFile(path.join(out, 'resultado.json'), JSON.stringify({ passed: false, stage, error_type: error.name, browser_error: lastBrowserError, checks, conversions, skipped }, null, 2))
  console.log('BROWSER_COVERAGE_FAILED', stage); process.exitCode = 1
} finally {
  if (call && ws?.readyState === 1) { await call('Browser.close').catch(() => {}); ws.close() }
  if (browser && browser.exitCode === null) browser.kill()
  await fs.copyFile(fileURLToPath(import.meta.url), path.join(out, 'cobertura_navegador.mjs'))
  console.log('BROWSER_COVERAGE_DIRECTORY', out)
}
