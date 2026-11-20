// Comparte el import diferido de administración entre las rutas que usan la misma pantalla.
const administracion = () => import('./Administracion.jsx')

const pantallas = {
  '/': () => import('./App.jsx'),
  '/seguimiento': () => import('./Seguimiento.jsx'),
  '/disponibilidad': () => import('./Disponibilidad.jsx'),
  '/acceso-profesional': () => import('./AccesoProfesional.jsx'),
  '/portal-profesional': () => import('./PortalProfesional.jsx'),
  '/administracion': administracion,
  '/administracion/validaciones': () => import('./ValidacionesAdministracion.jsx'),
  '/administracion/propuestas': () => import('./RevisionPropuestasAdministracion.jsx'),
  '/administracion/indicadores': () => import('./IndicadoresAdministracion.jsx'),
  '/administracion/comision': () => import('./ComisionAdministracion.jsx'),
  '/administracion/cancelaciones': () => import('./CargoCancelacionAdministracionE3.jsx'),
  '/administracion/expedientes-cancelacion': () => import('./ExpedientesCancelacionAdministracionE3.jsx'),
  '/administracion/cuentas-bancarias': () => import('./CuentasBancariasAdministracion.jsx'),
  '/administracion/trazabilidad': () => import('./TrazabilidadAdministracion.jsx'),
  '/administracion/reclamos': () => import('./ReclamosAdministracion.jsx'),
  // Se conserva el destino de la ruta anterior.
  '/administracion/entregables': administracion,
  '/administracion/retroalimentacion': () => import('./RetroalimentacionAdministracion.jsx'),
}

/**
 * Resuelve una ruta conocida después de quitar sus barras finales.
 * @param {string} pathname Ruta de location.pathname, sin consulta ni fragmento.
 * @returns {string} Ruta reconocida, o / cuando queda vacía o no está registrada.
 */
export function resolverRutaPantalla(pathname) {
  const ruta = pathname.replace(/\/+$/, '') || '/'
  return Object.hasOwn(pantallas, ruta) ? ruta : '/'
}

/**
 * Obtiene el cargador de una pantalla sin ejecutar todavía su importación.
 * @param {string} pathname Ruta que resolverá resolverRutaPantalla.
 * @returns {function(): Promise<Object>} Importación diferida del módulo con componente por defecto.
 */
export function obtenerCargadorPantalla(pathname) {
  return pantallas[resolverRutaPantalla(pathname)]
}
