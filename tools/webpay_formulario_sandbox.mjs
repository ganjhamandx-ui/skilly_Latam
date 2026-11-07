// Solo reconoce metadatos de campos; no recibe ni devuelve sus valores.
const normalize = text => String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

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
