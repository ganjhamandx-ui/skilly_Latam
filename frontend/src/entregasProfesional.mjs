/**
 * Comprueba límites de adjuntos antes del envío; no valida tipos ni contenido.
 * @param {File[]} archivos Arreglo de archivos seleccionados, no un FileList sin convertir.
 * @returns {boolean} Si supera tres archivos, 10 MiB por archivo o 25 MiB en conjunto.
 * Los valores exactamente iguales al límite se admiten.
 */
export function excedeLimitesDeArchivosEntrega(archivos) {
  return archivos.length > 3 ||
    archivos.some(archivo => archivo.size > 10 * 1024 * 1024) ||
    archivos.reduce((total, archivo) => total + archivo.size, 0) > 25 * 1024 * 1024
}

/**
 * Extrae entregas conservando prioridad de lista directa, entregas y resultados.
 * @param {Object|Array} datos Respuesta no nula de la API.
 * @returns {Array|null} Arreglo original, incluso vacío, o null si no hay formato conocido.
 */
export function entregasDeRespuesta(datos) {
  if (Array.isArray(datos)) return datos
  if (Array.isArray(datos.entregas)) return datos.entregas
  return Array.isArray(datos.resultados) ? datos.resultados : null
}
