/**
 * Ofrece un enlace para omitir la navegación y enfocar el primer main del documento.
 * @returns {import('react').ReactElement} Enlace de salto al contenido principal.
 */
export default function SaltarContenido() {
  /**
   * Enfoca main y lo desplaza al inicio; si falta, conserva la navegación normal del enlace.
   * @param {import('react').MouseEvent} evento Activación del enlace de accesibilidad.
   * @returns {void} Añade tabindex=-1 solamente cuando main no tenía tabindex.
   */
  function saltar(evento) {
    const contenido = document.querySelector('main')
    if (!contenido) return
    evento.preventDefault()
    if (!contenido.hasAttribute('tabindex')) contenido.setAttribute('tabindex', '-1')
    contenido.focus({ preventScroll: true })
    contenido.scrollIntoView({ block: 'start' })
  }

  return <a className="sk-salto-contenido" href="#contenido-principal" onClick={saltar}>Saltar al contenido principal</a>
}
