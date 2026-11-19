import { useState } from 'react'
import './RegistrarAvanceProfesional.css'

const ESTADOS_CERRADOS = [
  'FINALIZADA',
  'CANCELADA',
  'POSTERGADA',
]

// Coincide con el catálogo validado por el backend; el aviso no altera agenda.
const MOTIVOS_AVISO = [
  { valor: 'INASISTENCIA_ORGANIZACION', nombre: 'La organización no asistió a la reunión' },
  { valor: 'CANCELACION_PROFESIONAL', nombre: 'Solicito cancelar la reunión o prestación' },
  { valor: 'REPROGRAMACION_PROFESIONAL', nombre: 'Solicito reprogramar la reunión' },
  { valor: 'IMPOSIBILIDAD_EJECUCION', nombre: 'Impedimento para continuar el servicio' },
  { valor: 'PROBLEMA_COORDINACION', nombre: 'Problema de coordinación con la organización' },
  { valor: 'OTRO', nombre: 'Otra incidencia de la prestación' },
]

const ESTADOS_SUGERIDOS = [
  { valor: 'INICIADO', nombre: 'Iniciado' },
  { valor: 'EN_PROGRESO', nombre: 'En progreso' },
  { valor: 'PENDIENTE_INFORMACION', nombre: 'Pendiente de informaci\u00f3n' },
  { valor: 'HITO_COMPLETADO', nombre: 'Hito completado' },
]

// Extrae detalles de validación del servidor para evitar mensajes genéricos.
function obtenerMensaje(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  const errores = datos && typeof datos === 'object'
    ? Object.entries(datos)
      .map(([campo, valor]) =>
        `${campo}: ${Array.isArray(valor)
          ? valor.join(', ')
          : String(valor)}`,
      ).join(' | ')
    : ''

  return errores || `No se pudo registrar el avance (HTTP ${codigo}).`
}

