
import { useEffect, useState } from 'react'
import './DetalleRevision.css'

const etiquetas = {
  nombre: 'Nombre del servicio',
  descripcion: 'Descripción',
  id_categoria: 'Categoría',
  modalidad: 'Modalidad',
  alcance: 'Alcance',
  referencia_precio: 'Precio referencial revisado',
  precio_final: 'Precio final',
  precio_total: 'Precio total',
  ids_competencias: 'Competencias',
  observacion: 'Observaciones de Skilly',
  contenido_revisado: 'Contenido revisado',
  estado_revision: 'Estado de la revisión',
  numero_version: 'Número de versión',
  fecha_revision: 'Fecha de revisión',
}

/**
 * Intenta decodificar texto JSON únicamente cuando comienza con una llave o un corchete.
 * @param {*} valor Contenido recibido en la revisión.
 * @returns {*} Valor decodificado o el original si no es texto JSON reconocible.
 */
function interpretar(valor) {
  if (typeof valor !== 'string') return valor

  const limpio = valor.trim()

  if (
    !limpio.startsWith('{') &&
    !limpio.startsWith('[')
  ) {
    return valor
  }

  try {
    return JSON.parse(limpio)
  } catch {
    return valor
  }
}

/**
 * Representa valores de la versión revisada sin modificar su contenido.
 * @param {*} valor Dato JSON acíclico recibido del servidor.
 * @returns {string} Texto legible; en listas de objetos prioriza su propiedad nombre.
 */
function presentar(valor) {
  if (
    valor === null ||
    valor === undefined ||
    valor === ''
  ) {
    return 'No informado'
  }

  if (typeof valor === 'boolean') {
    return valor ? 'Sí' : 'No'
  }

  if (Array.isArray(valor)) {
    if (valor.length === 0) return 'Ninguna'

    return valor.map((elemento) => {
      // Extrae valores legibles de elementos compuestos de la propuesta.
      if (
        elemento &&
        typeof elemento === 'object'
      ) {
        return elemento.nombre ??
          JSON.stringify(elemento)
      }

      return String(elemento)
    }).join(', ')
  }

  if (typeof valor === 'object') {
    return Object.entries(valor)
      .map(([clave, dato]) =>
        `${clave}: ${presentar(dato)}`
      )
      .join(' | ')
  }

  return String(valor)
}

/**
 * Resuelve la versión estructurada desde los campos compatibles del historial de revisión.
 * @param {Object|null} revision Registro con propuesta_skilly, version_propuesta o contenido_revisado.
 * @returns {Object|null} Objeto version_propuesta interno o contenido completo; null si no es un objeto.
 */
function extraerVersion(revision) {
  const contenido = interpretar(
    revision?.propuesta_skilly ??
    revision?.version_propuesta ??
    revision?.contenido_revisado
  )

  if (
    !contenido ||
    typeof contenido !== 'object' ||
    Array.isArray(contenido)
  ) {
    return null
  }

  if (
    contenido.version_propuesta &&
    typeof contenido.version_propuesta === 'object' &&
    !Array.isArray(contenido.version_propuesta)
  ) {
    return contenido.version_propuesta
  }

  return contenido
}

/**
 * Resuelve un nombre recibido directamente o lo busca en el catálogo actual.
 * @param {Object[]} lista Catálogo consultado.
 * @param {string} campoId Campo identificador de cada elemento.
 * @param {*} valor Identificador escalar u objeto con nombre o identificador.
 * @param {string} tipo Etiqueta utilizada cuando no se encuentra el nombre.
 * @param {boolean} cargando Indica si todavía se consulta el catálogo.
 * @returns {string} Nombre, estado de carga o identificador legible como alternativa.
 */
function obtenerNombreCatalogo(
  lista,
  campoId,
  valor,
  tipo,
  cargando
) {
  if (
    valor === null ||
    valor === undefined ||
    valor === ''
  ) {
    return 'No informado'
  }

  if (
    typeof valor === 'object' &&
    !Array.isArray(valor)
  ) {
    if (valor.nombre) {
      return String(valor.nombre)
    }

    valor = valor[campoId] ?? valor.id
  }

  const identificador = Number(valor)

  if (
    !Number.isSafeInteger(identificador) ||
    identificador <= 0
  ) {
    return presentar(valor)
  }

  const encontrado = lista.find(
    (item) =>
      Number(item[campoId]) === identificador
  )

  if (encontrado?.nombre) {
    return encontrado.nombre
  }

  if (cargando) {
    return 'Consultando catálogo...'
  }

  return `${tipo} #${identificador} (nombre no disponible)`
}

/**
 * Resuelve las competencias seleccionadas mediante el catálogo disponible.
 * @param {*[]|null} valores Referencias de competencias recibidas.
 * @param {Object[]} competencias Catálogo actual.
 * @param {boolean} cargando Estado de la consulta de catálogo.
 * @returns {string} Nombres separados por coma o indicación de ausencia/lista vacía.
 */
