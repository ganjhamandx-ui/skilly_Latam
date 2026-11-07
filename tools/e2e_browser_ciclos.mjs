// Ciclos de negocio operados desde React. Las APIs auxiliares solo comprueban estado.
import { createHash, randomUUID } from 'node:crypto'
import { ident, portal } from './e2e_browser_profesional.mjs'

function rut(seed) {
  const body = String(80000000 + Number.parseInt(createHash('sha256').update(seed).digest('hex').slice(0, 8), 16) % 19999999)
  const sum = [...body].reverse().reduce((value, d, i) => value + Number(d) * (2 + i % 6), 0)
  const dv = 11 - sum % 11
  return body + '-' + (dv === 11 ? '0' : dv === 10 ? 'K' : dv)
}
const day = offset => new Date(Date.now() + offset * 24 * 3600000).toISOString().slice(0, 10)
export async function disponibilidad(h, date, suffix) {
  const p = h.professional
  await p.navigate('/disponibilidad')
  for (const [name, value] of Object.entries({ fecha: date, hora_inicio: '10:00', hora_fin: '11:00' })) await p.fill(`.dp-formulario [name=${name}]`, value)
  const response = await p.action('crear_disponibilidad_ui_' + suffix, () => p.click('Crear bloque', '.dp-formulario'), '/api/solicitudes/mi-disponibilidad/', 'POST', [201])
  return ident(response, 'id_disponibilidad')
}
export async function solicitudDetalle(h, c) {
  const a = h.admin
  await a.navigate('/administracion'); await a.click('Todas', '.adm-pestanas')
  await a.fill('input.adm-busqueda', c.organization)
  await a.wait(`!![...document.querySelectorAll('button.adm-item')].find(e=>e.innerText.includes(${JSON.stringify(c.organization)}))`, 'solicitud_empresa_no_visible')
  await a.evaluate(`(()=>{const e=[...document.querySelectorAll('button.adm-item')].find(e=>e.innerText.includes(${JSON.stringify(c.organization)}));e.dataset.e2eSolicitud='true'})()`)
  await a.clickSelector('[data-e2e-solicitud=true]'); await a.ready()
}
export async function pagoDetalle(h, c) {
  const a = h.admin
  await a.navigate('/administracion'); await a.click('Pagos', '.adm-accesos-gestion', false).catch(() => a.click('Pagos', 'main', false))
  await a.click('Todos', '.adm-pestanas')
  await a.wait(`!![...document.querySelectorAll('article.adm-item')].find(e=>e.innerText.includes('Pago #${c.payment_id} |'))`, 'pago_no_visible')
  await a.evaluate(`(()=>{const e=[...document.querySelectorAll('article.adm-item')].find(e=>e.innerText.includes('Pago #${c.payment_id} |'));e.dataset.e2ePago='true'})()`)
  await a.click('Ver detalle', '[data-e2e-pago=true]'); await a.ready()
}
export async function seguimiento(h, c) {
  const a = h.company
  await a.navigate('/seguimiento'); await a.fill('#sg-referencia', c.reference)
  await a.action('consultar_seguimiento_ui_' + c.label, () => a.click('Consultar estado'), `/api/solicitudes/seguimiento/${c.reference}/`, 'GET', [200])
  await a.wait("!!document.querySelector('#sg-solicitud')", 'seguimiento_sin_resultado'); await a.ready()
}
export async function contratar(h, label, date) {
  const { professional: p, admin: a, company: e, state: s } = h
  if (s[label]?.contracted) { h.secrets.add(s[label].reference); return s[label] }
  const c = s[label] || { label, date, organization: 'ORGANIZACION UI SINTETICA ' + randomUUID().slice(0, 10) }
  s[label] = c
  h.stage('contratacion_' + label + '_disponibilidad_ui')
  if (!c.availability_id) { c.availability_id = await disponibilidad(h, c.date, label); await h.persist() }
  if (!c.request_id) {
  await e.navigate('/'); await e.fill('input[aria-label="Buscar servicios"]', s.service_name)
  await e.wait("document.querySelectorAll('.servicio-card').length===1", 'servicio_sintetico_no_visible')
  await e.clickSelector('.servicio-card .boton-detalle'); await e.ready(); await e.click('Solicitar este servicio')
  const values = { id_disponibilidad: c.availability_id, nombre_organizacion: c.organization, rut: rut(c.organization), nombre_contacto: 'CONTACTO UI SINTETICO', correo_contacto: 'ui-company-' + randomUUID().slice(0, 8) + '@example.invalid', objetivo: 'Verificar ciclo sintetico desde React en copia aislada', descripcion_necesidad: 'Ejercicio funcional de la plataforma aislada sin compra real ni operacion comercial.' }
  h.secrets.add(values.correo_contacto)
  for (const [name, value] of Object.entries(values)) await e.fill(`.formulario-solicitud [name=${name}]`, value)
  h.stage('contratacion_' + label + '_solicitud_empresa_ui')
  const submitted = await e.action('enviar_solicitud_empresarial_ui_' + label, () => e.click('Enviar solicitud a Skilly'), '/api/solicitudes/enviar/', 'POST', [201])
  c.request_id = ident(submitted, 'id_solicitud'); c.reference = ident(submitted, 'referencia_seguimiento')
  if (typeof c.reference !== 'string') throw new Error('referencia_solicitud_no_recibida')
  await h.persist()
  }
  h.secrets.add(c.reference)
  const base = `/api/coordinacion/administracion/solicitudes/${c.request_id}`
  await solicitudDetalle(h, c)
  if (!c.assigned) {
  await a.action('autoasignar_solicitud_ui_' + label, () => a.click('Asignarme esta solicitud', '[role=dialog]', false), base + '/asignacion/')
  h.check('autoasignacion_duplicada_no_ofrecida_ui_' + label, await a.evaluate("![...document.querySelectorAll('[role=dialog] button')].some(e=>e.innerText.includes('Asignarme esta solicitud'))"))
  c.assigned = true; await h.persist()
  }
  if (!c.association_proposed) {
  await a.action('proponer_asociacion_ui_' + label, () => a.click('Proponer asociacion'), base + '/asociaciones/proponer/', 'POST', [201])
  c.association_proposed = true; await h.persist()
  }
  if (!c.association_confirmed) {
  await a.action('confirmar_asociacion_ui_' + label, () => a.click('Confirmar asociacion'), base + `/asociaciones/${s.professional_id}/confirmar/`)
  c.association_confirmed = true; await h.persist()
  }
  if (!c.engagement_id) {
  const prepared = await a.action('preparar_prestacion_ui_' + label, () => a.click('Preparar prestacion'), base + `/profesionales/${s.professional_id}/preparar-prestacion/`)
  c.engagement_id = ident(prepared, 'id_prestacion'); await h.persist()
  }
  if (!c.conditions_published) {
  await a.fill('#adm-condiciones-prestacion', 'Servicio sintetico aprobado; alcance y precio publicados sin cambios. Ejecucion y documentacion de prueba aislada, sin cobro real.')
  await a.action('publicar_condiciones_ui_' + label, () => a.click('Publicar condiciones en SKILLY'), base + '/coordinacion/')
  c.conditions_published = true; await h.persist()
  h.check('contratacion_sin_pago_no_ofrecida_ui_' + label, await a.evaluate("![...document.querySelectorAll('[role=dialog] button')].some(e=>e.innerText==='Agendar primera reunión')"))
  }
  h.stage('contratacion_' + label + '_pago_sintetico_ui')
  await seguimiento(h, c)
  if (!c.policy_accepted) {
  if (!await e.evaluate("!!document.querySelector('.ace3-dialogo')")) await e.click('Ver y aceptar condiciones')
  await e.clickSelector('.ace3-aceptacion input')
  await e.action('aceptar_politica_cancelacion_ui_' + label, () => e.click('Aceptar y continuar'), `/api/seguimiento/empresa/${c.reference}/politica-cancelacion/`)
  c.policy_accepted = true; await h.persist()
  }
  if (!c.payment_id) {
  await e.clickSelector('input[name=metodo-e3]')
  await e.wait("!!document.querySelector('#comprobante-transferencia')", 'cuenta_receptora_no_disponible')
  await e.file('#comprobante-transferencia', [h.pdf]); await e.fill('#referencia-transferencia', 'SIMULACION-UI-' + randomUUID().slice(0, 8))
  const payment = await e.action('enviar_comprobante_sintetico_ui_' + label, () => e.click('Enviar comprobante para verificacion'), `/api/pagos/empresa/${c.reference}/transferencia/`, 'POST', [201])
  c.payment_id = ident(payment, 'id_pago'); await h.persist()
  }
  if (!c.payment_verified) {
  await pagoDetalle(h, c)
  await a.fillLabel('Observacion administrativa', 'Comprobante sintetico de prueba en copia aislada; no se recibio ni se movio dinero real.', '[role=dialog]')
  await a.clickSelector('[role=dialog] input[type=checkbox]')
  h.interventions.push({ kind: 'recepcion_bancaria_simulada', operation: 'verificacion_transferencia_ui_' + label })
  const verified = await a.action('verificar_transferencia_sintetica_ui_' + label, () => a.click('Verificar transferencia'), `/api/pagos/administracion/${c.payment_id}/`)
  h.check('pago_retenido_estado_real_' + label, ident(verified, 'estado_pago') === 'RETENIDO')
  c.payment_verified = true; await h.persist()
  }
  await solicitudDetalle(h, c)
  const hired = await a.action('agendar_primera_reunion_contratar_ui_' + label, () => a.click('Agendar primera reunion'), `/api/coordinacion/administracion/prestaciones/${c.engagement_id}/agenda/`)
  h.check('contratacion_estado_real_' + label, ident(hired, 'prestacion_contratada') === true)
  await a.screenshot('04_contrato_' + label)
  c.contracted = true; await h.persist(); return c
}
async function professionalEngagement(h, target = 'Ver entregas') {
  const p = h.professional
  await portal(p, 'Trabajo y pagos', 'Mi trabajo y pagos', 'Servicios coordinados')
  await p.wait("!!document.querySelector('.pp-coordinados .pp-servicio')", 'prestacion_no_visible_portal')
  await p.click(target, '.pp-coordinados .pp-servicio'); await p.ready()
}
async function delivery(h, c, corrected) {
  const p = h.professional
  await professionalEngagement(h)
  await p.fill('#pp-descripcion-entrega', corrected ? 'Segunda version sintetica con la observacion empresarial corregida.' : 'Primera entrega sintetica que sera observada para probar la correccion.')
  await p.fill('#pp-referencia-entrega', 'https://entrega.example.invalid/version-' + (corrected ? '2' : '1'))
  const withFile = await p.evaluate("!!document.querySelector('#pp-archivos-entrega-e3')")
  if (withFile) await p.file('#pp-archivos-entrega-e3', [h.pdf])
  return p.action('registrar_entrega_ui_' + (corrected ? 'corregida' : 'inicial'), () => p.click('Registrar entrega'), `/api/seguimiento/profesional/prestaciones/${c.engagement_id}/${withFile ? 'entregas-con-archivos' : 'entregas'}/`, 'POST', [201])
}
async function resolveClaim(h, id, effect) {
  const a = h.admin
  await a.navigate('/administracion/reclamos'); await a.fill('#adm-reclamos-busqueda', String(id))
  await a.evaluate(`(()=>{const e=[...document.querySelectorAll('button.adm-item')].find(e=>e.querySelector('strong')?.textContent.trim().startsWith('Reclamo #${id} —'));if(e)e.dataset.e2eReclamo='true'})()`)
  await a.clickSelector('[data-e2e-reclamo=true]'); await a.ready()
  await a.fill('#reclamo-decision', 'ACEPTAR_CIERRE_PRUEBA'); await a.fill('#reclamo-efecto', effect)
  await a.fill('#reclamo-observacion', 'Revision sintetica documentada en copia aislada; no se ordena ninguna transferencia real.')
  return a.action('resolver_reclamo_ui_' + effect.toLowerCase(), () => a.click('Revisar y confirmar resolucion'), `/api/seguimiento/administracion/reclamos/${id}/`, 'POST', [201])
}
export async function ciclos(h) {
  const { professional: p, admin: a, company: e, state: s } = h
  await e.navigate('/')
  h.stage('ciclo_exitoso_ui')
  const c = await contratar(h, 'cierre', day(10))
  if (!c.complete) {
  if (!c.reschedule_confirmed) {
  if (!c.alternative_id) { c.alternative_id = await disponibilidad(h, day(11), 'reagendamiento'); await h.persist() }
  if (!c.reschedule_id) {
  await seguimiento(h, c); await e.fillLabel('Motivo del cambio', 'La organizacion sintetica solicita cambiar la primera reunion futura desde la plataforma.', '.rea-panel')
  const reschedule = await e.action('solicitar_reagendamiento_ui', () => e.click('Enviar solicitud a SKILLY', '.rea-panel'), `/api/reagendamientos/organizacion/${c.reference}/`, 'POST', [201])
  c.reschedule_id = ident(reschedule, 'id')
  await h.persist()
  }
  h.stage('reagendamiento_consenso_ui')
  if (!c.reschedule_proposed) {
  await a.navigate('/administracion')
  await a.evaluate(`(()=>{const e=[...document.querySelectorAll('.rea-caso')].find(e=>e.querySelector('strong')?.textContent.startsWith('Solicitud #${c.reschedule_id} ·'));if(e)e.dataset.e2eReagenda='true'})()`)
  await a.fill('[data-e2e-reagenda=true] select', c.alternative_id)
  await a.action('administracion_propone_reagendamiento_ui', () => a.click('Proponer al profesional', '[data-e2e-reagenda=true]'), '/api/reagendamientos/administracion/')
  c.reschedule_proposed = true; await h.persist()
  }
  if (!c.reschedule_professional_accepted) {
  await p.navigate('/portal-profesional')
  await p.action('profesional_acepta_reagendamiento_ui', () => p.click('Aceptar bloque propuesto', '.rea-panel'), '/api/reagendamientos/profesional/')
  c.reschedule_professional_accepted = true; await h.persist()
  }
  if (!c.reschedule_company_accepted) {
  await seguimiento(h, c)
  await e.action('empresa_acepta_reagendamiento_ui', () => e.click('Aceptar horario alternativo propuesto'), `/api/reagendamientos/organizacion/${c.reference}/`)
  c.reschedule_company_accepted = true; await h.persist()
  }
  await a.navigate('/administracion')
  const agreed = await a.action('administracion_confirma_reagendamiento_ui', () => a.click('Confirmar reagendamiento en agenda'), '/api/reagendamientos/administracion/')
  h.check('reagendamiento_confirmado_estado_real', ident(agreed, 'estado') === 'CONFIRMADO')
  c.reschedule_confirmed = true; await h.persist()
  await a.screenshot('05_reagendamiento_confirmado')
  }
  h.stage('avances_y_entregas_ui')
  if (!c.advance_done) {
  await professionalEngagement(h, 'Ver seguimiento'); await p.click('Registrar avance'); await p.click('Nuevo avance')
  await p.fill('#rap-estado', 'EN_PROGRESO'); await p.fill('#rap-detalle', 'Avance sintetico real registrado mediante React en la copia aislada.')
  await p.action('registrar_avance_ui', () => p.click('Confirmar registro de avance', '.rap-formulario'), `/api/seguimiento/profesional/prestaciones/${c.engagement_id}/`, 'POST', [201])
  c.advance_done = true; await h.persist()
  }
  if (!c.first_delivery_id) {
  const first = await delivery(h, c, false); c.first_delivery_id = ident(first, 'id_entrega'); c.first_delivery_version = ident(first, 'version'); await h.persist()
  }
  if (!c.first_delivery_observed) {
  await seguimiento(h, c); await e.click('Registrar observaciones')
  await e.fill('#sg-observacion-' + c.first_delivery_id, 'Corregir la seccion de prueba antes de aceptar esta entrega sintetica.')
  const observed = await e.action('empresa_observa_entrega_ui', () => e.click('Enviar observaciones'), `/api/seguimiento/empresa/${c.reference}/entregas/${c.first_delivery_id}/`, 'POST', [201])
  h.check('entrega_observada_estado_real', ident(observed, 'estado') === 'CON_OBSERVACIONES')
  c.first_delivery_observed = true; await h.persist()
  }
  if (!c.corrected_delivery_id) {
  await pagoDetalle(h, c)
  await a.action('liberacion_con_observaciones_rechazada_ui', () => a.click('Liberar pago al profesional'), `/api/pagos/administracion/${c.payment_id}/liberar/`, 'POST', [409])
  const second = await delivery(h, c, true); c.corrected_delivery_id = ident(second, 'id_entrega')
  h.check('entrega_incrementa_version_real', ident(second, 'version') === c.first_delivery_version + 1); await h.persist()
  }
  if (!c.corrected_delivery_accepted) {
  await seguimiento(h, c)
  const accepted = await e.action('empresa_acepta_correccion_ui', () => e.click('Aceptar entrega'), `/api/seguimiento/empresa/${c.reference}/entregas/${c.corrected_delivery_id}/`)
  h.check('entrega_aceptada_estado_real', ident(accepted, 'estado') === 'ACEPTADA')
  h.check('aceptacion_duplicada_no_ofrecida_ui', await e.evaluate("![...document.querySelectorAll('button')].some(e=>e.innerText==='Aceptar entrega')"))
  c.corrected_delivery_accepted = true; await h.persist()
  await e.screenshot('06_entrega_corregida_aceptada')
  }
  h.stage('reclamo_cierre_feedback_liberacion_ui')
  if (!c.claim_id) {
  await seguimiento(h, c); await e.click('Presentar un reclamo', 'body', false)
  await e.fill('#sg-motivo', 'Otro incidente de la prestación'); await e.fill('#sg-descripcion-reclamo', 'La organizacion sintetica solicita revision formal del resultado antes del cierre aislado.')
  const claim = await e.action('empresa_presenta_reclamo_ui', () => e.click('Enviar reclamo a Skilly'), `/api/seguimiento/empresa/${c.reference}/reclamos/`, 'POST', [201])
  c.claim_id = ident(claim, 'id_reclamo'); await h.persist()
  }
  if (!c.claim_resolved) {
  await pagoDetalle(h, c)
  await a.action('liberacion_con_reclamo_abierto_rechazada_ui', () => a.click('Liberar pago al profesional'), `/api/pagos/administracion/${c.payment_id}/liberar/`, 'POST', [409])
  await resolveClaim(h, c.claim_id, 'LIBERACION')
  c.claim_resolved = true; await h.persist()
  }
  if (!c.closed) {
  await solicitudDetalle(h, c); await a.click('Consultar avances')
  const closed = await a.action('finalizar_prestacion_ui', () => a.click('Finalizar prestacion'), `/api/seguimiento/administracion/prestaciones/${c.engagement_id}/`)
  h.check('prestacion_finalizada_estado_real', ident(closed, 'estado') === 'FINALIZADA')
  c.closed = true; await h.persist()
  }
  if (!c.feedback_id) {
  await seguimiento(h, c); await e.click('Retroalimentacion privada', 'body', false)
  c.feedback_content = 'RETROALIMENTACION PRIVADA UI SINTETICA ' + randomUUID().slice(0, 8)
  await e.fill('#sg-feedback', c.feedback_content)
  const feedback = await e.action('empresa_envia_feedback_privado_ui', () => e.click('Enviar retroalimentacion privada'), `/api/retroalimentacion/empresa/${c.reference}/`, 'POST', [201])
  c.feedback_id = ident(feedback, 'id_feedback'); h.check('feedback_visibilidad_privada_real', ident(feedback, 'visibilidad') === 'PRIVADA')
  await h.persist()
  }
  await a.navigate('/administracion/retroalimentacion')
  h.check('administracion_ve_feedback_privado_ui', await a.evaluate(`document.body.innerText.includes(${JSON.stringify(c.feedback_content)})`))
  const publicService = await e.api('confirmar_feedback_no_publicado', 'GET', `/api/marketplace/servicios/${s.service_id}/`)
  h.check('feedback_ausente_marketplace_real', !JSON.stringify(publicService).includes(c.feedback_content))
  await pagoDetalle(h, c)
  const released = await a.action('liberar_pago_sintetico_ui', () => a.click('Liberar pago al profesional'), `/api/pagos/administracion/${c.payment_id}/liberar/`)
  h.check('pago_liberado_estado_real', ident(released, 'estado_pago') === 'LIBERADO')
  const detail = await a.api('confirmar_comision_neto_liberados', 'GET', `/api/pagos/administracion/${c.payment_id}/`)
  const total = Number(ident(detail, 'monto_total')), fee = Number(ident(detail, 'monto_comision')), net = Number(ident(detail, 'monto_neto_profesional'))
  h.check('comision_y_neto_conservan_total_real', total > 0 && fee >= 0 && net >= 0 && Math.abs(total - fee - net) < 0.01)
  h.interventions.push({ kind: 'liberacion_contable_sintetica', operation: 'sin_transferencia_bancaria_real' })
  await a.screenshot('07_pago_liberado_comision')
  c.complete = true; await h.persist()
  }
  await cancelar(h, await contratar(h, 'cancelacion', day(12)))
  s.cycles_complete = true; await h.persist()
}
export async function cancelar(h, c) {
  const { company: e, admin: a } = h
  h.stage('cancelacion_evaluacion_y_reversa_ui')
  if (c.complete) return
  if (!c.case_id) {
  await seguimiento(h, c); await e.click('Presentar un reclamo', 'body', false)
  await e.fill('#sg-motivo', 'Cancelación solicitada por la organización')
  await e.fill('#sg-descripcion-reclamo', 'Cancelacion sintetica justificada del segundo escenario aislado; conservar antecedentes y revisar sin dinero real.')
  await e.file('#sg-evidencia-cancelacion', [h.pdf])
  const cancellation = await e.action('empresa_solicita_cancelacion_ui', () => e.click('Enviar reclamo a Skilly'), `/api/seguimiento/empresa/${c.reference}/cancelaciones/`, 'POST', [201])
  c.case_id = ident(cancellation, 'id_expediente'); c.claim_id = ident(cancellation, 'id_reclamo')
  await h.persist()
  }
  if (!c.case_evaluated) {
  await a.navigate('/administracion/expedientes-cancelacion')
  await a.click('#' + c.case_id + ' · Prestacion #' + c.engagement_id, 'main', false)
  await a.fill('#e3-dec', 'JUSTIFICADA'); await a.fill('#e3-trabajo', '0')
  await a.fill('#e3-fund', 'Evaluacion sintetica documentada: solicitud justificada y sin trabajo acreditado ni cargo, preservando los antecedentes.')
  await a.action('evaluar_cancelacion_ui', () => a.click('Guardar evaluacion'), `/api/seguimiento/administracion/cancelaciones/${c.case_id}/`, 'PATCH', [200])
  c.case_evaluated = true; await h.persist()
  }
  if (!c.claim_resolved) {
  await resolveClaim(h, c.claim_id, 'REVERSA')
  c.claim_resolved = true; await h.persist()
  }
  if (!c.cancelled) {
  await solicitudDetalle(h, c); await a.click('Gestionar agenda')
  await a.fillLabel('Operacion', 'CANCELAR', '.sk-agenda-e3')
  await a.fillLabel('Motivo administrativo', 'Cancelacion sintetica revisada y autorizada en expediente; sin dinero real.', '.sk-agenda-e3')
  await a.action('cancelar_contrato_revisado_ui', () => a.click('Confirmar decision administrativa'), `/api/coordinacion/administracion/prestaciones/${c.engagement_id}/agenda/`)
  c.cancelled = true; await h.persist()
  }
  await pagoDetalle(h, c)
  if (!c.reversal_id) {
  await a.action('pago_cancelado_liberacion_rechazada_ui', () => a.click('Liberar pago al profesional'), `/api/pagos/administracion/${c.payment_id}/liberar/`, 'POST', [409])
  await a.fill('#reversa-motivo', 'Prestacion sintetica cancelada y revisada; reversa academica solicitada sin movimiento real.')
  const reversal = await a.action('solicitar_reversa_sintetica_ui', () => a.click('Registrar solicitud de reversa'), `/api/pagos/administracion/${c.payment_id}/reversas/`, 'POST', [201])
  c.reversal_id = ident(reversal, 'id_reversa')
  await h.persist()
  h.check('reversa_duplicada_no_ofrecida_ui', await a.evaluate("![...document.querySelectorAll('button')].some(e=>e.innerText==='Registrar solicitud de reversa')"))
  }
  await a.fill('#reversa-fundamento', 'Se registra exclusivamente una simulacion academica de devolucion total, sin transferencia bancaria real.')
  await a.clickSelector('section[aria-label="Resolución de reversas E3"] input[type=checkbox]')
  h.interventions.push({ kind: 'devolucion_total_simulada', operation: 'confirmacion_ui_sin_movimiento_bancario' })
  const simulated = await a.action('simular_devolucion_total_ui_sin_dinero', () => a.click('Simular devolucion total (sin dinero)'), `/api/pagos/administracion/${c.payment_id}/reversas/${c.reversal_id}/resolver/`)
  h.check('reversa_estado_explicitamente_simulado', ident(simulated, 'estado_reversa') === 'SIMULADA' && ident(simulated, 'estado_pago') === 'REVERSA_SIMULADA' && ident(simulated, 'ambiente') === 'SIMULACION_ACADEMICA')
  await a.screenshot('08_reversa_explicitamente_simulada'); c.complete = true; await h.persist()
}
