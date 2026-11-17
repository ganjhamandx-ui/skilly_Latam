const ESTADOS_ABIERTOS = new Set([
  'PENDIENTE_ADMIN',
  'PENDIENTE_PROFESIONAL',
  'ESPERANDO_NUEVO_BLOQUE',
  'PENDIENTE_ORGANIZACION',
  'ESPERANDO_SELECCION',
  'LISTO_CONFIRMAR',
])

export function estaAbierto(estado) {
  return ESTADOS_ABIERTOS.has(estado)
}

export function payloadAlternativas(valor) {
  return {
    alternativas_existentes: valor?.existentes || [],
    alternativas_nuevas: (valor?.nuevas || []).filter(
      (item) => item.fecha && item.hora_inicio && item.hora_fin,
    ),
  }
}

export function tieneAlternativas(valor) {
  const payload = payloadAlternativas(valor)
  return payload.alternativas_existentes.length + payload.alternativas_nuevas.length > 0
}

export function puedeSeleccionarOrganizacion(caso) {
  return Boolean(
    caso
    && ['PENDIENTE_ORGANIZACION', 'ESPERANDO_SELECCION'].includes(caso.estado)
    && !caso.plazo_vencido,
  )
}

export function puedeResponderPropuesta(caso) {
  return Boolean(
    caso
    && caso.estado === 'PENDIENTE_PROFESIONAL'
    && caso.iniciador === 'ORGANIZACION'
    && !caso.plazo_vencido,
  )
}

export function puedeContraproponer(caso) {
  return puedeResponderPropuesta(caso) && !caso.contrapropuesta_profesional_usada
}

export function puedeEntregarDisponibilidad(caso) {
  return Boolean(caso && caso.estado === 'ESPERANDO_NUEVO_BLOQUE' && !caso.plazo_vencido)
}

export function puedeConfirmarAdministracion(caso) {
  return Boolean(
    caso
    && caso.estado === 'LISTO_CONFIRMAR'
    && caso.organizacion_autorizo_cambio
    && caso.profesional_confirmo_bloque
    && !caso.plazo_vencido,
  )
}
