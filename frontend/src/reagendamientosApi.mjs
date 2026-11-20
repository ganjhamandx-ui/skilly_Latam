// Transporte autenticado del reagendamiento; conserva cookies, CSRF y cuerpos multipart.
/**
 * Selecciona el mensaje textual de la API, priorizando mensaje sobre detail.
 * @param {Object|null|undefined} datos Cuerpo JSON de error, si pudo leerse.
 * @param {number} codigo Estado HTTP para el mensaje de respaldo.
 * @returns {string} Texto apto para mostrar al usuario.
 */
function mensajeDeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail
  return `Error HTTP ${codigo}`
}

/**
 * Solicita reagendamientos y valida la estructura de los listados recibidos.
 * Para métodos distintos de GET obtiene antes un token CSRF. Conserva FormData
 * sin fijar Content-Type y usa JSON para otros cuerpos, que debe serializar el llamador.
 * Las opciones y cabeceras explícitas del llamador prevalecen sobre los valores predeterminados.
 *
 * @param {string} url Ruta de la API, normalmente bajo el proxy del mismo origen.
 * @param {RequestInit} [opciones={}] Método en mayúsculas, cuerpo, señal y cabeceras.
 * @returns {Promise<Object>} JSON recibido; un cuerpo no legible se sustituye por un objeto vacío.
 * @throws {Error} Si falla la red, no se obtiene CSRF válido o la API devuelve un estado no exitoso.
 * @throws {TypeError} Si una lectura no contiene solicitudes con id y estado textual.
 */
export async function solicitudReagendamiento(url, opciones = {}) {
  const escritura = opciones.method && opciones.method !== 'GET'
  const esFormulario = typeof FormData !== 'undefined' && opciones.body instanceof FormData
  let token = null
  if (escritura) {
    const respuesta = await fetch('/api/acceso/csrf/', {
      credentials: 'same-origin', cache: 'no-store',
    })
    const datos = await respuesta.json().catch(() => ({}))
    if (!respuesta.ok || typeof datos?.csrfToken !== 'string' || !datos.csrfToken) {
      throw new Error('No se pudo obtener el token CSRF.')
    }
    token = datos.csrfToken
  }
  const respuesta = await fetch(url, {
    credentials: 'same-origin', cache: 'no-store', ...opciones,
    headers: {
      Accept: 'application/json',
      ...(opciones.body && !esFormulario ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { 'X-CSRFToken': token } : {}),
      ...(opciones.headers || {}),
    },
  })
  const datos = await respuesta.json().catch(() => ({}))
  if (!respuesta.ok) throw new Error(mensajeDeError(datos, respuesta.status))
  if (!escritura && (!Array.isArray(datos?.solicitudes) || !datos.solicitudes.every(
    (item) => item && typeof item === 'object' && item.id != null && typeof item.estado === 'string',
  ))) {
    throw new TypeError('El listado de reagendamientos tiene un formato inesperado. Vuelve a consultar.')
  }
  return datos
}
