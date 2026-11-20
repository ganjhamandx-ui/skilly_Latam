/**
 * Lector solo de presentación de condiciones ya publicadas.
 * No modifica los textos almacenados, su contenido, ni contratos del backend.
 */
const nombres = new Map([
  ['servicio', 'Servicio'],
  ['organizacion', 'Organización'],
  ['organizacion solicitante', 'Organización'],
  ['modalidad', 'Modalidad'],
  ['precio', 'Precio aprobado'],
  ['precio aprobado', 'Precio aprobado'],
  ['precio aprobado y publicado', 'Precio aprobado'],
  ['alcance', 'Alcance'],
  ['no incluye', 'Exclusiones'],
  ['exclusiones', 'Exclusiones'],
  ['primera reunion', 'Primera reunión'],
  ['coordinacion', 'Coordinación'],
  ['entrega', 'Entrega'],
  ['entregas', 'Entregas'],
  ['pagos', 'Pagos'],
  ['pago', 'Pagos'],
  ['incidencias', 'Incidencias'],
  ['condiciones de contratacion', 'Condiciones de contratación'],
  ['estas condiciones', 'Información importante'],
  ['informacion importante', 'Información importante'],
])

const grupos = [
  { id: 'resumen', titulo: 'Datos principales', clases: ['Servicio', 'Organización', 'Modalidad', 'Precio aprobado'] },
  { id: 'alcance', titulo: 'Alcance y exclusiones', clases: ['Alcance', 'Exclusiones'] },
  { id: 'coordinacion', titulo: 'Coordinación y entrega', clases: ['Primera reunión', 'Coordinación', 'Entrega', 'Entregas'] },
  { id: 'pagos', titulo: 'Pagos, incidencias y condiciones', clases: ['Pagos', 'Incidencias', 'Condiciones de contratación', 'Información importante'] },
]

/**
 * Normaliza etiquetas para buscar equivalencias sin modificar el texto persistido.
 * @param {string} texto Etiqueta a comparar.
 * @returns {string} Texto sin diacríticos, en minúsculas y con espacios internos unificados.
 */
function sinAcentos(texto) {
  return texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim().replace(/\s+/g, ' ')
}

/**
 * Retira delimitadores de negrita escritos como texto y espacios exteriores.
 * @param {string} texto Línea que se presentará en la interfaz.
 * @returns {string} Texto plano para mostrar; no interpreta ni sanea HTML.
 */
function limpiarFormato(texto) {
  // El formulario administrativo almacena texto plano, aunque admita **negritas** escritas por usuario.
  // Se muestran sus palabras sin exponer a la organización los delimitadores de Markdown.
  return texto.replace(/\*\*/g, '').trim()
}

/**
 * Reconoce una etiqueta conocida o un encabezado breve anterior a dos puntos.
 * También conserva frases iniciadas por No incluye y Estas condiciones como secciones.
 * @param {string} linea Línea de condiciones antes de limpiar formato.
 * @returns {{titulo: string, contenido: string}|null} Encabezado reconocido, o null.
 */
function leerEtiqueta(linea) {
  const valor = limpiarFormato(linea)
  const match = /^([^:\n]{1,70}):\s*(.*)$/.exec(valor)
  if (match) {
    const original = match[1].trim()
    const nombre = nombres.get(sinAcentos(original))
    if (nombre) return { titulo: nombre, contenido: match[2].trim() }
    // Encabezados de condiciones antiguas no previstos en el diccionario.
    // No adivinar una categoría genérica repetida; conservar el título original.
    if (original.length <= 40 && !/[.!?]/.test(original)) {
      return { titulo: original, contenido: match[2].trim() }
    }
  }
  if (/^No incluye\b/i.test(valor)) {
    return { titulo: 'Exclusiones', contenido: valor }
  }
  if (/^Estas condiciones\b/i.test(valor)) {
    return { titulo: 'Información importante', contenido: valor }
  }
  return null
}

/**
 * Divide condiciones en secciones ordenadas, conservando líneas bajo cada encabezado.
 * Omite secciones sin contenido y agrupa el texto inicial sin etiqueta como información complementaria.
 * @param {*} texto Texto publicado; los valores no textuales o vacíos producen una lista vacía.
 * @returns {Array<{titulo: string, contenido: string}>} Secciones de presentación, sin persistencia.
 */
export function extraerSeccionesCondiciones(texto) {
  if (typeof texto !== 'string' || !texto.trim()) return []
  const secciones = []
  const lineas = texto.replace(/\r\n?/g, '\n').split('\n')
  let actual = null

  // Conserva el bloque de texto bajo la etiqueta detectada antes de avanzar a la siguiente.
  function guardar() {
    if (actual) {
      actual.contenido = actual.contenido.trim()
      if (actual.contenido) secciones.push(actual)
    }
  }

  for (const lineaOriginal of lineas) {
    const linea = limpiarFormato(lineaOriginal)
    if (!linea) {
      if (actual?.contenido && !actual.contenido.endsWith('\n')) actual.contenido += '\n'
      continue
    }
    const etiqueta = leerEtiqueta(lineaOriginal)
    if (etiqueta && etiqueta.contenido) {
      guardar()
      actual = etiqueta
    } else if (etiqueta && !etiqueta.contenido) {
      guardar()
      actual = { ...etiqueta, contenido: '' }
    } else if (actual) {
      actual.contenido += `${actual.contenido ? '\n' : ''}${linea}`
    } else {
      actual = { titulo: 'Información complementaria', contenido: linea }
    }
  }
  guardar()
  return secciones
}

/**
 * Agrupa las secciones en categorías de presentación y conserva títulos desconocidos.
 * @param {*} texto Condiciones que se procesarán con extraerSeccionesCondiciones.
 * @returns {Array<{id: string, titulo: string, items: Array}>} Grupos no vacíos en orden
 * de la interfaz; los encabezados no clasificados se incluyen en Otros acuerdos.
 */
export function agruparSeccionesCondiciones(texto) {
  const secciones = extraerSeccionesCondiciones(texto)
  const conjuntos = grupos.map(({ id, titulo, clases }) => ({
    id, titulo, items: secciones.filter((seccion) => clases.includes(seccion.titulo)),
  }))
  const clasificados = new Set(grupos.flatMap((grupo) => grupo.clases))
  const adicionales = secciones.filter((seccion) => !clasificados.has(seccion.titulo))
  if (adicionales.length) conjuntos.push({ id: 'otros', titulo: 'Otros acuerdos', items: adicionales })
  return conjuntos.filter((grupo) => grupo.items.length > 0)
}
