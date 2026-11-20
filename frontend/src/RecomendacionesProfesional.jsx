import { useCallback, useEffect, useState } from 'react'
import './RecomendacionesProfesional.css'

const etiquetas = {
  id_recomendacion: 'Identificador',
  titulo: 'T\u00edtulo',
  nombre: 'Nombre',
  descripcion: 'Descripci\u00f3n',
  recomendacion: 'Recomendaci\u00f3n',
  contenido: 'Contenido',
  detalle: 'Detalle',
  estado: 'Estado',
  prioridad: 'Prioridad',
  categoria: 'Categor\u00eda',
  fecha_registro: 'Fecha de registro',
  fecha_creacion: 'Fecha de creaci\u00f3n',
  fecha_actualizacion: 'Fecha de actualizaci\u00f3n',
  observaciones: 'Observaciones',
  motivo: 'Motivo',
}

/**
 * Resuelve una etiqueta conocida o adapta el nombre técnico del campo.
 * @param {string} clave Nombre recibido de la API.
 * @returns {string} Etiqueta para la recomendación.
 */
function nombreCampo(clave) {
  return etiquetas[clave] ??
    clave.replaceAll('_', ' ')
      .replace(/^./, (letra) => letra.toUpperCase())
}

/**
 * Identifica claves sensibles que se omiten en la presentación.
 * @param {string} clave Nombre del campo.
 * @returns {boolean} Coincidencia textual; no concede ni verifica permisos del servidor.
 */
function esRestringido(clave) {
  return /password|contrasena|token|secret|hash|csrf|credential/i
    .test(clave)
}

/**
 * Convierte un valor individual a texto con etiquetas para booleanos y datos ausentes.
 * @param {*} valor Dato recibido.
 * @returns {string} Texto mostrado en la ficha.
 */
function convertirTexto(valor) {
  if (valor == null || valor === '') return 'No informado'
  if (typeof valor === 'boolean') return valor ? 'S\u00ed' : 'No'
  return String(valor)
}

/**
 * Presenta los datos de una recomendación autorizada y filtra ciertas claves de los objetos mostrados.
 * @param {Object} props Contenido de la ficha.
 * @param {*} props.datos Valor JSON; los objetos dentro de listas se representan mediante JSON.stringify.
 * @returns {import('react').ReactElement} Detalle textual sin aplicar un filtrado recursivo universal.
 */
