// Enlace de accesibilidad que lleva el foco al contenido principal de la pantalla.
export default function SaltarContenido() {
  // Lleva el foco al contenido principal para evitar repetir toda la navegación.
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
