
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import AdminNavegacion from './AdminNavegacion.jsx'
import './Administracion.css'

const RUTA = '/api/backoffice/trazabilidad/'

const NOMBRES_ENTIDAD = {
  servicio: 'Servicio profesional',
  revision_servicio: 'Revisión de propuesta',
  solicitud_servicio: 'Solicitud empresarial',
  solicitud_profesional: 'Asociación profesional',
  asignacion_solicitud: 'Asignación interna',
  disponibilidad: 'Disponibilidad de horarios',
  reserva_disponibilidad: 'Reserva de horario',
  prestacion_servicio: 'Prestación del servicio',
  pago: 'Pago',
}

const NOMBRES_ACCION = {
  PUBLICAR_SERVICIO: 'Publicar servicio',
  CREAR_PROPUESTA_SERVICIO:
    'Crear propuesta de servicio',
  ACTUALIZAR_PROPUESTA_SERVICIO:
    'Actualizar propuesta de servicio',
  ENVIAR_PROPUESTA_REVISION:
    'Enviar propuesta a revisión',
  APROBAR_REVISION_SERVICIO:
    'Aprobar revisión de propuesta',
  APROBAR_VERSION_SERVICIO:
    'Aprobar versión del servicio',
  CREAR_BLOQUE_DISPONIBILIDAD:
    'Crear horario disponible',
  ACTUALIZAR_BLOQUE_DISPONIBILIDAD:
    'Actualizar horario',
  ELIMINAR_BLOQUE_DISPONIBILIDAD:
    'Eliminar horario',
  SELECCIONAR_DISPONIBILIDAD:
    'Seleccionar horario',
  ENVIAR_SOLICITUD_SERVICIO:
    'Enviar solicitud empresarial',
  AUTOASIGNAR:
    'Autoasignar solicitud',
  CREAR_ASOCIACION:
    'Crear asociación profesional',
  CONFIRMAR_ASOCIACION:
    'Confirmar asociación profesional',
  PREPARAR_PRESTACION:
    'Preparar prestación de servicio',
  CAMBIO_ESTADO:
    'Cambio de estado',
}

/**
 * Obtiene el nombre conocido de una entidad o adapta su código a texto.
 * @param {string|null} codigo Tipo de entidad registrado en el evento.
 * @returns {string} Etiqueta para el historial y sus filtros.
 */
function etiquetaEntidad(codigo) {
  return (
    NOMBRES_ENTIDAD[codigo] ||
    (codigo || 'Entidad').replaceAll('_', ' ')
  )
}

/**
 * Resuelve una acción conocida o convierte su código a una etiqueta con inicial mayúscula.
 * @param {string|null} codigo Acción registrada por el backend.
 * @returns {string} Nombre legible de la operación.
 */
function etiquetaAccion(codigo) {
  if (NOMBRES_ACCION[codigo]) {
    return NOMBRES_ACCION[codigo]
  }

  const texto = (
    codigo || 'Acción sin nombre'
  )
    .toLowerCase()
    .replaceAll('_', ' ')

  return (
    texto.charAt(0).toUpperCase() +
    texto.slice(1)
  )
}

/**
 * Selecciona el error de trazabilidad o un texto con el estado HTTP.
 * @param {Object|null} datos Respuesta JSON.
 * @param {number} codigo Estado HTTP de respaldo.
 * @returns {string} Mensaje según el contrato textual de la API.
 */
function textoError(datos, codigo) {
  return (
    datos?.mensaje ||
    datos?.detail ||
    `Error al consultar trazabilidad (HTTP ${codigo}).`
  )
}

/**
 * Formatea el momento del evento con locale chileno y zona del navegador.
 * @param {string|null} valor Fecha recibida del servidor.
 * @returns {string} Fecha legible o indicación de ausencia/invalidez.
 */
