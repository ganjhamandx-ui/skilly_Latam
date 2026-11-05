import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import './VentanaAdministracion.css'

// Ventana reutilizable del back-office. El contenido sigue ejecutando
// sus acciones originales; sólo cambia la presentación.
export default function VentanaAdministracion({ abierta, titulo, onCerrar, bloqueado = false, children }) {
  useEffect(() => {
    if (!abierta) return undefined
    const overflowAnterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const alPulsar = (evento) => {
      if (evento.key === 'Escape' && !bloqueado) onCerrar()
    }
    document.addEventListener('keydown', alPulsar)
    return () => {
      document.body.style.overflow = overflowAnterior
      document.removeEventListener('keydown', alPulsar)
    }
  }, [abierta, bloqueado, onCerrar])

  if (!abierta) return null

  return createPortal(
    <div className="vam-fondo" onMouseDown={(evento) => {
      if (!bloqueado && evento.target === evento.currentTarget) onCerrar()
    }}>
      <section className="vam-ventana" role="dialog" aria-modal="true" aria-label={titulo}>
        <div className="vam-cabecera">
          <div>
            <small>SKILLY LATAM / BACK-OFFICE</small>
            <h2>{titulo}</h2>
          </div>
          <button type="button" autoFocus aria-label={`Cerrar ${titulo}`}
            disabled={bloqueado} onClick={onCerrar}>×</button>
        </div>
        <div className="vam-cuerpo">{children}</div>
      </section>
    </div>,
    document.body,
  )
}
