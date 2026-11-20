// Gestiona bloques y contactos de entrevista; el backend conserva la autoridad sobre reservas.
import { useEffect, useState } from 'react'

const RUTA_AGENDA = '/api/profesionales/administracion/entrevistas/'
const RUTA_BLOQUES = `${RUTA_AGENDA}bloques/`

const FORMULARIO_INICIAL = {
  fecha: '',
  hora_inicio: '',
  hora_fin: '',
  capacidad: '1',
  estado: 'DISPONIBLE',
}

const estiloCampos = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '11px 12px',
  borderRadius: 10,
  border: '1px solid #cfdcd4',
  background: '#fff',
  color: '#243a34',
  font: 'inherit',
}

const estiloGrilla = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 205px), 1fr))',
  gap: 14,
}

/**
 * Presenta las primeras cinco posiciones de la hora civil recibida.
 * @param {string|null} valor Hora del bloque.
 * @returns {string} Hora abreviada o «Sin hora».
 */
function mostrarHora(valor) {
  return valor ? String(valor).slice(0, 5) : 'Sin hora'
}

/**
 * Invierte las partes de una fecha civil sin convertir zonas horarias.
 * @param {string|null} valor Fecha recibida, posiblemente con hora.
 * @returns {string} Día-mes-año, texto original o «Sin fecha».
 */
function mostrarFecha(valor) {
  if (!valor) return 'Sin fecha'
  const partes = String(valor).slice(0, 10).split('-')
  return partes.length === 3
    ? `${partes[2]}-${partes[1]}-${partes[0]}`
    : String(valor)
}

/**
 * Prioriza mensajes generales y reúne errores textuales de campos.
 * @param {Object|null} datos Cuerpo de respuesta.
 * @param {number} codigo Estado HTTP usado como respaldo.
 * @returns {string} Explicación del error para la agenda.
 */
function mensajeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const errores = Object.entries(datos).flatMap(([campo, contenido]) => {
      if (Array.isArray(contenido)) {
        return contenido.map((mensaje) => `${campo}: ${mensaje}`)
      }
      return typeof contenido === 'string' ? [`${campo}: ${contenido}`] : []
    })
    if (errores.length) return errores.join(' | ')
  }

  return `La operación no se completó (HTTP ${codigo}).`
}

/**
 * Obtiene la colección de reservas sin filtrar sus estados.
 * @param {Object|null|undefined} bloque Bloque consultado.
 * @returns {Object[]} Reservas recibidas o una lista vacía.
 */
function reservasDe(bloque) {
  return Array.isArray(bloque?.reservas) ? bloque.reservas : []
}

/**
 * Convierte los valores del bloque a los controles del formulario.
 * @param {Object} bloque Bloque existente de entrevista.
 * @returns {Object} Fecha, horas, capacidad textual y estado de edición.
 */
function datosFormulario(bloque) {
  return {
    fecha: String(bloque.fecha ?? '').slice(0, 10),
    hora_inicio: mostrarHora(bloque.hora_inicio),
    hora_fin: mostrarHora(bloque.hora_fin),
    capacidad: String(bloque.capacidad ?? 1),
    estado: bloque.estado ?? 'DISPONIBLE',
  }
}

/**
 * Gestiona bloques de entrevistas y confirma contactos ya realizados.
 * Las reservas condicionan los cambios de horario, capacidad y vigencia.
 * @param {Object} props Propiedades de integración con la bandeja.
 * @param {function(boolean): void} [props.onProcesandoChange] Notifica las escrituras en curso.
 * @returns {import('react').ReactElement} Agenda y formulario administrativo.
 */
