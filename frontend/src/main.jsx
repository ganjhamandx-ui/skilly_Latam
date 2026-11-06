import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import CargaPantalla from './CargaPantalla.jsx'
import PantallaActual from './PantallaActual.jsx'
import SaltarContenido from './SaltarContenido.jsx'

import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SaltarContenido />
    <CargaPantalla>
      <PantallaActual />
    </CargaPantalla>
  </StrictMode>,
)
