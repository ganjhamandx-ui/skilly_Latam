import test from 'node:test'
import assert from 'node:assert/strict'
import { serviciosCoordinadosDeRespuesta } from '../src/serviciosCoordinadosApi.mjs'

test('admite los formatos de coleccion existentes sin transformar sus elementos', () => {
  const lista = [{ id_prestacion: 71 }]
  assert.equal(serviciosCoordinadosDeRespuesta(lista), lista)
  for (const clave of ['servicios_coordinados', 'prestaciones', 'servicios', 'resultados']) {
    assert.equal(serviciosCoordinadosDeRespuesta({ [clave]: lista }), lista)
  }
})

test('conserva la prioridad de las respuestas y acepta una coleccion vacia', () => {
  const prioridad = [], otra = [{ id_prestacion: 72 }]
  assert.equal(serviciosCoordinadosDeRespuesta({ servicios_coordinados: prioridad, prestaciones: otra }), prioridad)
  assert.equal(serviciosCoordinadosDeRespuesta({ prestaciones: prioridad, servicios: otra, resultados: otra }), prioridad)
})

test('un objeto sin coleccion valida mantiene el resultado de formato inesperado', () => {
  assert.equal(serviciosCoordinadosDeRespuesta({ servicios_coordinados: {}, prestaciones: 'no es una lista' }), null)
  assert.equal(serviciosCoordinadosDeRespuesta({}), null)
})
