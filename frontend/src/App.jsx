import { useEffect, useMemo, useRef, useState } from 'react'
import useDialogoAccesible from './useDialogoAccesible.js'
import './App.css'

const API_SERVICIOS = '/api/marketplace/servicios/'

// Selecciona un detalle visible para informar un fallo de catálogo o solicitud.
function obtenerMensajeError(respuesta) {
  if (respuesta.status === 404) {
    return 'El servicio solicitado no existe o dejó de estar publicado.'
  }

  return `No fue posible consultar Skilly (HTTP ${respuesta.status}).`
}

// Carga los servicios publicados desde el endpoint que consume el Marketplace.
async function consultarServicios(busqueda, signal) {
  const parametros = new URLSearchParams()

  if (busqueda.trim()) {
    parametros.set('q', busqueda.trim())
  }

  const url = parametros.size
    ? `${API_SERVICIOS}?${parametros.toString()}`
    : API_SERVICIOS

  const respuesta = await fetch(url, {
    method: 'GET',
    signal,
    headers: { Accept: 'application/json' },
  })

  if (!respuesta.ok) {
    throw new Error(obtenerMensajeError(respuesta))
  }

  const datos = await respuesta.json()

  if (!datos || !Array.isArray(datos.servicios)) {
    throw new Error('La API no devolvió el catálogo esperado.')
  }

  return datos.servicios
}

// Traduce la modalidad del servicio para el catálogo sin alterar su valor de API.
function obtenerModalidad(valor) {
  if (!valor) return 'Por confirmar'

  const modalidades = {
    REMOTA: 'Remota',
    PRESENCIAL: 'Presencial',
    HIBRIDA: 'Híbrida',
  }

  return modalidades[valor.toUpperCase()] || valor
}

// Presenta el precio del servicio en moneda chilena para la ficha pública.
function formatearPrecio(precio) {
  if (precio === null || precio === undefined || precio === '') {
    return 'Consultar condiciones'
  }

  const texto = String(precio).trim()

  const limpio = texto
    .replace(/^\$\s*/, '')
    .replace(/\s*CLP$/i, '')
    .trim()

  const numeroEntero = /^\d+$/.test(limpio)
  const numeroConPuntos = /^\d{1,3}(?:\.\d{3})+$/.test(limpio)

  if (numeroEntero || numeroConPuntos) {
    const numero = Number(limpio.replace(/\./g, ''))

    if (Number.isSafeInteger(numero) && numero >= 0) {
      const formateado = new Intl.NumberFormat('es-CL', {
        maximumFractionDigits: 0,
      }).format(numero)

      return `$${formateado} CLP`
    }
  }

  return texto
}


// SKILLY_FORMATO_83E
function fechaBloqueChile(fecha) {
  if (typeof fecha !== 'string') return ''
  const partes = fecha.slice(0, 10).split('-')
  if (partes.length !== 3) return fecha
  return `${partes[2]}/${partes[1]}/${partes[0]}`
}

// Presenta la hora civil del bloque sin desplazarla por conversión de zona.
function horaBloqueChile(hora) {
  if (typeof hora !== 'string') return ''
  return hora.slice(0, 5)
}

// Valida el dígito verificador del RUT mediante módulo 11 antes de enviar la solicitud.
function rutChilenoValido(valor) {
  const rut = String(valor || '').toUpperCase().replace(/[.\s-]/g, '')
  if (!/^\d{1,8}[\dK]$/.test(rut)) return false
  const cuerpo = rut.slice(0, -1)
  const digito = rut.slice(-1)
  let suma = 0
  for (let i = 0; i < cuerpo.length; i += 1) {
    suma += Number(cuerpo[cuerpo.length - 1 - i]) * (2 + (i % 6))
  }
  const resto = 11 - (suma % 11)
  const esperado = resto === 11 ? '0' : resto === 10 ? 'K' : String(resto)
  return digito === esperado
}

