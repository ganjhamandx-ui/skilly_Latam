import { useCallback, useEffect, useRef, useState } from 'react'
import useCargaAsincrona from './useCargaAsincrona.js'
import { solicitudReagendamiento as solicitudHttp } from './reagendamientosApi.mjs'
import './ReagendamientosSkilly.css'

const API = '/api/reagendamientos/'
const ABIERTOS = new Set([
  'PENDIENTE_ADMIN', 'PENDIENTE_PROFESIONAL', 'ESPERANDO_NUEVO_BLOQUE',
  'PENDIENTE_ORGANIZACION', 'LISTO_CONFIRMAR',
])
const ESTADOS = {
  PENDIENTE_ADMIN: 'Solicitud recibida; administración debe revisarla',
  PENDIENTE_PROFESIONAL: 'Propuesta enviada al profesional; esperando su decisión',
  ESPERANDO_NUEVO_BLOQUE: 'Esperando nueva disponibilidad del profesional',
  PENDIENTE_ORGANIZACION: 'Alternativa del profesional; esperando confirmación de la organización',
  LISTO_CONFIRMAR: 'Ambas partes han confirmado; administración debe aplicar el cambio',
  CONFIRMADO: 'Reagendamiento confirmado',
  SIN_ACUERDO: 'Cerrada sin acuerdo: se mantiene la reserva original',
  VENCIDA: 'Cerrada por vencimiento de la primera reunión',
}

function mostrarHorario(b) {
  if (!b) return 'Sin horario propuesto'
  const fecha = String(b.fecha || '').split('-').reverse().join('/')
  return `${fecha} · ${b.hora_inicio} a ${b.hora_fin} h (Santiago de Chile)`
}

function mostrarFechaEvento(fecha) {
  if (!fecha) return ''
  const valor = new Date(fecha)
  return Number.isNaN(valor.getTime()) ? '' : new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Santiago',
  }).format(valor)
}

function useBandejaReagendamientos(url) {
  const [datos, setDatos] = useState(null)
  const [estado, setEstado] = useState('cargando')
  const [error, setError] = useState('')
  const consultar = useCallback((signal) => {
    setEstado('cargando')
    setError('')
    if (!url) return Promise.reject(new Error('No se ha seleccionado una prestación.'))
    return solicitudHttp(url, { signal })
  }, [url])
  const completar = useCallback((respuesta) => {
    setDatos(respuesta)
    setEstado('lista')
    setError('')
  }, [])
  const fallar = useCallback((fallo) => {
    setError(fallo instanceof Error ? fallo.message : 'No se pudieron consultar los reagendamientos.')
    setEstado('error')
  }, [])
  const cargar = useCargaAsincrona(consultar, completar, fallar)
  return { datos, estado, error, cargar }
}

function EstadoConsulta({ estado, error }) {
  if (estado === 'cargando') return <p role="status">Consultando reagendamientos…</p>
  if (estado === 'error') return <p role="alert" className="rea-error">{error} Usa «Actualizar» para reintentar.</p>
  return null
}

// Los avisos se actualizan dentro de SKILLY, sin usar correo ni llamadas externas.
function useActualizacionInterna(cargar, pausada) {
  useEffect(() => {
    const actualizarSiVisible = () => {
      if (!pausada && document.visibilityState === 'visible') void cargar()
    }
    const intervalo = window.setInterval(actualizarSiVisible, 30000)
    document.addEventListener('visibilitychange', actualizarSiVisible)
    return () => {
      window.clearInterval(intervalo)
      document.removeEventListener('visibilitychange', actualizarSiVisible)
    }
  }, [cargar, pausada])
}

function Estado({ caso }) {
  return <div className="rea-estado">
    <strong>Solicitud #{caso.id} · {ESTADOS[caso.estado] || caso.estado}</strong>
    <p><b>Motivo:</b> {caso.motivo}</p>
    <p><b>Reunión original:</b> {mostrarHorario(caso.bloque_original)}</p>
    {caso.bloque_propuesto && <p><b>Nuevo horario propuesto:</b> {mostrarHorario(caso.bloque_propuesto)}</p>}
    {caso.motivo_profesional && <p><b>Observación profesional:</b> {caso.motivo_profesional}</p>}
    {caso.plazo_vencido && ABIERTOS.has(caso.estado) && <p className="rea-advertencia">El horario original ya comenzó o transcurrió. Administración debe cerrar el caso; no se modificará la reserva.</p>}
    {caso.historial?.length > 0 && <details><summary>Historial y comunicaciones internas</summary>
      <ol>{caso.historial.map((e, i) => <li key={`${i}-${e.fecha}`}>
        <b>{e.actor}:</b> <time dateTime={e.fecha}>{mostrarFechaEvento(e.fecha)}</time> — {e.detalle}
      </li>)}</ol></details>}
  </div>
}

