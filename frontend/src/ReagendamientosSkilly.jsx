import { useCallback, useEffect, useRef, useState } from 'react'
import useCargaAsincrona from './useCargaAsincrona.js'
import { solicitudReagendamiento as solicitudHttp } from './reagendamientosApi.mjs'
import useDialogoAccesible from './useDialogoAccesible.js'
import {
  estaAbierto,
  payloadAlternativas,
  puedeConfirmarAdministracion,
  puedeContraproponer,
  puedeEntregarDisponibilidad,
  puedeResponderPropuesta,
  puedeSeleccionarOrganizacion,
  tieneAlternativas,
} from './reagendamientosFlujo.mjs'
import './ReagendamientosSkilly.css'

const API = '/api/reagendamientos/'
const ESTADOS = {
  PENDIENTE_ADMIN: 'Administración debe revisar el expediente',
  PENDIENTE_PROFESIONAL: 'Esperando la decisión del profesional',
  ESPERANDO_NUEVO_BLOQUE: 'Esperando disponibilidad adicional del profesional',
  PENDIENTE_ORGANIZACION: 'La organización debe seleccionar un horario',
  ESPERANDO_SELECCION: 'Pendiente de selección de horario',
  LISTO_CONFIRMAR: 'Listo para aplicación administrativa',
  CONFIRMADO: 'Reagendamiento confirmado',
  SIN_ACUERDO: 'Cerrado sin acuerdo; se conserva la reserva original',
  VENCIDA: 'Cerrado por vencimiento de la primera reunión',
}

function mostrarHorario(bloque) {
  if (!bloque?.fecha) return 'Horario no disponible'
  const fecha = String(bloque.fecha).split('-').reverse().join('/')
  return `${fecha} · ${bloque.hora_inicio} a ${bloque.hora_fin} h (Santiago de Chile)`
}

function mostrarFechaEvento(fecha) {
  const valor = new Date(fecha)
  return Number.isNaN(valor.getTime()) ? '' : new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Santiago',
  }).format(valor)
}

function alternativasVacias() {
  return { existentes: [], nuevas: [{ fecha: '', hora_inicio: '', hora_fin: '' }] }
}

function EditorAlternativas({ disponibles = [], valor, onChange, disabled = false }) {
  const actual = valor || alternativasVacias()
  const cambiarExistente = (id, marcado) => {
    const ids = marcado
      ? [...new Set([...actual.existentes, id])]
      : actual.existentes.filter((item) => item !== id)
    onChange({ ...actual, existentes: ids })
  }
  const cambiarNueva = (indice, campo, nuevoValor) => {
    const nuevas = actual.nuevas.map((item, posicion) => (
      posicion === indice ? { ...item, [campo]: nuevoValor } : item
    ))
    onChange({ ...actual, nuevas })
  }
  return <fieldset className="rea-alternativas" disabled={disabled}>
    <legend>Horarios alternativos (puedes ofrecer varios)</legend>
    {disponibles.length > 0 && <div className="rea-lista-bloques">
      {disponibles.map((bloque) => <label key={bloque.id_disponibilidad} className="rea-opcion-bloque">
        <input type="checkbox" checked={actual.existentes.includes(bloque.id_disponibilidad)}
          onChange={(evento) => cambiarExistente(bloque.id_disponibilidad, evento.target.checked)} />
        <span>{mostrarHorario(bloque)}</span>
      </label>)}
    </div>}
    <p>Puedes agregar bloques nuevos. Deben ser futuros y no superponerse con otra disponibilidad.</p>
    {actual.nuevas.map((bloque, indice) => <div className="rea-bloque-nuevo" key={`nuevo-${indice}`}>
      <label>Fecha
        <input type="date" value={bloque.fecha}
          onChange={(evento) => cambiarNueva(indice, 'fecha', evento.target.value)} />
      </label>
      <label>Inicio
        <input type="time" value={bloque.hora_inicio}
          onChange={(evento) => cambiarNueva(indice, 'hora_inicio', evento.target.value)} />
      </label>
      <label>Término
        <input type="time" value={bloque.hora_fin}
          onChange={(evento) => cambiarNueva(indice, 'hora_fin', evento.target.value)} />
      </label>
      {actual.nuevas.length > 1 && <button type="button" onClick={() => onChange({
        ...actual, nuevas: actual.nuevas.filter((_, posicion) => posicion !== indice),
      })}>Quitar bloque</button>}
    </div>)}
    {actual.nuevas.length < 10 && <button type="button" onClick={() => onChange({
      ...actual, nuevas: [...actual.nuevas, { fecha: '', hora_inicio: '', hora_fin: '' }],
    })}>Agregar otro bloque</button>}
  </fieldset>
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
    setDatos(respuesta); setEstado('lista'); setError('')
  }, [])
  const fallar = useCallback((fallo) => {
    setError(fallo instanceof Error ? fallo.message : 'No se pudieron consultar los reagendamientos.')
    setEstado('error')
  }, [])
  const cargar = useCargaAsincrona(consultar, completar, fallar)
  return { datos, estado, error, cargar }
}

