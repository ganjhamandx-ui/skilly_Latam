// Aísla errores de carga diferida y presenta una espera común para todas las pantallas.
import { Component, Suspense } from 'react'

const contenedor = {
  maxWidth: '40rem',
  margin: 'clamp(2rem, 8vh, 5rem) auto',
  padding: '1.5rem',
}

/**
 * Contiene errores de renderizado de sus hijos y muestra la espera de Suspense.
 * La recuperación ofrecida recarga el documento; no intercepta fallos de handlers asíncronos.
 * @extends {Component<{children: import('react').ReactNode}, {fallo: boolean}>}
 */
export default class CargaPantalla extends Component {
  state = { fallo: false }

  /**
   * Activa la recuperación cuando React notifica un error de un descendiente.
   * @returns {{fallo: boolean}} Estado que sustituye la pantalla por el aviso de error.
   */
  static getDerivedStateFromError() {
    return { fallo: true }
  }

  /**
   * Presenta recuperación o los hijos contenidos por Suspense y su mensaje de espera.
   * @returns {import('react').ReactElement} Contenido correspondiente al estado del límite.
   */
  render() {
    if (this.state.fallo) {
      return (
        <main style={contenedor} role="alert" aria-labelledby="carga-pantalla-error">
          <h1 id="carga-pantalla-error">No se pudo cargar esta página</h1>
          <p>Comprueba tu conexión y vuelve a intentarlo.</p>
          <button type="button" onClick={() => window.location.reload()}>
            Recargar página
          </button>
          <p><a href="/">Volver al inicio</a></p>
        </main>
      )
    }

    return (
      <Suspense fallback={
        <main style={contenedor} role="status" aria-live="polite" aria-busy="true">
          Cargando página…
        </main>
      }>
        {this.props.children}
      </Suspense>
    )
  }
}