function presentarCompetencias(
  valores,
  competencias,
  cargando
) {
  if (
    valores === null ||
    valores === undefined
  ) {
    return 'No informado'
  }

  if (!Array.isArray(valores)) {
    return presentar(valores)
  }

  if (valores.length === 0) {
    return 'Ninguna'
  }

  return valores.map((valor) =>
    obtenerNombreCatalogo(
      competencias,
      'id_competencia',
      valor,
      'Competencia',
      cargando
    )
  ).join(', ')
}

/**
 * Presenta la versión revisada para lectura del profesional y resuelve nombres de catálogo.
 * @param {Object} props Revisión que se desea consultar.
 * @param {Object|null} props.revision Registro de revisión, con estructura actual o compatible.
 * @returns {import('react').ReactElement} Detalle de solo lectura; no envía decisiones administrativas.
 */
export default function DetalleRevision({ revision }) {
  const [catalogos, setCatalogos] = useState(null)
  const [errorCatalogos, setErrorCatalogos] = useState(false)

  // Consultar los catálogos reales desde la sesión
  // profesional. No modifica ningún registro.
  useEffect(() => {
    // Carga los catálogos para interpretar los identificadores de la propuesta.
    let activo = true

    /**
     * Consulta los catálogos y aplica el resultado solo mientras este efecto siga vigente.
     * @returns {Promise<void>} En caso de fallo conserva la posibilidad de mostrar identificadores.
     */
    async function cargarCatalogos() {
      try {
        const respuesta = await fetch(
          '/api/marketplace/catalogos/',
          {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              Accept: 'application/json',
            },
          }
        )

        const datos = await respuesta.json()
          .catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(
            'No fue posible consultar los catálogos.'
          )
        }

        if (
          !Array.isArray(datos.categorias) ||
          !Array.isArray(datos.competencias)
        ) {
          throw new Error(
            'El catálogo devolvió un formato inesperado.'
          )
        }

        if (activo) {
          setCatalogos({
            categorias: datos.categorias,
            competencias: datos.competencias,
          })
        }
      } catch {
        if (activo) {
          setErrorCatalogos(true)
        }
      }
    }

    if (revision) {
      void cargarCatalogos()
    }

    return () => {
      activo = false
    }
  }, [revision])

  if (
    !revision ||
    typeof revision !== 'object'
  ) {
    return (
      <p>No hay una versión disponible.</p>
    )
  }

  const propuesta = extraerVersion(revision)

  const campos = propuesta
    ? Object.entries(propuesta)
    : Object.entries(revision).filter(
        ([clave]) =>
          ![
            'contenido_revisado',
            'version_propuesta',
            'propuesta_skilly',
          ].includes(clave)
      )

  const categorias = catalogos?.categorias ?? []
  const competencias = catalogos?.competencias ?? []

  const cargandoCatalogos = (
    catalogos === null &&
    !errorCatalogos
  )

  /**
   * Resuelve categoría o competencias por catálogo y representa el resto como texto.
   * @param {string} clave Nombre de campo de la versión.
   * @param {*} valor Dato asociado.
   * @returns {string} Texto para la ficha de revisión.
   */
  function presentarCampo(clave, valor) {
    if (clave === 'id_categoria') {
      return obtenerNombreCatalogo(
        categorias,
        'id_categoria',
        valor,
        'Categoría',
        cargandoCatalogos
      )
    }

    if (clave === 'ids_competencias') {
      return presentarCompetencias(
        valor,
        competencias,
        cargandoCatalogos
      )
    }

    return presentar(valor)
  }

  return (
    <div className="dr-contenedor">
      <p className="dr-aviso">
        Revisa cuidadosamente las condiciones y el
        precio propuestos por Skilly antes de aceptar.
        La aceptación puede actualizar el contenido
        del servicio.
      </p>

      {revision.numero_version != null && (
        <p className="dr-version">
          Versión revisada #{revision.numero_version}
        </p>
      )}

      {errorCatalogos && (
        <p className="dr-aviso" role="status">
          No fue posible obtener los nombres de
          algunas categorías o competencias.
          Se conservarán sus identificadores
          como referencia.
        </p>
      )}

      {campos.length > 0 ? (
        <dl className="dr-datos">
          {campos.map(([clave, valor]) => (
            <div
              className={
                clave.includes('precio')
                  ? 'dr-dato dr-precio'
                  : 'dr-dato'
              }
              key={clave}
            >
              <dt>
                {etiquetas[clave] ??
                  clave.replaceAll('_', ' ')}
              </dt>

              <dd>
                {presentarCampo(clave, valor)}
              </dd>
            </div>
          ))}
        </dl>
      ) : (
        <p>
          No hay datos de propuesta para mostrar.
        </p>
      )}

      {revision.observacion && (
        <div className="dr-observacion">
          <strong>
            Observaciones de Skilly
          </strong>

          <p>
            {presentar(revision.observacion)}
          </p>
        </div>
      )}

      {!propuesta &&
        typeof revision.contenido_revisado ===
          'string' && (
          <div className="dr-observacion">
            <strong>Contenido revisado</strong>

            <p>
              {revision.contenido_revisado}
            </p>
          </div>
        )}
    </div>
  )
}