// Monta el catálogo y gestiona la ficha y la solicitud pública del servicio elegido.
function App() {
  const [busqueda, setBusqueda] = useState('')
  const [categoria, setCategoria] = useState('Todos')
  const [modalidadFiltro, setModalidadFiltro] = useState('Todas')
  const [soloDisponibles, setSoloDisponibles] = useState(false)
  const [catalogo, setCatalogo] = useState([])
  const [resultados, setResultados] = useState([])
  const [cargando, setCargando] = useState(true)
  const [errorCatalogo, setErrorCatalogo] = useState('')
  const [recargar, setRecargar] = useState(0)
  const [servicioActivo, setServicioActivo] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [errorDetalle, setErrorDetalle] = useState('')
  const [menuAbierto, setMenuAbierto] = useState(false)
  const [rolSesionActiva, setRolSesionActiva] = useState(null)
  const portalDeRegreso = rolSesionActiva === 'PROFESIONAL'
    ? '/portal-profesional'
    : rolSesionActiva === 'ADMIN_SKILLY' ? '/administracion' : null

  // SKILLY_SOLICITUDES_80D
  const [mostrarFormulario, setMostrarFormulario] = useState(false)
  const [enviandoSolicitud, setEnviandoSolicitud] = useState(false)
  const solicitudEnCurso = useRef(false)
  const modalPanelRef = useRef(null)
  const servicioDisparadorId = useRef(null)
  const devolverFocoAlCerrar = useRef(false)
  const busquedaRef = useRef(null)
  const [errorSolicitud, setErrorSolicitud] = useState('')
  const [solicitudCreada, setSolicitudCreada] = useState(null)
  const [datosSolicitud, setDatosSolicitud] = useState({
    id_disponibilidad: '',
    nombre_organizacion: '',
    rut: '',
    rubro: '',
    sitio_web: '',
    nombre_contacto: '',
    cargo_contacto: '',
    correo_contacto: '',
    telefono_contacto: '',
    objetivo: '',
    descripcion_necesidad: '',
    urgencia: '',
  })

  // La portada pública no inicia ni cierra sesiones: solo consulta si ya hay
  // una sesión profesional válida para ofrecer el regreso al portal.
  useEffect(() => {
    // Cancela la lectura de sesión al desmontar la pantalla del catálogo.
    const controlador = new AbortController()
    // Consulta la sesión real para decidir qué acciones de acceso mostrar en el catálogo.
    async function comprobarSesionActiva() {
      try {
        const respuesta = await fetch('/api/acceso/sesion-actual/', {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
          signal: controlador.signal,
        })
        if (!respuesta.ok) return
        const datos = await respuesta.json().catch(() => ({}))
        if (!controlador.signal.aborted) {
          setRolSesionActiva(['PROFESIONAL', 'ADMIN_SKILLY'].includes(datos.usuario?.rol) ? datos.usuario.rol : null)
        }
      } catch {
        // La portada continúa pública si no puede consultar la sesión.
      }
    }
    void comprobarSesionActiva()
    return () => controlador.abort()
  }, [])

  // Al entrar desde otra ruta, React todavía no había montado #marketplace
  // cuando el navegador intentó aplicar el fragmento de la URL.
  useEffect(() => {
    if (window.location.hash !== '#marketplace') return undefined
    const id = window.requestAnimationFrame(() => {
      document.getElementById('marketplace')?.scrollIntoView({ behavior: 'auto', block: 'start' })
    })
    return () => window.cancelAnimationFrame(id)
  }, [])

  // Consultar el catálogo completo para construir las categorías reales
  useEffect(() => {
    // Carga los servicios iniciales y cancela la consulta al salir de la pantalla.
    const controlador = new AbortController()

    // Actualiza el listado público y diferencia fallos de red de un catálogo vacío.
    async function cargarCatalogo() {
      try {
        const servicios = await consultarServicios('', controlador.signal)
        if (!controlador.signal.aborted) {
          setCatalogo(servicios)
        }
      } catch (error) {
        if (!controlador.signal.aborted) {
          setErrorCatalogo(error.message)
        }
      }
    }

    cargarCatalogo()

    return () => controlador.abort()
  }, [recargar])

  // Disponibilidad actualizada al regresar al marketplace desde otra pestaña.
  useEffect(() => {
    // Actualiza el frontend al recuperar el foco para reflejar cambios recientes.
    const refrescarAlRegresar = () => {
      if (document.visibilityState === 'visible') {
        setRecargar((anterior) => anterior + 1)
      }
    }
    window.addEventListener('focus', refrescarAlRegresar)
    document.addEventListener('visibilitychange', refrescarAlRegresar)
    return () => {
      window.removeEventListener('focus', refrescarAlRegresar)
      document.removeEventListener('visibilitychange', refrescarAlRegresar)
    }
  }, [])

  // Buscar en Django, no solamente en los elementos visibles de React
  useEffect(() => {
    // Agrupa cambios rápidos de filtros antes de enviar otra consulta.
    const controlador = new AbortController()

    const temporizador = setTimeout(async () => {
      // Consulta los resultados después de la pausa y comunica el fallo si corresponde.
      setCargando(true)
      setErrorCatalogo('')

      try {
        const servicios = await consultarServicios(
          busqueda,
          controlador.signal,
        )

        if (!controlador.signal.aborted) {
          setResultados(servicios)
          setCargando(false)
        }
      } catch (error) {
        if (!controlador.signal.aborted) {
          setErrorCatalogo(error.message)
          setCargando(false)
        }
      }
    }, busqueda ? 300 : 0)

    return () => {
      clearTimeout(temporizador)
      controlador.abort()
    }
  }, [busqueda, recargar])

  const categorias = useMemo(() => {
    // Deduplica categorías por identificador para armar los filtros del catálogo.
    const unicas = new Map()

    catalogo.forEach((servicio) => {
      const item = servicio.categoria

      if (item?.id_categoria != null && item.nombre) {
        unicas.set(item.id_categoria, item)
      }
    })

    return [...unicas.values()].sort((a, b) =>
      a.nombre.localeCompare(b.nombre, 'es'),
    )
  }, [catalogo])

  const serviciosFiltrados = useMemo(() => {
    // Calcula el listado visible a partir de los resultados de la consulta.
    return resultados.filter((servicio) => {
      // Contrasta cada servicio con los criterios de categoría y búsqueda.
      const categoriaCoincide =
        categoria === 'Todos' ||
        String(servicio.categoria?.id_categoria) === categoria

      const modalidadCoincide =
        modalidadFiltro === 'Todas' ||
        (servicio.modalidad || '').toUpperCase() === modalidadFiltro

      const disponibilidadCoincide =
        !soloDisponibles || servicio.tiene_disponibilidad === true

      return (
        categoriaCoincide &&
        modalidadCoincide &&
        disponibilidadCoincide
      )
    })
  }, [resultados, categoria, modalidadFiltro, soloDisponibles])

  // Navega al catálogo y preserva la experiencia de regreso al listado.
  function irAlMarketplace() {
    document.getElementById('marketplace')?.scrollIntoView({
      behavior: 'smooth',
    })
    setMenuAbierto(false)
  }

  // Vuelve a ejecutar la consulta después de un fallo en el listado.
  function reintentar() {
    setErrorCatalogo('')
    setRecargar((anterior) => anterior + 1)
  }

  // Conserva los demás campos mientras se actualiza el valor editado en la solicitud.
  function actualizarSolicitud(evento) {
    const { name, value } = evento.target
    setDatosSolicitud((actual) => ({ ...actual, [name]: value }))
  }

  // Relaciona el formulario con el servicio activo y envía la solicitud a la API.
  async function enviarSolicitud(evento) {
    evento.preventDefault()

    if (!servicioActivo || enviandoSolicitud || solicitudEnCurso.current) return

    const bloques = servicioActivo.disponibilidad || []
    const idBloque = Number(datosSolicitud.id_disponibilidad)

    if (!bloques.some((bloque) => bloque.id_disponibilidad === idBloque)) {
      setErrorSolicitud('Selecciona un horario disponible.')
      return
    }

    if (!rutChilenoValido(datosSolicitud.rut)) {
      setErrorSolicitud('Ingresa un RUT chileno válido, con dígito verificador correcto.')
      return
    }

    setErrorSolicitud('')
    solicitudEnCurso.current = true
    setEnviandoSolicitud(true)

    try {
      const cuerpo = {
        id_servicio: servicioActivo.id_servicio,
        id_disponibilidad: idBloque,
        nombre_organizacion: datosSolicitud.nombre_organizacion.trim(),
        rut: datosSolicitud.rut.trim(),
        nombre_contacto: datosSolicitud.nombre_contacto.trim(),
        correo_contacto: datosSolicitud.correo_contacto.trim(),
        objetivo: datosSolicitud.objetivo.trim(),
        descripcion_necesidad: datosSolicitud.descripcion_necesidad.trim(),
      }

      const opcionales = [
        'rubro',
        'sitio_web',
        'cargo_contacto',
        'telefono_contacto',
        'urgencia',
      ]

      for (const campo of opcionales) {
        const valor = datosSolicitud[campo].trim()
        if (valor) cuerpo[campo] = valor
      }

      const respuesta = await fetch('/api/solicitudes/enviar/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(cuerpo),
      })

      const resultado = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        const detalles = Object.entries(resultado)
          .map(([campo, valor]) =>
            `${campo}: ${Array.isArray(valor) ? valor.join(', ') : String(valor)}`,
          )
          .join(' | ')

        throw new Error(
          detalles || `No se pudo enviar la solicitud (HTTP ${respuesta.status}).`,
        )
      }

      const solicitud = resultado.solicitud || resultado
      const referencia =
        solicitud.referencia_seguimiento ||
        resultado.referencia_seguimiento

      if (!referencia) {
        throw new Error(
          'La API respondió, pero no entregó una referencia de seguimiento. ' +
          'Antes de reenviar, verifica si la solicitud fue registrada.',
        )
      }

      setSolicitudCreada({
        referencia,
        estado: solicitud.estado || 'RECIBIDA',
      })
      setMostrarFormulario(false)
      // El único horario puede haberse ocupado: refrescar catálogo y detalle
      // inmediatamente, sin borrar la referencia entregada a la organización.
      setRecargar((anterior) => anterior + 1)
      try {
        const detalleActualizado = await fetch(
          `${API_SERVICIOS}${servicioActivo.id_servicio}/`,
          { headers: { Accept: 'application/json' }, cache: 'no-store' },
        )
        if (detalleActualizado.ok) {
          setServicioActivo(await detalleActualizado.json())
        }
      } catch {
        // La solicitud ya se creó: una falla al refrescar no la revierte.
      }
    } catch (error) {
      setErrorSolicitud(error.message)
    } finally {
      solicitudEnCurso.current = false
      setEnviandoSolicitud(false)
    }
  }

  // Selecciona un registro y solicita sus datos antes de presentar el diálogo.
  async function abrirDetalle(idServicio) {
    servicioDisparadorId.current = idServicio
    devolverFocoAlCerrar.current = false
    setMostrarFormulario(false)
    setSolicitudCreada(null)
    setErrorSolicitud('')
    setDatosSolicitud({
      id_disponibilidad: '',
      nombre_organizacion: '',
      rut: '',
      rubro: '',
      sitio_web: '',
      nombre_contacto: '',
      cargo_contacto: '',
      correo_contacto: '',
      telefono_contacto: '',
      objetivo: '',
      descripcion_necesidad: '',
        urgencia: '',
    })
    setServicioActivo(null)
    setErrorDetalle('')
    setCargandoDetalle(true)

    try {
      const respuesta = await fetch(`${API_SERVICIOS}${idServicio}/`, {
        headers: { Accept: 'application/json' },
      })

      if (!respuesta.ok) {
        throw new Error(obtenerMensajeError(respuesta))
      }

      const detalle = await respuesta.json()
      setServicioActivo(detalle)
    } catch (error) {
      setErrorDetalle(error.message)
    } finally {
      setCargandoDetalle(false)
    }
  }

  // Descarta la selección del diálogo y evita dejar visible información anterior.
  function cerrarDetalle() {
    if (enviandoSolicitud || solicitudEnCurso.current) return
    devolverFocoAlCerrar.current = true
    setServicioActivo(null)
    setErrorDetalle('')
    setCargandoDetalle(false)
  }

  const modalVisible =
    servicioActivo !== null || cargandoDetalle || Boolean(errorDetalle)
  useDialogoAccesible(modalVisible, modalPanelRef, cerrarDetalle, enviandoSolicitud)
  useEffect(() => {
    // Restaura el foco cuando el diálogo se cierra y el foco no quedó en otro control.
    if (modalVisible || !devolverFocoAlCerrar.current) return
    devolverFocoAlCerrar.current = false
    const foco = document.activeElement
    if (foco?.isConnected && foco !== document.body && foco !== document.documentElement) return
    // Una actualizacion del catalogo puede haber sustituido el disparador
    // mientras el dialogo estaba abierto. Buscar su equivalente, o el filtro
    // estable si la rejilla sigue cargando, sin cambiar el foco valido del usuario.
    const reemplazo = [...document.querySelectorAll('[data-servicio-detalle]')]
      .find(elemento => elemento.dataset.servicioDetalle === String(servicioDisparadorId.current))
    const destino = reemplazo || busquedaRef.current
    destino?.focus({ preventScroll: true })
  }, [modalVisible])

  return (
    <div className="app-shell">
      <div className="barra-superior">
        <span>Una nueva forma de conectar talento y empresas</span>
        <span className="barra-derecha">
          Skilly Latam · Plataforma de servicios profesionales
        </span>
      </div>

      <header className="header">
        <div className="contenedor header-interior">
          <a className="marca" href="#inicio" aria-label="Skilly, ir al inicio">
            <span className="marca-icono">s<span>.</span></span>
            <span className="marca-texto">skilly<span>.</span></span>
          </a>

          <nav className={menuAbierto ? 'navegacion abierta' : 'navegacion'}>
            <a href="#inicio" onClick={() => setMenuAbierto(false)}>
              Inicio
            </a>
            <a href="#marketplace" onClick={() => setMenuAbierto(false)}>
              Explorar servicios
            </a>
            <a href="#como-funciona" onClick={() => setMenuAbierto(false)}>
              Cómo funciona
            </a>
            <a href="#profesionales" onClick={() => setMenuAbierto(false)}>
              Para profesionales
            </a>
            <a href="/seguimiento" onClick={() => setMenuAbierto(false)}>
              Seguimiento
            </a>
          </nav>

          <div className="header-acciones">
            <a className="boton boton-seguimiento-publico" href="/seguimiento">Seguimiento de mi solicitud ↗</a>
            {portalDeRegreso && (
              <a className="boton boton-regreso-portal" href={portalDeRegreso}>
                {rolSesionActiva === 'ADMIN_SKILLY' ? 'Volver a administración' : 'Volver a mi portal'}
              </a>
            )}
            <button
              className="boton boton-oscuro"
              type="button"
              onClick={irAlMarketplace}
            >
              Explorar servicios <span aria-hidden="true">↗</span>
            </button>
          </div>

          <button
            className="boton-menu"
            type="button"
            aria-label={menuAbierto ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={menuAbierto}
            onClick={() => setMenuAbierto((anterior) => !anterior)}
          >
            {menuAbierto ? '✕' : '☰'}
          </button>
        </div>
      </header>

      <main>
        <section className="hero-section" id="inicio">
          <div className="contenedor hero-grid">
            <div className="hero-contenido">
              <div className="eyebrow">
                <span className="punto-vivo" />
                Talento especializado para organizaciones
              </div>

              <h1>
                Las ideas crecen cuando encuentras el{' '}
                <span>talento correcto.</span>
              </h1>

              <p className="hero-descripcion">
                Conectamos empresas con servicios profesionales especializados
                mediante una experiencia cercana, organizada y confiable.
              </p>

              <div className="hero-acciones">
                <button
                  className="boton boton-primario"
                  type="button"
                  onClick={irAlMarketplace}
                >
                  Encontrar un servicio <span aria-hidden="true">↗</span>
                </button>

                <a className="enlace-secundario" href="#como-funciona">
                  Descubre cómo funciona →
                </a>
                <a className="enlace-secundario enlace-acceso-seguimiento" href="/seguimiento">
                  Ya solicitaste un servicio? Consulta su estado →
                </a>
              </div>

              <div className="hero-confianza">
                <span className="confianza-icono">✦</span>
                <span>
                  Servicios profesionales con revisión y acompañamiento de Skilly
                </span>
              </div>
            </div>

            <div className="hero-visual" aria-hidden="true">
              <div className="circulo-decorativo circulo-uno" />
              <div className="circulo-decorativo circulo-dos" />

              <div className="tarjeta-flotante tarjeta-superior">
                <span className="flotante-icono">✳</span>
                <div>
                  <strong>Talento especializado</strong>
                  <small>Soluciones para cada desafío</small>
                </div>
              </div>

              <div className="panel-visual">
                <div className="panel-cabecera">
                  <span className="panel-puntos">● ● ●</span>
                  <span>SKILLY / CONEXIONES</span>
                </div>

                <div className="panel-centro">
                  <div className="nodo nodo-empresa">
                    <span>▦</span>
                    <strong>Empresas</strong>
                    <small>Desafíos reales</small>
                  </div>

                  <div className="conexion-visual">
                    <span>✦</span>
                    <span className="conexion-linea" />
                    <small>Skilly conecta</small>
                  </div>

                  <div className="nodo nodo-talento">
                    <span>✧</span>
                    <strong>Talento</strong>
                    <small>Experiencia especializada</small>
                  </div>
                </div>

                <div className="panel-pie">
                  <span className="estado-dot" />
                  Una conexión que genera valor
                </div>
              </div>

              <div className="tarjeta-flotante tarjeta-inferior">
                <span className="check-circular">✓</span>
                <div>
                  <strong>Procesos más simples</strong>
                  <small>Todo en un mismo lugar</small>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="franja-valores">
          <div className="contenedor valores-grid">
            <div><span>✧</span> Servicios especializados</div>
            <div><span>◈</span> Conexiones con propósito</div>
            <div><span>◎</span> Acompañamiento profesional</div>
            <div><span>↗</span> Experiencias más simples</div>
          </div>
        </section>

        <section className="marketplace-section" id="marketplace">
          <div className="contenedor">
            <div className="encabezado-seccion">
              <div>
                <span className="etiqueta-seccion">
                  EXPLORA LAS POSIBILIDADES
                </span>
                <h2>
                  Servicios para llevar tu empresa más lejos<span>.</span>
                </h2>
                <p>
                  Encuentra soluciones especializadas según las necesidades
                  de tu organización.
                </p>
              </div>

              <span className="sello-catalogo">
                Catálogo conectado a Skilly
              </span>
            </div>

            <div className="barra-busqueda">
              <span className="icono-busqueda" aria-hidden="true">⌕</span>
              <input
                type="search"
                ref={busquedaRef}
                aria-label="Buscar servicios"
                placeholder="Busca servicios por nombre, descripción o competencia..."
                value={busqueda}
                onChange={(evento) => setBusqueda(evento.target.value)}
              />
              <button
                className="boton boton-primario buscar-boton"
                type="button"
                onClick={irAlMarketplace}
              >
                Buscar
              </button>
            </div>

            <div className="filtros" aria-label="Filtrar por categoría">
              <button
                type="button"
                className={categoria === 'Todos' ? 'filtro activo' : 'filtro'}
                aria-pressed={categoria === 'Todos'}
                onClick={() => setCategoria('Todos')}
              >
                Todos
              </button>

              {categorias.map((item) => {
                // Presenta la opción de filtro y su selección para cada categoría.
                const id = String(item.id_categoria)

                return (
                  <button
                    key={id}
                    type="button"
                    className={categoria === id ? 'filtro activo' : 'filtro'}
                    aria-pressed={categoria === id}
                    onClick={() => setCategoria(id)}
                  >
                    {item.nombre}
                  </button>
                )
              })}
            </div>

            <div className="filtros-avanzados">
              <div className="grupo-modalidad">
                <label htmlFor="filtro-modalidad">Modalidad</label>
                <select
                  id="filtro-modalidad"
                  value={modalidadFiltro}
                  onChange={(evento) => setModalidadFiltro(evento.target.value)}
                >
                  <option value="Todas">Todas las modalidades</option>
                  <option value="REMOTA">Remota</option>
                  <option value="PRESENCIAL">Presencial</option>
                  <option value="HIBRIDA">Híbrida</option>
                </select>
              </div>

              <label className="filtro-disponibilidad">
                <input
                  type="checkbox"
                  checked={soloDisponibles}
                  onChange={(evento) => setSoloDisponibles(evento.target.checked)}
                />
                Solo con disponibilidad
              </label>

              <button
                type="button"
                className="limpiar-filtros"
                onClick={() => {
                  setBusqueda('')
                  setCategoria('Todos')
                  setModalidadFiltro('Todas')
                  setSoloDisponibles(false)
                }}
              >
                Limpiar filtros
              </button>
            </div>

            <div className="resultados-cabecera">
              <p aria-live="polite">
                {cargando
                  ? 'Consultando servicios...'
                  : errorCatalogo
                    ? 'No se pudo consultar el catálogo'
                    : (
                      <>
                        <strong>{serviciosFiltrados.length}</strong>{' '}
                        {serviciosFiltrados.length === 1
                          ? 'servicio publicado'
                          : 'servicios publicados'}
                      </>
                    )}
              </p>
            </div>

            {cargando ? (
              <div className="estado-catalogo" role="status">
                <div className="indicador-carga" />
                <h3>Cargando servicios</h3>
                <p>Estamos consultando el catálogo de Skilly.</p>
              </div>
            ) : errorCatalogo ? (
              <div className="estado-catalogo" role="alert">
                <span className="estado-icono">!</span>
                <h3>No pudimos cargar los servicios</h3>
                <p>{errorCatalogo}</p>
                <button
                  className="boton boton-oscuro"
                  type="button"
                  onClick={reintentar}
                >
                  Reintentar conexión
                </button>
              </div>
            ) : serviciosFiltrados.length === 0 ? (
              <div className="sin-resultados">
                <span>⌕</span>
                <h3>No encontramos servicios disponibles</h3>
                <p>
                  Prueba otra búsqueda o categoría. Solo mostramos
                  servicios aprobados y publicados por Skilly.
                </p>
                <button
                  className="boton boton-oscuro"
                  type="button"
                  onClick={() => {
                    setBusqueda('')
                    setCategoria('Todos')
                    setModalidadFiltro('Todas')
                    setSoloDisponibles(false)
                  }}
                >
                  Limpiar filtros
                </button>
              </div>
            ) : (
              <div className="servicios-grid">
                {serviciosFiltrados.map((servicio, indice) => (
                  <article
                    className="servicio-card"
                    key={servicio.id_servicio}
                  >
                    <div className={`servicio-imagen tono-${[
                      'violeta',
                      'verde',
                      'naranja',
                      'rosa',
                      'azul',
                      'amarillo',
                    ][indice % 6]}`}>
                      <span className="imagen-forma forma-a" />
                      <span className="imagen-forma forma-b" />
                      <span className="servicio-ilustracion">✦</span>
                      <span className="servicio-categoria-visual">
                        {servicio.categoria?.nombre || 'Servicio'}
                      </span>
                    </div>

                    <div className="servicio-cuerpo">
                      <div className="servicio-meta">
                        <span>
                          {servicio.categoria?.nombre || 'Sin categoría'}
                        </span>
                        <span>Servicio publicado</span>
                      </div>

                      <h3>{servicio.nombre}</h3>

                      <p className="descripcion-listado">
                        Explora el alcance, las condiciones y los detalles
                        de este servicio profesional.
                      </p>

                      <div className="servicio-disponibilidad">
                        {servicio.tiene_disponibilidad ? (
                          <span className="disponible">
                            ● Con bloques disponibles
                          </span>
                        ) : (
                          <span className="no-disponible">
                            ● Sin bloques disponibles
                          </span>
                        )}
                      </div>

                      <div className="servicio-pie">
                        <span className="modalidad">
                          ◷ {obtenerModalidad(servicio.modalidad)}
                        </span>
                        <button
                          type="button"
                          className="boton-detalle"
                          data-servicio-detalle={servicio.id_servicio}
                          onClick={() => abrirDetalle(servicio.id_servicio)}
                          aria-label={`Ver detalle de ${servicio.nombre}`}
                        >
                          ↗
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}

            <p className="aviso-demo">Los servicios publicados se consultan desde Skilly. Las solicitudes, reservas y pagos siguen las validaciones correspondientes del sistema.</p>
          </div>
        </section>

        <section className="proceso-section" id="como-funciona">
          <div className="contenedor">
            <div className="encabezado-centrado">
              <span className="etiqueta-seccion">ASÍ FUNCIONA SKILLY</span>
              <h2>Del desafío a la solución<span>.</span></h2>
              <p>
                Un recorrido pensado para que las empresas se enfoquen en crecer.
              </p>
            </div>

            <div className="pasos-grid">
              <div className="paso-card">
                <span className="paso-numero">01</span>
                <span className="paso-icono">⌕</span>
                <h3>Explora</h3>
                <p>Encuentra servicios publicados para tu organización.</p>
              </div>

              <div className="paso-card">
                <span className="paso-numero">02</span>
                <span className="paso-icono">▦</span>
                <h3>Selecciona</h3>
                <p>Consulta el alcance, precio y disponibilidad del servicio.</p>
              </div>

              <div className="paso-card">
                <span className="paso-numero">03</span>
                <span className="paso-icono">✦</span>
                <h3>Conecta</h3>
                <p>Continúa con la solicitud y el proceso de coordinación acompañado por Skilly, segun las condiciones de contratación.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="profesionales-section" id="profesionales">
          <div className="contenedor profesionales-panel">
            <div className="profesionales-contenido">
              <span className="etiqueta-clara">
                PARA PROFESIONALES INDEPENDIENTES
              </span>
              <h2>Tu experiencia merece nuevas oportunidades.</h2>
              <p>
                Un espacio para mostrar lo que sabes hacer, proponer
                servicios y conectar con organizaciones que necesitan
                tu talento.
              </p>
              <a className="proximamente" href={rolSesionActiva === 'PROFESIONAL' ? '/portal-profesional' : '/acceso-profesional'}>{rolSesionActiva === 'PROFESIONAL' ? 'Volver a mi portal profesional' : 'Ingresar al portal profesional'}</a>
            </div>

            <div className="profesionales-arte" aria-hidden="true">
              <div className="arte-circulo arte-circulo-1" />
              <div className="arte-circulo arte-circulo-2" />
              <span>✳</span>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="contenedor footer-interior">
          <div>
            <div className="marca marca-footer">
              <span className="marca-icono">s<span>.</span></span>
              <span className="marca-texto">skilly<span>.</span></span>
            </div>
            <p>Talento, conexiones y oportunidades.</p>
          </div>

          <div className="footer-derecha">
            <span>Plataforma Skilly Latam · Desarrollo académico</span>
            <span>Proyecto Integrado · INACAP</span>
          </div>
        </div>
      </footer>

      {modalVisible && (
        <div
          className="modal-fondo"
          onMouseDown={(evento) => {
            if (evento.target === evento.currentTarget) {
              cerrarDetalle()
            }
          }}
        >
          <section
            className="modal-detalle"
            ref={modalPanelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-detalle"
          >
            <button
              className="modal-cerrar"
              type="button"
              data-dialogo-foco-inicial
              disabled={enviandoSolicitud}
              onClick={cerrarDetalle}
              aria-label="Cerrar detalle"
            >
              ✕
            </button>

            {cargandoDetalle ? (
              <div className="estado-catalogo" role="status">
                <div className="indicador-carga" />
                <h2 id="titulo-detalle">Cargando detalle</h2>
                <p>Consultando la información del servicio.</p>
              </div>
            ) : errorDetalle ? (
              <div className="estado-catalogo" role="alert">
                <h2 id="titulo-detalle">No se pudo abrir el servicio</h2>
                <p>{errorDetalle}</p>
                <button
                  type="button"
                  className="boton boton-oscuro"
                  disabled={enviandoSolicitud}
                  onClick={cerrarDetalle}
                >
                  Volver al catálogo
                </button>
              </div>
            ) : servicioActivo && (
              <>
                <div className="modal-encabezado tono-verde">
                  <span className="modal-icono">✦</span>
                  <span>
                    {servicioActivo.categoria?.nombre || 'Servicio'}
                  </span>
                </div>

                <div className="modal-contenido">
                  <span className="etiqueta-seccion">
                    SERVICIO PUBLICADO
                  </span>
                  <h2 id="titulo-detalle">{servicioActivo.nombre}</h2>

                  <p>{servicioActivo.descripcion}</p>

                  <div className="modal-dato">
                    <strong>Modalidad</strong>
                    <span>
                      {obtenerModalidad(servicioActivo.modalidad)}
                    </span>
                  </div>

                  <div className="modal-dato">
                    <strong>Precio publicado</strong>
                    <span>
                      {formatearPrecio(servicioActivo.referencia_precio)}
                    </span>
                  </div>

                  {servicioActivo.alcance && (
                    <div className="detalle-bloque">
                      <h3>Alcance del servicio</h3>
                      <p>{servicioActivo.alcance}</p>
                    </div>
                  )}

                  {servicioActivo.competencias?.length > 0 && (
                    <div className="detalle-bloque">
                      <h3>Competencias</h3>
                      <div className="competencias-grid">
                        {servicioActivo.competencias.map((item) => (
                          <span key={item.id_competencia}>
                            {item.nombre}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {servicioActivo.profesional && (
                    <div className="detalle-bloque">
                      <h3>Perfil profesional</h3>
                      <p>
                        {[
                          servicioActivo.profesional.nombres,
                          servicioActivo.profesional.apellidos,
                        ].filter(Boolean).join(' ')}
                      </p>
                      {servicioActivo.profesional.titulo_profesional && (
                        <p>
                          {servicioActivo.profesional.titulo_profesional}
                        </p>
                      )}
                    </div>
                  )}

                  <div className="detalle-bloque">
                    <h3>Disponibilidad para la primera reunión</h3>

                    {servicioActivo.disponibilidad?.length > 0 ? (
                      <div className="bloques-grid">
                        {servicioActivo.disponibilidad.map((bloque) => (
                          <div
                            className="bloque-disponible"
                            key={bloque.id_disponibilidad}
                          >
                            <strong>{bloque.fecha}</strong>
                            <span>
                              {bloque.hora_inicio} – {bloque.hora_fin}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p>
                        Este servicio no tiene bloques de disponibilidad
                        publicados actualmente.
                      </p>
                    )}
                  </div>

                  {solicitudCreada ? (
                    <div className="solicitud-exito" role="status">
                      <h3>Solicitud recibida por Skilly</h3>
                      <p>
                        Tu solicitud fue registrada. Guarda esta referencia
                        para consultar su seguimiento.
                      </p>
                      <strong className="referencia-solicitud">
                        {solicitudCreada.referencia}
                      </strong>
                      <button
                        type="button"
                        className="boton boton-oscuro"
                        onClick={() => {
                          navigator.clipboard?.writeText(
                            solicitudCreada.referencia,
                          )
                        }}
                      >
                        Copiar referencia
                      </button>
                      <p>
                        Estado: {solicitudCreada.estado}.
                        Aún no se ha realizado el pago ni se ha confirmado
                        la contratación.
                      </p>
                    </div>
                  ) : (
                    <>
                      {(servicioActivo.disponibilidad || []).length === 0 ? (
                        <div className="solicitud-sin-horarios">
                          <strong>No se puede solicitar este servicio todavía</strong>
                          <p>
                            El profesional no tiene horarios disponibles.
                            Cuando publique un bloque válido podrás iniciar
                            la solicitud.
                          </p>
                        </div>
                      ) : !mostrarFormulario ? (
                        <button
                          type="button"
                          className="boton boton-primario modal-boton"
                          onClick={() => setMostrarFormulario(true)}
                        >
                          Solicitar este servicio
                        </button>
                      ) : (
                        <form
                          className="formulario-solicitud"
                          onSubmit={enviarSolicitud}
                        >
                          <h3>Solicitud de servicio</h3>
                          <p>
                            Completa los datos de tu organización.
                            No necesitas crear una cuenta permanente.
                          </p>

                          <label>
                            Horario disponible *
                            <select
                              name="id_disponibilidad"
                              value={datosSolicitud.id_disponibilidad}
                              onChange={actualizarSolicitud}
                              required
                            >
                              <option value="">Selecciona un horario</option>
                              {servicioActivo.disponibilidad.map((bloque) => (
                                <option
                                  key={bloque.id_disponibilidad}
                                  value={bloque.id_disponibilidad}
                                >
                                  {fechaBloqueChile(bloque.fecha)} - {horaBloqueChile(bloque.hora_inicio)} a {horaBloqueChile(bloque.hora_fin)}
                                </option>
                              ))}
                            </select>
                          </label>

                          <div className="formulario-dos-columnas">
                            <label>
                              Organización *
                              <input name="nombre_organizacion"
                                value={datosSolicitud.nombre_organizacion}
                                onChange={actualizarSolicitud}
                                maxLength={180} required />
                            </label>
                            <label>
                              RUT de la organización *
                              <input name="rut" value={datosSolicitud.rut}
                                onChange={actualizarSolicitud}
                                placeholder="Ej.: 12.345.678-5"
                                maxLength={20} required />
                            </label>
                            <label>
                              Rubro (opcional)
                              <input name="rubro" value={datosSolicitud.rubro}
                                onChange={actualizarSolicitud}
                                maxLength={120} />
                            </label>
                            <label>
                              Sitio web (opcional)
                              <input name="sitio_web"
                                value={datosSolicitud.sitio_web}
                                onChange={actualizarSolicitud}
                                maxLength={255} />
                            </label>
                            <label>
                              Nombre de contacto *
                              <input name="nombre_contacto"
                                value={datosSolicitud.nombre_contacto}
                                onChange={actualizarSolicitud}
                                maxLength={150} required />
                            </label>
                            <label>
                              Cargo (opcional)
                              <input name="cargo_contacto"
                                value={datosSolicitud.cargo_contacto}
                                onChange={actualizarSolicitud}
                                maxLength={120} />
                            </label>
                            <label>
                              Correo de contacto *
                              <input type="email" name="correo_contacto"
                                value={datosSolicitud.correo_contacto}
                                onChange={actualizarSolicitud}
                                maxLength={150} required />
                            </label>
                            <label>
                              Teléfono (opcional)
                              <input type="tel" name="telefono_contacto"
                                value={datosSolicitud.telefono_contacto}
                                onChange={actualizarSolicitud}
                                maxLength={30} />
                            </label>
                          </div>

                          <label>
                            Objetivo de la solicitud *
                            <input name="objetivo" value={datosSolicitud.objetivo}
                              onChange={actualizarSolicitud}
                              maxLength={250} required />
                          </label>
                          <label>
                            Describe lo que necesita tu empresa *
                            <textarea name="descripcion_necesidad"
                              value={datosSolicitud.descripcion_necesidad}
                              onChange={actualizarSolicitud}
                              rows={4} required />
                          </label>
                          <div className="formulario-dos-columnas">
                            <div>
                              <strong>Precio publicado de contratación</strong>
                              <p>{formatearPrecio(servicioActivo.referencia_precio)}</p>
                              <small>Precio aprobado por Skilly. No es editable por la organización.</small>
                            </div>
                            <label>
                              Urgencia (opcional)
                              <input name="urgencia"
                                value={datosSolicitud.urgencia}
                                onChange={actualizarSolicitud}
                                maxLength={20} />
                            </label>
                          </div>

                          {errorSolicitud && (
                            <p className="error-solicitud" role="alert">
                              {errorSolicitud}
                            </p>
                          )}

                          <p className="aviso-solicitud">
                            Al enviar, se registrará una solicitud real
                            en Skilly y el bloque quedará reservado
                            pendiente de pago. No se efectuará un cobro
                            ni se confirmará la contratación.
                          </p>

                          <button
                            className="boton boton-primario modal-boton"
                            type="submit"
                            disabled={enviandoSolicitud}
                          >
                            {enviandoSolicitud
                              ? 'Enviando solicitud...'
                              : 'Enviar solicitud a Skilly'}
                          </button>

                          <button
                            className="boton-cancelar-solicitud"
                            type="button"
                            onClick={() => setMostrarFormulario(false)}
                            disabled={enviandoSolicitud}
                          >
                            Cancelar
                          </button>
                        </form>
                      )}
                    </>
                  )}

                  <a href="/seguimiento" className="enlace-seguimiento-publico">Consultar el estado de una solicitud existente</a>
                  <div className="modal-aviso">
                    Skilly permite registrar la solicitud y reservar un
                    horario disponible. El pago, su verificación y la
                    confirmación de la contratación son etapas
                    posteriores del proceso.
                  </div>

                  <button
                    type="button"
                    className="boton boton-primario modal-boton"
                    disabled={enviandoSolicitud}
                    onClick={cerrarDetalle}
                  >
                    Volver al catálogo
                  </button>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  )
}

export default App
