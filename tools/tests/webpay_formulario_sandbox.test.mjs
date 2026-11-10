import assert from 'node:assert/strict'
import { test } from 'node:test'
import { randomBytes } from 'node:crypto'
import path from 'node:path'
import os from 'node:os'
import { camposFormularioSandbox, indicadoresPaginaSandbox, checkoutDesdeFormularioSandbox, descriptorSesionSandbox } from '../webpay_formulario_sandbox.mjs'

const syntheticToken = '0'.repeat(16)
const providerRequest = () => ({ method: 'POST', url: 'https://webpay3gint.transbank.cl/webpayserver/initTransaction',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, postData: new URLSearchParams({ token_ws: syntheticToken }).toString() })

test('captura el token del POST real observado solo despues del inicio local 201', () => {
  const request = providerRequest()
  assert.equal(checkoutDesdeFormularioSandbox(request), null)
  assert.equal(checkoutDesdeFormularioSandbox(request, { inicioLocal201: 200 }), null)
  assert.deepEqual(checkoutDesdeFormularioSandbox(request, { inicioLocal201: true }), {
    token: syntheticToken, url: request.url, ambiente: 'TRANSBANK_INTEGRACION',
  })
})

test('no captura GET, produccion, host parecido, credenciales o rutas y query ajenas', () => {
  const initial = providerRequest()
  for (const change of [
    { method: 'GET' }, { url: 'https://webpay3g.transbank.cl/webpayserver/initTransaction' },
    { url: initial.url.replace('.cl/', '.cl.example.invalid/') },
    { url: initial.url.replace('https://', 'https://user@') },
    { url: initial.url + '?token_ws=' + syntheticToken }, { url: initial.url + '#fragment' },
    { url: initial.url.replace('/initTransaction', '/otro') },
    { headers: { 'Content-Type': 'application/json' } },
  ]) assert.equal(checkoutDesdeFormularioSandbox({ ...initial, ...change }, { inicioLocal201: true }), null)
})

test('rechaza tokens duplicados, campos adicionales y cuerpos invalidos sin excepcion con fragmentos', () => {
  const initial = providerRequest(), canary = 'private-' + randomBytes(36).toString('hex')
  for (const postData of [
    'token_ws=' + syntheticToken + '&token_ws=' + syntheticToken,
    'token_ws=' + syntheticToken + '&extra=' + canary, 'token_ws=../' + canary,
    '{"private":"' + canary, 'token_ws=' + '0'.repeat(201), 'token_ws=', 'x'.repeat(4097),
  ]) assert.equal(checkoutDesdeFormularioSandbox({ ...initial, postData }, { inicioLocal201: true }), null)
})

test('descriptor de sesion conserva destino privado en memoria y exige contexto y perfil del mismo ensayo', () => {
  const runDir = path.resolve(os.tmpdir(), 'skilly-session-test'), contextPath = path.join(runDir, 'contexto.json')
  const descriptor = { location: 'https://webpay3gint.transbank.cl/webpayserver/pago?opaque=' + syntheticToken,
    original_profile: path.join(runDir, 'sandbox_browser_fake', 'profile'), context_path: contextPath }
  assert.deepEqual(descriptorSesionSandbox(descriptor, { contextPath, runDir }), descriptor)
  assert.equal(descriptorSesionSandbox({ ...descriptor, context_path: path.resolve(os.tmpdir(), 'other', 'contexto.json') }, { contextPath, runDir }), null)
  assert.equal(descriptorSesionSandbox({ ...descriptor, original_profile: path.resolve(runDir, '..', 'other', 'profile') }, { contextPath, runDir }), null)
  assert.equal(descriptorSesionSandbox({ ...descriptor, original_profile: runDir }, { contextPath, runDir }), null)
})

