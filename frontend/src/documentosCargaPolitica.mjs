/**
 * Selecciona la acción de carga según la política documental recibida del servidor.
 * Prioriza corregir un documento RECHAZADA incluido en ids_rechazados; permite
 * agregar uno nuevo solo en la primera fila del tipo cuando nuevos_permitidos es verdadero.
 * @param {Object|null|undefined} documento Documento con id_documento y estado_revision.
 * @param {Object|null|undefined} politica Permisos actuales de corrección y altas.
 * @param {number} indiceEnTipo Posición de la fila dentro de su tipo documental.
 * @returns {{modo: string, etiqueta: string}|null} Acción disponible o null para ocultar el control.
 */
export function accionCargaDocumento(documento, politica, indiceEnTipo) {
  const corregible = Boolean(
    documento?.estado_revision === 'RECHAZADA'
    && politica?.ids_rechazados?.includes(documento.id_documento),
  )
  if (corregible) {
    return {
      modo: 'CORREGIR_RECHAZADO',
      etiqueta: 'Corregir documento rechazado',
    }
  }
  if (politica?.nuevos_permitidos && indiceEnTipo === 0) {
    return {
      modo: 'NUEVO_DOCUMENTO',
      etiqueta: 'Adjuntar nuevo documento',
    }
  }
  return null
}
