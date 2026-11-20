import { useEffect, useRef } from 'react'

const dialogos = []
let overflowAnterior = ''
const selectorFoco = 'a[href], button, input:not([type="hidden"]), select, textarea, [tabindex], [contenteditable="true"]'

/**
 * Localiza controles visibles y habilitados para el recorrido de teclado.
 * @param {HTMLElement} panel Contenedor del diálogo montado.
 * @returns {HTMLElement[]} Controles en orden DOM, excluidos ocultos, inertes y tabindex -1.
 */
function elementosFoco(panel) {
  return [...panel.querySelectorAll(selectorFoco)].filter(elemento =>
    !elemento.matches(':disabled, [tabindex="-1"]') &&
    !elemento.closest('[hidden], [inert], [aria-hidden="true"]') &&
    elemento.getClientRects().length > 0,
  )
}

/**
 * Enfoca el destino inicial explícito, el primer control disponible o el panel.
 * @param {HTMLElement} panel Contenedor que debe admitir foco si no tiene controles.
 * @returns {void}
 */
function enfocarInicio(panel) {
  const destino = panel.querySelector('[data-dialogo-foco-inicial]:not(:disabled)') || elementosFoco(panel)[0] || panel
  destino.focus({ preventScroll: true })
}

/**
 * Mantiene el foco y la navegación de teclado de diálogos apilados.
 * Solo el superior procesa Escape y Tab. Mientras haya diálogos bloquea el scroll
 * del body; al cerrar restaura el foco al disparador conectado o al diálogo anterior.
 * No añade atributos ARIA ni oculta el contenido de fondo: los define el componente.
 *
 * @param {boolean} abierto Si el diálogo debe registrarse como activo.
 * @param {{current: HTMLElement|null}} panelRef Referencia estable al panel montado.
 * @param {function(): void} onCerrar Solicitud de cierre por Escape.
 * @param {boolean} [bloqueado=false] Impide cierre por Escape durante una operación.
 * @returns {void}
 */
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

    /**
     * Procesa Escape o recircula Tab únicamente en el diálogo superior.
     * @param {KeyboardEvent} evento Evento del documento; respeta defaultPrevented.
     * @returns {void}
     */
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