function useActualizacionInterna(cargar, pausada) {
  useEffect(() => {
    const actualizar = () => {
      if (!pausada && document.visibilityState === 'visible') void cargar()
    }
    const intervalo = window.setInterval(actualizar, 30000)
    document.addEventListener('visibilitychange', actualizar)
    return () => {
      window.clearInterval(intervalo)
      document.removeEventListener('visibilitychange', actualizar)
    }
  }, [cargar, pausada])
}

function EstadoConsulta({ estado, error }) {
  if (estado === 'cargando') return <p role="status">Consultando reagendamientos…</p>
  if (estado === 'error') return <p role="alert" className="rea-error">{error} Usa «Actualizar» para reintentar.</p>
  return null
}

function Estado({ caso, actor }) {
  return <div className="rea-estado">
    <strong>Solicitud #{caso.id} · {ESTADOS[caso.estado] || caso.estado}</strong>
    <p><b>Iniciada por:</b> {caso.iniciador === 'PROFESIONAL' ? 'Profesional' : 'Organización'}</p>
    <p><b>Motivo:</b> {caso.motivo}</p>
    <p><b>Reunión original:</b> {mostrarHorario(caso.bloque_original)}</p>
    {caso.bloque_propuesto && <p><b>Nuevo horario:</b> {mostrarHorario(caso.bloque_propuesto)}</p>}
    {caso.motivo_profesional && caso.iniciador !== 'PROFESIONAL' &&
      <p><b>Respuesta profesional:</b> {caso.motivo_profesional}</p>}
    {caso.alternativas?.length > 0 && <div>
      <b>Alternativas registradas:</b>
      <ul>{caso.alternativas.map((item) => <li key={item.id_disponibilidad}>
        {mostrarHorario(item)} · {item.disponible ? 'Disponible' : 'Ya no disponible'}
      </li>)}</ul>
    </div>}
    {actor === 'ADMINISTRACION' && caso.evidencia_disponible &&
      <p><b>Evidencia privada:</b> <a href={caso.evidencia_url}>Descargar para revisión</a></p>}
    {actor === 'PROFESIONAL' && caso.evidencia_disponible &&
      <p><b>Evidencia entregada:</b> {caso.evidencia_nombre}</p>}
    {caso.plazo_vencido && estaAbierto(caso.estado) &&
      <p className="rea-advertencia">El horario original ya transcurrió. No se presenta como reunión futura; administración debe gestionar el expediente.</p>}
    {caso.historial?.length > 0 && <details><summary>Historial del expediente</summary>
      <ol>{caso.historial.map((evento, indice) => <li key={`${indice}-${evento.fecha}`}>
        <b>{evento.actor}:</b> <time dateTime={evento.fecha}>{mostrarFechaEvento(evento.fecha)}</time> — {evento.detalle}
      </li>)}</ol>
    </details>}
  </div>
}

function ModalPolitica({ politica, aceptada, onAceptada, onContinuar, onCerrar }) {
  const panelRef = useRef(null)
  useDialogoAccesible(true, panelRef, onCerrar)
  return <div className="rea-modal-fondo" role="presentation">
    <section ref={panelRef} className="rea-modal" role="dialog" aria-modal="true"
      aria-labelledby="rea-politica-titulo" tabIndex={-1}>
      <h3 id="rea-politica-titulo">Política de reagendamiento</h3>
      <p>{politica?.texto}</p>
      <p><small>Versión: {politica?.version}</small></p>
      <label className="rea-opcion-bloque">
        <input type="checkbox" checked={aceptada} onChange={(evento) => onAceptada(evento.target.checked)} />
        <span>He leído y acepto expresamente esta política.</span>
      </label>
      <button type="button" disabled={!aceptada} onClick={onContinuar}>Continuar</button>
      <button type="button" className="rea-secundario" onClick={onCerrar}>Cancelar</button>
    </section>
  </div>
}

