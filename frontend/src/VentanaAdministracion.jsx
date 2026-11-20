import { useRef } from 'react'
import { createPortal } from 'react-dom'
import useDialogoAccesible from './useDialogoAccesible.js'
import './VentanaAdministracion.css'

/**
 * Presenta contenido administrativo en un portal con gestión compartida de foco y cierre.
 * @param {Object} props Estado y contenido del diálogo.
 * @param {boolean} props.abierta Determina si se monta el portal.
 * @param {string} props.titulo Título visible y nombre accesible.
 * @param {function(): void} props.onCerrar Solicita al contenedor cerrar la ventana.
 * @param {boolean} [props.bloqueado=false] Impide cierre por botón, fondo y Escape.
 * @param {import('react').ReactNode} props.children Contenido que conserva sus propios handlers.
 * @returns {import('react').ReactPortal|null} Ventana en document.body o null si está cerrada.
 */
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
