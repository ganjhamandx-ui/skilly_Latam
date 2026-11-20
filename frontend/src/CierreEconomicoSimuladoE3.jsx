import { useEffect, useState } from 'react'

/**
 * Formatea un importe para mostrar pesos chilenos sin decimales.
 * @param {string|number|null|undefined} n Importe decimal recibido de la API.
 * @returns {string} Texto monetario; los valores falsos se presentan como cero.
 */
const CLP = (n) => Number(n || 0).toLocaleString('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 })
const API = '/api/seguimiento/administracion/cancelaciones/'

/**
 * Previsualiza y confirma la distribución económica simulada de un expediente.
 * Nunca representa una transferencia o devolución bancaria real.
 *
 * @param {Object} props Propiedades de la sección administrativa.
 * @param {number|string} props.idExpediente Identificador usado en consultas y cierre.
 * @param {boolean} props.habilitado Permite consultar y mostrar el cierre.
 * @param {function(): void} [props.onCompletado] Notificación tras guardar el resultado;
 * su retorno no se espera.
 * @returns {import('react').ReactElement|null} Desglose y confirmación, o null si está deshabilitado.
 */
export default function CierreEconomicoSimuladoE3({ idExpediente, habilitado, onCompletado }) {
  const [cierre, setCierre] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [confirmado, setConfirmado] = useState(false)
  const [mensaje, setMensaje] = useState('')

  useEffect(() => {
    if (!idExpediente || !habilitado) return undefined
    // Cancela la consulta al desmontar o cambiar de expediente para evitar estado obsoleto.
    const control = new AbortController()
    setCargando(true)
    setError('')
    fetch(`${API}${idExpediente}/cierre-simulado/`, {
      credentials: 'same-origin', cache: 'no-store', signal: control.signal,
    })
      .then(async (r) => {
        const datos = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(datos.mensaje || `HTTP ${r.status}`)
        return datos
      })
      .then((datos) => { if (!control.signal.aborted) setCierre(datos.cierre) })
      .catch((e) => { if (!control.signal.aborted) setError(e.message || 'No fue posible consultar el cierre.') })
      .finally(() => { if (!control.signal.aborted) setCargando(false) })
    return () => control.abort()
  }, [idExpediente, habilitado])

  if (!habilitado) return null
  // El estado persistido impide mostrar de nuevo el botón después de registrar el cierre.
  const terminado = cierre?.estado === 'DISTRIBUIDO_SIMULADO'

  /**
   * Confirma la simulación con CSRF y actualiza el desglose devuelto por Django.
   * Omite envíos en curso, cierres terminados y confirmaciones no aceptadas.
   * Los fallos se muestran en el estado de error y siempre se libera el indicador de envío.
   * @returns {Promise<void>} Finalización del intento; los errores capturados no se propagan.
   */
  async function finalizar() {
    if (enviando || terminado || !confirmado) return
    if (!window.confirm('¿Confirmar el cierre económico y la distribución para las tres partes?')) return
    setEnviando(true)
    setError('')
    setMensaje('')
    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', { credentials: 'same-origin', cache: 'no-store' })
      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))
      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) throw new Error('No se pudo validar la sesión.')
      const respuesta = await fetch(`${API}${idExpediente}/cierre-simulado/`, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfDatos.csrfToken },
        // Ambas confirmaciones son obligatorias: la operación no solicita transferencias reales.
        body: JSON.stringify({ confirmar_simulacion: true, confirmar_sin_dinero_real: true }),
      })
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(datos.mensaje || `HTTP ${respuesta.status}`)
      setCierre(datos.cierre)
      setMensaje('Cierre económico registrado correctamente.')
      onCompletado?.()
    } catch (e) {
      setError(e.message || 'No se pudo completar la simulación.')
    } finally { setEnviando(false) }
  }

  return (
    <div>
      <h4>Distribución final del dinero</h4>
      <p>Revisa los montos de cada parte antes de confirmar el cierre.</p>
      {cargando && <p>Consultando distribución…</p>}
      {error && <p role="alert" className="adm-error">{error}</p>}
      {mensaje && <p role="status" className="adm-nota">{mensaje}</p>}
      {cierre && <>
        <div className="adm-nota" style={{ padding: 14 }}>
          <p><strong>Devolución a la organización:</strong> {CLP(cierre.organizacion)}</p>
          <p><strong>Neto para el profesional:</strong> {CLP(cierre.profesional_neto)}</p>
          <p><strong>Comisión SKILLY por el trabajo:</strong> {CLP(cierre.skilly_comision_trabajo)}</p>
          <p><strong>Cargo SKILLY por cancelación:</strong> {CLP(cierre.skilly_cargo_cancelacion)}</p>
          <p><strong>Total de SKILLY:</strong> {CLP(cierre.skilly_total)}</p>
          <p><strong>Total conciliado:</strong> {CLP(cierre.total)}</p>
        </div>
        {terminado ? <p role="status"><strong>Distribución registrada correctamente.</strong> El caso quedó cerrado en el prototipo.</p> : <>
          <label style={{ display: 'flex', alignItems: 'start', gap: 8, marginBottom: 10 }}>
            <input type="checkbox" checked={confirmado} disabled={enviando} onChange={(e) => setConfirmado(e.target.checked)} />
            Confirmo la distribución económica indicada para la organización, el profesional y SKILLY.
          </label>
          <button className="adm-accion" type="button" disabled={!confirmado || enviando}
            onClick={finalizar}>{enviando ? 'Registrando distribución…' : 'Finalizar distribución'}</button>
        </>}
      </>}
    </div>
  )
}