export function ReagendamientosOrganizacion({ referencia, estadoPrestacion }) {
  return <ReagendamientosOrganizacionContenido key={referencia}
    referencia={referencia} estadoPrestacion={estadoPrestacion} />
}

function ReagendamientosOrganizacionContenido({ referencia, estadoPrestacion }) {
  const [motivo, setMotivo] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [politicaVisible, setPoliticaVisible] = useState(false)
  const [politicaAceptada, setPoliticaAceptada] = useState(false)
  const [formularioVisible, setFormularioVisible] = useState(false)
  const [seleccion, setSeleccion] = useState('')
  const escribiendo = useRef(false)
  const url = `${API}organizacion/${encodeURIComponent(referencia || '')}/`
  const bandeja = useBandejaReagendamientos(referencia ? url : null)
  const { cargar } = bandeja
  const items = bandeja.datos?.solicitudes || []
  const actual = items[0]
  const abierta = items.some((item) => estaAbierto(item.estado))
  const disponible = bandeja.estado === 'lista' && !cargando
  useActualizacionInterna(cargar, cargando)

  async function enviar(data) {
    if (escribiendo.current || !disponible) return
    escribiendo.current = true; setCargando(true); setError(''); setAviso('')
    try {
      const respuesta = await solicitudHttp(url, { method: 'POST', body: JSON.stringify(data) })
      setAviso(respuesta.mensaje); await cargar(); setMotivo(''); setSeleccion('')
      setFormularioVisible(false); setPoliticaAceptada(false)
    } catch (fallo) { setError(fallo.message) } finally {
      escribiendo.current = false; setCargando(false)
    }
  }

  const alternativas = new Map()
  for (const bloque of [...(actual?.alternativas || []), ...(actual?.bloques_disponibles || [])]) {
    alternativas.set(bloque.id_disponibilidad, bloque)
  }
  return <section className="rea-panel" aria-label="Reagendamiento de primera reunión"
    aria-busy={bandeja.estado === 'cargando' || cargando}>
    <div className="rea-titulo"><h3>Reagendamiento de primera reunión</h3>
      <button type="button" disabled={cargando} onClick={() => void cargar()}>Actualizar estado</button></div>
    <p>La reserva solo cambia cuando administración aplica un horario autorizado.</p>
    <EstadoConsulta estado={bandeja.estado} error={bandeja.error} />
    {actual && <Estado caso={actual} actor="ORGANIZACION" />}

    {puedeSeleccionarOrganizacion(actual) &&
      <div className="rea-controles">
        <h4>Selecciona un horario</h4>
        {[...alternativas.values()].map((bloque) => <label key={bloque.id_disponibilidad} className="rea-opcion-bloque">
          <input type="radio" name={`alternativa-${actual.id}`} value={bloque.id_disponibilidad}
            checked={String(seleccion) === String(bloque.id_disponibilidad)}
            disabled={!bloque.disponible && bloque.disponible !== undefined}
            onChange={(evento) => setSeleccion(evento.target.value)} />
          <span>{mostrarHorario(bloque)}</span>
        </label>)}
        <button type="button" disabled={!disponible || !seleccion}
          onClick={() => void enviar({ accion: 'SELECCIONAR', id: actual.id, id_disponibilidad: seleccion })}>
          Seleccionar este horario
        </button>
        {actual.estado === 'PENDIENTE_ORGANIZACION' && <button type="button" disabled={!disponible}
          onClick={() => void enviar({ accion: 'ESPERAR_SELECCION', id: actual.id })}>
          Ninguno me conviene por ahora
        </button>}
      </div>}

    {bandeja.estado === 'lista' && estadoPrestacion === 'CONTRATADA' && !abierta &&
      bandeja.datos?.permite_solicitar === true && !formularioVisible &&
      <button type="button" onClick={() => {
        setPoliticaAceptada(false)
        setPoliticaVisible(true)
      }}>
        Solicitar reagendamiento de primera reunión
      </button>}
    {formularioVisible && !abierta && <form onSubmit={(evento) => {
      evento.preventDefault()
      void enviar({
        accion: 'SOLICITAR', motivo, acepta_politica: true,
        politica_version: bandeja.datos?.politica?.version,
      })
    }}>
      <label>Motivo del cambio (15 a 1000 caracteres)
        <textarea value={motivo} onChange={(evento) => setMotivo(evento.target.value)}
          minLength={15} maxLength={1000} required rows={4} />
      </label>
      <button type="submit" disabled={!disponible || motivo.trim().length < 15}>Enviar solicitud</button>
      <button type="button" onClick={() => {
        setFormularioVisible(false)
        setPoliticaAceptada(false)
      }}>Cancelar</button>
    </form>}
    {!abierta && bandeja.datos?.permite_solicitar === false && bandeja.datos?.motivo_no_disponible &&
      <p className="rea-advertencia">{bandeja.datos.motivo_no_disponible}</p>}
    {politicaVisible && <ModalPolitica politica={bandeja.datos?.politica}
      aceptada={politicaAceptada} onAceptada={setPoliticaAceptada}
      onContinuar={() => {
        setPoliticaVisible(false)
        setFormularioVisible(true)
        setPoliticaAceptada(false)
      }}
      onCerrar={() => { setPoliticaVisible(false); setPoliticaAceptada(false) }} />}
    {aviso && <p role="status" className="rea-exito">{aviso}</p>}
    {error && <p role="alert" className="rea-error">{error}</p>}
  </section>
}

