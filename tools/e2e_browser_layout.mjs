// A/B visual sin escribir negocio. El driver bloquea POST salvo autenticacion.
import fs from 'node:fs/promises'
import path from 'node:path'

const variants = [
  { name: 'producto_actual', rule: '' },
  { name: 'correo_intro_wrap', rule: '.pp-introduccion p{overflow-wrap:anywhere}' },
]

export async function layout(h) {
  const p = h.professional
  const pdf = path.join(h.out, 'documento-sintetico-para-verificar-ajuste-de-formulario-en-movil.pdf')
  await fs.writeFile(pdf, await fs.readFile(h.pdf), { flag: 'wx' })
  h.layoutResults = []
  for (const panel of ['documentos', 'propuesta', 'entregas']) {
    for (const { name, rule } of h.assertLayout ? variants.slice(0, 1) : variants) {
      h.stage('layout_ab_' + panel + '_' + name)
      await p.navigate('/portal-profesional')
      const baseGeometry = await p.measureLayout()
      await fs.writeFile(path.join(h.out, 'base_' + panel + '_' + name + '.json'), JSON.stringify(baseGeometry, null, 2), { flag: 'wx' })
      if (rule) {
        await p.evaluate(`(()=>{const e=document.createElement('style');e.id='skilly-experimento-layout';e.textContent=${JSON.stringify(rule)};document.head.appendChild(e)})()`)
        h.interventions.push({ kind: 'estilo_efimero_ab', panel, rule })
      }
      const module = panel === 'documentos' ? 'Perfil y validacion' : panel === 'propuesta' ? 'Mis servicios' : 'Trabajo y pagos'
      await p.click(module, 'nav', false)
      await p.click(panel === 'documentos' ? 'Documentos y validacion' : panel === 'propuesta' ? 'Mis servicios' : 'Mi trabajo y pagos', '.pp-opciones-secciones', false)
      if (panel === 'documentos') {
        await p.click('Adjuntar documentos', '[role=dialog]', false); await p.ready()
        await p.fill('#dc-tipo', 'CERTIFICADO'); await p.file('#dc-archivo', [pdf])
      } else if (panel === 'propuesta') {
        await p.click('+ Nueva propuesta de servicio'); await p.click('Nueva propuesta', '.np-panel')
        await p.fill('#np-nombre', 'Propuesta sintetica de observacion visual; no guardar')
        await p.fill('#np-descripcion', 'Formulario de prueba para comparar ajuste visual sin modificar propuestas existentes.')
      } else {
        await p.click('Servicios coordinados', '[role=dialog]', false); await p.ready()
        await p.click('Ver entregas', '.pp-coordinados .pp-servicio'); await p.ready()
        await p.fill('#pp-descripcion-entrega', 'Borrador sintetico de prueba visual; no registrar la entrega.')
        if (await p.evaluate("!!document.querySelector('#pp-archivos-entrega-e3')")) await p.file('#pp-archivos-entrega-e3', [pdf])
      }
      const geometry = await p.screenshot('layout_' + panel + '_' + name)
      const clipped = await p.evaluate("[...document.querySelectorAll('[role=dialog] input,[role=dialog] select,[role=dialog] textarea,[role=dialog] button')].filter(e=>e.getClientRects().length).map(e=>{const d=e.closest('[role=dialog]').getBoundingClientRect(),r=e.getBoundingClientRect();return{tag:e.tagName,id:e.id||'',left:r.left,right:r.right,dialog_left:d.left,dialog_right:d.right}}).filter(e=>e.left<e.dialog_left-1||e.right>e.dialog_right+1)")
      h.layoutResults.push({ panel, variant: name, rule, base_document_scroll_width: baseGeometry.document_scroll_width,
        base_inner_width: baseGeometry.innerWidth, base_document_overflow: baseGeometry.document_horizontal_overflow,
        document_overflow: geometry.document_horizontal_overflow, document_client_width: geometry.document_client_width,
        document_scroll_width: geometry.document_scroll_width, controls_exceeding_dialog: clipped })
      h.check('layout_ab_capturado_' + panel + '_' + name, true, { source: 'interfaz_real_sin_mutacion_de_negocio' })
      if (h.assertLayout) h.check('layout_producto_sin_desborde_ni_controles_recortados_' + panel,
        !baseGeometry.document_horizontal_overflow && !geometry.document_horizontal_overflow && clipped.length === 0,
        { source: 'geometria_producto_actual_sin_estilos_efimeros' })
    }
  }
}
