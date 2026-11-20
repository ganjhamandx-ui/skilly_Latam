/**
 * Crea un control que invalida respuestas antiguas aunque el transporte ignore el aborto.
 * @returns {{iniciar: function(): {signal: AbortSignal, vigente: function(): boolean}, cancelar: function(): void}}
 * Control compartido por las consultas de una misma pantalla.
 */
export function crearControlConsultas() {
  let actual = null
  return {
    /**
     * Aborta la consulta anterior y registra una nueva identidad de solicitud.
     * @returns {{signal: AbortSignal, vigente: function(): boolean}} Señal y comprobación de vigencia.
     */
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
    /**
     * Aborta la solicitud activa e invalida las respuestas que lleguen después.
     * @returns {void}
     */
    cancelar() {
      actual?.abort()
      actual = null
    },
  }
}

/**
 * Inicia una consulta y entrega su resultado o error solo mientras siga vigente.
 * Si alCompletar lanza un error, también se entrega a alFallar mientras conserve vigencia.
 * No espera las promesas que pudieran devolver los callbacks.
 *
 * @param {ReturnType<typeof crearControlConsultas>} control Control de la consulta más reciente.
 * @param {function(AbortSignal): Promise<*>} consultar Operación que debe devolver una promesa.
 * @param {function(*): void} alCompletar Aplica el resultado vigente al estado de la pantalla.
 * @param {function(*): void} alFallar Maneja el error vigente.
 * @returns {Promise<void>} Promesa del procesamiento; rechaza si alFallar lanza un error.
 * @throws {*} Si consultar lanza sin devolver una promesa; ese fallo sincrónico se propaga.
 */
export function ejecutarConsulta(control, consultar, alCompletar, alFallar) {
  const solicitud = control.iniciar()
  return consultar(solicitud.signal)
    .then((datos) => { if (solicitud.vigente()) alCompletar(datos) })
    .catch((error) => { if (solicitud.vigente()) alFallar(error) })
}
