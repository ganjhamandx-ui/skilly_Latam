import { useCallback, useEffect, useRef, useState } from 'react'
import AdminNavegacion from './AdminNavegacion.jsx'
import useDialogoAccesible from './useDialogoAccesible.js'
import './RevisionPropuestasAdministracion.css'

const API = '/api/marketplace/administracion'

function obtenerError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const campos = Object.entries(datos).map(([clave, valor]) => {
      const contenido = Array.isArray(valor)
        ? valor.map((item) =>
            typeof item === 'string'
              ? item
              : JSON.stringify(item)
          ).join(', ')
        : typeof valor === 'object'
          ? JSON.stringify(valor)
          : String(valor)

      return `${clave}: ${contenido}`
    })

    if (campos.length) return campos.join(' | ')
  }

  return `No se completó la operación (HTTP ${codigo}).`
}

async function consultar(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, {
    credentials: 'same-origin',
    cache: 'no-store',
    ...opciones,
    headers: {
      Accept: 'application/json',
      ...(opciones.headers || {}),
    },
  })

  const datos = await respuesta.json().catch(() => ({}))

  if (!respuesta.ok) {
    throw new Error(obtenerError(datos, respuesta.status))
  }

  return datos
}

function fecha(valor) {
  if (!valor) return 'Sin fecha'

  const convertido = new Date(valor)

  return Number.isNaN(convertido.getTime())
    ? String(valor)
    : convertido.toLocaleString('es-CL')
}

function formularioDesdeServicio(servicio) {
  return {
    nombre: servicio.nombre ?? '',
    descripcion: servicio.descripcion ?? '',
    id_categoria: String(servicio.categoria?.id_categoria ?? ''),
    modalidad: servicio.modalidad ?? '',
    alcance: servicio.alcance ?? '',
    referencia_precio: servicio.referencia_precio ?? '',
    ids_competencias: (servicio.competencias ?? [])
      .map((competencia) => Number(competencia.id_competencia))
      .filter((id) => Number.isInteger(id) && id > 0),
    observacion: '',
    contenido_revisado: '',
  }
}

