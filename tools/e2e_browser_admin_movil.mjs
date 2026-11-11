// Cobertura complementaria de interfaces administrativas reales, solo lectura.
// Se reutiliza la sesion administrativa del driver y su transporte CDP nativo.
import fs from 'node:fs/promises'
import path from 'node:path'

const routes = [
  { key: 'indicadores', route: '/administracion/indicadores', title: 'Indicadores de SKILLY' },
  { key: 'comision', route: '/administracion/comision', title: 'Comisión de SKILLY' },
  { key: 'cancelaciones', route: '/administracion/cancelaciones', title: 'Cargo por cancelación injustificada' },
  { key: 'cuentas', route: '/administracion/cuentas-bancarias', title: 'Cuentas bancarias de SKILLY' },
  { key: 'trazabilidad', route: '/administracion/trazabilidad', title: 'Trazabilidad operacional' },
  { key: 'entregables_alias', route: '/administracion/entregables', title: 'Gestión de solicitudes' },
]

// Los overlays no cambian el texto, sus dimensiones ni la distribucion original.
// Nunca se exportan los valores privados utilizados para calcular los rectangulos.
const redact = `(()=>{
  if(window.__skillyRestoreAdminRedactions)throw new Error('redaccion_administrativa_ya_activa');
  const layer=document.createElement('div');
  layer.id='skilly-admin-mobile-redactions';layer.setAttribute('aria-hidden','true');
  layer.style.cssText='position:fixed;top:0;left:0;width:0;height:0;pointer-events:none;z-index:2147483646';
  const nodes=[],walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  while(walk.nextNode())nodes.push(walk.currentNode);
  let masks=0;
  for(const node of nodes){
    const parent=node.parentElement;
    if(!parent||['SCRIPT','STYLE','OPTION'].includes(parent.tagName))continue;
    const text=node.nodeValue,spans=[];
    if(parent.closest('.bancos-cuenta p'))spans.push([0,text.length]);
    else for(const match of text.matchAll(/(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|\\b\\d[\\d .-]{4,}\\d(?:-[0-9Kk])?\\b)/g))spans.push([match.index,match.index+match[0].length]);
    for(const[start,end]of spans){
      if(start===end)continue;
      const range=document.createRange();range.setStart(node,start);range.setEnd(node,end);
      for(const rect of range.getClientRects()){
        if(rect.width<=0||rect.height<=0||rect.bottom<0||rect.top>innerHeight)continue;
        const mask=document.createElement('span');
        mask.style.cssText='position:fixed;background:#20382f;border-radius:2px;pointer-events:none;left:'+rect.left+'px;top:'+rect.top+'px;width:'+rect.width+'px;height:'+rect.height+'px';
        layer.appendChild(mask);masks++;
      }
    }
  }
  document.body.appendChild(layer);
  window.__skillyRestoreAdminRedactions=()=>{layer.remove();delete window.__skillyRestoreAdminRedactions};
  return masks;
})()`

// Un carrusel con desplazamiento horizontal propio es accesible desplazandolo;
// no se confunde con un control recortado por el documento o por un dialogo.
const controls = `(()=>{
  const width=document.documentElement.clientWidth;
  const items=[...document.querySelectorAll('button,a,input,select,textarea')]
    .filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden')
    .map(e=>{
      const r=e.getBoundingClientRect(),dialog=e.closest('[role=dialog]'),d=dialog?.getBoundingClientRect();
      let scrollable=false;
      for(let p=e.parentElement;p&&p!==document.body;p=p.parentElement){
        if(/auto|scroll/.test(getComputedStyle(p).overflowX)&&p.scrollWidth>p.clientWidth+1){scrollable=true;break}
      }
      return{tag:e.tagName,id:e.id||'',width:r.width,height:r.height,
        outside_document:!scrollable&&(r.left< -1||r.right>width+1),
        outside_dialog:!!d&&!scrollable&&(r.left<d.left-1||r.right>d.right+1)};
    }).filter(e=>e.width>0&&e.height>0);
  return{count:items.length,min_height:items.length?Math.min(...items.map(e=>e.height)):null,
    clipped:items.filter(e=>e.outside_document||e.outside_dialog)};
})()`

async function capture(h, a, key) {
  const measured = await a.measureLayout()
  const measuredControls = await a.evaluate(controls)
  const masked = await a.evaluate(redact)
  try { await a.screenshot('admin_movil_' + key) }
  finally { await a.evaluate('window.__skillyRestoreAdminRedactions?.()') }
  const result = { key, document_client_width: measured.document_client_width,
    document_scroll_width: measured.document_scroll_width,
    document_horizontal_overflow: measured.document_horizontal_overflow,
    controls: measuredControls, redacted_rectangles: masked }
  h.check('admin_movil_geometria_' + key,
    !measured.document_horizontal_overflow && measuredControls.clipped.length === 0,
    { source: 'interfaz_producto_actual_sin_variantes_ab' })
  return result
}

