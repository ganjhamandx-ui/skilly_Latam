// Sólo presentación. No se cambia el contrato de API de Fase 6B.
export function mostrarAvisoPolitica({ referencia, habilitarFormulario, cargando, politica }) {
  return Boolean(
    referencia && habilitarFormulario && !cargando &&
    politica && !politica.aceptada && !politica.contrato_previo &&
    typeof politica.version === 'string' && politica.version.length > 0 &&
    typeof politica.texto === 'string' && politica.texto.trim().length > 0,
  )
}

export function claveAvisoPolitica(referencia, version) {
  return `${referencia}:${version}`
}

// Tras aceptar se elimina por completo el aviso del seguimiento.
export function mostrarBloquePolitica({ habilitarFormulario, cargando, politica }) {
  return Boolean(habilitarFormulario && !cargando && politica?.aceptada !== true)
}
