import { useCallback, useEffect, useRef } from 'react'
import { crearControlConsultas, ejecutarConsulta } from './cargaAsincrona.mjs'

/**
 * Ejecuta y cancela consultas de una pantalla, descartando respuestas obsoletas.
 * Repite la consulta cuando cambia la identidad de cualquiera de los callbacks;
 * el llamador debe estabilizarlos cuando no desea nuevas cargas en cada renderizado.
 * consultar debe obtener datos y dejar las actualizaciones de estado a los callbacks.
 *
 * @param {function(AbortSignal): Promise<*>} consultar Consulta que acepta una señal de cancelación.
 * @param {function(*): void} alCompletar Aplica el resultado de la consulta vigente.
 * @param {function(*): void} alFallar Comunica el error de la consulta vigente.
 * @returns {function(): Promise<void>} Recarga manual que puede esperarse antes de continuar.
 */
export default function useCargaAsincrona(consultar, alCompletar, alFallar) {
  const control = useRef(crearControlConsultas())
  useEffect(() => {
    void ejecutarConsulta(control.current, consultar, alCompletar, alFallar)
    const consultas = control.current
    return () => consultas.cancelar()
  }, [consultar, alCompletar, alFallar])
  return useCallback(
    () => ejecutarConsulta(control.current, consultar, alCompletar, alFallar),
    [consultar, alCompletar, alFallar],
  )
}
