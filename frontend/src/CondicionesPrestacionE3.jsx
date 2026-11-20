import { agruparSeccionesCondiciones } from './condicionesPrestacionE3.mjs'
import './CondicionesPrestacionE3.css'

/**
 * Representa una pareja de término y contenido dentro de la lista de condiciones.
 * @param {Object} props Datos de la sección analizada.
 * @param {string} props.titulo Etiqueta del dato.
 * @param {string} props.contenido Valor textual de la condición.
 * @returns {import('react').ReactElement} Elementos dt/dd con su contenedor.
 */
function Seccion({ titulo, contenido }) {
  return (
    <div className="cp-e3-item">
      <dt>{titulo}</dt>
      <dd>{contenido}</dd>
    </div>
  )
}

/**
 * Agrupa condiciones de solo lectura para administración y seguimiento empresarial.
 * @param {Object} props Condiciones comunicadas por el servidor.
 * @param {string|null|undefined} props.texto Texto interpretado por agruparSeccionesCondiciones.
 * @returns {import('react').ReactElement|null} Resumen y secciones, o null si no hay contenido.
 */
export default function CondicionesPrestacionE3({ texto }) {
  const grupos = agruparSeccionesCondiciones(texto)
  if (!grupos.length) return null

  const resumen = grupos.find((grupo) => grupo.id === 'resumen')
  const otros = grupos.filter((grupo) => grupo.id !== 'resumen')

  return (
    <section className="cp-e3" aria-label="Condiciones de contratación publicadas">
      {resumen && (
        <div className="cp-e3-resumen">
          <h4>Resumen de las condiciones</h4>
          <dl className="cp-e3-datos">
            {resumen.items.map((item, indice) => (
              <Seccion key={`r-${indice}`} titulo={item.titulo} contenido={item.contenido} />
            ))}
          </dl>
        </div>
      )}
      <div className="cp-e3-acuerdos">
        {otros.map((grupo) => (
          <details className="cp-e3-acordeon" key={grupo.id}>
            <summary>
              <span>{grupo.titulo}</span>
              <span className="cp-e3-indicador" aria-hidden="true">⌄</span>
            </summary>
            <dl className="cp-e3-lista">
              {grupo.items.map((item, indice) => (
                <Seccion key={`${grupo.id}-${indice}`} titulo={item.titulo} contenido={item.contenido} />
              ))}
            </dl>
          </details>
        ))}
      </div>
    </section>
  )
}
