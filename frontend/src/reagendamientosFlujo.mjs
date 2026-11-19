// Predicados puros que habilitan acciones según actor, iniciador y estado del expediente.
const ESTADOS_ABIERTOS = new Set([
  'PENDIENTE_ADMIN',
  'PENDIENTE_PROFESIONAL',
  'ESPERANDO_NUEVO_BLOQUE',
  'PENDIENTE_ORGANIZACION',
  'ESPERANDO_SELECCION',
  'LISTO_CONFIRMAR',
])

// Reconoce estados del expediente que todavía permiten acciones bilaterales.
export function estaAbierto(estado) {
  return ESTADOS_ABIERTOS.has(estado)
}

// Proyecta los bloques publicados y nuevos al contrato JSON de la API.
export function payloadAlternativas(valor) {
  return {
    alternativas_existentes: valor?.existentes || [],
    alternativas_nuevas: (valor?.nuevas || []).filter(
      (item) => item.fecha && item.hora_inicio && item.hora_fin,
    ),
  }
}

// Comprueba que exista al menos un bloque seleccionado o propuesto.
export function tieneAlternativas(valor) {
  const payload = payloadAlternativas(valor)
  return payload.alternativas_existentes.length + payload.alternativas_nuevas.length > 0
}

// Restringe la selección empresarial a los estados y alternativas que la habilitan.
export function puedeSeleccionarOrganizacion(caso) {
  return Boolean(
    caso
    && ['PENDIENTE_ORGANIZACION', 'ESPERANDO_SELECCION'].includes(caso.estado)
    && !caso.plazo_vencido,
  )
}

// Restringe la respuesta profesional a un expediente con una propuesta pendiente.
export function puedeResponderPropuesta(caso) {
  return Boolean(
    caso
    && caso.estado === 'PENDIENTE_PROFESIONAL'
    && caso.iniciador === 'ORGANIZACION'
    && !caso.plazo_vencido,
  )
}

// Habilita una contrapropuesta profesional únicamente si no se utilizó la anterior.
export function puedeContraproponer(caso) {
  return puedeResponderPropuesta(caso) && !caso.contrapropuesta_profesional_usada
}

// Indica cuándo el profesional debe entregar bloques adicionales.
export function puedeEntregarDisponibilidad(caso) {
  return Boolean(caso && caso.estado === 'ESPERANDO_NUEVO_BLOQUE' && !caso.plazo_vencido)
}

// Exige las autorizaciones y el estado que habilitan confirmar la agenda.
export function puedeConfirmarAdministracion(caso) {
  return Boolean(
    caso
    && caso.estado === 'LISTO_CONFIRMAR'
    && caso.organizacion_autorizo_cambio
    && caso.profesional_confirmo_bloque
    && !caso.plazo_vencido,
  )
}
