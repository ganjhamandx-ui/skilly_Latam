import test from 'node:test'
import assert from 'node:assert/strict'
import { obtenerCargadorPantalla, resolverRutaPantalla } from '../src/rutasPantalla.mjs'

test('las rutas conservan su destino al terminar en una o varias barras', () => {
  for (const ruta of ['/acceso-profesional', '/portal-profesional', '/seguimiento', '/administracion/reclamos']) {
    assert.equal(resolverRutaPantalla(`${ruta}///`), ruta)
    assert.equal(obtenerCargadorPantalla(`${ruta}/`), obtenerCargadorPantalla(ruta))
  }
})

test('el alias anterior de entregables sigue cargando administración', () => {
  assert.equal(
    obtenerCargadorPantalla('/administracion/entregables'),
    obtenerCargadorPantalla('/administracion'),
  )
})

test('la raíz y las rutas desconocidas conservan la pantalla pública inicial', () => {
  assert.equal(resolverRutaPantalla('///'), '/')
  assert.equal(resolverRutaPantalla('/ruta-no-definida'), '/')
  assert.equal(obtenerCargadorPantalla('/ruta-no-definida'), obtenerCargadorPantalla('/'))
})
