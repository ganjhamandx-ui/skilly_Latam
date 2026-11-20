
// Consolida indicadores administrativos de solo lectura y descarta respuestas obsoletas.
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import AdminNavegacion from './AdminNavegacion.jsx'
import useDialogoAccesible from './useDialogoAccesible.js'
import './Administracion.css'

const TARJETAS = [
  {
    clave: 'profesionales',
    titulo: 'Profesionales',
    descripcion: 'Estados de validación',
  },
  {
    clave: 'solicitudes',
    titulo: 'Solicitudes',
    descripcion: 'Estados de solicitudes',
  },
  {
    clave: 'prestaciones',
    titulo: 'Prestaciones',
    descripcion: 'Estados de prestaciones',
  },
  {
    clave: 'pagos',
    titulo: 'Pagos',
    descripcion: 'Estados y montos de pagos',
  },
]

/**
 * Presenta un importe de los indicadores en CLP con hasta dos decimales.
 * @param {number|string|null} valor Dato numérico; null o undefined se representan como cero.
 * @returns {string} Importe regional o «No disponible» si no es finito.
 */
function monto(valor) {
  const numero = Number(valor ?? 0)

  if (!Number.isFinite(numero)) {
    return 'No disponible'
  }

  return `${new Intl.NumberFormat('es-CL', {
    maximumFractionDigits: 2,
  }).format(numero)} CLP`
}

/**
 * Obtiene el mensaje de rechazo de indicadores o incluye el código HTTP como alternativa.
 * @param {Object|null} datos Respuesta JSON del servidor.
 * @param {number} codigo Estado HTTP.
 * @returns {string} Mensaje según el contrato textual del endpoint.
 */
function mensajeError(datos, codigo) {
  return (
    datos?.mensaje ||
    datos?.detail ||
    `No se pudo consultar indicadores (HTTP ${codigo}).`
  )
}

/**
 * Consulta conteos, estados e importes calculados por el backend y permite explorar su detalle.
 * @returns {import('react').ReactElement} Panel de indicadores de solo lectura con diálogo accesible.
 */