export function ReagendamientosAdministracion() {
  const [selecciones, setSelecciones] = useState({})
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
    if (accion === 'CONFIRMAR' && !window.confirm('¿Aplicar el horario seleccionado en la agenda segura?')) return
    escribiendo.current = true; setCargando(true); setError(''); setAviso('')
    try {
      const respuesta = await solicitudHttp(`${API}administracion/`, {
        method: 'POST', body: JSON.stringify({
          id: item.id, accion, id_disponibilidad: selecciones[item.id],
          motivo: motivosCierre[item.id] || '',
        }),
      })
      setAviso(respuesta.mensaje); await cargar()
    } catch (fallo) { setError(fallo.message) } finally {
      escribiendo.current = false; setCargando(false)
    }
  }

  return <section className="rea-panel" aria-label="Bandeja de solicitudes de reagendamiento"
    aria-busy={bandeja.estado === 'cargando' || cargando}>
    <div className="rea-titulo"><h2>Solicitudes de reagendamiento</h2>
      <button type="button" disabled={cargando} onClick={() => void cargar()}>Actualizar bandeja</button></div>
    <EstadoConsulta estado={bandeja.estado} error={bandeja.error} />
    {bandeja.estado === 'lista' && items.length === 0 && <p>Sin solicitudes registradas.</p>}
    {items.map((item) => <div key={item.id} className="rea-caso">
      <Estado caso={item} actor="ADMINISTRACION" />
      {estaAbierto(item.estado) && item.plazo_vencido && <button type="button"
        onClick={() => void accionar(item, 'CERRAR_VENCIDA')}>Cerrar vencida sin modificar reserva</button>}
      {item.estado === 'PENDIENTE_ADMIN' && !item.plazo_vencido && item.iniciador === 'ORGANIZACION' &&
        <div className="rea-controles">
          <label>Bloque disponible del profesional
            <select value={selecciones[item.id] || ''}
              onChange={(evento) => setSelecciones((valor) => ({ ...valor, [item.id]: evento.target.value }))}>
              <option value="">Selecciona un bloque</option>
              {item.bloques_disponibles?.map((bloque) => <option key={bloque.id_disponibilidad}
                value={bloque.id_disponibilidad}>{mostrarHorario(bloque)}</option>)}
            </select>
          </label>
          <button type="button" disabled={!selecciones[item.id]}
            onClick={() => void accionar(item, 'PROPONER')}>Proponer al profesional</button>
          <button type="button" onClick={() => void accionar(item, 'SOLICITAR_BLOQUE')}>Solicitar disponibilidad</button>
        </div>}
      {item.estado === 'PENDIENTE_ADMIN' && !item.plazo_vencido && item.iniciador === 'PROFESIONAL' &&
        <div className="rea-controles">
          <p>Revisa el motivo, la evidencia privada y los horarios antes de habilitarlos.</p>
          <button type="button" onClick={() => void accionar(item, 'VALIDAR_ALTERNATIVAS')}>
            Validar horarios y enviar a la organización
          </button>
          <button type="button" onClick={() => void accionar(item, 'SOLICITAR_BLOQUE')}>Solicitar nueva disponibilidad</button>
        </div>}
      {puedeConfirmarAdministracion(item) && <button type="button"
        onClick={() => void accionar(item, 'CONFIRMAR')}>Aplicar reagendamiento en agenda segura</button>}
      {estaAbierto(item.estado) && !item.plazo_vencido && <details className="rea-cierre">
        <summary>Cerrar expediente sin acuerdo</summary>
        <label>Motivo de cierre
          <textarea minLength={10} maxLength={500} value={motivosCierre[item.id] || ''}
            onChange={(evento) => setMotivosCierre((valor) => ({ ...valor, [item.id]: evento.target.value }))} />
        </label>
        <button type="button" disabled={(motivosCierre[item.id] || '').trim().length < 10}
          onClick={() => void accionar(item, 'CERRAR_SIN_ACUERDO')}>Cerrar sin modificar reserva</button>
      </details>}
    </div>)}
    {aviso && <p role="status" className="rea-exito">{aviso}</p>}
    {error && <p role="alert" className="rea-error">{error}</p>}
  </section>
}

