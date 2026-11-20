// Presenta antecedentes de validación profesional sin modificar el expediente recibido.
import './DatosValidacion.css'

const nombres = {
  estado: 'Estado',
  estado_validacion: 'Estado de validaci\u00f3n',
  resultado: 'Resultado',
  observacion: 'Observaci\u00f3n',
  observaciones: 'Observaciones',
  motivo: 'Motivo',
  nombre: 'Nombre',
  nombre_documento: 'Nombre del documento',
  tipo_documento: 'Tipo de documento',
  estado_documento: 'Estado del documento',
  fecha_registro: 'Fecha de registro',
  fecha_validacion: 'Fecha de validaci\u00f3n',
  fecha_revision: 'Fecha de revisi\u00f3n',
  fecha_carga: 'Fecha de carga',
  mensaje: 'Informaci\u00f3n',
  documentos: 'Documentos',
  validacion: 'Validaci\u00f3n',
}

/**
 * Obtiene la etiqueta conocida o adapta el nombre técnico para mostrarlo.
 * @param {string} clave Nombre del campo.
 * @returns {string} Etiqueta de la ficha.
 */
function tituloCampo(clave) {
  return nombres[clave] ?? clave
    .replaceAll('_', ' ')
    .replace(/^./, (letra) => letra.toUpperCase())
}

/**
 * Detecta nombres de campos que contienen expresiones sensibles, sin distinguir mayúsculas.
 * @param {string} clave Nombre de campo recibido en el objeto.
 * @returns {boolean} Si debe omitirse visualmente; no establece permisos de acceso a la API.
 */
function ocultarCampo(clave) {
  const nombre = clave.toLowerCase()
  return [
    'password', 'contrasena', 'secret', 'token',
    'hash', 'csrf', 'credential', 'authorization',
  ].some((palabra) => nombre.includes(palabra))
}

/**
 * Convierte un valor individual a texto, con etiquetas para booleanos y datos ausentes.
 * @param {*} valor Valor escalar que se desea mostrar.
 * @returns {string} Texto de presentación.
 */
function presentar(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return 'No informado'
  }

  if (typeof valor === 'boolean') {
    return valor ? 'S\u00ed' : 'No'
  }

  return String(valor)
}

/**
 * Presenta un campo escalar o recorre una colección después de filtrar su nombre.
 * @param {Object} props Campo de la respuesta.
 * @param {string} props.nombre Nombre usado para la etiqueta y el filtro de claves sensibles.
 * @param {*} props.valor Valor JSON acíclico del campo.
 * @param {number} [props.nivel=0] Profundidad; limita objetos a partir de cuatro, no las listas.
 * @returns {import('react').ReactElement|null} Campo o grupo, o null cuando se omite la clave.
 */
function Campo({ nombre, valor, nivel = 0 }) {
  if (ocultarCampo(nombre)) return null

  if (Array.isArray(valor)) {
    return (
      <div className="dv-grupo">
        <h4>{tituloCampo(nombre)}</h4>
        {valor.length === 0 ? (
          <p>No hay registros.</p>
        ) : (
          <div className="dv-elementos">
            {valor.map((elemento, indice) => (
              <div className="dv-elemento" key={indice}>
                {elemento !== null &&
                  typeof elemento === 'object' ? (
                    <Campos datos={elemento} nivel={nivel + 1} />
                  ) : (
                    <p>{presentar(elemento)}</p>
                  )}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (valor !== null && typeof valor === 'object') {
    if (nivel >= 4) {
      return (
        <div className="dv-campo">
          <dt>{tituloCampo(nombre)}</dt>
          <dd>Informaci&oacute;n adicional disponible</dd>
        </div>
      )
    }

    return (
      <div className="dv-grupo">
        <h4>{tituloCampo(nombre)}</h4>
        <Campos datos={valor} nivel={nivel + 1} />
      </div>
    )
  }

  return (
    <div className="dv-campo">
      <dt>{tituloCampo(nombre)}</dt>
      <dd>{presentar(valor)}</dd>
    </div>
  )
}

/**
 * Recorre los datos de validación y delega los campos en su representación correspondiente.
 * @param {Object} props Datos del nivel actual.
 * @param {*} props.datos Valor JSON acíclico, incluidos listas o escalares.
 * @param {number} [props.nivel=0] Profundidad transmitida a los objetos anidados.
 * @returns {import('react').ReactElement} Lista de campos o explicación del estado vacío.
 */
function Campos({ datos, nivel = 0 }) {
  if (datos === null || datos === undefined) {
    return <p>Informaci&oacute;n no disponible.</p>
  }

  if (Array.isArray(datos)) {
    if (datos.length === 0) {
      return <p>No hay registros asociados.</p>
    }

    return (
      <div className="dv-elementos">
        {datos.map((elemento, indice) => (
          <article key={indice} className="dv-elemento">
            {elemento && typeof elemento === 'object' ? (
              <Campos datos={elemento} nivel={nivel + 1} />
            ) : (
              <p>{presentar(elemento)}</p>
            )}
          </article>
        ))}
      </div>
    )
  }

  if (typeof datos !== 'object') {
    return <p>{presentar(datos)}</p>
  }

  const campos = Object.entries(datos)
    .filter(([clave]) => !ocultarCampo(clave))

  if (campos.length === 0) {
    return <p>No hay informaci&oacute;n para mostrar.</p>
  }

  return (
    <dl className="dv-campos">
      {campos.map(([clave, valor]) => (
        <Campo
          key={clave}
          nombre={clave}
          valor={valor}
          nivel={nivel}
        />
      ))}
    </dl>
  )
}

/**
 * Presenta una ficha de validación con un filtro visual de claves sensibles.
 * @param {Object} props Título y contenido ya autorizado por el servidor.
 * @param {string} props.titulo Encabezado de la ficha.
 * @param {*} props.datos Datos JSON que se recorrerán en Campos.
 * @returns {import('react').ReactElement} Ficha de solo lectura.
 */
export default function DatosValidacion({ titulo, datos }) {
  return (
    <div className="dv-contenedor">
      <h3>{titulo}</h3>
      <Campos datos={datos} />
    </div>
  )
}
