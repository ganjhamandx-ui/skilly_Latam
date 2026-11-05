import { useEffect, useState } from 'react'
import { ACCIONES, accionesDisponibles, bloquesElegibles, validarCambioAgenda } from './politicasAgendaPrestacionE3.mjs'
import './AgendaPrestacionAdministracionE3.css'

function textoError(datos, codigo) {
  return datos?.mensaje || datos?.detail || `No se completó la operación (HTTP ${codigo}).`
}

function fechaBloque(b) {
  const fecha = new Date(`${b.fecha}T${b.hora_inicio}`)
  const inicio = Number.isNaN(fecha.getTime())
    ? `${b.fecha} ${b.hora_inicio}`
    : fecha.toLocaleString('es-CL', { dateStyle: 'medium', timeStyle: 'short' })
  return `${inicio} a ${String(b.hora_fin).slice(0, 5)} · Bloque #${b.id_disponibilidad}`
}

/** Administración decide cambios usando el endpoint seguro ya existente (no pagos). */
export default function AgendaPrestacionAdministracionE3({ idPrestacion, estadoPrestacion, onActualizado }) {
  const [abierto, setAbierto] = useState(false)
  const [datos, setDatos] = useState(null)
  const [revision, setRevision] = useState(0)
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [accion, setAccion] = useState('')
  const [motivo, setMotivo] = useState('')
  const [bloqueId, setBloqueId] = useState('')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const ruta = `/api/coordinacion/administracion/prestaciones/${encodeURIComponent(idPrestacion)}/agenda/`

  useEffect(() => {
    if (!abierto) return undefined
    const controlador = new AbortController()
    async function cargar() {
      setCargando(true)
      setError('')
      try {
        const respuesta = await fetch(ruta, {
          credentials: 'same-origin', cache: 'no-store',
          headers: { Accept: 'application/json' }, signal: controlador.signal,
        })
        const json = await respuesta.json().catch(() => ({}))
        if (!respuesta.ok) throw new Error(textoError(json, respuesta.status))
        if (!json.prestacion || !Array.isArray(json.bloques_profesional) || !Array.isArray(json.reservas)) {
          throw new Error('La API de agenda devolvió datos incompletos.')
        }
        if (!controlador.signal.aborted) setDatos(json)
      } catch (fallo) {
        if (!controlador.signal.aborted) setError(fallo.message || 'No se pudo consultar la agenda.')
      } finally {
        if (!controlador.signal.aborted) setCargando(false)
      }
    }
    void cargar()
    return () => controlador.abort()
  }, [abierto, ruta, revision])

  const estado = datos?.prestacion?.estado ?? estadoPrestacion
  const opciones = accionesDisponibles(estado)
  const bloques = bloquesElegibles(datos?.bloques_profesional)
  const reservaActiva = (datos?.reservas ?? []).find((reserva) => reserva.estado === 'ACTIVA')

  async function ejecutar(evento) {
    evento.preventDefault()
    if (guardando || cargando || !datos) return
    const problema = validarCambioAgenda({ estado, accion, motivo, bloqueId, bloques: datos.bloques_profesional })
    if (problema) { setError(problema); return }
    const explicacion = accion === 'CANCELAR'
      ? `Vas a CANCELAR DEFINITIVAMENTE la prestación #${idPrestacion}. Esta decisión no devuelve dinero automáticamente. ¿Confirmas?`
      : `¿Confirmas ${accion === 'POSTERGAR' ? 'POSTERGAR' : 'REAGENDAR'} la prestación #${idPrestacion}?`
    if (!window.confirm(explicacion)) return
    setGuardando(true)
    setError('')
    setAviso('')
    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', { credentials: 'same-origin', cache: 'no-store' })
      const csrf = await respuestaCsrf.json().catch(() => ({}))
      if (!respuestaCsrf.ok || !csrf.csrfToken) throw new Error('No fue posible obtener el token CSRF.')
      const contenido = { accion, motivo: motivo.trim() }
      if (accion === 'REAGENDAR') contenido.id_disponibilidad_nueva = Number(bloqueId)
      const respuesta = await fetch(ruta, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf.csrfToken, Accept: 'application/json' },
        body: JSON.stringify(contenido),
      })
      const json = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(textoError(json, respuesta.status))
      setAviso(`${json.mensaje || 'Agenda actualizada.'} No se ha realizado ninguna devolución de dinero.`)
      setAccion('')
      setMotivo('')
      setBloqueId('')
      setRevision((actual) => actual + 1)
      if (onActualizado) {
        try { await onActualizado() }
        catch { setAviso('Cambio aplicado. La ficha general no se actualizó; vuelve a consultar la solicitud.') }
      }
    } catch (fallo) {
      setError(fallo.message || 'No se pudo modificar la agenda.')
    } finally {
      setGuardando(false)
    }
  }

  if (!accionesDisponibles(estadoPrestacion).length) return null

  return (
    <section className="sk-agenda-e3" aria-label="Gestión administrativa de agenda">
      <div className="sk-agenda-e3-header">
        <div>
          <h3>Gestión de cancelaciones y reprogramaciones</h3>
          <p>Acciones administrativas vinculadas a la prestación #{idPrestacion}, con motivo y trazabilidad.</p>
        </div>
        <button type="button" className="adm-secundario" disabled={guardando}
          aria-expanded={abierto} onClick={() => { setAbierto(!abierto); setError('') }}>
          {abierto ? 'Ocultar agenda' : 'Gestionar agenda'}
        </button>
      </div>
      {abierto && (
        <div className="sk-agenda-e3-contenido">
          {cargando && <p role="status">Consultando reservas y disponibilidad...</p>}
          {error && <p className="adm-error" role="alert">{error}</p>}
          {aviso && <p className="adm-aviso" role="status">{aviso}</p>}
          {datos && !cargando && (
            <>
              <div className="sk-agenda-e3-resumen">
                <span><small>Prestación</small><strong>{estado}</strong></span>
                <span><small>Reserva activa</small><strong>{reservaActiva ? `#${reservaActiva.id_reserva}` : 'No registrada'}</strong></span>
                <span><small>Horarios futuros libres</small><strong>{bloques.length}</strong></span>
              </div>
              {opciones.length === 0 ? (
                <p className="adm-nota">Esta prestación no admite modificaciones de agenda.</p>
              ) : (
                <form onSubmit={ejecutar} className="sk-agenda-e3-formulario">
                  <label>
                    Operación
                    <select value={accion} required disabled={guardando} onChange={(e) => { setAccion(e.target.value); setBloqueId(''); setError('') }}>
                      <option value="">Selecciona una acción</option>
                      {opciones.map((opcion) => <option key={opcion} value={opcion}>{ACCIONES[opcion]}</option>)}
                    </select>
                  </label>
                  {accion === 'REAGENDAR' && (
                    <label>
                      Nuevo horario del profesional
                      <select value={bloqueId} required disabled={guardando} onChange={(e) => setBloqueId(e.target.value)}>
                        <option value="">Selecciona un bloque futuro</option>
                        {bloques.map((bloque) => (
                          <option key={bloque.id_disponibilidad} value={bloque.id_disponibilidad}>
                            {fechaBloque(bloque)}
                          </option>
                        ))}
                      </select>
                      {bloques.length === 0 && <small>No existen bloques disponibles. El profesional debe publicar disponibilidad antes de reagendar.</small>}
                    </label>
                  )}
                  <label>
                    Motivo administrativo (20 a 500 caracteres)
                    <textarea rows={3} value={motivo} minLength={20} maxLength={500} required disabled={guardando}
                      onChange={(e) => setMotivo(e.target.value)} placeholder="Explica lo sucedido, antecedentes revisados y decisión acordada." />
                    <small>{motivo.trim().length}/500 caracteres</small>
                  </label>
                  {accion === 'CANCELAR' && <p className="sk-agenda-e3-alerta">La cancelación es definitiva. Si existe pago retenido, debes gestionar por separado el reclamo y la eventual reversa en CU040.</p>}
                  {accion === 'POSTERGAR' && <p className="adm-nota">Postergar libera el horario y conserva el pago retenido, siempre que el backend valide los requisitos. Se debe reagendar después.</p>}
                  <div className="sk-agenda-e3-acciones">
                    <button className="adm-accion" type="submit" disabled={guardando || !accion || (accion === 'REAGENDAR' && !bloques.length)}>
                      {guardando ? 'Guardando decisión...' : 'Confirmar decisión administrativa'}
                    </button>
                    <button type="button" className="adm-secundario" disabled={guardando} onClick={() => setRevision((actual) => actual + 1)}>↻ Consultar disponibilidad</button>
                  </div>
                </form>
              )}
              <p className="sk-agenda-e3-aviso">La operación requiere permisos administrativos en el servidor y no libera pagos, ejecuta sanciones ni produce reembolsos automáticamente.</p>
            </>
          )}
        </div>
      )}
    </section>
  )
}
