// Resuelve la pantalla por ruta y conserva la carga diferida para reducir el paquete inicial.
import { lazy } from 'react'
import { obtenerCargadorPantalla } from './rutasPantalla.mjs'

// La selección se fija al evaluar el módulo; los enlaces de navegación cargan un nuevo documento.
const Pantalla = lazy(obtenerCargadorPantalla(window.location.pathname))

/**
 * Renderiza la pantalla diferida seleccionada a partir del pathname al cargar este módulo.
 * @returns {import('react').ReactElement} Pantalla que debe estar contenida por Suspense.
 */
export default function PantallaActual() {
  return <Pantalla />
}
