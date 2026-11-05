
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

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

function mensajeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') {
    return datos.mensaje
  }

  if (typeof datos?.detail === 'string') {
    return datos.detail
  }

  return `No se pudo consultar el seguimiento (HTTP ${codigo}).`
}

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
    if (!abierto) return undefined

    const controlador = new AbortController()

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
          !Array.isArray(contenido.avances)
        ) {
          throw new Error(
            'La API devolvió información de seguimiento incompleta.',
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

  function abrir() {
    setDatos(null)
    setError('')
    setAvisoCierre('')
    setAbierto(true)
  }

  function cerrar() {
    setAbierto(false)
  }

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

  const prestacion = datos?.prestacion
  const avances = datos?.avances ?? []
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
                Consulta los avances registrados de la prestación #{idPrestacion}.
              </p>
              <button
                type="button"
                className="adm-accion adm-accion-seguimiento"
                onClick={abrir}
              >
                Consultar avances
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
                  Esta consulta presenta la prestación
                  y sus avances. Las entregas, reclamos
                  y pagos se gestionan en sus
                  respectivos flujos. La consulta
                  no modifica la contratación.
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
