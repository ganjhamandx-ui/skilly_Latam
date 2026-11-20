import CierreEconomicoSimuladoE3 from './CierreEconomicoSimuladoE3.jsx'
// Bandeja administrativa: evaluación, liquidación y cierre simulado único; sin cobros bancarios.
import { useEffect, useState } from 'react'
import AdminNavegacion from './AdminNavegacion.jsx'
import './Administracion.css'

const API = '/api/seguimiento/administracion/cancelaciones/'
/**
 * Extrae el mensaje administrativo o combina errores de campo de la respuesta.
 * @param {Object|null} datos JSON recibido del servidor.
 * @param {number} codigo Código HTTP usado si no hay detalles.
 * @returns {string} Mensaje según el contrato textual de la API.
 */
const textoError = (datos, codigo) => datos?.mensaje || datos?.detail ||
  Object.values(datos || {}).flat().join(' | ') || `Error HTTP ${codigo}`
/**
 * Formatea un monto para presentación en CLP sin decimales visibles.
 * @param {number|string|null} valor Importe del backend; valores falsos se presentan como cero.
 * @returns {string} Texto monetario regional, sin modificar el importe persistido.
 */
const pesos = (valor) => Number(valor || 0).toLocaleString('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 })

/**
 * Coordina la consulta, evaluación y autorización de liquidaciones de cancelación.
 * Mantiene cada resultado de liquidación asociado al expediente y a la revisión consultada.
 * @returns {import('react').ReactElement} Bandeja privada con formularios y cierre simulado.
 */
export default function ExpedientesCancelacionAdministracionE3() {
  const [lista, setLista] = useState([])
  const [elegido, setElegido] = useState(null)
  const [decision, setDecision] = useState('')
  const [trabajo, setTrabajo] = useState('0')
  const [fundamento, setFundamento] = useState('')
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [revision, setRevision] = useState(0)
  const [cargoAutorizado, setCargoAutorizado] = useState('0')
  const [excepcionLegal, setExcepcionLegal] = useState(false)
  const [derechosVerificados, setDerechosVerificados] = useState(false)
  const [fundamentoLiquidacion, setFundamentoLiquidacion] = useState('')
  const [confirmacionSinDinero, setConfirmacionSinDinero] = useState(false)
  const [resultadoLiquidacion, setResultadoLiquidacion] = useState(null)

  const elegidoId = elegido?.id_expediente
  const estadoElegido = elegido?.estado
  const liquidacionVigente = resultadoLiquidacion?.id === elegidoId && resultadoLiquidacion?.revision === revision
  const liquidacion = liquidacionVigente ? resultadoLiquidacion.datos : null
  const consultandoLiq = estadoElegido === 'RESUELTO' && !liquidacionVigente

  // Recarga la bandeja cuando cambia la revisión, sin conservar respuestas de una consulta anterior.
  useEffect(() => {
    let activo = true
    fetch(API, { credentials: 'same-origin', cache: 'no-store' })
      .then(async r => { const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(textoError(d,r.status)); return d })
      .then(d => { if (activo) { setLista(d.expedientes || []); setCargando(false) } })
      .catch(e => { if (activo) { setError(e.message); setCargando(false) } })
    return () => { activo = false }
  }, [revision])

  // El cierre solo se ofrece después de una evaluación resuelta y una liquidación existente.
  useEffect(() => {
    if (!elegidoId || estadoElegido !== 'RESUELTO') return
    const controller = new AbortController()
    fetch(`${API}${elegidoId}/liquidacion/`, {credentials:'same-origin',cache:'no-store',signal:controller.signal})
      .then(async r => {const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(textoError(d,r.status));return d})
      .then(d => {if(!controller.signal.aborted) setResultadoLiquidacion({id:elegidoId,revision,datos:d.liquidacion})})
      .catch(e => {if(!controller.signal.aborted) {setError(e.message);setResultadoLiquidacion({id:elegidoId,revision,datos:null})}})
    return () => controller.abort()
  }, [elegidoId, estadoElegido, revision])


  /**
   * Autoriza la liquidación documentada tras confirmar derechos y ausencia de movimiento bancario.
   * @param {import('react').FormEvent} e Envío del formulario que se cancela.
   * @returns {Promise<void>} Guarda el resultado y fuerza su consulta posterior, o presenta el error.
   */
  async function registrarLiquidacion(e) {
    e.preventDefault()
    if (!elegido || guardando || !derechosVerificados || !confirmacionSinDinero) return
    if (!window.confirm('¿Autorizar esta liquidación? Se crea una SOLICITUD de reversa, pero no se devuelve ni se descuenta dinero.')) return
    setGuardando(true);setError('');setMensaje('')
    try {
      const t=await fetch('/api/acceso/csrf/',{credentials:'same-origin',cache:'no-store'})
      const token=await t.json().catch(()=>({}))
      if (!t.ok || !token.csrfToken) throw Error('No se obtuvo CSRF.')
      const r=await fetch(`${API}${elegido.id_expediente}/liquidacion/`,{
        method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':token.csrfToken},
        body:JSON.stringify({cargo_autorizado:cargoAutorizado, fundamento:fundamentoLiquidacion,
          excepcion_legal:excepcionLegal,derechos_verificados:derechosVerificados,confirmacion_sin_dinero:confirmacionSinDinero})
      })
      const d=await r.json().catch(()=>({}))
      if(!r.ok) throw Error(textoError(d,r.status))
      setResultadoLiquidacion({id:elegidoId,revision,datos:d.liquidacion});setMensaje(d.mensaje);setRevision(x=>x+1)
    }catch(e){setError(e.message || 'No se registró la liquidación.')}
    finally{setGuardando(false)}
  }

  /**
   * Envía la evaluación del expediente pendiente sin resolver el reclamo asociado.
   * @param {import('react').FormEvent} e Envío del formulario que se cancela.
   * @returns {Promise<void>} Actualiza el expediente con la respuesta o muestra el rechazo.
   */
  async function resolver(e) {
    e.preventDefault()
    if (!elegido || elegido.estado !== 'PENDIENTE' || guardando) return
    if (!window.confirm(`¿Registrar evaluación del expediente #${elegido.id_expediente}? No cancela ni devuelve dinero.`)) return
    setGuardando(true); setError(''); setMensaje('')
    try {
      const t = await fetch('/api/acceso/csrf/', { credentials:'same-origin', cache:'no-store' })
      const token = await t.json().catch(() => ({}))
      if (!t.ok || !token.csrfToken) throw new Error('No se obtuvo el token CSRF.')
      const r = await fetch(`${API}${elegido.id_expediente}/`, {
        method:'PATCH', credentials:'same-origin', headers: { 'Content-Type':'application/json', 'X-CSRFToken':token.csrfToken },
        body: JSON.stringify({ decision, fundamento, monto_trabajo_acreditado: trabajo }),
      })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(textoError(d,r.status))
      setMensaje(d.mensaje); setElegido(d.expediente); setRevision(x => x + 1)
    } catch(e) { setError(e.message || 'No se guardó la evaluación.') } finally { setGuardando(false) }
  }

  return <div className="adm-pagina">
    <header className="adm-header"><a className="adm-logo" href="/administracion">✦ Skilly</a><nav><a href="/administracion">Administración</a></nav></header>
    <AdminNavegacion activo="expedientes" />
    <main className="adm-contenedor">
      <div className="adm-intro"><span className="adm-eyebrow">BACK-OFFICE · CANCELACIONES</span><h1>Expedientes de cancelación</h1><p>Antecedentes privados, revisión y desglose económico. Esta pantalla no cancela prestaciones ni ejecuta reembolsos.</p></div>
      {error && <div role="alert" className="adm-error">{error}</div>}
      {mensaje && <p role="status" className="adm-nota">{mensaje}</p>}
      <div className="adm-panel">
        <h2>Solicitudes recibidas</h2>
        {cargando ? <p>Consultando expedientes…</p> : lista.length === 0 ? <p>Sin expedientes de cancelación registrados.</p> :
        <div style={{display:'grid',gap:10}}>{lista.map(x => <button type="button" key={x.id_expediente}
          className="adm-busqueda" onClick={() => {setElegido(x);setError('');setDecision('');setFundamento('');setTrabajo('0')}}
          style={{textAlign:'left',padding:16,cursor:'pointer'}}>
          <strong>#{x.id_expediente} · Prestación #{x.id_prestacion}</strong> · {x.origen} · {x.estado}<div>{x.motivo}</div>
        </button>)}</div>}
      </div>
      {elegido && <section className="adm-panel" style={{marginTop:20}}>
        <h2>Expediente #{elegido.id_expediente}</h2><p><strong>Prestación #{elegido.id_prestacion}</strong> · {elegido.origen} · {elegido.estado}</p>
        <p><strong>Motivo:</strong> {elegido.motivo}</p>
        {elegido.id_reclamo && <p className="adm-nota">Reclamo vinculado #{elegido.id_reclamo}. Después de evaluar el expediente, resuelve formalmente el reclamo desde <a href="/administracion/reclamos">Gestión de reclamos</a>; la evaluación no lo cierra por sí sola.</p>}<p style={{whiteSpace:'pre-wrap'}}>{elegido.descripcion}</p>
        {elegido.evidencia_disponible ? <a href={`${API}${elegido.id_expediente}/evidencia/`}>Descargar documento justificativo (acceso administrativo)</a>
          : <p className="adm-nota">No se adjuntó documentación. La ausencia de archivo no implica automáticamente falta de justificación.</p>}
        {elegido.estado === 'RESUELTO' ? <div className="adm-nota">
          <h3>Evaluación guardada: {elegido.decision}</h3><p>{elegido.fundamento}</p>
        </div> : <form onSubmit={resolver} style={{display:'grid',gap:12,maxWidth:700}}>
          <h3>Evaluación administrativa</h3>
          <label htmlFor="e3-dec">Clasificación de la solicitud</label>
          <select id="e3-dec" className="adm-busqueda" required value={decision} onChange={e => setDecision(e.target.value)}>
            <option value="">Selecciona clasificación</option><option value="JUSTIFICADA">Cancelación justificada</option>
            <option value="INJUSTIFICADA">Desistimiento injustificado</option><option value="INCUMPLIMIENTO_CONTRAPARTE">Incumplimiento de contraparte</option>
            <option value="RECHAZAR_SOLICITUD">Rechazar solicitud con fundamento</option>
          </select>
          <label htmlFor="e3-trabajo">Trabajo efectivamente acreditado (CLP)</label>
          <input id="e3-trabajo" className="adm-busqueda" required type="number" min="0" step="1" value={trabajo} onChange={e => setTrabajo(e.target.value)}/>
          <label htmlFor="e3-fund">Fundamento de revisión (20 a 2000 caracteres)</label>
          <textarea id="e3-fund" className="adm-busqueda" required minLength={20} maxLength={2000} rows={5} value={fundamento} onChange={e => setFundamento(e.target.value)}/>
          <p className="adm-nota">Se registrará el porcentaje vigente y un cálculo teórico. No se aplica el cargo sin aceptación válida anterior al pago. No se ejecutan cancelaciones ni devoluciones.</p>
          <button disabled={guardando || !decision || fundamento.trim().length<20} type="submit" className="adm-secundario">{guardando?'Guardando…':'Guardar evaluación'}</button>
        </form>}
        {elegido.estado === 'RESUELTO' && <div className="adm-panel" style={{marginTop:18}}>
          <h3>Cierre económico y distribución final</h3>
          {consultandoLiq ? <p>Consultando liquidación…</p> : liquidacion ? <CierreEconomicoSimuladoE3
            idExpediente={elegido.id_expediente}
            habilitado={true}
            onCompletado={() => setRevision(x => x + 1)}
          /> : <form onSubmit={registrarLiquidacion} style={{display:'grid',gap:12,maxWidth:700}}>
            <p>Requisitos: prestación CANCELADA, pago RETENIDO y VERIFICADO; si existe reclamo, debe tener resolución formal con efecto REVERSA y monto consistente.</p>
            <p>Para una cancelación injustificada de organización con aceptación previa válida, cargo máximo teórico: {pesos(elegido.cargo_teorico)}. Si no se permite cargo, escribe 0.</p>
            <label htmlFor="liq-cargo">Cargo que se autoriza (CLP)</label>
            <input id="liq-cargo" className="adm-busqueda" type="number" min="0" step="1" value={cargoAutorizado} onChange={e=>setCargoAutorizado(e.target.value)}/>
            <label htmlFor="liq-fund">Fundamento de liquidación y evaluación legal (mínimo 30 caracteres)</label>
            <textarea id="liq-fund" className="adm-busqueda" rows={4} minLength={30} maxLength={2000} value={fundamentoLiquidacion} onChange={e=>setFundamentoLiquidacion(e.target.value)} required/>
            <label><input type="checkbox" checked={excepcionLegal} onChange={e=>setExcepcionLegal(e.target.checked)}/> Existe derecho de devolución íntegra o excepción al cargo: aplicar cargo $0.</label>
            <label><input type="checkbox" checked={derechosVerificados} onChange={e=>setDerechosVerificados(e.target.checked)} required/> Confirmo que verifiqué los derechos aplicables, los antecedentes y la aceptación de la política.</label>
            <label><input type="checkbox" checked={confirmacionSinDinero} onChange={e=>setConfirmacionSinDinero(e.target.checked)} required/> Entiendo que esto solo solicita una reversa; NO transfiere ni devuelve dinero.</label>
            <button type="submit" disabled={guardando || !derechosVerificados || !confirmacionSinDinero || fundamentoLiquidacion.trim().length<30} className="adm-secundario">{guardando?'Registrando…':'Registrar liquidación y solicitar reversa'}</button>
          </form>}
        </div>}
      </section>}
    </main>
  </div>
}
