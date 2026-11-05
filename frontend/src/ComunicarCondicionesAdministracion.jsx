import { useState } from 'react'
import CondicionesPrestacionE3 from './CondicionesPrestacionE3.jsx'

const API = '/api'

function extraerError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const mensajes = Object.entries(datos).flatMap(([campo, valor]) =>
      Array.isArray(valor)
        ? valor.map((mensaje) => `${campo}: ${mensaje}`)
        : [],
    )
    if (mensajes.length) return mensajes.join(' | ')
  }

  return `No fue posible registrar las condiciones (HTTP ${codigo}).`
}

export default function ComunicarCondicionesAdministracion({
  idSolicitud,
  prestacion,
  onRegistrado,
}) {
  const [condiciones, setCondiciones] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [publicadasLocalmente, setPublicadasLocalmente] = useState('')

  if (!prestacion) return null

  const condicionesRegistradas = String(
    prestacion.condiciones_comunicadas || publicadasLocalmente || '',
  ).trim()

  const pendiente = prestacion.estado === 'PENDIENTE_CONTRATACION'

  if (!pendiente && !condicionesRegistradas) return null

  async function registrar(evento) {
    evento.preventDefault()
    const texto = condiciones.trim()
    if (!pendiente || condicionesRegistradas || guardando) return

    if (!texto) {
      setError('Escribe las condiciones que se publicarán para la organización en su seguimiento.')
      return
    }

    const confirmado = window.confirm(
      `¿Confirmas que deseas publicar estas condiciones para la solicitud #${idSolicitud}?\n\n` +
      'SKILLY mostrará el texto a quien consulte la solicitud con su referencia válida. Se registrará trazabilidad; no se enviará correo ni se creará un pago.',
    )
    if (!confirmado) return

    setGuardando(true)
    setError('')
    setAviso('')

    try {
      const respuestaCsrf = await fetch(`${API}/acceso/csrf/`, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })
      const csrf = await respuestaCsrf.json().catch(() => ({}))
      if (!respuestaCsrf.ok || !csrf.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }

      const respuesta = await fetch(
        `${API}/coordinacion/administracion/solicitudes/${idSolicitud}/coordinacion/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({
            accion: 'COMUNICAR_CONDICIONES',
            condiciones_comunicadas: texto,
          }),
        },
      )
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(extraerError(datos, respuesta.status))
      if (!datos.prestacion?.id_prestacion) {
        throw new Error('El servidor respondió, pero no confirmó la prestación actualizada. Revisa la ficha antes de intentar de nuevo.')
      }

      const textoConfirmado = String(datos.prestacion.condiciones_comunicadas || texto).trim()
      setPublicadasLocalmente(textoConfirmado)
      setGuardando(false)
      setAviso('Las condiciones fueron publicadas en el seguimiento de SKILLY.')
      onRegistrado?.(datos.prestacion)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo guardar la comunicación.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="adm-detalle-pago" style={{ marginTop: 18 }}>
      <h4>Condiciones de la prestación</h4>

      {condicionesRegistradas ? (
        <div style={{ display: 'grid', gap: 12 }}>
          <p className="adm-aviso" role="status" style={{ margin: 0 }}>
            ✓ Condiciones publicadas. La organización puede consultarlas con su referencia de seguimiento.
          </p>
          <CondicionesPrestacionE3 texto={condicionesRegistradas} />
          <p style={{ margin: 0, color: '#667970', fontSize: 13 }}>
            Publicarlas no confirma el pago ni la contratación.
          </p>
        </div>
      ) : (
        <>
          <p>
            Escribe las condiciones que la organización podrá consultar dentro de SKILLY usando su referencia de seguimiento. Esta acción registra las condiciones sin enviar correos ni crear pagos.
          </p>
          <form onSubmit={registrar} style={{ display: 'grid', gap: 10 }}>
            <label htmlFor="adm-condiciones-prestacion">Condiciones que verá la organización</label>
            <textarea
              id="adm-condiciones-prestacion"
              className="adm-busqueda"
              rows={5}
              required
              value={condiciones}
              onChange={(evento) => setCondiciones(evento.target.value)}
              disabled={guardando}
              placeholder="Escribe el alcance, precio y demás condiciones acordadas."
              style={{ marginBottom: 0, resize: 'vertical' }}
            />
            <button className="adm-accion" type="submit" disabled={guardando || !condiciones.trim()}>
              {guardando ? 'Registrando condiciones…' : 'Publicar condiciones en SKILLY'}
            </button>
          </form>
        </>
      )}

      {error && <p className="adm-error" role="alert">{error}</p>}
      {aviso && !condicionesRegistradas && <p className="adm-aviso" role="status">{aviso}</p>}
    </div>
  )
}
