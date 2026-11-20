// Registra constancias de abono simulado y consulta su destino; no calcula saldos bancarios.
import { useCallback, useState } from 'react'
import useCargaAsincrona from './useCargaAsincrona.js'
import './RegistroAbonoAdministracion.css'
/**
 * Obtiene un token CSRF en la sesión vigente para registrar el abono.
 * @returns {Promise<string>} Token entregado por el servidor.
 * @throws {Error} Si falla la conexión, la respuesta HTTP o falta el token.
 */
const csrf = async () => {
  const r=await fetch('/api/acceso/csrf/',{credentials:'same-origin',cache:'no-store'})
  const d=await r.json().catch(()=>({}))
  if(!r.ok||!d.csrfToken)throw new Error('No se pudo obtener el token CSRF.')
  return d.csrfToken
}
/**
 * Lee la respuesta y convierte los rechazos HTTP en errores comunicables.
 * @param {Response} r Respuesta fetch de la API de abonos.
 * @returns {Promise<Object>} Cuerpo JSON o un objeto vacío si no puede leerse.
 * @throws {Error} Si el estado HTTP no es satisfactorio.
 */
async function leer(r){
  const d=await r.json().catch(()=>({}))
  if(!r.ok)throw new Error(d.mensaje||d.detail||Object.values(d).flat().join(' · ')||`Error HTTP ${r.status}`)
  return d
}
/**
 * Reinicia el estado del formulario cuando cambia el identificador del pago.
 * @param {Object} props Datos del pago seleccionado.
 * @param {Object} props.pago Pago con id_pago, estado, neto y moneda.
 * @returns {import('react').ReactElement} Instancia del formulario asociada a ese pago.
 */
export default function RegistroAbonoAdministracion({pago}){
 return <RegistroAbono key={pago.id_pago} pago={pago}/>
}
/**
 * Consulta el destino autorizado y permite registrar una constancia académica.
 * @param {Object} props Datos necesarios para consultar el pago.
 * @param {Object} props.pago Pago mostrado; el formulario solo se renderiza si está LIBERADO.
 * @returns {import('react').ReactElement|null} Cuenta, constancia o formulario de abono simulado.
 */
