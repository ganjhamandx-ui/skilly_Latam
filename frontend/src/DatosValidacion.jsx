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

// Convierte el identificador técnico del campo en una etiqueta legible.
function tituloCampo(clave) {
  return nombres[clave] ?? clave
    .replaceAll('_', ' ')
    .replace(/^./, (letra) => letra.toUpperCase())
}

// Identifica campos técnicos o sensibles que la ficha no debe mostrar.
function ocultarCampo(clave) {
  const nombre = clave.toLowerCase()
  return [
    'password', 'contrasena', 'secret', 'token',
    'hash', 'csrf', 'credential', 'authorization',
  ].some((palabra) => nombre.includes(palabra))
}

// Convierte el valor recibido en texto de ficha y maneja valores faltantes.
function presentar(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return 'No informado'
  }

  if (typeof valor === 'boolean') {
    return valor ? 'S\u00ed' : 'No'
  }

  return String(valor)
}

// Muestra un valor de validación con su etiqueta legible y el tratamiento correspondiente.
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

// Aplica la selección de campos de la ficha antes de representarlos en pantalla.
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

// Presenta los antecedentes de validación y omite claves que no corresponden a la ficha.
export default function DatosValidacion({ titulo, datos }) {
  return (
    <div className="dv-contenedor">
      <h3>{titulo}</h3>
      <Campos datos={datos} />
    </div>
  )
}
