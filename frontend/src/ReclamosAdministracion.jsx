
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import AdminNavegacion from './AdminNavegacion.jsx'
import './Administracion.css'

const API = '/api/seguimiento/administracion/reclamos/'

/**
 * Identifica reclamos terminales por su estado o por la presencia de fecha de cierre.
 * @param {Object|null} reclamo Registro consultado.
 * @returns {boolean} Si la interfaz debe tratar el reclamo como resuelto.
 */
function estaResuelto(reclamo) {
  return (
    reclamo?.estado === 'RESUELTO' ||
    reclamo?.estado === 'CERRADO' ||
    Boolean(reclamo?.fecha_cierre)
  )
}

/**
 * Presenta una marca temporal en la zona local del navegador.
 * @param {string|null} valor Fecha recibida.
 * @returns {string} Fecha legible o indicación de ausencia o invalidez.
 */
function fecha(valor) {
  if (!valor) return 'No registrada'

  const dato = new Date(valor)

  if (Number.isNaN(dato.getTime())) {
    return 'Fecha no disponible'
  }

  return dato.toLocaleString('es-CL', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

/**
 * Formatea un importe con hasta dos decimales y añade la moneda indicada.
 * @param {number|string|null} valor Importe recibido.
 * @param {string} [moneda='CLP'] Etiqueta monetaria.
 * @returns {string} Importe legible o indicación de dato ausente o inválido.
 */
function dinero(valor, moneda = 'CLP') {
  if (valor === null || valor === undefined) {
    return 'No informado'
  }

  const numero = Number(valor)

  if (!Number.isFinite(numero)) {
    return 'No disponible'
  }

  return `${new Intl.NumberFormat('es-CL', {
    maximumFractionDigits: 2,
  }).format(numero)} ${moneda}`
}

/**
 * Prioriza mensajes generales y reúne el contenido de errores por campo.
 * @param {Object|null} datos Respuesta de la API.
 * @param {number} codigo Estado HTTP de respaldo.
 * @returns {string} Explicación del rechazo.
 */
function mensajeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') {
    return datos.mensaje
  }

  if (typeof datos?.detail === 'string') {
    return datos.detail
  }

  if (datos && typeof datos === 'object') {
    const errores = Object.entries(datos).map(
      ([campo, valor]) => {
        const mensaje = Array.isArray(valor)
          ? valor.join(', ')
          : String(valor)

        return `${campo}: ${mensaje}`
      },
    )

    if (errores.length > 0) {
      return errores.join(' | ')
    }
  }

  return `La operación no pudo completarse (HTTP ${codigo}).`
}

/**
 * Consulta reclamos, filtra la bandeja localmente y registra resoluciones.
 * Mantiene el detalle abierto durante la escritura y recarga la lista tras resolver.
 * @returns {import('react').ReactElement} Bandeja y diálogo administrativo.
 */
