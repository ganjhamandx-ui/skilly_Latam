import { useCallback, useEffect, useState } from 'react'
import './SolicitarValidacionProfesional.css'

function obtenerError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  return `No fue posible completar la solicitud (HTTP ${codigo}).`
}

export default function SolicitarValidacionProfesional() {
  const [documentos, setDocumentos] = useState([])
  const [solicitud, setSolicitud] = useState(null)
  const [consultado, setConsultado] = useState(false)
  const [consultando, setConsultando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  const consultarEstado = useCallback(async () => {

    setConsultando(true)
    setError('')

    try {
      const [respuestaDocumentos, respuestaValidacion] =
        await Promise.all([
          fetch('/api/profesionales/mis-documentos/', {
            credentials: 'same-origin',
            cache: 'no-store',
            headers: { Accept: 'application/json' },
          }),
          fetch('/api/profesionales/mi-validacion/', {
            credentials: 'same-origin',
            cache: 'no-store',
            headers: { Accept: 'application/json' },
          }),
        ])

      const datosDocumentos =
        await respuestaDocumentos.json().catch(() => ({}))

      const datosValidacion =
        await respuestaValidacion.json().catch(() => ({}))

      if (!respuestaDocumentos.ok) {
        throw new Error(
          obtenerError(datosDocumentos, respuestaDocumentos.status),
        )
      }

      if (!Array.isArray(datosDocumentos.documentos)) {
        throw new Error('Formato de documentos inesperado.')
      }

      if (!respuestaValidacion.ok &&
          respuestaValidacion.status !== 404) {
        throw new Error(
          obtenerError(datosValidacion, respuestaValidacion.status),
        )
      }

      setDocumentos(datosDocumentos.documentos)

      setSolicitud(
        respuestaValidacion.ok ? datosValidacion : null,
      )

      setConsultado(true)
    } catch (fallo) {
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo consultar la validaci\u00f3n.',
      )
    } finally {
      setConsultando(false)
    }
  }, [])

  useEffect(() => {
    let activo = true
    // La consulta comienza tras el montaje del componente.
    Promise.resolve().then(() => {
      if (activo) void consultarEstado()
    })
    return () => { activo = false }
  }, [consultarEstado])

  async function enviarSolicitud() {
    if (enviando || consultando || solicitud) return

    if (!consultado) {
      setError('Primero consulta tus antecedentes.')
      return
    }

    if (documentos.length === 0) {
      setError('Adjunta al menos un documento antes de continuar.')
      return
    }

    if (!window.confirm(
      `Enviar ${documentos.length} documento(s) a revision de Skilly?`,
    )) return

    setEnviando(true)
    setError('')
    setExito('')

    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const csrf = await respuestaCsrf.json().catch(() => ({}))

      if (!respuestaCsrf.ok || !csrf.csrfToken) {
        throw new Error('No se pudo obtener el token CSRF.')
      }

      const respuesta = await fetch(
        '/api/profesionales/mi-validacion/solicitar/',
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({}),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        if (respuesta.status === 409 && datos.solicitud) {
          setSolicitud(datos.solicitud)
        }

        throw new Error(obtenerError(datos, respuesta.status))
      }

      setSolicitud(datos.solicitud)
      setExito(
        typeof datos.mensaje === 'string'
          ? datos.mensaje
          : 'Solicitud enviada correctamente.',
      )
    } catch (fallo) {
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo enviar la solicitud.',
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="pp-panel svp-panel">
      {!solicitud && (
        <p>Cuando tengas documentos preparados, puedes enviarlos a
          Skilly para su revisión administrativa.</p>
      )}
      {solicitud && (
        <p>Consulta el estado oficial de tu solicitud registrada en Skilly.</p>
      )}

      <div className="svp-acciones">
        <button
          type="button"
          className="pp-boton pp-secundario"
          onClick={consultarEstado}
          disabled={consultando || enviando}
        >
          {consultando
            ? 'Consultando...'
            : 'Actualizar estado'}
        </button>
      </div>

      {consultando && !consultado && (
        <p role="status">Consultando documentos y validación...</p>
      )}

      {error && (
        <p role="alert" className="pp-error">{error}</p>
      )}

      {exito && (
        <p role="status" className="svp-exito">{exito}</p>
      )}

      {consultado && (
        <div className="svp-resumen">
          <div className="svp-dato">
            <strong>Documentos registrados</strong>
            <span>{documentos.length}</span>
          </div>

          <div className="svp-dato">
            <strong>Solicitud de validaci&oacute;n</strong>
            <span>{solicitud?.estado ?? 'Sin solicitud'}</span>
          </div>
        </div>
      )}

      {solicitud && (
        <div className="svp-estado">
          <h3>Solicitud presentada</h3>
          <p>
            Identificador: #{solicitud.id_validacion}
          </p>
          <p>
            Estado: <strong>{solicitud.estado}</strong>
          </p>
          <p>
            {solicitud.estado === 'APROBADA'
              ? 'Tu solicitud ya fue aprobada por Skilly.'
              : solicitud.estado === 'RECHAZADA'
                ? 'La solicitud fue rechazada. Consulta las observaciones administrativas.'
                : 'Tu solicitud está registrada. La revisión depende de Skilly y no es automática.'}
          </p>
        </div>
      )}

      {consultado && !solicitud && (
        <div className="svp-enviar">
          {documentos.length === 0 ? (
            <p>
              Todav&iacute;a necesitas adjuntar documentos en
              el apartado &laquo;Mis documentos&raquo;.
            </p>
          ) : (
            <>
              <p>
                Tienes {documentos.length} documento(s) disponible(s)
                para presentar a Skilly.
              </p>

              <button
                type="button"
                className="pp-boton"
                disabled={enviando || consultando}
                onClick={enviarSolicitud}
              >
                {enviando
                  ? 'Enviando solicitud...'
                  : 'Enviar antecedentes a revisi\u00f3n'}
              </button>
            </>
          )}
        </div>
      )}

      {!solicitud && (
        <p className="svp-nota">Enviar antecedentes no implica aprobación automática;
          el proceso requiere revisión de Skilly.</p>
      )}
    </section>
  )
}
