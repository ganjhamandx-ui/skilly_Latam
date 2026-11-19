// Resume la prestación visible para el profesional y normaliza campos opcionales de la API.
import './DetalleSeguimientoProfesional.css'

const etiquetas = {
  id_prestacion: 'N\u00famero de prestaci\u00f3n',
  id_solicitud: 'Solicitud asociada',
  nombre_servicio: 'Servicio',
  nombre: 'Nombre',
  estado: 'Estado',
  estado_prestacion: 'Estado de la prestaci\u00f3n',
  descripcion: 'Descripci\u00f3n',
  detalle: 'Detalle',
  fecha_inicio: 'Fecha de inicio',
  fecha_fin: 'Fecha de finalizaci\u00f3n',
  fecha_registro: 'Fecha de registro',
  fecha_entrega: 'Fecha de entrega',
  fecha_avance: 'Fecha del avance',
  porcentaje_avance: 'Porcentaje de avance',
  version: 'Versi\u00f3n',
  referencia_entrega: 'Referencia de entrega',
  observaciones: 'Observaciones',
  modalidad: 'Modalidad',
  alcance: 'Alcance',
}

// Presenta un nombre de campo obtenido de la API en una forma legible.
function etiqueta(nombre) {
  return etiquetas[nombre] ??
    nombre.replaceAll('_', ' ')
      .replace(/^./, (letra) => letra.toUpperCase())
}

// Filtra claves de antecedentes internos que no corresponden a la vista profesional.
function esDatoRestringido(nombre) {
  return /password|contrasena|token|secret|hash|csrf|credential/i
    .test(nombre)
}

// Prepara un valor de la ficha como texto legible y maneja campos ausentes.
function texto(valor) {
  if (valor === null || valor === undefined || valor === '') {
    return 'No informado'
  }

  if (typeof valor === 'boolean') {
    return valor ? 'S\u00ed' : 'No'
  }

  return String(valor)
}

// Presenta la colección de datos permitidos para la vista sin mostrar claves técnicas.
function Valores({ datos, profundidad = 0 }) {
  if (datos === null || datos === undefined) {
    return <p>No hay informaci&oacute;n disponible.</p>
  }

  if (Array.isArray(datos)) {
    if (datos.length === 0) {
      return <p>No hay registros asociados.</p>
    }

    return (
      <div className="dsp-listado">
        {datos.map((elemento, indice) => (
          <article className="dsp-elemento" key={indice}>
            <Valores datos={elemento} profundidad={profundidad + 1} />
          </article>
        ))}
      </div>
    )
  }

  if (typeof datos !== 'object') {
    return <p>{texto(datos)}</p>
  }

  if (profundidad > 5) {
    return <p>Informaci&oacute;n adicional disponible.</p>
  }

  const campos = Object.entries(datos).filter(
    ([nombre]) => !esDatoRestringido(nombre),
  )

  if (campos.length === 0) {
    return <p>No hay datos para mostrar.</p>
  }

  return (
    <dl className="dsp-campos">
      {campos.map(([nombre, valor]) => {
        // Presenta antecedentes estructurados o valores simples en el mismo detalle.
        const compuesto = valor !== null &&
          typeof valor === 'object'

        if (compuesto) {
          return (
            <div className="dsp-grupo" key={nombre}>
              <h4>{etiqueta(nombre)}</h4>
              <Valores
                datos={valor}
                profundidad={profundidad + 1}
              />
            </div>
          )
        }

        return (
          <div className="dsp-campo" key={nombre}>
            <dt>{etiqueta(nombre)}</dt>
            <dd>{texto(valor)}</dd>
          </div>
        )
      })}
    </dl>
  )
}

// Organiza el seguimiento de una prestación propia y oculta antecedentes restringidos.
export default function DetalleSeguimientoProfesional({ datos }) {
  if (!datos || typeof datos !== 'object') {
    return (
      <p>No se encontraron datos de seguimiento.</p>
    )
  }

  const prestacion = datos.prestacion ?? null
  const avances = datos.avances ?? null
  const entregas = datos.entregas ?? null

  const estructurado = Boolean(
    prestacion || avances || entregas,
  )

  return (
    <div className="dsp-contenedor">
      {estructurado ? (
        <>
          {prestacion && (
            <section className="dsp-seccion">
              <h3>Datos de la prestaci&oacute;n</h3>
              <Valores datos={prestacion} />
            </section>
          )}

          {avances !== null && (
            <section className="dsp-seccion">
              <h3>Avances registrados</h3>
              <Valores datos={avances} />
            </section>
          )}

          {entregas !== null && (
            <section className="dsp-seccion">
              <h3>Entregas registradas</h3>
              <Valores datos={entregas} />
            </section>
          )}

          {Object.entries(datos).some(
            ([nombre]) => ![
              'prestacion', 'avances', 'entregas',
            ].includes(nombre),
          ) && (
            <section className="dsp-seccion">
              <h3>Informaci&oacute;n complementaria</h3>
              <Valores
                datos={Object.fromEntries(
                  Object.entries(datos).filter(
                    ([nombre]) => ![
                      'prestacion', 'avances', 'entregas',
                    ].includes(nombre),
                  ),
                )}
              />
            </section>
          )}
        </>
      ) : (
        <Valores datos={datos} />
      )}
    </div>
  )
}
