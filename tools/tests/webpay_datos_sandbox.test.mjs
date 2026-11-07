// Credenciales ficticias generadas para probar el formato, sin servicios externos.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { datosSandboxDesdeDocumentacion } from '../webpay_datos_sandbox.mjs'

const pan = '0'.repeat(16), cvv = '0'.repeat(3)
const rut = '0'.repeat(8) + '-0', password = '0'.repeat(3)
const header = '### Tarjetas de Prueba\nTipo de tarjeta | Detalle | Resultado\n'
const row = `VISA | ${pan}<br />CVV ${cvv}<br />cualquier fecha | Genera transacciones **aprobadas**.\n`
const auth = `Cuando aparece un formulario de autenticación con RUT y clave, se debe\nusar el RUT **${rut}** y la clave **${password}**.\n`

test('autenticacion en dos lineas conserva los cuatro campos sin registrar valores', () => {
  const result = datosSandboxDesdeDocumentacion(header + row + auth + '### Códigos de comercio\n')
  assert.equal(result.code, null)
  assert.deepEqual(result.data, { pan, cvv, rut, password })
  assert.equal(result.metadata.authentication_multiline, true)
  assert.deepEqual(Object.values(result.metadata).every(Boolean), true)
})

test('el mismo parrafo de autenticacion en una linea sigue siendo valido', () => {
  const result = datosSandboxDesdeDocumentacion(header + row + auth.replace('\n', ' '))
  assert.equal(result.code, null)
  assert.equal(result.metadata.authentication_multiline, false)
})

test('no toma una clave del siguiente apartado si falta la del parrafo de pruebas', () => {
  const incomplete = `Cuando aparece un formulario de autenticación\nse debe usar el RUT **${rut}**.\n### Códigos de comercio\nclave ${password}\n`
  const result = datosSandboxDesdeDocumentacion(header + row + incomplete)
  assert.equal(result.code, 'OFFICIAL_DOCS_AUTH_FORMAT_INVALID')
  assert.equal(result.data, null)
  assert.equal(result.metadata.password_found, false)
})

test('no usa filas que describan rechazo ni documentos sin la seccion esperada', () => {
  assert.equal(datosSandboxDesdeDocumentacion(header + row.replace('aprobadas', 'rechazadas') + auth).code, 'OFFICIAL_DOCS_VISA_ROW_INVALID')
  assert.equal(datosSandboxDesdeDocumentacion('Documento sin tarjetas ni datos de autenticacion').code, 'OFFICIAL_DOCS_SECTION_MISSING')
})
