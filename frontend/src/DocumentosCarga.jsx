import { useCallback, useEffect, useRef, useState } from 'react'
import { accionCargaDocumento } from './documentosCargaPolitica.mjs'
import './DocumentosCarga.css'

function obtenerError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  const mensajes = datos && typeof datos === 'object'
    ? Object.entries(datos)
      .map(([clave, valor]) =>
        `${clave}: ${Array.isArray(valor) ? valor.join(', ') : String(valor)}`,
      ).join(' | ')
    : ''

  return mensajes || `Error HTTP ${codigo}`
}

export default function DocumentosCarga() {
  const [tipo, setTipo] = useState('')
  const [archivo, setArchivo] = useState(null)
  const [idReemplazado, setIdReemplazado] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [consultando, setConsultando] = useState(false)
  const [documentos, setDocumentos] = useState([])
  const [politica, setPolitica] = useState(null)
  const [consultados, setConsultados] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')
  const [avisoNuevaVersion, setAvisoNuevaVersion] = useState('')
  const [ultimaConsulta, setUltimaConsulta] = useState('')
  const campoArchivo = useRef(null)

  const cargarDocumentos = useCallback(async () => {

    setConsultando(true)
    setError('')

    try {
      const respuesta = await fetch(
        '/api/profesionales/mis-documentos/',
        {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerError(datos, respuesta.status))
      }

      if (!Array.isArray(datos.documentos)) {
        throw new Error('El listado tiene un formato inesperado.')
      }

      setDocumentos(datos.documentos)
      setPolitica(datos.politica_carga || null)
      setConsultados(true)
      setUltimaConsulta(new Date().toLocaleTimeString('es-CL'))
    } catch (fallo) {
      setError(
        fallo instanceof Error ? fallo.message : 'Error al consultar documentos.',
      )
    } finally {
      setConsultando(false)
    }
  }, [])

  useEffect(() => {
    let activo = true
    // La consulta comienza tras el montaje del componente.
    Promise.resolve().then(() => {
      if (activo) void cargarDocumentos()
    })
    return () => { activo = false }
  }, [cargarDocumentos])

  async function subirDocumento(evento) {
    evento.preventDefault()

    if (enviando || !archivo) return
    if (!politica || (!politica.nuevos_permitidos &&
        (!idReemplazado || !politica.ids_rechazados?.includes(idReemplazado)))) {
      setError('La carga está bloqueada. Solo puedes corregir un documento rechazado.')
      return
    }

    if (archivo.size <= 0 || archivo.size > 10 * 1024 * 1024) {
      setError('El archivo debe tener un tamaño máximo de 10 MB.')
      return
    }

    if (!tipo.trim() || tipo.trim().length > 60) {
      setError('Indica el tipo de documento.')
      return
    }

    setEnviando(true)
    setError('')
    setExito('')

    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datosCsrf = await respuestaCsrf.json().catch(() => ({}))

      if (!respuestaCsrf.ok || !datosCsrf.csrfToken) {
        throw new Error('No se pudo obtener el token CSRF.')
      }

      const formulario = new FormData()
      formulario.append('archivo', archivo)
      formulario.append('tipo_documento', tipo.trim())
      if (idReemplazado) formulario.append('id_documento_reemplazado', String(idReemplazado))

      const respuesta = await fetch(
        '/api/profesionales/mis-documentos/subir/',
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': datosCsrf.csrfToken,
          },
          body: formulario,
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerError(datos, respuesta.status))
      }

      setExito(
        typeof datos.mensaje === 'string'
          ? datos.mensaje
          : 'Documento cargado correctamente.',
      )

      setArchivo(null)
      setTipo('')
      setIdReemplazado(null)
      setAvisoNuevaVersion('')

      if (campoArchivo.current) campoArchivo.current.value = ''

      await cargarDocumentos()
    } catch (fallo) {
      setError(
        fallo instanceof Error ? fallo.message : 'Error al subir documento.',
      )
    } finally {
      setEnviando(false)
    }
  }

  async function descargarDocumento(documento) {
    setError('')

    try {
      const respuesta = await fetch(
        `/api/profesionales/mis-documentos/${encodeURIComponent(documento.id_documento)}/descargar/`,
        { credentials: 'same-origin', cache: 'no-store' },
      )

      if (!respuesta.ok) {
        if (respuesta.status === 404) {
          throw new Error(
            'El registro existe, pero el archivo original no está disponible para descargar. ' +
            'El registro histórico y su estado de revisión se mantienen disponibles.',
          )
        }
        throw new Error(`No fue posible descargar (HTTP ${respuesta.status}).`)
      }

      const contenido = await respuesta.blob()
      const direccion = URL.createObjectURL(contenido)
      const enlace = document.createElement('a')
      enlace.href = direccion
      enlace.download = documento.nombre_archivo || 'documento'
      document.body.appendChild(enlace)
      enlace.click()
      enlace.remove()
      window.setTimeout(() => URL.revokeObjectURL(direccion), 1500)
    } catch (fallo) {
      setError(
        fallo instanceof Error ? fallo.message : 'Error al descargar.',
      )
    }
  }

  
  function prepararNuevaVersion(documento) {
    const esRechazado = documento.estado_revision === 'RECHAZADA'
    const corregible = esRechazado && politica?.ids_rechazados?.includes(documento.id_documento)
    if (!corregible && !politica?.nuevos_permitidos) {
      setError('Este documento no puede reemplazarse durante la validación inicial.')
      return
    }
    const tipoDocumento = String(documento.tipo_documento || '')
    setTipo(tipoDocumento)
    setIdReemplazado(corregible ? documento.id_documento : null)
    setArchivo(null)
    setError('')
    setExito('')
    setAvisoNuevaVersion(
      corregible
        ? `Corrección del documento rechazado ${documento.nombre_archivo} (#${documento.id_documento}). La versión anterior permanece en el historial.`
        : `Nuevo documento del tipo ${tipoDocumento}. No altera revisiones previas.`,
    )
    if (campoArchivo.current) {
      campoArchivo.current.value = ''
      campoArchivo.current.click()
    }
  }

  const historial = [...documentos].sort((a, b) => {
    const fechaA = Date.parse(a.fecha_carga || '') || 0
    const fechaB = Date.parse(b.fecha_carga || '') || 0
    if (fechaA !== fechaB) return fechaB - fechaA
    return Number(b.id_documento || 0) - Number(a.id_documento || 0)
  })

  const agrupados = Object.groupBy
    ? Object.groupBy(historial, (item) => item.tipo_documento)
    : historial.reduce((resultado, item) => {
        const tipoDocumento = item.tipo_documento
        if (!resultado[tipoDocumento]) resultado[tipoDocumento] = []
        resultado[tipoDocumento].push(item)
        return resultado
      }, {})

