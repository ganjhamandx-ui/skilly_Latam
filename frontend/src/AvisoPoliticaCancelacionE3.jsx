import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import './AvisoPoliticaCancelacionE3.css'

/** Presentación solamente: la aceptación real se registra en la API de Fase 6B. */
export default function AvisoPoliticaCancelacionE3({
  politica, acepto, onCambiarAceptacion, guardando, error, onAceptar, onCerrar,
}) {
  const panelRef = useRef(null)
  const cerrarRef = useRef(null)
  const porcentaje = Number(politica?.porcentaje)
  const porcentajeLegible = Number.isFinite(porcentaje)
    ? porcentaje.toLocaleString('es-CL', { maximumFractionDigits: 4 })
    : 'No informado'

  useEffect(() => {
    // Mantiene el foco y bloquea el desplazamiento de fondo durante el aviso.
    const focoAnterior = document.activeElement
    const overflowAnterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    cerrarRef.current?.focus()
    return () => {
      document.body.style.overflow = overflowAnterior
      if (focoAnterior && typeof focoAnterior.focus === 'function') focoAnterior.focus()
    }
  }, [])

  // Controla las teclas del diálogo para cerrar o mantener una navegación de foco accesible.
  function manejarTeclado(evento) {
    if (evento.key === 'Escape') {
      evento.preventDefault()
      onCerrar()
      return
    }
    if (evento.key !== 'Tab' || !panelRef.current) return
    const focos = [...panelRef.current.querySelectorAll('button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')]
    if (!focos.length) return
    const primero = focos[0]
    const ultimo = focos[focos.length - 1]
    if (evento.shiftKey && document.activeElement === primero) {
      evento.preventDefault()
      ultimo.focus()
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault()
      primero.focus()
    }
  }

  return createPortal(
    <div className="ace3-capa" onKeyDown={manejarTeclado}>
      <section
        className="ace3-dialogo"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ace3-titulo"
        aria-describedby="ace3-introduccion"
        ref={panelRef}
      >
        <header className="ace3-cabecera">
          <div>
            <span className="ace3-etiqueta">ANTES DEL PAGO</span>
            <h2 id="ace3-titulo">Cancelaciones y reembolsos</h2>
          </div>
          <button type="button" className="ace3-cerrar" onClick={onCerrar} ref={cerrarRef} aria-label="Cerrar aviso de cancelaciones">✕</button>
        </header>
        <div className="ace3-contenido">
          <div className="ace3-porcentaje" aria-label={`Cargo máximo de cancelación ${porcentajeLegible} por ciento`}>
            <span>Cargo máximo por cancelación injustificada</span>
            <strong>{porcentajeLegible}%</strong>
          </div>
          <p id="ace3-introduccion" className="ace3-texto-breve">
            {politica?.texto || 'No se pudieron cargar las condiciones de cancelación.'}
          </p>
          <label className="ace3-aceptacion">
            <input
              type="checkbox"
              checked={acepto}
              onChange={evento => onCambiarAceptacion(evento.target.checked)}
              disabled={guardando}
            />
            <span>He leído y acepto estas condiciones de cancelación.</span>
          </label>
          {error && <p className="ace3-error" role="alert">{error}</p>}
        </div>
        <footer className="ace3-pie">
          <button type="button" className="ace3-secundario" onClick={onCerrar} disabled={guardando}>
            Revisar más tarde
          </button>
          <button type="button" className="ace3-primario" onClick={onAceptar} disabled={!acepto || guardando || !politica?.version}>
            {guardando ? 'Registrando…' : 'Aceptar y continuar'}
          </button>
        </footer>
      </section>
    </div>,
    document.body,
  )
}
