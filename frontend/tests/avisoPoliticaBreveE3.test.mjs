import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve, dirname } from 'node:path'
import { mostrarAvisoPolitica, mostrarBloquePolitica } from '../src/avisoPoliticaCancelacionE3.mjs'

const dir = dirname(fileURLToPath(import.meta.url))
const src = readFileSync(resolve(dir, '../src/PagoEmpresaSeguimiento.jsx'), 'utf8')
const modal = readFileSync(resolve(dir, '../src/AvisoPoliticaCancelacionE3.jsx'), 'utf8')
const pendiente = { habilitarFormulario: true, cargando: false, politica: { aceptada: false, version: 'firma', texto: 'Condiciones', contrato_previo: false } }

test('se muestra el aviso antes de la aceptación', () => {
  assert.equal(mostrarBloquePolitica(pendiente), true)
  assert.equal(mostrarAvisoPolitica({ ...pendiente, referencia: 'consulta-1' }), true)
})
test('una vez aceptada, desaparece el bloque de política y no se abre de nuevo el modal', () => {
  const aceptado = { ...pendiente, politica: { ...pendiente.politica, aceptada: true } }
  assert.equal(mostrarBloquePolitica(aceptado), false)
  assert.equal(mostrarAvisoPolitica({ ...aceptado, referencia: 'consulta-1' }), false)
})
test('al cerrar sin aceptar, el consentimiento sigue pendiente', () => {
  assert.equal(mostrarBloquePolitica(pendiente), true)
})
test('no presenta bloque de política si aún no corresponde pagar', () => {
  assert.equal(mostrarBloquePolitica({ ...pendiente, habilitarFormulario: false }), false)
})
test('la interfaz oculta completamente el bloque tras aceptación persistida', () => {
  assert.match(src, /mostrarBloquePolitica\(\{ habilitarFormulario, cargando, politica \}\)/)
  assert.match(src, /politica\.aceptada && \(/)
  assert.match(src, /if \(d\.aceptada !== true\) throw new Error/)
  assert.doesNotMatch(src, /Consultar política aceptada/)
})
test('no comunica datos internos ni versiones a la organización en el aviso', () => {
  assert.doesNotMatch(modal, /comisión normal|versión contractual|SKILLY-E3|E3-CANCELACION|perfil profesional/i)
  assert.match(modal, /politica\?\.texto/)
})