export default function EntrevistasAdministracion({ onProcesandoChange }) {
  const [bloques, setBloques] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [modo, setModo] = useState(null)
  const [idEdicion, setIdEdicion] = useState(null)
  const [formulario, setFormulario] = useState({ ...FORMULARIO_INICIAL })
  const [guardando, setGuardando] = useState(false)
  const [errorAccion, setErrorAccion] = useState('')
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    // Cancela la lectura de agenda cuando cambia la pantalla.
    const controlador = new AbortController()

    /**
     * Consulta bloques con sus reservas y verifica la colección recibida.
     * Ignora resultados y errores si la lectura fue cancelada.
     * @returns {Promise<void>} Finalización de la consulta con errores visibles.
     */
    async function consultarAgenda() {
      setCargando(true)
      setError('')
      try {
        const respuesta = await fetch(RUTA_AGENDA, {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
          signal: controlador.signal,
        })
        const datos = await respuesta.json().catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(mensajeError(datos, respuesta.status))
        }
        if (!Array.isArray(datos.bloques)) {
          throw new Error('La API no devolvió una lista válida de bloques.')
        }
        if (!controlador.signal.aborted) setBloques(datos.bloques)
      } catch (fallo) {
        if (!controlador.signal.aborted) {
          setError(fallo instanceof Error ? fallo.message : 'No se pudo consultar la agenda.')
        }
      } finally {
        if (!controlador.signal.aborted) setCargando(false)
      }
    }

    void consultarAgenda()
    return () => controlador.abort()
  }, [revision])

  /**
   * Actualiza una entrada conservando el resto del borrador y limpia su error.
   * @param {string} nombre Campo del formulario.
   * @param {string} valor Valor capturado por el control.
   * @returns {void}
   */
  function actualizarCampo(nombre, valor) {
    setFormulario((anterior) => ({ ...anterior, [nombre]: valor }))
    setErrorAccion('')
  }

  /**
   * Abre un borrador vacío cuando no hay una escritura en curso.
   * @returns {void}
   */
  function iniciarCreacion() {
    if (guardando) return
    setModo('crear')
    setIdEdicion(null)
    setFormulario({ ...FORMULARIO_INICIAL })
    setErrorAccion('')
    setAviso('')
  }

  /**
   * Carga el bloque seleccionado en el formulario si no se está guardando.
   * @param {Object} bloque Bloque de entrevista que se desea modificar.
   * @returns {void}
   */
  function iniciarEdicion(bloque) {
    if (guardando) return
    setModo('editar')
    setIdEdicion(bloque.id_bloque_entrevista)
    setFormulario(datosFormulario(bloque))
    setErrorAccion('')
    setAviso('')
  }

  /**
   * Cierra la edición local cuando no hay una escritura en curso.
   * @returns {void}
   */
  function cancelarFormulario() {
    if (guardando) return
    setModo(null)
    setIdEdicion(null)
    setErrorAccion('')
  }

  /**
   * Valida horario, capacidad y restricciones de reservas antes de confirmar.
   * En edición envía solo campos diferentes; la capacidad debe cubrir todas las
   * reservas recibidas. La respuesta debe identificar el bloque para recargar la agenda.
   * @param {import('react').FormEvent<HTMLFormElement>} evento Envío del formulario.
   * @returns {Promise<void>} Finalización de la escritura con errores en el formulario.
   */
  async function guardar(evento) {
    evento.preventDefault()
    if (guardando || cargando || !modo) return

    const capacidad = Number(formulario.capacidad)
    const bloqueOriginal = bloques.find(
      (bloque) => String(bloque.id_bloque_entrevista) === String(idEdicion),
    )
    const reservas = reservasDe(bloqueOriginal).length

    if (!formulario.fecha || !formulario.hora_inicio || !formulario.hora_fin) {
      setErrorAccion('Debes completar fecha y horario.')
      return
    }
    if (formulario.hora_inicio >= formulario.hora_fin) {
      setErrorAccion('La hora de término debe ser posterior a la hora de inicio.')
      return
    }
    if (!Number.isInteger(capacidad) || capacidad < 1 || capacidad < reservas) {
      setErrorAccion('La capacidad debe ser un entero positivo y cubrir las reservas registradas.')
      return
    }
    if (!['DISPONIBLE', 'DESHABILITADO'].includes(formulario.estado)) {
      setErrorAccion('El estado del bloque no es válido.')
      return
    }
    if (modo === 'editar' && reservas > 0 && formulario.estado === 'DESHABILITADO') {
      setErrorAccion('No se puede deshabilitar un bloque con entrevistas reservadas.')
      return
    }
    if (modo === 'editar' && !bloqueOriginal) {
      setErrorAccion('El bloque seleccionado no está disponible. Actualiza la agenda.')
      return
    }

    const datos = {
      fecha: formulario.fecha,
      hora_inicio: formulario.hora_inicio,
      hora_fin: formulario.hora_fin,
      capacidad,
      estado: formulario.estado,
    }

    if (modo === 'editar') {
      const actuales = datosFormulario(bloqueOriginal)
      if (reservas > 0 && (
        datos.fecha !== actuales.fecha ||
        datos.hora_inicio !== actuales.hora_inicio ||
        datos.hora_fin !== actuales.hora_fin
      )) {
        setErrorAccion('No se puede cambiar el horario de un bloque con entrevistas reservadas.')
        return
      }

      const cambios = Object.fromEntries(
        Object.entries(datos).filter(([campo, valor]) =>
          String(valor) !== String(actuales[campo]),
        ),
      )
      if (Object.keys(cambios).length === 0) {
        setErrorAccion('No hay cambios que guardar.')
        return
      }
      Object.keys(datos).forEach((clave) => {
        if (!(clave in cambios)) delete datos[clave]
      })
    }

    const operacion = modo === 'crear' ? 'crear' : 'modificar'
    if (!window.confirm(
      `¿Confirmas ${operacion} este bloque de entrevista? Esta acción guardará cambios reales en SKILLY.`,
    )) return

    setGuardando(true)
    onProcesandoChange?.(true)
    setErrorAccion('')
    setAviso('')

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })
      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))
      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad CSRF.')
      }

      const ruta = modo === 'crear'
        ? RUTA_BLOQUES
        : `${RUTA_BLOQUES}${encodeURIComponent(idEdicion)}/`
      const respuesta = await fetch(ruta, {
        method: modo === 'crear' ? 'POST' : 'PATCH',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfDatos.csrfToken,
        },
        body: JSON.stringify(datos),
      })
      const resultado = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) {
        throw new Error(mensajeError(resultado, respuesta.status))
      }
      if (!resultado.bloque?.id_bloque_entrevista) {
        throw new Error('La respuesta no confirma el bloque. Actualiza la agenda antes de intentar nuevamente.')
      }

      setModo(null)
      setIdEdicion(null)
      setAviso(resultado.mensaje || 'Bloque guardado correctamente.')
      setRevision((anterior) => anterior + 1)
    } catch (fallo) {
      setErrorAccion(fallo instanceof Error ? fallo.message : 'No se pudo guardar el bloque.')
    } finally {
      setGuardando(false)
      onProcesandoChange?.(false)
    }
  }

  /**
   * Registra la confirmación de un contacto que administración ya realizó.
   * Requiere confirmación del usuario y del servidor antes de recargar la agenda.
   * @param {Object} reserva Reserva con el identificador de entrevista.
   * @returns {Promise<void>} Finalización del registro con errores visibles.
   */
  async function marcarContactado(reserva) {
    if (guardando) return
    if (!window.confirm(`¿Confirmas que SKILLY ya contactó al profesional de la entrevista #${reserva.id_entrevista}?`)) return
    setGuardando(true)
    onProcesandoChange?.(true)
    setAviso('')
    setErrorAccion('')
    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        method: 'GET', credentials: 'same-origin', cache: 'no-store',
        headers: { Accept: 'application/json' },
      })
      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))
      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad CSRF.')
      }
      const respuesta = await fetch(
        `${RUTA_AGENDA}${encodeURIComponent(reserva.id_entrevista)}/contacto/`,
        {
          method: 'POST', credentials: 'same-origin',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfDatos.csrfToken },
          body: JSON.stringify({ confirmar: true }),
        },
      )
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok || !datos.contactado) {
        throw new Error(mensajeError(datos, respuesta.status))
      }
      setAviso(datos.mensaje || 'Contacto confirmado.')
      setRevision((anterior) => anterior + 1)
    } catch (fallo) {
      setErrorAccion(fallo instanceof Error ? fallo.message : 'No se pudo registrar el contacto.')
    } finally {
      setGuardando(false)
      onProcesandoChange?.(false)
    }
  }

  const bloqueEditado = bloques.find(
    (bloque) => String(bloque.id_bloque_entrevista) === String(idEdicion),
  )
  const tieneReservas = modo === 'editar' && reservasDe(bloqueEditado).length > 0

  return (
    <section className="va-panel" aria-label="Agenda de entrevistas de validación">
      <div className="va-panel-titulo">
        <div>
          <h2>Agenda de entrevistas de validación</h2>
          <p className="va-descripcion">
            Consulta bloques, cupos y entrevistas registradas. La creación y modificación
            requiere confirmación administrativa.
          </p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 9 }}>
          <button type="button" disabled={cargando || guardando} onClick={() => setRevision((valor) => valor + 1)}>
            {cargando ? 'Consultando...' : '↻ Actualizar agenda'}
          </button>
          <button type="button" disabled={guardando} onClick={iniciarCreacion}>
            + Crear bloque
          </button>
        </div>
      </div>

      {cargando && <p role="status">Consultando agenda administrativa...</p>}
      {error && <p className="va-error" role="alert">{error}</p>}
      {aviso && <p role="status" style={{ color: '#315c50', fontWeight: 700 }}>{aviso}</p>}
      {!cargando && !error && bloques.length === 0 && (
        <p>No hay bloques de entrevistas registrados.</p>
      )}

      {!cargando && !error && bloques.length > 0 && (
        <div className="va-lista" style={{ marginTop: 18 }}>
          {bloques.map((bloque) => {
            // Calcula la ocupación sin contar entrevistas canceladas.
            const reservas = reservasDe(bloque)
            const reservasVigentes = reservas.filter((item) => item.estado !== 'CANCELADA')
            const capacidad = Number(bloque.capacidad) || 0
            return (
              <article className="va-item" key={bloque.id_bloque_entrevista}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <h3>Bloque #{bloque.id_bloque_entrevista}</h3>
                  <p><strong>Fecha:</strong> {mostrarFecha(bloque.fecha)}</p>
                  <p><strong>Horario:</strong> {mostrarHora(bloque.hora_inicio)} – {mostrarHora(bloque.hora_fin)}</p>
                  <p><strong>Disponibilidad:</strong> {bloque.disponibilidad || (bloque.estado === "DISPONIBLE" && reservasVigentes.length >= capacidad ? "COMPLETO" : bloque.estado)}</p>
                  <p><strong>Gestor:</strong> #{bloque.id_usuario_gestor ?? 'No asignado'}</p>
                  <p><strong>Reservas vigentes:</strong> {reservasVigentes.length} de {capacidad} · Cupos disponibles: {Math.max(0, capacidad - reservasVigentes.length)}</p>
                  {reservas.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <strong>Entrevistas registradas</strong>
                      <div style={{ display: 'grid', gap: 7, marginTop: 8 }}>
                        {reservas.map((reserva) => (
                          <div key={reserva.id_entrevista} style={{ borderLeft: '3px solid #8ab29d', paddingLeft: 10 }}>
                            <span>Entrevista #{reserva.id_entrevista}</span>
                            {' · '}Validación #{reserva.id_validacion}
                            {' · '}{reserva.estado}
                            {reserva.fecha_reserva && (
                              <span> · Reservada: {String(reserva.fecha_reserva).slice(0, 16).replace('T', ' ')}</span>
                            )}
                            {reserva.estado === 'AGENDADA' && (
                              <div style={{ marginTop: 7 }}>
                                {reserva.contactado ? (
                                  <p style={{ color: '#315c50', fontWeight: 700 }}>✓ Contactado · Entrevista agendada</p>
                                ) : (
                                  <>
                                    <p>Contacto pendiente: contactar al profesional por correo o teléfono para entregarle las instrucciones previas a su entrevista.</p>
                                    <button type="button" disabled={guardando} onClick={() => marcarContactado(reserva)}>
                                      Marcar como contactado
                                    </button>
                                  </>
                                )}
                              </div>
                            )}
                            {reserva.observacion && <p>Observación: {reserva.observacion}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <button type="button" disabled={guardando} onClick={() => iniciarEdicion(bloque)}>
                  Modificar bloque
                </button>
              </article>
            )
          })}
        </div>
      )}

      {modo && (
        <form onSubmit={guardar} className="va-panel" style={{ background: '#f8fbf9' }}>
          <h3>{modo === 'crear' ? 'Crear bloque de entrevista' : `Modificar bloque #${idEdicion}`}</h3>
          {tieneReservas && (
            <p className="va-nota">
              Este bloque ya tiene entrevistas. Su fecha y horario no pueden modificarse;
              la capacidad tampoco puede ser inferior a las reservas.
            </p>
          )}
          <div style={estiloGrilla}>
            <label style={{ display: 'grid', gap: 7 }} htmlFor="ea-fecha">
              Fecha
              <input id="ea-fecha" type="date" required style={estiloCampos} value={formulario.fecha}
                disabled={guardando || tieneReservas} onChange={(evento) => actualizarCampo('fecha', evento.target.value)} />
            </label>
            <label style={{ display: 'grid', gap: 7 }} htmlFor="ea-inicio">
              Hora de inicio
              <input id="ea-inicio" type="time" required style={estiloCampos} value={formulario.hora_inicio}
                disabled={guardando || tieneReservas} onChange={(evento) => actualizarCampo('hora_inicio', evento.target.value)} />
            </label>
            <label style={{ display: 'grid', gap: 7 }} htmlFor="ea-fin">
              Hora de término
              <input id="ea-fin" type="time" required style={estiloCampos} value={formulario.hora_fin}
                disabled={guardando || tieneReservas} onChange={(evento) => actualizarCampo('hora_fin', evento.target.value)} />
            </label>
            <label style={{ display: 'grid', gap: 7 }} htmlFor="ea-capacidad">
              Capacidad
              <input id="ea-capacidad" type="number" min={Math.max(1, reservasDe(bloqueEditado).length)} step="1" required
                style={estiloCampos} value={formulario.capacidad} disabled={guardando}
                onChange={(evento) => actualizarCampo('capacidad', evento.target.value)} />
            </label>
            <label style={{ display: 'grid', gap: 7 }} htmlFor="ea-estado">
              Estado
              <select id="ea-estado" style={estiloCampos} value={formulario.estado} disabled={guardando}
                onChange={(evento) => actualizarCampo('estado', evento.target.value)}>
                <option value="DISPONIBLE">DISPONIBLE</option>
                <option value="DESHABILITADO" disabled={tieneReservas}>DESHABILITADO</option>
              </select>
            </label>
          </div>

          {errorAccion && <p className="va-error" role="alert">{errorAccion}</p>}
          <p className="va-nota">
            Guardar ejecutará una operación real en PostgreSQL. Por ahora puedes revisar
            la agenda sin crear ni modificar registros.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <button type="submit" disabled={guardando}>
              {guardando ? 'Guardando...' : modo === 'crear' ? 'Confirmar creación' : 'Guardar modificaciones'}
            </button>
            <button type="button" disabled={guardando} onClick={cancelarFormulario}>Cancelar</button>
          </div>
        </form>
      )}
    </section>
  )
}
