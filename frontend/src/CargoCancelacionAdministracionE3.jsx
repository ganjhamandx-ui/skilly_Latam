import { useEffect, useState } from 'react'
import AdminNavegacion from './AdminNavegacion.jsx'
import './Administracion.css'

const URL = '/api/backoffice/configuracion/cancelaciones/'

const mostrarPorcentaje = (valor) => {
  if (valor == null || valor === '') return 'Sin configurar'
  const numero = Number(valor)
  return Number.isFinite(numero)
    ? `${new Intl.NumberFormat('es-CL', { maximumFractionDigits: 4 }).format(numero)} %`
    : 'No disponible'
}

const fechaLocal = (valor) => {
  if (!valor) return 'Sin información'
  const fecha = new Date(valor)
  return Number.isNaN(fecha.getTime()) ? 'Fecha no disponible' :
    fecha.toLocaleString('es-CL', { dateStyle: 'medium', timeStyle: 'short' })
}

const detalleError = (datos, codigo) => {
  if (datos?.mensaje) return datos.mensaje
  if (datos?.detail) return String(datos.detail)
  if (datos?.valor_nuevo) return Array.isArray(datos.valor_nuevo)
    ? datos.valor_nuevo.join(' ') : String(datos.valor_nuevo)
  return `No se pudo completar la operación (HTTP ${codigo}).`
}