function RegistroAbono({pago}){
 const [datos,setDatos]=useState(null)
 const [referencia,setReferencia]=useState('')
 const [observacion,setObservacion]=useState('')
 const [confirmado,setConfirmado]=useState(false)
 const [cargando,setCargando]=useState(true)
 const [error,setError]=useState('')
 const [aviso,setAviso]=useState('')
 const [visible,setVisible]=useState(false)
 const ruta=`/api/profesionales/administracion/pagos/${pago.id_pago}/destino-abono/`
 const consultar=useCallback(async signal=>leer(await fetch(ruta,{credentials:'same-origin',cache:'no-store',signal})),[ruta])
 const aplicarConsulta=useCallback(d=>{setDatos(d);setError('');setCargando(false)},[])
 const fallarConsulta=useCallback(e=>{setError(e.message);setCargando(false)},[])
 const recargar=useCargaAsincrona(consultar,aplicarConsulta,fallarConsulta)
 /**
  * Reinicia el estado de consulta y recarga destino y abono del pago seleccionado.
  * @returns {Promise<void>} La gestión de resultados corresponde a useCargaAsincrona.
  */
 async function cargar(){setCargando(true);setError('');await recargar()}
 /**
  * Solicita confirmación local y registra el abono simulado con protección CSRF.
  * @param {import('react').FormEvent} e Envío del formulario cuya navegación se evita.
  * @returns {Promise<void>} Refresca la constancia al guardar o presenta el error recibido.
  */
 async function registrar(e){
  e.preventDefault()
  if(cargando||!confirmado||!referencia.trim()||datos?.abono)return
  if(!window.confirm(`¿Registrar un abono SIMULADO de ${Number(pago.monto_neto_profesional).toLocaleString('es-CL')} ${pago.moneda} para el pago #${pago.id_pago}? Esta acción guardará una constancia académica en SKILLY, pero NO realizará una transferencia bancaria.`))return
  setCargando(true);setError('');setAviso('')
  try{
   const token=await csrf()
   const d=await leer(await fetch(ruta,{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-CSRFToken':token},
    body:JSON.stringify({accion:'REGISTRAR_ABONO',referencia_abono:referencia.trim(),observacion:observacion.trim(),confirmado:true})}))
   setAviso(d.mensaje);setReferencia('');setObservacion('');setConfirmado(false)
   await cargar()
  }catch(e){setError(e.message)}finally{setCargando(false)}
 }
 if(pago.estado_pago!=='LIBERADO')return null
 return <section className="raa-modulo">
  <h4>Registro de abono al profesional</h4>
  <p>El pago está LIBERADO. El abono se registra por separado y no modifica la liberación.</p>
  <p className="raa-simulacion" role="note"><strong>Simulación académica:</strong> el registro deja una constancia para las pruebas de SKILLY. No ejecuta ni acredita una transferencia bancaria real. No ingreses referencias bancarias auténticas.</p>
  {error&&<p className="raa-error" role="alert">{error}</p>}
  {aviso&&<p className="raa-exito" role="status">{aviso}</p>}
  {cargando&&!datos?<p>Consultando cuenta de destino...</p>:datos&&<>
   {datos.abono ? <div className="raa-exito" role="status">
    <strong>Abono de prueba registrado</strong>
    <p>El registro permanece en el historial administrativo. No acredita que el profesional haya recibido dinero real.</p>
    <p>Destino: {datos.abono.destino}</p>
    <p>Neto: {Number(datos.abono.monto_neto).toLocaleString('es-CL')} {datos.abono.moneda}</p>
    <p>Referencia: {datos.abono.referencia_abono}</p>
    <p>Fecha: {new Intl.DateTimeFormat('es-CL',{timeZone:'America/Santiago',dateStyle:'medium',timeStyle:'short'}).format(new Date(datos.abono.fecha_registro))}</p>
    {datos.auditoria_abono && <div className="raa-auditoria">
      <strong>Auditoría administrativa</strong>
      <p>Registrado por: usuario SKILLY #{datos.auditoria_abono.responsable_id}</p>
      <p>Observación: {datos.auditoria_abono.observacion || 'Sin observación adicional'}</p>
    </div>}
   </div>: datos.cuenta ? <>
    <div className="raa-cuenta">
     <strong>Cuenta de destino</strong>
     <p>Titular: {datos.cuenta.titular} · RUT: {datos.cuenta.rut_titular}</p>
     <p>{datos.cuenta.banco} · {datos.cuenta.tipo_cuenta.replaceAll('_',' ')}</p>
     <p>Número: {visible?datos.numero_cuenta:datos.cuenta.numero_oculto} <button type="button" className="raa-sec" onClick={()=>setVisible(!visible)}>{visible?'Ocultar':'Mostrar'}</button></p>
     <p>Correo: {datos.cuenta.correo}</p>
    </div>
    <form onSubmit={registrar} className="raa-form">
      <label>Referencia del abono simulado
        <input required maxLength={120} value={referencia} onChange={e=>setReferencia(e.target.value)} placeholder="Ej.: SIM-SKILLY-ABONO-0001" />
        <small className="raa-ayuda">Identificador ficticio para localizar el registro, no un número de transferencia bancaria real.</small>
      </label>
      <label>Observación administrativa (opcional)
        <textarea maxLength={1000} rows={2} value={observacion} onChange={e=>setObservacion(e.target.value)} placeholder="Ej.: Abono simulado del pago #1 para demostración; no hubo transferencia real." />
        <small className="raa-ayuda">Nota interna para explicar el motivo o contexto del registro. Se conserva para la auditoría administrativa.</small>
      </label>
      <label className="raa-check"><input type="checkbox" checked={confirmado} onChange={e=>setConfirmado(e.target.checked)}/> Confirmo que deseo <strong>registrar un abono de prueba</strong> en SKILLY, sin realizar una transferencia bancaria real.</label>
      <button type="submit" disabled={!confirmado||!referencia.trim()||cargando} className="raa-primary">{cargando?'Registrando...':'Registrar abono de prueba'}</button>
    </form>
   </> : <p className="raa-aviso">El profesional debe registrar primero su cuenta desde «Mi trabajo y pagos». No es posible registrar un abono sin cuenta de destino.</p>}
  </>}
  <button type="button" className="raa-sec" disabled={cargando} onClick={cargar}>↻ Actualizar cuenta y abono</button>
 </section>
}
