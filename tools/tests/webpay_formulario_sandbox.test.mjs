import assert from 'node:assert/strict'
import { test } from 'node:test'
import { randomBytes } from 'node:crypto'
import { camposFormularioSandbox, indicadoresPaginaSandbox } from '../webpay_formulario_sandbox.mjs'

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
