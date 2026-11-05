import test from 'node:test'
import assert from 'node:assert/strict'
import { accionesDisponibles, bloquesElegibles, validarCambioAgenda } from '../src/politicasAgendaPrestacionE3.mjs'

const motivo = 'La organización solicitó modificar el horario de la primera reunión.'
const futuro = { id_disponibilidad: 12, fecha: '2099-06-12', hora_inicio: '10:00:00', hora_fin: '11:00:00', estado: 'DISPONIBLE', tiene_reserva_activa: false }

test('solo CONTRATADA permite cancelar o postergar', () => {
  assert.deepEqual(accionesDisponibles('CONTRATADA'), ['REAGENDAR', 'POSTERGAR', 'CANCELAR'])
  assert.deepEqual(accionesDisponibles('POSTERGADA'), ['REAGENDAR'])
  assert.deepEqual(accionesDisponibles('FINALIZADA'), [])
})
test('bloques disponibles futuros excluyen pasado, ocupado y reservado', () => {
  const bloques = [futuro, { ...futuro, id_disponibilidad: 13, estado: 'RESERVADA' }, { ...futuro, id_disponibilidad: 14, tiene_reserva_activa: true }, { ...futuro, id_disponibilidad: 15, fecha: '2020-01-01' }]
  assert.deepEqual(bloquesElegibles(bloques).map(b => b.id_disponibilidad), [12])
})
test('reagendar requiere bloque elegible existente', () => {
  assert.ok(validarCambioAgenda({ estado: 'CONTRATADA', accion: 'REAGENDAR', motivo, bloqueId: '99', bloques: [futuro] }))
  assert.equal(validarCambioAgenda({ estado: 'CONTRATADA', accion: 'REAGENDAR', motivo, bloqueId: '12', bloques: [futuro] }), '')
})
test('cancelar no se ofrece para prestación POSTERGADA', () => {
  assert.ok(validarCambioAgenda({ estado: 'POSTERGADA', accion: 'CANCELAR', motivo, bloqueId: '', bloques: [] }))
})
test('motivo obligatorio con límites de 20 a 500 caracteres', () => {
  assert.ok(validarCambioAgenda({ estado: 'CONTRATADA', accion: 'CANCELAR', motivo: 'Corto', bloques: [] }))
  assert.ok(validarCambioAgenda({ estado: 'CONTRATADA', accion: 'CANCELAR', motivo: 'x'.repeat(501), bloques: [] }))
  assert.equal(validarCambioAgenda({ estado: 'CONTRATADA', accion: 'CANCELAR', motivo, bloques: [] }), '')
})
