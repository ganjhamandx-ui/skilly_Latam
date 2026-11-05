
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import './index.css'

import App from './App.jsx'
import Seguimiento from './Seguimiento.jsx'
import Disponibilidad from './Disponibilidad.jsx'
import AccesoProfesional from './AccesoProfesional.jsx'
import PortalProfesional from './PortalProfesional.jsx'

import Administracion from './Administracion.jsx'
import ValidacionesAdministracion from './ValidacionesAdministracion.jsx'
import RevisionPropuestasAdministracion from './RevisionPropuestasAdministracion.jsx'
import IndicadoresAdministracion from './IndicadoresAdministracion.jsx'
import ComisionAdministracion from './ComisionAdministracion.jsx'
import CargoCancelacionAdministracionE3 from './CargoCancelacionAdministracionE3.jsx'
import ExpedientesCancelacionAdministracionE3 from './ExpedientesCancelacionAdministracionE3.jsx'
import CuentasBancariasAdministracion from './CuentasBancariasAdministracion.jsx'
import TrazabilidadAdministracion from './TrazabilidadAdministracion.jsx'
import ReclamosAdministracion from './ReclamosAdministracion.jsx'
import RetroalimentacionAdministracion from './RetroalimentacionAdministracion.jsx'

const ruta = window.location.pathname.replace(/\/+$/, '') || '/'

let pantalla

switch (ruta) {
  case '/seguimiento':
    pantalla = <Seguimiento />
    break

  case '/disponibilidad':
    pantalla = <Disponibilidad />
    break

  case '/acceso-profesional':
    pantalla = <AccesoProfesional />
    break

  case '/portal-profesional':
    pantalla = <PortalProfesional />
    break

  case '/administracion':
    pantalla = <Administracion />
    break

  case '/administracion/validaciones':
    pantalla = <ValidacionesAdministracion />
    break

  case '/administracion/propuestas':
    pantalla = <RevisionPropuestasAdministracion />
    break

  case '/administracion/indicadores':
    pantalla = <IndicadoresAdministracion />
    break

  case '/administracion/comision':
    pantalla = <ComisionAdministracion />
    break

  case '/administracion/cancelaciones':
    pantalla = <CargoCancelacionAdministracionE3 />
    break

  case '/administracion/expedientes-cancelacion':
    pantalla = <ExpedientesCancelacionAdministracionE3 />
    break

  case '/administracion/cuentas-bancarias':
    pantalla = <CuentasBancariasAdministracion />
    break

  case '/administracion/trazabilidad':
    pantalla = <TrazabilidadAdministracion />
    break

  case '/administracion/reclamos':
    pantalla = <ReclamosAdministracion />
    break

  case '/administracion/entregables':
    // Ruta anterior: ya no requiere gestion de formatos por administracion.
    pantalla = <Administracion />
    break

  case '/administracion/retroalimentacion':
    pantalla = <RetroalimentacionAdministracion />
    break

  default:
    pantalla = <App />
    break
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {pantalla}
  </StrictMode>,
)
