/**
 * Extrae la primera colección reconocida conservando la compatibilidad de respuestas.
 * Prioriza servicios_coordinados, el cuerpo si es arreglo, prestaciones, servicios
 * y resultados, en ese orden. Un arreglo vacío también es un resultado válido.
 * @param {Object|Array} datos Cuerpo JSON no nulo recibido de la API.
 * @returns {Array|null} Colección original sin copiar, o null si no hay un formato admitido.
 */
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
