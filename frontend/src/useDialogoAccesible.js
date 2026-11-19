import { useEffect, useRef } from 'react'

const dialogos = []
let overflowAnterior = ''
const selectorFoco = 'a[href], button, input:not([type="hidden"]), select, textarea, [tabindex], [contenteditable="true"]'

// Localiza controles disponibles para construir el recorrido de teclado del diálogo.
function elementosFoco(panel) {
  return [...panel.querySelectorAll(selectorFoco)].filter(elemento =>
    !elemento.matches(':disabled, [tabindex="-1"]') &&
    !elemento.closest('[hidden], [inert], [aria-hidden="true"]') &&
    elemento.getClientRects().length > 0,
  )
}

// Mueve el foco al primer control útil o al panel si no hay controles.
function enfocarInicio(panel) {
  const destino = panel.querySelector('[data-dialogo-foco-inicial]:not(:disabled)') || elementosFoco(panel)[0] || panel
  destino.focus({ preventScroll: true })
}

// Cada ventana conserva su disparador y solo la superior responde al teclado.
export default function useDialogoAccesible(abierto, panelRef, onCerrar, bloqueado = false) {
  const acciones = useRef({ onCerrar, bloqueado })
  useEffect(() => { acciones.current = { onCerrar, bloqueado } }, [onCerrar, bloqueado])

  useEffect(() => {
    // Registra el diálogo activo y el disparador antes de enfocar el contenido.
    const panel = panelRef.current
    if (!abierto || !panel) return undefined
    const disparador = document.activeElement
    const dialogo = { panel }
    if (!dialogos.length) {
      overflowAnterior = document.body.style.overflow
      document.body.style.overflow = 'hidden'
    }
    dialogos.push(dialogo)
    enfocarInicio(panel)

    // Controla las teclas del diálogo para cerrar o mantener una navegación de foco accesible.
    function manejarTeclado(evento) {
      if (dialogos.at(-1) !== dialogo || evento.defaultPrevented) return
      if (evento.key === 'Escape') {
        if (!acciones.current.bloqueado) {
          evento.preventDefault()
          acciones.current.onCerrar()
        }
        return
      }
      if (evento.key !== 'Tab') return
      const focos = elementosFoco(panel)
      if (!focos.length) {
        evento.preventDefault()
        panel.focus()
        return
      }
      const primero = focos[0], ultimo = focos.at(-1)
      if (!panel.contains(document.activeElement) ||
          (evento.shiftKey && document.activeElement === primero) ||
          (!evento.shiftKey && document.activeElement === ultimo)) {
        evento.preventDefault()
        const destino = evento.shiftKey ? ultimo : primero
        destino.focus()
      }
    }
    document.addEventListener('keydown', manejarTeclado)
    return () => {
      // Retira el diálogo del registro y restituye el foco que corresponda.
      document.removeEventListener('keydown', manejarTeclado)
      const superior = dialogos.at(-1) === dialogo
      dialogos.splice(dialogos.indexOf(dialogo), 1)
      const siguiente = dialogos.at(-1)
      if (!dialogos.length) document.body.style.overflow = overflowAnterior
      if (superior) {
        if (disparador?.isConnected && (!siguiente || siguiente.panel.contains(disparador))) {
          disparador.focus({ preventScroll: true })
        } else if (siguiente && !siguiente.panel.contains(document.activeElement)) {
          enfocarInicio(siguiente.panel)
        }
      }
    }
  }, [abierto, panelRef])
}
