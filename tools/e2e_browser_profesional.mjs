// Interacciones de la UI profesional/administrativa. Identificadores privados solo en memoria.
import { randomUUID } from 'node:crypto'

export function ident(body, key) {
  if (body && typeof body === 'object') {
    if (Object.hasOwn(body, key)) return body[key]
    for (const value of Object.values(body)) { const found = ident(value, key); if (found !== undefined) return found }
  }
}
export async function login(actor, account, h) {
  await actor.navigate('/acceso-profesional')
  await actor.fill('#ap-correo', account.email); await actor.fill('#ap-contrasena', account.password)
  await actor.action('login_ui_' + actor.name, () => actor.clickSelector('.ap-formulario button[type=submit]'), '/api/acceso/iniciar-sesion/')
  await actor.wait("location.pathname!=='/acceso-profesional'", 'login_no_redirige'); await actor.ready()
  h.check('sesion_ui_' + actor.name, true)
}
export async function portal(actor, module, option, suboption) {
  await actor.navigate('/portal-profesional')
  await actor.click(module, 'nav', false)
  await actor.click(option, '.pp-opciones-secciones', false)
  if (suboption) await actor.click(suboption, '[role=dialog]', false)
  await actor.ready()
}
export async function validationDetail(h) {
  const { admin: a, state: s } = h
  await a.navigate('/administracion/validaciones')
  await a.click('Todas', 'main').catch(() => {})
  await a.wait(`!![...document.querySelectorAll('.va-item')].find(e=>e.innerText.includes('Solicitud #${s.validation_id}'))`, 'solicitud_no_visible')
  await a.evaluate(`(()=>{const e=[...document.querySelectorAll('.va-item')].find(e=>e.innerText.includes('Solicitud #${s.validation_id}'));e.dataset.e2eSelected='true'})()`)
  await a.click('Ver antecedentes', '[data-e2e-selected=true]')
  await a.wait("!!document.querySelector('.va-documento')", 'antecedentes_no_visibles'); await a.ready()
}
export async function onboarding(h) {
  const { professional: p, admin: a, state: s, fixture, check, pdf, badFile } = h
  if (s.onboarding_complete) { await login(p, s.professional, h); await login(a, fixture.admin, h); return }
  if (!s.professional_id) {
  h.stage('registro_ui')
  await p.navigate('/acceso-profesional'); await p.click('Crear cuenta profesional')
  for (const [id, value] of Object.entries({ 'rp-correo': s.professional.email, 'rp-clave': s.professional.password, 'rp-confirmar': s.professional.password, 'rp-nombres': 'Profesional UI', 'rp-apellidos': 'Prueba aislada', 'rp-titulo': 'Especialista de pruebas', 'rp-ubicacion': 'Santiago', 'rp-resumen': 'Perfil sintetico generado exclusivamente para verificar React en copia aislada.' })) await p.fill('#' + id, value)
  await p.action('registro_profesional_ui', () => p.click('Crear mi cuenta profesional'), '/api/acceso/registro-profesional/', 'POST', [201])
  await p.wait("!!document.querySelector('.rp-exito')", 'registro_sin_confirmacion_ui')
  await login(p, s.professional, h); await login(a, fixture.admin, h)
  const profile = await p.api('confirmar_id_profesional_creado_por_ui', 'GET', '/api/profesionales/mi-perfil/')
  s.professional_id = ident(profile, 'id_profesional'); check('id_profesional_recibido', Number.isInteger(s.professional_id))
  } else { await login(p, s.professional, h); await login(a, fixture.admin, h) }
  if (!h.completed('finalizar_revision_documental_ui')) {
  h.stage('documentos_ui')
  await portal(p, 'Perfil y validacion', 'Documentos y validacion', 'Adjuntar documentos')
  await p.fill('#dc-tipo', 'TITULO')
  if (!h.android) {
  await p.file('#dc-archivo', [badFile])
  await p.action('archivo_invalido_rechazado_ui_backend', () => p.click('Adjuntar documento'), '/api/profesionales/mis-documentos/subir/', 'POST', [400])
  check('error_de_documento_visible_ui', await p.evaluate("!!document.querySelector('.dc-panel [role=alert]')"))
  } else h.interventions.push({ kind: 'archivo_invalido_no_repetido_android', reason: 'No se altera el filtro accept nativo para introducir un ejecutable; rechazo backend y escritorio conservados en evidencia previa.' })
  await p.file('#dc-archivo', [pdf])
  const doc = await p.action('carga_documento_ui', () => p.click('Adjuntar documento'), '/api/profesionales/mis-documentos/subir/', 'POST', [201])
  s.document_id = ident(doc, 'id_documento')
  await p.screenshot('01_documento_cargado')
  await portal(p, 'Perfil y validacion', 'Documentos y validacion', 'Solicitar validacion')
  const validation = await p.action('enviar_antecedentes_ui', () => p.click('Enviar antecedentes a revision'), '/api/profesionales/mi-validacion/solicitar/', 'POST', [201])
  s.validation_id = ident(validation, 'id_validacion'); await h.persist()
  h.stage('revision_y_correccion_documental_ui')
  await validationDetail(h)
  await a.fill('#revision-documento-' + s.document_id, 'Documento sintetico requiere la version corregida para continuar.')
  await a.action('rechazar_documento_ui', () => a.click('Rechazar documento'), `/api/profesionales/administracion/validaciones/${s.validation_id}/resolver/`)
  await p.navigate('/portal-profesional')
  await portal(p, 'Perfil y validacion', 'Documentos y validacion', 'Adjuntar documentos')
  await p.click('Adjuntar otra version')
  await p.file('#dc-archivo', [pdf])
  const corrected = await p.action('corregir_documento_ui', () => p.click('Adjuntar documento'), '/api/profesionales/mis-documentos/subir/', 'POST', [201])
  s.corrected_document_id = ident(corrected, 'id_documento')
  check('historial_documental_conservado_ui', await p.evaluate("document.querySelectorAll('.dc-documento').length===2"))
  await validationDetail(h)
  const article = `.va-documento:has(#revision-documento-${s.corrected_document_id})`
  await a.action('aprobar_documento_corregido_ui', () => a.click('Aprobar documento', article), `/api/profesionales/administracion/validaciones/${s.validation_id}/resolver/`)
  await a.fill('#va-observacion', 'Documentos sinteticos vigentes revisados en copia aislada.')
  await a.action('finalizar_revision_documental_ui', () => a.click('Finalizar aprobacion documental'), `/api/profesionales/administracion/validaciones/${s.validation_id}/resolver/`)
  }
  h.stage('entrevista_ui')
  let interviewDay = s.interview_day
  if (!s.interview_id) {
  interviewDay = new Date(Date.now() + (3 + Number.parseInt(randomUUID().slice(0, 3), 16) % 30) * 24 * 3600000).toISOString().slice(0, 10)
  s.interview_day = interviewDay
  await a.navigate('/administracion/validaciones'); await a.click('Gestionar entrevistas', 'main', false)
  await a.ready()
  const agenda = a.responses.findLast(r => r.method === 'GET' && r.path === '/api/profesionales/administracion/entrevistas/' && Array.isArray(r.body?.bloques))?.body.bloques
  if (!agenda) throw new Error('agenda_entrevista_ui_no_cargada')
  // Seleccionar un hueco de la agenda real cargada por React. No reutilizar bloques ocupados.
  for (let offset = 0; offset < 90; offset++) {
    const candidate = new Date(new Date(interviewDay).getTime() + offset * 24 * 3600000).toISOString().slice(0, 10)
    if (!agenda.some(b => String(b.fecha).slice(0, 10) === candidate && String(b.hora_inicio) < '20:30:00' && String(b.hora_fin) > '20:00:00')) { s.interview_day = candidate; break }
  }
  interviewDay = s.interview_day
  if (agenda.some(b => String(b.fecha).slice(0, 10) === interviewDay && String(b.hora_inicio) < '20:30:00' && String(b.hora_fin) > '20:00:00')) throw new Error('sin_hueco_sintetico_entrevista')
  await a.click('+ Crear bloque'); await a.fill('#ea-fecha', interviewDay)
  await a.fill('#ea-inicio', '20:00'); await a.fill('#ea-fin', '20:30'); await a.fill('#ea-capacidad', '1')
  const block = await a.action('crear_bloque_entrevista_ui', () => a.click('Confirmar creacion'), '/api/profesionales/administracion/entrevistas/bloques/', 'POST', [201])
  s.interview_block_id = ident(block, 'id_bloque_entrevista')
  await portal(p, 'Perfil y validacion', 'Documentos y validacion', 'Reservar entrevista')
  await p.fill('#pp-bloque-entrevista', s.interview_block_id)
  const interview = await p.action('reservar_entrevista_ui', () => p.click('Confirmar reserva'), '/api/profesionales/mi-entrevista/reservar/')
  s.interview_id = ident(interview, 'id_entrevista')
  await h.persist()
  } else if (!interviewDay) {
    const reserved = await p.api('confirmar_fecha_entrevista_reservada_en_ui', 'GET', '/api/profesionales/mi-entrevista/')
    interviewDay = String(ident(reserved, 'fecha')).slice(0, 10); s.interview_day = interviewDay
    if (!/^\d{4}-\d{2}-\d{2}$/.test(interviewDay)) throw new Error('fecha_entrevista_no_recibida')
  }
  if (!h.completed('confirmar_contacto_entrevista_sintetico_ui')) {
  await a.navigate('/administracion/validaciones'); await a.click('Gestionar entrevistas', 'main', false)
  await a.ready()
  await a.wait(`!![...document.querySelectorAll('.va-item')].find(e=>e.innerText.includes('Bloque #${s.interview_block_id}'))`, 'bloque_reservado_no_cargado')
  await a.evaluate(`(()=>{const e=[...document.querySelectorAll('.va-item')].find(e=>e.innerText.includes('Bloque #${s.interview_block_id}'));if(e)e.dataset.e2eInterview='true'})()`)
  h.interventions.push({ kind: 'contacto_humano_simulado', operation: 'confirmacion_mediante_ui_sin_envio_real' })
  await a.action('confirmar_contacto_entrevista_sintetico_ui', () => a.click('Marcar como contactado', '[data-e2e-interview=true]'), `/api/profesionales/administracion/entrevistas/${s.interview_id}/contacto/`)
  }
  if (!h.completed('resultado_entrevista_prematuro_rechazado_ui')) {
  await validationDetail(h); await a.fill('#va-observacion-entrevista', 'Resultado sintetico de entrevista de prueba; no acredita una entrevista humana real.')
  await a.clickSelector('label:has(input[type=checkbox]) input[type=checkbox]')
  await a.action('resultado_entrevista_prematuro_rechazado_ui', () => a.click('Aprobar perfil profesional'), `/api/profesionales/administracion/validaciones/${s.validation_id}/resultado-entrevista/`, 'POST', [409])
  check('entrevista_prematura_error_visible', await a.evaluate("!!document.querySelector('[role=dialog] [role=alert]')"))
  }
  await h.clock(new Date(new Date(interviewDay).getTime() + 2 * 24 * 3600000).toISOString())
  // El avance de dias expira legitimamente las sesiones. Reautenticar sin alterar su TTL.
  await login(a, fixture.admin, h)
  await validationDetail(h); await a.fill('#va-observacion-entrevista', 'Resultado sintetico de entrevista de prueba; no acredita una entrevista humana real.')
  await a.clickSelector('label:has(input[type=checkbox]) input[type=checkbox]')
  h.interventions.push({ kind: 'entrevista_humana_simulada', operation: 'aprobacion_despues_del_horario_sintetico' })
  await a.action('habilitar_perfil_despues_entrevista_ui', () => a.click('Aprobar perfil profesional'), `/api/profesionales/administracion/validaciones/${s.validation_id}/resultado-entrevista/`)
  await login(p, s.professional, h)
  const approved = await p.api('confirmar_habilitacion_producida_por_ui', 'GET', '/api/profesionales/mi-perfil/')
  check('perfil_habilitado_ui_estado_real', ident(approved, 'estado_validacion') === 'APROBADO')
  await a.screenshot('02_perfil_habilitado'); await h.clock(null); s.onboarding_complete = true; await h.persist()
}
export async function serviceDetail(h) {
  const p = h.professional
  await portal(p, 'Mis servicios', 'Mis servicios')
  await p.evaluate(`(()=>{const e=[...document.querySelectorAll('.pp-servicio')].find(e=>e.innerText.includes(${JSON.stringify(h.state.service_name)}));if(e)e.dataset.e2eService='true'})()`)
  await p.click('Ver detalle', '[data-e2e-service=true]'); await p.ready()
}
export async function proposalDetail(h) {
  const a = h.admin
  await a.navigate('/administracion/propuestas'); await a.fill('input[type=search]', h.state.service_name)
  await a.click('Revisar propuesta', '.rp-tarjeta'); await a.ready()
}
export async function publicacion(h) {
  const { professional: p, admin: a, state: s, check } = h
  if (s.publication_complete) return
  h.stage('propuesta_servicio_ui')
  s.service_name = 'Servicio UI desarrollo web ' + randomUUID().slice(0, 8)
  await portal(p, 'Mis servicios', 'Mis servicios'); await p.click('+ Nueva propuesta de servicio'); await p.click('Nueva propuesta', '.np-panel')
  await p.wait("document.querySelector('#np-categoria').options.length>1", 'catalogo_no_cargado')
  const category = await p.evaluate("document.querySelector('#np-categoria').options[1].value")
  for (const [id, value] of Object.entries({ 'np-nombre': s.service_name, 'np-descripcion': 'Desarrollo de sitio web y documentos para una organizacion sintetica.', 'np-categoria': category, 'np-modalidad': 'REMOTO', 'np-alcance': 'Sitio web, informe y codigo fuente con una correccion.', 'np-precio': '25000 CLP' })) await p.fill('#' + id, value)
  const service = await p.action('guardar_borrador_servicio_ui', () => p.click('Guardar propuesta como borrador'), '/api/marketplace/mis-servicios/', 'POST', [201])
  s.service_id = ident(service, 'id_servicio'); await h.persist()
  await serviceDetail(h)
  await p.action('enviar_propuesta_revision_ui', () => p.click('Enviar a revision'), `/api/marketplace/mis-servicios/${s.service_id}/enviar-revision/`)
  await proposalDetail(h); await a.click('Solicitar correcciones', '[role=dialog]')
  await a.fillLabel('Correcciones solicitadas', 'Precisar el alcance y el manual de uso en esta propuesta sintetica.', '[role=dialog]')
  await a.action('solicitar_correccion_propuesta_ui', () => a.click('Enviar correcciones'), `/api/marketplace/administracion/servicios/${s.service_id}/revisar/`)
  await serviceDetail(h); await p.click('Editar propuesta', '[role=dialog]', false)
  await p.fillLabel('Alcance', 'Sitio web, informe y codigo fuente, una correccion y manual de uso.', '.ep-formulario')
  await p.action('guardar_correccion_propuesta_ui', () => p.click('Guardar cambios', '.ep-formulario', false), `/api/marketplace/mis-servicios/${s.service_id}/`, 'PATCH', [200])
  await p.action('reenviar_propuesta_corregida_ui', () => p.click('Enviar a revision'), `/api/marketplace/mis-servicios/${s.service_id}/enviar-revision/`)
  await proposalDetail(h); await a.click('Preparar version final')
  await a.action('administracion_envia_version_final_ui', () => a.click('Enviar version al profesional'), `/api/marketplace/administracion/servicios/${s.service_id}/revisar/`)
  await serviceDetail(h); await p.click('Consultar version revisada')
  await p.action('profesional_acepta_version_revisada_ui', () => p.click('Aceptar version revisada'), `/api/marketplace/mis-servicios/${s.service_id}/version-revisada/`)
  await p.action('publicar_servicio_ui', () => p.click('Publicar servicio'), `/api/marketplace/mis-servicios/${s.service_id}/publicar/`)
  await p.screenshot('03_servicio_publicado')
  await h.company.navigate('/')
  const publicService = await h.company.api('confirmar_servicio_publicado_por_ui', 'GET', `/api/marketplace/servicios/${s.service_id}/`)
  check('servicio_publicado_identidad_real', ident(publicService, 'id_servicio') === s.service_id)
  s.publication_complete = true; await h.persist()
}
