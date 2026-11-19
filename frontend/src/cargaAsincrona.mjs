// Cada carga invalida la anterior, incluso si el servidor no respeta AbortSignal.
export function crearControlConsultas() {
  let actual = null
  return {
    // Cancela la consulta previa y crea una señal para identificar la consulta vigente.
    iniciar() {
      actual?.abort()
      const controlador = new AbortController()
      actual = controlador
      return {
        signal: controlador.signal,
        // Comprueba que la respuesta corresponde a la última consulta iniciada.
        vigente: () => actual === controlador && !controlador.signal.aborted,
      }
    },
    // Aborta la solicitud activa e invalida las respuestas que lleguen después.
    cancelar() {
      actual?.abort()
      actual = null
    },
  }
}

// Entrega el resultado solo si la consulta sigue vigente después de resolver la promesa.
export function ejecutarConsulta(control, consultar, alCompletar, alFallar) {
  const solicitud = control.iniciar()
  return consultar(solicitud.signal)
    .then((datos) => { if (solicitud.vigente()) alCompletar(datos) })
    .catch((error) => { if (solicitud.vigente()) alFallar(error) })
}
