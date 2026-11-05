import test from 'node:test'
import assert from 'node:assert/strict'
import { extraerSeccionesCondiciones, agruparSeccionesCondiciones } from '../src/condicionesPrestacionE3.mjs'

const reciente = [
  '**Servicio:** Desarrollo de páginas web para pequeñas empresas.',
  '**Organización solicitante:** Nova Digital Demo SpA.',
  '**Alcance:** Sitio web con hasta cinco secciones y formulario de contacto.',
  '**Precio aprobado:** $250.000 CLP.',
  '**Coordinación:** Reunión inicial y horario reservado.',
  '**Entrega:** Código fuente e instrucciones básicas.',
  '**Exclusiones:** No incluye dominio ni hosting.',
  '**Pagos:** Webpay Plus en entorno de pruebas.',
  '**Incidencias:** Reprogramación mediante SKILLY.',
].join('\n\n')

test('los nueve títulos del texto publicado se interpretan y no aparece Detalle adicional', () => {
  const partes = extraerSeccionesCondiciones(reciente)
  assert.equal(partes.length, 9)
  assert.deepEqual(partes.map(x => x.titulo), ['Servicio','Organización','Alcance','Precio aprobado','Coordinación','Entrega','Exclusiones','Pagos','Incidencias'])
  assert.equal(partes.some(x => x.contenido.includes('**')), false)
})

test('los datos completos quedan presentes sin repetición ni pérdida de campos', () => {
  const grupos = agruparSeccionesCondiciones(reciente)
  const todos = grupos.flatMap(x => x.items)
  assert.equal(todos.length, 9)
  assert.ok(todos.some(x => x.contenido.includes('$250.000')))
  assert.ok(todos.some(x => x.contenido.includes('Webpay Plus')))
  assert.equal(grupos[0].titulo, 'Datos principales')
})

test('las condiciones anteriores sin Markdown siguen siendo compatibles', () => {
  const anterior = 'Servicio: Asesoría de gestión\nOrganización: Empresa Uno\nPrecio aprobado y publicado: $15.000\nNo incluye asesoría tributaria'
  assert.deepEqual(extraerSeccionesCondiciones(anterior).map(s => s.titulo), ['Servicio','Organización','Precio aprobado','Exclusiones'])
})

test('las líneas adicionales y los párrafos se preservan dentro del apartado', () => {
  const texto = '**Alcance:** Primero.\nSegundo párrafo.\n\nTercer párrafo.\n**Entrega:** Producto final.'
  const s = extraerSeccionesCondiciones(texto)
  assert.equal(s.length, 2)
  assert.ok(s[0].contenido.includes('Segundo párrafo.'))
  assert.ok(s[0].contenido.includes('Tercer párrafo.'))
})

test('títulos no previstos se muestran sin sustituirlos por tarjetas genéricas', () => {
  const s = extraerSeccionesCondiciones('**Garantía:** Treinta días.\n**Confidencialidad:** Se protegen los antecedentes.')
  assert.deepEqual(s.map(x => x.titulo), ['Garantía','Confidencialidad'])
  assert.equal(agruparSeccionesCondiciones('Garantía: Treinta días.').at(-1).titulo, 'Otros acuerdos')
})

test('el texto vacío o inexistente no crea acuerdos falsos', () => {
  assert.deepEqual(extraerSeccionesCondiciones('  '), [])
  assert.deepEqual(extraerSeccionesCondiciones(null), [])
})

test('los textos HTML no se ejecutan ni se interpretan como marcado', () => {
  const s = extraerSeccionesCondiciones('**Alcance:** <script>alert(1)</script>')
  assert.equal(s[0].contenido, '<script>alert(1)</script>')
})