export async function adminMovil(h) {
  const a = h.admin
  if (!a || !Array.isArray(a.responses)) throw new Error('admin_movil_requiere_actor_admin_autenticado')
  const report = { kind: 'interfaz_administrativa_solo_lectura', routes: [],
    bank_configuration_changed: false, commission_changed: false,
    cancellation_configuration_changed: false, visual_style_overrides: false }
  h.adminMovilResults = report
  const firstResponse = a.responses.length
  try {
    for (const item of routes) {
      if (h.completed('admin_movil_http_' + item.key)) continue
      h.stage('admin_movil_' + item.key)
      const fromResponse = a.responses.length
      const navSelector = '.sk-admin-menu a[href="' + item.route + '"]'
      const canUseMenu = await a.evaluate('!!document.querySelector(' + JSON.stringify(navSelector) + ')')
      if (canUseMenu) { await a.clickSelector(navSelector); await a.ready() }
      else await a.navigate(item.route)
      await a.wait('location.pathname===' + JSON.stringify(item.route) + '&&document.querySelector("h1")?.textContent.trim()===' + JSON.stringify(item.title), 'admin_movil_pagina_no_disponible_' + item.key)
      await a.ready()
      h.check('admin_movil_pagina_' + item.key, true, { source: 'ruta_real_producto', route: item.route })
      h.check('admin_movil_sin_error_' + item.key,
        await a.evaluate('!document.querySelector(".adm-error,.bancos-error")'), { source: 'estado_visible_producto' })

      if (item.key === 'cuentas') {
        await a.click('Consultar historial'); await a.ready()
        h.check('admin_movil_historial_cuentas_consultado',
          a.responses.slice(fromResponse).some(r => r.method === 'GET' && r.path === '/api/backoffice/configuracion/cuentas-bancarias/historial/' && r.status === 200),
          { source: 'integracion_http_real_solo_lectura' })
      }
      if (item.key === 'trazabilidad') {
        await a.click('Mostrar todos', '[aria-label="Filtros de trazabilidad"]'); await a.ready()
        h.check('admin_movil_trazabilidad_filtros_todos',
          await a.evaluate('[...document.querySelectorAll("[aria-label=\\"Filtros de trazabilidad\\"] select,[aria-label=\\"Filtros de trazabilidad\\"] input")].every(e=>e.value==="")'),
          { source: 'interaccion_ui_real_filtros_lectura' })
      }
      const geometry = await capture(h, a, item.key)
      if (item.key === 'indicadores') {
        await a.clickSelector('[aria-label="Resumen de indicadores"] .adm-resumen button:first-child')
        await a.wait('!!document.querySelector("[role=dialog] #sk-indicadores-modal-titulo")', 'admin_movil_detalle_indicador_no_abierto')
        report.indicator_dialog = await capture(h, a, 'indicadores_detalle')
        await a.clickSelector('[role="dialog"] button[aria-label="Cerrar detalle"]')
        await a.wait('!document.querySelector("[role=dialog]")', 'admin_movil_detalle_indicador_no_cerrado')
        h.check('admin_movil_indicador_abrir_cerrar', true, { source: 'interaccion_ui_real_sin_mutacion' })
      }
      const requests = a.responses.slice(fromResponse).map(r => ({ method: r.method, path: r.path, status: r.status }))
      h.check('admin_movil_http_' + item.key,
        requests.length > 0 && requests.every(r => ['GET', 'HEAD', 'OPTIONS'].includes(r.method) && r.status >= 200 && r.status < 400),
        { source: 'integracion_http_real_solo_lectura' })
      report.routes.push({ ...item, navigation: canUseMenu ? 'enlace_real_modulo' : 'ruta_real_directa', geometry, requests })
    }
    // El alias tambien debe permitir regresar al modulo canonico mediante su menu.
    if (!h.completed('admin_movil_alias_retorno_canonico')) {
    await a.clickSelector('.sk-admin-menu a[href="/administracion"]'); await a.ready()
    await a.wait('location.pathname==="/administracion"&&document.querySelector("h1")?.textContent.trim()==="Gestión de solicitudes"', 'admin_movil_retorno_no_completado')
    h.check('admin_movil_alias_retorno_canonico', true, { source: 'enlace_real_producto' })
    }
  } finally {
    report.requests = a.responses.slice(firstResponse).map(r => ({ method: r.method, path: r.path, status: r.status }))
    report.only_read_requests = report.requests.every(r => ['GET', 'HEAD', 'OPTIONS'].includes(r.method))
    await fs.writeFile(path.join(h.out, 'administracion_movil_lectura.json'), JSON.stringify(report, null, 2), { flag: 'wx' })
  }
  h.check('admin_movil_sin_mutaciones_http', report.only_read_requests, { source: 'respuestas_http_observadas_por_cdp' })
}