export default function ReclamosAdministracion() {
  const [reclamos, setReclamos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [revision, setRevision] = useState(0)

  const [pestana, setPestana] = useState('TODOS')
  const [busqueda, setBusqueda] = useState('')

  const [idSeleccionado, setIdSeleccionado] = useState(null)
  const [detalle, setDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [errorDetalle, setErrorDetalle] = useState('')

  const [decision, setDecision] = useState('')
  const [efectoEconomico, setEfectoEconomico] = useState('')
  const [montoAfectado, setMontoAfectado] = useState('')
  const [observacion, setObservacion] = useState('')
  const [guardando, setGuardando] = useState(false)

  // Consultar la bandeja administrativa existente.
  useEffect(() => {
    // Consulta la bandeja para la sesión administrativa activa.
    let activo = true

    /**
     * Consulta y valida la lista de reclamos para la sesión actual.
     * La marca activa impide aplicar resultados de un efecto sustituido.
     * @returns {Promise<void>} Finalización de la consulta con errores visibles.
     */
    async function consultar() {
      try {
        const respuesta = await fetch(API, {
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
            mensajeError(datos, respuesta.status),
          )
        }

        if (!Array.isArray(datos.reclamos)) {
          throw new Error(
            'La API no devolvió una lista válida de reclamos.',
          )
        }

        if (activo) {
          setReclamos(datos.reclamos)
        }
      } catch (fallo) {
        if (activo) {
          setError(
            fallo.message ||
            'No se pudo consultar la bandeja.',
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
  }, [revision])

  // Consultar el detalle de un reclamo seleccionado.
  useEffect(() => {
    // Actualiza el historial del reclamo cuando cambia la selección.
    if (idSeleccionado === null) {
      return undefined
    }

    let activo = true

    const desbordamientoAnterior =
      document.body.style.overflow

    document.body.style.overflow = 'hidden'

    /**
     * Cierra el diálogo con Escape cuando no se está guardando una resolución.
     * @param {KeyboardEvent} evento Pulsación recibida por el documento.
     * @returns {void}
     */
    function tecla(evento) {
      if (evento.key === 'Escape' && !guardando) {
        setIdSeleccionado(null)
      }
    }

    document.addEventListener('keydown', tecla)

    /**
     * Consulta el reclamo y sus antecedentes económicos antes de permitir resolverlo.
     * Ignora resultados si la selección dejó de estar activa.
     * @returns {Promise<void>} Finalización de la lectura con errores en el diálogo.
     */
    async function consultarDetalle() {
      try {
        const respuesta = await fetch(
          `${API}${idSeleccionado}/`,
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
            mensajeError(datos, respuesta.status),
          )
        }

        if (!datos.reclamo) {
          throw new Error(
            'La API no devolvió el detalle del reclamo.',
          )
        }

        if (activo) {
          setDetalle(datos)
        }
      } catch (fallo) {
        if (activo) {
          setErrorDetalle(
            fallo.message ||
            'No se pudo consultar el reclamo.',
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
      // Desactiva las actualizaciones y restaura el fondo al cerrar el detalle.
      activo = false

      document.body.style.overflow =
        desbordamientoAnterior

      document.removeEventListener('keydown', tecla)
    }
  }, [idSeleccionado, guardando])

  /**
   * Solicita una nueva lectura de la bandeja conservando sus filtros locales.
   * @returns {void}
   */
  function recargar() {
    setError('')
    setCargando(true)
    setRevision((actual) => actual + 1)
  }

  /**
   * Selecciona un reclamo y reinicia el borrador de resolución anterior.
   * @param {number|string} id Identificador del reclamo.
   * @returns {void}
   */
  function abrirDetalle(id) {
    setDetalle(null)
    setErrorDetalle('')
    setCargandoDetalle(true)

    setDecision('')
    setEfectoEconomico('')
    setMontoAfectado('')
    setObservacion('')

    setIdSeleccionado(id)
  }

  /**
   * Cierra el detalle únicamente cuando no hay una resolución en curso.
   * @returns {void}
   */
  function cerrarDetalle() {
    if (guardando) return
    setIdSeleccionado(null)
  }

  /**
   * Valida decisión, efecto económico y formato decimal antes de confirmar.
   * Envía el importe opcional como texto normalizado para que el servidor lo valide.
   * Tras el registro cierra el detalle y recarga la bandeja; los errores quedan visibles.
   * @param {import('react').FormEvent<HTMLFormElement>} evento Envío de la resolución.
   * @returns {Promise<void>} Finalización de la solicitud de resolución.
   */
  async function resolverReclamo(evento) {
    evento.preventDefault()

    const reclamo = detalle?.reclamo

    if (
      !reclamo ||
      estaResuelto(reclamo) ||
      detalle?.resolucion ||
      guardando
    ) {
      return
    }

    const decisionLimpia = decision.trim()
    const observacionLimpia = observacion.trim()
    const montoNormalizado = montoAfectado
      .trim()
      .replace(',', '.')

    if (
      !decisionLimpia ||
      decisionLimpia.length > 40 ||
      !efectoEconomico
    ) {
      setErrorDetalle(
        'Indica una decisión de hasta 40 caracteres y selecciona el efecto económico.',
      )
      return
    }

    if (
      montoNormalizado &&
      !/^\d{1,10}(\.\d{1,2})?$/.test(montoNormalizado)
    ) {
      setErrorDetalle(
        'El monto debe ser positivo y tener como máximo dos decimales.',
      )
      return
    }

    const confirmado = window.confirm(
      `¿Confirmas la resolución del reclamo #${reclamo.id_reclamo}?\n\n` +
      `Decisión: ${decisionLimpia}\n` +
      `Efecto económico: ${efectoEconomico}\n\n` +
      'Esta acción registra una resolución y no debe repetirse.',
    )

    if (!confirmado) return

    setGuardando(true)
    setErrorDetalle('')

    try {
      const respuestaCsrf = await fetch(
        '/api/acceso/csrf/',
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: {
            Accept: 'application/json',
          },
        },
      )

      const datosCsrf = await respuestaCsrf
        .json()
        .catch(() => ({}))

      if (
        !respuestaCsrf.ok ||
        !datosCsrf.csrfToken
      ) {
        throw new Error(
          'No se pudo obtener el token de seguridad.',
        )
      }

      const cuerpo = {
        decision: decisionLimpia,
        efecto_economico: efectoEconomico,
      }

      if (montoNormalizado) {
        cuerpo.monto_afectado = montoNormalizado
      }

      if (observacionLimpia) {
        cuerpo.observacion = observacionLimpia
      }

      const respuesta = await fetch(
        `${API}${reclamo.id_reclamo}/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': datosCsrf.csrfToken,
          },
          body: JSON.stringify(cuerpo),
        },
      )

      const datos = await respuesta
        .json()
        .catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          mensajeError(datos, respuesta.status),
        )
      }

      setAviso(
        datos.mensaje ||
        'Resolución registrada correctamente.',
      )

      setIdSeleccionado(null)
      setCargando(true)
      setRevision((actual) => actual + 1)
    } catch (fallo) {
      setErrorDetalle(
        fallo.message ||
        'No se pudo resolver el reclamo.',
      )
    } finally {
      setGuardando(false)
    }
  }

  const pendientes = reclamos.filter(
    (reclamo) => !estaResuelto(reclamo),
  )

  const resueltos = reclamos.filter(
    (reclamo) => estaResuelto(reclamo),
  )

  const filtrados = reclamos.filter((reclamo) => {
    // Aplica el criterio de estado sobre el listado visible de reclamos.
    if (
      pestana === 'PENDIENTES' &&
      estaResuelto(reclamo)
    ) {
      return false
    }

    if (
      pestana === 'RESUELTOS' &&
      !estaResuelto(reclamo)
    ) {
      return false
    }

    const termino = busqueda
      .trim()
      .toLowerCase()

    if (!termino) return true

    return [
      reclamo.id_reclamo,
      reclamo.id_prestacion,
      reclamo.estado,
      reclamo.motivo,
    ].some((valor) =>
      String(valor ?? '')
        .toLowerCase()
        .includes(termino),
    )
  })

  const reclamoActual = detalle?.reclamo
  const resolucionActual = detalle?.resolucion
  const pagoActual = detalle?.pago

  const sePuedeResolver = Boolean(
    reclamoActual &&
    !estaResuelto(reclamoActual) &&
    !resolucionActual,
  )

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

      <AdminNavegacion activo="reclamos" />

      <main className="adm-contenedor">
        <div className="adm-intro">
          <span className="adm-eyebrow">
            BACK-OFFICE · SEGUIMIENTO
          </span>

          <h1>Gestión de reclamos</h1>

          <p>
            Consulta los reclamos empresariales,
            sus antecedentes y sus resoluciones.
          </p>
        </div>

        <section className="adm-panel">
          <div className="adm-panel-header">
            <h2>Resumen de reclamos</h2>

            <button
              className="adm-secundario"
              type="button"
              disabled={cargando}
              onClick={recargar}
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

          {aviso && (
            <p className="adm-aviso" role="status">
              {aviso}
            </p>
          )}

          {cargando && (
            <p role="status">
              Consultando reclamos del servidor…
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
              <span>Total registrados</span>
              <strong>{reclamos.length}</strong>
            </div>

            <div>
              <span>Pendientes</span>
              <strong>{pendientes.length}</strong>
            </div>

            <div>
              <span>Resueltos o cerrados</span>
              <strong>{resueltos.length}</strong>
            </div>
          </div>
        </section>

        <section className="adm-panel">
          <h2>Bandeja administrativa</h2>

          <div
            className="adm-pestanas"
            role="group"
            aria-label="Filtrar reclamos"
          >
            {[
              ['TODOS', 'Todos'],
              ['PENDIENTES', 'Pendientes'],
              ['RESUELTOS', 'Resueltos'],
            ].map(([valor, etiqueta]) => (
              <button
                type="button"
                key={valor}
                className={
                  pestana === valor ? 'activa' : ''
                }
                onClick={() => setPestana(valor)}
              >
                {etiqueta}
              </button>
            ))}
          </div>

          <label
            htmlFor="adm-reclamos-busqueda"
            style={{
              display: 'block',
              marginBottom: 8,
            }}
          >
            Buscar por número, motivo o estado
          </label>

          <input
            id="adm-reclamos-busqueda"
            className="adm-busqueda"
            type="search"
            value={busqueda}
            onChange={(evento) =>
              setBusqueda(evento.target.value)
            }
            placeholder="Ej.: reclamo 1 o motivo"
          />

          {!cargando &&
            !error &&
            filtrados.length === 0 && (
              <p className="adm-vacio">
                No hay reclamos para estos filtros.
              </p>
            )}

          <div className="adm-lista">
            {filtrados.map((reclamo) => (
              <button
                key={reclamo.id_reclamo}
                className="adm-item"
                type="button"
                style={{
                  width: '100%',
                  font: 'inherit',
                }}
                onClick={() =>
                  abrirDetalle(reclamo.id_reclamo)
                }
              >
                <span className="adm-item-cuerpo">
                  <strong>
                    Reclamo #{reclamo.id_reclamo}
                    {' — '}
                    {reclamo.motivo}
                  </strong>

                  <small>
                    Prestación #{reclamo.id_prestacion}
                    {' · '}
                    {fecha(reclamo.fecha_registro)}
                  </small>

                  <small>
                    {reclamo.descripcion}
                  </small>
                </span>

                <span className="adm-estado">
                  {reclamo.estado}
                  {' →'}
                </span>
              </button>
            ))}
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
              cerrarDetalle()
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
            aria-labelledby="reclamo-titulo"
            style={{
              width: 'min(740px, 100%)',
              maxHeight: '88vh',
              overflowY: 'auto',
              background: '#fff',
              color: '#203a38',
              borderRadius: 22,
              padding: 26,
            }}
          >
            <div className="adm-panel-header">
              <h2 id="reclamo-titulo">
                Reclamo #{idSeleccionado}
              </h2>

              <button
                className="adm-secundario"
                type="button"
                disabled={guardando}
                onClick={cerrarDetalle}
              >
                ✕ Cerrar
              </button>
            </div>

            {cargandoDetalle && (
              <p role="status">
                Consultando antecedentes…
              </p>
            )}

            {errorDetalle && (
              <p className="adm-error" role="alert">
                {errorDetalle}
              </p>
            )}

            {reclamoActual && (
              <>
                <div className="adm-datos">
                  <div>
                    <small>Estado del reclamo</small>
                    <strong>
                      {reclamoActual.estado}
                    </strong>
                  </div>

                  <div>
                    <small>Prestación</small>
                    <strong>
                      #{reclamoActual.id_prestacion}
                    </strong>
                  </div>

                  <div>
                    <small>Estado de prestación</small>
                    <strong>
                      {detalle.prestacion?.estado ||
                        'No informado'}
                    </strong>
                  </div>

                  <div>
                    <small>Fecha de registro</small>
                    <strong>
                      {fecha(
                        reclamoActual.fecha_registro,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Fecha de cierre</small>
                    <strong>
                      {fecha(
                        reclamoActual.fecha_cierre,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Contacto empresarial</small>
                    <strong>
                      #{reclamoActual.id_contacto}
                    </strong>
                  </div>
                </div>

                <div className="adm-detalle">
                  <h3>Motivo</h3>
                  <p>{reclamoActual.motivo}</p>

                  <h3>Descripción del reclamo</h3>
                  <p>{reclamoActual.descripcion}</p>

                  {reclamoActual.orientacion && (
                    <div className="adm-nota">
                      <h3>Orientación de gestión de incidencia</h3>
                      <p>{reclamoActual.orientacion.accion_recomendada}</p>
                      <p>{reclamoActual.orientacion.precaucion}</p>
                      <p>
                        Para cambiar fechas o cancelar una prestación,
                        utiliza la gestión de agenda de SKILLY.
                        La resolución de este reclamo no sustituye ese paso.
                      </p>
                    </div>
                  )}
                </div>

                <div className="adm-nota">
                  <strong>Información económica</strong>

                  {pagoActual ? (
                    <p>
                      Pago #{pagoActual.id_pago}
                      {' · '}
                      {pagoActual.estado_pago}
                      {' · '}
                      {dinero(
                        pagoActual.monto_total,
                        pagoActual.moneda,
                      )}
                    </p>
                  ) : (
                    <p>
                      No hay un pago asociado
                      a esta prestación.
                    </p>
                  )}
                </div>

                {resolucionActual && (
                  <div className="adm-detalle">
                    <h3>Resolución registrada</h3>

                    <div className="adm-datos">
                      <div>
                        <small>Decisión</small>
                        <strong>
                          {resolucionActual.decision}
                        </strong>
                      </div>

                      <div>
                        <small>Efecto económico</small>
                        <strong>
                          {resolucionActual.efecto_economico}
                        </strong>
                      </div>

                      <div>
                        <small>Monto afectado</small>
                        <strong>
                          {dinero(
                            resolucionActual.monto_afectado,
                          )}
                        </strong>
                      </div>

                      <div>
                        <small>Fecha de resolución</small>
                        <strong>
                          {fecha(
                            resolucionActual.fecha_resolucion,
                          )}
                        </strong>
                      </div>
                    </div>

                    <p>
                      {resolucionActual.observacion ||
                        'Sin observaciones adicionales.'}
                    </p>

                    <p className="adm-nota">
                      Resolución histórica de solo lectura.
                      Este reclamo no puede resolverse
                      nuevamente.
                    </p>
                  </div>
                )}

                {sePuedeResolver && (
                  <form
                    onSubmit={resolverReclamo}
                    style={{
                      display: 'grid',
                      gap: 12,
                      marginTop: 24,
                    }}
                  >
                    <h3>Registrar resolución</h3>

                    <p className="adm-nota">
                      Esta acción registra la decisión
                      administrativa y su efecto económico.
                      No ejecuta automáticamente una
                      liberación o reversa de pago.
                    </p>

                    <label htmlFor="reclamo-decision">
                      Decisión administrativa
                    </label>

                    <input
                      id="reclamo-decision"
                      className="adm-busqueda"
                      type="text"
                      required
                      maxLength={40}
                      placeholder="Describe la decisión"
                      value={decision}
                      disabled={guardando}
                      onChange={(evento) =>
                        setDecision(
                          evento.target.value,
                        )
                      }
                    />

                    <label htmlFor="reclamo-efecto">
                      Efecto económico
                    </label>

                    <select
                      id="reclamo-efecto"
                      className="adm-busqueda"
                      required
                      value={efectoEconomico}
                      disabled={guardando}
                      onChange={(evento) =>
                        setEfectoEconomico(
                          evento.target.value,
                        )
                      }
                    >
                      <option value="">
                        Selecciona una opción
                      </option>

                      <option value="LIBERACION">
                        Liberación
                      </option>

                      <option value="RETENCION">
                        Retención
                      </option>

                      <option value="REVERSA">
                        Reversa
                      </option>
                    </select>

                    <label htmlFor="reclamo-monto">
                      Monto afectado (opcional)
                    </label>

                    <input
                      id="reclamo-monto"
                      className="adm-busqueda"
                      type="text"
                      inputMode="decimal"
                      placeholder="Ej.: 100000.00"
                      value={montoAfectado}
                      disabled={guardando}
                      onChange={(evento) =>
                        setMontoAfectado(
                          evento.target.value,
                        )
                      }
                    />

                    <label htmlFor="reclamo-observacion">
                      Observación (opcional)
                    </label>

                    <textarea
                      id="reclamo-observacion"
                      className="adm-busqueda"
                      rows={4}
                      value={observacion}
                      disabled={guardando}
                      onChange={(evento) =>
                        setObservacion(
                          evento.target.value,
                        )
                      }
                    />

                    <button
                      className="adm-secundario"
                      type="submit"
                      disabled={
                        guardando ||
                        !decision.trim() ||
                        !efectoEconomico
                      }
                    >
                      {guardando
                        ? 'Guardando resolución…'
                        : 'Revisar y confirmar resolución'}
                    </button>
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
