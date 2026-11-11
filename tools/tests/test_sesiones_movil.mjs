// Regresiones del modulo real; sin DOM, CDP, HTTP, sesiones ni datos reales.
import test from 'node:test'
import assert from 'node:assert/strict'
import { sesionesMoviles } from '../e2e_browser_sesiones_movil.mjs'

function harness({ completed = [], statuses = {}, failWait = null } = {}) {
  const events = [], expressions = [], checks = []
  const prior = new Set(completed)
  function compile(expression) {
    assert.equal(typeof expression, 'string')
    // Solo compilar: ejecutar esto requeriria un DOM real y ocultaria el
    // defecto de comillas que esta regresion debe detectar.
    new Function('return (' + expression + ')')
    expressions.push(expression)
  }
  function actor(name, role, authenticated) {
    return {
      name, role, authenticated, route: null,
      async navigate(route) {
        this.route = route
        events.push({ kind: 'navigate', actor: name, route, authenticated: this.authenticated })
      },
      async wait(expression, diagnostic) {
        compile(expression)
        events.push({ kind: 'wait', actor: name, diagnostic, authenticated: this.authenticated })
        if (diagnostic === failWait) throw new Error('Barrera privada ausente')
      },
      async evaluate(expression) {
        compile(expression)
        const visiblePrivatePanel = this.route === '/administracion'
          ? this.authenticated && this.role === 'ADMIN_SKILLY'
          : this.authenticated && this.role === 'PROFESIONAL'
        events.push({ kind: 'evaluate', actor: name, authenticated: this.authenticated })
        return !visiblePrivatePanel
      },
      async click(label, scope) {
        events.push({ kind: 'click', actor: name, label, scope })
      },
      async action(nameCheck, callback, endpoint, method, expected, options) {
        assert.equal(endpoint, '/api/acceso/cerrar-sesion/')
        assert.equal(method, 'POST')
        assert.deepEqual(expected, [200])
        assert.deepEqual(options, { readBody: false })
        await callback()
        const status = statuses[name] ?? 200
        if (!expected.includes(status)) throw new Error('HTTP de cierre rechazado')
        this.authenticated = false
        events.push({ kind: 'logout', actor: name, nameCheck, status, options })
      },
      async ready() { events.push({ kind: 'ready', actor: name }) },
      async screenshot(label) { events.push({ kind: 'screenshot', actor: name, label }) },
    }
  }
  const professional = actor('profesional', 'PROFESIONAL', true)
  const admin = actor('administracion', 'ADMIN_SKILLY', true)
  const company = actor('organizacion', null, false)
  const h = {
    professional, admin, company, state: {},
    stage(value) { events.push({ kind: 'stage', value }) },
    completed(name) { return prior.has(name) },
    check(name, passed) {
      assert.equal(passed, true)
      if (name === 'android_sesiones_por_rol_aisladas') {
        assert.equal(professional.authenticated, false)
        assert.equal(admin.authenticated, true)
      }
      checks.push(name)
      events.push({ kind: 'check', name })
    },
    async persist() { events.push({ kind: 'persist', state: structuredClone(this.state) }) },
  }
  return { h, events, expressions, checks }
}

test('compila expresiones reales y exige HTTP 200 sin cuerpo para ambos cierres', async () => {
  const { h, events, expressions, checks } = harness()
  await sesionesMoviles(h)
  const logouts = events.filter(event => event.kind === 'logout')
  assert.deepEqual(logouts.map(event => event.actor), ['profesional', 'administracion'])
  assert.ok(logouts.every(event => event.status === 200 && event.options.readBody === false))
  assert.equal(events.filter(event => event.kind === 'click').length, 2)
  assert.ok(expressions.length >= 7)
  assert.equal(checks.length, 5)
  assert.equal(h.state.mobile_sessions_complete, true)
  assert.equal(events.at(-1).kind, 'persist')
})

test('comprueba barreras despues de cada cierre y mantiene separado al administrador', async () => {
  const { h, events } = harness()
  await sesionesMoviles(h)
  for (const [actor, diagnostic, check] of [
    ['profesional', 'portal_accesible_despues_logout', 'android_portal_privado_bloqueado_despues_logout'],
    ['administracion', 'administracion_accesible_despues_logout', 'android_admin_privado_bloqueado_despues_logout'],
  ]) {
    const logout = events.findIndex(event => event.kind === 'logout' && event.actor === actor)
    const wait = events.findIndex(event => event.kind === 'wait' && event.diagnostic === diagnostic)
    const checked = events.findIndex(event => event.kind === 'check' && event.name === check)
    assert.ok(logout >= 0 && wait > logout && checked > wait)
    assert.equal(events[wait].authenticated, false)
    assert.ok(events.slice(logout + 1, wait).some(event => event.kind === 'navigate' && event.actor === actor))
  }
  const isolated = events.findIndex(event => event.kind === 'check' && event.name === 'android_sesiones_por_rol_aisladas')
  const adminLogout = events.findIndex(event => event.kind === 'logout' && event.actor === 'administracion')
  assert.ok(isolated > 0 && isolated < adminLogout)
})

test('reutiliza barreras heredadas pero sigue verificando el cierre de las sesiones nuevas', async () => {
  const { h, events, checks } = harness({ completed: [
    'android_anonimo_portal_solicita_acceso', 'android_profesional_no_ve_solicitudes_admin',
  ] })
  await sesionesMoviles(h)
  assert.ok(!events.some(event => event.actor === 'organizacion'))
  assert.ok(!events.some(event => event.actor === 'profesional' && event.route === '/administracion'))
  assert.equal(events.filter(event => event.kind === 'logout').length, 2)
  assert.ok(checks.includes('android_portal_privado_bloqueado_despues_logout'))
  assert.ok(checks.includes('android_admin_privado_bloqueado_despues_logout'))
})

test('un cierre HTTP fallido impide declarar y persistir la cobertura completa', async () => {
  const { h, events } = harness({ statuses: { profesional: 503 } })
  await assert.rejects(sesionesMoviles(h), /HTTP de cierre rechazado/)
  assert.notEqual(h.state.mobile_sessions_complete, true)
  assert.ok(!events.some(event => event.kind === 'persist'))
  assert.equal(h.admin.authenticated, true)
})

test('una barrera ausente tras cerrar no se acepta aunque HTTP haya sido correcto', async () => {
  const { h, events } = harness({ failWait: 'portal_accesible_despues_logout' })
  await assert.rejects(sesionesMoviles(h), /Barrera privada ausente/)
  assert.equal(events.filter(event => event.kind === 'logout').length, 1)
  assert.notEqual(h.state.mobile_sessions_complete, true)
  assert.equal(h.admin.authenticated, true)
  assert.ok(!events.some(event => event.kind === 'persist'))
})
