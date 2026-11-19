/** Validaciones de interfaz; el servidor es la autoridad final. */
export const ACCIONES = Object.freeze({
  REAGENDAR: 'Reagendar a un bloque disponible',
  POSTERGAR: 'Postergar sin nueva fecha',
  CANCELAR: 'Cancelar definitivamente la prestación',
})

// Determina qué decisiones de agenda corresponden al estado de la prestación.
export function accionesDisponibles(estado) {
  if (estado === 'CONTRATADA') return ['REAGENDAR', 'POSTERGAR', 'CANCELAR']
  if (estado === 'POSTERGADA') return ['REAGENDAR']
  return []
}

// Filtra bloques compatibles con la acción y el expediente activo.
export function bloquesElegibles(bloques, ahora = new Date()) {
  if (!Array.isArray(bloques)) return []
  return bloques.filter((bloque) => {
    if (bloque?.estado !== 'DISPONIBLE' || bloque?.tiene_reserva_activa) return false
    if (!Number.isSafeInteger(Number(bloque.id_disponibilidad)) || Number(bloque.id_disponibilidad) < 1) return false
    if (typeof bloque.fecha !== 'string' || typeof bloque.hora_inicio !== 'string') return false
    const inicio = new Date(`${bloque.fecha}T${bloque.hora_inicio}`)
    return !Number.isNaN(inicio.getTime()) && inicio > ahora
  })
}

// Comprueba los datos de la operación de agenda antes de enviarla.
export function validarCambioAgenda({ estado, accion, motivo, bloqueId, bloques }) {
  if (!accionesDisponibles(estado).includes(accion)) {
    return 'La acción no corresponde al estado actual de la prestación.'
  }
  if (typeof motivo !== 'string' || motivo.trim().length < 20 || motivo.trim().length > 500) {
    return 'Explica el motivo en 20 a 500 caracteres para conservar trazabilidad.'
  }
  if (accion === 'REAGENDAR') {
    if (!bloquesElegibles(bloques).some((b) => String(b.id_disponibilidad) === String(bloqueId))) {
      return 'Selecciona un bloque futuro que esté disponible.'
    }
  }
  return ''
}
