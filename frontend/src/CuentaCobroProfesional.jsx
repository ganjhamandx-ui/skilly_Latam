// Consulta y actualiza la cuenta de cobro del profesional sin exponer datos de otros titulares.
import { useCallback, useState } from 'react'
import useCargaAsincrona from './useCargaAsincrona.js'
import './CuentaCobroProfesional.css'

const API = '/api/profesionales/'
const inicial = { titular: '', rut_titular: '', banco: '', tipo_cuenta: 'VISTA', numero_cuenta: '', correo: '' }

/**
 * Formatea el instante de registro en la zona America/Santiago.
 * @param {string|null|undefined} fecha Instante recibido de la API.
 * @returns {string} Fecha legible o «No registrada» si falta o es inválida.
 */
function fechaRegistroChile(fecha) {
  if (!fecha) return 'No registrada'
  const fechaValida = new Date(fecha)
  if (Number.isNaN(fechaValida.getTime())) return 'No registrada'
  return new Intl.DateTimeFormat('es-CL', {
    timeZone: 'America/Santiago', dateStyle: 'medium', timeStyle: 'short',
  }).format(fechaValida)
}


/**
 * Lee la respuesta de cuenta o abonos y propaga los rechazos HTTP.
 * @param {Response} respuesta Respuesta de fetch.
 * @returns {Promise<Object>} JSON recibido o un objeto vacío si falla su lectura.
 * @throws {Error} Si el estado HTTP no es satisfactorio.
 */
async function jsonRespuesta(respuesta) {
  const datos = await respuesta.json().catch(() => ({}))
  if (!respuesta.ok) {
    const detalle = datos.mensaje || datos.detail || Object.values(datos).flat().join(' · ')
    throw new Error(typeof detalle === 'string' ? detalle : `Error HTTP ${respuesta.status}`)
  }
  return datos
}

/**
 * Consulta cuenta y abonos propios y permite reemplazar los datos bancarios.
 * La cuenta consultada llega enmascarada; al editar se exige reingresar su número.
 * @returns {import('react').ReactElement} Formulario, cuenta e historial de abonos simulados.
 */
