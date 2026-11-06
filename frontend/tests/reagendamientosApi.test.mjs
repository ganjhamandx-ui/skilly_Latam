import test from 'node:test'
import assert from 'node:assert/strict'
import { solicitudReagendamiento } from '../src/reagendamientosApi.mjs'

function respuesta(datos, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => datos }
}

test('la lectura conserva signal, cookies y contrato sin pedir CSRF', async (t) => {
  const signal = new AbortController().signal
  const solicitudes = [{ id: 7, estado: 'PENDIENTE_ADMIN' }]
  const llamadas = []
  t.mock.method(globalThis, 'fetch', async (...args) => {
    llamadas.push(args)
    return respuesta({ solicitudes, permite_solicitar: false })
  })
  assert.deepEqual(await solicitudReagendamiento('/api/reagendamientos/administracion/', { signal }), { solicitudes, permite_solicitar: false })
  assert.equal(llamadas.length, 1)
  assert.equal(llamadas[0][1].signal, signal)
  assert.equal(llamadas[0][1].credentials, 'same-origin')
  assert.equal(llamadas[0][1].cache, 'no-store')
})

test('solo un listado vacío válido representa ausencia de solicitudes', async (t) => {
  for (const datos of [null, {}, { solicitudes: {} }, { solicitudes: [null] }, { solicitudes: [{}] }]) {
    t.mock.method(globalThis, 'fetch', async () => respuesta(datos))
    await assert.rejects(solicitudReagendamiento('/api/reagendamientos/profesional/'), /formato inesperado/)
    t.mock.restoreAll()
  }
  t.mock.method(globalThis, 'fetch', async () => respuesta({ solicitudes: [] }))
  assert.deepEqual(await solicitudReagendamiento('/api/reagendamientos/profesional/'), { solicitudes: [] })
})

test('un fallo HTTP de consulta se comunica antes de validar el listado', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => respuesta({ mensaje: 'No disponible temporalmente.' }, 503))
  await assert.rejects(solicitudReagendamiento('/api/reagendamientos/profesional/'), /No disponible temporalmente/)
})

test('no se escribe si falla la consulta CSRF aunque incluya un token', async (t) => {
  let llamadas = 0
  t.mock.method(globalThis, 'fetch', async () => { llamadas += 1; return respuesta({ csrfToken: 'token-ficticio-de-prueba' }, 403) })
  await assert.rejects(solicitudReagendamiento('/api/reagendamientos/profesional/', { method: 'POST', body: '{}' }), /token CSRF/)
  assert.equal(llamadas, 1)
})

test('un token ausente, nulo o de tipo incorrecto no autoriza el envío', async (t) => {
  for (const datos of [null, {}, { csrfToken: '' }, { csrfToken: {} }]) {
    let llamadas = 0
    t.mock.method(globalThis, 'fetch', async () => { llamadas += 1; return respuesta(datos) })
    await assert.rejects(solicitudReagendamiento('/api/reagendamientos/profesional/', { method: 'POST', body: '{}' }), /token CSRF/)
    assert.equal(llamadas, 1)
    t.mock.restoreAll()
  }
})

test('el envío conserva el cuerpo y usa el token recibido por la API', async (t) => {
  const llamadas = []
  t.mock.method(globalThis, 'fetch', async (...args) => {
    llamadas.push(args)
    return respuesta(llamadas.length === 1 ? { csrfToken: 'token-ficticio-de-prueba' } : { mensaje: 'Solicitud registrada.' })
  })
  const body = JSON.stringify({ id: 7, accion: 'ACEPTAR' })
  assert.deepEqual(await solicitudReagendamiento('/api/reagendamientos/profesional/', { method: 'POST', body }), { mensaje: 'Solicitud registrada.' })
  assert.equal(llamadas[1][1].body, body)
  assert.equal(llamadas[1][1].headers['X-CSRFToken'], 'token-ficticio-de-prueba')
  assert.equal(llamadas[1][1].headers['Content-Type'], 'application/json')
})

test('un error de acción conserva el detalle de negocio y admite un reintento', async (t) => {
  let solicitudes = 0
  t.mock.method(globalThis, 'fetch', async (url) => {
    if (url === '/api/acceso/csrf/') return respuesta({ csrfToken: 'token-ficticio-de-prueba' })
    solicitudes += 1
    return solicitudes === 1 ? respuesta({ detail: 'El bloque ya no está disponible.' }, 409) : respuesta({ mensaje: 'Solicitud registrada.' })
  })
  const opciones = { method: 'POST', body: '{}' }
  await assert.rejects(solicitudReagendamiento('/api/reagendamientos/administracion/', opciones), /bloque ya no está disponible/)
  assert.deepEqual(await solicitudReagendamiento('/api/reagendamientos/administracion/', opciones), { mensaje: 'Solicitud registrada.' })
})

test('un error no JSON ofrece un mensaje HTTP y conserva los abortos', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => ({ ok: false, status: 502, json: async () => { throw new SyntaxError('respuesta no JSON') } }))
  await assert.rejects(solicitudReagendamiento('/api/reagendamientos/profesional/'), /Error HTTP 502/)
  const fallo = new DOMException('Consulta cancelada', 'AbortError')
  t.mock.method(globalThis, 'fetch', async () => { throw fallo })
  await assert.rejects(solicitudReagendamiento('/api/reagendamientos/profesional/'), (error) => error === fallo)
})