export default function IndicadoresAdministracion() {
  const [datos, setDatos] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [detalle, setDetalle] = useState(null)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    // Descarta el resultado cuando cambia la revisión o se desmonta esta consulta.
    let activo = true

    /**
     * Exige indicadores, estados y resumen_financiero antes de aplicar la respuesta vigente.
     * @returns {Promise<void>} Presenta los errores de consulta sin inventar cifras ausentes.
     */
    async function consultar() {
      try {
        const respuesta = await fetch(
          '/api/backoffice/indicadores/',
          {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              Accept: 'application/json',
            },
          },
        )

        const contenido = await respuesta
          .json()
          .catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(
            mensajeError(contenido, respuesta.status),
          )
        }

        if (
          !contenido.indicadores ||
          !contenido.estados ||
          !contenido.resumen_financiero
        ) {
          throw new Error(
            'La API devolvió datos de indicadores incompletos.',
          )
        }

        if (activo) {
          setDatos(contenido)
        }
      } catch (error) {
        if (activo) {
          setError(
            error instanceof Error
              ? error.message
              : 'Error al consultar indicadores.',
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

  /**
   * Inicia otra consulta de indicadores mediante el contador de revisión.
   * @returns {void} Limpia el error y activa el estado de carga.
   */
  function recargar() {
    setError('')
    setCargando(true)
    setRevision((actual) => actual + 1)
  }

  const detalleRef = useRef(null)
  useDialogoAccesible(Boolean(detalle), detalleRef, () => setDetalle(null))

  const finanzas = datos?.resumen_financiero

  const tarjetaActiva = TARJETAS.find(
    (item) => item.clave === detalle,
  )

  const filas = tarjetaActiva
    ? datos?.estados?.[tarjetaActiva.clave]
    : []

  return (
    <div className="adm-pagina">
      <header className="adm-header">
        <a className="adm-logo" href="/administracion">
          <span className="adm-estrella">✦</span>{' '}
          Skilly
        </a>

        <nav aria-label="Enlaces principales">
          <a href="/administracion">Administración</a>
          <a href="/">Marketplace</a>
        </nav>
      </header>

      <AdminNavegacion activo="indicadores" />

      <main className="adm-contenedor">
        <div className="adm-intro">
          <span className="adm-eyebrow">
            BACK-OFFICE · CONSULTA
          </span>

          <h1>Indicadores de SKILLY</h1>

          <p>
            Resumen del sistema. Presiona una tarjeta
            para consultar el desglose por estado.
          </p>
        </div>

        <section
          className="adm-panel"
          aria-label="Resumen de indicadores"
        >
          <div className="adm-panel-header">
            <h2>Resumen general</h2>

            <button
              className="adm-secundario"
              type="button"
              disabled={cargando}
              onClick={recargar}
            >
              {cargando
                ? 'Consultando…'
                : '↻ Recargar datos'}
            </button>
          </div>

          {error && (
            <p className="adm-error" role="alert">
              {error}
            </p>
          )}

          {cargando && (
            <p>
              <output aria-live="polite" aria-atomic="true">Consultando información del servidor…</output>
            </p>
          )}

          {datos && (
            <div
              className="adm-resumen"
              style={{
                gridTemplateColumns:
                  'repeat(auto-fit, minmax(190px, 1fr))',
              }}
            >
              {TARJETAS.map((item) => (
                <button
                  key={item.clave}
                  type="button"
                  onClick={() => setDetalle(item.clave)}
                  style={{
                    background: '#fff',
                    border: '1px solid #dce8df',
                    borderRadius: 20,
                    padding: 24,
                    textAlign: 'left',
                    color: '#203a38',
                    cursor: 'pointer',
                    display: 'grid',
                    gap: 12,
                    minWidth: 0,
                  }}
                >
                  <span style={{ color: '#68817b' }}>
                    {item.titulo}
                  </span>

                  <strong style={{ fontSize: 34 }}>
                    {datos.indicadores[item.clave] ?? 0}
                  </strong>

                  <small style={{ color: '#306455' }}>
                    {item.descripcion} →
                  </small>
                </button>
              ))}
            </div>
          )}
        </section>

        {finanzas && (
          <section
            className="adm-panel"
            aria-label="Resumen financiero"
          >
            <h2>Resumen financiero</h2>

            <div className="adm-datos">
              {[
                [
                  'Pagos retenidos',
                  finanzas.monto_retenido_clp,
                ],
                [
                  'Pagos liberados',
                  finanzas.monto_liberado_clp,
                ],
                [
                  'Comisión de pagos liberados',
                  finanzas.comision_pagos_liberados_clp,
                ],
                [
                  'Neto de pagos liberados',
                  finanzas.neto_pagos_liberados_clp,
                ],
              ].map(([titulo, valor]) => (
                <div key={titulo}>
                  <small>{titulo}</small>
                  <strong>{monto(valor)}</strong>
                </div>
              ))}
            </div>

            <button
              className="adm-secundario"
              type="button"
              onClick={() => setDetalle('retenciones')}
              disabled={cargando || !!error}
              style={{ marginTop: 16 }}
            >
              Ver desglose de fondos retenidos →
            </button>

            <p className="adm-nota">
              Solo lectura. Estos importes corresponden
              a los estados registrados; no se liberan
              ni modifican pagos desde esta pantalla.
            </p>
          </section>
        )}
      </main>

      {detalle === 'retenciones' && createPortal(
        <div
          role="presentation"
          onMouseDown={(evento) => {
            if (evento.target === evento.currentTarget) setDetalle(null)
          }}
          style={{ position: 'fixed', inset: 0, zIndex: 2000,
            background: 'rgba(11,30,25,.75)', display: 'grid',
            placeItems: 'center', padding: 18 }}
        >
          <section
            ref={detalleRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="sk-retenciones-titulo"
            style={{ background: '#fff', color: '#203a38',
              borderRadius: 22, width: 'min(750px, 100%)',
              maxHeight: '86vh', overflowY: 'auto', padding: 26 }}
          >
            <div className="adm-panel-header">
              <h2 id="sk-retenciones-titulo">Detalle de fondos retenidos</h2>
              <button className="adm-secundario" type="button"
                onClick={() => setDetalle(null)} aria-label="Cerrar desglose">
                ✕ Cerrar
              </button>
            </div>
            <p className="adm-nota">
              Solo pagos con estado RETENIDO. El importe total es dinero
              custodiado por SKILLY; el neto del profesional se muestra
              por separado y no representa fondos ya liberados.
            </p>
            <div className="adm-datos" style={{ marginBottom: 16 }}>
              <div>
                <small>Total retenido</small>
                <strong>{monto(finanzas?.monto_retenido_clp)}</strong>
              </div>
              <div>
                <small>Operaciones retenidas</small>
                <strong>{datos?.detalle_retenciones?.length ?? 0}</strong>
              </div>
            </div>
            {Array.isArray(datos?.detalle_retenciones) &&
              datos.detalle_retenciones.length > 0 ? (
              <div className="adm-lista">
                {datos.detalle_retenciones.map((pago) => (
                  <article className="adm-item" key={pago.id_pago}>
                    <div className="adm-item-cuerpo"
                      style={{ display: 'grid', gap: 8 }}>
                      <strong>Pago #{pago.id_pago} · Prestación #{pago.id_prestacion}</strong>
                      <span>Solicitud #{pago.id_solicitud}</span>
                      <span>Profesional #{pago.id_profesional}: {pago.profesional}</span>
                      <span><b>Retenido:</b> {monto(pago.monto_total_clp)}</span>
                      <span><b>Comisión aplicada:</b> {monto(pago.monto_comision_clp)}</span>
                      <span><b>Neto del profesional:</b> {monto(pago.monto_neto_profesional_clp)}</span>
                    </div>
                    <span className="adm-estado">{pago.estado_pago}</span>
                  </article>
                ))}
              </div>
            ) : (
              <p className="adm-vacio">No hay pagos retenidos.</p>
            )}
          </section>
        </div>,
        document.body,
      )}

      {tarjetaActiva && createPortal(
        <div
          role="presentation"
          onMouseDown={(evento) => {
            if (evento.target === evento.currentTarget) {
              setDetalle(null)
            }
          }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 2000,
            background: 'rgba(11,30,25,.75)',
            display: 'grid',
            placeItems: 'center',
            padding: 18,
          }}
        >
          <section
            ref={detalleRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="sk-indicadores-modal-titulo"
            style={{
              background: '#fff',
              color: '#203a38',
              borderRadius: 22,
              width: 'min(620px, 100%)',
              maxHeight: '86vh',
              overflowY: 'auto',
              padding: 26,
            }}
          >
            <div className="adm-panel-header">
              <h2 id="sk-indicadores-modal-titulo">
                {tarjetaActiva.titulo} por estado
              </h2>

              <button
                type="button"
                className="adm-secundario"
                onClick={() => setDetalle(null)}
                aria-label="Cerrar detalle"
              >
                ✕ Cerrar
              </button>
            </div>

            {Array.isArray(filas) && filas.length > 0 ? (
              <div className="adm-lista">
                {filas.map((fila, indice) => (
                  <div
                    className="adm-item"
                    key={`${fila.estado}-${indice}`}
                    style={{ cursor: 'default' }}
                  >
                    <div className="adm-item-cuerpo">
                      <strong>
                        {fila.estado || 'Sin estado'}
                      </strong>

                      {detalle === 'pagos' && (
                        <small>
                          Total: {monto(fila.monto_total_clp)}
                          {' · '}
                          Comisión: {monto(
                            fila.comision_calculada_clp,
                          )}
                          {' · '}
                          Neto: {monto(
                            fila.neto_profesional_calculado_clp,
                          )}
                        </small>
                      )}
                    </div>

                    <span className="adm-estado">
                      {fila.cantidad ?? 0}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="adm-vacio">
                No hay registros en esta categoría.
              </p>
            )}
          </section>
        </div>,
        document.body,
      )}
    </div>
  )
}
