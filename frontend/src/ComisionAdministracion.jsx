
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import AdminNavegacion from './AdminNavegacion.jsx'
import './Administracion.css'

const URL = '/api/backoffice/configuracion/comision/'

function mensajeError(datos, codigo) {
  return datos?.mensaje || datos?.detail ||
    (datos?.valor_nuevo
      ? String(datos.valor_nuevo)
      : `Error HTTP ${codigo}.`)
}

function porcentaje(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return 'No configurado'
  }
  const numero = Number(valor)

  return Number.isFinite(numero)
    ? `${new Intl.NumberFormat('es-CL', {
        maximumFractionDigits: 4,
      }).format(numero)} %`
    : 'No disponible'
}

function fechaLocal(valor) {
  if (!valor) return 'Sin información'

  const fecha = new Date(valor)

  return Number.isNaN(fecha.getTime())
    ? 'Fecha no disponible'
    : fecha.toLocaleString('es-CL', {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
}

export default function ComisionAdministracion() {
  const [parametro, setParametro] = useState(null)
  const [historial, setHistorial] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [revision, setRevision] = useState(0)

  // null: cerrada
  // editar: formulario de porcentaje
  // confirmar: ventana pequeña de advertencia
  const [modo, setModo] = useState(null)

  const [valorNuevo, setValorNuevo] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [errorFormulario, setErrorFormulario] = useState('')

  useEffect(() => {
    let activo = true

    async function cargar() {
      try {
        const respuesta = await fetch(URL, {
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

        if (respuesta.status === 404) {
          if (activo) {
            setParametro(null)
            setHistorial([])
            setError('')
          }
          return
        }

        if (!respuesta.ok) {
          throw new Error(
            mensajeError(datos, respuesta.status),
          )
        }

        if (
          !datos.parametro ||
          !Array.isArray(datos.historial)
        ) {
          throw new Error(
            'La API devolvió datos incompletos.',
          )
        }

        if (activo) {
          setParametro(datos.parametro)
          setHistorial(datos.historial)
          setError('')
        }
      } catch (fallo) {
        if (activo) {
          setError(
            fallo.message ||
            'No se pudo consultar la comisión.',
          )
        }
      } finally {
        if (activo) {
          setCargando(false)
        }
      }
    }

    void cargar()

    return () => {
      activo = false
    }
  }, [revision])

  useEffect(() => {
    if (!modo) return undefined

    const anterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function tecla(evento) {
      if (evento.key === 'Escape' && !guardando) {
        setModo(
          modo === 'confirmar' ? 'editar' : null,
        )
      }
    }

    document.addEventListener('keydown', tecla)

    return () => {
      document.body.style.overflow = anterior
      document.removeEventListener('keydown', tecla)
    }
  }, [modo, guardando])

  function recargar() {
    setError('')
    setAviso('')
    setCargando(true)
    setRevision((anterior) => anterior + 1)
  }

  function abrirEdicion() {
    setValorNuevo(
      parametro ? String(parametro.valor_actual).replace('.', ',') : '',
    )

    setErrorFormulario('')
    setModo('editar')
  }

  const valorNormalizado = valorNuevo
    .trim()
    .replace(',', '.')

  const numeroNuevo = Number(valorNormalizado)

  const formatoCorrecto =
    /^\d{1,3}(?:\.\d{1,4})?$/.test(valorNormalizado)

  const valorValido =
    formatoCorrecto &&
    numeroNuevo >= 0 &&
    numeroNuevo <= 100

  const diferente = valorValido && (
    !parametro || numeroNuevo !== Number(parametro.valor_actual)
  )

  async function guardar() {
    // No guardar si no se confirmó explícitamente.
    if (
      modo !== 'confirmar' ||
      !diferente ||
      guardando
    ) {
      return
    }

    setGuardando(true)
    setErrorFormulario('')

    try {
      const csrfRespuesta = await fetch(
        '/api/acceso/csrf/',
        {
          credentials: 'same-origin',
          cache: 'no-store',
        },
      )

      const csrfDatos = await csrfRespuesta
        .json()
        .catch(() => ({}))

      if (
        !csrfRespuesta.ok ||
        !csrfDatos.csrfToken
      ) {
        throw new Error(
          'No se pudo obtener el token de seguridad.',
        )
      }

      // Se mantiene el endpoint PATCH original.
      const respuesta = await fetch(URL, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfDatos.csrfToken,
        },
        body: JSON.stringify({
          valor_nuevo: valorNormalizado,
        }),
      })

      const datos = await respuesta
        .json()
        .catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          mensajeError(datos, respuesta.status),
        )
      }

      setModo(null)

      setAviso(
        datos.mensaje ||
        'Porcentaje de comisión actualizado correctamente.',
      )

      setCargando(true)
      setRevision((anterior) => anterior + 1)
    } catch (fallo) {
      setErrorFormulario(
        fallo.message ||
        'No se pudo guardar la comisión.',
      )
    } finally {
      setGuardando(false)
    }
  }

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

      <AdminNavegacion activo="comision" />

      <main className="adm-contenedor">
        <div className="adm-intro">
          <span className="adm-eyebrow">
            BACK-OFFICE · CONFIGURACIÓN
          </span>

          <h1>Comisión de SKILLY</h1>

          <p>
            Consulta el porcentaje vigente
            y su historial de modificaciones.
          </p>
        </div>

        <section
          className="adm-panel"
          aria-label="Porcentaje de comisión"
        >
          <div className="adm-panel-header">
            <h2>Configuración vigente</h2>

            <button
              className="adm-secundario"
              type="button"
              onClick={recargar}
              disabled={cargando}
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
              Consultando el parámetro del servidor…
            </p>
          )}

          {!cargando && !error && !parametro && (
            <div>
              <p className="adm-nota">No hay un porcentaje configurado.</p>
              <button
                className="adm-secundario"
                type="button"
                onClick={abrirEdicion}
              >
                Establecer porcentaje de comisión
              </button>
            </div>
          )}

          {parametro && (
            <>
              <div className="adm-datos">
                <div>
                  <small>
                    Porcentaje de comisión actual
                  </small>

                  <strong style={{ fontSize: 30 }}>
                    {porcentaje(
                      parametro.valor_actual,
                    )}
                  </strong>
                </div>

                <div>
                  <small>Última actualización</small>

                  <strong>
                    {fechaLocal(
                      parametro.fecha_actualizacion,
                    )}
                  </strong>
                </div>

                <div>
                  <small>Tipo de parámetro</small>

                  <strong>
                    {parametro.tipo_dato ||
                      'No informado'}
                  </strong>
                </div>

                <div>
                  <small>
                    Responsable de la última modificación
                  </small>

                  <strong>
                    {parametro.responsable_actualizacion?.correo ||
                      'No informado'}
                  </strong>
                </div>
              </div>

              {parametro.descripcion && (
                <p className="adm-nota">
                  {parametro.descripcion}
                </p>
              )}

              <button
                className="adm-secundario"
                type="button"
                onClick={abrirEdicion}
              >
                Cambiar porcentaje de comisión
              </button>

              <p className="adm-nota">
                La modificación utiliza la API
                administrativa existente. No altera
                pagos anteriores ni libera fondos.
              </p>
            </>
          )}
        </section>

        <section
          className="adm-panel"
          aria-label="Historial de comisión"
        >
          <h2>Historial de modificaciones</h2>

          {!cargando && historial.length === 0 && (
            <p className="adm-vacio">
              No hay cambios registrados.
            </p>
          )}

          <div className="adm-lista">
            {historial.map((evento) => (
              <div
                className="adm-item"
                style={{ cursor: 'default' }}
                key={evento.id_historial_parametro}
              >
                <div className="adm-item-cuerpo">
                  <strong>
                    {porcentaje(
                      evento.valor_anterior,
                    )}
                    {' → '}
                    {porcentaje(
                      evento.valor_nuevo,
                    )}
                  </strong>

                  <small>
                    Fecha:{' '}
                    {fechaLocal(evento.fecha_cambio)}
                  </small>

                  <small>
                    Responsable:{' '}
                    {evento.responsable_skilly?.correo ||
                      'No informado'}
                  </small>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      {modo && createPortal(
        <div
          role="presentation"
          onMouseDown={(evento) => {
            if (
              evento.target === evento.currentTarget &&
              !guardando
            ) {
              setModo(null)
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
          {modo === 'editar' ? (
            <section
              role="dialog"
              aria-modal="true"
              aria-labelledby="sk-comision-editar"
              style={{
                width: 'min(560px, 100%)',
                maxHeight: '85vh',
                overflowY: 'auto',
                background: '#fff',
                color: '#203a38',
                borderRadius: 22,
                padding: 28,
              }}
            >
              <div className="adm-panel-header">
                <h2 id="sk-comision-editar">
                  {parametro
                    ? 'Cambiar porcentaje de comisión'
                    : 'Establecer porcentaje de comisión'}
                </h2>

                <button
                  className="adm-secundario"
                  type="button"
                  onClick={() => setModo(null)}
                >
                  ✕ Cerrar
                </button>
              </div>

              <p>
                Porcentaje vigente:{' '}
                <strong>
                  {porcentaje(
                    parametro?.valor_actual,
                  )}
                </strong>
              </p>

              <label
                style={{
                  display: 'grid',
                  gap: 10,
                  fontWeight: 700,
                }}
              >
                Nuevo porcentaje
                (0 a 100; máximo 4 decimales)

                <input
                  className="adm-busqueda"
                  inputMode="decimal"
                  autoComplete="off"
                  value={valorNuevo}
                  onChange={(evento) => {
                    setValorNuevo(
                      evento.target.value,
                    )

                    setErrorFormulario('')
                  }}
                />
              </label>

              {!valorValido &&
                valorNuevo.trim() && (
                  <p className="adm-error">
                    Introduce un porcentaje válido
                    entre 0 y 100.
                  </p>
                )}

              {parametro && valorValido && !diferente && (
                <p className="adm-nota">
                  El porcentaje es igual al vigente.
                  No hay cambios para guardar.
                </p>
              )}

              <button
                className="adm-secundario"
                type="button"
                disabled={!diferente}
                onClick={() =>
                  setModo('confirmar')
                }
              >
                Revisar cambio
              </button>
            </section>
          ) : (
            <section
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="sk-comision-confirmar"
              aria-describedby="sk-comision-confirmar-mensaje"
              style={{
                width: 'min(430px, 100%)',
                background: '#fff',
                color: '#203a38',
                borderRadius: 22,
                padding: 26,
              }}
            >
              <div className="adm-panel-header">
                <h2 id="sk-comision-confirmar">
                  ⚠ Confirmar modificación
                </h2>
              </div>

              <div
                className="adm-nota"
                id="sk-comision-confirmar-mensaje"
              >
                Vas a cambiar la comisión de{' '}
                <strong>
                  {porcentaje(
                    parametro?.valor_actual,
                  )}
                </strong>
                {' '}a{' '}
                <strong>
                  {porcentaje(numeroNuevo)}
                </strong>.

                <p>
                  {parametro
                    ? 'Se actualizará el porcentaje vigente y quedará registrado en el historial.'
                    : 'Se guardará el porcentaje inicial y quedará registrado en el historial.'}
                </p>

                <p>
                  Los pagos anteriores conservarán
                  sus montos.
                </p>
              </div>

              {errorFormulario && (
                <p
                  className="adm-error"
                  role="alert"
                >
                  {errorFormulario}
                </p>
              )}

              <div
                style={{
                  display: 'flex',
                  gap: 10,
                  flexWrap: 'wrap',
                }}
              >
                <button
                  className="adm-secundario"
                  type="button"
                  disabled={guardando}
                  onClick={() => {
                    setErrorFormulario('')
                    setModo('editar')
                  }}
                >
                  Volver y corregir
                </button>

                <button
                  className="adm-secundario"
                  type="button"
                  disabled={
                    guardando || !diferente
                  }
                  onClick={guardar}
                >
                  {guardando
                    ? 'Guardando…'
                    : 'Sí, confirmar y guardar'}
                </button>
              </div>
            </section>
          )}
        </div>,
        document.body,
      )}
    </div>
  )
}
