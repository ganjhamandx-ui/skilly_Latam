
import { useState } from 'react'
import './Seguimiento.css'
import PagoEmpresaSeguimiento from './PagoEmpresaSeguimiento.jsx'
import { ReagendamientosOrganizacion } from './ReagendamientosSkilly.jsx'
import AdjuntosEntregaEmpresaE3 from './AdjuntosEntregaEmpresaE3.jsx'
import CondicionesPrestacionE3 from './CondicionesPrestacionE3.jsx'

// Prepara un valor de la ficha como texto legible y maneja campos ausentes.
function texto(valor, defecto = 'No informado') {
  if (valor === null || valor === undefined || valor === '') {
    return defecto
  }
  return String(valor)
}

// Presenta los registros en formato local y conserva el día civil de las fechas sin hora.
function formatoFecha(valor) {
  if (!valor) return 'No informada'
  const fecha = String(valor).slice(0, 10)
  const partes = fecha.split('-')
  if (partes.length !== 3) return fecha
  return `${partes[2]}-${partes[1]}-${partes[0]}`
}

// Extrae el motivo del fallo de API para mostrarlo en el seguimiento.
function mensajeDeApi(datos, estado, porDefecto) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const campos = Object.entries(datos)
      .filter(([nombre]) => nombre !== 'mensaje' && nombre !== 'detail')
      .map(([nombre, valor]) => {
        const detalle = Array.isArray(valor) ? valor.join(', ') : String(valor)
        return `${nombre}: ${detalle}`
      })

    if (campos.length > 0) return campos.join(' | ')
  }

  return `${porDefecto} (HTTP ${estado}).`
}

// Renueva el token CSRF que acompañará la escritura desde el seguimiento.
async function tokenCsrf() {
  const respuesta = await fetch('/api/acceso/csrf/', {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })

  const datos = await respuesta.json().catch(() => ({}))

  if (!respuesta.ok || !datos.csrfToken) {
    throw new Error('No se pudo obtener el token de seguridad CSRF.')
  }

  return datos.csrfToken
}

