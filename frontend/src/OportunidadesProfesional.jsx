
// Consulta las solicitudes asociadas al profesional; no ofrece acciones de postulación.
import { useEffect, useState } from 'react'

/**
 * Convierte un dato de la oportunidad en texto legible.
 * @param {*} valor Dato individual de la respuesta.
 * @returns {string} Texto o «No informado» para null, undefined o cadena vacía.
 */
function mostrar(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return 'No informado'
  }

  return String(valor)
}

/**
 * Presenta una fecha con formato chileno en la zona del navegador.
 * @param {string|null} valor Fecha del registro.
 * @returns {string} Fecha legible, texto original si es inválido o «No informada» si falta.
 */
function fecha(valor) {
  if (!valor) return 'No informada'

  const fechaConvertida = new Date(valor)

  if (Number.isNaN(fechaConvertida.getTime())) {
    return String(valor)
  }

  return fechaConvertida.toLocaleDateString('es-CL')
}

/**
 * Consulta las oportunidades asociadas a la sesión profesional y sus estados de coordinación.
 * @returns {import('react').ReactElement} Listado de solo lectura con actualización manual.
 */
export default function OportunidadesProfesional() {
  const [oportunidades, setOportunidades] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    // Cancela la lectura privada de oportunidades al salir del componente.
    const controlador = new AbortController()

    /**
     * Consulta oportunidades y valida la lista antes de aplicarla si la petición sigue vigente.
     * @returns {Promise<void>} Conserva los resultados o muestra el error, ignorando abortos.
     */
    async function consultar() {
      setCargando(true)
      setError('')

      try {
        const respuesta = await fetch(
          '/api/coordinacion/mis-oportunidades/',
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

        const datos = await respuesta
          .json()
          .catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(
            datos.mensaje ||
            datos.detail ||
            `No se pudieron consultar las oportunidades (HTTP ${respuesta.status}).`,
          )
        }

        if (!Array.isArray(datos.oportunidades)) {
          throw new Error(
            'La API no devolvió una lista válida de oportunidades.',
          )
        }

        if (!controlador.signal.aborted) {
          setOportunidades(datos.oportunidades)
        }
      } catch (fallo) {
        if (!controlador.signal.aborted) {
          setError(
            fallo instanceof Error
              ? fallo.message
              : 'Error al consultar oportunidades.',
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
  }, [revision])

  return (
    <section className="pp-panel">
      <div className="pp-servicios-cabecera">
        <div>
          <p>
            Consulta las solicitudes empresariales
            asociadas a tu perfil profesional y sus
            estados de coordinación.
          </p>
        </div>

        <button
          type="button"
          className="pp-boton"
          disabled={cargando}
          onClick={() =>
            setRevision((actual) => actual + 1)
          }
        >
          {cargando
            ? 'Consultando...'
            : '↻ Actualizar oportunidades'}
        </button>
      </div>

      {cargando && (
        <p role="status">
          Consultando oportunidades profesionales...
        </p>
      )}

      {error && (
        <p role="alert" className="pp-error">
          {error}
        </p>
      )}

      {!cargando &&
        !error &&
        oportunidades.length === 0 && (
          <p>
            Actualmente no tienes oportunidades
            empresariales asociadas a tu perfil.
          </p>
        )}

      {!cargando &&
        !error &&
        oportunidades.length > 0 && (
          <div className="pp-listado-servicios">
            {oportunidades.map((item, indice) => (
              <article
                className="pp-servicio"
                key={
                  item.id_solicitud ??
                  indice
                }
              >
                <h3>
                  {mostrar(item.servicio?.nombre)}
                </h3>

                <p>
                  <strong>Solicitud:</strong>{' '}
                  #{mostrar(item.id_solicitud)}
                </p>

                <p>
                  <strong>Empresa:</strong>{' '}
                  {mostrar(
                    item.empresa?.nombre_organizacion,
                  )}
                </p>

                <p>
                  <strong>Objetivo:</strong>{' '}
                  {mostrar(item.necesidad?.objetivo)}
                </p>

                <p>
                  <strong>Necesidad empresarial:</strong>{' '}
                  {mostrar(
                    item.necesidad?.descripcion_necesidad,
                  )}
                </p>

                <p>
                  <strong>Modalidad:</strong>{' '}
                  {mostrar(
                    item.necesidad?.modalidad ??
                    item.servicio?.modalidad,
                  )}
                </p>

                <p>
                  <strong>Fecha preferida:</strong>{' '}
                  {fecha(item.necesidad?.fecha_preferida)}
                </p>

                <p>
                  <strong>Tipo de asociación:</strong>{' '}
                  {mostrar(item.tipo_asociacion)}
                </p>

                <p>
                  <strong>Estado de asociación:</strong>{' '}
                  {mostrar(item.estado)}
                </p>

                <p>
                  <strong>Coordinación:</strong>{' '}
                  {mostrar(
                    item.estado_coordinacion?.estado,
                  )}
                </p>

                <p>
                  <strong>Fecha de asociación:</strong>{' '}
                  {fecha(item.fecha_asociacion)}
                </p>
              </article>
            ))}
          </div>
        )}

      <p style={{ marginTop: 18 }}>
        Esta consulta no acepta solicitudes,
        no registra pagos y no modifica
        la coordinación.
      </p>
    </section>
  )
}
