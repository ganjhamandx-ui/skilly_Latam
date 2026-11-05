import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const src=(file)=>readFileSync(new URL(`../src/${file}`,import.meta.url),'utf8')
const py=readFileSync(new URL('../../backend/seguimiento/entregables_multiservicio_e3.py',import.meta.url),'utf8')
test('sin habilitaciones manuales administrativas',()=>{
 assert.doesNotMatch(src('AdminNavegacion.jsx'),/Formatos de entrega/)
 assert.doesNotMatch(src('main.jsx'),/import EntregablesPorServicioAdministracionE3/)
 assert.doesNotMatch(py,/ParametroSistema|HistorialParametro|ConfiguracionEntregablesAdminE3View/)
})
test('eleccion de formatos la decide el servidor segun servicio',()=>{
 assert.match(py,/def politica_entrega_servicio\(servicio\)/)
 assert.match(py,/def servicio_de_prestacion\(prestacion\)/)
 assert.match(py,/politica=politica_entrega_servicio\(servicio_de_prestacion\(prestacion\)\)/)
 assert.match(py,/validar_archivo\(a,politica\['formatos_permitidos'\]\)/)
})
test('profesional ve formatos automaticos sin carga obligatoria',()=>{
 const p=src('PortalProfesional.jsx')
 assert.match(p,/setFormatosEntrega\(Array\.isArray\(d\.formatos_permitidos\)/)
 assert.match(p,/accept=\{formatosEntrega.join/)
 assert.match(p,/conArchivos \? formulario : JSON\.stringify/)
})
test('se preservan descargas privadas y operaciones originales',()=>{
 assert.match(py,/leer_referencia_seguimiento\(referencia\)/)
 assert.match(py,/RAIZ_PRIVADA=Path\(settings\.BASE_DIR\)/)
 assert.doesNotMatch(py,/Webpay|ReversaPago|monto_total/)
})
