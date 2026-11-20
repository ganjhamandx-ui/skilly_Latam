const ERROR_TARGET = 'Define SKILLY_API_PROXY_TARGET con un origen HTTP loopback y puerto explícito distinto de 8000.'

/**
 * Valida el origen HTTP local antes de usarlo como destino del proxy de desarrollo.
 * Admite localhost, ::1 o IPv4 decimal completo de 127/8, puerto explícito 1..65535
 * distinto de 8000 y barra final opcional. Rechaza credenciales, rutas y URL ambiguas.
 * @param {string} value Origen, sin espacios exteriores y de hasta 200 caracteres.
 * @returns {string} Origen normalizado sin barra final.
 * @throws {Error} Si la configuración es inválida; el mensaje no incluye el valor recibido.
 */
export function validarDestinoApiLocal(value) {
  if (typeof value !== 'string' || value.length > 200 || value.trim() !== value) {
    throw new Error(ERROR_TARGET)
  }

  // Validar también la forma escrita: URL normaliza IPv4 abreviado, octal y
  // otros formatos que no deben ampliar el conjunto de destinos admitidos.
  const authority = /^http:\/\/(\[[^\]]+\]|[^/:?#@\s]+):([1-9][0-9]{0,4})\/?$/i.exec(value)
  if (!authority) throw new Error(ERROR_TARGET)

  const host = authority[1].toLowerCase()
  const octets = host.split('.')
  const ipv4Loopback = octets.length === 4 && octets[0] === '127'
    && octets.every(octet => /^(0|[1-9][0-9]{0,2})$/.test(octet) && Number(octet) <= 255)
  const port = Number(authority[2])
  if (!(host === 'localhost' || host === '[::1]' || ipv4Loopback)
      || port > 65535 || port === 8000) throw new Error(ERROR_TARGET)

  try {
    const target = new URL(value)
    if (target.protocol !== 'http:' || target.hostname !== host || target.username
        || target.password || target.pathname !== '/' || target.search || target.hash) {
      throw new Error(ERROR_TARGET)
    }
    return `http://${host}:${port}`
  } catch {
    // El mensaje nunca incluye el destino recibido: podría contener credenciales.
    throw new Error(ERROR_TARGET)
  }
}

/**
 * Configura el servidor local y proxy de API únicamente para el comando serve.
 * @param {string} command Comando recibido desde la configuración de Vite.
 * @param {Object} [environment={}] Variables del proceso.
 * @param {string} [environment.SKILLY_API_PROXY_TARGET] Origen local requerido al servir.
 * @returns {Object|undefined} Configuración fija de listener y proxy; undefined para compilar.
 * @throws {Error} Si el destino de API no supera la validación durante serve.
 */
export function configurarServidorLocal(command, environment = {}) {
  if (command !== 'serve') return undefined

  return {
    host: '127.0.0.2',
    port: 57744,
    strictPort: true,
    proxy: {
      '/api': {
        target: validarDestinoApiLocal(environment.SKILLY_API_PROXY_TARGET),
        changeOrigin: true,
      },
    },
  }
}
