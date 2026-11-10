// Comparacion reproductible del App anterior y actual. No Django/BD/red externa.
// node tools/pruebas_marketplace_navegador.mjs --before-ref 34a2834 --evidence C:\ruta\externa
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { createRequire } from 'node:module'
import { createHash, randomUUID } from 'node:crypto'
import { execFile, spawn } from 'node:child_process'
import { promisify } from 'node:util'

async function main() {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
  const option = name => { const index = process.argv.indexOf(name); return index > 1 ? process.argv[index + 1] : null }
  const beforeRef = option('--before-ref'), evidenceBase = option('--evidence')
  if (!/^[a-f0-9]{7,40}$/i.test(beforeRef || '') || !evidenceBase || !path.isAbsolute(evidenceBase)) throw new Error('argumentos_invalidos')
  const base = await fs.realpath(evidenceBase), relative = path.relative(root, base)
  if (!relative || !relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('evidencia_debe_ser_externa')
  if (!(await fs.stat(base)).isDirectory()) throw new Error('evidencia_no_es_directorio')
  const git = async args => (await promisify(execFile)('git', ['-C', root, ...args], { encoding: 'utf8', windowsHide: true, maxBuffer: 5 * 1024 * 1024 })).stdout
  const beforeCommit = (await git(['rev-parse', '--verify', beforeRef + '^{commit}'])).trim()
  const beforeSource = await git(['show', beforeCommit + ':frontend/src/App.jsx'])
  const sha = source => createHash('sha256').update(source).digest('hex')
  const sourceFiles = ['frontend/src/App.jsx', 'frontend/src/App.css', 'frontend/src/useDialogoAccesible.js', 'tools/harness_marketplace.js', 'tools/pruebas_marketplace_navegador.mjs']
  const fingerprint = async () => Object.fromEntries(await Promise.all(sourceFiles.map(async file => [file, sha(await fs.readFile(path.join(root, file)))])))
  const beforeHashes = await fingerprint()
  const out = path.join(base, 'marketplace_modal_' + randomUUID().replaceAll('-', '')); await fs.mkdir(out)
  await fs.writeFile(path.join(out, 'App_antes.jsx'), beforeSource, { flag: 'wx' })
  const requireFrontend = createRequire(path.join(root, 'frontend/package.json'))
  const { createServer, transformWithOxc } = await import(pathToFileURL(requireFrontend.resolve('vite')).href)
  const react = (await import(pathToFileURL(requireFrontend.resolve('@vitejs/plugin-react')).href)).default
  const compiled = (await transformWithOxc(beforeSource, 'App.jsx', { jsx: { runtime: 'automatic', importSource: 'react' }, sourcemap: false })).code
    .replace(/from\s+(["'])\.\/([^"']+)\1/g, 'from "/src/$2"').replace(/import\s+(["'])\.\/([^"']+)\1/g, 'import "/src/$2"')
  const harness = await fs.readFile(path.join(root, 'tools/harness_marketplace.js'), 'utf8')
  const checks = [], runs = [], errors = [], blocked = []
  let server, browser, ws, apiRequests = 0, stage = 'iniciar_servidor'
  const errorCodes = new Set(['argumentos_invalidos', 'evidencia_debe_ser_externa', 'evidencia_no_es_directorio',
    'edge_no_iniciado', 'pagina_cdp_no_encontrada', 'cdp_timeout', 'cdp_rechazado', 'harness_rechazado',
    'modulos_no_cargados', 'puerto_efimero_ajeno_al_entorno_operativo', 'ninguna_peticion_API_real', 'fuentes_sin_cambios_durante_ensayo',
    ...[1366, 390].flatMap(width => ['before', 'after'].map(phase => phase + '_' + width + '_completo'))])
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
  const until = async (fn, code) => { const end = Date.now() + 20000; while (Date.now() < end) { if (await fn()) return; await pause(50) } throw new Error(code) }
  const check = (name, passed) => { checks.push({ name, passed: !!passed }); if (!passed) throw new Error(name) }
  try {
    server = await createServer({ root: path.join(root, 'frontend'), configFile: false, publicDir: false,
      cacheDir: path.join(out, 'vite_cache'), plugins: [react(), {
        name: 'marketplace-harness',
        resolveId(id) { if (id === 'virtual:marketplace-entry') return '\0marketplace-entry.js'; if (id === 'virtual:marketplace-before') return '\0marketplace-before.jsx' },
        load(id) {
          if (id === '\0marketplace-before.jsx') return compiled
          if (id === '\0marketplace-entry.js') return "import React from 'react';import {createRoot} from 'react-dom/client';import Before from 'virtual:marketplace-before';import After from '/src/App.jsx';import '/src/index.css';window.__marketplaceModules={React,createRoot,Before,After};"
        },
        configureServer(vite) { vite.middlewares.use(async (req, res, next) => {
          if (req.url?.startsWith('/api/')) { apiRequests++; res.statusCode = 503; res.end('{}'); return }
          if (req.url !== '/__marketplace_harness') return next()
          const html = await vite.transformIndexHtml('/__marketplace_harness', '<!doctype html><html lang="es"><head><meta charset="UTF-8"></head><body><script type="module">import "virtual:marketplace-entry"</script></body></html>')
          res.setHeader('Content-Type', 'text/html'); res.end(html)
        }) },
      }], server: { host: '127.0.0.1', port: 0, strictPort: true, hmr: false, open: false } })
    await server.listen()
    const serverPort = server.httpServer.address().port
    check('puerto_efimero_ajeno_al_entorno_operativo', ![8000, 5173, 5432, 9000].includes(serverPort))
    const origin = 'http://127.0.0.1:' + serverPort
    stage = 'iniciar_edge'
    browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--disable-background-networking', '--disable-sync', '--disable-extensions', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--user-data-dir=' + path.join(out, 'profile'), 'about:blank'], { windowsHide: true, stdio: 'ignore' })
    let debugPort
    await until(async () => { try { debugPort = Number((await fs.readFile(path.join(out, 'profile/DevToolsActivePort'), 'utf8')).split('\n')[0]); return !!debugPort } catch { return false } }, 'edge_no_iniciado')
    const targets = await (await fetch('http://127.0.0.1:' + debugPort + '/json/list', { redirect: 'error' })).json()
    const target = targets.find(item => item.type === 'page'); if (!target) throw new Error('pagina_cdp_no_encontrada')
    ws = new WebSocket(target.webSocketDebuggerUrl)
    await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }) })
    let id = 0; const pending = new Map()
    const call = (method, params = {}) => new Promise((resolve, reject) => {
      const key = ++id, timer = setTimeout(() => { pending.delete(key); reject(new Error('cdp_timeout')) }, 90000)
      pending.set(key, { resolve, reject, timer }); ws.send(JSON.stringify({ id: key, method, params }))
    })
    ws.addEventListener('message', event => {
      const data = JSON.parse(event.data)
      if (data.id) { const request = pending.get(data.id); if (request) { pending.delete(data.id); clearTimeout(request.timer); data.error ? request.reject(new Error('cdp_rechazado')) : request.resolve(data.result) } }
      if (data.method === 'Fetch.requestPaused') {
        let allowed = false
        try { const url = new URL(data.params.request.url); allowed = url.origin === origin || ['data:', 'blob:'].includes(url.protocol) } catch { /* fail closed */ }
        if (!allowed) blocked.push({ blocked: true })
        call(allowed ? 'Fetch.continueRequest' : 'Fetch.failRequest', { requestId: data.params.requestId, ...(!allowed ? { errorReason: 'BlockedByClient' } : {}) }).catch(() => {})
      }
    })
    const evaluate = async expression => {
      const response = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
      if (response.exceptionDetails) throw new Error('harness_rechazado')
      return response.result.value
    }
    await call('Runtime.enable'); await call('Page.enable'); await call('Fetch.enable', { patterns: [{ urlPattern: '*' }] })
    for (const width of [1366, 390]) {
      stage = 'cargar_modulos_' + width
      await call('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false })
      await call('Page.navigate', { url: origin + '/__marketplace_harness' })
      await until(() => evaluate('!!window.__marketplaceModules'), 'modulos_no_cargados')
      await evaluate(harness)
      for (const phase of ['before', 'after']) {
        stage = 'harness_' + phase + '_' + width
        const result = await evaluate(`window.__runMarketplaceHarness(${JSON.stringify(phase)})`)
        runs.push({ viewport: width, ...result })
        check(phase + '_' + width + '_completo', result.completed && result.checks.every(item => item.passed))
        const shot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
        await fs.writeFile(path.join(out, phase + '_' + width + '.png'), Buffer.from(shot.data, 'base64'), { flag: 'wx' })
      }
    }
    check('ninguna_peticion_API_real', apiRequests === 0)
    const afterHashes = await fingerprint()
    check('fuentes_sin_cambios_durante_ensayo', JSON.stringify(beforeHashes) === JSON.stringify(afterHashes))
    await fs.writeFile(path.join(out, 'fuentes.json'), JSON.stringify({ before_commit: beforeCommit, before_App_sha256: sha(beforeSource), before: beforeHashes, after: afterHashes }, null, 2), { flag: 'wx' })
  } catch (error) {
    errors.push({ stage, error_type: ['Error', 'TypeError', 'SyntaxError'].includes(error.name) ? error.name : 'Error',
      code: errorCodes.has(error.message) ? error.message : 'fallo_del_harness' })
  } finally {
    try { ws?.close() } catch { /* Own browser only. */ }
    browser?.kill()
    await server?.close()
    const result = { completed: !errors.length, checks, runs, errors, blocked_requests: blocked.length,
      api_requests_real: apiRequests, postgres: false, external_services: false,
      real: ['React/DOM y componentes App anteriores/actuales'], simulated: ['fetch GET/POST y datos sinteticos'],
      limitations: ['No es E2E con Django/PostgreSQL. No acredita eventos fisicos ni dispositivos moviles reales.'] }
    await fs.writeFile(path.join(out, 'resultado.json'), JSON.stringify(result, null, 2), { flag: 'wx' })
    console.log(JSON.stringify({ output: out, completed: result.completed, runs: runs.length, passed: checks.filter(item => item.passed).length, errors }))
    if (!result.completed) process.exitCode = 1
  }
}
main().catch(error => { console.log(JSON.stringify({ completed: false, error_type: ['Error', 'TypeError', 'SyntaxError'].includes(error.name) ? error.name : 'Error' })); process.exitCode = 1 })
