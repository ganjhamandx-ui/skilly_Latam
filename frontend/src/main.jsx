import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import CargaPantalla from './CargaPantalla.jsx'
import PantallaActual from './PantallaActual.jsx'

import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <CargaPantalla>
      <PantallaActual />
    </CargaPantalla>
  </StrictMode>,
)
