import { useRef } from 'react'
import { createPortal } from 'react-dom'
import useDialogoAccesible from './useDialogoAccesible.js'
import './VentanaAdministracion.css'

// Ventana reutilizable del back-office. El contenido sigue ejecutando
// sus acciones originales; sólo cambia la presentación.
export default function VentanaAdministracion({ abierta, titulo, onCerrar, bloqueado = false, children }) {
  const panelRef = useRef(null)
  useDialogoAccesible(abierta, panelRef, onCerrar, bloqueado)

  if (!abierta) return null

  return createPortal(
    <div className="vam-fondo" onMouseDown={(evento) => {
      if (!bloqueado && evento.target === evento.currentTarget) onCerrar()
    }}>
      <section ref={panelRef} tabIndex={-1} className="vam-ventana" role="dialog" aria-modal="true" aria-label={titulo}>
        <div className="vam-cabecera">
          <div>
            <small>SKILLY LATAM / BACK-OFFICE</small>
            <h2>{titulo}</h2>
          </div>
          <button type="button" data-dialogo-foco-inicial aria-label={`Cerrar ${titulo}`}
            disabled={bloqueado} onClick={onCerrar}>×</button>
        </div>
        <div className="vam-cuerpo">{children}</div>
      </section>
    </div>,
    document.body,
  )
}
