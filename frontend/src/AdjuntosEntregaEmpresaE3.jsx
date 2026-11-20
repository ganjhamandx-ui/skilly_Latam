import './EntregablesPorServicioAdministracionE3.css'
import { useEffect, useState } from 'react'

/**
 * Consulta adjuntos autorizados y muestra los correspondientes a una entrega.
 * Cancela la lectura anterior al cambiar de referencia, entrega o desmontarse.
 * @param {Object} props Identificación del seguimiento privado.
 * @param {string} props.referencia Referencia firmada usada también para descargar.
 * @param {number|string} props.idEntrega Entrega cuyo identificador se compara numéricamente.
 * @returns {import('react').ReactElement|null} Enlaces de descarga, error o nada si no hay datos.
 */
export default function AdjuntosEntregaEmpresaE3({ referencia, idEntrega }) {
  const [archivos, setArchivos] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    // Cancela la lectura de adjuntos al cambiar de entrega o desmontar la pantalla.
    if (!referencia || !idEntrega) return undefined
    const controller = new AbortController()
    /**
     * Carga metadatos y aplica el resultado solo mientras la señal siga activa.
     * @returns {Promise<void>} Los fallos se presentan en el estado local del componente.
     */
    const consultar = async () => {
      try {
        const r = await fetch(`/api/seguimiento/empresa/${encodeURIComponent(referencia)}/entregables/`, {
          method: 'GET', credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
          headers: { Accept: 'application/json' },
        })
        const d = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(d.mensaje || 'No se pudieron consultar los archivos.')
        if (!controller.signal.aborted) {
          setArchivos((d.archivos || []).filter((a) => Number(a.id_entrega) === Number(idEntrega)))
          setError('')
        }
      } catch (e) {
        if (!controller.signal.aborted) setError(e.message || 'Error de archivos.')
      }
    }
    void consultar()
    return () => controller.abort()
  }, [referencia, idEntrega])
  if (!archivos.length && !error) return null
  return <div className="sg-adjuntos-e3">
    {archivos.length > 0 && <><strong>Documentos adjuntos</strong>
      <ul>{archivos.map((a) => <li key={a.id_archivo}>
        <a href={`/api/seguimiento/empresa/${encodeURIComponent(referencia)}/entregables/archivos/${a.id_archivo}/`}>
          Descargar {a.nombre}
        </a>
      </li>)}</ul></>}
    {error && <small role="status">{error}</small>}
  </div>
}
