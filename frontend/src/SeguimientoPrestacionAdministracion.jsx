
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

// Presenta los registros en formato local y conserva el día civil de las fechas sin hora.
function formatoFecha(valor) {
  if (!valor) return 'No registrada'

  const dia = /^(\d{4})-(\d{2})-(\d{2})$/.exec(
    String(valor),
  )

  if (dia) {
    return `${dia[3]}-${dia[2]}-${dia[1]}`
  }

  const fecha = new Date(valor)

  if (Number.isNaN(fecha.getTime())) {
    return String(valor)
  }

  return fecha.toLocaleString('es-CL', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

// Presenta el rechazo de la API en términos útiles para revisar o reintentar.
function mensajeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') {
    return datos.mensaje
  }

  if (typeof datos?.detail === 'string') {
    return datos.detail
  }

  return `No se pudo consultar el seguimiento (HTTP ${codigo}).`
}

// Consulta el historial y presenta la acción de cierre según la respuesta del backend.
export default function SeguimientoPrestacionAdministracion({
  idPrestacion,
  estadoPrestacion,
}) {
  const dialogoRef = useRef(null)

  const [abierto, setAbierto] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [datos, setDatos] = useState(null)
  const [revision, setRevision] = useState(0)
  const [finalizando, setFinalizando] = useState(false)
  const [avisoCierre, setAvisoCierre] = useState('')

  // Ventana nativa en la capa superior del navegador.
  // Evita quedar detrás del detalle empresarial.
  useEffect(() => {
    // Sincroniza la apertura del diálogo nativo con el estado del panel.
    if (!abierto) return undefined

    const dialogo = dialogoRef.current

    if (dialogo && !dialogo.open) {
      dialogo.showModal()
    }

    return () => {
      if (dialogo?.open) {
        dialogo.close()
      }
    }
  }, [abierto])

  // Consulta de solo lectura.
  useEffect(() => {
    // Cancela la consulta de seguimiento al cerrar o cambiar de prestación.
    if (!abierto) return undefined

    const controlador = new AbortController()

    // Consulta la prestación y verifica que el historial recibido tenga todos los grupos.
    async function consultar() {
      setCargando(true)
      setError('')

      try {
        const respuesta = await fetch(
          `/api/seguimiento/administracion/prestaciones/${encodeURIComponent(idPrestacion)}/`,
          {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              Accept: 'application/json',
            },
            signal: controlador.signal,
          },
        )

        const contenido = await respuesta
          .json()
          .catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(
            mensajeError(
              contenido,
              respuesta.status,
            ),
          )
        }

        if (
          !contenido.prestacion ||
          !Array.isArray(contenido.avances) ||
          !Array.isArray(contenido.entregas) ||
          !Array.isArray(contenido.observaciones)
        ) {
          throw new Error(
            'El servidor Django SKILLY todavía no entrega el historial de entregas. Reinicia solamente el backend de SKILLY.',
          )
        }

        if (!controlador.signal.aborted) {
          setDatos(contenido)
        }
      } catch (fallo) {
        if (!controlador.signal.aborted) {
          setError(
            fallo instanceof Error
              ? fallo.message
              : 'No se pudo consultar el seguimiento.',
          )
        }
      } finally {
        if (!controlador.signal.aborted) {
          setCargando(false)
        }
      }
    }

    void consultar()

    return () => controlador.abort()
  }, [abierto, idPrestacion, revision])

  // Inicializa la consulta de seguimiento al abrir el diálogo.
  function abrir() {
    setDatos(null)
    setError('')
    setAvisoCierre('')
    setAbierto(true)
  }

  // Cierra la consulta de seguimiento sin cambiar la prestación.
  function cerrar() {
    setAbierto(false)
  }

  // Solicita el cierre después de leer el token CSRF y recarga el estado confirmado.
  async function finalizarPrestacion() {
    if (!datos?.cierre?.habilitado || finalizando) return
    if (!window.confirm(`¿Finalizar formalmente la prestación #${idPrestacion}? Esta acción no libera el pago.`)) return
    setFinalizando(true)
    setError('')
    setAvisoCierre('')
    try {
      const csrfResponse = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin', cache: 'no-store',
      })
      const csrf = await csrfResponse.json().catch(() => ({}))
      if (!csrfResponse.ok || !csrf.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }
      const respuesta = await fetch(
        `/api/seguimiento/administracion/prestaciones/${encodeURIComponent(idPrestacion)}/`,
        {
          method: 'POST', credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf.csrfToken },
          body: JSON.stringify({ accion: 'FINALIZAR_PRESTACION' }),
        },
      )
      const contenido = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(mensajeError(contenido, respuesta.status))
      setAvisoCierre(contenido.mensaje || 'Prestación finalizada.')
      setRevision((actual) => actual + 1)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No fue posible finalizar la prestación.')
    } finally {
      setFinalizando(false)
    }
  }

  // Avances y entregas son historiales independientes y se presentan por separado.
  const prestacion = datos?.prestacion
  const avances = datos?.avances ?? []
  const entregas = datos?.entregas ?? []
  const observaciones = datos?.observaciones ?? []
  const avisosProfesional = avances.filter((avance) => avance.estado === 'INCIDENCIA_REPORTADA')
  // La ficha usa el estado del padre; tras cerrar, prevalece el estado
  // recién consultado al backend sin requerir actualizar la página.
  const prestacionFinalizada =
    prestacion?.estado === 'FINALIZADA' ||
    (!prestacion && estadoPrestacion === 'FINALIZADA')

  return (
    <>
      <div className="adm-detalle-pago">
        {prestacionFinalizada ? (
          <div role="status" style={{ display: 'grid', gap: 7 }}>
            <strong style={{ color: '#2e594b' }}>
              Prestación finalizada
            </strong>
            <p style={{ margin: 0, color: '#61756a', lineHeight: 1.55 }}>
              El cierre formal de la prestación #{idPrestacion} está registrado.
              Los avances y entregas se conservan en el historial.
              El pago se gestiona por separado.
            </p>
          </div>
        ) : (
          <>
            <div className="adm-seguimiento-accion-fila">
              <p className="adm-seguimiento-accion-descripcion">
                Consulta los avances y las entregas de la prestación #{idPrestacion}.
              </p>
              <button
                type="button"
                className="adm-accion adm-accion-seguimiento"
                onClick={abrir}
              >
                Consultar seguimiento
              </button>
            </div>
          </>
        )}
      </div>

      {abierto && createPortal(
        <>
          <style>{`
            .sk-seguimiento-dialogo::backdrop {
              background: rgba(11, 30, 25, 0.74);
              backdrop-filter: blur(2px);
            }
          `}</style>

          <dialog
            ref={dialogoRef}
            className="sk-seguimiento-dialogo"
            aria-labelledby="adm-seguimiento-titulo"
            onCancel={(evento) => {
              evento.preventDefault()
              cerrar()
            }}
            onClose={cerrar}
            style={{
              width: 'min(760px, calc(100vw - 36px))',
              maxWidth: 'calc(100vw - 36px)',
              maxHeight: '88vh',
              overflowY: 'auto',
              margin: 'auto',
              padding: 26,
              border: 'none',
              borderRadius: 22,
              boxSizing: 'border-box',
              background: '#fff',
              color: '#203a38',
              boxShadow:
                '0 24px 90px rgba(0, 0, 0, 0.3)',
            }}
          >
            <div className="adm-panel-header">
              <div>
                <span className="adm-eyebrow">
                  CONSULTA DE SOLO LECTURA
                </span>

                <h2 id="adm-seguimiento-titulo">
                  Prestación #{idPrestacion}
                </h2>
              </div>

              <button
                type="button"
                className="adm-secundario"
                onClick={cerrar}
              >
                ✕ Cerrar
              </button>
            </div>

            {cargando && (
              <p role="status">
                Consultando avances…
              </p>
            )}

            {error && (
              <p
                className="adm-error"
                role="alert"
              >
                {error}
              </p>
            )}

            {prestacion && (
              <>
                <div className="adm-datos">
                  <div>
                    <small>Estado</small>

                    <strong>
                      {prestacion.estado ||
                        'No informado'}
                    </strong>
                  </div>

                  <div>
                    <small>Solicitud</small>

                    <strong>
                      #{prestacion.id_solicitud}
                    </strong>
                  </div>

                  <div>
                    <small>Profesional</small>

                    <strong>
                      #{prestacion.id_profesional}
                    </strong>
                  </div>

                  <div>
                    <small>Fecha de inicio</small>

                    <strong>
                      {formatoFecha(
                        prestacion.fecha_inicio,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Fecha de término</small>

                    <strong>
                      {formatoFecha(
                        prestacion.fecha_fin,
                      )}
                    </strong>
                  </div>

                  <div>
                    <small>Fecha de cierre</small>

                    <strong>
                      {formatoFecha(
                        prestacion.fecha_cierre,
                      )}
                    </strong>
                  </div>
                </div>

                {avisosProfesional.length > 0 && (
                  <section className="adm-detalle-pago" role="status">
                    <h3>Avisos informados por el profesional ({avisosProfesional.length})</h3>
                    <p>Estos avisos aportan antecedentes para coordinación y seguimiento.
                      No sustituyen una cancelación formal, un reclamo empresarial ni una reversa económica.</p>
                    {avisosProfesional.map((aviso) => (
                      <article key={aviso.id_avance} className="adm-item"
                        style={{ marginTop: 12, display: 'grid', gap: 6 }}>
                        <strong>Incidencia #{aviso.id_avance} · {formatoFecha(aviso.fecha_registro)}</strong>
                        <span style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                          {aviso.detalle || 'Sin detalle.'}
                        </span>
                      </article>
                    ))}
                    <p className="adm-nota">Si corresponde cambiar la agenda, utiliza el módulo de coordinación.
                      Si existe una disputa económica, utiliza reclamos y pagos; no hagas descuentos automáticos.</p>
                  </section>
                )}
                <section className="adm-detalle-pago">
                  <h3>Cierre formal de la prestación</h3>
                  {avisoCierre && <p role="status" className="adm-aviso">{avisoCierre}</p>}
                  {prestacion.estado === 'FINALIZADA' ? (
                    <p>Esta prestación se encuentra finalizada. El pago se gestiona por separado.</p>
                  ) : (
                    <>
                      {(datos.cierre?.razones ?? []).map((motivo) => (
                        <p key={motivo} className="adm-nota">{motivo}</p>
                      ))}
                      <button
                        type="button"
                        className="adm-accion"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          minHeight: 44,
                          padding: '12px 18px',
                          border: '1px solid transparent',
                          borderRadius: 10,
                          backgroundColor: (!datos.cierre?.habilitado || finalizando)
                            ? '#8ba39b'
                            : '#355e52',
                          color: '#ffffff',
                          fontSize: 14,
                          fontWeight: 700,
                          lineHeight: 1.3,
                          cursor: (!datos.cierre?.habilitado || finalizando)
                            ? 'not-allowed'
                            : 'pointer',
                        }}
                        onClick={finalizarPrestacion}
                        disabled={!datos.cierre?.habilitado || finalizando}
                      >
                        {finalizando ? 'Finalizando prestación...' : 'Finalizar prestación'}
                      </button>
                      <p className="adm-nota">La finalización registra el cierre del servicio. No libera ni modifica el pago.</p>
                    </>
                  )}
                </section>

                <section className="adm-detalle-pago">
                  <h3>Entregas registradas ({entregas.length})</h3>
                  <p className="adm-nota">
                    Las entregas y los avances son registros independientes. Una entrega aprobada
                    no crea automáticamente un avance. Este historial es de solo lectura.
                  </p>
                  {entregas.length === 0 ? (
                    <p className="adm-vacio">No hay entregas registradas.</p>
                  ) : (
                    <div className="adm-lista">
                      {entregas.map((entrega) => (
                        <article className="adm-item" key={entrega.id_entrega}
                          style={{ display: 'grid', gap: 8, overflowWrap: 'anywhere' }}>
                          <strong>Entrega #{entrega.id_entrega} · Versión {entrega.version}</strong>
                          <span className="adm-estado">Estado: {entrega.estado}</span>
                          <small>{formatoFecha(entrega.fecha_entrega)}</small>
                          <span style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                            {entrega.descripcion || 'Sin descripción.'}
                          </span>
                          {entrega.referencia_entrega && (
                            <small>Referencia: {entrega.referencia_entrega}</small>
                          )}
                          {observaciones.filter((obs) =>
                            Number(obs.id_entrega) === Number(entrega.id_entrega)
                          ).map((obs) => (
                            <div key={obs.id_observacion} style={{
                              borderLeft: '3px solid #4a7967', paddingLeft: 12,
                              display: 'grid', gap: 4,
                            }}>
                              <strong>Observaciones de la organización</strong>
                              <small>{formatoFecha(obs.fecha)}</small>
                              <span style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                                {obs.detalle || 'Sin detalle.'}
                              </span>
                            </div>
                          ))}
                        </article>
                      ))}
                    </div>
                  )}
                </section>

                <div className="adm-panel-header">
                  <h3>
                    Avances registrados
                    {' ('}{avances.length}{')'}
                  </h3>

                  <button
                    type="button"
                    className="adm-secundario"
                    disabled={cargando}
                    onClick={() =>
                      setRevision(
                        (actual) => actual + 1,
                      )
                    }
                  >
                    ↻ Actualizar
                  </button>
                </div>

                {avances.length === 0 ? (
                  <p className="adm-vacio">
                    Todavía no existen avances
                    registrados.
                  </p>
                ) : (
                  <div className="adm-lista">
                    {avances.map((avance) => (
                      <article
                        className="adm-item"
                        key={avance.id_avance}
                      >
                        <span className="adm-item-cuerpo">
                          <strong>
                            Avance #{avance.id_avance}
                          </strong>

                          <small>
                            {formatoFecha(
                              avance.fecha_registro,
                            )}
                          </small>

                          <span
                            style={{
                              whiteSpace: 'pre-wrap',
                              overflowWrap: 'anywhere',
                            }}
                          >
                            {avance.detalle ||
                              'Sin detalle registrado.'}
                          </span>
                        </span>

                        <span className="adm-estado">
                          {avance.estado}
                        </span>
                      </article>
                    ))}
                  </div>
                )}

                <p
                  className="adm-nota"
                  style={{ marginTop: 20 }}
                >
                  Esta consulta presenta la prestación, sus avances,
                  las entregas y observaciones registradas. Los reclamos
                  y los pagos siguen en sus respectivos módulos.
                  Consultar no modifica la contratación.
                </p>
              </>
            )}
          </dialog>
        </>,
        document.body,
      )}
    </>
  )
}
