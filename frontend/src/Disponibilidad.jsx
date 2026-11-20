
import { useEffect, useState } from 'react'
import './Disponibilidad.css'

const API = '/api/solicitudes/mi-disponibilidad/'

const vacio = {
  fecha: '',
  hora_inicio: '',
  hora_fin: '',
}

/**
 * Lee y decodifica una cookie accesible desde el navegador.
 * @param {string} nombre Nombre exacto de la cookie.
 * @returns {string} Valor decodificado o cadena vacía si falta.
 * @throws {URIError} Si el valor contiene una codificación porcentual inválida.
 */
function leerCookie(nombre) {
  const valor = document.cookie
    .split('; ')
    .find((parte) => parte.startsWith(`${nombre}=`))
  return valor ? decodeURIComponent(valor.slice(nombre.length + 1)) : ''
}

/**
 * Compone el mensaje de rechazo de un bloque desde la respuesta de la API.
 * @param {Object|null} datos Cuerpo JSON del servidor.
 * @param {number} estado Código HTTP de respaldo.
 * @returns {string} Mensaje general o errores por campo.
 */
function mensajeError(datos, estado) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const mensajes = Object.entries(datos).map(([campo, valor]) => {
      // Reúne los mensajes del servidor para explicar por qué se rechazó el bloque.
      const texto = Array.isArray(valor)
        ? valor.join(', ')
        : typeof valor === 'string'
          ? valor
          : JSON.stringify(valor)
      return `${campo}: ${texto}`
    })
    if (mensajes.length) return mensajes.join(' | ')
  }

  return `La operación no se completó (HTTP ${estado}).`
}

/**
 * Consulta disponibilidad y usa la cookie CSRF existente cuando el método indicado no es GET.
 * @param {string} url Endpoint solicitado.
 * @param {RequestInit} [opciones={}] Opciones fetch y cabeceras que prevalecen sobre las predeterminadas.
 * @returns {Promise<Object>} JSON recibido o un objeto vacío si no puede leerse.
 * @throws {Error} Ante fallo de red o HTTP; los errores HTTP incorporan la propiedad estado.
 */
async function peticion(url, opciones = {}) {
  const csrf = leerCookie('csrftoken')
  const headers = {
    Accept: 'application/json',
    ...(opciones.body ? { 'Content-Type': 'application/json' } : {}),
    ...(csrf && opciones.method && opciones.method !== 'GET'
      ? { 'X-CSRFToken': csrf }
      : {}),
    ...opciones.headers,
  }

  const respuesta = await fetch(url, {
    credentials: 'same-origin',
    cache: 'no-store',
    ...opciones,
    headers,
  })

  const datos = await respuesta.json().catch(() => ({}))

  if (!respuesta.ok) {
    const error = new Error(mensajeError(datos, respuesta.status))
    error.estado = respuesta.status
    throw error
  }

  return datos
}

/**
 * Extrae los primeros cinco caracteres de una hora textual sin validarla.
 * @param {*} valor Hora recibida de la API.
 * @returns {string} Texto HH:mm esperado o cadena vacía si no es string.
 */
function horaCorta(valor) {
  return typeof valor === 'string' ? valor.slice(0, 5) : ''
}

/**
 * Reordena una fecha textual para mostrarla sin conversión de zona horaria.
 * @param {*} valor Fecha cuyo prefijo se espera en formato YYYY-MM-DD.
 * @returns {string} Día/mes/año, texto original si no tiene tres partes o guion si falta.
 */
function fechaVisible(valor) {
  if (!valor || typeof valor !== 'string') return '-'
  const partes = valor.slice(0, 10).split('-')
  return partes.length === 3
    ? `${partes[2]}/${partes[1]}/${partes[0]}`
    : valor
}

/**
 * Determina si la reserva comunicada impide editar el bloque en la interfaz.
 * @param {Object} bloque Registro con reserva_actual opcional.
 * @returns {boolean} True para PENDIENTE_PAGO o ACTIVA; el servidor revalida la ocupación.
 */
function tieneReservaVigente(bloque) {
  return ['PENDIENTE_PAGO', 'ACTIVA'].includes(bloque.reserva_actual?.estado)
}

/**
 * Consulta y gestiona los bloques propios con validaciones locales complementarias al servidor.
 * Refresca reservas al recuperar foco y cada quince segundos mientras el documento está visible.
 * @returns {import('react').ReactElement} Agenda editable y controles de sesión.
 */
