// Valida el proxy local estricto sin destinos alternativos ni exposición de variables privadas.
import test from 'node:test'
import assert from 'node:assert/strict'
import { randomBytes } from 'node:crypto'
import { configurarServidorLocal, validarDestinoApiLocal } from '../config/proxyApiLocal.mjs'
import configurarVite from '../vite.config.js'

test('acepta únicamente orígenes HTTP loopback con puerto explícito autorizado', () => {
  for (const target of [
    'http://127.0.0.1:48123', 'http://127.0.0.2:48123',
    'http://127.10.20.30:65535', 'http://localhost:48123', 'http://[::1]:48123',
    'HTTP://LOCALHOST:48123/', 'http://127.0.0.2:80',
  ]) {
    const normalized = validarDestinoApiLocal(target)
    assert.ok(normalized.startsWith('http://'))
    assert.ok(normalized.endsWith(':' + Number(target.match(/:([0-9]+)\/?$/)[1])))
  }
})

test('rechaza el puerto 8000 en todas las formas locales y puertos inválidos', () => {
  for (const host of ['127.0.0.1', '127.0.0.2', '127.255.255.255', 'localhost', '[::1]']) {
    assert.throws(() => validarDestinoApiLocal(`http://${host}:8000`))
  }
  for (const target of ['http://127.0.0.1', 'http://127.0.0.1:0', 'http://127.0.0.1:08000',
    'http://127.0.0.1:65536', 'http://127.0.0.1:-1', 'http://127.0.0.1:1.2']) {
    assert.throws(() => validarDestinoApiLocal(target))
  }
})

test('rechaza destinos remotos, nombres ambiguos, rutas, query, fragmentos y credenciales', () => {
  for (const target of [
    'https://127.0.0.1:48123', 'http://0.0.0.0:48123', 'http://192.168.1.2:48123',
    'http://example.invalid:48123', 'http://localhost.example.invalid:48123',
    'http://127.0.0.1.example.invalid:48123', 'http://127.0.0.1.:48123',
    'http://127.1:48123', 'http://2130706433:48123', 'http://0177.0.0.1:48123',
    'http://127.001.0.1:48123', 'http://127.0.0.256:48123', 'http://[::]:48123',
    'http://[::ffff:127.0.0.1]:48123', '//127.0.0.1:48123',
    'http://user@127.0.0.1:48123', 'http://user:password@localhost:48123',
    'http://127.0.0.1:48123/api', 'http://127.0.0.1:48123//',
    'http://127.0.0.1:48123?', 'http://127.0.0.1:48123#',
    'http://127.0.0.1:48123?target=other', 'http://127.0.0.1:48123#route',
    ' http://127.0.0.1:48123', 'http://127.0.0.1:48123\n',
    'http://local\thost:48123', 'http:\\127.0.0.1:48123',
    undefined, null, 48123, '',
  ]) {
    assert.throws(() => validarDestinoApiLocal(target))
  }
})

test('los errores no incluyen un destino con credenciales o canarios', () => {
  const canary = randomBytes(32).toString('hex')
  const target = `http://user:${canary}@example.invalid:48123`
  assert.throws(() => validarDestinoApiLocal(target), error => {
    assert.ok(!error.message.includes(canary) && !error.message.includes(target))
    assert.match(error.message, /SKILLY_API_PROXY_TARGET/)
    return true
  })
})

test('serve falla sin configuración y no usa variables VITE ni un fallback a 8000', () => {
  assert.throws(() => configurarServidorLocal('serve'))
  assert.throws(() => configurarServidorLocal('serve', { VITE_API_PROXY_TARGET: 'http://127.0.0.2:48123' }))
  const canary = randomBytes(32).toString('hex')
  const config = configurarServidorLocal('serve', {
    SKILLY_API_PROXY_TARGET: 'http://127.0.0.2:48123', PRIVATE_CANARY: canary,
  })
  assert.equal(config.host, '127.0.0.2')
  assert.equal(config.port, 57744)
  assert.equal(config.strictPort, true)
  assert.deepEqual(Object.keys(config.proxy), ['/api'])
  assert.deepEqual(config.proxy['/api'], { target: 'http://127.0.0.2:48123', changeOrigin: true })
  assert.ok(!JSON.stringify(config).includes(canary))
})

test('build no requiere ni consulta la variable del proxy y no publica configuración de servidor', () => {
  const environment = new Proxy({}, {
    // Cualquier intento de leer el entorno de desarrollo hace fallar la prueba.
    get() { throw new Error('No leer entorno de desarrollo durante build') },
  })
  assert.equal(configurarServidorLocal('build', environment), undefined)
  assert.equal(configurarServidorLocal('build', { SKILLY_API_PROXY_TARGET: 'http://example.invalid:8000' }), undefined)
})

test('la configuración Vite real usa el entorno vigente en cada invocación sin definir datos para el cliente', () => {
  const previous = process.env.SKILLY_API_PROXY_TARGET
  try {
    delete process.env.SKILLY_API_PROXY_TARGET
    assert.throws(() => configurarVite({ command: 'serve' }))
    const build = configurarVite({ command: 'build' })
    assert.equal(Object.hasOwn(build, 'server'), false)
    assert.equal(Object.hasOwn(build, 'define'), false)
    assert.equal(Object.hasOwn(build, 'envPrefix'), false)
    for (const target of ['http://127.0.0.2:48123', 'http://[::1]:48124']) {
      process.env.SKILLY_API_PROXY_TARGET = target
      const config = configurarVite({ command: 'serve' })
      assert.equal(config.server.proxy['/api'].target, target)
      assert.equal(Object.hasOwn(config, 'define'), false)
      assert.equal(Object.hasOwn(config, 'envPrefix'), false)
    }
  } finally {
    if (previous === undefined) delete process.env.SKILLY_API_PROXY_TARGET
    else process.env.SKILLY_API_PROXY_TARGET = previous
  }
})