export default function CargoCancelacionAdministracionE3() {
  const [parametro, setParametro] = useState(null)
  const [historial, setHistorial] = useState([])
  const [revision, setRevision] = useState(0)
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [nuevo, setNuevo] = useState('')
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [confirmando, setConfirmando] = useState(false)

  useEffect(() => {
    let activo = true
    async function cargar() {
      try {
        const respuesta = await fetch(URL, {
          credentials: 'same-origin', cache: 'no-store',
          headers: { Accept: 'application/json' },
        })
        const datos = await respuesta.json().catch(() => ({}))
        if (!respuesta.ok) throw new Error(detalleError(datos, respuesta.status))
        if (!Array.isArray(datos.historial)) throw new Error('Respuesta incompleta del servidor.')
        if (activo) {
          setParametro(datos.parametro || null)
          setHistorial(datos.historial)
          setError('')
        }
      } catch (fallo) {
        if (activo) setError(fallo.message || 'No fue posible consultar el porcentaje.')
      } finally {
        if (activo) setCargando(false)
      }
    }
    void cargar()
    return () => { activo = false }
  }, [revision])

  const normalizado = nuevo.trim().replace(',', '.')
  const valor = Number(normalizado)
  const valido = /^\d{1,3}(?:\.\d{1,4})?$/.test(normalizado) &&
    Number.isFinite(valor) && valor >= 0 && valor <= 100
  const modificado = valido && (parametro === null || valor !== Number(parametro.valor_actual))

  async function guardar() {
    if (!confirmando || !modificado || guardando) return
    setError('')
    setMensaje('')
    setGuardando(true)
    try {
      const tokenRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin', cache: 'no-store',
      })
      const tokenDatos = await tokenRespuesta.json().catch(() => ({}))
      if (!tokenRespuesta.ok || !tokenDatos.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }
      const respuesta = await fetch(URL, {
        method: 'PATCH', credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': tokenDatos.csrfToken,
        },
        body: JSON.stringify({ valor_nuevo: normalizado }),
      })
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(detalleError(datos, respuesta.status))
      setMensaje(datos.mensaje || 'Cambio guardado correctamente.')
      setNuevo('')
      setConfirmando(false)
      setCargando(true)
      setRevision((v) => v + 1)
    } catch (fallo) {
      setError(fallo.message || 'No se pudo guardar el cambio.')
      setConfirmando(false)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="adm-pagina">
      <header className="adm-header">
        <a className="adm-logo" href="/administracion"><span className="adm-estrella">✦</span> Skilly</a>
        <nav aria-label="Enlaces principales">
          <a href="/administracion">Administración</a>
          <a href="/">Marketplace</a>
        </nav>
      </header>
      <AdminNavegacion activo="cancelaciones" />
      <main className="adm-contenedor">
        <div className="adm-intro">
          <span className="adm-eyebrow">BACK-OFFICE · POLÍTICAS ECONÓMICAS</span>
          <h1>Cargo por cancelación injustificada</h1>
          <p>Configura el porcentaje de gestión de SKILLY. Es independiente de la comisión por servicio finalizado.</p>
        </div>
        <section className="adm-panel" aria-labelledby="cargo-configuracion-titulo">
          <div className="adm-panel-header">
            <h2 id="cargo-configuracion-titulo">Porcentaje vigente</h2>
            <button className="adm-secundario" type="button" disabled={cargando}
              onClick={() => { setCargando(true); setRevision((v) => v + 1) }}>
              ↻ Actualizar
            </button>
          </div>
          {error && <p className="adm-error" role="alert">{error}</p>}
          {mensaje && <p className="adm-aviso" role="status">{mensaje}</p>}
          {cargando ? <p role="status">Consultando la configuración…</p> : (
            <>
              <div className="adm-datos">
                <div>
                  <small>Cargo de gestión configurado</small>
                  <strong style={{ fontSize: 30 }}>{mostrarPorcentaje(parametro?.valor_actual)}</strong>
                </div>
                <div>
                  <small>Última actualización</small>
                  <strong>{fechaLocal(parametro?.fecha_actualizacion)}</strong>
                </div>
                <div>
                  <small>Responsable</small>
                  <strong>{parametro?.responsable_actualizacion?.correo || 'Sin configurar'}</strong>
                </div>
              </div>
              <p className="adm-nota">
                Este ajuste no se aplica por sí solo: SKILLY debe evaluar una cancelación y
                verificar los derechos de reembolso antes de liquidar cualquier cargo.
                Los cambios nunca recalculan contratos anteriores.
              </p>
              <div style={{ display: 'grid', gap: 10, maxWidth: 450 }}>
                <label htmlFor="sk-cargo-valor"><strong>Nuevo porcentaje de cancelación (0–100 %)</strong></label>
                <input id="sk-cargo-valor" className="adm-busqueda" inputMode="decimal"
                  autoComplete="off" placeholder="Ejemplo: 5" value={nuevo}
                  onChange={(e) => { setNuevo(e.target.value); setError(''); setMensaje(''); setConfirmando(false) }} />
                {nuevo.trim() && !valido && (
                  <p className="adm-error" role="alert">Ingresa un porcentaje de 0 a 100, con hasta cuatro decimales.</p>
                )}
                {valido && !modificado && <p className="adm-nota">Este porcentaje ya está vigente.</p>}
                {!confirmando ? (
                  <button className="adm-secundario" type="button" disabled={!modificado}
                    onClick={() => setConfirmando(true)}>Revisar cambio</button>
                ) : (
                  <div className="adm-panel" role="group" aria-label="Confirmar nuevo porcentaje">
                    <p>Cambiarás el porcentaje de <strong>{mostrarPorcentaje(parametro?.valor_actual)}</strong> a{' '}
                      <strong>{mostrarPorcentaje(valor)}</strong>.</p>
                    <p className="adm-nota">El valor anterior, el nuevo, la fecha y tu usuario quedarán en el historial.</p>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      <button className="adm-secundario" type="button" disabled={guardando}
                        onClick={() => setConfirmando(false)}>Volver</button>
                      <button className="adm-secundario" type="button" disabled={guardando || !modificado}
                        onClick={guardar}>{guardando ? 'Guardando…' : 'Confirmar y guardar'}</button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </section>
        <section className="adm-panel" aria-label="Historial de cambios del cargo por cancelación">
          <h2>Historial de modificaciones</h2>
          {!cargando && historial.length === 0 && <p className="adm-vacio">Aún no hay cambios registrados.</p>}
          <div className="adm-lista">
            {historial.map((evento) => (
              <div className="adm-item" key={evento.id_historial_parametro}>
                <div className="adm-item-cuerpo">
                  <strong>{mostrarPorcentaje(evento.valor_anterior)} → {mostrarPorcentaje(evento.valor_nuevo)}</strong>
                  <small>Fecha: {fechaLocal(evento.fecha_cambio)}</small>
                  <small>Responsable: {evento.responsable_skilly?.correo || 'No informado'}</small>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
