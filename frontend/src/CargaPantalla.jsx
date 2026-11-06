import { Component, Suspense } from 'react'

const contenedor = {
  maxWidth: '40rem',
  margin: 'clamp(2rem, 8vh, 5rem) auto',
  padding: '1.5rem',
}

export default class CargaPantalla extends Component {
  state = { fallo: false }

  static getDerivedStateFromError() {
    return { fallo: true }
  }

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
