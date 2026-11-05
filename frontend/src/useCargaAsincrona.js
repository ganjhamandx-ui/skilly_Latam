import { useCallback, useEffect, useRef } from 'react'
import { crearControlConsultas, ejecutarConsulta } from './cargaAsincrona.mjs'

// La consulta no modifica estado; los resultados se aplican al resolverse.
// El retorno permite que las acciones esperen una recarga antes de continuar.
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
