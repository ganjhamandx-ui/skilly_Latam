
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import AdminNavegacion from './AdminNavegacion.jsx'
import './Administracion.css'

const API = '/api/retroalimentacion/administracion/'

// Presenta la fecha almacenada en un formato adecuado para la ficha.
function fecha(valor) {
  if (!valor) return 'No registrada'

  const dato = new Date(valor)

  if (Number.isNaN(dato.getTime())) {
    return 'No disponible'
  }

  return dato.toLocaleString('es-CL', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

// Extrae el mensaje devuelto por el backend para presentarlo en el panel.
function mensajeApi(datos, codigo) {
  if (typeof datos?.mensaje === 'string') {
    return datos.mensaje
  }

  if (typeof datos?.detail === 'string') {
    return datos.detail
  }

  if (datos && typeof datos === 'object') {
    const mensajes = Object.entries(datos).map(
      ([campo, valor]) => {
        const contenido = Array.isArray(valor)
          ? valor.join(', ')
          : String(valor)

        return `${campo}: ${contenido}`
      },
    )

    if (mensajes.length) return mensajes.join(' | ')
  }

  return `No se pudo completar la operación (HTTP ${codigo}).`
}

// Obtiene el token CSRF que exige una acción autenticada de administración.
async function csrfToken() {
  const respuesta = await fetch('/api/acceso/csrf/', {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })

  const datos = await respuesta.json().catch(() => ({}))

  if (!respuesta.ok || !datos.csrfToken) {
    throw new Error(
      'No fue posible obtener el token de seguridad CSRF.',
    )
  }

  return datos.csrfToken
}

// Coordina la revisión administrativa de evaluaciones y recomendaciones.
export default function RetroalimentacionAdministracion() {
  const [registros, setRegistros] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [versionLista, setVersionLista] = useState(0)
  const [busqueda, setBusqueda] = useState('')

  const [idSeleccionado, setIdSeleccionado] = useState(null)
  const [detalle, setDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [errorDetalle, setErrorDetalle] = useState('')
  const [avisoDetalle, setAvisoDetalle] = useState('')
  const [versionDetalle, setVersionDetalle] = useState(0)

  const [creando, setCreando] = useState(false)
  const [titulo, setTitulo] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [guardando, setGuardando] = useState(false)

  // Consulta privada disponible solo para administradores.
  useEffect(() => {
    // Carga las evaluaciones según los filtros activos del panel.
    let vigente = true

    // Carga las filas que corresponden a los filtros activos del panel.
    async function consultarLista() {
      try {
        const respuesta = await fetch(API, {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        })

        const datos = await respuesta
          .json()
          .catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(
            mensajeApi(datos, respuesta.status),
          )
        }

        if (!Array.isArray(datos.retroalimentaciones)) {
          throw new Error(
            'La API no devolvió una lista válida de retroalimentaciones.',
          )
        }

        if (vigente) {
          setRegistros(datos.retroalimentaciones)
          setError('')
        }
      } catch (fallo) {
        if (vigente) {
          setError(
            fallo.message ||
            'No se pudo consultar la bandeja.',
          )
        }
      } finally {
        if (vigente) setCargando(false)
      }
    }

    void consultarLista()

    return () => {
      vigente = false
    }
  }, [versionLista])

  // Detalle con recomendaciones relacionadas.
  useEffect(() => {
    // Busca el detalle al cambiar la evaluación seleccionada.
    if (idSeleccionado === null) return undefined

    let vigente = true

    // Carga la evaluación y sus antecedentes para el expediente seleccionado.
    async function consultarDetalle() {
      try {
        const respuesta = await fetch(
          `${API}${idSeleccionado}/`,
          {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: { Accept: 'application/json' },
          },
        )

        const datos = await respuesta
          .json()
          .catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(
            mensajeApi(datos, respuesta.status),
          )
        }

        if (
          !datos.retroalimentacion ||
          !Array.isArray(datos.recomendaciones)
        ) {
          throw new Error(
            'La API devolvió un detalle incompleto.',
          )
        }

        if (vigente) {
          setDetalle(datos)
          setErrorDetalle('')
        }
      } catch (fallo) {
        if (vigente) {
          setErrorDetalle(
            fallo.message ||
            'No se pudo abrir el detalle.',
          )
        }
      } finally {
        if (vigente) setCargandoDetalle(false)
      }
    }

    void consultarDetalle()

    return () => {
      vigente = false
    }
  }, [idSeleccionado, versionDetalle])

  // Bloqueo del desplazamiento al abrir una ventana.
  useEffect(() => {
    // Mantiene el fondo inmóvil durante la apertura del detalle.
    if (idSeleccionado === null) return undefined

    const anterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // Activa con teclado la interacción disponible en una fila.
    function alPresionar(evento) {
      if (evento.key === 'Escape' && !guardando) {
        setIdSeleccionado(null)
      }
    }

    document.addEventListener('keydown', alPresionar)

    return () => {
      document.body.style.overflow = anterior
      document.removeEventListener('keydown', alPresionar)
    }
  }, [idSeleccionado, guardando])

  // Refresca las filas del panel conservando sus filtros.
  function recargarLista() {
    setCargando(true)
    setError('')
    setVersionLista((actual) => actual + 1)
  }

  // Selecciona la evaluación y carga su detalle antes de mostrar el diálogo.
  function abrir(id) {
    setIdSeleccionado(id)
    setDetalle(null)
    setCargandoDetalle(true)
    setErrorDetalle('')
    setAvisoDetalle('')
    setCreando(false)
    setTitulo('')
    setDescripcion('')
  }

  // Limpia la evaluación seleccionada y cierra el diálogo.
  function cerrar() {
    if (!guardando) setIdSeleccionado(null)
  }

  // Vuelve a consultar el expediente abierto después de registrar una decisión.
  function refrescarDetalle() {
    setCargandoDetalle(true)
    setVersionDetalle((actual) => actual + 1)
  }

  // Registra una recomendación interna, sin comunicarla todavía.
  async function registrarRecomendacion(evento) {
    evento.preventDefault()

    const id = detalle?.retroalimentacion?.id_feedback
    const tituloLimpio = titulo.trim()
    const descripcionLimpia = descripcion.trim()

    if (guardando || !id) return

    if (
      !tituloLimpio ||
      tituloLimpio.length > 150 ||
      !descripcionLimpia
    ) {
      setErrorDetalle(
        'Indica un título de hasta 150 caracteres y una descripción.',
      )
      return
    }

    if (
      !window.confirm(
        '¿Confirmas registrar esta recomendación interna? No será comunicada al profesional todavía.',
      )
    ) {
      return
    }

    setGuardando(true)
    setErrorDetalle('')
    setAvisoDetalle('')

    try {
      const token = await csrfToken()

      const respuesta = await fetch(`${API}${id}/`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': token,
        },
        body: JSON.stringify({
          titulo: tituloLimpio,
          descripcion: descripcionLimpia,
        }),
      })

      const datos = await respuesta
        .json()
        .catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          mensajeApi(datos, respuesta.status),
        )
      }

      if (datos.recomendacion) {
        setDetalle((actual) => actual ? {
          ...actual,
          recomendaciones: [
            ...actual.recomendaciones,
            datos.recomendacion,
          ],
        } : actual)
      }

      setAvisoDetalle(
        datos.mensaje ||
        'Recomendación registrada correctamente.',
      )

      setCreando(false)
      setTitulo('')
      setDescripcion('')
      refrescarDetalle()
    } catch (fallo) {
      setErrorDetalle(
        fallo.message ||
        'No se pudo registrar la recomendación.',
      )
    } finally {
      setGuardando(false)
    }
  }

  // Comunica exclusivamente la recomendación al profesional.
  async function comunicarRecomendacion(recomendacion) {
    if (
      guardando ||
      recomendacion.estado !== 'REGISTRADA'
    ) {
      return
    }

    const confirmado = window.confirm(
      `¿Confirmas comunicar la recomendación #${recomendacion.id_recomendacion} al profesional?\n\n` +
      'Esta acción cambia su estado a COMUNICADA.',
    )

    if (!confirmado) return

    setGuardando(true)
    setErrorDetalle('')
    setAvisoDetalle('')

    try {
      const token = await csrfToken()

      const respuesta = await fetch(
        `${API}recomendaciones/${recomendacion.id_recomendacion}/comunicar/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'X-CSRFToken': token,
          },
        },
      )

      const datos = await respuesta
        .json()
        .catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          mensajeApi(datos, respuesta.status),
        )
      }

      if (datos.recomendacion) {
        setDetalle((actual) => actual ? {
          ...actual,
          recomendaciones: actual.recomendaciones.map(
            (elemento) =>
              elemento.id_recomendacion ===
              recomendacion.id_recomendacion
                ? datos.recomendacion
                : elemento,
          ),
        } : actual)
      }

      setAvisoDetalle(
        datos.mensaje ||
        'Recomendación comunicada correctamente.',
      )

      refrescarDetalle()
    } catch (fallo) {
      setErrorDetalle(
        fallo.message ||
        'No se pudo comunicar la recomendación.',
      )
    } finally {
      setGuardando(false)
    }
  }

  const filtrados = registros.filter((registro) => {
    // Aplica el término de búsqueda a los campos visibles de la ficha.
    const feedback = registro.retroalimentacion ?? {}
    const termino = busqueda.trim().toLowerCase()

    if (!termino) return true

    return [
      feedback.id_feedback,
      feedback.id_prestacion,
      registro.profesional?.id_profesional,
      feedback.estado,
      feedback.contenido,
    ].some((valor) =>
      String(valor ?? '')
        .toLowerCase()
        .includes(termino),
    )
  })

  const prestaciones = new Set(
    registros
      .map(
        (registro) =>
          registro.retroalimentacion?.id_prestacion,
      )
      .filter((valor) => valor != null),
  ).size

  const feedbackActual = detalle?.retroalimentacion
  const recomendaciones = detalle?.recomendaciones ?? []

  return (
    <div className="adm-pagina">
      <header className="adm-header">
        <a
          className="adm-logo"
          href="/administracion"
        >
          <span className="adm-estrella">✦</span>
          {' '}Skilly
        </a>

        <nav aria-label="Enlaces principales">
          <a href="/administracion">
            Administración
          </a>

          <a href="/">
            Marketplace
          </a>
        </nav>
      </header>

      <AdminNavegacion activo="retroalimentacion" />

      <main className="adm-contenedor">
        <div className="adm-intro">
          <span className="adm-eyebrow">
            BACK-OFFICE · RETROALIMENTACIÓN PRIVADA
          </span>

          <h1>Retroalimentación administrativa</h1>

          <p>
            Revisa comentarios privados de empresas
            y gestiona recomendaciones de desarrollo
            para profesionales.
          </p>
        </div>

        <section className="adm-panel">
          <div className="adm-panel-header">
            <h2>Resumen de retroalimentaciones</h2>

            <button
              className="adm-secundario"
              type="button"
              disabled={cargando}
              onClick={recargarLista}
            >
              {cargando
                ? 'Consultando…'
                : '↻ Recargar información'}
            </button>
          </div>

          {error && (
            <p className="adm-error" role="alert">
              {error}
            </p>
          )}

          {cargando && (
            <p role="status">
              Consultando registros privados…
            </p>
          )}

          <div
            className="adm-resumen"
            style={{
              gridTemplateColumns:
                'repeat(auto-fit, minmax(180px, 1fr))',
            }}
          >
            <div>
              <span>Total de comentarios</span>
              <strong>{registros.length}</strong>
            </div>

            <div>
              <span>Prestaciones relacionadas</span>
              <strong>{prestaciones}</strong>
            </div>

            <div>
              <span>Visibilidad</span>
              <strong style={{ fontSize: 22 }}>
                PRIVADA
              </strong>
            </div>
          </div>
        </section>

        <section className="adm-panel">
          <h2>Bandeja de retroalimentación</h2>

          <p className="adm-nota">
            Los comentarios originales solo se
            consultan en administración. El profesional
            recibe únicamente las recomendaciones que
            Skilly decide comunicar.
          </p>

          <label
            htmlFor="feedback-busqueda"
            style={{
              display: 'block',
              margin: '20px 0 8px',
            }}
          >
            Buscar por comentario, prestación,
            profesional o estado
          </label>

          <input
            id="feedback-busqueda"
            className="adm-busqueda"
            type="search"
            value={busqueda}
            onChange={(evento) =>
              setBusqueda(evento.target.value)
            }
            placeholder="Ej.: prestación 1 o comentario"
          />

          {!cargando &&
            !error &&
            filtrados.length === 0 && (
              <p className="adm-vacio">
                No hay retroalimentaciones para
                esta búsqueda.
              </p>
            )}

          <div className="adm-lista">
            {filtrados.map((registro) => {
              // Omite registros que no incluyen una evaluación para presentar.
              const feedback = registro.retroalimentacion

              if (!feedback) return null

              return (
                <button
                  className="adm-item"
                  type="button"
                  key={feedback.id_feedback}
                  onClick={() =>
                    abrir(feedback.id_feedback)
                  }
                  style={{
                    width: '100%',
                    font: 'inherit',
                  }}
                >
                  <span className="adm-item-cuerpo">
                    <strong>
                      Retroalimentación
                      {' #'}{feedback.id_feedback}
                    </strong>

                    <small>
                      Prestación
                      {' #'}{feedback.id_prestacion}
                      {' · '}
                      Profesional
                      {' #'}
                      {registro.profesional?.id_profesional ?? '—'}
                      {' · '}
                      {fecha(feedback.fecha_registro)}
                    </small>

                    <small>
                      {feedback.contenido}
                    </small>
                  </span>

                  <span className="adm-estado">
                    {feedback.estado} →
                  </span>
                </button>
              )
            })}
          </div>
        </section>
      </main>

      {idSeleccionado !== null && createPortal(
        <div
          role="presentation"
          onMouseDown={(evento) => {
            if (
              evento.target === evento.currentTarget
            ) {
              cerrar()
            }
          }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 2100,
            background: 'rgba(11,30,25,.75)',
            display: 'grid',
            placeItems: 'center',
            padding: 18,
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="feedback-titulo"
            style={{
              width: 'min(760px, 100%)',
              maxHeight: '88vh',
              overflowY: 'auto',
              background: '#fff',
              color: '#203a38',
              borderRadius: 22,
              padding: 26,
            }}
          >
            <div className="adm-panel-header">
              <h2 id="feedback-titulo">
                Retroalimentación #{idSeleccionado}
              </h2>

              <button
                type="button"
                className="adm-secundario"
                onClick={cerrar}
                disabled={guardando}
              >
                ✕ Cerrar
              </button>
            </div>

            {cargandoDetalle && (
              <p role="status">
                Actualizando detalle…
              </p>
            )}

            {errorDetalle && (
              <p
                className="adm-error"
                role="alert"
              >
                {errorDetalle}
              </p>
            )}

            {avisoDetalle && (
              <p
                className="adm-aviso"
                role="status"
              >
                {avisoDetalle}
              </p>
            )}

            {feedbackActual && (
              <>
                <div className="adm-datos">
                  <div>
                    <small>Estado</small>
                    <strong>
                      {feedbackActual.estado}
                    </strong>
                  </div>

                  <div>
                    <small>Visibilidad</small>
                    <strong>
                      {feedbackActual.visibilidad}
                    </strong>
                  </div>

                  <div>
                    <small>Prestación</small>
                    <strong>
                      #{feedbackActual.id_prestacion}
                    </strong>
                  </div>

                  <div>
                    <small>Profesional</small>
                    <strong>
                      #
                      {detalle.profesional?.id_profesional ?? '—'}
                    </strong>
                  </div>

                  <div>
                    <small>Contacto empresarial</small>
                    <strong>
                      #{feedbackActual.id_contacto}
                    </strong>
                  </div>

                  <div>
                    <small>Fecha de registro</small>
                    <strong>
                      {fecha(
                        feedbackActual.fecha_registro,
                      )}
                    </strong>
                  </div>
                </div>

                <div className="adm-detalle">
                  <h3>
                    Comentario privado de la empresa
                  </h3>

                  <p
                    style={{
                      whiteSpace: 'pre-wrap',
                      overflowWrap: 'anywhere',
                    }}
                  >
                    {feedbackActual.contenido}
                  </p>
                </div>

                <div className="adm-nota">
                  Este comentario se mantiene privado
                  para Skilly. Crear una recomendación
                  no la comunica automáticamente.
                </div>

                <div className="adm-detalle">
                  <h3>
                    Recomendaciones de desarrollo
                    {' ('}{recomendaciones.length}{')'}
                  </h3>

                  {recomendaciones.length === 0 && (
                    <p>
                      No hay recomendaciones asociadas todavía.
                    </p>
                  )}

                  {recomendaciones.map((recomendacion) => (
                    <article
                      className="adm-nota"
                      key={recomendacion.id_recomendacion}
                      style={{ marginTop: 14 }}
                    >
                      <div className="adm-panel-header">
                        <strong>
                          #{recomendacion.id_recomendacion}
                          {' — '}
                          {recomendacion.titulo}
                        </strong>

                        <span className="adm-estado">
                          {recomendacion.estado}
                        </span>
                      </div>

                      <p
                        style={{
                          whiteSpace: 'pre-wrap',
                          overflowWrap: 'anywhere',
                        }}
                      >
                        {recomendacion.descripcion}
                      </p>

                      <small>
                        Creación:{' '}
                        {fecha(recomendacion.fecha_creacion)}

                        {recomendacion.fecha_comunicacion && (
                          <>
                            {' · '}
                            Comunicación:{' '}
                            {fecha(
                              recomendacion.fecha_comunicacion,
                            )}
                          </>
                        )}
                      </small>

                      {recomendacion.estado === 'REGISTRADA' && (
                        <div style={{ marginTop: 12 }}>
                          <button
                            type="button"
                            className="adm-secundario"
                            disabled={
                              guardando ||
                              cargandoDetalle
                            }
                            onClick={() =>
                              comunicarRecomendacion(
                                recomendacion,
                              )
                            }
                          >
                            {guardando
                              ? 'Procesando…'
                              : 'Comunicar al profesional'}
                          </button>
                        </div>
                      )}
                    </article>
                  ))}
                </div>

                {!creando ? (
                  <button
                    className="adm-secundario"
                    type="button"
                    disabled={
                      guardando ||
                      cargandoDetalle
                    }
                    onClick={() => {
                      setCreando(true)
                      setErrorDetalle('')
                    }}
                    style={{ marginTop: 22 }}
                  >
                    + Registrar recomendación de desarrollo
                  </button>
                ) : (
                  <form
                    onSubmit={registrarRecomendacion}
                    style={{
                      display: 'grid',
                      gap: 12,
                      marginTop: 22,
                    }}
                  >
                    <h3>
                      Nueva recomendación interna
                    </h3>

                    <label htmlFor="feedback-reco-titulo">
                      Título
                    </label>

                    <input
                      id="feedback-reco-titulo"
                      className="adm-busqueda"
                      required
                      maxLength={150}
                      value={titulo}
                      disabled={guardando}
                      onChange={(evento) =>
                        setTitulo(evento.target.value)
                      }
                      placeholder="Ej.: mejorar la comunicación"
                    />

                    <label htmlFor="feedback-reco-descripcion">
                      Descripción
                    </label>

                    <textarea
                      id="feedback-reco-descripcion"
                      className="adm-busqueda"
                      required
                      rows={4}
                      value={descripcion}
                      disabled={guardando}
                      onChange={(evento) =>
                        setDescripcion(
                          evento.target.value,
                        )
                      }
                      placeholder="Explica el aspecto que debe mejorar el profesional."
                    />

                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 10,
                      }}
                    >
                      <button
                        className="adm-secundario"
                        type="submit"
                        disabled={
                          guardando ||
                          !titulo.trim() ||
                          !descripcion.trim()
                        }
                      >
                        {guardando
                          ? 'Registrando…'
                          : 'Confirmar registro'}
                      </button>

                      <button
                        className="adm-secundario"
                        type="button"
                        disabled={guardando}
                        onClick={() =>
                          setCreando(false)
                        }
                      >
                        Cancelar
                      </button>
                    </div>
                  </form>
                )}
              </>
            )}
          </section>
        </div>,
        document.body,
      )}
    </div>
  )
}