export function ReagendamientosProfesional() {
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [rechazos, setRechazos] = useState({})
  const [editores, setEditores] = useState({})
  const [inicioVisible, setInicioVisible] = useState(false)
  const [politicaVisible, setPoliticaVisible] = useState(false)
  const [politicaAceptada, setPoliticaAceptada] = useState(false)
  const [prestacionId, setPrestacionId] = useState('')
  const [motivoInicio, setMotivoInicio] = useState('')
  const [evidencia, setEvidencia] = useState(null)
  const [editorInicio, setEditorInicio] = useState(alternativasVacias())
  const escribiendo = useRef(false)
  const bandeja = useBandejaReagendamientos(`${API}profesional/`)
  const { cargar } = bandeja
  const items = bandeja.datos?.solicitudes || []
  const prestaciones = bandeja.datos?.prestaciones_disponibles || []
  const prestacionSeleccionada = prestaciones.find((item) => String(item.id_prestacion) === String(prestacionId))
  const disponible = bandeja.estado === 'lista' && !cargando
  useActualizacionInterna(cargar, cargando)

  async function enviarJson(item, accion, campos = {}) {
    if (escribiendo.current || !disponible) return
    escribiendo.current = true; setCargando(true); setError(''); setAviso('')
    try {
      const respuesta = await solicitudHttp(`${API}profesional/`, {
        method: 'POST', body: JSON.stringify({ id: item?.id, accion, ...campos }),
      })
      setAviso(respuesta.mensaje); await cargar()
    } catch (fallo) { setError(fallo.message) } finally {
      escribiendo.current = false; setCargando(false)
    }
  }

  async function solicitarComoProfesional(evento) {
    evento.preventDefault()
    if (escribiendo.current || !disponible) return
    const alternativas = payloadAlternativas(editorInicio)
    const datos = new FormData()
    datos.set('accion', 'SOLICITAR_PROFESIONAL')
    datos.set('id_prestacion', prestacionId)
    datos.set('motivo', motivoInicio)
    datos.set('acepta_politica', 'true')
    datos.set('politica_version', bandeja.datos?.politica?.version || '')
    datos.set('alternativas_existentes', JSON.stringify(alternativas.alternativas_existentes))
    datos.set('alternativas_nuevas', JSON.stringify(alternativas.alternativas_nuevas))
    if (evidencia) datos.set('evidencia', evidencia)
    escribiendo.current = true; setCargando(true); setError(''); setAviso('')
    try {
      const respuesta = await solicitudHttp(`${API}profesional/`, { method: 'POST', body: datos })
      setAviso(respuesta.mensaje); await cargar(); setInicioVisible(false)
      setPrestacionId(''); setMotivoInicio(''); setEvidencia(null); setEditorInicio(alternativasVacias())
    } catch (fallo) { setError(fallo.message) } finally {
      escribiendo.current = false; setCargando(false)
    }
  }

  return <section className="rea-panel" id="notificaciones-reagendamiento"
    aria-label="Notificaciones de reagendamiento profesional"
    aria-busy={bandeja.estado === 'cargando' || cargando}>
    <div className="rea-titulo"><h2>Notificaciones de reagendamiento</h2>
      <button type="button" disabled={cargando} onClick={() => void cargar()}>Actualizar avisos</button></div>
    <p>Aquí puedes responder propuestas o iniciar formalmente un cambio por impedimento.</p>
    <EstadoConsulta estado={bandeja.estado} error={bandeja.error} />
    {!inicioVisible && prestaciones.length > 0 && <button type="button"
      onClick={() => {
        setPoliticaAceptada(false)
        setPoliticaVisible(true)
      }}>Solicitar reagendamiento por impedimento</button>}
    {inicioVisible && <form onSubmit={solicitarComoProfesional} className="rea-controles">
      <label>Prestación y primera reunión
        <select required value={prestacionId} onChange={(evento) => setPrestacionId(evento.target.value)}>
          <option value="">Selecciona una prestación</option>
          {prestaciones.map((item) => <option value={item.id_prestacion} key={item.id_prestacion}>
            #{item.id_prestacion} · {item.objetivo} · {mostrarHorario(item.bloque_original)}
          </option>)}
        </select>
      </label>
      <label>Motivo del impedimento
        <textarea required minLength={20} maxLength={2000} value={motivoInicio}
          onChange={(evento) => setMotivoInicio(evento.target.value)} />
      </label>
      <label>Evidencia justificativa privada (PDF/JPG/PNG, máximo 5 MB)
        <input required type="file" accept=".pdf,.jpg,.jpeg,.png"
          onChange={(evento) => setEvidencia(evento.target.files?.[0] || null)} />
      </label>
      <EditorAlternativas disponibles={prestacionSeleccionada?.bloques_disponibles || []}
        valor={editorInicio} onChange={setEditorInicio} disabled={cargando} />
      <button type="submit" disabled={!prestacionId || motivoInicio.trim().length < 20 || !evidencia || !tieneAlternativas(editorInicio)}>
        Enviar solicitud formal
      </button>
      <button type="button" onClick={() => {
        setInicioVisible(false)
        setPoliticaAceptada(false)
      }}>Cancelar</button>
    </form>}

    {items.map((item) => <div key={item.id} className="rea-caso">
      <Estado caso={item} actor="PROFESIONAL" />
      {puedeResponderPropuesta(item) && <div className="rea-controles">
        <button type="button" onClick={() => void enviarJson(item, 'ACEPTAR')}>Aceptar bloque propuesto</button>
        {puedeContraproponer(item) && <label>Motivo del rechazo excepcional
          <textarea minLength={10} maxLength={500} value={rechazos[item.id] || ''}
            onChange={(evento) => setRechazos((valor) => ({ ...valor, [item.id]: evento.target.value }))} />
        </label>}
        {puedeContraproponer(item) && <EditorAlternativas disponibles={item.bloques_disponibles || []}
          valor={editores[item.id] || alternativasVacias()}
          onChange={(valor) => setEditores((actual) => ({ ...actual, [item.id]: valor }))} />}
        {puedeContraproponer(item) && <button type="button" disabled={(rechazos[item.id] || '').trim().length < 10 || !tieneAlternativas(editores[item.id])}
          onClick={() => void enviarJson(item, 'RECHAZAR_CON_ALTERNATIVAS', {
            motivo: rechazos[item.id], ...payloadAlternativas(editores[item.id]),
          })}>Rechazar y enviar única contrapropuesta</button>}
      </div>}
      {puedeEntregarDisponibilidad(item) && <div className="rea-controles">
        <EditorAlternativas disponibles={item.bloques_disponibles || []}
          valor={editores[item.id] || alternativasVacias()}
          onChange={(valor) => setEditores((actual) => ({ ...actual, [item.id]: valor }))} />
        <button type="button" disabled={!tieneAlternativas(editores[item.id])}
          onClick={() => void enviarJson(item, 'OFRECER_ALTERNATIVAS', payloadAlternativas(editores[item.id]))}>
          Enviar disponibilidad adicional
        </button>
      </div>}
    </div>)}
    {politicaVisible && <ModalPolitica politica={bandeja.datos?.politica}
      aceptada={politicaAceptada} onAceptada={setPoliticaAceptada}
      onContinuar={() => {
        setPoliticaVisible(false)
        setInicioVisible(true)
        setPoliticaAceptada(false)
      }}
      onCerrar={() => { setPoliticaVisible(false); setPoliticaAceptada(false) }} />}
    {aviso && <p role="status" className="rea-exito">{aviso}</p>}
    {error && <p role="alert" className="rea-error">{error}</p>}
  </section>
}
