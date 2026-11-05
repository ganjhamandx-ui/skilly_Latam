// Cada carga invalida la anterior, incluso si el servidor no respeta AbortSignal.
export function crearControlConsultas() {
  let actual = null
  return {
    iniciar() {
      actual?.abort()
      const controlador = new AbortController()
      actual = controlador
      return {
        signal: controlador.signal,
        vigente: () => actual === controlador && !controlador.signal.aborted,
      }
    },
    cancelar() {
      actual?.abort()
      actual = null
    },
  }
}

export function ejecutarConsulta(control, consultar, alCompletar, alFallar) {
  const solicitud = control.iniciar()
  return consultar(solicitud.signal)
    .then((datos) => { if (solicitud.vigente()) alCompletar(datos) })
    .catch((error) => { if (solicitud.vigente()) alFallar(error) })
}
