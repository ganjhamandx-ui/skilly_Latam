// Ejecutar como Runtime.evaluate con awaitPromise en el origen Vite aislado.
// React y componentes reales; fetch simulado, sin PostgreSQL ni envíos externos.
(async () => {
  const origen = new URL(location.href)
  if (!['localhost', '127.0.0.1'].includes(origen.hostname) || ['8000', '5173', '9000'].includes(origen.port)) throw new Error('Origen aislado obligatorio')
  const recurso = (nombre) => performance.getEntriesByType('resource').map((r) => r.name).reverse().find((r) => new URL(r).pathname === '/node_modules/.vite/deps/' + nombre)
  const React = (await import(recurso('react.js'))).default
  const moduloDOM = await import(recurso('react-dom_client.js'))
  const createRoot = moduloDOM.createRoot || moduloDOM.default.createRoot
  const componentes = await import('/src/ReagendamientosSkilly.jsx')
  const originalFetch = window.fetch
  const original = document.getElementById('root')
  const anteriorHidden = original.hidden
  const host = document.createElement('main')
  host.id = 'ux-reagendamientos-harness'
  document.body.appendChild(host)
  original.hidden = true
  const root = createRoot(host)
  let consultas = [], escrituras = [], totalEscrituras = 0, clave = 0
  const checks = []
  const esperar = async (condicion) => {
    const inicio = Date.now()
    while (!condicion()) {
      if (Date.now() - inicio > 5000) throw new Error('Tiempo agotado en harness de reagendamientos')
      await new Promise((resolve) => setTimeout(resolve, 15))
    }
  }
  const check = (nombre, valor) => { checks.push({ nombre, aprobado: !!valor }); if (!valor) throw new Error(nombre) }
  const boton = (texto) => [...host.querySelectorAll('button')].find((b) => b.textContent.includes(texto))
  const respuesta = (datos, status = 200) => new Response(JSON.stringify(datos), { status, headers: { 'Content-Type': 'application/json' } })
  const resolverConsulta = async (datos, status = 200) => {
    await esperar(() => consultas.length > 0)
    consultas.shift().resolve(respuesta(datos, status))
    await esperar(() => host.querySelector('.rea-panel')?.getAttribute('aria-busy') === 'false')
  }
  const resolverEscritura = async (datos, status = 200) => {
    await esperar(() => escrituras.length > 0)
    escrituras.shift().resolve(respuesta(datos, status))
  }
  const montar = async (componente, props = {}) => {
    consultas = []; escrituras = []
    root.render(React.createElement(componente, { key: ++clave, ...props }))
    await esperar(() => consultas.length > 0)
  }
  window.fetch = (url, opciones = {}) => {
    if (url === '/api/acceso/csrf/') return Promise.resolve(respuesta({ csrfToken: 'token-ficticio-del-harness' }))
    if (typeof url !== 'string' || !url.startsWith('/api/reagendamientos/')) return Promise.reject(new Error('Red bloqueada por el harness'))
    return new Promise((resolve, reject) => {
      if (opciones.method === 'POST') { totalEscrituras += 1; escrituras.push({ resolve, reject }) }
      else consultas.push({ resolve, reject })
    })
  }
  const pendiente = { id: 7, estado: 'PENDIENTE_PROFESIONAL', motivo: 'Motivo sintético de reagendamiento', bloque_original: { fecha: '2030-11-07', hora_inicio: '10:00', hora_fin: '11:00' } }
  try {
    await montar(componentes.ReagendamientosProfesional)
    check('profesional_carga_no_muestra_vacio', host.textContent.includes('Consultando reagendamientos') && !host.textContent.includes('No tienes solicitudes pendientes'))
    check('profesional_actualizar_bloqueado_en_carga', boton('Actualizar avisos').disabled)
    await resolverConsulta({ mensaje: 'Fallo sintético de consulta' }, 503)
    check('profesional_error_no_muestra_vacio', !!host.querySelector('[role=alert]') && !host.textContent.includes('No tienes solicitudes pendientes'))
    boton('Actualizar avisos').click()
    await resolverConsulta({ solicitudes: [] })
    check('profesional_reintento_vacio_confirmado', host.textContent.includes('No tienes solicitudes pendientes') && !host.querySelector('[role=alert]'))
    boton('Actualizar avisos').click()
    await esperar(() => consultas.length > 0)
    check('profesional_no_vacio_durante_actualizacion', !host.textContent.includes('No tienes solicitudes pendientes'))
    await resolverConsulta({ solicitudes: [pendiente] })
    const textarea = host.querySelector('textarea')
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(textarea, 'Motivo sintético de rechazo y nueva disponibilidad')
    textarea.dispatchEvent(new Event('input', { bubbles: true }))
    await esperar(() => !boton('No disponible').disabled)
    const previas = totalEscrituras
    const rechazar = boton('No disponible')
    rechazar.click(); rechazar.click()
    await esperar(() => escrituras.length === 1)
    await new Promise((resolve) => setTimeout(resolve, 50))
    check('profesional_doble_accion_un_solo_envio', totalEscrituras === previas + 1)
    check('profesional_envio_bloquea_edicion_y_actualizacion', textarea.disabled && boton('Actualizar avisos').disabled)
    await resolverEscritura({ mensaje: 'El bloque ya no está disponible.' }, 409)
    await esperar(() => !boton('No disponible').disabled)
    check('profesional_error_conserva_motivo_y_reintento', textarea.value.includes('Motivo sintético') && host.textContent.includes('El bloque ya no está disponible'))
    boton('No disponible').click()
    await resolverEscritura({ mensaje: 'Decisión registrada.' })
    await esperar(() => consultas.length > 0)
    check('profesional_acciones_bloqueadas_hasta_recarga', boton('Aceptar bloque').disabled)
    await resolverConsulta({ solicitudes: {} })
    check('profesional_post_exitoso_recarga_fallida_diferenciados', host.textContent.includes('Decisión registrada') && host.textContent.includes('formato inesperado') && boton('Aceptar bloque').disabled)
    boton('Actualizar avisos').click()
    await resolverConsulta({ solicitudes: [] })
    check('profesional_recuperacion_final_consulta', host.textContent.includes('No tienes solicitudes pendientes') && !host.querySelector('[role=alert]'))

    await montar(componentes.ReagendamientosAdministracion)
    check('admin_carga_no_muestra_vacio', !host.textContent.includes('Sin solicitudes de reagendamiento registradas'))
    await resolverConsulta({ solicitudes: [{ ...pendiente, estado: 'PENDIENTE_ADMIN', bloques_disponibles: [] }] })
    const previasAdmin = totalEscrituras
    const solicitar = boton('Solicitar nueva disponibilidad')
    solicitar.click(); solicitar.click()
    await esperar(() => escrituras.length === 1)
    await new Promise((resolve) => setTimeout(resolve, 50))
    check('admin_doble_accion_un_solo_envio', totalEscrituras === previasAdmin + 1)
    await resolverEscritura({ mensaje: 'Solicitud administrativa registrada.' })
    await resolverConsulta({ solicitudes: [] })
    check('admin_lista_vacia_confirmada', host.textContent.includes('Sin solicitudes de reagendamiento registradas') && host.textContent.includes('Solicitud administrativa registrada'))

    await montar(componentes.ReagendamientosOrganizacion, { referencia: 'referencia-sintetica', estadoPrestacion: 'CONTRATADA' })
    check('organizacion_no_solicita_antes_de_consultar', !boton('Enviar solicitud'))
    await resolverConsulta({ solicitudes: [], permite_solicitar: true })
    const motivo = host.querySelector('textarea')
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(motivo, 'Motivo sintético para solicitar un cambio de horario')
    motivo.dispatchEvent(new Event('input', { bubbles: true }))
    await esperar(() => !boton('Enviar solicitud').disabled)
    boton('Actualizar estado').click()
    await esperar(() => consultas.length > 0)
    check('organizacion_preserva_motivo_en_actualizacion', motivo.value.includes('Motivo sintético') && boton('Enviar solicitud').disabled)
    await resolverConsulta({ mensaje: 'Fallo sintético de actualización' }, 503)
    check('organizacion_error_impide_accion_sobre_estado_obsoleto', boton('Enviar solicitud').disabled && motivo.value.includes('Motivo sintético'))
    boton('Actualizar estado').click()
    await resolverConsulta({ solicitudes: [], permite_solicitar: true })
    check('organizacion_recupera_accion_y_motivo', !boton('Enviar solicitud').disabled && motivo.value.includes('Motivo sintético'))
    const previasOrg = totalEscrituras
    const formulario = host.querySelector('form')
    formulario.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    formulario.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await esperar(() => escrituras.length === 1)
    await new Promise((resolve) => setTimeout(resolve, 50))
    check('organizacion_doble_submit_un_solo_envio', totalEscrituras === previasOrg + 1)
    await resolverEscritura({ mensaje: 'Solicitud sintética registrada.' })
    await resolverConsulta({ solicitudes: [{ ...pendiente, estado: 'PENDIENTE_ADMIN' }], permite_solicitar: false })
    check('organizacion_exito_muestra_caso_y_cierra_formulario', host.textContent.includes('Solicitud sintética registrada') && !host.querySelector('form'))
    return { aprobado: true, reales: 'React y DOM en navegador', simulado: 'fetch y respuestas de reagendamiento/CSRF', checks }
  } finally {
    root.unmount()
    host.remove()
    original.hidden = anteriorHidden
    window.fetch = originalFetch
  }
})()
