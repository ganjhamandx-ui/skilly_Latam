import test from 'node:test'
import assert from 'node:assert/strict'
import { crearControlConsultas, ejecutarConsulta } from '../src/cargaAsincrona.mjs'

function pendiente() {
  let resolver, rechazar
  const promesa = new Promise((resolve, reject) => { resolver = resolve; rechazar = reject })
  return { promesa, resolver, rechazar }
}

test('una respuesta anterior no sustituye el recurso seleccionado más reciente', async () => {
  const control = crearControlConsultas()
  const anterior = pendiente(), reciente = pendiente(), resultados = []
  let signalAnterior
  const primera = ejecutarConsulta(control, signal => { signalAnterior = signal; return anterior.promesa }, d => resultados.push(d), assert.fail)
  const segunda = ejecutarConsulta(control, () => reciente.promesa, d => resultados.push(d), assert.fail)
  assert.equal(signalAnterior.aborted, true)
  reciente.resolver({ id: 2 })
  await segunda
  anterior.resolver({ id: 1 })
  await primera
  assert.deepEqual(resultados, [{ id: 2 }])
})

test('cancelar al desmontar evita actualizaciones aunque fetch termine después', async () => {
  const control = crearControlConsultas(), consulta = pendiente(), resultados = []
  const carga = ejecutarConsulta(control, () => consulta.promesa, d => resultados.push(d), assert.fail)
  control.cancelar()
  consulta.resolver('respuesta tardía')
  await carga
  assert.deepEqual(resultados, [])
})

test('los fallos de consultas obsoletas no ocultan la respuesta vigente', async () => {
  const control = crearControlConsultas(), anterior = pendiente(), errores = [], resultados = []
  const primera = ejecutarConsulta(control, () => anterior.promesa, d => resultados.push(d), e => errores.push(e))
  await ejecutarConsulta(control, async () => 'vigente', d => resultados.push(d), e => errores.push(e))
  anterior.rechazar(new Error('consulta anterior'))
  await primera
  assert.deepEqual(resultados, ['vigente'])
  assert.deepEqual(errores, [])
})

test('el error vigente se entrega y la promesa termina después del callback', async () => {
  const control = crearControlConsultas(), error = new Error('sin conexión'), errores = []
  await ejecutarConsulta(control, async () => { throw error }, assert.fail, e => errores.push(e))
  assert.deepEqual(errores, [error])
})