export function ReagendamientosOrganizacion({ referencia, estadoPrestacion }) {
  return <ReagendamientosOrganizacionContenido key={referencia} referencia={referencia} estadoPrestacion={estadoPrestacion} />
}

function ReagendamientosOrganizacionContenido({ referencia, estadoPrestacion }) {
  const [motivo, setMotivo] = useState('')
  const [motivoAlternativa, setMotivoAlternativa] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const escribiendo = useRef(false)
  const url = `${API}organizacion/${encodeURIComponent(referencia || '')}/`
  const bandeja = useBandejaReagendamientos(referencia ? url : null)
  const { cargar } = bandeja
  const items = bandeja.datos?.solicitudes || []
  const permiteSolicitar = bandeja.datos?.permite_solicitar === true
  const motivoNoDisponible = bandeja.datos?.motivo_no_disponible || ''
  const disponible = bandeja.estado === 'lista' && !cargando
  useActualizacionInterna(cargar, cargando)
  async function enviar(data) {
    if (escribiendo.current || !disponible) return
    escribiendo.current = true
    setCargando(true); setError(''); setAviso('')
    try { const r = await solicitudHttp(url, { method: 'POST', body: JSON.stringify(data) }); setAviso(r.mensaje); await cargar(); setMotivo('') }
    catch (e) { setError(e.message) } finally { escribiendo.current = false; setCargando(false) }
  }
  const actual = items[0]
  const abierta = items.some((x) => ABIERTOS.has(x.estado))
  return <section className="rea-panel" aria-label="Reagendamiento de primera reunión" aria-busy={bandeja.estado === 'cargando' || cargando}>
    <div className="rea-titulo"><h3>Solicitar cambio de primera reunión</h3>
      <button type="button" disabled={bandeja.estado === 'cargando' || cargando} onClick={() => void cargar()}>Actualizar estado</button></div>
    <p>La solicitud se comunica exclusivamente por SKILLY. No modifica tu reserva hasta que ambas partes confirmen el nuevo horario y administración lo aplique.</p>
    <EstadoConsulta estado={bandeja.estado} error={bandeja.error} />
    {actual && <Estado caso={actual} />}
    {actual?.estado === 'PENDIENTE_ORGANIZACION' && !actual.plazo_vencido && <div className="rea-controles">
      <button type="button" disabled={!disponible}
        onClick={() => void enviar({ accion: 'ACEPTAR_ALTERNATIVA', id: actual.id })}>
        Aceptar horario alternativo propuesto
      </button>
      <label>Si la alternativa no te sirve, indica el motivo
        <textarea rows={2} minLength={10} maxLength={500} value={motivoAlternativa} disabled={cargando}
          onChange={(e) => setMotivoAlternativa(e.target.value)} />
      </label>
      <button type="button" disabled={!disponible || motivoAlternativa.trim().length < 10}
        onClick={() => void enviar({ accion: 'NO_ACEPTAR_ALTERNATIVA', id: actual.id, motivo: motivoAlternativa })}>
        No aceptar esta alternativa
      </button>
    </div>}
    {bandeja.estado === 'lista' && estadoPrestacion === 'CONTRATADA' && !abierta && !permiteSolicitar && motivoNoDisponible &&
      <p className="rea-advertencia">{motivoNoDisponible}</p>}
    {estadoPrestacion === 'CONTRATADA' && !abierta && permiteSolicitar && <form onSubmit={(e) => { e.preventDefault(); void enviar({ accion: 'SOLICITAR', motivo }) }}>
      <label>Motivo del cambio (15 a 1000 caracteres)
        <textarea value={motivo} disabled={cargando} onChange={(e) => setMotivo(e.target.value)} minLength={15} maxLength={1000} required rows={3} />
      </label>
      <button type="submit" disabled={!disponible || motivo.trim().length < 15}>{cargando ? 'Enviando…' : 'Enviar solicitud a SKILLY'}</button>
    </form>}
    {aviso && <p role="status" className="rea-exito">{aviso}</p>}
    {error && <p role="alert" className="rea-error">{error}</p>}
  </section>
}

