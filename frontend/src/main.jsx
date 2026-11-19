// Punto de entrada: monta la ruta solicitada dentro del límite común de carga y errores.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import CargaPantalla from './CargaPantalla.jsx'
import PantallaActual from './PantallaActual.jsx'
import SaltarContenido from './SaltarContenido.jsx'

import './index.css'

// Monta la aplicación y aplica los controles compartidos de carga y accesibilidad.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SaltarContenido />
    <CargaPantalla>
      <PantallaActual />
    </CargaPantalla>
  </StrictMode>,
)