return (
    <section className="pp-panel dc-panel">
      <span className="pp-etiqueta">ANTECEDENTES PROFESIONALES</span>
      <p>
        Adjunta tus antecedentes profesionales para la
        revisi&oacute;n de Skilly. Puedes agregar varios documentos.
      </p>

      {politica && !politica.nuevos_permitidos && !idReemplazado && (
        <p className="dc-instruccion" role="status">
          Carga inicial cerrada. Durante la validación no puedes adjuntar nuevos documentos.
          Solo podrás corregir aquellos que SKILLY rechace. Tras aprobar tu entrevista
          y validar definitivamente tu perfil, podrás presentar nuevas capacitaciones.
        </p>
      )}
      {(!politica || politica.nuevos_permitidos || Boolean(idReemplazado)) && (
      <form className="dc-formulario" onSubmit={subirDocumento}>
        {avisoNuevaVersion && (
          <p className="dc-exito" role="status">{avisoNuevaVersion}</p>
        )}
        <p className="dc-instruccion">
          {idReemplazado
            ? 'Estás corrigiendo un documento rechazado. La versión anterior permanecerá en el historial.'
            : 'Adjunta un documento nuevo. Esta acción no reemplaza ni elimina documentos aprobados o anteriores.'}
        </p>
        <div className="dc-campo">
          <label htmlFor="dc-tipo">Tipo de documento *</label>
          <select
            id="dc-tipo"
            required
            value={tipo}
            disabled={enviando || Boolean(idReemplazado)}
            onChange={(evento) => { setTipo(evento.target.value); setIdReemplazado(null) }}
          >
            <option value="">Selecciona el tipo</option>
            <option value="TITULO">T&iacute;tulo profesional</option>
            <option value="CERTIFICADO">Certificado</option>
            <option value="CURRICULUM">Curr&iacute;culum</option>
            <option value="EXPERIENCIA">Acreditaci&oacute;n de experiencia</option>
            <option value="OTRO">Otro antecedente</option>
          </select>
        </div>

        <div className="dc-campo">
          <label htmlFor="dc-archivo">Archivo *</label>
          <input
            id="dc-archivo"
            ref={campoArchivo}
            type="file"
            required
            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,application/pdf,image/jpeg,image/png,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            disabled={enviando}
            onChange={(evento) =>
              setArchivo(evento.target.files?.[0] ?? null)
            }
          />
          <small>PDF, JPG, PNG, DOC o DOCX. M&aacute;ximo 10 MB.</small>
        </div>

        <button
          type="submit"
          className="pp-boton"
          disabled={enviando || !politica || !archivo || !tipo}
        >
          {enviando
            ? 'Subiendo documento...'
            : idReemplazado
              ? 'Enviar corrección del rechazado'
              : 'Adjuntar nuevo documento'}
        </button>
      </form>
      )}

      {error && <p className="pp-error" role="alert">{error}</p>}
      {exito && <p className="dc-exito" role="status">{exito}</p>}

      <div className="dc-listado-cabecera">
        <h3>Documentos registrados</h3>
        <button
          type="button"
          className="pp-boton pp-secundario"
          disabled={consultando}
          onClick={cargarDocumentos}
        >
          {consultando ? 'Consultando...' : '↻ Recargar lista'}
        </button>
      </div>

      {ultimaConsulta && (
        <p className="dc-nota" role="status">Última consulta al servidor: {ultimaConsulta}.</p>
      )}

      {consultados && documentos.length === 0 && (
        <p>Todav&iacute;a no tienes documentos registrados.</p>
      )}

            <div className="dc-listado">
        {Object.entries(agrupados).map(([tipoDocumento, registros]) => (
          <section className="dc-grupo" key={tipoDocumento}>
            <div className="dc-grupo-cabecera">
              <h4>{tipoDocumento}</h4>
              <span>
                {registros.length} {registros.length === 1
                  ? 'documento registrado'
                  : 'documentos registrados'}
              </span>
            </div>

            {registros.map((documento, indice) => {
              const accionCarga = accionCargaDocumento(documento, politica, indice)
              return (
              <article
                className="dc-documento"
                key={documento.id_documento}
              >
                <div>
                  <h4>{documento.nombre_archivo}</h4>
                  <p>
                    {indice === 0
                      ? 'Carga m\u00e1s reciente'
                      : 'Carga anterior conservada'}
                  </p>
                  <p>Estado del archivo: <strong>{documento.estado_revision || documento.estado}</strong></p>
                  {documento.observacion_revision && (
                    <p>Observación de SKILLY: {documento.observacion_revision}</p>
                  )}
                  {documento.fecha_carga && (
                    <p>
                      Fecha: {new Date(
                        documento.fecha_carga,
                      ).toLocaleString('es-CL')}
                    </p>
                  )}
                </div>

                <div className="dc-acciones">
                  {accionCarga && (
                    <button
                      type="button"
                      className="pp-boton pp-secundario"
                      onClick={() => prepararNuevaVersion(documento)}
                    >
                      {accionCarga.etiqueta}
                    </button>
                  )}
                  <button
                    type="button"
                    className="pp-boton pp-secundario"
                    onClick={() => descargarDocumento(documento)}
                  >
                    Descargar
                  </button>
                </div>
              </article>
              )
            })}
          </section>
        ))}
      </div>
<p className="dc-nota">
        La carga de documentos no implica aprobaci&oacute;n
        autom&aacute;tica. Skilly revisar&aacute; los antecedentes.
      </p>
    </section>
  )
}
