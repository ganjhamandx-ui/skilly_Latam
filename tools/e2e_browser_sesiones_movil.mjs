// Interacciones de sesion y limites visibles de rol sobre Chrome Android.
export async function sesionesMoviles(h) {
  const p = h.professional, a = h.admin, e = h.company
  h.stage('sesiones_y_limites_visibles_android')
  if (!h.completed('android_anonimo_portal_solicita_acceso')) {
  await e.navigate('/portal-profesional')
  await e.wait(`!!document.querySelector(${JSON.stringify('.pp-panel a[href="/acceso-profesional"]')})`, 'anonimo_sin_barrera_profesional')
  h.check('android_anonimo_portal_solicita_acceso', await e.evaluate('!document.querySelector(".pp-menu-modulos")'))
  }
  if (!h.completed('android_profesional_no_ve_solicitudes_admin')) {
  await p.navigate('/administracion')
  await p.wait('!!document.querySelector(".adm-login")', 'profesional_sin_barrera_administrativa')
  h.check('android_profesional_no_ve_solicitudes_admin', await p.evaluate('!document.querySelector(".adm-resumen")'))
  await p.screenshot('sesion_profesional_limite_admin')
  }
  await p.navigate('/portal-profesional')
  await p.wait('!!document.querySelector(".pp-menu-modulos")', 'profesional_perdio_sesion_al_visitar_admin')
  // El producto navega al cerrar sesion; CDP Android puede perder el cuerpo
  // del documento anterior. Se exige HTTP 200 y luego la barrera privada real.
  await p.action('android_logout_profesional_ui', () => p.click('Cerrar sesion', 'header'), '/api/acceso/cerrar-sesion/', 'POST', [200], { readBody: false })
  await p.navigate('/portal-profesional')
  await p.wait(`!!document.querySelector(${JSON.stringify('.pp-panel a[href="/acceso-profesional"]')})`, 'portal_accesible_despues_logout')
  h.check('android_portal_privado_bloqueado_despues_logout', await p.evaluate('!document.querySelector(".pp-menu-modulos")'))
  await a.navigate('/administracion')
  await a.wait('!!document.querySelector(".adm-resumen")', 'logout_profesional_altero_sesion_administrativa')
  h.check('android_sesiones_por_rol_aisladas', true, { source: 'interfaz_real_contextos_cookies_separados' })
  await a.action('android_logout_administrativo_ui', () => a.click('Cerrar sesion', 'header'), '/api/acceso/cerrar-sesion/', 'POST', [200], { readBody: false })
  await a.navigate('/administracion')
  await a.wait('!!document.querySelector(".adm-login")', 'administracion_accesible_despues_logout')
  h.check('android_admin_privado_bloqueado_despues_logout', await a.evaluate('!document.querySelector(".adm-resumen")'))
  await a.screenshot('sesion_administrativa_cerrada')
  h.state.mobile_sessions_complete = true
  await h.persist()
}