export function ReagendamientosAdministracion() {
  const [opciones, setOpciones] = useState({})
  const [motivosCierre, setMotivosCierre] = useState({})
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const escribiendo = useRef(false)
  const bandeja = useBandejaReagendamientos(`${API}administracion/`)
  const { cargar } = bandeja
  const items = bandeja.datos?.solicitudes || []
  const disponible = bandeja.estado === 'lista' && !cargando
  useActualizacionInterna(cargar, cargando)
  async function accionar(item, accion) {
    if (escribiendo.current || !disponible) return
    if (accion === 'CONFIRMAR' && !window.confirm('¿Confirmas el nuevo horario? Esta acción reemplaza la reserva actual.')) return
    escribiendo.current = true
    setCargando(true); setError(''); setAviso('')
    try {
      const r = await solicitudHttp(`${API}administracion/`, { method: 'POST',
        body: JSON.stringify({ id: item.id, accion, id_disponibilidad: opciones[item.id], motivo: motivosCierre[item.id] || '' }) })
      setAviso(r.mensaje); await cargar()
    } catch (e) { setError(e.message) } finally { escribiendo.current = false; setCargando(false) }
  }
  return <section className="rea-panel" aria-label="Bandeja de solicitudes de reagendamiento" aria-busy={bandeja.estado === 'cargando' || cargando}>
    <div className="rea-titulo"><h2>Solicitudes de reagendamiento</h2>
      <button type="button" disabled={bandeja.estado === 'cargando' || cargando} onClick={() => void cargar()}>Actualizar bandeja</button></div>
    <p>Solicitudes recibidas dentro de SKILLY. La agenda no cambia hasta confirmar las decisiones de las partes.</p>
    <EstadoConsulta estado={bandeja.estado} error={bandeja.error} />
    {bandeja.estado === 'lista' && items.length === 0 && <p>Sin solicitudes de reagendamiento registradas.</p>}
    {items.map((item) => <div key={item.id} className="rea-caso"><Estado caso={item} />
      {ABIERTOS.has(item.estado) && item.plazo_vencido && <button type="button" disabled={!disponible}
        onClick={() => void accionar(item, 'CERRAR_VENCIDA')}>Cerrar solicitud vencida sin modificar la reserva</button>}
      {item.estado === 'PENDIENTE_ADMIN' && !item.plazo_vencido && <div className="rea-controles">
        <label>Bloque disponible del profesional
          <select value={opciones[item.id] || ''} disabled={cargando} onChange={(e) => setOpciones((x) => ({ ...x, [item.id]: e.target.value }))}>
            <option value="">Selecciona un bloque</option>
            {item.bloques_disponibles?.map((b) => <option key={b.id_disponibilidad} value={b.id_disponibilidad}>{mostrarHorario(b)}</option>)}
          </select>
        </label>
        <button type="button" disabled={!disponible || !opciones[item.id]} onClick={() => void accionar(item, 'PROPONER')}>Proponer al profesional</button>
        <button type="button" disabled={!disponible} onClick={() => void accionar(item, 'SOLICITAR_BLOQUE')}>Solicitar nueva disponibilidad</button>
      </div>}
      {item.estado === 'LISTO_CONFIRMAR' && !item.plazo_vencido && <button type="button" disabled={!disponible}
        onClick={() => void accionar(item, 'CONFIRMAR')}>Confirmar reagendamiento en agenda</button>}
      {ABIERTOS.has(item.estado) && !item.plazo_vencido && <details className="rea-cierre"><summary>Cerrar solicitud sin acuerdo</summary>
        <label>Motivo de cierre (10 a 500 caracteres)
          <textarea rows={2} minLength={10} maxLength={500} value={motivosCierre[item.id] || ''} disabled={cargando}
            onChange={(e) => setMotivosCierre((v) => ({ ...v, [item.id]: e.target.value }))} />
        </label>
        <button type="button" disabled={!disponible || (motivosCierre[item.id] || '').trim().length < 10}
          onClick={() => void accionar(item, 'CERRAR_SIN_ACUERDO')}>Cerrar sin modificar la reserva</button>
      </details>}
    </div>)}
    {aviso && <p role="status" className="rea-exito">{aviso}</p>}
    {error && <p role="alert" className="rea-error">{error}</p>}
  </section>
}

