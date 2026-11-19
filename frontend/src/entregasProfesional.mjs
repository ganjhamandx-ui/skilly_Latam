// Normaliza entregas profesionales y aplica en interfaz los límites que revalida el backend.
export function excedeLimitesDeArchivosEntrega(archivos) {
  return archivos.length > 3 ||
    archivos.some(archivo => archivo.size > 10 * 1024 * 1024) ||
    archivos.reduce((total, archivo) => total + archivo.size, 0) > 25 * 1024 * 1024
}

// La lista directa tiene prioridad sobre los formatos de objeto existentes.
export function entregasDeRespuesta(datos) {
  if (Array.isArray(datos)) return datos
  if (Array.isArray(datos.entregas)) return datos.entregas
  return Array.isArray(datos.resultados) ? datos.resultados : null
}
