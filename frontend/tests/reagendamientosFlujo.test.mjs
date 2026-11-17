import test from 'node:test'
import assert from 'node:assert/strict'

import {
  estaAbierto,
  payloadAlternativas,
  puedeConfirmarAdministracion,
  puedeContraproponer,
  puedeEntregarDisponibilidad,
  puedeResponderPropuesta,
  puedeSeleccionarOrganizacion,
  tieneAlternativas,
} from '../src/reagendamientosFlujo.mjs'

test('una contrapropuesta conserva varios bloques existentes y nuevos completos', () => {
  const valor = {
    existentes: [17, 19],
    nuevas: [
      { fecha: '2035-03-10', hora_inicio: '10:00', hora_fin: '11:00' },
      { fecha: '', hora_inicio: '12:00', hora_fin: '13:00' },
      { fecha: '2035-03-11', hora_inicio: '15:00', hora_fin: '16:00' },
    ],
  }

  assert.deepEqual(payloadAlternativas(valor), {
    alternativas_existentes: [17, 19],
    alternativas_nuevas: [
      { fecha: '2035-03-10', hora_inicio: '10:00', hora_fin: '11:00' },
      { fecha: '2035-03-11', hora_inicio: '15:00', hora_fin: '16:00' },
    ],
  })
  assert.equal(tieneAlternativas(valor), true)
  assert.equal(tieneAlternativas({ existentes: [], nuevas: [{}] }), false)
})

test('la organización puede seleccionar ahora o después sin reiniciar la negociación', () => {
  assert.equal(puedeSeleccionarOrganizacion({ estado: 'PENDIENTE_ORGANIZACION' }), true)
  assert.equal(puedeSeleccionarOrganizacion({ estado: 'ESPERANDO_SELECCION' }), true)
  assert.equal(puedeSeleccionarOrganizacion({ estado: 'ESPERANDO_SELECCION', plazo_vencido: true }), false)
  assert.equal(estaAbierto('ESPERANDO_SELECCION'), true)
})

test('el profesional responde solo el caso A y usa como máximo una contrapropuesta', () => {
  const caso = {
    estado: 'PENDIENTE_PROFESIONAL',
    iniciador: 'ORGANIZACION',
    contrapropuesta_profesional_usada: false,
  }
  assert.equal(puedeResponderPropuesta(caso), true)
  assert.equal(puedeContraproponer(caso), true)
  assert.equal(puedeContraproponer({ ...caso, contrapropuesta_profesional_usada: true }), false)
  assert.equal(puedeResponderPropuesta({ ...caso, iniciador: 'PROFESIONAL' }), false)
  assert.equal(puedeEntregarDisponibilidad({ estado: 'ESPERANDO_NUEVO_BLOQUE' }), true)
})

test('administración solo puede aplicar un bloque con ambas autorizaciones', () => {
  const caso = {
    estado: 'LISTO_CONFIRMAR',
    organizacion_autorizo_cambio: true,
    profesional_confirmo_bloque: true,
  }
  assert.equal(puedeConfirmarAdministracion(caso), true)
  assert.equal(puedeConfirmarAdministracion({ ...caso, organizacion_autorizo_cambio: false }), false)
  assert.equal(puedeConfirmarAdministracion({ ...caso, profesional_confirmo_bloque: false }), false)
  assert.equal(puedeConfirmarAdministracion({ ...caso, estado: 'CONFIRMADO' }), false)
})
