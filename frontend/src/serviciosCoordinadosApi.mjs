// Conserva la prioridad de los formatos que admite el endpoint existente.
export function serviciosCoordinadosDeRespuesta(datos) {
  const formatos = [
    datos.servicios_coordinados,
    datos,
    datos.prestaciones,
    datos.servicios,
    datos.resultados,
  ]
  return formatos.find(formato => Array.isArray(formato)) ?? null
}