function Disponibilidad() {
  const [bloques, setBloques] = useState([])
  const [formulario, setFormulario] = useState(vacio)
  const [editando, setEditando] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')
  const [sinAcceso, setSinAcceso] = useState(false)

  /**
   * Recarga la disponibilidad y distingue errores de acceso 401/403 de otros fallos.
   * @returns {Promise<void>} Sustituye el listado o lo vacía si falla la consulta.
   */
  async function cargar() {
    setCargando(true)
    setError('')
    setExito('')

    try {
      const datos = await peticion(API)
      if (!Array.isArray(datos.disponibilidad)) {
        throw new Error('Django devolvió una lista inesperada.')
      }
      setBloques(datos.disponibilidad)
      setSinAcceso(false)
    } catch (fallo) {
      setBloques([])
      if (fallo.estado === 401 || fallo.estado === 403) {
        setSinAcceso(true)
        setError(
          'Esta sección requiere una sesión activa de profesional Skilly.',
        )
      } else {
        setError(fallo.message)
      }
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    // Sincroniza la disponibilidad inicial mientras la vista permanece activa.
    let activo = true

    /**
     * Carga la disponibilidad inicial y evita aplicar resultados cuando el efecto ya se limpió.
     * @returns {Promise<void>} Actualiza bloques, acceso y estado de carga.
     */
    async function iniciar() {
      try {
        const datos = await peticion(API)
        if (!activo) return
        if (!Array.isArray(datos.disponibilidad)) {
          throw new Error('Respuesta de disponibilidad inesperada.')
        }
        setBloques(datos.disponibilidad)
      } catch (fallo) {
        if (!activo) return
        setError(
          fallo.estado === 401 || fallo.estado === 403
            ? 'Esta sección requiere una sesión activa de profesional Skilly.'
            : fallo.message,
        )
        setSinAcceso(fallo.estado === 401 || fallo.estado === 403)
      } finally {
        if (activo) setCargando(false)
      }
    }

    iniciar()
    return () => { activo = false }
  }, [])


  // Sincroniza las reservas hechas desde otra pestaña o sesión.
  useEffect(() => {
    /**
     * Refresca los bloques únicamente si el documento es visible, sin mostrar fallos de esa consulta.
     * @returns {void} Inicia la petición sin esperar su resolución.
     */
    const refrescarAlVolver = () => {
      if (document.visibilityState === 'visible') {
        void peticion(API).then((datos) => {
          if (Array.isArray(datos.disponibilidad)) setBloques(datos.disponibilidad)
        }).catch(() => {})
      }
    }
    document.addEventListener('visibilitychange', refrescarAlVolver)
    window.addEventListener('focus', refrescarAlVolver)
    const intervalo = window.setInterval(refrescarAlVolver, 15000)
    return () => {
      document.removeEventListener('visibilitychange', refrescarAlVolver)
      window.removeEventListener('focus', refrescarAlVolver)
      window.clearInterval(intervalo)
    }
  }, [])

  /**
   * Obtiene un token CSRF nuevo, solicita cerrar sesión y navega al acceso tras confirmar el servidor.
   * @returns {Promise<void>} Conserva la pantalla y presenta un error si el cierre falla.
   */
  async function cerrarSesion() {
    setError('')
    setExito('')

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
      })

      const csrfDatos = await csrfRespuesta.json()

      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }

      const respuesta = await fetch('/api/acceso/cerrar-sesion/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfDatos.csrfToken,
        },
        body: JSON.stringify({}),
      })

      if (!respuesta.ok) {
        throw new Error('No se pudo cerrar la sesión.')
      }

      window.location.assign('/acceso-profesional')
    } catch (fallo) {
      setError(fallo.message)
    }
  }

  /**
   * Copia name y value del control al formulario de horario.
   * @param {import('react').ChangeEvent<HTMLInputElement>} evento Cambio del campo.
   * @returns {void}
   */
  function cambiar(evento) {
    const { name, value } = evento.target
    setFormulario((actual) => ({ ...actual, [name]: value }))
  }

  /**
   * Prepara la edición solo para bloques DISPONIBLE sin reserva pendiente o activa comunicada.
   * @param {Object} bloque Bloque seleccionado con identificador, fecha, horas y estado.
   * @returns {void} En caso admisible, desplaza la pantalla hacia el formulario.
   */
  function comenzarEdicion(bloque) {
    if (bloque.estado !== 'DISPONIBLE' || tieneReservaVigente(bloque)) return
    setEditando(bloque.id_disponibilidad)
    setFormulario({
      fecha: bloque.fecha,
      hora_inicio: horaCorta(bloque.hora_inicio),
      hora_fin: horaCorta(bloque.hora_fin),
    })
    setError('')
    setExito('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  /**
   * Abandona la edición local sin enviar modificaciones al servidor.
   * @returns {void} Limpia el identificador, formulario y error.
   */
  function cancelarEdicion() {
    setEditando(null)
    setFormulario(vacio)
    setError('')
  }

  /**
   * Crea por POST o actualiza por PATCH tras validar orden de horas y fecha local no pasada.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Recarga el listado al guardar; el backend decide disponibilidad y cruces.
   */
  async function guardar(evento) {
    evento.preventDefault()
    if (guardando || sinAcceso) return

    setError('')
    setExito('')

    if (formulario.hora_inicio >= formulario.hora_fin) {
      setError(
        'La hora de término debe ser posterior a la de inicio.',
      )
      return
    }

    const hoy = new Date()
    const fechaLocal = [
      hoy.getFullYear(),
      String(hoy.getMonth() + 1).padStart(2, '0'),
      String(hoy.getDate()).padStart(2, '0'),
    ].join('-')

    if (formulario.fecha < fechaLocal) {
      setError('No puedes publicar bloques en fechas pasadas.')
      return
    }

    setGuardando(true)

    try {
      const datos = await peticion(
        editando ? `${API}${editando}/` : API,
        {
          method: editando ? 'PATCH' : 'POST',
          body: JSON.stringify(formulario),
        },
      )

      const accion = editando ? 'actualizado' : 'creado'
      setEditando(null)
      setFormulario(vacio)
      await cargar()
      setExito(
        datos.mensaje || `Bloque ${accion} correctamente.`,
      )
    } catch (fallo) {
      if (fallo.estado === 401 || fallo.estado === 403) {
        setSinAcceso(true)
      }
      setError(fallo.message)
    } finally {
      setGuardando(false)
    }
  }

  /**
   * Confirma y solicita eliminar un bloque disponible sin reserva vigente informada.
   * @param {Object} bloque Bloque con identificador, horario y estado.
   * @returns {Promise<void>} Recarga los bloques o presenta el rechazo del servidor.
   */
  async function eliminar(bloque) {
    if (guardando || sinAcceso || bloque.estado !== 'DISPONIBLE' || tieneReservaVigente(bloque)) return

    const confirmado = window.confirm(
      `¿Eliminar el bloque del ${fechaVisible(bloque.fecha)} ` +
      `de ${horaCorta(bloque.hora_inicio)} a ${horaCorta(bloque.hora_fin)}?`,
    )

    if (!confirmado) return

    setGuardando(true)
    setError('')
    setExito('')

    try {
      const datos = await peticion(
        `${API}${bloque.id_disponibilidad}/`,
        { method: 'DELETE' },
      )
      await cargar()
      setExito(datos.mensaje || 'Bloque eliminado correctamente.')
      if (editando === bloque.id_disponibilidad) cancelarEdicion()
    } catch (fallo) {
      setError(fallo.message)
      if (fallo.estado === 401 || fallo.estado === 403) {
        setSinAcceso(true)
      }
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="dp-pagina">
      <header className="dp-cabecera">
        <a href="/portal-profesional" className="dp-volver-portal">Volver al portal profesional</a>
        <a href="/" className="dp-marca">
          <svg width="25" height="25" viewBox="0 0 24 24"
            fill="none" aria-hidden="true">
            <path
              d="M12 1L14.7 9.3L23 12L14.7 14.7L12 23L9.3 14.7L1 12L9.3 9.3L12 1Z"
              fill="#447D69"
            />
          </svg>
          SKILLY
        </a>
        <div className="dp-navegacion"><a href="/#marketplace">Volver al marketplace</a>
<button type="button" className="dp-secundario" onClick={cerrarSesion} disabled={sinAcceso}>Cerrar sesión</button></div>
      </header>

      <main className="dp-contenido">
        <div className="dp-intro">
          <span className="dp-etiqueta">ESPACIO PROFESIONAL</span>
          <h1>Mi disponibilidad</h1>
          <a href="/portal-profesional" className="dp-volver-portal">← Volver a mi portal profesional</a>
          <p>
            Organiza los bloques de fecha y hora para las primeras
            reuniones de tus servicios publicados.
          </p>
        </div>

        {error && <div className="dp-error" role="alert">{error}</div>}
        {exito && <div className="dp-exito" role="status">{exito}</div>}

        {sinAcceso ? (
          <section className="dp-tarjeta">
            <h2>Acceso profesional requerido</h2>
            <p>
              Necesitas iniciar sesión como profesional de Skilly.
              La administración de horarios no es pública.
            </p>
            <a href="/acceso-profesional" className="dp-enlace-acceso">Ir al inicio de sesión profesional</a>
            <button type="button" onClick={cargar}>
              Comprobar mi sesión
            </button>
          </section>
        ) : (
          <>
            <section className="dp-tarjeta">
              <div className="dp-seccion">
                <div>
                  <span className="dp-etiqueta">GESTIÓN DE BLOQUES</span>
                  <h2>
                    {editando
                      ? 'Editar disponibilidad'
                      : 'Publicar nuevo bloque'}
                  </h2>
                </div>
                {editando && (
                  <button className="dp-secundario" type="button"
                    onClick={cancelarEdicion} disabled={guardando}>
                    Cancelar edición
                  </button>
                )}
              </div>

              <form className="dp-formulario" onSubmit={guardar}>
                <label>
                  Fecha
                  <input type="date" name="fecha"
                    value={formulario.fecha} onChange={cambiar}
                    required disabled={cargando || guardando} />
                </label>
                <label>
                  Hora de inicio
                  <input type="time" name="hora_inicio"
                    value={formulario.hora_inicio} onChange={cambiar}
                    required disabled={cargando || guardando} />
                </label>
                <label>
                  Hora de término
                  <input type="time" name="hora_fin"
                    value={formulario.hora_fin} onChange={cambiar}
                    required disabled={cargando || guardando} />
                </label>
                <button type="submit" disabled={cargando || guardando}>
                  {guardando
                    ? 'Guardando...'
                    : editando
                      ? 'Guardar cambios'
                      : 'Crear bloque'}
                </button>
              </form>
              <p className="dp-nota">
                Django validará fechas, superposiciones y disponibilidad.
                Los bloques reservados no se pueden editar ni eliminar.
              </p>
            </section>

            <section className="dp-tarjeta">
              <div className="dp-seccion">
                <div>
                  <span className="dp-etiqueta">MIS HORARIOS</span>
                  <h2>Bloques registrados</h2>
                </div>
                <button type="button" className="dp-secundario"
                  onClick={cargar} disabled={cargando || guardando}>
                  ↻ Recargar bloques
                </button>
              </div>

              {cargando ? (
                <p>Cargando horarios...</p>
              ) : bloques.length === 0 ? (
                <p>
                  Todavía no tienes bloques registrados.
                  Publica el primero cuando estés listo.
                </p>
              ) : (
                <div className="dp-lista">
                  {bloques.map((bloque) => {
                    // Considera la reserva vigente antes de habilitar acciones del bloque.
                    const reservado = tieneReservaVigente(bloque)
                    const disponible = bloque.estado === 'DISPONIBLE' && !reservado
                    return (
                      <article className="dp-bloque"
                        key={bloque.id_disponibilidad}>
                        <div>
                          <strong>{fechaVisible(bloque.fecha)}</strong>
                          <p>
                            {horaCorta(bloque.hora_inicio)} a{' '}
                            {horaCorta(bloque.hora_fin)}
                          </p>
                          <span className={
                            disponible
                              ? 'dp-estado dp-disponible'
                              : 'dp-estado dp-reservado'
                          }>
                            {reservado ? 'RESERVADO' : bloque.estado}
                          </span>
                          {bloque.reserva_actual && (
                            <p className="dp-reserva">
                              {reservado && bloque.reserva_actual.estado === 'PENDIENTE_PAGO'
                                ? 'Pendiente de pago'
                                : `Reserva: ${bloque.reserva_actual.estado}`}
                            </p>
                          )}
                        </div>

                        {disponible && (
                        <div className="dp-acciones">
                          <button type="button"
                            className="dp-secundario"
                            onClick={() => comenzarEdicion(bloque)}
                            disabled={!disponible || guardando}>
                            Editar
                          </button>
                          <button type="button"
                            className="dp-eliminar"
                            onClick={() => eliminar(bloque)}
                            disabled={!disponible || guardando}>
                            Eliminar
                          </button>
                        </div>
                        )}
                      </article>
                    )
                  })}
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  )
}

export default Disponibilidad
