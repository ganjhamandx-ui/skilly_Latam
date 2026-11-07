// Pago real del proveedor de integración, exclusivamente con datos sintéticos oficiales.
// Requiere el contexto sandbox dedicado; no inicia servidores ni altera configuración.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createHash, randomUUID } from 'node:crypto'
import { spawn } from 'node:child_process'
import { datosSandboxDesdeDocumentacion } from './webpay_datos_sandbox.mjs'
import { camposFormularioSandbox, indicadoresPaginaSandbox } from './webpay_formulario_sandbox.mjs'

// Solo estos codigos controlados pueden salir a evidencia; nunca mensajes de
// excepcion, snippets de JSON, respuestas del proveedor o valores de campos.
const ERROR_CODES = new Set([
  'CONTEXT_REQUIRED', 'CONTEXT_INVALID', 'BACKEND_INVALID', 'RESUME_INVALID', 'CHECKOUT_INVALID', 'FIXTURE_INVALID',
  'BACKEND_GUARD_FAILED', 'FRONTEND_GUARD_FAILED', 'PROVIDER_ALREADY_CONTACTED', 'LOCAL_API_INVALID',
  'OFFICIAL_DOCS_NETWORK_FAILED', 'OFFICIAL_DOCS_HTTP_FAILED', 'OFFICIAL_DOCS_TOO_LARGE',
  'OFFICIAL_DOCS_SECTION_MISSING', 'OFFICIAL_DOCS_VISA_ROW_INVALID', 'OFFICIAL_DOCS_CARD_FORMAT_INVALID', 'OFFICIAL_DOCS_AUTH_FORMAT_INVALID',
  'CDP_TARGET_MISSING', 'CDP_TIMEOUT', 'CDP_REJECTED', 'UI_EVALUATION_FAILED', 'UNEXPECTED_FAILURE', 'JSON_INVALID',
  'proxy_navegador_aislado_antes_de_referencia_privada', 'proxy_navegador_aislado_antes_de_reanudar', 'proxy_navegador_aislado_antes_de_iniciar',
  'datos_sinteticos_obtenidos_de_fuente_oficial', 'edge_no_iniciado', 'origen_local_no_preparado',
  'pagina_local_no_lista_para_reanudar', 'checkout_previo_no_reanudado', 'checkout_pendiente_reanudado_sin_crear_otro_pago',
  'consulta_seguimiento_no_disponible', 'formulario_pago_no_disponible', 'politica_o_horario_no_habilita_pago', 'checkout_no_iniciado_en_sandbox',
  'checkout_skilly_http_y_proveedor_sandbox_reales', 'destino_de_autenticacion_fuera_del_sandbox_permitido',
  'desafio_humano_del_proveedor_requiere_interaccion_local', 'campos_tarjeta_sandbox_no_reconocidos_no_se_envia',
  'retorno_del_proveedor_no_completado', 'datos_oficiales_ingresados_en_sandbox', 'retorno_local_real_sin_sustituir_respuesta',
  'pago_no_retenido_no_declarar_autorizado', 'pago_retenido_en_copia_por_confirmacion_real', 'creacion_y_confirmacion_https_reales',
  'retorno_duplicado_idempotente', 'retorno_duplicado_no_confirma_ni_cobra_de_nuevo',
])
function controlError(code) {
  const error = new Error('Fallo controlado del ensayo sandbox')
  error.controlCode = ERROR_CODES.has(code) ? code : 'UNEXPECTED_FAILURE'
  return error
}
function errorInfo(error) {
  const name = ['Error', 'TypeError', 'SyntaxError', 'RangeError', 'AbortError', 'TimeoutError'].includes(error?.name) ? error.name : 'Error'
  const code = ERROR_CODES.has(error?.controlCode) ? error.controlCode : name === 'SyntaxError' ? 'JSON_INVALID' : 'UNEXPECTED_FAILURE'
  return { error_type: name, code }
}