export default function RevisionPropuestasAdministracion() {
  const [sesion, setSesion] = useState('cargando')

  const [pendientes, setPendientes] = useState([])
  const [historial, setHistorial] = useState([])
  const [categorias, setCategorias] = useState([])
  const [competencias, setCompetencias] = useState([])

  const [consultando, setConsultando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  const [vista, setVista] = useState('pendientes')
  const [busqueda, setBusqueda] = useState('')

  const [seleccionado, setSeleccionado] = useState(null)
  const [decision, setDecision] = useState('')
  const [formulario, setFormulario] = useState(null)
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    setConsultando(true)
    setError('')

    try {
      const [datos, historico] = await Promise.all([
        consultar(`${API}/servicios/pendientes/`),
        consultar(`${API}/revisiones/`),
      ])

      if (
        !Array.isArray(datos.servicios) ||
        !Array.isArray(historico.revisiones)
      ) {
        throw new Error(
          'La API devolvió una bandeja incompleta.'
        )
      }

      setPendientes(datos.servicios)
      setHistorial(historico.revisiones)

      setCategorias(
        Array.isArray(datos.categorias)
          ? datos.categorias
          : []
      )

      setCompetencias(
        Array.isArray(datos.competencias)
          ? datos.competencias
          : []
      )
    } catch (fallo) {
      setError(
        fallo.message || 'No se pudo cargar la bandeja.'
      )
    } finally {
      setConsultando(false)
    }
  }, [])

  // Verificar que la sesión corresponda a administración.
  useEffect(() => {
    let activo = true

    async function iniciar() {
      try {
        const datos = await consultar(
          '/api/acceso/sesion-actual/'
        )

        if (!activo) return

        if (datos.usuario?.rol !== 'ADMIN_SKILLY') {
          setSesion('sin-permiso')
          return
        }

        setSesion('administrador')
        await cargar()
      } catch {
        if (activo) {
          setSesion('sin-permiso')
        }
      }
    }

    void iniciar()

    return () => {
      activo = false
    }
  }, [cargar])

  const detalleRef = useRef(null)
  useDialogoAccesible(Boolean(seleccionado && formulario), detalleRef, () => setSeleccionado(null), guardando)

  function abrir(servicio) {
    setSeleccionado(servicio)
    setDecision('')
    setFormulario(formularioDesdeServicio(servicio))
    setError('')
    setAviso('')
  }

  function cambiar(campo, valor) {
    setFormulario((anterior) => ({
      ...anterior,
      [campo]: valor,
    }))
  }

  function marcarCompetencia(id, marcado) {
    setFormulario((anterior) => ({
      ...anterior,
      ids_competencias: marcado
        ? [
            ...anterior.ids_competencias.filter(
              (valor) => valor !== id
            ),
            id,
          ]
        : anterior.ids_competencias.filter(
            (valor) => valor !== id
          ),
    }))
  }

  // Registrar una decisión usando la API existente.
  async function guardar(evento) {
    evento.preventDefault()

    if (
      !seleccionado ||
      !formulario ||
      guardando ||
      !decision
    ) {
      return
    }

    setError('')
    setAviso('')

    const observacion = formulario.observacion.trim()
    let cuerpo

    if (decision === 'corregir') {
      if (!observacion) {
        setError(
          'Describe las correcciones que debe realizar el profesional.'
        )
        return
      }

      cuerpo = {
        decision: 'SOLICITAR_CORRECCIONES',
        observacion,
      }
    } else {
      const precio = formulario.referencia_precio
        .trim()
        .toUpperCase()

      if (!/^[1-9]\d{0,9}\s*CLP$/.test(precio)) {
        setError(
          'El precio final debe tener el formato 140000 CLP, sin puntos ni símbolos.'
        )
        return
      }

      if (
        !formulario.nombre.trim() ||
        !formulario.descripcion.trim() ||
        !Number.isInteger(Number(formulario.id_categoria)) ||
        Number(formulario.id_categoria) <= 0
      ) {
        setError(
          'Completa nombre, descripción y categoría de la versión final.'
        )
        return
      }

      if ((seleccionado.reconsideracion_comercial ||
          precio.replace(/\s*CLP$/, ' CLP') !== (seleccionado.referencia_precio || '').trim().toUpperCase().replace(/\s*CLP$/, ' CLP')) &&
          observacion.length < 15) {
        setError('Justifica la modificación comercial en la observación administrativa (mínimo 15 caracteres).')
        return
      }

      cuerpo = {
        decision: 'APROBAR_REVISION',
        observacion,
        contenido_revisado:
          formulario.contenido_revisado.trim(),

        version_propuesta: {
          nombre: formulario.nombre.trim(),
          descripcion: formulario.descripcion.trim(),

          id_categoria: Number(
            formulario.id_categoria
          ),

          ids_competencias:
            formulario.ids_competencias,

          modalidad: formulario.modalidad.trim(),
          alcance: formulario.alcance.trim(),

          referencia_precio: precio.replace(
            /\s*CLP$/,
            ' CLP'
          ),
        },
      }
    }

    const mensaje = decision === 'corregir'
      ? '¿Confirmas devolver la propuesta con correcciones solicitadas?'
      : '¿Confirmas enviar la versión revisada de SKILLY al profesional? No se publicará el servicio.'

    if (!window.confirm(mensaje)) return

    setGuardando(true)

    try {
      const csrf = await consultar(
        '/api/acceso/csrf/'
      )

      if (!csrf.csrfToken) {
        throw new Error(
          'No se pudo obtener el token CSRF.'
        )
      }

      const resultado = await consultar(
        `${API}/servicios/${seleccionado.id_servicio}/revisar/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify(cuerpo),
        }
      )

      setSeleccionado(null)

      setAviso(
        resultado.mensaje ||
        'Revisión registrada correctamente.'
      )

      await cargar()
    } catch (fallo) {
      setError(
        fallo.message ||
        'No se pudo registrar la revisión.'
      )
    } finally {
      setGuardando(false)
    }
  }

  const termino = busqueda
    .trim()
    .toLocaleLowerCase('es-CL')

  const lista = (
    vista === 'pendientes'
      ? pendientes
      : historial
  ).filter((item) => {
    const servicio = vista === 'pendientes'
      ? item
      : item.servicio

    const profesional = item.profesional ?? {}

    const texto = [
      servicio?.id_servicio,
      servicio?.nombre,
      servicio?.descripcion,
      profesional.nombres,
      profesional.apellidos,
      item.estado_revision,
    ]
      .filter((valor) => valor != null)
      .join(' ')
      .toLocaleLowerCase('es-CL')

    return texto.includes(termino)
  })

  if (sesion === 'cargando') {
    return (
      <main className="rp-estado" role="status">
        Verificando sesión administrativa...
      </main>
    )
  }

  if (sesion !== 'administrador') {
    return (
      <main className="rp-estado">
        <h1>Acceso administrativo restringido</h1>

        <p>
          Debes iniciar sesión con una cuenta de
          administración SKILLY.
        </p>

        <a href="/administracion">
          Ir al acceso administrativo
        </a>
      </main>
    )
  }

  return (
    <div className="rp-pagina">
      <header className="rp-cabecera">
        <a href="/administracion">✦ Skilly</a>
        <a href="/administracion">
          Volver a administración
        </a>
      </header>

      <AdminNavegacion activo="propuestas" compacto />

      <main className="rp-contenido">
        <div className="rp-titulo">
          <div>
            <span className="rp-etiqueta">
              GESTIÓN PROFESIONAL
            </span>

            <h1>Revisión de propuestas</h1>

            <p>
              Revisa los servicios enviados a SKILLY
              antes de que puedan publicarse.
            </p>
          </div>

          <button
            className="rp-boton rp-boton--suave"
            type="button"
            onClick={() => void cargar()}
            disabled={consultando}
          >
            {consultando
              ? 'Actualizando...'
              : '↻ Recargar bandeja'}
          </button>
        </div>

        <div className="rp-metricas">
          <article>
            <span>Pendientes de revisión</span>
            <strong>{pendientes.length}</strong>
          </article>

          <article>
            <span>Revisiones registradas</span>
            <strong>{historial.length}</strong>
          </article>
        </div>

        {aviso && (
          <p className="rp-aviso" role="status">
            {aviso}
          </p>
        )}

        {error && !seleccionado && (
          <p className="rp-error" role="alert">
            {error}
          </p>
        )}

        <section className="rp-panel">
          <div className="rp-pestanas">
            <button
              type="button"
              className={
                vista === 'pendientes'
                  ? 'activo'
                  : ''
              }
              onClick={() => setVista('pendientes')}
            >
              Pendientes
            </button>

            <button
              type="button"
              className={
                vista === 'historial'
                  ? 'activo'
                  : ''
              }
              onClick={() => setVista('historial')}
            >
              Historial
            </button>
          </div>

          <label className="rp-busqueda">
            Buscar por servicio, profesional o número

            <input
              type="search"
              value={busqueda}
              onChange={(evento) =>
                setBusqueda(evento.target.value)
              }
              placeholder="Buscar propuestas..."
            />
          </label>

          {consultando && (
            <p role="status">
              Consultando información...
            </p>
          )}

          {!consultando && lista.length === 0 && (
            <p className="rp-vacio">
              {vista === 'pendientes'
                ? 'No hay propuestas pendientes con ese filtro.'
                : 'No hay revisiones registradas con ese filtro.'}
            </p>
          )}

          <div className="rp-lista">
            {lista.map((item) => {
              const servicio = vista === 'pendientes'
                ? item
                : item.servicio

              const nombre = [
                item.profesional?.nombres,
                item.profesional?.apellidos,
              ]
                .filter(Boolean)
                .join(' ') || 'No informado'

              return (
                <article
                  className="rp-tarjeta"
                  key={
                    vista === 'pendientes'
                      ? `s-${item.id_servicio}`
                      : `r-${item.id_revision_servicio}`
                  }
                >
                  <div>
                    <span className="rp-referencia">
                      Servicio #{servicio.id_servicio}
                    </span>

                    <h3>{servicio.nombre}</h3>

                    <p>
                      {nombre} ·{' '}
                      {vista === 'pendientes'
                        ? 'Pendiente de revisión'
                        : item.estado_revision}
                    </p>

                    <small>
                      {vista === 'pendientes'
                        ? fecha(item.fecha_actualizacion)
                        : fecha(item.fecha_revision)}
                    </small>
                  </div>

                  {vista === 'pendientes' ? (
                    <button
                      className="rp-boton"
                      type="button"
                      onClick={() => abrir(item)}
                    >
                      Revisar propuesta
                    </button>
                  ) : (
                    <span className="rp-insignia">
                      Versión {item.numero_version}
                    </span>
                  )}
                </article>
              )
            })}
          </div>
        </section>
      </main>

      {seleccionado && formulario && (
        <div className="rp-fondo">
          <section
            ref={detalleRef}
            className="rp-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="rp-modal-titulo"
            tabIndex={-1}
          >
            <div className="rp-modal-cabecera">
              <div>
                <span className="rp-etiqueta">
                  PROPUESTA #{seleccionado.id_servicio}
                </span>

                <h2 id="rp-modal-titulo">
                  {seleccionado.nombre}
                </h2>
              </div>

              <button
                type="button"
                className="rp-cerrar"
                disabled={guardando}
                aria-label="Cerrar detalle"
                onClick={() => setSeleccionado(null)}
              >
                ×
              </button>
            </div>

            <div className="rp-datos">
              <div>
                <strong>Profesional</strong>
                <span>
                  {[
                    seleccionado.profesional?.nombres,
                    seleccionado.profesional?.apellidos,
                  ].filter(Boolean).join(' ')}
                </span>
              </div>

              <div>
                <strong>Categoría</strong>
                <span>
                  {seleccionado.categoria?.nombre ||
                    'Sin categoría'}
                </span>
              </div>

              <div>
                <strong>Descripción</strong>
                <span>{seleccionado.descripcion}</span>
              </div>

              <div>
                <strong>Alcance</strong>
                <span>
                  {seleccionado.alcance ||
                    'No informado'}
                </span>
              </div>

              <div>
                <strong>Modalidad</strong>
                <span>
                  {seleccionado.modalidad ||
                    'No informada'}
                </span>
              </div>

              <div>
                <strong>Precio referencial</strong>
                <span>
                  {seleccionado.referencia_precio ||
                    'Sin precio propuesto'}
                </span>
              </div>
            </div>

            {seleccionado.reconsideracion_comercial && (
              <section className="rp-nota" style={{ marginTop: 12, padding: 16 }}>
                <h3>Reconsideración única de condiciones</h3>
                <p><strong>Motivo del profesional:</strong> {seleccionado.reconsideracion_comercial.categoria}</p>
                <p>{seleccionado.reconsideracion_comercial.motivo}</p>
                <p>La administración puede enviar una segunda y última versión final. No se admiten nuevas rondas de correcciones.</p>
              </section>
            )}

            <div className="rp-pestanas rp-decisiones">
              {!seleccionado.reconsideracion_comercial && (
              <button
                type="button"
                className={
                  decision === 'corregir'
                    ? 'activo'
                    : ''
                }
                onClick={() => {
                  setDecision('corregir')
                  setError('')
                }}
              >
                Solicitar correcciones
              </button>
              )}

              <button
                type="button"
                className={
                  decision === 'aprobar'
                    ? 'activo'
                    : ''
                }
                onClick={() => {
                  setDecision('aprobar')
                  setError('')
                }}
              >
                Preparar versión final
              </button>
            </div>

            {decision && (
              <form
                className="rp-formulario"
                onSubmit={guardar}
              >
                {decision === 'aprobar' && (
                  <>
                    <p className="rp-nota">
                      SKILLY propone esta versión al
                      profesional. No publica el servicio.
                    </p>

                    <label>
                      Nombre del servicio *
                      <input
                        value={formulario.nombre}
                        maxLength={150}
                        required
                        onChange={(evento) =>
                          cambiar(
                            'nombre',
                            evento.target.value
                          )
                        }
                      />
                    </label>

                    <label>
                      Descripción *
                      <textarea
                        rows={3}
                        required
                        value={formulario.descripcion}
                        onChange={(evento) =>
                          cambiar(
                            'descripcion',
                            evento.target.value
                          )
                        }
                      />
                    </label>

                    <div className="rp-fila">
                      <label>
                        Categoría *
                        <select
                          required
                          value={formulario.id_categoria}
                          onChange={(evento) =>
                            cambiar(
                              'id_categoria',
                              evento.target.value
                            )
                          }
                        >
                          <option value="">
                            Selecciona una categoría
                          </option>

                          {categorias.map((categoria) => (
                            <option
                              key={categoria.id_categoria}
                              value={categoria.id_categoria}
                            >
                              {categoria.nombre}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label>
                        Modalidad
                        <input
                          maxLength={30}
                          value={formulario.modalidad}
                          onChange={(evento) =>
                            cambiar(
                              'modalidad',
                              evento.target.value
                            )
                          }
                        />
                      </label>
                    </div>

                    <label>
                      Alcance
                      <textarea
                        rows={3}
                        value={formulario.alcance}
                        onChange={(evento) =>
                          cambiar(
                            'alcance',
                            evento.target.value
                          )
                        }
                      />
                    </label>

                    <label>
                      Precio final en CLP *
                      <input
                        value={formulario.referencia_precio}
                        required
                        maxLength={120}
                        placeholder="140000 CLP"
                        onChange={(evento) =>
                          cambiar(
                            'referencia_precio',
                            evento.target.value
                          )
                        }
                      />

                      <small>
                        Formato obligatorio: 140000 CLP.
                        No utilices puntos ni el símbolo $.
                      </small>
                    </label>

                    <fieldset className="rp-competencias">
                      <legend>
                        Competencias de la versión final
                      </legend>

                      {competencias.map((competencia) => (
                        <label
                          key={competencia.id_competencia}
                        >
                          <input
                            type="checkbox"
                            checked={
                              formulario.ids_competencias.includes(
                                Number(
                                  competencia.id_competencia
                                )
                              )
                            }
                            onChange={(evento) =>
                              marcarCompetencia(
                                Number(
                                  competencia.id_competencia
                                ),
                                evento.target.checked
                              )
                            }
                          />

                          {competencia.nombre}
                        </label>
                      ))}
                    </fieldset>

                    <label>
                      Resumen de los cambios (opcional)
                      <textarea
                        rows={2}
                        value={
                          formulario.contenido_revisado
                        }
                        onChange={(evento) =>
                          cambiar(
                            'contenido_revisado',
                            evento.target.value
                          )
                        }
                      />
                    </label>
                  </>
                )}

                <label>
                  {decision === 'corregir'
                    ? 'Correcciones solicitadas *'
                    : 'Observación administrativa (opcional)'}

                  <textarea
                    rows={3}
                    required={decision === 'corregir'}
                    value={formulario.observacion}
                    placeholder={
                      decision === 'corregir'
                        ? 'Indica qué debe corregir el profesional.'
                        : 'Comentario para el profesional.'
                    }
                    onChange={(evento) =>
                      cambiar(
                        'observacion',
                        evento.target.value
                      )
                    }
                  />
                </label>

                {error && (
                  <p className="rp-error" role="alert">
                    {error}
                  </p>
                )}

                <div className="rp-acciones">
                  <button
                    type="button"
                    className="rp-boton rp-boton--suave"
                    disabled={guardando}
                    onClick={() =>
                      setSeleccionado(null)
                    }
                  >
                    Cancelar
                  </button>

                  <button
                    type="submit"
                    className="rp-boton"
                    disabled={guardando}
                  >
                    {guardando
                      ? 'Registrando...'
                      : decision === 'corregir'
                        ? 'Enviar correcciones'
                        : 'Enviar versión al profesional'}
                  </button>
                </div>
              </form>
            )}

            {!decision && (
              <p className="rp-nota">
                {seleccionado.reconsideracion_comercial
                  ? 'Prepara la segunda versión final; será la última oportunidad de aceptación.'
                  : 'Selecciona una de las dos decisiones para continuar.'}
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