// Permite registrar avance o informar una incidencia en una prestación propia.
export default function RegistrarAvanceProfesional({
  idPrestacion,
  estadoPrestacion,
  onRegistrado,
}) {
  const [abierto, setAbierto] = useState(false)
  const [opcionEstado, setOpcionEstado] = useState('')
  const [estadoPersonalizado, setEstadoPersonalizado] = useState('')
  const [detalle, setDetalle] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')
  const [mostrarAviso, setMostrarAviso] = useState(false)
  const [motivoAviso, setMotivoAviso] = useState('')
  const [descripcionAviso, setDescripcionAviso] = useState('')
  const [evidenciaCancelacion, setEvidenciaCancelacion] = useState(null)
  const [procesandoAviso, setProcesandoAviso] = useState(false)
  const [errorAviso, setErrorAviso] = useState('')
  const [exitoAviso, setExitoAviso] = useState('')

  const cerrada = ESTADOS_CERRADOS.includes(
    String(estadoPrestacion ?? '').toUpperCase(),
  )

  const puedeInformarIncidencia = String(estadoPrestacion ?? '').toUpperCase() === 'CONTRATADA'

  const estadoFinal = opcionEstado === 'PERSONALIZADO'
    ? estadoPersonalizado.trim()
    : opcionEstado

  // Envía la decisión o cambios del formulario y refleja el resultado autorizado por la API.
  async function registrar(evento) {
    evento.preventDefault()

    if (enviando || cerrada || !idPrestacion) return

    if (!estadoFinal || estadoFinal.length > 30) {
      setError('El estado debe tener entre 1 y 30 caracteres.')
      return
    }

    if (!window.confirm(
      `Confirmas registrar este avance para la prestaci\u00f3n #${idPrestacion}?`,
    )) return

    setEnviando(true)
    setError('')
    setExito('')

    let registrado = false

    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const csrf = await respuestaCsrf.json().catch(() => ({}))

      if (!respuestaCsrf.ok || !csrf.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }

      const respuesta = await fetch(
        `/api/seguimiento/profesional/prestaciones/${encodeURIComponent(idPrestacion)}/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({
            estado: estadoFinal,
            detalle: detalle.trim(),
          }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerMensaje(datos, respuesta.status))
      }

      registrado = true
      setOpcionEstado('')
      setEstadoPersonalizado('')
      setDetalle('')
      setAbierto(false)

      setExito(
        typeof datos.mensaje === 'string'
          ? datos.mensaje
          : 'Avance registrado correctamente.',
      )

      if (typeof onRegistrado === 'function') {
        try {
          await onRegistrado()
        } catch {
          setExito(
            'Avance registrado. Consulta nuevamente el seguimiento para actualizarlo.',
          )
        }
      }
    } catch (fallo) {
      if (!registrado) {
        setError(
          fallo instanceof Error
            ? fallo.message
            : 'No fue posible registrar el avance.',
        )
      }
    } finally {
      setEnviando(false)
    }
  }

  // Envía la incidencia profesional al canal previsto sin registrarla como entrega.
  async function informarIncidencia(evento) {
    evento.preventDefault()
    if (!puedeInformarIncidencia || procesandoAviso || !idPrestacion) return
    const descripcion = descripcionAviso.trim()
    if (!motivoAviso || descripcion.length < 20 || descripcion.length > 2000) {
      setErrorAviso('Selecciona un motivo y describe la incidencia (20 a 2000 caracteres).')
      return
    }
    if (!window.confirm(
      `¿Enviar el aviso de incidencia de la prestación #${idPrestacion} para revisión de SKILLY?`,
    )) return
    setProcesandoAviso(true)
    setErrorAviso('')
    setExitoAviso('')
    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        method: 'GET', credentials: 'same-origin', cache: 'no-store',
        headers: { Accept: 'application/json' },
      })
      const csrf = await respuestaCsrf.json().catch(() => ({}))
      if (!respuestaCsrf.ok || !csrf.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }
      const esCancelacion = motivoAviso === 'CANCELACION_PROFESIONAL'
      const formulario = new FormData()
      formulario.append('motivo', 'Cancelación solicitada por el profesional')
      formulario.append('descripcion', descripcion)
      if (esCancelacion && evidenciaCancelacion) formulario.append('evidencia', evidenciaCancelacion)
      const respuesta = await fetch(
        `/api/seguimiento/profesional/prestaciones/${encodeURIComponent(idPrestacion)}/${esCancelacion ? 'cancelaciones' : 'incidencias'}/`,
        {
          method: 'POST', credentials: 'same-origin',
          headers: esCancelacion ? {
            Accept: 'application/json', 'X-CSRFToken': csrf.csrfToken,
          } : {
            Accept: 'application/json', 'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: esCancelacion ? formulario : JSON.stringify({ motivo: motivoAviso, descripcion }),
        },
      )
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(obtenerMensaje(datos, respuesta.status))
      setMotivoAviso('')
      setDescripcionAviso('')
      setEvidenciaCancelacion(null)
      setMostrarAviso(false)
      setExitoAviso(datos.mensaje || 'Incidencia informada a SKILLY.')
      if (typeof onRegistrado === 'function') {
        try { await onRegistrado() } catch { /* El aviso ya quedó registrado. */ }
      }
    } catch (fallo) {
      setErrorAviso(fallo instanceof Error ? fallo.message : 'No se pudo registrar el aviso.')
    } finally {
      setProcesandoAviso(false)
    }
  }

  return (
    <section className="pp-panel rap-panel">
      <div className="rap-encabezado">
        <div>
          <span className="pp-etiqueta">
            SEGUIMIENTO DE PRESTACIONES
          </span>
          <h2>Registrar avance</h2>
          <p>
            Prestaci&oacute;n #{idPrestacion}.
            Informa el progreso del trabajo realizado.
          </p>
        </div>

        {!cerrada && (
          <button
            type="button"
            className="pp-boton"
            disabled={enviando}
            onClick={() => setAbierto((actual) => !actual)}
          >
            {abierto ? 'Ocultar formulario' : 'Nuevo avance'}
          </button>
        )}
      </div>

      {cerrada && (
        <p className="rap-aviso">
          Esta prestaci&oacute;n est&aacute; cerrada y no admite
          nuevos avances.
        </p>
      )}

      {error && (
        <p className="pp-error" role="alert">{error}</p>
      )}

      {exito && (
        <p className="rap-exito" role="status">{exito}</p>
      )}

      {puedeInformarIncidencia && (
        <div className="rap-aviso-profesional">
          <div className="rap-encabezado">
            <div>
              <h3>Informar una incidencia a SKILLY</h3>
              <p>Usa este aviso si la organización no asistió, necesitas
                solicitar un cambio de fecha o surge un impedimento.</p>
            </div>
            <button type="button" className="pp-boton pp-secundario"
              disabled={procesandoAviso}
              onClick={() => setMostrarAviso((actual) => !actual)}>
              {mostrarAviso ? 'Ocultar aviso' : 'Informar incidencia'}
            </button>
          </div>
          <p className="rap-aviso">
            El aviso deja constancia para revisión administrativa. No cancela,
            reagenda, suspende ni modifica pagos automáticamente.
          </p>
          {errorAviso && <p className="pp-error" role="alert">{errorAviso}</p>}
          {exitoAviso && <p className="rap-exito" role="status">{exitoAviso}</p>}
          {mostrarAviso && (
            <form className="rap-formulario" onSubmit={informarIncidencia}>
              <div className="rap-campo">
                <label htmlFor="rap-motivo-aviso">Motivo del aviso *</label>
                <select id="rap-motivo-aviso" required value={motivoAviso}
                  disabled={procesandoAviso}
                  onChange={(evento) => setMotivoAviso(evento.target.value)}>
                  <option value="">Selecciona un motivo</option>
                  {MOTIVOS_AVISO.map((motivo) => (
                    <option value={motivo.valor} key={motivo.valor}>{motivo.nombre}</option>
                  ))}
                </select>
              </div>
              <div className="rap-campo">
                <label htmlFor="rap-descripcion-aviso">¿Qué ocurrió? *</label>
                <textarea id="rap-descripcion-aviso" rows={4} required
                  minLength={20} maxLength={2000}
                  value={descripcionAviso} disabled={procesandoAviso}
                  onChange={(evento) => setDescripcionAviso(evento.target.value)}
                  placeholder="Describe fecha, reunión y antecedentes; no incluyas datos bancarios." />
                <small>Entre 20 y 2000 caracteres. Este aviso quedará en el historial.</small>
              </div>
              {motivoAviso === 'CANCELACION_PROFESIONAL' && (
                <div className="rap-campo">
                  <label htmlFor="rap-evidencia-cancelacion">Respaldo justificativo (opcional, PDF/JPG/PNG, máximo 5 MB)</label>
                  <input id="rap-evidencia-cancelacion" type="file" accept=".pdf,.jpg,.jpeg,.png"
                    disabled={procesandoAviso}
                    onChange={(evento) => setEvidenciaCancelacion(evento.target.files?.[0] || null)} />
                  <small>Archivo privado para revisión por SKILLY. No incluir datos médicos sensibles.</small>
                </div>
              )}
              <button type="submit" className="pp-boton" disabled={procesandoAviso}>
                {procesandoAviso ? 'Enviando aviso...' : 'Enviar a revisión de SKILLY'}
              </button>
            </form>
          )}
        </div>
      )}

      {abierto && !cerrada && (
        <form className="rap-formulario" onSubmit={registrar}>
          <div className="rap-campo">
            <label htmlFor="rap-estado">
              Estado del avance *
            </label>

            <select
              id="rap-estado"
              required
              value={opcionEstado}
              disabled={enviando}
              onChange={(evento) => {
                setOpcionEstado(evento.target.value)
                setError('')
              }}
            >
              <option value="">Selecciona un estado</option>

              {ESTADOS_SUGERIDOS.map((opcion) => (
                <option key={opcion.valor} value={opcion.valor}>
                  {opcion.nombre}
                </option>
              ))}

              <option value="PERSONALIZADO">
                Otro estado (personalizado)
              </option>
            </select>

            {opcionEstado === 'PERSONALIZADO' && (
              <>
                <label htmlFor="rap-estado-personalizado">
                  Escribe el estado personalizado *
                </label>
                <input
                  id="rap-estado-personalizado"
                  type="text"
                  required
                  maxLength={30}
                  value={estadoPersonalizado}
                  disabled={enviando}
                  onChange={(evento) =>
                    setEstadoPersonalizado(evento.target.value)
                  }
                  placeholder="M\u00e1ximo 30 caracteres"
                />
              </>
            )}

            <small>
              Los estados son sugerencias de registro; el backend
              permite un estado personalizado de hasta 30 caracteres.
            </small>
          </div>

          <div className="rap-campo">
            <label htmlFor="rap-detalle">
              Detalle del avance (opcional)
            </label>
            <textarea
              id="rap-detalle"
              rows={5}
              value={detalle}
              disabled={enviando}
              onChange={(evento) =>
                setDetalle(evento.target.value)
              }
              placeholder="Describe el progreso del servicio"
            />
          </div>

          <button
            type="submit"
            className="pp-boton"
            disabled={
              enviando ||
              !estadoFinal ||
              estadoFinal.length > 30
            }
          >
            {enviando
              ? 'Registrando avance...'
              : 'Confirmar registro de avance'}
          </button>
        </form>
      )}
    </section>
  )
}
