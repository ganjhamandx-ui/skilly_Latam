// Confirmaciones HTTP de lectura desde actores aislados; no sustituye acciones UI.
import { ident, login } from './e2e_browser_profesional.mjs'

async function read(actor, name, endpoint, expected, h) {
  if (!endpoint.startsWith('/api/') || endpoint.includes('?')) throw new Error('lectura_no_permitida')
  h.interventions.push({ kind: 'confirmacion_permiso_http_real', actor: actor.name, operation: name })
  const status = await actor.evaluate(`(async()=>{const r=await fetch(${JSON.stringify(endpoint)},{credentials:'same-origin',cache:'no-store',redirect:'error'});return r.status})()`)
  h.check(name, expected.includes(status), { source: 'confirmacion_permiso_http_real', status, expected })
}
export async function seguridad(h) {
  const { professional: p, company: e, state: s } = h
  h.stage('permisos_por_rol_y_objeto_http_real')
  await p.navigate('/portal-profesional'); await e.navigate('/')
  const other = await h.actor('otro_profesional')
  await login(other, h.fixture.professional_ui, h)
  const profile = await other.api('confirmar_actor_profesional_distinto', 'GET', '/api/profesionales/mi-perfil/')
  h.check('actores_profesionales_distintos', ident(profile, 'id_profesional') !== s.professional_id)
  const doc = `/api/profesionales/mis-documentos/${s.corrected_document_id}/descargar/`
  await read(p, 'documento_privado_propietario_admitido_real', doc, [200], h)
  await read(e, 'documento_privado_anonimo_rechazado_real', doc, [403], h)
  await read(other, 'documento_privado_otro_profesional_rechazado_real', doc, [404], h)
  await read(p, 'profesional_no_consulta_documentos_revision_admin', `/api/profesionales/administracion/validaciones/${s.validation_id}/`, [403], h)
  await read(p, 'profesional_no_consulta_pagos_admin', '/api/pagos/administracion/', [403], h)
  await read(e, 'anonimo_no_consulta_feedback_admin', '/api/retroalimentacion/administracion/', [403], h)
  await read(p, 'profesional_no_consulta_feedback_admin', '/api/retroalimentacion/administracion/', [403], h)
  if (s.cierre?.engagement_id) {
    await read(other, 'seguimiento_prestacion_ajena_rechazado_real', `/api/seguimiento/profesional/prestaciones/${s.cierre.engagement_id}/`, [404], h)
  }
  s.permissions_complete = true; await h.persist()
}
