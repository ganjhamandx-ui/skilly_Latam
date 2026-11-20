/** Validaciones de interfaz; el servidor es la autoridad final. */
export const ACCIONES = Object.freeze({
  REAGENDAR: 'Reagendar a un bloque disponible',
  POSTERGAR: 'Postergar sin nueva fecha',
  CANCELAR: 'Cancelar definitivamente la prestación',
})

/**
 * Selecciona acciones de interfaz según el estado, sin comprobar permisos del usuario.
 * @param {string} estado Estado persistido de la prestación.
 * @returns {string[]} Tres acciones para CONTRATADA, solo REAGENDAR para POSTERGADA, o lista vacía.
 */
export function accionesDisponibles(estado) {
  if (estado === 'CONTRATADA') return ['REAGENDAR', 'POSTERGAR', 'CANCELAR']
  if (estado === 'POSTERGADA') return ['REAGENDAR']
  return []
}

/**
 * Filtra bloques disponibles, sin reserva activa, con id válido e inicio futuro.
 * Interpreta fecha y hora en la zona del navegador; el servidor revalida su propia zona
 * y la pertenencia del bloque. No comprueba aquí profesional, hora de término ni expediente.
 * @param {*} bloques Lista recibida de la API; otras entradas producen una lista vacía.
 * @param {Date} [ahora=new Date()] Instante de referencia para comparar el inicio.
 * @returns {Object[]} Bloques elegibles conservando su orden y sus objetos originales.
 */
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

/**
 * Valida acción, motivo y selección horaria antes de enviar el formulario.
 * @param {Object} datos Estado del formulario.
 * @param {string} datos.estado Estado actual de la prestación.
 * @param {string} datos.accion Acción elegida.
 * @param {string} datos.motivo Explicación de 20 a 500 caracteres tras recortar espacios.
 * @param {number|string} [datos.bloqueId] Bloque requerido solo para REAGENDAR.
 * @param {Object[]} [datos.bloques] Bloques usados para revalidar la selección futura.
 * @returns {string} Primer mensaje de error, o cadena vacía si el formulario es admisible.
 */
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
