// Comparte el import diferido de administración entre las rutas que usan la misma pantalla.
const administracion = () => import('./Administracion.jsx')

const pantallas = {
  // Carga el módulo de catálogo público al navegar a esta ruta.
  '/': () => import('./App.jsx'),
  // Carga el módulo de seguimiento de la organización al navegar a esta ruta.
  '/seguimiento': () => import('./Seguimiento.jsx'),
  // Carga el módulo de calendario profesional al navegar a esta ruta.
  '/disponibilidad': () => import('./Disponibilidad.jsx'),
  // Carga el módulo de portal de acceso al navegar a esta ruta.
  '/acceso-profesional': () => import('./AccesoProfesional.jsx'),
  // Carga el módulo de área profesional al navegar a esta ruta.
  '/portal-profesional': () => import('./PortalProfesional.jsx'),
  '/administracion': administracion,
  // Carga el módulo de validación documental al navegar a esta ruta.
  '/administracion/validaciones': () => import('./ValidacionesAdministracion.jsx'),
  // Carga el módulo de revisión de propuestas al navegar a esta ruta.
  '/administracion/propuestas': () => import('./RevisionPropuestasAdministracion.jsx'),
  // Carga el módulo de indicadores al navegar a esta ruta.
  '/administracion/indicadores': () => import('./IndicadoresAdministracion.jsx'),
  // Carga el módulo de configuración de comisión al navegar a esta ruta.
  '/administracion/comision': () => import('./ComisionAdministracion.jsx'),
  // Carga el módulo de configuración de cancelaciones al navegar a esta ruta.
  '/administracion/cancelaciones': () => import('./CargoCancelacionAdministracionE3.jsx'),
  // Carga el módulo de expedientes de cancelación al navegar a esta ruta.
  '/administracion/expedientes-cancelacion': () => import('./ExpedientesCancelacionAdministracionE3.jsx'),
  // Carga el módulo de cuentas bancarias al navegar a esta ruta.
  '/administracion/cuentas-bancarias': () => import('./CuentasBancariasAdministracion.jsx'),
  // Carga el módulo de trazabilidad al navegar a esta ruta.
  '/administracion/trazabilidad': () => import('./TrazabilidadAdministracion.jsx'),
  // Carga el módulo de reclamos al navegar a esta ruta.
  '/administracion/reclamos': () => import('./ReclamosAdministracion.jsx'),
  // Se conserva el destino de la ruta anterior.
  '/administracion/entregables': administracion,
  // Carga el módulo de retroalimentación al navegar a esta ruta.
  '/administracion/retroalimentacion': () => import('./RetroalimentacionAdministracion.jsx'),
}

// Normaliza el destino y comprueba que exista en el catálogo de pantallas.
export function resolverRutaPantalla(pathname) {
  const ruta = pathname.replace(/\/+$/, '') || '/'
  return Object.hasOwn(pantallas, ruta) ? ruta : '/'
}

// Obtiene el import diferido correspondiente a la ruta reconocida.
export function obtenerCargadorPantalla(pathname) {
  return pantallas[resolverRutaPantalla(pathname)]
}
