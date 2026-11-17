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
