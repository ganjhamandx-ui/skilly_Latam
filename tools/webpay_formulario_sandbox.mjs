// Solo reconoce metadatos de campos; no recibe ni devuelve sus valores.
import path from 'node:path'
const normalize = text => String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

export function descriptorSesionSandbox(data, { contextPath, runDir } = {}) {
  try {
    if (!data || typeof data !== 'object' || Array.isArray(data)
        || ![data.location, data.original_profile, data.context_path, contextPath, runDir].every(value => typeof value === 'string')
        || ![data.original_profile, data.context_path, contextPath, runDir].every(value => path.isAbsolute(value))) return null
    if (/[\u0000-\u001f\u007f-\u009f]/.test(data.location)) return null
    const destination = new URL(data.location)
    if (destination.origin !== 'https://webpay3gint.transbank.cl' || destination.username || destination.password) return null
    // El checkout oficial usa rutas SPA #/. Navegar esa URL conserva origen y
    // protocolo; no se evalua el fragmento. Rechazar controles, rutas ambiguas
    // y fragmentos ajenos a ese formato antes de entregarla a Page.navigate.
    if (destination.hash) {
      if (destination.hash.length > 2048 || !destination.hash.startsWith('#/')) return null
      const route = decodeURIComponent(destination.hash.slice(1))
      if (!route.startsWith('/') || route.startsWith('//') || /[\u0000-\u001f\u007f-\u009f]/.test(route)) return null
    }
    if (path.resolve(data.context_path) !== path.resolve(contextPath)) return null
    const profile = path.resolve(data.original_profile), relative = path.relative(path.resolve(runDir), profile)
    if (!relative || relative.startsWith('..') || path.isAbsolute(relative) || path.basename(profile) !== 'profile') return null
    return { location: destination.href, original_profile: profile, context_path: path.resolve(data.context_path) }
  } catch { return null }
}

// Recupera en memoria el token que React envia realmente al proveedor. No
// acepta navegaciones ajenas, respuestas no creadas o formularios ambiguos.
export function checkoutDesdeFormularioSandbox(request, { inicioLocal201 = false } = {}) {
  if (inicioLocal201 !== true || request?.method !== 'POST'
      || typeof request.postData !== 'string' || request.postData.length > 4096) return null
  try {
    const destination = new URL(request.url)
    if (destination.origin !== 'https://webpay3gint.transbank.cl'
        || destination.username || destination.password || destination.search || destination.hash
        || destination.pathname !== '/webpayserver/initTransaction') return null
    const header = Object.entries(request.headers || {}).find(([key]) => key.toLowerCase() === 'content-type')?.[1]
    if (typeof header !== 'string' || header.split(';')[0].trim().toLowerCase() !== 'application/x-www-form-urlencoded') return null
    const fields = new URLSearchParams(request.postData)
    if ([...fields.keys()].length !== 1 || fields.getAll('token_ws').length !== 1) return null
    const token = fields.get('token_ws')
    if (!/^[A-Za-z0-9_-]{5,200}$/.test(token || '')) return null
    return { token, url: destination.href, ambiente: 'TRANSBANK_INTEGRACION' }
  } catch { return null }
}

export function camposFormularioSandbox(fields) {
  const field = re => fields.find(item => re.test(normalize(item.key)))
  const card = field(/numero.*tarjeta|tarjeta.*numero|card.?number|pan\b|creditcardnumber|numero_tarjeta|nrotarjeta/)
  const cvv = field(/cvv|cvc|codigo.*seguridad|security.?code/)
  const month = field(/\bmes\b|month/), year = field(/\bano\b|year/)
  const expiry = field(/vencim|expir|expiry/)
  const rut = field(/\brut\b|rut_?cliente|usuario|identificaci/)
  const password = fields.find(item => item.type === 'password' && item !== cvv)
  return { card, cvv, month, year, expiry, rut, password,
    cardDetailsComplete: !!cvv && (!!expiry || (!!month && !!year)),
    cardDetailsPresent: !!(cvv || month || year || expiry),
  }
}

// Resultado cerrado de booleanos: nunca devuelve texto, URL ni fragmentos de
// una pagina del proveedor. Tambien se ejecuta dentro del navegador.
export function indicadoresPaginaSandbox(value) {
  const text = typeof value === 'string' ? value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() : ''
  return {
    transaction_expired: /(?:transaccion|sesion|token).{0,60}(?:expir|vencid)|(?:expired|expirad).{0,60}(?:transaction|session|transaccion|sesion)/.test(text),
    transaction_invalid: /transaccion.{0,60}(?:invalida|no existe)|invalid.{0,40}(?:transaction|token)|token.{0,40}(?:invalido|no existe)/.test(text),
    service_unavailable: /servicio.{0,40}(?:no disponible|temporalmente)|service unavailable|error de conexion|no es posible.{0,40}(?:conectar|procesar)/.test(text),
    payment_rejected: /(?:transaccion|pago).{0,40}rechaz|(?:payment|transaction).{0,40}declined/.test(text),
    generic_error: /ocurrio.{0,30}error|ha ocurrido un problema|error inesperado|unexpected error/.test(text),
    human_challenge: /captcha|verifica.{0,30}(?:humano|robot)|verify.{0,30}human/.test(text),
  }
}