function MostrarDatos({ datos }) {
  if (!datos || typeof datos !== 'object') {
    return <p>{convertirTexto(datos)}</p>
  }

  const entradas = Object.entries(datos)
    .filter(([clave]) => !esRestringido(clave))

  return (
    <dl className="rp-datos">
      {entradas.map(([clave, valor]) => (
        <div className="rp-dato" key={clave}>
          <dt>{nombreCampo(clave)}</dt>
          <dd>
            {valor !== null && typeof valor === 'object'
              ? Array.isArray(valor)
                ? valor.map((elemento) =>
                    typeof elemento === 'object'
                      ? JSON.stringify(elemento)
                      : convertirTexto(elemento)
                  ).join(', ')
                : Object.entries(valor)
                    .filter(([campo]) => !esRestringido(campo))
                    .map(([campo, dato]) =>
                      `${nombreCampo(campo)}: ${convertirTexto(dato)}`
                    ).join(' | ')
              : convertirTexto(valor)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

/**
 * Admite una lista directa o los envoltorios recomendaciones, resultados y results, en ese orden.
 * @param {*} datos Respuesta del endpoint de recomendaciones.
 * @returns {Array|null} Primera lista reconocida, o null si el formato no es compatible.
 */
function normalizarLista(datos) {
  if (Array.isArray(datos)) return datos

  for (const clave of [
    'recomendaciones',
    'resultados',
    'results',
  ]) {
    if (Array.isArray(datos?.[clave])) return datos[clave]
  }

  return null
}

/**
 * Prioriza mensaje o detail textuales y usa el estado HTTP como alternativa.
 * @param {Object|null} datos JSON del servidor.
 * @param {number} estado Código HTTP recibido.
 * @returns {string} Mensaje de error de consulta.
 */
function obtenerMensaje(datos, estado) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  return `La solicitud no pudo completarse (HTTP ${estado}).`
}

/**
 * Consulta recomendaciones comunicadas al profesional y permite abrir su detalle autorizado.
 * @returns {import('react').ReactElement} Listado y detalle de solo lectura con cargas independientes.
 */
export default function RecomendacionesProfesional() {
  const [recomendaciones, setRecomendaciones] = useState([])
  const [consultadas, setConsultadas] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [detalle, setDetalle] = useState(null)
  const [idDetalle, setIdDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [errorDetalle, setErrorDetalle] = useState('')

  /**
   * Reinicia listado y selección antes de consultar y normalizar las recomendaciones disponibles.
   * @returns {Promise<void>} Aplica la lista o muestra el error sin conservar un detalle anterior.
   */
  const consultarRecomendaciones = useCallback(async () => {

    setCargando(true)
    setError('')
    setConsultadas(false)
    setRecomendaciones([])
    setDetalle(null)
    setIdDetalle(null)

    try {
      const respuesta = await fetch(
        '/api/retroalimentacion/profesional/recomendaciones/',
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerMensaje(datos, respuesta.status))
      }

      const lista = normalizarLista(datos)

      if (!lista) {
        throw new Error(
          'El servidor devolvi\u00f3 un formato de recomendaciones inesperado.',
        )
      }

      setRecomendaciones(lista)
      setConsultadas(true)
    } catch (fallo) {
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible consultar las recomendaciones.',
      )
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    // Omite la consulta inicial si la vista se desmontó antes de iniciarla.
    let activo = true
    // La consulta comienza tras el montaje del componente.
    Promise.resolve().then(() => {
      if (activo) void consultarRecomendaciones()
    })
    return () => { activo = false }
  }, [consultarRecomendaciones])

  /**
   * Consulta una recomendación por identificador; el backend verifica la pertenencia al profesional.
   * @param {number|string} id Identificador seleccionado.
   * @returns {Promise<void>} Actualiza el detalle o su error específico, sin modificar la recomendación.
   */
  async function consultarDetalle(id) {
    if (cargandoDetalle || id == null) return

    setCargandoDetalle(true)
    setErrorDetalle('')
    setDetalle(null)
    setIdDetalle(id)

    try {
      const respuesta = await fetch(
        `/api/retroalimentacion/profesional/recomendaciones/${encodeURIComponent(id)}/`,
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerMensaje(datos, respuesta.status))
      }

      setDetalle(datos.recomendacion ?? datos)
    } catch (fallo) {
      setErrorDetalle(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible consultar el detalle.',
      )
    } finally {
      setCargandoDetalle(false)
    }
  }

  return (
    <section className="pp-panel rp-panel">
      <div className="rp-encabezado">
        <div>
          <p>
            Consulta las recomendaciones de desarrollo
            asociadas a tu perfil profesional.
          </p>
        </div>

        <button
          type="button"
          className="pp-boton"
          onClick={consultarRecomendaciones}
          disabled={cargando}
        >
          {cargando
            ? 'Consultando...'
            : '↻ Recargar recomendaciones'}
        </button>
      </div>

      {cargando && !consultadas && (
        <p role="status">Cargando recomendaciones...</p>
      )}

      {error && (
        <p className="pp-error" role="alert">{error}</p>
      )}

      {consultadas && recomendaciones.length === 0 && (
        <p>No tienes recomendaciones registradas actualmente.</p>
      )}

      {recomendaciones.length > 0 && (
        <div className="rp-listado">
          {recomendaciones.map((item, indice) => {
            // Adapta recomendaciones de texto y estructuradas al mismo formato de tarjeta.
            const recomendacion = item && typeof item === 'object'
              ? item
              : { descripcion: item }

            const id = recomendacion.id_recomendacion

            return (
              <article
                className="rp-tarjeta"
                key={id ?? indice}
              >
                <h3>
                  {recomendacion.titulo ??
                    recomendacion.nombre ??
                    `Recomendaci\u00f3n ${indice + 1}`}
                </h3>

                {(recomendacion.descripcion ??
                  recomendacion.resumen) && (
                  <p>
                    {recomendacion.descripcion ??
                      recomendacion.resumen}
                  </p>
                )}

                {recomendacion.estado && (
                  <p>
                    Estado: <strong>{recomendacion.estado}</strong>
                  </p>
                )}

                {id != null && (
                  <button
                    type="button"
                    className="pp-boton pp-secundario"
                    disabled={cargandoDetalle}
                    onClick={() => consultarDetalle(id)}
                  >
                    {cargandoDetalle && idDetalle === id
                      ? 'Consultando...'
                      : 'Ver detalle'}
                  </button>
                )}
              </article>
            )
          })}
        </div>
      )}

      {idDetalle !== null && (
        <div className="rp-detalle">
          <div className="rp-detalle-cabecera">
            <h3>Detalle de recomendaci&oacute;n</h3>
            <button
              type="button"
              className="pp-boton pp-secundario"
              onClick={() => {
                setIdDetalle(null)
                setDetalle(null)
                setErrorDetalle('')
              }}
            >
              Cerrar detalle
            </button>
          </div>

          {cargandoDetalle && (
            <p role="status">Cargando detalle...</p>
          )}

          {errorDetalle && (
            <p className="pp-error" role="alert">
              {errorDetalle}
            </p>
          )}

          {detalle && <MostrarDatos datos={detalle} />}
        </div>
      )}
    </section>
  )
}
