import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
const src=(file)=>readFileSync(new URL(`../src/${file}`,import.meta.url),'utf8')
const api=readFileSync(new URL('../../backend/seguimiento/entregables_multiservicio_e3.py',import.meta.url),'utf8')
test('el selector de archivos depende de clasificacion automatica de servicio',()=>{
 const s=src('PortalProfesional.jsx')
 assert.match(s,/\{habilitaArchivoEntrega && \(/)
 assert.match(s,/setHabilitaArchivoEntrega\(d\.permitir_archivos === true\)/)
 assert.match(s,/setFormatosEntrega\(Array\.isArray\(d\.formatos_permitidos\)/)
})
test('conservar entregas originales sin adjuntos',()=>{
 const s=src('PortalProfesional.jsx')
 assert.match(s,/conArchivos \? formulario : JSON\.stringify/)
 assert.match(s,/\/entregas\/`/)
 assert.match(s,/\/entregas-con-archivos\/`/)
})
test('no registrar una entrega antes de validar archivos',()=>{
 assert.match(api, /comprobados=\[validar_archivo\(a,politica\['formatos_permitidos'\]\) for a in archivos\]/)
 assert.match(api,/with transaction\.atomic\(\):/)
 assert.match(api,/store\.delete\(ruta\)/)
})
test('archivos se guardan fuera de media publico',()=>{
 assert.match(api,/RAIZ_PRIVADA=Path\(settings\.BASE_DIR\)/)
 assert.match(api,/Cache-Control.*private, no-store/)
 assert.match(api,/leer_referencia_seguimiento\(referencia\)/)
})
test('la organizacion obtiene documentos mediante su referencia',()=>{
 const s=src('AdjuntosEntregaEmpresaE3.jsx')
 assert.match(s,/encodeURIComponent\(referencia\)/)
 assert.match(s,/entregables\/archivos\//)
})
test('no existe activacion manual administrativa ni ruta de configuracion',()=>{
 const nav=src('AdminNavegacion.jsx')
 const main=src('main.jsx')
 const urls=readFileSync(new URL('../../backend/seguimiento/urls.py',import.meta.url),'utf8')
 assert.doesNotMatch(nav,/Formatos de entrega|id: 'entregables'/)
 assert.doesNotMatch(main,/EntregablesPorServicioAdministracionE3/)
 assert.doesNotMatch(urls,/ConfiguracionEntregablesAdminE3View|administracion\/entregables\/servicios/)
 assert.doesNotMatch(api,/ParametroSistema|habilitado_servicio/)
 assert.match(api,/politica_entrega_servicio/)
})