function fechaLegible(valor) {
  if (!valor) return 'Sin fecha'

  const fecha = new Date(valor)

  return Number.isNaN(fecha.getTime())
    ? 'Fecha no disponible'
    : fecha.toLocaleString('es-CL', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
}

/**
 * Consulta eventos y sus detalles manteniendo separados filtros editados y filtros aplicados.
 * Construye las opciones de entidad y acción a partir de los eventos existentes.
 * @returns {import('react').ReactElement} Historial administrativo de solo lectura.
 */
export default function TrazabilidadAdministracion() {
  // Valores seleccionados por el administrador.
  const [tipo, setTipo] = useState('')
  const [accion, setAccion] = useState('')
  const [identificador, setIdentificador] =
    useState('')

  // Filtros enviados al backend.
  const [filtros, setFiltros] = useState({})
  const [revision, setRevision] = useState(0)

  // Catálogo para construir los filtros.
  const [catalogo, setCatalogo] = useState([])

  const [eventos, setEventos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  // Ventana de detalle.
  const [idDetalle, setIdDetalle] = useState(null)
  const [detalle, setDetalle] = useState(null)

  const [
    cargandoDetalle,
    setCargandoDetalle,
  ] = useState(false)

  const [
    errorDetalle,
    setErrorDetalle,
  ] = useState('')

  useEffect(() => {
    // Actualiza el historial y sus filtros mientras la vista permanece activa.
    let activo = true

    /**
     * Consulta una ruta de trazabilidad y exige una lista eventos válida.
     * @param {string} url URL del historial, con filtros opcionales.
     * @returns {Promise<Object[]>} Eventos de la respuesta.
     * @throws {Error} Si falla la conexión, el estado HTTP o el formato del listado.
     */
    async function obtener(url) {
      const respuesta = await fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: {
          Accept: 'application/json',
        },
      })

      const datos = await respuesta
        .json()
        .catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          textoError(datos, respuesta.status),
        )
      }

      if (!Array.isArray(datos.eventos)) {
        throw new Error(
          'La API no devolvió una lista válida de eventos.',
        )
      }

      return datos.eventos
    }

    /**
     * Consulta primero el catálogo completo y después el listado filtrado si hay criterios.
     * @returns {Promise<void>} Aplica ambos resultados solo mientras este efecto permanece activo.
     */
    async function consultar() {
      try {
        // Consulta general: nombres reales
        // para construir las listas desplegables.
        const todos = await obtener(RUTA)

        const parametros = new URLSearchParams(
          filtros,
        )

        // Los filtros siguen utilizando
        // los nombres originales aceptados
        // por el backend.
        const resultado = parametros.size
          ? await obtener(
              `${RUTA}?${parametros.toString()}`,
            )
          : todos

        if (activo) {
          setCatalogo(todos)
          setEventos(resultado)
        }
      } catch (fallo) {
        if (activo) {
          setError(
            fallo.message ||
            'No se pudo consultar trazabilidad.',
          )
        }
      } finally {
        if (activo) {
          setCargando(false)
        }
      }
    }

    void consultar()

    return () => {
      activo = false
    }
  }, [filtros, revision])

  useEffect(() => {
    // Consulta los antecedentes del evento de auditoría seleccionado.
    if (idDetalle === null) {
      return undefined
    }

    let activo = true

    const anterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    /**
     * Cierra el detalle seleccionado al pulsar Escape.
     * @param {KeyboardEvent} evento Evento del documento mientras el diálogo está abierto.
     * @returns {void}
     */
    function alEscapar(evento) {
      if (evento.key === 'Escape') {
        setIdDetalle(null)
      }
    }

    document.addEventListener(
      'keydown',
      alEscapar,
    )

    /**
     * Consulta el evento seleccionado y descarta su resultado al cerrar o cambiar de selección.
     * @returns {Promise<void>} Actualiza detalle o error sin modificar el historial.
     */
    async function consultarDetalle() {
      try {
        const respuesta = await fetch(
          `${RUTA}${idDetalle}/`,
          {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              Accept: 'application/json',
            },
          },
        )

        const datos = await respuesta
          .json()
          .catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(
            textoError(datos, respuesta.status),
          )
        }

        if (activo) {
          setDetalle(datos)
        }
      } catch (fallo) {
        if (activo) {
          setErrorDetalle(
            fallo.message ||
            'No se pudo consultar el evento.',
          )
        }
      } finally {
        if (activo) {
          setCargandoDetalle(false)
        }
      }
    }

    void consultarDetalle()

    return () => {
      // Desactiva la actualización pendiente y restaura el desplazamiento al cerrar.
      activo = false

      document.body.style.overflow =
        anterior

      document.removeEventListener(
        'keydown',
        alEscapar,
      )
    }
  }, [idDetalle])

  // Obtener los tipos de entidades que existen
  // realmente en los eventos registrados.
  const tiposDisponibles = [
    ...new Set(
      catalogo
        .map((item) => item.entidad_tipo)
        .filter(Boolean),
    ),
  ].sort((a, b) =>
    etiquetaEntidad(a).localeCompare(
      etiquetaEntidad(b),
      'es',
    ),
  )

  // Si seleccionamos una entidad,
  // mostrar solo sus acciones conocidas.
  const accionesDisponibles = [
    ...new Set(
      catalogo
        .filter(
          (item) =>
            !tipo ||
            item.entidad_tipo === tipo,
        )
        .map((item) => item.accion)
        .filter(Boolean),
    ),
  ].sort((a, b) =>
    etiquetaAccion(a).localeCompare(
      etiquetaAccion(b),
      'es',
    ),
  )

  /**
   * Valida el identificador positivo y aplica los criterios escritos para iniciar otra consulta.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {void} Omite los filtros vacíos y conserva los nombres de parámetros del backend.
   */
  function consultarFiltros(evento) {
    evento.preventDefault()

    if (
      identificador.trim() &&
      !/^[1-9]\d*$/.test(
        identificador.trim(),
      )
    ) {
      setError(
        'El número de registro debe ser un entero positivo.',
      )
      return
    }

    const nuevos = {}

    if (tipo) {
      nuevos.entidad_tipo = tipo
    }

    if (accion) {
      nuevos.accion = accion
    }

    if (identificador.trim()) {
      nuevos.entidad_id =
        identificador.trim()
    }

    setError('')
    setCargando(true)
    setEventos([])
    setFiltros(nuevos)
  }

  /**
   * Restablece controles y filtros enviados para volver a consultar todos los eventos.
   * @returns {void}
   */
  function limpiarFiltros() {
    setTipo('')
    setAccion('')
    setIdentificador('')
    setError('')
    setCargando(true)
    setEventos([])
    setFiltros({})
  }

  /**
   * Recarga los eventos con los filtros ya aplicados y vacía el resultado anterior mientras consulta.
   * @returns {void}
   */
  function recargar() {
    setError('')
    setCargando(true)
    setEventos([])

    setRevision(
      (anterior) => anterior + 1,
    )
  }

  /**
   * Selecciona un evento y prepara el estado para que el efecto consulte su detalle.
   * @param {number|string} id Identificador del evento del listado.
   * @returns {void}
   */
  function abrirDetalle(id) {
    setDetalle(null)
    setErrorDetalle('')
    setCargandoDetalle(true)
    setIdDetalle(id)
  }

  return (
    <div className="adm-pagina">
      <header className="adm-header">
        <a
          className="adm-logo"
          href="/administracion"
        >
          <span className="adm-estrella">
            ✦
          </span>
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

      <AdminNavegacion activo="trazabilidad" />

      <main className="adm-contenedor">
        <div className="adm-intro">
          <span className="adm-eyebrow">
            BACK-OFFICE · AUDITORÍA
          </span>

          <h1>Trazabilidad operacional</h1>

          <p>
            Consulta los eventos registrados
            sin modificar su historial.
          </p>
        </div>

        <section
          className="adm-panel"
          aria-label="Filtros de trazabilidad"
        >
          <h2>Buscar eventos</h2>

          <p className="adm-nota">
            Elige la categoría y la acción en las listas.
            No necesitas conocer códigos internos.
          </p>

          <form onSubmit={consultarFiltros}>
            <div className="adm-datos">
              <label>
                <small>
                  ¿Sobre qué tipo de registro?
                </small>

                <select
                  className="adm-busqueda"
                  value={tipo}
                  disabled={cargando}
                  onChange={(evento) => {
                    setTipo(
                      evento.target.value,
                    )

                    setAccion('')
                  }}
                >
                  <option value="">
                    Todas las categorías
                  </option>

                  {tiposDisponibles.map(
                    (codigo) => (
                      <option
                        value={codigo}
                        key={codigo}
                      >
                        {etiquetaEntidad(codigo)}
                      </option>
                    ),
                  )}
                </select>
              </label>

              <label>
                <small>
                  ¿Qué acción se realizó?
                </small>

                <select
                  className="adm-busqueda"
                  value={accion}
                  disabled={cargando}
                  onChange={(evento) =>
                    setAccion(
                      evento.target.value,
                    )
                  }
                >
                  <option value="">
                    Todas las acciones
                  </option>

                  {accionesDisponibles.map(
                    (codigo) => (
                      <option
                        value={codigo}
                        key={codigo}
                      >
                        {etiquetaAccion(codigo)}
                      </option>
                    ),
                  )}
                </select>
              </label>

              <label>
                <small>
                  Número de registro (opcional)
                </small>

                <input
                  className="adm-busqueda"
                  value={identificador}
                  disabled={cargando}
                  onChange={(evento) =>
                    setIdentificador(
                      evento.target.value,
                    )
                  }
                  inputMode="numeric"
                  placeholder="Ej.: 2"
                />

                <small>
                  Es el ID del servicio, solicitud
                  o registro; no el número del evento.
                </small>
              </label>
            </div>

            <div
              style={{
                display: 'flex',
                gap: 12,
                flexWrap: 'wrap',
              }}
            >
              <button
                className="adm-secundario"
                type="submit"
                disabled={cargando}
              >
                Buscar eventos
              </button>

              <button
                className="adm-secundario"
                type="button"
                onClick={limpiarFiltros}
                disabled={cargando}
              >
                Mostrar todos
              </button>
            </div>
          </form>
        </section>

        <section
          className="adm-panel"
          aria-label="Eventos registrados"
        >
          <div className="adm-panel-header">
            <h2>
              Eventos registrados:{' '}
              {cargando
                ? '…'
                : eventos.length}
            </h2>

            <button
              className="adm-secundario"
              type="button"
              onClick={recargar}
              disabled={cargando}
            >
              {cargando
                ? 'Consultando…'
                : '↻ Recargar eventos'}
            </button>
          </div>

          {error && (
            <p
              className="adm-error"
              role="alert"
            >
              {error}
            </p>
          )}

          {cargando && (
            <p role="status">
              Cargando eventos desde
              el servidor…
            </p>
          )}

          {!cargando &&
            !error &&
            eventos.length === 0 && (
              <p className="adm-vacio">
                No hay eventos para
                esos criterios.
              </p>
            )}

          <div className="adm-lista">
            {eventos.map((evento) => (
              <button
                className="adm-item"
                type="button"
                key={evento.id_evento}
                onClick={() =>
                  abrirDetalle(
                    evento.id_evento,
                  )
                }
              >
                <span className="adm-item-cuerpo">
                  <strong>
                    {etiquetaAccion(
                      evento.accion,
                    )}
                  </strong>

                  <small>
                    {etiquetaEntidad(
                      evento.entidad_tipo,
                    )}
                    {' · Registro #'}
                    {evento.entidad_id ?? '—'}
                  </small>

                  <small>
                    {evento.detalle_resumido ||
                      'Sin descripción'}
                  </small>

                  <small>
                    {fechaLegible(
                      evento.fecha_evento,
                    )}
                  </small>
                </span>

                <span className="adm-estado">
                  Ver evento #{evento.id_evento} →
                </span>
              </button>
            ))}
          </div>

          <p className="adm-nota">
            Solo lectura. Esta pantalla no crea,
            edita ni elimina eventos.
          </p>
        </section>
      </main>

      {idDetalle !== null && createPortal(
        <div
          role="presentation"
          onMouseDown={(evento) => {
            // Cierra el diálogo solo si el clic fue sobre su fondo.
            if (
              evento.target ===
              evento.currentTarget
            ) {
              setIdDetalle(null)
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
            aria-labelledby="sk-evento-titulo"
            style={{
              width: 'min(650px, 100%)',
              maxHeight: '86vh',
              overflowY: 'auto',
              background: '#fff',
              color: '#203a38',
              borderRadius: 22,
              padding: 28,
            }}
          >
            <div className="adm-panel-header">
              <h2 id="sk-evento-titulo">
                Detalle del evento #{idDetalle}
              </h2>

              <button
                className="adm-secundario"
                type="button"
                onClick={() =>
                  setIdDetalle(null)
                }
              >
                ✕ Cerrar
              </button>
            </div>

            {cargandoDetalle && (
              <p role="status">
                Consultando detalle…
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

            {detalle && (
              <div className="adm-datos">
                <div>
                  <small>Acción</small>

                  <strong>
                    {etiquetaAccion(
                      detalle.accion,
                    )}
                  </strong>

                  <small>
                    Código registrado:{' '}
                    {detalle.accion ||
                      'No informado'}
                  </small>
                </div>

                <div>
                  <small>Tipo de registro</small>

                  <strong>
                    {etiquetaEntidad(
                      detalle.entidad_tipo,
                    )}
                  </strong>

                  <small>
                    Código:{' '}
                    {detalle.entidad_tipo ||
                      'No informado'}
                  </small>
                </div>

                <div>
                  <small>ID del registro</small>

                  <strong>
                    {detalle.entidad_id ??
                      'No informado'}
                  </strong>
                </div>

                <div>
                  <small>Fecha</small>

                  <strong>
                    {fechaLegible(
                      detalle.fecha_evento,
                    )}
                  </strong>
                </div>

                <div>
                  <small>Responsable</small>

                  <strong>
                    {detalle.responsable?.correo ||
                      'No informado'}
                  </strong>
                </div>

                <div>
                  <small>Rol</small>

                  <strong>
                    {detalle.responsable?.rol ||
                      'No informado'}
                  </strong>
                </div>

                <div
                  style={{
                    gridColumn: '1 / -1',
                  }}
                >
                  <small>
                    Descripción registrada
                  </small>

                  <strong>
                    {detalle.detalle_resumido ||
                      'Sin descripción'}
                  </strong>
                </div>
              </div>
            )}
          </section>
        </div>,
        document.body,
      )}
    </div>
  )
}