test('descriptor rechaza produccion, userinfo, fragmentos y datos corruptos sin exponer canarios', () => {
  const canary = 'private-' + randomBytes(36).toString('hex')
  const runDir = path.resolve(os.tmpdir(), 'skilly-session-test'), contextPath = path.join(runDir, 'contexto.json')
  const descriptor = { location: 'https://webpay3gint.transbank.cl/webpayserver/pago',
    original_profile: path.join(runDir, 'sandbox_browser_fake', 'profile'), context_path: contextPath }
  for (const location of ['https://webpay3g.transbank.cl/' + canary,
    'https://webpay3gint.transbank.cl.example.invalid/' + canary,
    'https://' + canary + '@webpay3gint.transbank.cl/pago', descriptor.location + '#' + canary,
    'http://webpay3gint.transbank.cl/' + canary, descriptor.location.replace('.cl/', '.cl:444/')]) {
    assert.equal(descriptorSesionSandbox({ ...descriptor, location }, { contextPath, runDir }), null)
  }
  for (const invalid of [null, canary, [], { ...descriptor, original_profile: canary }]) {
    assert.equal(descriptorSesionSandbox(invalid, { contextPath, runDir }), null)
  }
})

test('descriptor admite la ruta SPA oficial #/ conservando el mismo origen HTTPS', () => {
  const runDir = path.resolve(os.tmpdir(), 'skilly-session-test'), contextPath = path.join(runDir, 'contexto.json')
  const descriptor = { location: 'https://webpay3gint.transbank.cl/webpayserver/#/pago?opaque=' + syntheticToken,
    original_profile: path.join(runDir, 'sandbox_browser_fake', 'profile'), context_path: contextPath }
  assert.deepEqual(descriptorSesionSandbox(descriptor, { contextPath, runDir }), descriptor)
})

test('descriptor SPA rechaza controles, fragmentos ajenos, rutas relativas a otro host y exceso de longitud', () => {
  const runDir = path.resolve(os.tmpdir(), 'skilly-session-test'), contextPath = path.join(runDir, 'contexto.json')
  const descriptor = { location: 'https://webpay3gint.transbank.cl/webpayserver/',
    original_profile: path.join(runDir, 'sandbox_browser_fake', 'profile'), context_path: contextPath }
  for (const location of [descriptor.location + '#otro', descriptor.location + '#//example.invalid/',
    descriptor.location + '#/%2Fexample.invalid/', descriptor.location + '#/paso\nprivado',
    descriptor.location + '#/paso%0Aprivado', descriptor.location + '#/' + 'x'.repeat(2048),
    'javascript:alert(0)', '//webpay3gint.transbank.cl/#/pago']) {
    assert.equal(descriptorSesionSandbox({ ...descriptor, location }, { contextPath, runDir }), null)
  }
})

test('el primer paso de numero de tarjeta no requiere todavia vencimiento ni CVV', () => {
  const card = { key: 'card-number', type: 'tel' }
  const result = camposFormularioSandbox([card])
  assert.equal(result.card, card)
  assert.equal(result.cardDetailsPresent, false)
  assert.equal(result.cardDetailsComplete, false)
})

test('el paso de seguridad admite vencimiento combinado o mes y ano separados', () => {
  const cvv = { key: 'codigo de seguridad', type: 'password' }
  const expiry = { key: 'card-expiration-date' }
  assert.equal(camposFormularioSandbox([cvv, expiry]).cardDetailsComplete, true)
  assert.equal(camposFormularioSandbox([cvv, { key: 'mes' }, { key: 'año' }]).cardDetailsComplete, true)
  assert.equal(camposFormularioSandbox([cvv, { key: 'mes' }]).cardDetailsComplete, false)
})

test('el CVV oculto no se confunde con la clave de autenticacion bancaria', () => {
  const cvv = { key: 'security-code', type: 'password' }
  const password = { key: 'clave', type: 'password' }
  const rut = { key: 'rut cliente', type: 'text' }
  const result = camposFormularioSandbox([cvv, rut, password])
  assert.equal(result.cvv, cvv)
  assert.equal(result.password, password)
  assert.equal(result.rut, rut)
  assert.equal(camposFormularioSandbox([cvv]).password, undefined)
})

test('diagnostico de pagina identifica expiracion sin devolver texto, referencias ni secretos', () => {
  const canary = randomBytes(36).toString('hex')
  const result = indicadoresPaginaSandbox('La sesión ha expirado. Dato privado: ' + canary)
  assert.equal(result.transaction_expired, true)
  assert.ok(Object.values(result).every(value => typeof value === 'boolean'))
  assert.ok(!JSON.stringify(result).includes(canary))
  assert.ok(!JSON.stringify(result).includes('Dato privado'))
  assert.equal(indicadoresPaginaSandbox('Confirmación bancaria normal').transaction_expired, false)
})
