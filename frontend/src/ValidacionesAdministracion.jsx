import AdminNavegacion from './AdminNavegacion.jsx'
import VentanaAdministracion from './VentanaAdministracion.jsx'
import EntrevistasAdministracion from './EntrevistasAdministracion.jsx'
import { useEffect, useState } from 'react'
import './ValidacionesAdministracion.css'

const API = '/api/profesionales/administracion/validaciones/'

const FILTROS = [
  { valor: 'TODAS', texto: 'Todas' },
  { valor: 'PENDIENTE', texto: 'Pendientes' },
  { valor: 'EN_REVISION', texto: 'En revisi\u00f3n' },
  { valor: 'APROBADA', texto: 'Aprobadas' },
  { valor: 'RECHAZADA', texto: 'Rechazadas' },
]

function mensajeError(datos, estado) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail
  return `No se pudo completar la consulta (HTTP ${estado}).`
}

function extraerLista(datos) {
  if (Array.isArray(datos)) return datos

  for (const clave of [
    'solicitudes', 'validaciones', 'resultados', 'results',
  ]) {
    if (Array.isArray(datos?.[clave])) return datos[clave]
  }

  return null
}

function fechaLegible(valor) {
  if (!valor) return 'No informada'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return String(valor)
  return fecha.toLocaleString('es-CL')
}

function texto(valor) {
  if (valor == null || valor === '') return 'No informado'
  if (typeof valor === 'boolean') return valor ? 'S\u00ed' : 'No'
  if (typeof valor === 'object') {
    return Object.entries(valor)
      .filter(([clave, dato]) =>
        !/password|token|secret|hash|csrf/i.test(clave) &&
        dato != null &&
        typeof dato !== 'object'
      )
      .map(([clave, dato]) => `${clave}: ${dato}`)
      .join(' | ') || 'No informado'
  }
  return String(valor)
}

function nombreProfesional(valor) {
  if (!valor || typeof valor !== 'object') return texto(valor)

  const nombre = [
    valor.nombres,
    valor.apellidos,
  ].filter(Boolean).join(' ').trim()

  const correo = valor.correo ?? ''

  if (nombre && correo) return `${nombre} (${correo})`
  return nombre || correo || texto(valor)
}

function EntrevistaResumen({ entrevista }) {
  if (!entrevista || typeof entrevista !== 'object' || Array.isArray(entrevista)) {
    return <span>{texto(entrevista)}</span>
  }

  const campos = [
    ['ID entrevista', entrevista.id_entrevista],
    ['ID validación', entrevista.id_validacion],
    ['ID bloque', entrevista.id_bloque_entrevista],
    ['Estado', entrevista.estado],
    ['Fecha de reserva', entrevista.fecha_reserva],
    ['Fecha', entrevista.fecha],
    ['Hora de inicio', entrevista.hora_inicio],
    ['Hora de término', entrevista.hora_fin],
  ]
  const camposUsados = new Set([
    'id_entrevista', 'id_validacion', 'id_bloque_entrevista',
    'estado', 'fecha_reserva', 'fecha', 'hora_inicio', 'hora_fin',
    'observacion',
  ])
  const restantes = Object.entries(entrevista)
    .filter(([clave, valor]) => !camposUsados.has(clave) && valor != null
      && !/token|secret|password|hash/i.test(clave))
    .map(([clave, valor]) => [clave.replaceAll('_', ' '), valor])
  return (
    <div className="va-entrevista-campos">
      {[...campos, ...restantes].filter(([, valor]) => valor != null && valor !== '')
        .map(([etiqueta, valor]) => (
          <div className="va-entrevista-campo" key={etiqueta}>
            <strong>{etiqueta}</strong>
            <span>{etiqueta.startsWith('Fecha') ? fechaLegible(valor) : texto(valor)}</span>
          </div>
        ))}
    </div>
  )
}

