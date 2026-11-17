function mensajeDeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail
  return `Error HTTP ${codigo}`
}

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
