// Presenta el estado y horario de entrevista sin inferir decisiones no devueltas por la API.
import './ResumenEntrevista.css'

const etiquetas = {
  estado: 'Estado de la entrevista',
  estado_entrevista: 'Estado de la entrevista',
  fecha: 'Fecha',
  fecha_entrevista: 'Fecha de entrevista',
  fecha_reserva: 'Fecha de reserva',
  hora_inicio: 'Hora de inicio',
  hora_fin: 'Hora de finalizaci\u00f3n',
  modalidad: 'Modalidad',
  enlace_reunion: 'Enlace de reuni\u00f3n',
  enlace_entrevista: 'Enlace de entrevista',
  observacion: 'Observaciones',
  observaciones: 'Observaciones',
  id_entrevista: 'N\u00famero de entrevista',
  id_validacion: 'Validaci\u00f3n asociada',
  id_bloque_entrevista: 'Bloque de entrevista',
}

// Genera una etiqueta legible para los campos del resumen de entrevista.
function titulo(clave) {
  return etiquetas[clave] ??
    clave.replaceAll('_', ' ')
      .replace(/^./, (letra) => letra.toUpperCase())
}

// Prepara un valor de la ficha como texto legible y maneja campos ausentes.
function texto(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return 'No informado'
  }

  if (typeof valor === 'boolean') {
    return valor ? 'S\u00ed' : 'No'
  }

  if (Array.isArray(valor)) {
    return valor.map(texto).join(', ') || 'Sin datos'
  }

  if (typeof valor === 'object') {
    return Object.entries(valor)
      .filter(([clave]) => !/token|secret|password|hash/i.test(clave))
      .map(([clave, dato]) => `${titulo(clave)}: ${texto(dato)}`)
      .join(' | ')
  }

  return String(valor)
}

// Evita presentar identificadores y datos internos en el resumen.
function campoOculto(nombre) {
  return /token|secret|password|hash|csrf|credential/i.test(nombre)
}

// Acota la presentación de la entrevista a fecha, horario y antecedentes comunicables.
export default function ResumenEntrevista({ datos }) {
  if (!datos || typeof datos !== 'object') {
    return <p>La informaci&oacute;n de la entrevista no est&aacute; disponible.</p>
  }

  const valores = Object.entries(datos).filter(
    ([clave]) => !campoOculto(clave),
  )

  return (
    <div className="re-contenedor">
      <div className="re-encabezado">
        <h3>Detalle de la entrevista</h3>
        {(datos.estado || datos.estado_entrevista) && (
          <span className="re-estado">
            {texto(datos.estado ?? datos.estado_entrevista)}
          </span>
        )}
      </div>

      <dl className="re-campos">
        {valores.map(([clave, valor]) => (
          <div className="re-campo" key={clave}>
            <dt>{titulo(clave)}</dt>
            <dd>{texto(valor)}</dd>
          </div>
        ))}
      </dl>

      <p className="re-nota">
        Los horarios y el estado oficial de la entrevista
        son determinados por Skilly.
      </p>
    </div>
  )
}