function DocumentosRevision({ documentos, idValidacion, onResolver, procesando, editable }) {
  const [comentarios, setComentarios] = useState({})
  const [descargando, setDescargando] = useState(null)
  const [error, setError] = useState('')

  async function descargar(documento) {
    const id = documento.id_documento

    if (!id || !idValidacion || descargando !== null) return

    setDescargando(id)
    setError('')

    try {
      const ruta =
        `${API}${encodeURIComponent(idValidacion)}/documentos/` +
        `${encodeURIComponent(id)}/descargar/`

      const respuesta = await fetch(ruta, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
      })

      if (!respuesta.ok) {
        if (respuesta.status === 404) {
          throw new Error(
            'No está disponible el archivo físico de este documento. ' +
            'Comprueba la carga original o solicita una nueva versión al profesional.',
          )
        }
        const datos = await respuesta.json().catch(() => ({}))
        throw new Error(mensajeError(datos, respuesta.status))
      }

      const archivo = await respuesta.blob()
      const url = URL.createObjectURL(archivo)
      const enlace = document.createElement('a')

      enlace.href = url
      enlace.download = documento.nombre_archivo || 'documento'
      document.body.appendChild(enlace)
      enlace.click()
      enlace.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1500)
    } catch (fallo) {
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo descargar el documento.',
      )
    } finally {
      setDescargando(null)
    }
  }

  if (!Array.isArray(documentos) || documentos.length === 0) {
    return <p>No hay documentos asociados a esta solicitud.</p>
  }

  return (
    <div className="va-documentos">
      {error && (
        <p className="va-error" role="alert">{error}</p>
      )}

      {documentos.map((item, indice) => {
        const documento = item.documento &&
          typeof item.documento === 'object'
          ? item.documento
          : item

        const id = documento.id_documento ?? item.id_documento

        return (
          <article
            className="va-documento"
            key={id ?? indice}
          >
            <strong>
              {documento.nombre_archivo ??
                documento.tipo_documento ??
                `Documento ${indice + 1}`}
            </strong>

            <p>Tipo: {texto(documento.tipo_documento)}</p>

            <p>
              Estado: {texto(
                item.estado_revision ?? documento.estado,
              )}
            </p>

            {item.estado_revision === 'REEMPLAZADA' && (
              <p>Versión histórica reemplazada. No interviene en la aprobación actual.</p>
            )}
            {item.observacion && (
              <p>Observaci&oacute;n: {item.observacion}</p>
            )}

            {editable && id != null && item.estado_revision !== 'REEMPLAZADA' && (
              <div className="va-revision" style={{ marginTop: 12 }}>
                <label htmlFor={`revision-documento-${id}`}>Observación de este documento</label>
                <textarea
                  id={`revision-documento-${id}`}
                  rows={2}
                  maxLength={4000}
                  style={{ display: 'block', width: '100%', boxSizing: 'border-box' }}
                  placeholder="Obligatoria al rechazar: describe qué debe corregir."
                  value={comentarios[id] || ''}
                  onChange={(evento) => setComentarios((previo) => ({
                    ...previo, [id]: evento.target.value,
                  }))}
                />
                <div className="va-documento-acciones">
                  <button type="button" disabled={procesando || item.estado_revision === 'APROBADA'}
                    onClick={() => onResolver(id, 'APROBADA', comentarios[id] || '')}>
                    Aprobar documento
                  </button>
                  <button type="button" disabled={procesando || item.estado_revision === 'APROBADA' || !(comentarios[id] || '').trim()}
                    onClick={() => onResolver(id, 'RECHAZADA', comentarios[id])}>
                    Rechazar documento
                  </button>
                </div>
              </div>
            )}

            {id != null && (
              <div className="va-documento-acciones">
                <button
                  type="button"
                  disabled={descargando !== null}
                  onClick={() => descargar({
                    ...documento,
                    id_documento: id,
                  })}
                >
                  {descargando === id
                    ? 'Descargando...'
                    : 'Descargar para revisar'}
                </button>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}

export default function ValidacionesAdministracion() {
  const [solicitudes, setSolicitudes] = useState([])
  const [seleccionada, setSeleccionada] = useState(null)
  const [detalle, setDetalle] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [error, setError] = useState('')
  const [errorDetalle, setErrorDetalle] = useState('')
  const [filtro, setFiltro] = useState('TODAS')
  const [procesando, setProcesando] = useState(false)
  const [observacion, setObservacion] = useState('')
  const [mensajeAccion, setMensajeAccion] = useState('')
  const [agendaAbierta, setAgendaAbierta] = useState(false)
  const [procesandoAgenda, setProcesandoAgenda] = useState(false)
  const [observacionEntrevista, setObservacionEntrevista] = useState('')
  const [confirmoEntrevista, setConfirmoEntrevista] = useState(false)
  const [procesandoEntrevista, setProcesandoEntrevista] = useState(false)


  useEffect(() => {
    let vigente = true

    async function cargar() {
      try {
        const sesion = await fetch('/api/acceso/sesion-actual/', {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        })

        const datosSesion = await sesion.json().catch(() => ({}))

        if (
          !sesion.ok ||
          datosSesion.usuario?.rol !== 'ADMIN_SKILLY'
        ) {
          throw new Error(
            'Esta secci\u00f3n requiere una cuenta administrativa.',
          )
        }

        const respuesta = await fetch(API, {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        })

        const datos = await respuesta.json().catch(() => ({}))

        if (!respuesta.ok) {
          throw new Error(mensajeError(datos, respuesta.status))
        }

        const lista = extraerLista(datos)

        if (!lista) {
          throw new Error(
            'La API devolvi\u00f3 un listado inesperado.',
          )
        }

        if (vigente) {
          setSolicitudes(lista)
          setError('')
        }
      } catch (fallo) {
        if (vigente) {
          setError(
            fallo instanceof Error
              ? fallo.message
              : 'No se pudo cargar la bandeja.',
          )
        }
      } finally {
        if (vigente) setCargando(false)
      }
    }

    void cargar()

    return () => {
      vigente = false
    }
  }, [])

  async function ejecutarAccion(id, accion, comentario = '', extra = {}) {
    if (procesando) return

    setProcesando(true)
    setErrorDetalle('')
    setMensajeAccion('')

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
      })

      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))

      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }

      const respuesta = await fetch(
        `${API}${encodeURIComponent(id)}/resolver/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfDatos.csrfToken,
          },
          body: JSON.stringify({
            accion,
            observacion: comentario,
            ...extra,
          }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(mensajeError(datos, respuesta.status))
      }

      if (datos.solicitud) {
        setDetalle(datos.solicitud)
        setSolicitudes((anteriores) =>
          anteriores.map((item) =>
            Number(item.id_validacion ?? item.id) === Number(id)
              ? datos.solicitud
              : item
          ),
        )
      }

      setObservacion('')
      setMensajeAccion(datos.mensaje || 'Operacion completada.')
    } catch (fallo) {
      setErrorDetalle(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo completar la operacion.',
      )
    } finally {
      setProcesando(false)
    }
  }

  async function resolverEntrevista(id, resultado) {
    if (procesandoEntrevista || procesando || !confirmoEntrevista ||
        !observacionEntrevista.trim()) return

    if (!window.confirm(
      `¿Confirma el resultado ${resultado} de la entrevista y su aplicación al perfil profesional?`,
    )) return

    setProcesandoEntrevista(true)
    setErrorDetalle('')
    setMensajeAccion('')

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
      })
      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))
      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }

      const respuesta = await fetch(
        `${API}${encodeURIComponent(id)}/resultado-entrevista/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfDatos.csrfToken,
          },
          body: JSON.stringify({
            resultado,
            observacion: observacionEntrevista.trim(),
            confirmacion_realizada: true,
          }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) {
        throw new Error(mensajeError(datos, respuesta.status))
      }

      if (datos.solicitud) {
        setDetalle(datos.solicitud)
        setSolicitudes((anteriores) => anteriores.map((item) =>
          Number(item.id_validacion ?? item.id) === Number(id)
            ? datos.solicitud
            : item,
        ))
      }
      setMensajeAccion(datos.mensaje || 'Resultado de entrevista registrado.')
      setObservacionEntrevista('')
      setConfirmoEntrevista(false)
    } catch (fallo) {
      setErrorDetalle(fallo instanceof Error
        ? fallo.message
        : 'No se pudo registrar el resultado de la entrevista.')
    } finally {
      setProcesandoEntrevista(false)
    }
  }

  async function abrirAntecedentes(id) {
    if (id == null || cargandoDetalle || procesando) return

    setSeleccionada(id)
    setDetalle(null)
    setErrorDetalle('')
    setMensajeAccion('')
    setObservacion('')
    setCargandoDetalle(true)
    setObservacionEntrevista('')
    setConfirmoEntrevista(false)

    try {
      const respuesta = await fetch(
        `${API}${encodeURIComponent(id)}/`,
        {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(mensajeError(datos, respuesta.status))
      }

      const solicitud = datos.solicitud ?? datos.validacion ?? datos
      setDetalle(solicitud)

      if (String(solicitud.estado).toUpperCase() === 'PENDIENTE') {
        await ejecutarAccion(id, 'INICIAR_REVISION')
      }
    } catch (fallo) {
      setErrorDetalle(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo consultar el detalle.',
      )
    } finally {
      setCargandoDetalle(false)
    }
  }

  function cambiarFiltro(valor) {
    setFiltro(valor)
    setObservacionEntrevista('')
    setConfirmoEntrevista(false)
    setSeleccionada(null)
    setDetalle(null)
    setErrorDetalle('')
    setMensajeAccion('')
    setObservacion('')
  }

  const visibles = solicitudes.filter((solicitud) => {
    const estado = String(solicitud.estado ?? '')
      .trim().toUpperCase()

    return filtro === 'TODAS' || estado === filtro
  })

  return (
    <div className="va-pagina">
      <header className="va-cabecera">
        <a href="/administracion">
          &larr; Volver a administraci&oacute;n
        </a>
       <span>SKILLY / BACK-OFFICE</span>
      </header>

      <AdminNavegacion activo="validaciones" />

      <main className="va-contenido">
        <span className="va-etiqueta">
          GESTI&Oacute;N PROFESIONAL
        </span>

        <h1>Validaci&oacute;n documental de profesionales</h1>

        <p className="va-descripcion">
          Consulta las solicitudes de validaci&oacute;n
          y los documentos presentados por cada profesional.
        </p>

        <section className="va-panel">
          <div className="va-panel-titulo">
            <div>
              <h2>Agenda de entrevistas de validación</h2>
              <p className="va-descripcion">
                Consulta los bloques, las reservas y los cupos disponibles.
                La creación y modificación se gestionan por separado de la revisión documental.
              </p>
            </div>
            <button type="button" onClick={() => setAgendaAbierta(true)}>
              Gestionar entrevistas
            </button>
          </div>
        </section>

        <div className="va-resumen">
          <div>
            <span>Solicitudes recibidas</span>
            <strong>{solicitudes.length}</strong>
          </div>

          <div>
            <span>Pendientes</span>
            <strong>
              {solicitudes.filter(
                (item) => String(item.estado ?? '')
                  .trim().toUpperCase() === 'PENDIENTE',
              ).length}
            </strong>
          </div>
        </div>

        <section className="va-panel">
          <div className="va-panel-titulo">
            <h2>Solicitudes de validaci&oacute;n documental</h2>

            <button
              type="button"
              onClick={() => window.location.reload()}
            >
              ↻ Recargar bandeja
            </button>
          </div>

          <div className="va-filtros">
            {FILTROS.map((opcion) => (
              <button
                key={opcion.valor}
                type="button"
                className={
                  filtro === opcion.valor ? 'activo' : ''
                }
                onClick={() => cambiarFiltro(opcion.valor)}
              >
                {opcion.texto}
              </button>
            ))}
          </div>

          {cargando && (
            <p role="status">Consultando solicitudes...</p>
          )}

          {error && (
            <p className="va-error" role="alert">{error}</p>
          )}

          {!cargando && !error && visibles.length === 0 && (
            <p>No hay solicitudes con este estado.</p>
          )}

          <div className="va-lista">
            {visibles.map((solicitud) => {
              const id =
                solicitud.id_validacion ?? solicitud.id

              return (
                <article className="va-item" key={id}>
                  <div>
                    <h3>Solicitud #{id}</h3>

                    <p>
                      Profesional: {nombreProfesional(
                        solicitud.profesional ??
                        solicitud.correo ??
                        solicitud.id_profesional,
                      )}
                    </p>

                    <p>
                      Estado: <strong>
                        {texto(solicitud.estado)}
                      </strong>
                    </p>

                    <p>
                      Fecha: {fechaLegible(
                        solicitud.fecha_solicitud,
                      )}
                    </p>
                  </div>

                  <button
                    type="button"
                    disabled={cargandoDetalle || procesando}
                    onClick={() => abrirAntecedentes(id)}
                  >
                    Ver antecedentes
                  </button>
                </article>
              )
            })}
          </div>
        </section>

        {agendaAbierta && (
          <VentanaAdministracion
            abierta
            titulo="Agenda de entrevistas profesionales"
            bloqueado={procesandoAgenda}
            onCerrar={() => {
              if (!procesandoAgenda) setAgendaAbierta(false)
            }}
          >
            <EntrevistasAdministracion onProcesandoChange={setProcesandoAgenda} />
          </VentanaAdministracion>
        )}

        {seleccionada !== null && (
          <VentanaAdministracion abierta titulo={`Validación profesional #${seleccionada}`}
            bloqueado={procesando || procesandoEntrevista}
            onCerrar={() => { setSeleccionada(null); setDetalle(null); setErrorDetalle('') }}>
          <section className="va-panel">
            <h2>Detalle de solicitud #{seleccionada}</h2>

            {cargandoDetalle && (
              <p role="status">Cargando antecedentes...</p>
            )}

            {errorDetalle && (
              <p className="va-error" role="alert">
                {errorDetalle}
              </p>
            )}

            {detalle && (
              <>
                <div className="va-detalle">
                  {Object.entries(detalle)
                    .filter(([clave, valor]) =>
                      clave !== 'documentos' &&
                      valor !== null &&
                      !Array.isArray(valor) &&
                      !/token|secret|password|hash/i.test(clave)
                    )
                    .map(([clave, valor]) => (
                      <div key={clave} className={clave === "entrevista" ? "va-detalle-entrevista" : undefined}>
                        <strong>
                          {clave.replaceAll('_', ' ')}
                        </strong>

                        {clave === 'entrevista' ? (
                          <EntrevistaResumen entrevista={valor} />
                        ) : (
                          <span>
                            {clave.startsWith('fecha_')
                              ? fechaLegible(valor)
                              : clave === 'profesional'
                                ? nombreProfesional(valor)
                                : texto(valor)}
                          </span>
                        )}
                      </div>
                    ))}
                </div>

                <h3>Documentaci&oacute;n asociada</h3>

                <DocumentosRevision
                  documentos={detalle.documentos}
                  idValidacion={seleccionada}
                  editable={['EN_REVISION', 'RECHAZADA'].includes(String(detalle.estado).toUpperCase())}
                  procesando={procesando}
                  onResolver={(idDocumento, decision, comentario) =>
                    ejecutarAccion(seleccionada, 'REVISAR_DOCUMENTO', comentario, {
                      id_documento: idDocumento,
                      decision,
                    })}
                />


                {mensajeAccion && (
                  <p role="status">{mensajeAccion}</p>
                )}

                {['EN_REVISION', 'RECHAZADA'].includes(
                  String(detalle.estado).toUpperCase()) && (
                  <div className="va-revision">
                    <h3>Finalizar revisi&oacute;n documental</h3>

                    <p>
                      Revisa cada archivo mediante sus botones individuales.
                      Solo podrás finalizar cuando todos los documentos vigentes estén aprobados.
                    </p>

                    <label
                      htmlFor="va-observacion"
                      style={{ display: 'block', marginBottom: 8 }}
                    >
                      Observaci&oacute;n administrativa
                    </label>

                    <textarea
                      id="va-observacion"
                      value={observacion}
                      onChange={(evento) =>
                        setObservacion(evento.target.value)}
                      maxLength={4000}
                      rows={4}
                      style={{
                        display: 'block',
                        width: '100%',
                        boxSizing: 'border-box',
                        padding: 12,
                        marginBottom: 14,
                      }}
                      placeholder="Indica los requisitos incumplidos si rechazas."
                    />

                    <div
                      style={{
                        display: 'flex',
                        gap: 12,
                        flexWrap: 'wrap',
                      }}
                    >
                      <button
                        type="button"
                        disabled={procesando}
                        onClick={() =>
                          ejecutarAccion(
                            seleccionada,
                            'APROBAR',
                            observacion,
                          )}
                      >
                        Finalizar aprobación documental
                      </button>

                      <button
                        type="button"
                        disabled={
                          procesando || !observacion.trim()
                        }
                        onClick={() =>
                          ejecutarAccion(
                            seleccionada,
                            'RECHAZAR',
                            observacion,
                          )}
                      >
                        Devolver solicitud con observaciones
                      </button>
                    </div>
                  </div>
                )}

                {['APROBADA', 'RECHAZADA'].includes(
                  String(detalle.estado).toUpperCase(),
                ) && (
                  <p className="va-nota">
                    Resoluci&oacute;n registrada:
                    {' '}{detalle.estado}.
                    {detalle.observacion_resultado &&
                      ` ${detalle.observacion_resultado}`}
                  </p>
                )}

                {String(detalle.estado).toUpperCase() === 'APROBADA' && (
                  <div className="va-revision">
                    <h3>Resultado de entrevista y validación final</h3>
                    <p>
                      Estado actual del perfil profesional:{' '}
                      <strong>{texto(detalle.profesional?.estado_validacion)}</strong>
                    </p>

                    {detalle.entrevista ? (
                      <>
                        <p>
                          Entrevista #{detalle.entrevista.id_entrevista}:{' '}
                          <strong>{texto(detalle.entrevista.estado)}</strong>.
                          {' '}Fecha: {detalle.entrevista.fecha}, de{' '}
                          {detalle.entrevista.hora_inicio} a{' '}
                          {detalle.entrevista.hora_fin}.
                        </p>
                        {detalle.entrevista.observacion && (
                          <p>Resultado registrado: {detalle.entrevista.observacion}</p>
                        )}
                      </>
                    ) : (
                      <p>
                        Todavía no existe una entrevista reservada para esta solicitud.
                        El profesional debe reservarla antes de la validación final.
                      </p>
                    )}

                    {String(detalle.profesional?.estado_validacion).toUpperCase() ===
                      'PENDIENTE' &&
                      String(detalle.entrevista?.estado).toUpperCase() ===
                      'AGENDADA' && (
                      <>
                        <p>
                          Registre el resultado únicamente después de realizar la
                          entrevista. No basta con haber reservado el horario.
                        </p>
                        <label htmlFor="va-observacion-entrevista">
                          Observación sobre el resultado de la entrevista
                        </label>
                        <textarea
                          id="va-observacion-entrevista"
                          value={observacionEntrevista}
                          onChange={(evento) =>
                            setObservacionEntrevista(evento.target.value)}
                          rows={4}
                          maxLength={2000}
                          style={{
                            display: 'block',
                            boxSizing: 'border-box',
                            width: '100%',
                            padding: 12,
                            marginTop: 8,
                            marginBottom: 12,
                          }}
                          placeholder="Describa el resultado de la entrevista realizada."
                        />
                        <label style={{ display: 'block', marginBottom: 12 }}>
                          <input
                            type="checkbox"
                            checked={confirmoEntrevista}
                            onChange={(evento) =>
                              setConfirmoEntrevista(evento.target.checked)}
                          />{' '}
                          Confirmo que la entrevista fue realizada.
                        </label>
                        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            disabled={procesando || procesandoEntrevista ||
                              !observacionEntrevista.trim() || !confirmoEntrevista}
                            onClick={() =>
                              resolverEntrevista(seleccionada, 'APROBADO')}
                          >
                            Aprobar perfil profesional
                          </button>
                          <button
                            type="button"
                            disabled={procesando || procesandoEntrevista ||
                              !observacionEntrevista.trim() || !confirmoEntrevista}
                            onClick={() =>
                              resolverEntrevista(seleccionada, 'RECHAZADO')}
                          >
                            Rechazar perfil profesional
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}

                <p className="va-nota">
                  La aprobación de documentos y la validación final
                  del profesional son etapas distintas.
                </p>
              </>
            )}
          </section>
          </VentanaAdministracion>
        )}
      </main>
    </div>
  )
}
