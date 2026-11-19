// Resuelve la pantalla por ruta y conserva la carga diferida para reducir el paquete inicial.
import { lazy } from 'react'
import { obtenerCargadorPantalla } from './rutasPantalla.mjs'

// Selecciona y carga la vista correspondiente a la ruta actual sin cargar todas las vistas.
const Pantalla = lazy(obtenerCargadorPantalla(window.location.pathname))

// Resuelve el componente diferido correspondiente a la ruta actual.
export default function PantallaActual() {
  return <Pantalla />
}