export function ReagendamientosProfesional() {
  const [rechazos, setRechazos] = useState({})
  const [alternativas, setAlternativas] = useState({})
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const escribiendo = useRef(false)
  const bandeja = useBandejaReagendamientos(`${API}profesional/`)
  const { cargar } = bandeja
  const items = bandeja.datos?.solicitudes || []
  const disponible = bandeja.estado === 'lista' && !cargando
  useActualizacionInterna(cargar, cargando)
  async function accionar(item, accion, campos = {}) {
    if (escribiendo.current || !disponible) return
    escribiendo.current = true
    setCargando(true); setError(''); setAviso('')
    try { const r = await solicitudHttp(`${API}profesional/`, { method: 'POST', body: JSON.stringify({ id: item.id, accion, ...campos }) }); setAviso(r.mensaje); await cargar() }
    catch (e) { setError(e.message) } finally { escribiendo.current = false; setCargando(false) }
  }
  return <section className="rea-panel" aria-label="Notificaciones de reagendamiento profesional" aria-busy={bandeja.estado === 'cargando' || cargando}>
    <div className="rea-titulo"><h2>Notificaciones de reagendamiento</h2>
      <button type="button" disabled={bandeja.estado === 'cargando' || cargando} onClick={() => void cargar()}>Actualizar avisos</button></div>
    <EstadoConsulta estado={bandeja.estado} error={bandeja.error} />
    {bandeja.estado === 'lista' && items.filter((x) => ABIERTOS.has(x.estado)).length === 0 && <p>No tienes solicitudes pendientes de reagendamiento.</p>}
    {items.map((item) => <div key={item.id} className="rea-caso"><Estado caso={item} />
      {item.estado === 'PENDIENTE_PROFESIONAL' && !item.plazo_vencido && <div className="rea-controles">
        <button type="button" disabled={!disponible} onClick={() => void accionar(item, 'ACEPTAR')}>Aceptar bloque propuesto</button>
        <label>Si no puedes asistir, indica el motivo
          <textarea value={rechazos[item.id] || ''} minLength={10} maxLength={500} disabled={cargando}
            onChange={(e) => setRechazos((v) => ({ ...v, [item.id]: e.target.value }))} rows={2} />
        </label>
        <button type="button" disabled={!disponible || (rechazos[item.id] || '').trim().length < 10}
          onClick={() => void accionar(item, 'RECHAZAR', { motivo: rechazos[item.id] })}>No disponible: proponer alternativa</button>
      </div>}
      {item.estado === 'ESPERANDO_NUEVO_BLOQUE' && !item.plazo_vencido && <form className="rea-controles" onSubmit={(e) => {
        e.preventDefault(); void accionar(item, 'CREAR_ALTERNATIVA', alternativas[item.id] || {})
      }}>
        <p>Registra un bloque real de tu agenda (fecha y horario de Santiago de Chile). SKILLY avisará dentro de la plataforma a la organización para que confirme ese horario.</p>
        <label>Fecha <input type="date" required value={alternativas[item.id]?.fecha || ''} onChange={(e) => setAlternativas((a) => ({ ...a, [item.id]: { ...a[item.id], fecha: e.target.value } }))} /></label>
        <label>Hora de inicio <input type="time" required value={alternativas[item.id]?.hora_inicio || ''} onChange={(e) => setAlternativas((a) => ({ ...a, [item.id]: { ...a[item.id], hora_inicio: e.target.value } }))} /></label>
        <label>Hora de término <input type="time" required value={alternativas[item.id]?.hora_fin || ''} onChange={(e) => setAlternativas((a) => ({ ...a, [item.id]: { ...a[item.id], hora_fin: e.target.value } }))} /></label>
        <button type="submit" disabled={!disponible}>Registrar bloque y notificar a la organización</button>
      </form>}
    </div>)}
    {aviso && <p role="status" className="rea-exito">{aviso}</p>}
    {error && <p role="alert" className="rea-error">{error}</p>}
  </section>
}