async function main() {
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const contextPath = process.argv[2]
if (!contextPath || !path.isAbsolute(contextPath)) throw controlError('CONTEXT_REQUIRED')
const ctx = JSON.parse(await fs.readFile(contextPath, 'utf8'))
const run = await fs.realpath(ctx.run_dir)
const inside = (base, file) => { const rel = path.relative(base, file); return !!rel && !rel.startsWith('..') && !path.isAbsolute(rel) }
if (inside(root, run) || run === root || ctx.isolated !== true || ctx.sandbox_transport !== true || ctx.database_port !== 57647 || ctx.frontend_origin !== 'http://localhost:5173') throw controlError('CONTEXT_INVALID')
const backend = new URL(ctx.backend_origin)
if (backend.protocol !== 'http:' || backend.hostname !== '127.0.0.1' || !backend.port || ['8000', '5173', '5432'].includes(backend.port) || backend.pathname !== '/' || backend.search || backend.hash || backend.username || backend.password) throw controlError('BACKEND_INVALID')
const origin = ctx.frontend_origin, provider = 'https://webpay3gint.transbank.cl'
// Transporte local fijo, sin cambiar el origen visible ni la configuracion DNS
// de Windows. El listener IPv6 ajeno no recibe referencias ni tokens de prueba.
const frontendTransport = 'http://127.0.0.1:5173'
const frontendHost = new URL(origin).host
const resumeIndex = process.argv.indexOf('--resume-checkout')
let resumePayment
if (resumeIndex > 2) {
  const resumePath = process.argv[resumeIndex + 1]
  if (!resumePath || !path.isAbsolute(resumePath) || !inside(run, await fs.realpath(resumePath))) throw controlError('RESUME_INVALID')
  resumePayment = JSON.parse(await fs.readFile(resumePath, 'utf8'))
  if (typeof resumePayment.token !== 'string' || !/^[A-Za-z0-9_-]{5,200}$/.test(resumePayment.token) || new URL(resumePayment.url).origin !== provider || resumePayment.ambiente !== 'TRANSBANK_INTEGRACION') throw controlError('CHECKOUT_INVALID')
}
const privateFixture = JSON.parse(await fs.readFile(path.join(run, 'fixture_privado.json'), 'utf8'))
if (privateFixture.origin !== origin || privateFixture.run_id !== ctx.run_id || typeof privateFixture.reference !== 'string' || !privateFixture.reference || !Number.isInteger(privateFixture.prestacion_id)) throw controlError('FIXTURE_INVALID')
async function health() {
  const r = await fetch(ctx.backend_origin + '/__isolated/health', { redirect: 'error', signal: AbortSignal.timeout(8000) })
  const h = await r.json()
  if (!r.ok || h.isolated !== true || h.run_id !== ctx.run_id || h.database_port !== 57647 || h.sandbox_transport !== true) throw controlError('BACKEND_GUARD_FAILED')
  return h
}
async function frontendHealth() {
  // El mismo origen que recibe los POST de React debe llegar al backend
  // comprobado. Una instancia Vite operativa en 5173 no puede usarse por error.
  const r = await fetch(frontendTransport + '/api/__isolated/health', {
    redirect: 'error', signal: AbortSignal.timeout(8000), headers: { Host: frontendHost },
  })
  const h = await r.json()
  if (!r.ok || h.isolated !== true || h.run_id !== ctx.run_id
      || h.database_port !== ctx.database_port || h.sandbox_transport !== true) {
    throw controlError('FRONTEND_GUARD_FAILED')
  }
  return h
}
async function browserFrontendHealth(checkName) {
  // Chrome puede resolver localhost distinto de Node. Comprobar la ruta que
  // usara el formulario del navegador, sin hacer ninguna escritura.
  const h = await evaluate(`(async()=>{const r=await fetch('/api/__isolated/health',{credentials:'omit',cache:'no-store',redirect:'error'});const d=await r.json().catch(()=>({}));return{status:r.status,origin:location.origin,isolated:d.isolated,run_id:d.run_id,database_port:d.database_port,sandbox_transport:d.sandbox_transport}})()`)
  check(checkName, h.status === 200 && h.origin === origin && h.isolated === true
    && h.run_id === ctx.run_id && h.database_port === ctx.database_port && h.sandbox_transport === true)
}
const initialHealth = await health()
await frontendHealth()
if (resumePayment ? initialHealth.provider_calls.POST !== 1 || (initialHealth.provider_calls.PUT || 0) !== 0 : Object.values(initialHealth.provider_calls).some(Boolean)) throw controlError('PROVIDER_ALREADY_CONTACTED')
const out = path.join(run, 'sandbox_browser_' + randomUUID().replaceAll('-', ''))
await fs.mkdir(out)
const checks = [], blocked = [], errors = [], screenshots = []
let stage = 'datos_oficiales', browser, ws, port, call, evaluate, payment, official, authorizationVerified = false
const authorizationSteps = { card_number_entered: false, card_details_entered: false,
  number_submitted: false, details_submitted: false, bank_credentials_entered: false, bank_submitted: false }
const httpSummary = new Map(), networkFailureSummary = new Map(), networkRequests = new Map()
const resourceTypes = new Set(['Document', 'Stylesheet', 'Image', 'Media', 'Font', 'Script', 'XHR', 'Fetch', 'WebSocket', 'Other'])
const networkErrors = new Set(['net::ERR_ABORTED', 'net::ERR_BLOCKED_BY_CLIENT', 'net::ERR_CONNECTION_REFUSED',
  'net::ERR_CONNECTION_RESET', 'net::ERR_TIMED_OUT', 'net::ERR_NAME_NOT_RESOLVED', 'net::ERR_FAILED',
  'net::ERR_CERT_AUTHORITY_INVALID', 'net::ERR_CERT_DATE_INVALID', 'net::ERR_SSL_PROTOCOL_ERROR', 'net::ERR_INTERNET_DISCONNECTED'])
function networkCategory(url) {
  try { const at = new URL(url).origin; return at === provider ? 'webpay_sandbox' : at === origin ? 'frontend_aislado' : at === ctx.backend_origin ? 'backend_aislado' : 'otro_origen' }
  catch { return 'origen_invalido' }
}
function countNetwork(map, item) { const key = JSON.stringify(item); map.set(key, (map.get(key) || 0) + 1) }
function networkSummary(map) { return [...map].map(([key, count]) => ({ ...JSON.parse(key), count })) }
const secrets = [privateFixture.control, privateFixture.reference, privateFixture.admin?.password, privateFixture.admin?.email, privateFixture.professional?.email, privateFixture.professional?.password].filter(Boolean)
function redact(value) {
  let text = String(value)
  for (const secret of secrets) if (secret.length >= 3) text = text.replaceAll(secret, '<oculto>')
  return text.replace(/[A-Za-z0-9_-]{25,}/g, '<identificador>').replace(/\b\d{6,}\b/g, '<numero>')
}
function check(name, passed, extra = {}) { checks.push({ name, passed: !!passed, ...extra }); if (!passed) throw controlError(name) }
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(fn, label, timeout = 25000) {
  const start = Date.now()
  while (Date.now() - start < timeout) { if (await fn()) return; await delay(100) }
  throw controlError(label)
}
async function localApi(endpoint) {
  if (!endpoint.startsWith('/api/') || endpoint.includes('?')) throw controlError('LOCAL_API_INVALID')
  return evaluate(`(async()=>{const r=await fetch(${JSON.stringify(endpoint)},{credentials:'same-origin',cache:'no-store',redirect:'error'});return{status:r.status,body:await r.json().catch(()=>null)}})()`)
}
async function clickText(pattern) {
  const regex = new RegExp(pattern)
  return evaluate(`(()=>{const regex=new RegExp(${JSON.stringify(regex.source)});const n=s=>s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();const docs=[document];for(const f of document.querySelectorAll('iframe')){try{if(f.contentDocument)docs.push(f.contentDocument)}catch{}}for(const d of docs){const e=[...d.querySelectorAll('button,input[type=submit],input[type=button],a,[role=button]')].find(e=>e.getClientRects().length&&!e.disabled&&regex.test(n(e.innerText||e.value||e.getAttribute('aria-label')||'')));if(e){e.click();return true}}return false})()`)
}
async function snapshot(label) {
  await evaluate(`(()=>{for(const e of document.querySelectorAll('input,textarea'))e.style.visibility='hidden';const s=${JSON.stringify(secrets)};const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);const a=[];while(w.nextNode())a.push(w.currentNode);for(const n of a){if(['SCRIPT','STYLE'].includes(n.parentElement?.tagName))continue;let t=n.nodeValue;for(const p of s)if(p.length>=3)t=t.replaceAll(p,'[oculto]');n.nodeValue=t.replace(/\\b(?:\\d[ -]?){12,19}\\b/g,'[dato oculto]').replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}/g,'[correo]')}})()`)
  const shot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
  await fs.writeFile(path.join(out, label + '.png'), Buffer.from(shot.data, 'base64'), { flag: 'wx' })
  screenshots.push(label + '.png')
}
try {
  // Fuente primaria: el repositorio oficial de documentación. Ningún valor va al código/log.
  const docsUrl = 'https://raw.githubusercontent.com/TransbankDevelopers/transbank-developers-docs/master/documentacion/como_empezar/README.md'
  const docsMetadata = { source: docsUrl, http_status: null, bytes_utf8: null, sha256_utf8: null, parser: null }
  const saveDocsMetadata = () => fs.writeFile(path.join(out, 'documentacion_oficial_metadatos.json'), JSON.stringify(docsMetadata, null, 2))
  let docsResponse
  try {
    docsResponse = await fetch(docsUrl, { redirect: 'error', signal: AbortSignal.timeout(15000) })
  } catch {
    await saveDocsMetadata()
    throw controlError('OFFICIAL_DOCS_NETWORK_FAILED')
  }
  docsMetadata.http_status = docsResponse.status
  if (!docsResponse.ok) {
    await saveDocsMetadata()
    throw controlError('OFFICIAL_DOCS_HTTP_FAILED')
  }
  let document
  try { document = await docsResponse.text() }
  catch {
    await saveDocsMetadata()
    throw controlError('OFFICIAL_DOCS_NETWORK_FAILED')
  }
  docsMetadata.bytes_utf8 = Buffer.byteLength(document, 'utf8')
  docsMetadata.sha256_utf8 = createHash('sha256').update(document, 'utf8').digest('hex')
  if (docsMetadata.bytes_utf8 > 500000) {
    await saveDocsMetadata()
    throw controlError('OFFICIAL_DOCS_TOO_LARGE')
  }
  const parsed = datosSandboxDesdeDocumentacion(document)
  docsMetadata.parser = parsed.metadata
  await saveDocsMetadata()
  if (parsed.code) throw controlError(parsed.code)
  official = { ...parsed.data, month: '12', year: String(new Date().getFullYear() + 2), source: docsUrl }
  secrets.push(...Object.values(parsed.data))
  await fs.writeFile(path.join(out, 'datos_sandbox_privados.json'), JSON.stringify(official), { flag: 'wx' })
  check('datos_sinteticos_obtenidos_de_fuente_oficial', true)
  stage = 'inicio_navegador'
  browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-sync', '--disable-extensions', '--host-resolver-rules=MAP localhost 127.0.0.1', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--user-data-dir=' + path.join(out, 'profile'), 'about:blank'], { stdio: 'ignore', windowsHide: true })
  await until(async () => { try { port = Number((await fs.readFile(path.join(out, 'profile/DevToolsActivePort'), 'utf8')).split('\n')[0]); return !!port } catch { return false } }, 'edge_no_iniciado')
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`, { redirect: 'error' })).json()
  const target = targets.find(t => t.type === 'page')
  if (!target) throw controlError('CDP_TARGET_MISSING')
  ws = new WebSocket(target.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
  let id = 0
  const pending = new Map(), responses = new Map()
  call = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id, timer = setTimeout(() => { pending.delete(n); reject(controlError('CDP_TIMEOUT')) }, 20000)
    pending.set(n, { resolve, reject, timer }); ws.send(JSON.stringify({ id: n, method, params }))
  })
  ws.addEventListener('message', event => {
    const m = JSON.parse(event.data)
    if (m.id) { const p = pending.get(m.id); if (p) { pending.delete(m.id); clearTimeout(p.timer); m.error ? p.reject(controlError('CDP_REJECTED')) : p.resolve(m.result) } }
    if (m.method === 'Network.requestWillBeSent' && networkRequests.size < 2000) {
      networkRequests.set(m.params.requestId, { origin: networkCategory(m.params.request.url),
        type: resourceTypes.has(m.params.type) ? m.params.type : 'Other' })
    }
    if (m.method === 'Network.responseReceived') {
      const status = m.params.response.status
      if (Number.isInteger(status) && status >= 100 && status <= 599) countNetwork(httpSummary, {
        origin: networkCategory(m.params.response.url), type: resourceTypes.has(m.params.type) ? m.params.type : 'Other', status,
      })
    }
    if (m.method === 'Network.loadingFailed') {
      const request = networkRequests.get(m.params.requestId) || { origin: 'origen_invalido', type: 'Other' }
      countNetwork(networkFailureSummary, { ...request, code: networkErrors.has(m.params.errorText) ? m.params.errorText : 'OTHER', canceled: m.params.canceled === true })
      networkRequests.delete(m.params.requestId)
    }
    if (m.method === 'Network.loadingFinished') networkRequests.delete(m.params.requestId)
    if (m.method === 'Fetch.requestPaused') {
      let allowed = false, host = 'desconocido'
      try { const u = new URL(m.params.request.url); host = u.hostname; allowed = [origin, ctx.backend_origin, provider].includes(u.origin) || ['data:', 'blob:'].includes(u.protocol) } catch { /* fail closed */ }
      const op = allowed ? call('Fetch.continueRequest', { requestId: m.params.requestId }) : call('Fetch.failRequest', { requestId: m.params.requestId, errorReason: 'BlockedByClient' })
      if (!allowed && blocked.length < 100) blocked.push({ stage, hostname: host })
      op.catch(() => {})
    }
    if (m.method === 'Network.responseReceived') {
      const u = new URL(m.params.response.url)
      if (u.origin === origin && u.pathname.endsWith('/webpay/iniciar/')) responses.set(m.params.requestId, { status: m.params.response.status })
    }
    if (m.method === 'Network.loadingFinished' && responses.has(m.params.requestId)) {
      const status = responses.get(m.params.requestId).status
      call('Network.getResponseBody', { requestId: m.params.requestId }).then(r => {
        const body = JSON.parse(r.base64Encoded ? Buffer.from(r.body, 'base64').toString('utf8') : r.body)
        if (status === 201 && body.ambiente === 'TRANSBANK_INTEGRACION' && typeof body.token === 'string' && typeof body.url === 'string' && new URL(body.url).origin === provider) { payment = body; secrets.push(body.token) }
      }).catch(() => {})
    }
  })
  evaluate = async expression => { const r = await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw controlError('UI_EVALUATION_FAILED'); return r.result.value }
  await call('Runtime.enable'); await call('Page.enable'); await call('Network.enable')
  await call('Fetch.enable', { patterns: [{ urlPattern: '*' }] })
  await call('Emulation.setDeviceMetricsOverride', { width: 1366, height: 1000, deviceScaleFactor: 1, mobile: false })
  stage = 'guardia_proxy_desde_navegador_antes_de_referencia'
  await call('Page.navigate', { url: origin + '/acceso-profesional' })
  await until(() => evaluate("document.readyState==='complete'&&location.origin==='http://localhost:5173'"), 'origen_local_no_preparado')
  await browserFrontendHealth('proxy_navegador_aislado_antes_de_referencia_privada')
  stage = 'seguimiento_empresa_sintetica'
  if (resumePayment) {
    payment = resumePayment; secrets.push(payment.token)
    await call('Page.navigate', { url: origin + '/acceso-profesional' })
    await until(() => evaluate("document.readyState==='complete'&&!!document.querySelector('main')"), 'pagina_local_no_lista_para_reanudar')
    await frontendHealth()
    await browserFrontendHealth('proxy_navegador_aislado_antes_de_reanudar')
    await evaluate(`(()=>{const f=document.createElement('form');f.method='POST';f.action=${JSON.stringify(payment.url)};const t=document.createElement('input');t.type='hidden';t.name='token_ws';t.value=${JSON.stringify(payment.token)};f.append(t);document.body.append(f);f.submit()})()`)
    await until(() => evaluate("location.origin==='https://webpay3gint.transbank.cl'"), 'checkout_previo_no_reanudado')
    check('checkout_pendiente_reanudado_sin_crear_otro_pago', true)
  } else {
  await call('Page.navigate', { url: origin + '/seguimiento?referencia=' + encodeURIComponent(privateFixture.reference) })
  // La referencia en la URL solo precarga el formulario y se retira del
  // historial. Consultar requiere la misma accion explicita que hace la empresa.
  await until(() => evaluate("!!document.querySelector('#sg-referencia')"), 'consulta_seguimiento_no_disponible')
  if (!await clickText('^consultar estado$')) throw controlError('consulta_seguimiento_no_disponible')
  await until(() => evaluate("!!document.querySelector('input[name=\"metodo-e3\"]')"), 'formulario_pago_no_disponible')
  await evaluate("document.querySelectorAll('input[name=\"metodo-e3\"]')[1].click()")
  await until(() => evaluate("[...document.querySelectorAll('button')].some(e=>!e.disabled&&e.textContent.includes('Pagar mediante Webpay'))"), 'politica_o_horario_no_habilita_pago')
  await snapshot('01_webpay_antes_sin_datos_tarjeta')
  await frontendHealth()
  await browserFrontendHealth('proxy_navegador_aislado_antes_de_iniciar')
  await clickText('pagar mediante webpay')
  await until(() => payment && evaluate("location.origin==='https://webpay3gint.transbank.cl'"), 'checkout_no_iniciado_en_sandbox', 30000)
  }
  await fs.writeFile(path.join(out, 'checkout_privado.json'), JSON.stringify(payment), { flag: 'wx' })
  check('checkout_skilly_http_y_proveedor_sandbox_reales', true)
  stage = 'autorizacion_sandbox'
  const end = Date.now() + 90000
  let cardEntered = false, cardDetailsEntered = false, bankEntered = false, creditChosen = false
  let submittedNumber = false, submittedCard = false, submittedBank = false
  while (Date.now() < end) {
    const where = await evaluate("({origin:location.origin,path:location.pathname,returned:location.origin==='http://localhost:5173'&&location.pathname==='/seguimiento'})")
    if (where.returned) break
    if (where.origin !== provider) throw controlError('destino_de_autenticacion_fuera_del_sandbox_permitido')
    const form = await evaluate(`(()=>{const docs=[document];for(const f of document.querySelectorAll('iframe')){try{if(f.contentDocument)docs.push(f.contentDocument)}catch{}}const fields=[];for(let d=0;d<docs.length;d++)for(const e of docs[d].querySelectorAll('input,select')){if(e.getClientRects().length&&!e.disabled&&e.type!=='hidden'){const key=[e.id,e.name,e.placeholder,e.autocomplete,e.labels?.[0]?.innerText||''].join(' ');e.dataset.sandboxField=String(fields.length);fields.push({key,type:e.type,tag:e.tagName,index:fields.length,doc:d,max:e.maxLength,options:e.tagName==='SELECT'?[...e.options].map(o=>({value:o.value,text:o.textContent})):[]})}}return{fields,challenge:[...document.querySelectorAll('iframe')].some(f=>/captcha|challenge/i.test(f.title+' '+f.src))}})()`)
    if (form.challenge) throw controlError('desafio_humano_del_proveedor_requiere_interaccion_local')
    const recognized = camposFormularioSandbox(form.fields)
    const { card, cvv: cvvField, month, year, expiry, rut: rutField, password: passwordField } = recognized
    const fill = async (f, value) => {
      if (!f) return false
      await evaluate(`(()=>{const docs=[document];for(const f of document.querySelectorAll('iframe')){try{if(f.contentDocument)docs.push(f.contentDocument)}catch{}}const e=docs[${f.doc}].querySelector('[data-sandbox-field="${f.index}"]');const p=e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));e.dispatchEvent(new Event('blur',{bubbles:true}))})()`)
      return true
    }
    if (card && !cardEntered) {
      await fill(card, official.pan)
      cardEntered = true
      authorizationSteps.card_number_entered = true
    }
    // El checkout actual solicita primero el numero y luego los campos de
    // seguridad. No inventar campos ni saltar ese primer Continuar del proveedor.
    if (cardEntered && !cardDetailsEntered && recognized.cardDetailsComplete) {
      await fill(cvvField, official.cvv)
      if (month && year) {
        const chosenMonth = month.options.find(o => Number(o.value) === Number(official.month))?.value || official.month
        const chosenYear = year.options.find(o => [official.year, official.year.slice(-2)].includes(o.value))?.value || official.year
        await fill(month, chosenMonth); await fill(year, chosenYear)
      } else await fill(expiry, official.month + (expiry.max === 4 ? '' : '/') + official.year.slice(-2))
      cardDetailsEntered = true
      authorizationSteps.card_details_entered = true
    }
    if (rutField && passwordField && !bankEntered) {
      await fill(rutField, official.rut); await fill(passwordField, official.password); bankEntered = true
      authorizationSteps.bank_credentials_entered = true
    }
    if (bankEntered && !submittedBank) submittedBank = await clickText('^(aceptar|autorizar|autenticar|continuar|pagar|ingresar)(\\b|$)')
    else if (cardDetailsEntered && !submittedCard) submittedCard = await clickText('^(pagar|continuar|aceptar)(\\b|$)')
    else if (cardEntered && !submittedNumber && !recognized.cardDetailsPresent) submittedNumber = await clickText('^continuar(\\b|$)')
    else if (!cardEntered && !creditChosen) creditChosen = await clickText('credito|credit card')
    authorizationSteps.number_submitted = submittedNumber
    authorizationSteps.details_submitted = submittedCard
    authorizationSteps.bank_submitted = submittedBank
    await delay(400)
  }
  await until(() => evaluate("location.origin==='http://localhost:5173'&&location.pathname==='/seguimiento'"), 'retorno_del_proveedor_no_completado', 1000)
  check('datos_oficiales_ingresados_en_sandbox', cardEntered && cardDetailsEntered)
  check('retorno_local_real_sin_sustituir_respuesta', true)
  stage = 'estado_e_idempotencia'
  let statusResult
  await until(async () => {
    statusResult = await localApi('/api/pagos/empresa/' + encodeURIComponent(privateFixture.reference) + '/estado/')
    return statusResult.status === 200 && statusResult.body?.estado_pago === 'RETENIDO'
      && statusResult.body?.id_prestacion === privateFixture.prestacion_id
  }, 'pago_no_retenido_no_declarar_autorizado', 10000)
  check('pago_retenido_en_copia_por_confirmacion_real', true)
  const beforeDuplicate = await health()
  check('creacion_y_confirmacion_https_reales', beforeDuplicate.provider_calls.POST === 1 && beforeDuplicate.provider_calls.PUT === 1)
  await frontendHealth()
  const duplicate = await fetch(frontendTransport + '/api/pagos/webpay/retorno/', { method: 'POST', redirect: 'manual', headers: { Host: frontendHost, 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ token_ws: payment.token }) })
  check('retorno_duplicado_idempotente', duplicate.status === 302)
  const afterDuplicate = await health()
  check('retorno_duplicado_no_confirma_ni_cobra_de_nuevo', afterDuplicate.provider_calls.PUT === beforeDuplicate.provider_calls.PUT)
  await snapshot('02_pago_sandbox_confirmado')
  authorizationVerified = true
} catch (error) {
  errors.push({ stage, ...errorInfo(error) })
  if (evaluate) {
    try {
      const meta = await evaluate("({origin:location.origin,fields:[...document.querySelectorAll('input,select,button')].filter(e=>e.getClientRects().length).map(e=>({tag:e.tagName,type:e.type,id:e.id,name:e.name,disabled:e.disabled,required:e.required,valid:e.validity?.valid,value_missing:e.validity?.valueMissing,pattern_mismatch:e.validity?.patternMismatch,type_mismatch:e.validity?.typeMismatch,placeholder:e.placeholder||'',text:e.tagName==='BUTTON'?e.textContent.trim().slice(0,60):''})),alerts:[...document.querySelectorAll('[role=alert],.error,.invalid-feedback')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim().slice(0,150)),iframes:[...document.querySelectorAll('iframe')].map(e=>({title:e.title,origin:(()=>{try{return new URL(e.src,location.href).origin}catch{return 'desconocido'}})()}))})")
      await fs.writeFile(path.join(out, 'bloqueo_interfaz.json'), redact(JSON.stringify(meta, null, 2)), { flag: 'wx' })
    } catch { /* No valores de campos, URLs privadas o tokens en diagnóstico. */ }
    try {
      const page = await evaluate(`(()=>{const text=document.body?.innerText||'';return{ready_state:document.readyState,body_text_length:text.length,visible_controls:[...document.querySelectorAll('input,select,button')].filter(e=>e.getClientRects().length).length,iframe_count:document.querySelectorAll('iframe').length,flags:(${indicadoresPaginaSandbox.toString()})(text)}})()`)
      await fs.writeFile(path.join(out, 'pagina_proveedor_metadatos.json'), JSON.stringify(page, null, 2), { flag: 'wx' })
    } catch { /* Nunca recopilar el texto bruto de una pagina del proveedor. */ }
  }
} finally {
  try { ws?.close() } catch { /* Own context only. */ }
  if (browser) { browser.kill(); await delay(200) }
  const finalHealth = await health().catch(() => null)
  const result = { completed: !errors.length, authorization_verified: authorizationVerified, resumed_checkout: !!resumePayment, real_money: false, production_provider: false, run_id: ctx.run_id, frontend_transport: 'ipv4_host_localhost', browser_dns_scope: 'private_profile_only', stage, checks, passed: checks.filter(c => c.passed).length, failed: checks.filter(c => !c.passed).length, errors, blocked_requests: blocked, screenshots, provider_calls: finalHealth?.provider_calls || null, real: ['React', 'Django/HTTP/PostgreSQL de copia', 'Webpay integración HTTPS y UI si los checks correspondientes pasan'], mocks: false, limitations: ['Un contrato sandbox dedicado; no acredita pagos, reembolsos ni liquidaciones productivos.'] }
  result.authorization_steps = authorizationSteps
  result.network_summary = { http: networkSummary(httpSummary), failures: networkSummary(networkFailureSummary) }
  await fs.writeFile(path.join(out, 'resultado.json'), JSON.stringify(result, null, 2), { flag: 'wx' })
  console.log(JSON.stringify({ output: out, completed: result.completed, authorization_verified: authorizationVerified, passed: result.passed, stage, errors }))
  if (!result.completed) process.exitCode = 1
}
}

// JSON privado malformado, errores de lectura y guardias de setup tampoco
// deben imprimir mensajes, snippets ni stacks con valores de las fixtures.
main().catch(error => {
  console.log(JSON.stringify({ completed: false, authorization_verified: false, ...errorInfo(error) }))
  process.exitCode = 1
})
