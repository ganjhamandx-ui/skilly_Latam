// Predicados puros que habilitan acciones según actor, iniciador y estado del expediente.
const ESTADOS_ABIERTOS = new Set([
  'PENDIENTE_ADMIN',
  'PENDIENTE_PROFESIONAL',
  'ESPERANDO_NUEVO_BLOQUE',
  'PENDIENTE_ORGANIZACION',
  'ESPERANDO_SELECCION',
  'LISTO_CONFIRMAR',
])

/**
 * Reconoce estados pendientes del flujo bilateral; no evalúa permisos ni plazos.
 * @param {string} estado Estado devuelto por la API.
 * @returns {boolean} Si pertenece al conjunto de estados abiertos.
 */
export function estaAbierto(estado) {
  return ESTADOS_ABIERTOS.has(estado)
}

/**
 * Proyecta la selección de bloques al contrato de la API sin modificar la entrada.
 * Conserva los identificadores existentes y omite propuestas nuevas sin fecha u horas.
 * La validez cronológica y disponibilidad deben verificarse en el servidor.
 * @param {Object|null|undefined} valor Selección del formulario.
 * @param {Array<number|string>} [valor.existentes] Identificadores de bloques publicados.
 * @param {Array<Object>} [valor.nuevas] Propuestas con fecha, hora_inicio y hora_fin.
 * @returns {{alternativas_existentes: Array, alternativas_nuevas: Array}} Cuerpo de alternativas.
 */
export function payloadAlternativas(valor) {
  return {
    alternativas_existentes: valor?.existentes || [],
    alternativas_nuevas: (valor?.nuevas || []).filter(
      (item) => item.fecha && item.hora_inicio && item.hora_fin,
    ),
  }
}

/**
 * Comprueba si el cuerpo normalizado contiene al menos una alternativa.
 * @param {Object|null|undefined} valor Selección aceptada por payloadAlternativas.
 * @returns {boolean} Si quedan bloques existentes o propuestas con sus tres campos.
 */
export function tieneAlternativas(valor) {
  const payload = payloadAlternativas(valor)
  return payload.alternativas_existentes.length + payload.alternativas_nuevas.length > 0
}

/**
 * Habilita selección empresarial pendiente mientras no se marque el plazo vencido.
 * @param {Object|null|undefined} caso Expediente con estado y plazo_vencido.
 * @returns {boolean} Si espera respuesta de organización o selección; no verifica bloques disponibles.
 */
export function puedeSeleccionarOrganizacion(caso) {
  return Boolean(
    caso
    && ['PENDIENTE_ORGANIZACION', 'ESPERANDO_SELECCION'].includes(caso.estado)
    && !caso.plazo_vencido,
  )
}

/**
 * Habilita respuesta profesional a una propuesta iniciada por la organización.
 * @param {Object|null|undefined} caso Expediente con estado, iniciador y plazo_vencido.
 * @returns {boolean} Si está pendiente del profesional y no tiene el plazo vencido.
 */
export function puedeResponderPropuesta(caso) {
  return Boolean(
    caso
    && caso.estado === 'PENDIENTE_PROFESIONAL'
    && caso.iniciador === 'ORGANIZACION'
    && !caso.plazo_vencido,
  )
}

/**
 * Permite una contrapropuesta cuando procede responder y aún no se ha utilizado.
 * @param {Object|null|undefined} caso Expediente con contrapropuesta_profesional_usada.
 * @returns {boolean} Disponibilidad del control de contrapropuesta en la interfaz.
 */
export function puedeContraproponer(caso) {
  return puedeResponderPropuesta(caso) && !caso.contrapropuesta_profesional_usada
}

/**
 * Habilita nuevos bloques durante la espera de disponibilidad no vencida.
 * @param {Object|null|undefined} caso Expediente con estado y plazo_vencido.
 * @returns {boolean} Si está en ESPERANDO_NUEVO_BLOQUE y conserva plazo.
 */
export function puedeEntregarDisponibilidad(caso) {
  return Boolean(caso && caso.estado === 'ESPERANDO_NUEVO_BLOQUE' && !caso.plazo_vencido)
}

/**
 * Habilita la confirmación administrativa cuando ambas partes autorizaron el cambio.
 * @param {Object|null|undefined} caso Expediente con estado, autorizaciones y plazo_vencido.
 * @returns {boolean} Si está LISTO_CONFIRMAR, ambas marcas son verdaderas y conserva plazo.
 */
export function puedeConfirmarAdministracion(caso) {
  return Boolean(
    caso
    && caso.estado === 'LISTO_CONFIRMAR'
    && caso.organizacion_autorizo_cambio
    && caso.profesional_confirmo_bloque
    && !caso.plazo_vencido,
  )
}
