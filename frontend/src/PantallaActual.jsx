import { lazy } from 'react'
import { obtenerCargadorPantalla } from './rutasPantalla.mjs'

const Pantalla = lazy(obtenerCargadorPantalla(window.location.pathname))

export default function PantallaActual() {
  return <Pantalla />
}
