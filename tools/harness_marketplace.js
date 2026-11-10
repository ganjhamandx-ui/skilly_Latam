// React/DOM reales, fetch exclusivamente simulado. No consulta Django ni BD.
window.__runMarketplaceHarness = async function runMarketplaceHarness(phase) {
  window.__marketplaceCleanup?.()
  const { React, createRoot, Before, After } = window.__marketplaceModules
  const Component = phase === 'before' ? Before : After
  const checks = [], expectedDefects = []
  const originalFetch = window.fetch
  let root, host, pending = [], posts = 0, unexpected = 0, refreshFails = false, failureCode = null
  let deferCatalog = false, pendingCatalog = []
  const stage = name => { window.__marketplaceHarnessStage = phase + '_' + name }
  stage('iniciar')
  window.__marketplaceCleanup = () => { root?.unmount(); host?.remove() }
  const pause = () => new Promise(resolve => setTimeout(resolve, 25))
  const check = (name, passed) => { checks.push({ name, passed: !!passed }); if (!passed) { failureCode = name; throw new Error('comprobacion_fallida') } }
  async function until(fn, name) {
    const end = Date.now() + 6000
    while (Date.now() < end) { if (fn()) return; await pause() }
    failureCode = name
    throw new Error('espera_agotada')
  }
  const service = { id_servicio: 101, nombre: 'Servicio ficticio de prueba', descripcion: 'Detalle sintetico del servicio.',
    alcance: 'Escenario exclusivo de interfaz.', referencia_precio: '15000 CLP', modalidad: 'REMOTA',
    categoria: { id_categoria: 1, nombre: 'Pruebas' }, tiene_disponibilidad: true,
    profesional: { nombres: 'Profesional', apellidos: 'Ficticio' },
    disponibilidad: [{ id_disponibilidad: 201, fecha: '2030-12-20', hora_inicio: '10:00', hora_fin: '11:00' }] }
  const reply = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
  window.fetch = (url, options = {}) => {
    const address = new URL(url, location.origin)
    if (address.origin !== location.origin) { unexpected++; return Promise.reject(new Error('origen_no_simulado')) }
    if (address.pathname === '/api/acceso/sesion-actual/') return Promise.resolve(reply({}, 403))
    if (address.pathname === '/api/marketplace/servicios/') return deferCatalog
      ? new Promise(resolve => pendingCatalog.push(resolve)) : Promise.resolve(reply({ servicios: [service] }))
    if (address.pathname === '/api/marketplace/servicios/101/') return Promise.resolve(refreshFails && posts > 0
      ? reply({ detail: 'Fallo ficticio del refresco posterior al registro.' }, 503) : reply(service))
    if (address.pathname === '/api/solicitudes/enviar/' && options.method === 'POST') {
      posts++
      return new Promise(resolve => pending.push(resolve))
    }
    unexpected++
    return Promise.reject(new Error('endpoint_no_simulado'))
  }
  const dialog = () => document.querySelector('.modal-detalle')
  const button = text => [...document.querySelectorAll('button')].find(element => element.textContent.trim() === text)
  const visibleReference = () => !!document.querySelector('.referencia-solicitud')?.getClientRects().length
  async function mount() {
    if (root) root.unmount()
    host?.remove()
    host = document.createElement('div'); document.body.append(host)
    root = createRoot(host); pending = []; posts = 0; refreshFails = false; deferCatalog = false; pendingCatalog = []
    root.render(React.createElement(Component))
    await until(() => !!document.querySelector('.boton-detalle'), 'catalogo_no_listo')
    const opener = document.querySelector('.boton-detalle')
    opener.focus(); opener.click()
    await until(() => !!dialog()?.querySelector('#titulo-detalle')?.textContent.includes(service.nombre), 'detalle_no_listo')
    return opener
  }
  async function fillForm() {
    button('Solicitar este servicio').click()
    await until(() => !!document.querySelector('.formulario-solicitud'), 'formulario_no_listo')
    const fields = { id_disponibilidad: '201', nombre_organizacion: 'Organizacion ficticia', rut: '00000000-0',
      nombre_contacto: 'Contacto ficticio', correo_contacto: 'ficticio@example.invalid',
      objetivo: 'Comprobar el formulario', descripcion_necesidad: 'Datos sinteticos de prueba de interfaz.' }
    for (const [name, value] of Object.entries(fields)) {
      const input = document.querySelector(`[name="${name}"]`)
      const prototype = input.tagName === 'SELECT' ? HTMLSelectElement.prototype : input.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
      Object.getOwnPropertyDescriptor(prototype, 'value').set.call(input, value)
      input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true }))
    }
    await pause()
    const form = document.querySelector('.formulario-solicitud')
    check(phase + '_formulario_valido', form.checkValidity())
    return form
  }
  function submit(form) { form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })) }
  async function resolvePost(data, status = 201) {
    const callbacks = pending.splice(0)
    for (const resolve of callbacks) resolve(reply(data, status))
    await pause(); await pause()
  }
  async function startCatalogRefresh(opener) {
    deferCatalog = true
    window.dispatchEvent(new Event('focus'))
    await until(() => pendingCatalog.length >= 2 && !opener.isConnected, 'refresco_no_desmonto_disparador')
  }
  async function resolveCatalog() {
    deferCatalog = false
    for (const resolve of pendingCatalog.splice(0)) resolve(reply({ servicios: [service] }))
    await until(() => !!document.querySelector('.boton-detalle'), 'catalogo_refrescado_no_listo')
    await pause()
  }
  const actions = {
    Escape() { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })) },
    fondo() { document.querySelector('.modal-fondo').dispatchEvent(new MouseEvent('mousedown', { bubbles: true })) },
    X() { document.querySelector('.modal-cerrar').click() },
    volver() { button('Volver al catálogo').click() },
  }
  try {
    for (const [name, close] of Object.entries(actions)) {
      stage('cierre_' + name + '_montar')
      await mount(); const form = await fillForm(); submit(form)
      await until(() => posts === 1, 'post_no_iniciado')
      stage('cierre_' + name + '_POST_pendiente')
      close(); await pause()
      const stayed = !!dialog()
      stage('cierre_' + name + '_resolver_POST_refresco_200')
      await resolvePost({ referencia_seguimiento: 'REFERENCIA-FICTICIA', estado: 'RECIBIDA' })
      if (phase === 'before') {
        check('antes_permite_cierre_' + name, !stayed)
        expectedDefects.push('cierre_' + name + '_durante_POST')
      } else {
        check('despues_bloquea_cierre_' + name, stayed)
        check('despues_conserva_referencia_' + name, visibleReference())
      }
      check(phase + '_un_post_' + name, posts === 1)
    }
    stage('POST_correcto_refresco_503')
    await mount(); let refreshForm = await fillForm(); refreshFails = true; submit(refreshForm)
    await until(() => posts === 1, 'post_refresco_503_no_iniciado')
    actions.Escape(); await pause()
    await resolvePost({ referencia_seguimiento: 'REFERENCIA-REFRESCO-FALLIDO', estado: 'RECIBIDA' })
    if (phase === 'before') {
      check('antes_perdida_referencia_con_refresco_503', !dialog() && !visibleReference())
      expectedDefects.push('cierre_durante_POST_y_refresco_503_oculta_referencia')
    } else {
      check('despues_referencia_visible_con_refresco_503', !!dialog() && visibleReference())
    }
    if (phase === 'after') {
      stage('foco_y_teclado')
      const opener = await mount(), panel = dialog(), close = panel.querySelector('.modal-cerrar')
      check('foco_inicial_dentro_del_dialogo', document.activeElement === close)
      const focusable = [...panel.querySelectorAll('a[href],button,input,select,textarea,[tabindex]')].filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length)
      focusable.at(-1).focus()
      const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
      document.dispatchEvent(tab)
      check('Tab_circular_al_inicio', tab.defaultPrevented && document.activeElement === focusable[0])
      const backTab = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true })
      document.dispatchEvent(backTab)
      check('ShiftTab_circular_al_final', backTab.defaultPrevented && document.activeElement === focusable.at(-1))
      actions.Escape(); await pause()
      check('Escape_cierra_sin_envio', !dialog())
      check('retorno_de_foco_al_disparador', document.activeElement === opener)
      check('scroll_restaurado', document.body.style.overflow !== 'hidden')

      stage('retorno_foco_refresco_pendiente')
      let refreshedOpener = await mount()
      await startCatalogRefresh(refreshedOpener)
      check('refresco_pendiente_desconecta_disparador', !refreshedOpener.isConnected)
      actions.Escape(); await pause()
      const filter = document.querySelector('input[type="search"]')
      check('Escape_con_refresco_retorna_al_filtro_estable', !dialog() && document.activeElement === filter)
      await resolveCatalog()
      check('fin_refresco_no_roba_foco_valido_del_filtro', document.activeElement === filter)

      stage('retorno_foco_disparador_reemplazado')
      refreshedOpener = await mount()
      await startCatalogRefresh(refreshedOpener)
      await resolveCatalog()
      const replacement = document.querySelector('[data-servicio-detalle="101"]')
      check('refresco_reemplaza_disparador_sin_cerrar_modal', !refreshedOpener.isConnected && !!replacement && !!dialog())
      actions.X(); await pause()
      check('X_retorna_al_disparador_equivalente', !dialog() && document.activeElement === replacement)

      stage('respuesta_2xx_sin_referencia')
      await mount(); let form = await fillForm(); submit(form)
      await until(() => posts === 1, 'post_sin_referencia_no_iniciado')
      await resolvePost({ estado: 'RECIBIDA' })
      check('mensaje_sin_referencia_con_acentos', document.querySelector('.error-solicitud')?.textContent.includes('La API respondió, pero no entregó una referencia'))

      stage('doble_envio_error_y_reintento')
      await mount(); form = await fillForm(); submit(form); submit(form)
      await until(() => posts >= 1, 'post_error_no_iniciado')
      check('doble_submit_mismo_turno_un_solo_POST', posts === 1)
      await resolvePost({ detail: 'Fallo ficticio para probar reintento.' }, 503)
      check('error_mantiene_formulario_y_datos', !!dialog() && !!document.querySelector('.error-solicitud')
        && document.querySelector('[name="nombre_organizacion"]')?.value === 'Organizacion ficticia')
      form = document.querySelector('.formulario-solicitud'); submit(form)
      await until(() => posts === 2, 'reintento_no_iniciado')
      await resolvePost({ referencia_seguimiento: 'REFERENCIA-REINTENTO', estado: 'RECIBIDA' })
      check('reintento_correcto_muestra_referencia', visibleReference())
    }
    check(phase + '_sin_endpoints_no_simulados', unexpected === 0)
    stage('terminado')
    return { completed: true, phase, stage: window.__marketplaceHarnessStage, checks, expected_defects: expectedDefects,
      real: ['React', 'DOM', 'componentes reales de App'], simulated: ['GET/POST fetch', 'fallo de refresco GET posterior', 'solicitudes y referencias sinteticas'],
      limitations: ['Acciones DOM y teclado sintetico; no navegador E2E con Django/PostgreSQL ni eventos fisicos confiables.'] }
  } catch (error) {
    return { completed: false, phase, stage: window.__marketplaceHarnessStage,
      checks, expected_defects: expectedDefects, error_code: failureCode || 'excepcion_en_harness',
      error_type: ['Error', 'TypeError', 'ReferenceError', 'SyntaxError'].includes(error?.name) ? error.name : 'Error' }
  } finally { window.fetch = originalFetch }
}
