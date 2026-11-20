/**
 * Decide si el aviso previo al pago tiene datos suficientes para mostrarse.
 * @param {Object} opciones Estado del seguimiento y de la política consultada.
 * @param {string} opciones.referencia Referencia privada de la contratación.
 * @param {boolean} opciones.habilitarFormulario Habilitación visual del formulario.
 * @param {boolean} opciones.cargando Indica si la consulta continúa pendiente.
 * @param {Object|null} opciones.politica Política y aceptación recibidas del servidor.
 * @returns {boolean} Visibilidad; no valida autorización ni registra aceptación.
 */
export function mostrarAvisoPolitica({ referencia, habilitarFormulario, cargando, politica }) {
  return Boolean(
    referencia && habilitarFormulario && !cargando &&
    politica && !politica.aceptada && !politica.contrato_previo &&
    typeof politica.version === 'string' && politica.version.length > 0 &&
    typeof politica.texto === 'string' && politica.texto.trim().length > 0,
  )
}

/**
 * Combina referencia y versión para distinguir avisos de contrataciones diferentes.
 * @param {string} referencia Referencia privada de seguimiento.
 * @param {string} version Versión de la política mostrada.
 * @returns {string} Clave de presentación separada por dos puntos, sin codificar.
 */
export function claveAvisoPolitica(referencia, version) {
  return `${referencia}:${version}`
}

/**
 * Mantiene el bloque visible mientras no haya aceptación explícita del servidor.
 * @param {Object} opciones Estado visual del formulario.
 * @param {boolean} opciones.habilitarFormulario Habilitación del formulario de pago.
 * @param {boolean} opciones.cargando Estado de la consulta de política.
 * @param {Object|null} opciones.politica Política consultada, que puede faltar.
 * @returns {boolean} True si está habilitado, no carga y aceptada no es exactamente true.
 */
export function mostrarBloquePolitica({ habilitarFormulario, cargando, politica }) {
  return Boolean(habilitarFormulario && !cargando && politica?.aceptada !== true)
}
