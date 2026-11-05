import { useCallback, useState } from 'react'
import useCargaAsincrona from './useCargaAsincrona.js'

const api = '/api/pagos/administracion/'

function errorTexto(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail
  return `Operación no completada (HTTP ${codigo}).`
}

async function peticion(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, {
    credentials: 'same-origin', cache: 'no-store',
    headers: { Accept: 'application/json', ...opciones.headers },
    ...opciones,
  })
  const datos = await respuesta.json().catch(() => ({}))
  if (!respuesta.ok) throw new Error(errorTexto(datos, respuesta.status))
  return datos
}

async function obtenerCsrf() {
  const datos = await peticion('/api/acceso/csrf/')
  if (!datos.csrfToken) throw new Error('No se obtuvo CSRF.')
  return datos.csrfToken
}

const campos = { width: '100%', padding: 10, borderRadius: 8,
  border: '1px solid #abc7b9', boxSizing: 'border-box', font: 'inherit' }

export default function GestionReversasPagoE3({ pago, alActualizar }) {
  return <GestionReversasPago key={pago?.id_pago} pago={pago} alActualizar={alActualizar} />
}

function GestionReversasPago({ pago, alActualizar }) {
  const idPago = pago?.id_pago
  const [reversas, setReversas] = useState([])
  const [cargando, setCargando] = useState(Boolean(idPago))
  const [procesando, setProcesando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [motivo, setMotivo] = useState('')
  const [fundamento, setFundamento] = useState('')
  const [confirma, setConfirma] = useState(false)

  const consultar = useCallback(async (signal) => {
    if (!idPago) return { reversas: [] }
    return peticion(`${api}${idPago}/reversas/`, { signal })
  }, [idPago])
  const aplicarConsulta = useCallback((datos) => {
      setReversas(Array.isArray(datos.reversas) ? datos.reversas : [])
      setError('')
      setCargando(false)
  }, [])
  const fallarConsulta = useCallback((e) => { setError(e.message); setCargando(false) }, [])
  const recargar = useCargaAsincrona(consultar, aplicarConsulta, fallarConsulta)
  async function cargar() { setCargando(true); setError(''); await recargar() }

  async function solicitar() {
    if (procesando || motivo.trim().length < 20) {
      setError('Describe el motivo de la reversa (mínimo 20 caracteres).')
      return
    }
    if (!window.confirm('¿Registrar una SOLICITUD? No se devolverá dinero.')) return
    setProcesando(true); setError(''); setAviso('')
    try {
      const csrf = await obtenerCsrf()
      const datos = await peticion(`${api}${idPago}/reversas/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ motivo: motivo.trim() }),
      })
      setAviso(datos.mensaje || 'Solicitud registrada.')
      setMotivo(''); await cargar(); alActualizar?.()
    } catch (e) { setError(e.message) }
    finally { setProcesando(false) }
  }

  async function resolver(reversa, accion) {
    if (procesando || fundamento.trim().length < 20) {
      setError('Explica la decisión administrativa (mínimo 20 caracteres).')
      return
    }
    if (accion === 'REGISTRAR_DEVOLUCION_SIMULADA' && !confirma) {
      setError('Debes confirmar que no se transferirá dinero real.')
      return
    }
    const confirmar = accion === 'RECHAZAR_SOLICITUD'
      ? '¿Rechazar esta solicitud de reversa con el fundamento escrito?'
      : '¿Registrar una SIMULACIÓN de devolución total? NO mueve dinero ni confirma un reembolso bancario.'
    if (!window.confirm(confirmar)) return
    setProcesando(true); setError(''); setAviso('')
    try {
      const csrf = await obtenerCsrf()
      const datos = await peticion(`${api}${idPago}/reversas/${reversa.id_reversa}/resolver/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ accion, fundamento: fundamento.trim(),
          confirma_sin_dinero_real: accion === 'REGISTRAR_DEVOLUCION_SIMULADA' && confirma }),
      })
      setAviso(datos.mensaje || 'Resolución registrada.')
      setFundamento(''); setConfirma(false)
      await cargar(); alActualizar?.()
    } catch (e) { setError(e.message) }
    finally { setProcesando(false) }
  }

  const pendiente = reversas.find((r) => r.estado_reversa === 'SOLICITADA')
  const montoPendiente = pendiente?.monto_reversa ?? pago?.monto_total
  const simulacionTotalPosible = pendiente != null &&
    Number(montoPendiente) === Number(pago?.monto_total) &&
    Number(pago?.monto_total) > 0
  const pagable = pago?.estado_pago === 'RETENIDO' &&
    pago?.estado_verificacion === 'VERIFICADO' &&
    pago?.metodo_pago === 'TRANSFERENCIA'

  return (
    <section aria-label="Resolución de reversas E3" style={{ padding: 18, border: '1px solid #c6dcd1', borderRadius: 12, margin: '22px 0', background: '#f7faf8' }}>
      <h4 style={{ marginTop: 0 }}>Reclamos económicos y reversas</h4>
      <p style={{ fontSize: 14 }}><strong>Modo académico:</strong> una reversa SOLICITADA no devuelve fondos. La opción de simulación deja constancia sin movimientos bancarios.</p>
      <button type="button" className="adm-secundario" disabled={cargando || procesando} onClick={() => void cargar()}>
        {cargando ? 'Consultando…' : 'Actualizar reversas'}
      </button>
      {error && <p role="alert" style={{ color: '#a12323' }}>{error}</p>}
      {aviso && <p role="status">{aviso}</p>}
      {!cargando && reversas.length === 0 && <p>No hay solicitudes de reversa registradas.</p>}
      {reversas.map((r) => (
        <div key={r.id_reversa} style={{ marginTop: 14, borderTop: '1px solid #d2e3da', paddingTop: 12 }}>
          <strong>Reversa #{r.id_reversa} — {r.estado_reversa}</strong>
          <p style={{ overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }}>{r.motivo || 'Sin detalle'}</p>
          <small>Monto: {r.monto_reversa || pago?.monto_total} {pago?.moneda || 'CLP'} · Referencia: {r.referencia_externa || 'No registrada'}</small>
        </div>
      ))}
      {pagable && !pendiente && reversas.every((r) => r.estado_reversa !== 'SIMULADA') && (
        <div style={{ display: 'grid', gap: 9, marginTop: 18 }}>
          <label htmlFor="reversa-motivo">Motivo de la solicitud de reversa</label>
          <textarea id="reversa-motivo" rows={3} maxLength={1000} style={campos}
            value={motivo} onChange={(e) => setMotivo(e.target.value)} disabled={procesando} />
          <button type="button" className="adm-secundario" onClick={() => void solicitar()} disabled={procesando || motivo.trim().length < 20}>
            Registrar solicitud de reversa
          </button>
          <small>SKILLY solo admite solicitudes autorizadas por una cancelación o resolución de reclamo.</small>
        </div>
      )}
      {pendiente && pagable && (
        <div style={{ display: 'grid', gap: 10, marginTop: 18 }}>
          <h5 style={{ margin: 0 }}>Resolver solicitud #{pendiente.id_reversa}</h5>
          <label htmlFor="reversa-fundamento">Fundamento administrativo</label>
          <textarea id="reversa-fundamento" rows={3} maxLength={1000} style={campos}
            value={fundamento} onChange={(e) => setFundamento(e.target.value)} disabled={procesando} />
          <label style={{ display: 'flex', gap: 9, alignItems: 'start' }}>
            <input type="checkbox" checked={confirma} disabled={procesando} onChange={(e) => setConfirma(e.target.checked)} />
            <span>Entiendo que la simulación académica NO efectúa ninguna devolución de dinero.</span>
          </label>
          {!simulacionTotalPosible && <p role="note">La devolución parcial no se simula aquí porque requiere conciliar el saldo restante. Puedes rechazar con fundamento; no se moverán fondos.</p>}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button type="button" className="adm-secundario" disabled={procesando || fundamento.trim().length < 20}
              onClick={() => void resolver(pendiente, 'RECHAZAR_SOLICITUD')}>Rechazar con fundamento</button>
            <button type="button" className="adm-accion" disabled={procesando || fundamento.trim().length < 20 || !confirma || !simulacionTotalPosible}
              onClick={() => void resolver(pendiente, 'REGISTRAR_DEVOLUCION_SIMULADA')}>Simular devolución total (sin dinero)</button>
          </div>
        </div>
      )}
    </section>
  )
}
