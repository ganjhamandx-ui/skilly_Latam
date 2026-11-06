import test from 'node:test'
import assert from 'node:assert/strict'
import { entregasDeRespuesta, excedeLimitesDeArchivosEntrega } from '../src/entregasProfesional.mjs'

const MiB = 1024 * 1024
const archivos = (...tamanos) => tamanos.map(size => ({ size }))

test('permite cero archivos y los limites exactos de cantidad, archivo y total', () => {
  assert.equal(excedeLimitesDeArchivosEntrega([]), false)
  assert.equal(excedeLimitesDeArchivosEntrega(archivos(10 * MiB)), false)
  assert.equal(excedeLimitesDeArchivosEntrega(archivos(10 * MiB, 10 * MiB, 5 * MiB)), false)
})

test('rechaza una unidad por encima de cada limite de adjuntos', () => {
  assert.equal(excedeLimitesDeArchivosEntrega(archivos(0, 0, 0, 0)), true)
  assert.equal(excedeLimitesDeArchivosEntrega(archivos(10 * MiB + 1)), true)
  assert.equal(excedeLimitesDeArchivosEntrega(archivos(10 * MiB, 10 * MiB, 5 * MiB + 1)), true)
})

test('admite los tres formatos existentes de entregas sin transformar la lista', () => {
  const lista = [{ id_entrega: 37 }]
  assert.equal(entregasDeRespuesta(lista), lista)
  assert.equal(entregasDeRespuesta({ entregas: lista }), lista)
  assert.equal(entregasDeRespuesta({ resultados: lista }), lista)
})

test('mantiene prioridad de entregas y permite listas vacias', () => {
  const prioridad = [], otra = [{ id_entrega: 38 }]
  assert.equal(entregasDeRespuesta({ entregas: prioridad, resultados: otra }), prioridad)
  assert.equal(entregasDeRespuesta({ entregas: null, resultados: prioridad }), prioridad)
  assert.equal(entregasDeRespuesta({ entregas: {}, resultados: 'incorrecto' }), null)
  assert.equal(entregasDeRespuesta({}), null)
})
