import test from 'node:test'
import assert from 'node:assert/strict'

import { accionCargaDocumento } from '../src/documentosCargaPolitica.mjs'

test('solo el rechazado indicado ofrece una corrección de versión', () => {
  const politica = { nuevos_permitidos: false, ids_rechazados: [12] }
  assert.deepEqual(
    accionCargaDocumento({ id_documento: 12, estado_revision: 'RECHAZADA' }, politica, 0),
    { modo: 'CORREGIR_RECHAZADO', etiqueta: 'Corregir documento rechazado' },
  )
  assert.equal(
    accionCargaDocumento({ id_documento: 13, estado_revision: 'RECHAZADA' }, politica, 0),
    null,
  )
  assert.equal(
    accionCargaDocumento({ id_documento: 12, estado_revision: 'APROBADA' }, politica, 0),
    null,
  )
})

test('un perfil habilitado adjunta un documento nuevo sin reemplazar el aprobado', () => {
  const politica = { nuevos_permitidos: true, ids_rechazados: [] }
  assert.deepEqual(
    accionCargaDocumento({ id_documento: 20, estado_revision: 'APROBADA' }, politica, 0),
    { modo: 'NUEVO_DOCUMENTO', etiqueta: 'Adjuntar nuevo documento' },
  )
  assert.equal(
    accionCargaDocumento({ id_documento: 19, estado_revision: 'APROBADA' }, politica, 1),
    null,
  )
})
