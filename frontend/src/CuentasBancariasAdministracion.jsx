// Administra cuentas receptoras y su vigencia mediante operaciones autenticadas con CSRF.
import { useCallback, useState } from 'react'
import useCargaAsincrona from './useCargaAsincrona.js'
import AdminNavegacion from './AdminNavegacion.jsx'
import './Administracion.css'
import './CuentasBancariasAdministracion.css'

const API = '/api/backoffice/configuracion/cuentas-bancarias/'
const vacio = { titular:'', rut_titular:'', banco:'', tipo_cuenta:'', numero_cuenta:'', correo:'' }
const etiquetas = { titular:'Titular', rut_titular:'RUT del titular', banco:'Banco', tipo_cuenta:'Tipo de cuenta', numero_cuenta:'Número de cuenta', correo:'Correo de comprobantes' }
const tipos = ['CORRIENTE','VISTA','CUENTA_RUT','AHORRO']

/**
 * Administra cuentas receptoras y consulta el historial de sus modificaciones.
 * Las escrituras obtienen CSRF y recargan las cuentas confirmadas por el servidor.
 * @returns {import('react').ReactElement} Formulario, cuentas e historial opcional.
 */
export default function CuentasBancariasAdministracion() {
  const [cuentas,setCuentas]=useState([])
  const [historial,setHistorial]=useState([])
  const [form,setForm]=useState(vacio)
  const [editando,setEditando]=useState(null)
  const [error,setError]=useState('')
  const [cargando,setCargando]=useState(true)
  const [trabajando,setTrabajando]=useState(false)
  const [verHistorial,setVerHistorial]=useState(false)
  /**
   * Obtiene las cuentas visibles para la sesión administrativa.
   * @param {AbortSignal} signal Señal que cancela una consulta sustituida.
   * @returns {Promise<Object>} Respuesta con la colección de cuentas.
   * @throws {Error} Si falla la conexión o el servidor rechaza la consulta.
   */
  const consultar=useCallback(async (signal)=>{
      const r=await fetch(API,{credentials:'same-origin',headers:{Accept:'application/json'},signal})
      const d=await r.json().catch(()=>({}))
      if(!r.ok) throw new Error(d.mensaje || `HTTP ${r.status}`)
      return d
  },[])
  const aplicarConsulta=useCallback(d=>{setCuentas(d.cuentas || []);setError('');setCargando(false)},[])
  const fallarConsulta=useCallback(e=>{setError(e.message);setCargando(false)},[])
  const recargar=useCargaAsincrona(consultar,aplicarConsulta,fallarConsulta)
  /**
   * Reinicia los indicadores y espera la recarga gestionada por el hook.
   * @returns {Promise<void>} Finalización de la consulta y sus callbacks.
   */
  async function cargar(){setCargando(true);setError('');await recargar()}
  /**
   * Consulta el historial general de cuentas y abre su panel.
   * Los fallos de lectura se muestran en el mensaje del formulario.
   * @returns {Promise<void>} Finalización de la consulta.
   */
  async function historialCuentas(){
    try {const r=await fetch(`${API}historial/`,{credentials:'same-origin'});const d=await r.json();
      if(!r.ok)throw new Error(d.mensaje||`HTTP ${r.status}`);setHistorial(d.historial||[]);setVerHistorial(true)}
    catch(e){setError(e.message)}
  }
  /**
   * Solicita el token asociado a las cookies de la sesión.
   * @returns {Promise<string>} Token necesario para la siguiente escritura.
   * @throws {Error} Si falla la consulta o no se recibe un token válido.
   */
  async function obtenerCsrf(){
    const r=await fetch('/api/acceso/csrf/',{credentials:'same-origin',cache:'no-store'})
    const d=await r.json().catch(()=>({}))
    if(!r.ok||!d.csrfToken)throw new Error('No se pudo obtener el token de seguridad.')
    return d.csrfToken
  }
  /**
   * Envía una operación y recarga cuentas e historial si este está abierto.
   * Los errores se reflejan en pantalla y el bloqueo se libera al terminar.
   * @param {string} url Endpoint de creación o modificación de la cuenta.
   * @param {string} method Método HTTP de escritura.
   * @param {Object} body Datos o acción que validará el servidor.
   * @returns {Promise<void>} Finalización de la escritura y las recargas.
   */
  async function enviar(url,method,body){
    setTrabajando(true);setError('')
    try {const csrf=await obtenerCsrf();const r=await fetch(url,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(body)});
      const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.mensaje || `HTTP ${r.status}`)
      setForm(vacio);setEditando(null);await cargar();if(verHistorial) await historialCuentas()
    }catch(e){setError(e.message)}finally{setTrabajando(false)}
  }
  /**
   * Inicia la creación o modificación según la cuenta en edición.
   * @param {import('react').FormEvent<HTMLFormElement>} e Envío del formulario.
   * @returns {void}
   */
  function guardar(e){e.preventDefault();if(trabajando)return;
    enviar(editando?`${API}${editando}/`:API,editando?'PATCH':'POST',editando?{...form,accion:'MODIFICAR'}:form)
  }
  /**
   * Solicita confirmación antes de cambiar la vigencia o la cuenta principal.
   * @param {Object} c Cuenta seleccionada, con identificador y datos bancarios.
   * @param {'ACTIVAR'|'DESACTIVAR'|'PRINCIPAL'} accion Operación solicitada.
   * @returns {void}
   */
  function accion(c,accion){
    if(trabajando)return
    const descripcion={ACTIVAR:'activar',DESACTIVAR:'desactivar',PRINCIPAL:'seleccionar como principal'}[accion]
    if(!window.confirm(`¿Confirmas ${descripcion} la cuenta ${c.banco} terminada en ${c.numero_cuenta.slice(-4)}?`))return
    enviar(`${API}${c.id_cuenta}/`,'PATCH',{accion})
  }
  return <main className="bancos-root">
    <AdminNavegacion activo="cuentas" />
    <header><span className="bancos-subtitulo">BACK-OFFICE · CONFIGURACIÓN</span><h1>Cuentas bancarias de SKILLY</h1>
    <p>Configura las cuentas receptoras de transferencias. No modifica pagos históricos.</p></header>
    {error && <p role="alert" className="bancos-error">{error}</p>}
    <section className="bancos-panel"><h2>{editando?'Modificar cuenta inactiva':'Registrar nueva cuenta'}</h2>
      <p>Los seis campos son obligatorios. Las cuentas nuevas se crean inactivas hasta su autorización.</p>
      <form onSubmit={guardar} className="bancos-form">
        {Object.keys(vacio).map(k=><label key={k}>{etiquetas[k]} *
          {k==='tipo_cuenta'?<select required value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})}>
            <option value="">Seleccionar</option>{tipos.map(t=><option key={t}>{t}</option>)}</select>:
            <input required type={k==='correo'?'email':'text'} value={form[k]} maxLength={k==='numero_cuenta'?32:254}
              inputMode={k==='numero_cuenta'?'numeric':'text'} pattern={k==='numero_cuenta'?'[0-9]{5,32}':undefined}
              onChange={e=>setForm({...form,[k]:e.target.value})}/>}</label>)}
        <div className="bancos-acciones"><button type="submit" disabled={trabajando}>{editando?'Guardar cambios':'Registrar cuenta'}</button>
          {editando && <button type="button" onClick={()=>{setEditando(null);setForm(vacio)}}>Cancelar</button>}</div>
      </form>
    </section>
    <section className="bancos-panel"><div className="bancos-titulo"><h2>Cuentas registradas</h2><button onClick={cargar}>Actualizar</button></div>
      {cargando?<p>Cargando cuentas…</p>:cuentas.length===0?<p>Sin cuentas registradas.</p>:cuentas.map(c=><article className="bancos-cuenta" key={c.id_cuenta}>
        <h3>{c.banco} · {c.tipo_cuenta} {c.principal?'· PRINCIPAL':''}</h3>
        <p>{c.titular} · RUT {c.rut_titular} · Cuenta terminada en {c.numero_cuenta.slice(-4)}</p>
        <p>{c.activa?'Activa':'Inactiva'} · {c.correo}</p>
        <div className="bancos-acciones">
          {!c.activa&&<button disabled={trabajando} onClick={()=>{setEditando(c.id_cuenta);setForm(Object.fromEntries(Object.keys(vacio).map(k=>[k,c[k]])));window.scrollTo({top:0,behavior:'smooth'})}}>Editar</button>}
          {!c.activa&&<button disabled={trabajando} onClick={()=>accion(c,'ACTIVAR')}>Activar</button>}
          {c.activa&&!c.principal&&<button disabled={trabajando} onClick={()=>accion(c,'PRINCIPAL')}>Establecer principal</button>}
          {c.activa&&!c.principal&&<button disabled={trabajando} onClick={()=>accion(c,'DESACTIVAR')}>Desactivar</button>}
        </div>
      </article>)}
    </section>
    <section className="bancos-panel"><div className="bancos-titulo"><h2>Historial de cambios</h2><button onClick={historialCuentas}>Consultar historial</button></div>
      {verHistorial&&historial.map(h=><p key={h.id_cambio}>Cuenta #{h.id_cuenta} · {h.accion} · Administrador #{h.usuario_id} · {new Date(h.fecha).toLocaleString('es-CL')}</p>)}
    </section>
  </main>
}
