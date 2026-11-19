// Aísla errores de carga diferida y presenta una espera común para todas las pantallas.
import { Component, Suspense } from 'react'

const contenedor = {
  maxWidth: '40rem',
  margin: 'clamp(2rem, 8vh, 5rem) auto',
  padding: '1.5rem',
}

// Aísla errores de renderizado durante la carga diferida de una pantalla.
export default class CargaPantalla extends Component {
  state = { fallo: false }

  // Activa la vista de recuperación tras un error de renderizado del módulo.
  static getDerivedStateFromError() {
    return { fallo: true }
  }

  // Presenta la carga, el estado de recuperación o el módulo activo según el estado actual.
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