// Integra estado, agenda, pago, entregas y reclamos de la referencia empresarial.
function Seguimiento() {
  const [webpayResultado] = useState(() => new URLSearchParams(window.location.search).get('webpay'))
  const [referencia, setReferencia] = useState(() => {
    // Recupera la referencia desde la URL para abrir el seguimiento correspondiente.
    const parametros = new URLSearchParams(window.location.search)
    const codigo = parametros.get('referencia') || ''

    if (codigo) {
      const urlLimpia = new URL(window.location.href)
      urlLimpia.searchParams.delete('referencia')
      window.history.replaceState(
        null,
        '',
        urlLimpia.pathname + urlLimpia.search + urlLimpia.hash,
      )
    }

    return codigo.length <= 500 ? codigo : ''
  })

  // Estados originales del seguimiento.
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [resultado, setResultado] = useState(null)
  const [seguimientoPrestacion, setSeguimientoPrestacion] = useState(null)
  const [errorPrestacion, setErrorPrestacion] = useState('')
  const [sinPrestacion, setSinPrestacion] = useState(false)
  const [revisandoEntrega, setRevisandoEntrega] = useState(null)
  const [observandoEntrega, setObservandoEntrega] = useState(null)
  const [detalleObservacion, setDetalleObservacion] = useState('')
  const [errorRevision, setErrorRevision] = useState('')
  const [avisoRevision, setAvisoRevision] = useState('')

  // Nuevos estados para los formularios empresariales.
  const [referenciaConsultada, setReferenciaConsultada] = useState('')
  const [motivoReclamo, setMotivoReclamo] = useState('')
  const [descripcionReclamo, setDescripcionReclamo] = useState('')
  const [evidenciaCancelacion, setEvidenciaCancelacion] = useState(null)
  const [enviandoReclamo, setEnviandoReclamo] = useState(false)
  const [errorReclamo, setErrorReclamo] = useState('')
  const [avisoReclamo, setAvisoReclamo] = useState('')
  const [reclamoEnviado, setReclamoEnviado] = useState(false)

  const [infoFeedback, setInfoFeedback] = useState(null)
  const [contenidoFeedback, setContenidoFeedback] = useState('')
  const [enviandoFeedback, setEnviandoFeedback] = useState(false)
  const [errorFeedback, setErrorFeedback] = useState('')
  const [avisoFeedback, setAvisoFeedback] = useState('')
  const [feedbackEnviado, setFeedbackEnviado] = useState(false)

  // Obtiene los datos de la prestación usando la referencia de seguimiento.
  async function consultar(evento) {
    evento.preventDefault()
    if (cargando) return

    const codigo = referencia.trim()

    setSeguimientoPrestacion(null)
    setErrorPrestacion('')
    setSinPrestacion(false)
    setObservandoEntrega(null)
    setDetalleObservacion('')
    setErrorRevision('')
    setAvisoRevision('')

    setReferenciaConsultada('')
    setMotivoReclamo('')
    setDescripcionReclamo('')
    setErrorReclamo('')
    setAvisoReclamo('')
    setReclamoEnviado(false)

    setInfoFeedback(null)
    setContenidoFeedback('')
    setErrorFeedback('')
    setAvisoFeedback('')
    setFeedbackEnviado(false)

    setResultado(null)
    setError('')

    if (!codigo || codigo.length > 500) {
      setError('Ingresa una referencia de seguimiento válida.')
      return
    }

    setCargando(true)

    try {
      const respuesta = await fetch(
        `/api/solicitudes/seguimiento/${encodeURIComponent(codigo)}/`,
        {
          method: 'GET',
          headers: { Accept: 'application/json' },
          cache: 'no-store',
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        const mensaje = datos.mensaje || datos.detail

        if (respuesta.status === 404) {
          throw new Error('La referencia no existe o no es válida.')
        }

        throw new Error(
          typeof mensaje === 'string'
            ? mensaje
            : `No fue posible consultar la solicitud (HTTP ${respuesta.status}).`,
        )
      }

      if (!datos.solicitud || typeof datos.solicitud !== 'object') {
        throw new Error('La API devolvió una respuesta inesperada.')
      }

      setResultado(datos)
      setReferenciaConsultada(codigo)

      try {
        const respuestaPrestacion = await fetch(
          `/api/seguimiento/empresa/${encodeURIComponent(codigo)}/prestacion/`,
          {
            method: 'GET',
            headers: { Accept: 'application/json' },
            cache: 'no-store',
          },
        )

        if (respuestaPrestacion.status === 404) {
          setSinPrestacion(true)
        } else {
          const datosPrestacion = await respuestaPrestacion
            .json()
            .catch(() => ({}))

          if (!respuestaPrestacion.ok) {
            throw new Error(
              typeof datosPrestacion.mensaje === 'string'
                ? datosPrestacion.mensaje
                : 'No fue posible consultar la prestación.',
            )
          }

          if (
            !datosPrestacion.prestacion ||
            !Array.isArray(datosPrestacion.avances) ||
            !Array.isArray(datosPrestacion.entregas)
          ) {
            throw new Error(
              'La API devolvió datos de seguimiento incompletos.',
            )
          }

          setSeguimientoPrestacion(datosPrestacion)

          // Consultar la habilitación de retroalimentación.
          // Un fallo aquí no debe ocultar avances ni entregas.
          try {
            const respuestaFeedback = await fetch(
              `/api/retroalimentacion/empresa/${encodeURIComponent(codigo)}/`,
              {
                method: 'GET',
                cache: 'no-store',
                headers: { Accept: 'application/json' },
              },
            )

            const datosFeedback = await respuestaFeedback
              .json()
              .catch(() => ({}))

            if (!respuestaFeedback.ok) {
              throw new Error(
                mensajeDeApi(
                  datosFeedback,
                  respuestaFeedback.status,
                  'No se pudo consultar la retroalimentación',
                ),
              )
            }

            if (
              typeof datosFeedback.feedback_habilitado !== 'boolean'
            ) {
              throw new Error(
                'La API devolvió un estado de retroalimentación inesperado.',
              )
            }

            setInfoFeedback(datosFeedback)
          } catch (falloFeedback) {
            setErrorFeedback(
              falloFeedback.message ||
              'No se pudo consultar el feedback privado.',
            )
          }
        }
      } catch (errorSeguimiento) {
        setErrorPrestacion(
          errorSeguimiento instanceof Error
            ? errorSeguimiento.message
            : 'No fue posible consultar la prestación.',
        )
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'No fue posible completar la consulta.',
      )
    } finally {
      setCargando(false)
    }
  }

  // Función original de revisión de entregas.
  async function revisarEntrega(entrega, accion) {
    if (
      revisandoEntrega !== null ||
      entrega.estado !== 'ENTREGADA'
    ) {
      return
    }

    const codigoReferencia = referencia.trim()

    if (!codigoReferencia) {
      setErrorRevision('No hay una referencia empresarial válida.')
      return
    }

    const detalle = detalleObservacion.trim()

    if (accion === 'OBSERVAR' && !detalle) {
      setErrorRevision(
        'Debes escribir las observaciones de la entrega.',
      )
      return
    }

    const mensajeConfirmacion = accion === 'ACEPTAR'
      ? `¿Confirmas que aceptas la entrega #${entrega.id_entrega}?`
      : `¿Confirmas que deseas enviar las observaciones de la entrega #${entrega.id_entrega}?`

    if (!window.confirm(mensajeConfirmacion)) return

    setRevisandoEntrega(entrega.id_entrega)
    setErrorRevision('')
    setAvisoRevision('')

    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datosCsrf = await respuestaCsrf
        .json()
        .catch(() => ({}))

      if (!respuestaCsrf.ok || !datosCsrf.csrfToken) {
        throw new Error(
          'No fue posible obtener la protección CSRF.',
        )
      }

      const respuesta = await fetch(
        `/api/seguimiento/empresa/${encodeURIComponent(codigoReferencia)}/entregas/${entrega.id_entrega}/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': datosCsrf.csrfToken,
            Accept: 'application/json',
          },
          body: JSON.stringify({
            accion,
            ...(accion === 'OBSERVAR' ? { detalle } : {}),
          }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        const mensaje = datos.mensaje || datos.detail

        throw new Error(
          typeof mensaje === 'string'
            ? mensaje
            : `No fue posible revisar la entrega (HTTP ${respuesta.status}).`,
        )
      }

      setAvisoRevision(
        accion === 'ACEPTAR'
          ? 'Entrega aceptada correctamente.'
          : 'Observaciones registradas correctamente.',
      )

      setObservandoEntrega(null)
      setDetalleObservacion('')

      const respuestaActualizada = await fetch(
        `/api/seguimiento/empresa/${encodeURIComponent(codigoReferencia)}/prestacion/`,
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      if (!respuestaActualizada.ok) {
        throw new Error(
          'La revisión fue registrada, pero no se pudo actualizar el listado.',
        )
      }

      const datosActualizados = await respuestaActualizada
        .json()
        .catch(() => ({}))

      if (
        !datosActualizados.prestacion ||
        !Array.isArray(datosActualizados.avances) ||
        !Array.isArray(datosActualizados.entregas)
      ) {
        throw new Error(
          'La revisión fue registrada, pero la respuesta de actualización es inválida.',
        )
      }

      setSeguimientoPrestacion(datosActualizados)
    } catch (errorAccion) {
      setErrorRevision(
        errorAccion instanceof Error
          ? errorAccion.message
          : 'No fue posible completar la revisión.',
      )
    } finally {
      setRevisandoEntrega(null)
    }
  }

  // NUEVO: reclamo empresarial.
  async function registrarReclamo(evento) {
    evento.preventDefault()

    if (
      enviandoReclamo ||
      reclamoEnviado ||
      !referenciaConsultada ||
      !seguimientoPrestacion?.prestacion
    ) {
      return
    }

    const motivo = motivoReclamo.trim()
    const descripcion = descripcionReclamo.trim()

    if (!motivo || motivo.length > 120 || !descripcion) {
      setErrorReclamo(
        'Indica un motivo de hasta 120 caracteres y describe el reclamo.',
      )
      return
    }

    if (
      !window.confirm(
        '¿Confirmas que deseas presentar este reclamo a Skilly?',
      )
    ) {
      return
    }

    setEnviandoReclamo(true)
    setErrorReclamo('')
    setAvisoReclamo('')

    try {
      const csrf = await tokenCsrf()

      const esCancelacion = motivo === 'Cancelación solicitada por la organización'
      const formulario = new FormData()
      formulario.append('motivo', motivo)
      formulario.append('descripcion', descripcion)
      if (esCancelacion && evidenciaCancelacion) formulario.append('evidencia', evidenciaCancelacion)
      const respuesta = await fetch(
        esCancelacion
          ? `/api/seguimiento/empresa/${encodeURIComponent(referenciaConsultada)}/cancelaciones/`
          : `/api/seguimiento/empresa/${encodeURIComponent(referenciaConsultada)}/reclamos/`,
        {
          method: 'POST', credentials: 'same-origin',
          headers: esCancelacion
            ? { 'X-CSRFToken': csrf, Accept: 'application/json' }
            : { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, Accept: 'application/json' },
          body: esCancelacion ? formulario : JSON.stringify({ motivo, descripcion }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          mensajeDeApi(
            datos,
            respuesta.status,
            'No se pudo registrar el reclamo',
          ),
        )
      }

      setAvisoReclamo(
        datos.mensaje ||
        'Reclamo registrado para gestión de Skilly.',
      )

      setReclamoEnviado(true)
      setMotivoReclamo('')
      setDescripcionReclamo('')
      setEvidenciaCancelacion(null)
    } catch (fallo) {
      setErrorReclamo(
        fallo.message ||
        'No se pudo registrar el reclamo.',
      )
    } finally {
      setEnviandoReclamo(false)
    }
  }

  // NUEVO: retroalimentación privada.
  async function registrarFeedback(evento) {
    evento.preventDefault()

    if (
      enviandoFeedback ||
      feedbackEnviado ||
      !referenciaConsultada ||
      !infoFeedback?.feedback_habilitado
    ) {
      return
    }

    const contenido = contenidoFeedback.trim()

    if (!contenido) {
      setErrorFeedback(
        'Escribe tu retroalimentación antes de enviarla.',
      )
      return
    }

    if (
      !window.confirm(
        '¿Confirmas enviar esta retroalimentación privada a Skilly?',
      )
    ) {
      return
    }

    setEnviandoFeedback(true)
    setErrorFeedback('')
    setAvisoFeedback('')

    try {
      const csrf = await tokenCsrf()

      const respuesta = await fetch(
        `/api/retroalimentacion/empresa/${encodeURIComponent(referenciaConsultada)}/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf,
            Accept: 'application/json',
          },
          body: JSON.stringify({ contenido }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          mensajeDeApi(
            datos,
            respuesta.status,
            'No se pudo enviar la retroalimentación',
          ),
        )
      }

      setAvisoFeedback(
        datos.mensaje ||
        'Retroalimentación privada registrada correctamente.',
      )

      setFeedbackEnviado(true)
      setContenidoFeedback('')
    } catch (fallo) {
      setErrorFeedback(
        fallo.message ||
        'No se pudo enviar la retroalimentación.',
      )
    } finally {
      setEnviandoFeedback(false)
    }
  }

  const solicitud = resultado?.solicitud
  const reserva = solicitud?.reserva
  const servicio = solicitud?.servicio
  const empresa = solicitud?.empresa

  const prestacion = seguimientoPrestacion?.prestacion
  const avances = seguimientoPrestacion?.avances ?? []
  const entregas = seguimientoPrestacion?.entregas ?? []

  return (
    <div className="sg-pagina">
      <header className="sg-cabecera">
        <a href="/" className="sg-marca">
          <svg
            width="25"
            height="25"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
            style={{
              verticalAlign: 'middle',
              marginRight: 9,
            }}
          >
            <path
              d="M12 1L14.7 9.3L23 12L14.7 14.7L12 23L9.3 14.7L1 12L9.3 9.3L12 1Z"
              fill="#447D69"
            />
          </svg>
          SKILLY
        </a>

        <a href="/#marketplace" className="sg-volver">
          Volver al marketplace
        </a>
      </header>
      {webpayResultado && (
        <div className="sg-nota" role="status" style={{ marginBottom: 14 }}>
          {webpayResultado === 'aprobado'
            ? 'Webpay confirmó la autorización en ambiente de pruebas. Consulta el seguimiento para ver el pago.'
            : webpayResultado === 'agenda_pendiente'
              ? 'Webpay confirmó el pago de prueba, pero administración debe regularizar el horario.'
              : webpayResultado === 'revision'
              ? 'Webpay necesita conciliación administrativa. No repitas el pago.'
              : webpayResultado === 'cancelado'
                ? 'Cancelaste el pago de prueba. Puedes elegir un nuevo intento.'
                : 'Webpay no autorizó la operación de prueba. Puedes consultar el estado y reintentar.'}
        </div>
      )}


      <main className="sg-contenido">
        <div className="sg-intro">
          <span className="sg-etiqueta">
            SKILLY LATAM
          </span>

          <h1>Seguimiento de solicitudes</h1>

          <p>
            Consulta el estado de tu solicitud con la
            referencia entregada al registrarla.
            No necesitas crear una cuenta.
          </p>
        </div>

        <section className="sg-tarjeta">
          <h2>Buscar una solicitud</h2>

          <form onSubmit={consultar}>
            <label htmlFor="sg-referencia">
              Referencia de seguimiento
            </label>

            <div className="sg-fila">
              <input
                id="sg-referencia"
                name="referencia"
                type="text"
                value={referencia}
                onChange={(evento) =>
                  setReferencia(evento.target.value)
                }
                maxLength={500}
                placeholder="Pega tu referencia"
                autoComplete="off"
                required
              />

              <button
                type="submit"
                disabled={cargando}
              >
                {cargando
                  ? 'Consultando...'
                  : 'Consultar estado'}
              </button>
            </div>
          </form>

          {error && (
            <div
              className="sg-error"
              role="alert"
            >
              {error}
            </div>
          )}
        </section>

        {solicitud && (
          <nav className="sg-navegacion-resumen" aria-label="Secciones del seguimiento">
            <a href="#sg-solicitud">01 · Solicitud</a>
            <a href="#sg-servicio">02 · Servicio</a>
            <a href="#sg-ayuda">03 · Ayuda y opinión</a>
            <a href="#sg-pago">04 · Pago</a>
          </nav>
        )}

        {solicitud && (
          <section
            id="sg-solicitud"
            className="sg-tarjeta sg-resultado"
            aria-live="polite"
          >
            <div className="sg-titulo-resultado">
              <div>
                <span className="sg-etiqueta">
                  SOLICITUD ENCONTRADA
                </span>

                <h2>Estado de tu solicitud</h2>
              </div>

              <span className="sg-estado">
                {texto(solicitud.estado)}
              </span>
            </div>

            <div className="sg-grilla">
              <div>
                <span>Referencia</span>

                <strong className="sg-codigo sg-codigo-seguro">Referencia validada</strong>
              </div>

              <div>
                <span>Servicio</span>
                <strong>
                  {texto(servicio?.nombre)}
                </strong>
              </div>

              <div>
                <span>Organización</span>
                <strong>
                  {texto(
                    empresa?.nombre_organizacion,
                  )}
                </strong>
              </div>

              <div>
                <span>Objetivo</span>
                <strong>
                  {texto(solicitud.objetivo)}
                </strong>
              </div>

              <div>
                <span>Fecha de solicitud</span>
                <strong>
                  {formatoFecha(
                    solicitud.fecha_solicitud,
                  )}
                </strong>
              </div>

              <div>
                <span>Estado de reserva</span>

                <strong>
                  {reserva
                    ? texto(reserva.estado)
                    : 'Sin reserva activa o pendiente'}
                </strong>
              </div>
            </div>

            {reserva && (
              <div className="sg-reserva">
                <h3>Primera reunión</h3>

                <p>
                  Fecha:{' '}
                  {formatoFecha(reserva.fecha)}
                </p>

                <p>
                  Horario:{' '}
                  {texto(reserva.hora_inicio)}
                  {' a '}
                  {texto(reserva.hora_fin)}
                </p>

                <p>
                  {reserva.confirmada === true
                    ? 'Reserva confirmada'
                    : 'Reserva pendiente de confirmación'}
                </p>
              </div>
            )}

            {prestacion && referenciaConsultada && (
              <ReagendamientosOrganizacion referencia={referenciaConsultada} estadoPrestacion={prestacion.estado} />
            )}

            <div className="sg-nota">
              Una solicitud recibida o una reserva
              pendiente de pago no acreditan una
              contratación ni un pago realizado.
            </div>
          </section>
        )}

        {solicitud && sinPrestacion && (
          <section className="sg-tarjeta sg-panel-prestacion">
            <h2>Prestación del servicio</h2>

            <p>
              Todavía no existe una prestación
              disponible para esta solicitud.
              Esto no confirma contratación ni pago.
            </p>
          </section>
        )}

        {solicitud && errorPrestacion && (
          <section className="sg-tarjeta sg-panel-prestacion">
            <h2>Seguimiento de la prestación</h2>

            <div
              className="sg-error"
              role="alert"
            >
              {errorPrestacion}
            </div>
          </section>
        )}

        {solicitud && prestacion && (
          <details id="sg-servicio" className="sg-acordeon" open>
            <summary><span><small>02 · DETALLE</small> Servicio, condiciones y entregas</span><span className="sg-flecha">⌄</span></summary>
          <section className="sg-tarjeta sg-panel-prestacion">
            <span className="sg-etiqueta">
              SEGUIMIENTO EMPRESARIAL
            </span>

            <h2>Prestación del servicio</h2>

            <div className="sg-grilla">
              <div>
                <span>Número de prestación</span>
                <strong>
                  #{prestacion.id_prestacion}
                </strong>
              </div>

              <div>
                <span>Estado</span>
                <strong>
                  {texto(prestacion.estado)}
                </strong>
              </div>

              <div>
                <span>Fecha de inicio</span>
                <strong>
                  {formatoFecha(
                    prestacion.fecha_inicio,
                  )}
                </strong>
              </div>

              <div>
                <span>Fecha de término</span>
                <strong>
                  {formatoFecha(
                    prestacion.fecha_fin,
                  )}
                </strong>
              </div>

              <div>
                <span>Fecha de cierre</span>
                <strong>
                  {formatoFecha(
                    prestacion.fecha_cierre,
                  )}
                </strong>
              </div>
            </div>

            <div className="sg-bloque-listado">
              <h3>Condiciones de la prestación</h3>
              {typeof prestacion.condiciones_comunicadas === 'string' &&
              prestacion.condiciones_comunicadas.trim() ? (
                <CondicionesPrestacionE3 texto={prestacion.condiciones_comunicadas} />
              ) : (
                <p>
                  SKILLY todavía no ha publicado las condiciones
                  para esta solicitud. No corresponde informar
                  una transferencia hasta que estén disponibles.
                </p>
              )}
            </div>

            <div className="sg-bloque-listado">
              <h3>Avances del servicio</h3>

              {avances.length === 0 ? (
                <p>
                  Aún no se han registrado avances.
                </p>
              ) : (
                <div className="sg-listado">
                  {avances.map((avance) => (
                    <article
                      className="sg-elemento"
                      key={avance.id_avance}
                    >
                      <div className="sg-elemento-cabecera">
                        <strong>
                          {texto(avance.estado)}
                        </strong>

                        <span>
                          {formatoFecha(
                            avance.fecha_registro,
                          )}
                        </span>
                      </div>

                      <p>
                        {texto(avance.detalle)}
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </div>

            <div className="sg-bloque-listado">
              <h3>Entregas del servicio</h3>

              {errorRevision && (
                <div
                  className="sg-error"
                  role="alert"
                >
                  {errorRevision}
                </div>
              )}

              {avisoRevision && (
                <div
                  className="sg-aviso"
                  role="status"
                >
                  {avisoRevision}
                </div>
              )}

              {entregas.length === 0 ? (
                <p>
                  Todavía no hay entregas registradas.
                </p>
              ) : (
                <div className="sg-listado">
                  {entregas.map((entrega) => (
                    <article
                      className="sg-elemento"
                      key={entrega.id_entrega}
                    >
                      <div className="sg-elemento-cabecera">
                        <strong>
                          Entrega #{entrega.id_entrega}
                          {' — '}
                          Versión {texto(entrega.version)}
                        </strong>

                        <span>
                          {texto(entrega.estado)}
                        </span>
                      </div>

                      <p>
                        {texto(entrega.descripcion)}
                      </p>
                      <AdjuntosEntregaEmpresaE3
                        referencia={referencia.trim()}
                        idEntrega={entrega.id_entrega}
                      />

                      <p>
                        <strong>
                          Referencia:
                        </strong>
                        {' '}
                        {texto(
                          entrega.referencia_entrega,
                        )}
                      </p>

                      <p>
                        <strong>
                          Fecha:
                        </strong>
                        {' '}
                        {formatoFecha(
                          entrega.fecha_entrega,
                        )}
                      </p>

                      {entrega.estado === 'ENTREGADA' && (
                        <div className="sg-acciones-entrega">
                          <button
                            type="button"
                            disabled={
                              revisandoEntrega !== null
                            }
                            onClick={() =>
                              revisarEntrega(
                                entrega,
                                'ACEPTAR',
                              )
                            }
                          >
                            {revisandoEntrega === entrega.id_entrega
                              ? 'Procesando...'
                              : 'Aceptar entrega'}
                          </button>

                          <button
                            type="button"
                            className="sg-boton-secundario"
                            disabled={
                              revisandoEntrega !== null
                            }
                            onClick={() => {
                              // Prepara la observación de la entrega elegida y limpia el error anterior.
                              setErrorRevision('')

                              setObservandoEntrega(
                                observandoEntrega === entrega.id_entrega
                                  ? null
                                  : entrega.id_entrega,
                              )

                              setDetalleObservacion('')
                            }}
                          >
                            Registrar observaciones
                          </button>
                        </div>
                      )}

                      {entrega.estado === 'ENTREGADA' &&
                        observandoEntrega === entrega.id_entrega && (
                          <div className="sg-formulario-observacion">
                            <label
                              htmlFor={`sg-observacion-${entrega.id_entrega}`}
                            >
                              Detalle de las observaciones
                            </label>

                            <textarea
                              id={`sg-observacion-${entrega.id_entrega}`}
                              rows={4}
                              maxLength={3000}
                              value={detalleObservacion}
                              onChange={(evento) =>
                                setDetalleObservacion(
                                  evento.target.value,
                                )
                              }
                              disabled={
                                revisandoEntrega !== null
                              }
                              placeholder="Describe las observaciones de la entrega"
                            />

                            <button
                              type="button"
                              disabled={
                                revisandoEntrega !== null ||
                                !detalleObservacion.trim()
                              }
                              onClick={() =>
                                revisarEntrega(
                                  entrega,
                                  'OBSERVAR',
                                )
                              }
                            >
                              Enviar observaciones
                            </button>
                          </div>
                        )}
                    </article>
                  ))}
                </div>
              )}
            </div>

            <div className="sg-nota">
              La visualización de una prestación no
              confirma por sí sola un pago realizado.
              La contratación requiere las condiciones
              verificadas por Skilly.
            </div>
          </section>
          </details>
        )}

        <div id="sg-ayuda" className="sg-grupo-ayuda">
        {/* NUEVO: formulario de reclamos empresariales. */}
        {solicitud && prestacion && (
          <details className="sg-acordeon">
            <summary><span><small>03 · AYUDA</small> Presentar un reclamo</span><span className="sg-flecha">⌄</span></summary>
          <section className="sg-tarjeta sg-panel-prestacion">
            <span className="sg-etiqueta">
              ATENCIÓN EMPRESARIAL
            </span>

            <h2>Formulario de reclamo</h2>

            <p>
              Si tienes un problema con la prestación,
              puedes enviar un reclamo para su revisión
              por Skilly. El reclamo no genera
              devoluciones automáticas.
            </p>

            {errorReclamo && (
              <div className="sg-error" role="alert">
                {errorReclamo}
              </div>
            )}

            {avisoReclamo && (
              <div className="sg-aviso" role="status">
                {avisoReclamo}
              </div>
            )}

            {!reclamoEnviado && (
              <form
                className="sg-formulario-observacion"
                onSubmit={registrarReclamo}
              >
                <label htmlFor="sg-motivo">
                  ¿Qué ocurrió con el servicio o la reunión?
                </label>

                <select
                  id="sg-motivo"
                  required
                  value={motivoReclamo}
                  onChange={(evento) => setMotivoReclamo(evento.target.value)}
                  disabled={enviandoReclamo}
                  style={{
                    width: '100%',
                    padding: 14,
                    border: '1px solid #ceded5',
                    borderRadius: 10,
                    font: 'inherit',
                  }}
                >
                  <option value="">Selecciona el motivo</option>
                  <option>Inasistencia del profesional a la reunión</option>
                  <option>Cancelación solicitada por la organización</option>
                  <option>Cancelación solicitada por el profesional</option>
                  <option>Solicitud de reprogramación de la reunión</option>
                  <option>Abandono o interrupción del servicio</option>
                  <option>Incumplimiento de entregables o condiciones</option>
                  <option>Otro incidente de la prestación</option>
                </select>
                <p className="sg-nota">
                  La solicitud de reprogramación o cancelación se envía
                  a revisión de Skilly: no modifica automáticamente la
                  agenda ni el estado del pago.
                </p>

                <label htmlFor="sg-descripcion-reclamo">
                  Descripción del problema
                </label>

                <textarea
                  id="sg-descripcion-reclamo"
                  required
                  rows={4}
                  value={descripcionReclamo}
                  onChange={(evento) =>
                    setDescripcionReclamo(
                      evento.target.value,
                    )
                  }
                  disabled={enviandoReclamo}
                  placeholder="Explica lo ocurrido para que Skilly pueda revisarlo."
                />

                {motivoReclamo === 'Cancelación solicitada por la organización' && (
                  <div className="sg-nota">
                    <label htmlFor="sg-evidencia-cancelacion">Documento justificativo (opcional, privado, PDF/JPG/PNG, máximo 5 MB)</label>
                    <input id="sg-evidencia-cancelacion" type="file" accept=".pdf,.jpg,.jpeg,.png"
                      disabled={enviandoReclamo}
                      onChange={(evento) => setEvidenciaCancelacion(evento.target.files?.[0] || null)} />
                    <p>SKILLY revisará la solicitud antes de cancelar o determinar reembolsos. No subas información médica sensible.</p>
                  </div>
                )}
                <button
                  type="submit"
                  disabled={
                    enviandoReclamo ||
                    !motivoReclamo.trim() ||
                    !descripcionReclamo.trim()
                  }
                >
                  {enviandoReclamo
                    ? 'Enviando…'
                    : 'Enviar reclamo a Skilly'}
                </button>
              </form>
            )}
          </section>
          </details>
        )}

        {/* NUEVO: retroalimentación privada empresarial. */}
        {solicitud && prestacion && (
          <details className="sg-acordeon">
            <summary><span><small>OPINIÓN PRIVADA</small> Retroalimentación privada</span><span className="sg-flecha">⌄</span></summary>
          <section className="sg-tarjeta sg-panel-prestacion">
            <span className="sg-etiqueta">
              OPINIÓN PRIVADA
            </span>

            <h2>Retroalimentación para Skilly</h2>

            <p>
              Tu comentario es privado: Skilly
              lo utiliza para revisar la prestación
              y generar recomendaciones internas.
              No se publica como calificación
              del profesional.
            </p>

            {errorFeedback && (
              <div
                className="sg-error"
                role="alert"
              >
                {errorFeedback}
              </div>
            )}

            {avisoFeedback && (
              <div
                className="sg-aviso"
                role="status"
              >
                {avisoFeedback}
              </div>
            )}

            {!infoFeedback && !errorFeedback && (
              <p role="status">
                Consultando si la prestación
                admite retroalimentación…
              </p>
            )}

            {infoFeedback &&
              !infoFeedback.feedback_habilitado && (
                <div className="sg-nota">
                  La retroalimentación se habilita
                  cuando la prestación esté FINALIZADA.

                  <p>
                    Estado actual:{' '}
                    <strong>
                      {texto(prestacion.estado)}
                    </strong>
                  </p>
                </div>
              )}

            {infoFeedback?.feedback_habilitado &&
              !feedbackEnviado && (
                <form
                  className="sg-formulario-observacion"
                  onSubmit={registrarFeedback}
                >
                  <label htmlFor="sg-feedback">
                    Comentario privado de la empresa
                  </label>

                  <textarea
                    id="sg-feedback"
                    required
                    rows={5}
                    value={contenidoFeedback}
                    onChange={(evento) =>
                      setContenidoFeedback(
                        evento.target.value,
                      )
                    }
                    disabled={enviandoFeedback}
                    placeholder="Describe tu experiencia y oportunidades de mejora."
                  />

                  <button
                    type="submit"
                    disabled={
                      enviandoFeedback ||
                      !contenidoFeedback.trim()
                    }
                  >
                    {enviandoFeedback
                      ? 'Enviando…'
                      : 'Enviar retroalimentación privada'}
                  </button>
                </form>
              )}
          </section>
          </details>
        )}
        </div>

        {solicitud && prestacion && referenciaConsultada && (
          <details id="sg-pago" className="sg-acordeon sg-acordeon-pago" open>
            <summary><span><small>04 · ECONOMÍA</small> Pago y transferencia</span><span className="sg-flecha">⌄</span></summary>
            <PagoEmpresaSeguimiento
              referencia={referenciaConsultada}
              prestacion={prestacion}
            />
          </details>
        )}

        <footer className="sg-pie">
          Skilly - Plataforma de servicios profesionales
        </footer>
      </main>
    </div>
  )
}

export default Seguimiento