export default function CuentaCobroProfesional() {
  const [cuenta, setCuenta] = useState(null)
  const [abonos, setAbonos] = useState([])
  const [formulario, setFormulario] = useState(inicial)
  const [editando, setEditando] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  const consultar = useCallback(async (signal) => {
      // Consulta en paralelo la cuenta y sus abonos con la misma señal de cancelación.
      const [a, b] = await Promise.all([
        fetch(`${API}mi-cuenta-bancaria/`, { credentials: 'same-origin', cache: 'no-store', signal }),
        fetch(`${API}mis-abonos/`, { credentials: 'same-origin', cache: 'no-store', signal }),
      ])
      const datosCuenta = await jsonRespuesta(a)
      const datosAbonos = await jsonRespuesta(b)
      return { datosCuenta, datosAbonos }
  }, [])
  const aplicarConsulta = useCallback(({ datosCuenta, datosAbonos }) => {
      setCuenta(datosCuenta.cuenta)
      setAbonos(datosAbonos.abonos || [])
      if (!datosCuenta.cuenta) setEditando(true)
      setError('')
      setCargando(false)
  }, [])
  const fallarConsulta = useCallback((e) => {
    setError(e.message)
    setCargando(false)
  }, [])
  useCargaAsincrona(consultar, aplicarConsulta, fallarConsulta)

  /**
   * Envía la cuenta completa por PUT y reemplaza la representación local por la respuesta.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Vacía el formulario al guardar y presenta los errores capturados.
   */
  async function guardar(evento) {
    evento.preventDefault()
    if (guardando) return
    setError('')
    setAviso('')
    setGuardando(true)
    try {
      const t = await jsonRespuesta(await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin', cache: 'no-store',
      }))
      const respuesta = await fetch(`${API}mi-cuenta-bancaria/`, {
        method: 'PUT', credentials: 'same-origin',
        headers: { 'Content-Type':'application/json', 'X-CSRFToken':t.csrfToken },
        body: JSON.stringify(formulario),
      })
      const datos = await jsonRespuesta(respuesta)
      setCuenta(datos.cuenta)
      setFormulario(inicial)
      setEditando(false)
      setAviso(datos.mensaje)
    } catch (e) { setError(e.message) }
    finally { setGuardando(false) }
  }

  /**
   * Actualiza un campo del formulario preservando los demás valores.
   * @param {string} nombre Clave del dato bancario editado.
   * @param {string} valor Valor recibido del control.
   * @returns {void}
   */
  const campo = (nombre, valor) => setFormulario((anterior) => ({ ...anterior, [nombre]: valor }))

  return <section className="ccp-modulo">
    <p className="ccp-descripcion">Registra tu cuenta para recibir los pagos de tus servicios. Solo tú y la administración autorizada pueden consultar estos datos.</p>
    {error && <p className="ccp-error" role="alert">{error}</p>}
    {aviso && <p className="ccp-exito" role="status">{aviso}</p>}
    {cargando ? <p>Consultando información...</p> : <>
      {cuenta && !editando && <div className="ccp-resumen">
        <h3>Cuenta registrada</h3>
        <dl>
          <div><dt>Titular</dt><dd>{cuenta.titular}</dd></div>
          <div><dt>RUT</dt><dd>{cuenta.rut_titular}</dd></div>
          <div><dt>Banco</dt><dd>{cuenta.banco}</dd></div>
          <div><dt>Tipo de cuenta</dt><dd>{cuenta.tipo_cuenta.replaceAll('_', ' ')}</dd></div>
          <div><dt>Número</dt><dd>{cuenta.numero_oculto}</dd></div>
          <div><dt>Correo</dt><dd>{cuenta.correo}</dd></div>
        </dl>
        <button className="ccp-boton" type="button" onClick={() => {
          setFormulario({ titular:cuenta.titular, rut_titular:cuenta.rut_titular,
            banco:cuenta.banco, tipo_cuenta:cuenta.tipo_cuenta, numero_cuenta:'', correo:cuenta.correo })
          setEditando(true); setAviso('')
        }}>Actualizar cuenta bancaria</button>
      </div>}
      {editando && <form onSubmit={guardar} className="ccp-formulario">
        <h3>{cuenta ? 'Actualizar cuenta' : 'Registrar cuenta para recibir pagos'}</h3>
        {cuenta && <p className="ccp-ayuda">Para actualizar la cuenta, vuelve a ingresar su número completo.</p>}
        <div className="ccp-campos">
          <label>Titular de la cuenta<input required maxLength={180} autoComplete="off" value={formulario.titular} onChange={(e)=>campo('titular',e.target.value)}/></label>
          <label>RUT del titular<input required maxLength={15} placeholder="12.345.678-9" autoComplete="off" value={formulario.rut_titular} onChange={(e)=>campo('rut_titular',e.target.value)}/></label>
          <label>Banco<input required maxLength={120} autoComplete="off" value={formulario.banco} onChange={(e)=>campo('banco',e.target.value)}/></label>
          <label>Tipo de cuenta<select value={formulario.tipo_cuenta} onChange={(e)=>campo('tipo_cuenta',e.target.value)}>
            <option value="VISTA">Cuenta vista</option><option value="CORRIENTE">Cuenta corriente</option><option value="CUENTA_RUT">CuentaRUT</option><option value="AHORRO">Cuenta de ahorro</option>
          </select></label>
          <label>Número de cuenta<input required inputMode="numeric" pattern="[0-9]{5,32}" minLength={5} maxLength={32} autoComplete="off" value={formulario.numero_cuenta} onChange={(e)=>campo('numero_cuenta',e.target.value)}/></label>
          <label>Correo para comprobantes<input required type="email" maxLength={254} autoComplete="off" value={formulario.correo} onChange={(e)=>campo('correo',e.target.value)}/></label>
        </div>
        <div className="ccp-acciones">
          <button type="submit" className="ccp-boton" disabled={guardando}>{guardando ? 'Guardando...' : 'Guardar cuenta'}</button>
          {cuenta && <button type="button" className="ccp-secundario" disabled={guardando} onClick={()=>{setEditando(false);setFormulario(inicial);setError('')}}>Cancelar</button>}
        </div>
      </form>}
      <div className="ccp-abonos">
        <div className="ccp-historial-titulo">
          <h3>Historial de abonos</h3>
          <span className="ccp-etiqueta-simulacion">Simulación académica</span>
        </div>
        <p className="ccp-nota-simulacion">Esta sección muestra abonos <strong>registrados en SKILLY para la demostración</strong>. No acredita transferencias bancarias ni dinero efectivamente recibido. Un pago LIBERADO y un abono registrado son operaciones diferentes.</p>
        {abonos.length === 0 ? <p className="ccp-sin-abonos">Todavía no hay abonos registrados para tus servicios.</p> :
        abonos.map((a)=><article key={a.id_abono} className="ccp-abono-item">
          <div className="ccp-abono-cabecera">
            <div>
              <span className="ccp-abono-subtitulo">Abono #{a.id_abono} · Pago #{a.id_pago}</span>
              <strong className="ccp-abono-monto">{new Intl.NumberFormat('es-CL',{maximumFractionDigits:2}).format(Number(a.monto_neto))} {a.moneda}</strong>
            </div>
            <span className="ccp-abono-estado">Registrado</span>
          </div>
          <dl className="ccp-abono-datos">
            <div><dt>Fecha de registro</dt><dd>{fechaRegistroChile(a.fecha_registro)}</dd></div>
            <div><dt>Cuenta de destino</dt><dd>{a.destino}</dd></div>
            <div><dt>Referencia</dt><dd>{a.referencia_abono}</dd></div>
          </dl>
        </article>)}
      </div>
    </>}
  </section>
}
