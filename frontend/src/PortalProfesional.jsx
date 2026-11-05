import SolicitarValidacionProfesional from './SolicitarValidacionProfesional'
import { ReagendamientosProfesional } from './ReagendamientosSkilly.jsx'
import DocumentosCarga from './DocumentosCarga'
import CompletarPerfilProfesional from './CompletarPerfilProfesional'
import RegistrarAvanceProfesional from './RegistrarAvanceProfesional'
import RecomendacionesProfesional from './RecomendacionesProfesional'
import OportunidadesProfesional from './OportunidadesProfesional'
import ResumenPagosProfesional from './ResumenPagosProfesional'
import CuentaCobroProfesional from './CuentaCobroProfesional'
import DetalleSeguimientoProfesional from './DetalleSeguimientoProfesional'
import ResumenEntrevista from './ResumenEntrevista'
import DatosValidacion from './DatosValidacion'
import DetalleRevision from './DetalleRevision'
import EditarPropuesta from './EditarPropuesta'
import NuevaPropuesta from './NuevaPropuesta'
import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import './PortalProfesional.css'
import './EntregablesPorServicioAdministracionE3.css'


// Todas las consultas se presentan en una ventana centrada.
// Las acciones y los formularios siguen usando sus componentes originales.
function VentanaProfesional({ abierta, titulo, onCerrar, children }) {
  useEffect(() => {
    if (!abierta) return undefined
    const overflowAnterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const cerrarConEscape = (evento) => {
      if (evento.key === 'Escape') onCerrar()
    }
    document.addEventListener('keydown', cerrarConEscape)
    return () => {
      document.body.style.overflow = overflowAnterior
      document.removeEventListener('keydown', cerrarConEscape)
    }
  }, [abierta, onCerrar])

  if (!abierta) return null

  return createPortal(
    <div className="pp-modal-fondo pp-modal-accion"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) onCerrar()
      }}>
      <div className="pp-modal-accion-contenido" role="dialog"
        aria-modal="true" aria-label={titulo}>
        <div className="pp-modal-accion-cabecera">
          <div>
            <span className="pp-etiqueta">ESPACIO PROFESIONAL</span>
            <h2>{titulo}</h2>
          </div>
          <button type="button" className="pp-modal-cerrar"
            aria-label={`Cerrar ${titulo}`} onClick={onCerrar} autoFocus>
            &times;
          </button>
        </div>
        <div className="pp-modal-accion-cuerpo">{children}</div>
      </div>
    </div>,
    document.body,
  )
}

function formatearFechaChile(valor, conHora = false) {
  if (!valor) return 'No informada'
  const texto = String(valor)
  if (/^\d{4}-\d{2}-\d{2}$/.test(texto)) {
    const [anio, mes, dia] = texto.split('-')
    return `${dia}/${mes}/${anio}`
  }
  const fecha = new Date(texto)
  if (Number.isNaN(fecha.getTime())) return texto
  return new Intl.DateTimeFormat('es-CL', {
    timeZone: 'America/Santiago',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    ...(conHora ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}),
  }).format(fecha)
}

function PortalProfesional() {
  const [estado, setEstado] = useState('cargando')
  const [moduloPortal, setModuloPortal] = useState('servicios')
  const [ventanaPortal, setVentanaPortal] = useState(null)
  const [ultimaConsulta, setUltimaConsulta] = useState({})

  function registrarConsulta(seccion) {
    setUltimaConsulta((actual) => ({
      ...actual,
      [seccion]: new Date().toLocaleTimeString('es-CL'),
    }))
  }
  const [detalleServicio, setDetalleServicio] = useState(null)
  const [cargandoDetalleServicio, setCargandoDetalleServicio] = useState(false)
  const [errorDetalleServicio, setErrorDetalleServicio] = useState('')

  const [idServicioDetalle, setIdServicioDetalle] = useState(null)
  const [versionRevisada, setVersionRevisada] = useState(null)
  const [cargandoVersion, setCargandoVersion] = useState(false)
  const [accionServicio, setAccionServicio] = useState('')
  const [errorAccionServicio, setErrorAccionServicio] = useState('')
  const [avisoAccionServicio, setAvisoAccionServicio] = useState('')
  const [motivoCategoriaComercial, setMotivoCategoriaComercial] = useState('')
  const [motivoDetalleComercial, setMotivoDetalleComercial] = useState('')
  const [usuario, setUsuario] = useState(null)

  const [pagosProfesional, setPagosProfesional] = useState([])
  const [cargandoPagos, setCargandoPagos] = useState(false)
  const [errorPagos, setErrorPagos] = useState('')
  const [pagosConsultados, setPagosConsultados] = useState(false)

  const [descripcionNuevaEntrega, setDescripcionNuevaEntrega] = useState('')
  const [referenciaNuevaEntrega, setReferenciaNuevaEntrega] = useState('')
  const [archivosNuevaEntrega, setArchivosNuevaEntrega] = useState([])
  const [habilitaArchivoEntrega, setHabilitaArchivoEntrega] = useState(false)
  const [formatosEntrega, setFormatosEntrega] = useState([])
  const [orientacionEntrega, setOrientacionEntrega] = useState('')
  const [archivosEntregaE3, setArchivosEntregaE3] = useState([])
  const [errorAdjuntosE3, setErrorAdjuntosE3] = useState('')
  const [registrandoEntrega, setRegistrandoEntrega] = useState(false)
  const [errorNuevaEntrega, setErrorNuevaEntrega] = useState('')
  const [exitoNuevaEntrega, setExitoNuevaEntrega] = useState('')


  const [entregasProfesional, setEntregasProfesional] = useState([])
  const [observacionesEntregas, setObservacionesEntregas] = useState([])
  const [entregasSeleccionadas, setEntregasSeleccionadas] = useState(null)
  const [cargandoEntregas, setCargandoEntregas] = useState(false)
  const [errorEntregas, setErrorEntregas] = useState('')


  const [seguimientoProfesional, setSeguimientoProfesional] = useState(null)
  const [seguimientoSeleccionado, setSeguimientoSeleccionado] = useState(null)
  const [cargandoSeguimiento, setCargandoSeguimiento] = useState(false)
  const [errorSeguimiento, setErrorSeguimiento] = useState('')


  const [coordinados, setCoordinados] = useState([])
  const [cargandoCoordinados, setCargandoCoordinados] = useState(false)
  const [errorCoordinados, setErrorCoordinados] = useState('')
  const [coordinadosConsultados, setCoordinadosConsultados] = useState(false)


  const [bloquesEntrevista, setBloquesEntrevista] = useState([])
  const [cargandoBloques, setCargandoBloques] = useState(false)
  const [reservandoEntrevista, setReservandoEntrevista] = useState(false)
  const [bloqueSeleccionado, setBloqueSeleccionado] = useState('')
  const [errorReserva, setErrorReserva] = useState('')
  const [avisoReserva, setAvisoReserva] = useState('')
  const [bloquesConsultados, setBloquesConsultados] = useState(false)

  const [entrevista, setEntrevista] = useState(null)
  const [cargandoEntrevista, setCargandoEntrevista] = useState(false)
  const [errorEntrevista, setErrorEntrevista] = useState('')
  const [entrevistaConsultada, setEntrevistaConsultada] = useState(false)
  const [cancelandoEntrevista, setCancelandoEntrevista] = useState(false)
  const [motivoCancelacion, setMotivoCancelacion] = useState('')
  const [avisoEntrevista, setAvisoEntrevista] = useState('')
  const [documentos, setDocumentos] = useState(null)
  const [validacion, setValidacion] = useState(null)
  const [cargandoValidacion, setCargandoValidacion] = useState(false)
  const [errorValidacion, setErrorValidacion] = useState('')
  const [perfil, setPerfil] = useState(null)
  const [cargandoPerfil, setCargandoPerfil] = useState(false)
  const [errorPerfil, setErrorPerfil] = useState('')
  const [servicios, setServicios] = useState([])
  const [cargandoServicios, setCargandoServicios] = useState(false)
  const [errorServicios, setErrorServicios] = useState('')
  const [cerrando, setCerrando] = useState(false)
  const [errorSesion, setErrorSesion] = useState('')

  // SKILLY_MODAL_SERVICIOS_V1
  function cerrarDetalleServicio() {
    if (cargandoDetalleServicio || accionServicio || cargandoVersion) return
    setDetalleServicio(null)
    setVentanaPortal('mis-servicios')
    setErrorDetalleServicio('')
    setIdServicioDetalle(null)
    setVersionRevisada(null)
  }

  useEffect(() => {
    if (!detalleServicio && !errorDetalleServicio && !cargandoDetalleServicio) return
    const anterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const conEscape = (evento) => {
      if (evento.key !== 'Escape' || cargandoDetalleServicio || accionServicio || cargandoVersion) return
      setDetalleServicio(null)
      setVentanaPortal('mis-servicios')
      setErrorDetalleServicio('')
      setIdServicioDetalle(null)
      setVersionRevisada(null)
    }
    document.addEventListener('keydown', conEscape)
    return () => {
      document.body.style.overflow = anterior
      document.removeEventListener('keydown', conEscape)
    }
  }, [detalleServicio, errorDetalleServicio, cargandoDetalleServicio, accionServicio, cargandoVersion])


  useEffect(() => {
    let activo = true

    async function verificar() {
      try {
        const respuesta = await fetch('/api/acceso/sesion-actual/', {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        })

        const datos = await respuesta.json().catch(() => ({}))

        if (!activo) return

        if (!respuesta.ok || datos.usuario?.rol !== 'PROFESIONAL') {
          setEstado('sin-acceso')
          return
        }

        setUsuario(datos.usuario)
        setEstado('autorizado')
      } catch {
        if (activo) setEstado('error')
      }
    }

    verificar()
    return () => { activo = false }
  }, [])

  async function cerrarSesion() {
    if (cerrando) return

    setCerrando(true)
    setErrorSesion('')

    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
      })

      const datosCsrf = await respuestaCsrf.json().catch(() => ({}))

      if (!respuestaCsrf.ok || !datosCsrf.csrfToken) {
        throw new Error('No se pudo obtener el token CSRF.')
      }

      const respuesta = await fetch('/api/acceso/cerrar-sesion/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': datosCsrf.csrfToken,
        },
        body: JSON.stringify({}),
      })

      if (!respuesta.ok) {
        throw new Error('No se pudo cerrar la sesi\u00f3n.')
      }

      window.location.assign('/acceso-profesional')
    } catch (error) {
      setErrorSesion(
        error instanceof Error
          ? error.message
          : 'Error al cerrar la sesi\u00f3n.',
      )
      setCerrando(false)
    }
  }



  


  async function consultarVersionRevisada(idServicio) {
    if (!idServicio || cargandoVersion) return

    setCargandoVersion(true)
    setErrorAccionServicio('')
    setVersionRevisada(null)

    try {
      const respuesta = await fetch(
        `/api/marketplace/mis-servicios/${encodeURIComponent(idServicio)}/version-revisada/`,
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          typeof datos.mensaje === 'string'
            ? datos.mensaje
            : typeof datos.detail === 'string'
              ? datos.detail
              : `No fue posible consultar la versi\u00f3n (HTTP ${respuesta.status}).`,
        )
      }

      setVersionRevisada(datos)
    } catch (fallo) {
      setErrorAccionServicio(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo consultar la versi\u00f3n.',
      )
    } finally {
      setCargandoVersion(false)
    }
  }

  async function ejecutarAccionServicio(accion) {
    if (accionServicio || !idServicioDetalle) return

    const estado = detalleServicio?.estado_publicacion
    const configuracion = {
      revisar: {
        ruta: 'enviar-revision/',
        confirmacion: 'Enviar esta propuesta a revisi\u00f3n de Skilly?',
      },
      aprobar: {
        ruta: 'version-revisada/',
        confirmacion:
          'Confirmas que aceptas la versi\u00f3n final revisada por Skilly?',
      },
      rechazar_comercial: {
        ruta: 'rechazar-version-comercial/',
        confirmacion: '¿Confirmas rechazar estas condiciones? Esta decisión quedará registrada y no se publicará automáticamente.',
      },
      publicar: {
        ruta: 'publicar/',
        confirmacion:
          'Confirmas la publicaci\u00f3n del servicio con el precio aprobado?',
      },
    }

    const permitido = (
      (accion === 'revisar' &&
        ['BORRADOR', 'CORRECCION_SOLICITADA'].includes(estado)) ||
      (accion === 'aprobar' &&
        estado === 'PEND_APROBACION_PROFESIONAL') ||
      (accion === 'rechazar_comercial' &&
        estado === 'PEND_APROBACION_PROFESIONAL') ||
      (accion === 'publicar' &&
        estado === 'APROBADA_PARA_PUBLICAR')
    )

    if (!permitido || !configuracion[accion]) {
      setErrorAccionServicio(
        'El estado actual del servicio no permite esta acci\u00f3n.',
      )
      return
    }

    if (['aprobar', 'rechazar_comercial'].includes(accion) && !versionRevisada) {
      setErrorAccionServicio(
        'Primero debes consultar la versi\u00f3n revisada.',
      )
      return
    }

    if (accion === 'rechazar_comercial') {
      if (!motivoCategoriaComercial) {
        setErrorAccionServicio('Selecciona el motivo del rechazo.')
        return
      }
      if (motivoDetalleComercial.trim().length < 10 || motivoDetalleComercial.trim().length > 600) {
        setErrorAccionServicio('Explica el desacuerdo en 10 a 600 caracteres.')
        return
      }
    }

    if (!window.confirm(configuracion[accion].confirmacion)) return

    setAccionServicio(accion)
    setErrorAccionServicio('')
    setAvisoAccionServicio('')

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))

      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No fue posible obtener el token CSRF.')
      }

      const respuesta = await fetch(
        `/api/marketplace/mis-servicios/${encodeURIComponent(idServicioDetalle)}/${configuracion[accion].ruta}`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfDatos.csrfToken,
          },
          body: JSON.stringify(accion === 'rechazar_comercial'
            ? { motivo_categoria: motivoCategoriaComercial, motivo_detalle: motivoDetalleComercial.trim() }
            : {}),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        const mensaje = datos.mensaje ?? datos.detail
        throw new Error(
          typeof mensaje === 'string'
            ? mensaje
            : `No se pudo completar la operaci\u00f3n (HTTP ${respuesta.status}).`,
        )
      }

      setAvisoAccionServicio(
        typeof datos.mensaje === 'string'
          ? datos.mensaje
          : 'Operaci\u00f3n registrada correctamente.',
      )
      setVersionRevisada(null)
      if (accion === 'rechazar_comercial') {
        setMotivoCategoriaComercial('')
        setMotivoDetalleComercial('')
      }

      const detalleRespuesta = await fetch(
        `/api/marketplace/mis-servicios/${encodeURIComponent(idServicioDetalle)}/`,
        {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      if (detalleRespuesta.ok) {
        const detalleDatos = await detalleRespuesta.json().catch(() => ({}))
        setDetalleServicio(detalleDatos.servicio ?? detalleDatos)
      }

      await cargarServicios()
    } catch (fallo) {
      setErrorAccionServicio(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible completar la operaci\u00f3n.',
      )
    } finally {
      setAccionServicio('')
    }
  }

  async function consultarDetalleServicio(idServicio) {
    if (!idServicio || cargandoDetalleServicio) return
    setVentanaPortal(null)

    setCargandoDetalleServicio(true)
    setErrorDetalleServicio('')
    setDetalleServicio(null)
    setIdServicioDetalle(idServicio)
    setVersionRevisada(null)
    setErrorAccionServicio('')
    setAvisoAccionServicio('')

    try {
      const respuesta = await fetch(
        `/api/marketplace/mis-servicios/${encodeURIComponent(idServicio)}/`,
        {
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        const mensaje = datos.mensaje ?? datos.detail
        throw new Error(
          typeof mensaje === 'string'
            ? mensaje
            : `No se pudo consultar el servicio (HTTP ${respuesta.status}).`,
        )
      }

      const servicio = datos.servicio ?? datos

      if (!servicio || typeof servicio !== 'object' || Array.isArray(servicio)) {
        throw new Error('El detalle del servicio tiene un formato inesperado.')
      }

      setDetalleServicio(servicio)
    } catch (fallo) {
      setErrorDetalleServicio(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo consultar el servicio.',
      )
    } finally {
      setCargandoDetalleServicio(false)
    }
  }

  async function cargarServicios() {
    setCargandoServicios(true)
    setErrorServicios('')

    try {
      const respuesta = await fetch('/api/marketplace/mis-servicios/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          typeof datos.detail === 'string'
            ? datos.detail
            : `No fue posible consultar mis servicios (HTTP ${respuesta.status}).`,
        )
      }

      const lista = Array.isArray(datos)
        ? datos
        : Array.isArray(datos.servicios)
          ? datos.servicios
          : Array.isArray(datos.resultados)
            ? datos.resultados
            : null

      if (!lista) {
        throw new Error('La API de servicios devolvió un formato inesperado.')
      }

      setServicios(lista)
      registrarConsulta('servicios')
    } catch (error) {
      setErrorServicios(
        error instanceof Error ? error.message : 'Error al consultar servicios.',
      )
    } finally {
      setCargandoServicios(false)
    }
  }


  async function cargarPerfil() {
    setCargandoPerfil(true)
    setErrorPerfil('')

    try {
      const respuesta = await fetch('/api/profesionales/mi-perfil/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          typeof datos.detail === 'string'
            ? datos.detail
            : `No fue posible consultar el perfil (HTTP ${respuesta.status}).`,
        )
      }

      setPerfil(datos.perfil ?? datos.profesional ?? datos)
      registrarConsulta('perfil')
    } catch (fallo) {
      setErrorPerfil(
        fallo instanceof Error ? fallo.message : 'Error al consultar el perfil.',
      )
    } finally {
      setCargandoPerfil(false)
    }
  }


  async function cargarValidacion() {
    setCargandoValidacion(true)
    setErrorValidacion('')

    try {
      const rutas = [
        '/api/profesionales/mis-documentos/',
        '/api/profesionales/mi-validacion/',
      ]

      const respuestas = await Promise.all(
        rutas.map((ruta) =>
          fetch(ruta, {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: { Accept: 'application/json' },
          }),
        ),
      )

      const datos = await Promise.all(
        respuestas.map((respuesta) =>
          respuesta.json().catch(() => ({})),
        ),
      )

      for (let indice = 0; indice < respuestas.length; indice += 1) {
        if (!respuestas[indice].ok) {
          throw new Error(
            `No fue posible consultar la informaci\u00f3n profesional ` +
            `(HTTP ${respuestas[indice].status}).`,
          )
        }
      }

      setDocumentos(datos[0])
      setValidacion(datos[1])
      registrarConsulta('validacion')
    } catch (fallo) {
      setErrorValidacion(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible consultar la validaci\u00f3n.',
      )
    } finally {
      setCargandoValidacion(false)
    }
  }



  async function consultarBloquesEntrevista() {
    if (cargandoBloques) return

    setCargandoBloques(true)
    setErrorReserva('')
    setAvisoReserva('')

    try {
      const respuesta = await fetch(
        '/api/profesionales/mi-entrevista/reservar/',
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          datos.mensaje ?? datos.detail ??
          `No fue posible consultar los horarios (HTTP ${respuesta.status}).`,
        )
      }

      if (!Array.isArray(datos.bloques_disponibles)) {
        throw new Error('La API devolvi\u00f3 horarios en un formato inesperado.')
      }

      setBloquesEntrevista(datos.bloques_disponibles)
      setBloqueSeleccionado('')
      setBloquesConsultados(true)
      registrarConsulta('reserva')
    } catch (fallo) {
      setErrorReserva(
        fallo instanceof Error ? fallo.message : 'Error al consultar horarios.',
      )
    } finally {
      setCargandoBloques(false)
    }
  }

  async function reservarEntrevista(evento) {
    evento.preventDefault()

    if (reservandoEntrevista || !bloqueSeleccionado) return

    const bloque = bloquesEntrevista.find(
      (item) => String(item.id_bloque_entrevista) === bloqueSeleccionado,
    )

    if (!bloque) {
      setErrorReserva('Selecciona un bloque disponible.')
      return
    }

    const confirmacion = window.confirm(
      `\u00bfConfirmas la reserva del ${bloque.fecha} ` +
      `a las ${String(bloque.hora_inicio).slice(0, 5)}?`,
    )

    if (!confirmacion) return

    setReservandoEntrevista(true)
    setErrorReserva('')
    setAvisoReserva('')

    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datosCsrf = await respuestaCsrf.json().catch(() => ({}))

      if (!respuestaCsrf.ok || !datosCsrf.csrfToken) {
        throw new Error('No fue posible obtener el token de seguridad.')
      }

      const respuesta = await fetch(
        '/api/profesionales/mi-entrevista/reservar/',
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': datosCsrf.csrfToken,
          },
          body: JSON.stringify({
            id_bloque_entrevista: Number(bloqueSeleccionado),
          }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          datos.mensaje ?? datos.detail ??
          `No fue posible reservar (HTTP ${respuesta.status}).`,
        )
      }

      setEntrevista(datos.entrevista ?? null)
      setEntrevistaConsultada(true)
      setAvisoReserva(
        datos.mensaje ?? 'Entrevista agendada correctamente.',
      )
      setBloquesEntrevista([])
      setBloqueSeleccionado('')
      setBloquesConsultados(false)
    } catch (fallo) {
      setErrorReserva(
        fallo instanceof Error ? fallo.message : 'Error al reservar.',
      )
    } finally {
      setReservandoEntrevista(false)
    }
  }





  async function registrarEntregaProfesional(evento) {
    evento.preventDefault()

    if (registrandoEntrega || !entregasSeleccionadas) return

    const descripcion = descripcionNuevaEntrega.trim()
    const referenciaEntrega = referenciaNuevaEntrega.trim()

    if (!descripcion) {
      setErrorNuevaEntrega('Debes ingresar una descripci\u00f3n.')
      return
    }

    const prestacionActual = coordinados.find(
      (item) =>
        Number(item.id_prestacion) === Number(entregasSeleccionadas),
    )

    if (
      ['FINALIZADA', 'CANCELADA', 'POSTERGADA'].includes(
        prestacionActual?.estado,
      )
    ) {
      setErrorNuevaEntrega(
        'La prestaci\u00f3n est\u00e1 cerrada para nuevas entregas.',
      )
      return
    }

    if (!window.confirm(
      `\u00bfConfirmas registrar una nueva entrega para la prestaci\u00f3n #${entregasSeleccionadas}?`,
    )) {
      return
    }

    if (archivosNuevaEntrega.length > 3 ||
        archivosNuevaEntrega.some((f) => f.size > 10 * 1024 * 1024) ||
        archivosNuevaEntrega.reduce((total, f) => total + f.size, 0) > 25 * 1024 * 1024) {
      setErrorNuevaEntrega('Máximo 3 archivos, 10 MB cada uno y 25 MB en total.')
      return
    }

    setRegistrandoEntrega(true)
    setErrorNuevaEntrega('')
    setExitoNuevaEntrega('')

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))

      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }

      // Si no hay archivos, conservar sin cambios el endpoint original.
      const conArchivos = habilitaArchivoEntrega && archivosNuevaEntrega.length > 0
      const formulario = new FormData()
      if (conArchivos) {
        formulario.append('descripcion', descripcion)
        if (referenciaEntrega) formulario.append('referencia_entrega', referenciaEntrega)
        archivosNuevaEntrega.forEach((archivo) => formulario.append('archivos', archivo))
      }
      const respuesta = await fetch(
        conArchivos
          ? `/api/seguimiento/profesional/prestaciones/${encodeURIComponent(entregasSeleccionadas)}/entregas-con-archivos/`
          : `/api/seguimiento/profesional/prestaciones/${encodeURIComponent(entregasSeleccionadas)}/entregas/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            ...(conArchivos ? {} : { 'Content-Type': 'application/json' }),
            'X-CSRFToken': csrfDatos.csrfToken,
          },
          body: conArchivos ? formulario : JSON.stringify({
            descripcion,
            referencia_entrega: referenciaEntrega || null,
          }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        const mensaje = datos.mensaje ?? datos.detail

        if (typeof mensaje === 'string') {
          throw new Error(mensaje)
        }

        const validaciones = Object.entries(datos)
          .map(([campo, valor]) =>
            `${campo}: ${Array.isArray(valor) ? valor.join(', ') : String(valor)}`,
          )
          .join(' | ')

        throw new Error(
          validaciones ||
          `No fue posible registrar la entrega (HTTP ${respuesta.status}).`,
        )
      }

      setDescripcionNuevaEntrega('')
      setReferenciaNuevaEntrega('')
      setArchivosNuevaEntrega([])
      setExitoNuevaEntrega(
        datos.mensaje ?? 'Entrega registrada correctamente.',
      )

      await cargarEntregasProfesional(entregasSeleccionadas)
    } catch (fallo) {
      setErrorNuevaEntrega(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible registrar la entrega.',
      )
    } finally {
      setRegistrandoEntrega(false)
    }
  }

  async function cargarEntregasProfesional(idPrestacion) {
    if (!idPrestacion || cargandoEntregas) return
    setVentanaPortal('entregas')

    setCargandoEntregas(true)
    setErrorEntregas('')
    setEntregasProfesional([])
    setObservacionesEntregas([])
    setEntregasSeleccionadas(idPrestacion)
    setHabilitaArchivoEntrega(false)
    setFormatosEntrega([])
    setOrientacionEntrega('')
    setArchivosNuevaEntrega([])
    setArchivosEntregaE3([])
    setErrorAdjuntosE3('')

    try {
      const respuesta = await fetch(
        `/api/seguimiento/profesional/prestaciones/${encodeURIComponent(idPrestacion)}/entregas/`,
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          typeof datos.mensaje === 'string'
            ? datos.mensaje
            : `No fue posible consultar entregas (HTTP ${respuesta.status}).`,
        )
      }

      const lista = Array.isArray(datos)
        ? datos
        : Array.isArray(datos.entregas)
          ? datos.entregas
          : Array.isArray(datos.resultados)
            ? datos.resultados
            : null

      if (!lista) {
        throw new Error('Formato inesperado de entregas.')
      }

      if (!Array.isArray(datos.observaciones)) {
        throw new Error('La API no devolvió las observaciones de las entregas.')
      }

      setEntregasProfesional(lista)
      setObservacionesEntregas(datos.observaciones)
      // Adicional: metadatos/documentos protegidos del servicio.
      // Su fallo no elimina ni cambia las entregas tradicionales.
      try {
        const r = await fetch(
          `/api/seguimiento/profesional/prestaciones/${encodeURIComponent(idPrestacion)}/entregables/`,
          { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } },
        )
        const d = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(d.mensaje || 'No se pudo verificar el formato de entrega.')
        setHabilitaArchivoEntrega(d.permitir_archivos === true)
        setFormatosEntrega(Array.isArray(d.formatos_permitidos) ? d.formatos_permitidos : [])
        setOrientacionEntrega(typeof d.orientacion === 'string' ? d.orientacion : '')
        setArchivosEntregaE3(Array.isArray(d.archivos) ? d.archivos : [])
      } catch (e) {
        setErrorAdjuntosE3(e.message || 'No se pudieron consultar los adjuntos.')
      }
    } catch (fallo) {
      setErrorEntregas(
        fallo instanceof Error ? fallo.message : 'Error al consultar entregas.',
      )
    } finally {
      setCargandoEntregas(false)
    }
  }

  async function cargarSeguimientoProfesional(idPrestacion) {
    if (!idPrestacion || cargandoSeguimiento) return
    setVentanaPortal('seguimiento')

    setCargandoSeguimiento(true)
    setErrorSeguimiento('')
    setSeguimientoProfesional(null)
    setSeguimientoSeleccionado(idPrestacion)

    try {
      const respuesta = await fetch(
        `/api/seguimiento/profesional/prestaciones/${encodeURIComponent(idPrestacion)}/`,
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          typeof datos.mensaje === 'string'
            ? datos.mensaje
            : `No fue posible consultar el seguimiento (HTTP ${respuesta.status}).`,
        )
      }

      setSeguimientoProfesional(datos)
    } catch (fallo) {
      setErrorSeguimiento(
        fallo instanceof Error
          ? fallo.message
          : 'Error al consultar el seguimiento.',
      )
    } finally {
      setCargandoSeguimiento(false)
    }
  }


  async function cargarPagosProfesional() {
    if (cargandoPagos) return

    setCargandoPagos(true)
    setErrorPagos('')
    setPagosConsultados(false)

    try {
      const respuesta = await fetch('/api/pagos/profesional/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          typeof datos.mensaje === 'string'
            ? datos.mensaje
            : typeof datos.detail === 'string'
              ? datos.detail
              : `No fue posible consultar los pagos (HTTP ${respuesta.status}).`,
        )
      }

      const lista = Array.isArray(datos)
        ? datos
        : Array.isArray(datos.pagos)
          ? datos.pagos
          : Array.isArray(datos.resultados)
            ? datos.resultados
            : null

      if (!lista) {
        throw new Error('La API devolvi\u00f3 un formato de pagos inesperado.')
      }

      setPagosProfesional(lista)
      setPagosConsultados(true)
      registrarConsulta('pagos')
    } catch (fallo) {
      setPagosProfesional([])
      setErrorPagos(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible consultar los pagos.',
      )
    } finally {
      setCargandoPagos(false)
    }
  }

  async function cargarCoordinados() {
    if (cargandoCoordinados) return

    setCargandoCoordinados(true)
    setErrorCoordinados('')

    try {
      const respuesta = await fetch(
        '/api/coordinacion/mis-servicios-coordinados/',
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: { Accept: 'application/json' },
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          typeof datos.mensaje === 'string'
            ? datos.mensaje
            : `No fue posible consultar las prestaciones (HTTP ${respuesta.status}).`,
        )
      }

      const lista = Array.isArray(datos.servicios_coordinados)
        ? datos.servicios_coordinados
        : Array.isArray(datos)
          ? datos
          : Array.isArray(datos.prestaciones)
            ? datos.prestaciones
            : Array.isArray(datos.servicios)
              ? datos.servicios
              : Array.isArray(datos.resultados)
                ? datos.resultados
                : null

      if (!lista) {
        throw new Error('La API devolvió un formato inesperado.')
      }

      setCoordinados(lista)
      setCoordinadosConsultados(true)
      registrarConsulta('coordinados')
    } catch (fallo) {
      setErrorCoordinados(
        fallo instanceof Error
          ? fallo.message
          : 'Error al consultar los servicios coordinados.',
      )
    } finally {
      setCargandoCoordinados(false)
    }
  }

  async function cancelarEntrevista(evento) {
    evento.preventDefault()
    const motivo = motivoCancelacion.trim()
    if (cancelandoEntrevista || entrevista?.estado !== 'AGENDADA') return
    if (motivo.length < 10 || motivo.length > 500) {
      setErrorEntrevista('Indica un motivo entre 10 y 500 caracteres.')
      return
    }
    if (!window.confirm('¿Confirmas cancelar esta entrevista? Se conservará el historial.')) return

    setCancelandoEntrevista(true)
    setErrorEntrevista('')
    setAvisoEntrevista('')
    try {
      const csrf = await fetch('/api/acceso/csrf/', {
        method: 'GET', credentials: 'same-origin', cache: 'no-store',
        headers: { Accept: 'application/json' },
      })
      const datosCsrf = await csrf.json().catch(() => ({}))
      if (!csrf.ok || !datosCsrf.csrfToken) {
        throw new Error('No fue posible obtener el token de seguridad.')
      }
      const respuesta = await fetch('/api/profesionales/mi-entrevista/cancelar/', {
        method: 'POST', credentials: 'same-origin',
        headers: {
          Accept: 'application/json', 'Content-Type': 'application/json',
          'X-CSRFToken': datosCsrf.csrfToken,
        },
        body: JSON.stringify({ motivo }),
      })
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) {
        throw new Error(datos.mensaje ?? datos.detail ?? `No se pudo cancelar (HTTP ${respuesta.status}).`)
      }
      setEntrevista(datos.entrevista)
      setMotivoCancelacion('')
      setAvisoEntrevista(datos.mensaje ?? 'Entrevista cancelada.')
      registrarConsulta('entrevista')
    } catch (fallo) {
      setErrorEntrevista(fallo instanceof Error ? fallo.message : 'No se pudo cancelar.')
    } finally {
      setCancelandoEntrevista(false)
    }
  }

  async function cargarEntrevista() {
    if (cargandoEntrevista) return

    setCargandoEntrevista(true)
    setErrorEntrevista('')

    try {
      const respuesta = await fetch('/api/profesionales/mi-entrevista/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        const mensaje = datos.mensaje ?? datos.detail
        throw new Error(
          typeof mensaje === 'string'
            ? mensaje
            : `No fue posible consultar la entrevista (HTTP ${respuesta.status}).`,
        )
      }

      setEntrevista(datos)
      registrarConsulta('entrevista')
      setEntrevistaConsultada(true)
    } catch (fallo) {
      setErrorEntrevista(
        fallo instanceof Error
          ? fallo.message
          : 'Error al consultar la entrevista.',
      )
    } finally {
      setCargandoEntrevista(false)
    }
  }


  const cerrarVentana = useCallback(() => {
    // No interrumpir operaciones de escritura en curso.
    if (registrandoEntrega || reservandoEntrevista || cancelandoEntrevista || accionServicio) return
    setVentanaPortal(null)
  }, [registrandoEntrega, reservandoEntrevista, cancelandoEntrevista, accionServicio])

  const volverACoordinados = useCallback(() => {
    if (registrandoEntrega) return
    setVentanaPortal('coordinados')
    setErrorNuevaEntrega('')
    setExitoNuevaEntrega('')
  }, [registrandoEntrega])

  function abrirOpcion(seccion) {
    setVentanaPortal(seccion)
    if (seccion === 'mis-servicios') void cargarServicios()
    if (seccion === 'perfil') void cargarPerfil()
    if (seccion === 'validacion') void cargarValidacion()
    if (seccion === 'entrevista') {
      setAvisoEntrevista('')
      void cargarEntrevista()
    }
    if (seccion === 'reserva') void consultarBloquesEntrevista()
    if (seccion === 'coordinados') void cargarCoordinados()
    if (seccion === 'pagos') void cargarPagosProfesional()
  }

  const opcionesPorModulo = {
    servicios: [
      ['mis-servicios', 'Mis servicios', 'Consultar propuestas y crear nuevos servicios', '▤'],
    ],
    cuenta: [
      ['perfil', 'Mi perfil', 'Consultar datos profesionales', '◉'],
      ['centro-validacion', 'Documentos y validación', 'Documentos, solicitudes y entrevistas en un solo lugar', '✓'],
    ],
    actividad: [
      ['centro-actividad', 'Mi trabajo y pagos', 'Oportunidades, prestaciones, entregas y pagos en un solo lugar', '▤'],
    ],
    desarrollo: [
      ['centro-desarrollo', 'Explorar y desarrollo', 'Recomendaciones, disponibilidad y Marketplace en un solo lugar', '◇'],
    ],
  }

return (
    <div className="pp-pagina">
      <header className="pp-cabecera">
        <a href="/" className="pp-marca">SKILLY</a>
        <div className="pp-navegacion">
          <a href="/#marketplace">Marketplace</a>
          {estado === 'autorizado' && (
            <button
              type="button"
              className="pp-cerrar"
              onClick={cerrarSesion}
              disabled={cerrando}
            >
              {cerrando ? 'Cerrando...' : 'Cerrar sesi\u00f3n'}
            </button>
          )}
        </div>
      </header>

      <main className="pp-contenido">
        {errorSesion && (
          <p role="alert" className="pp-error">{errorSesion}</p>
        )}

        {estado === 'cargando' && (
          <p role="status">Verificando la sesi&oacute;n profesional...</p>
        )}

        {estado === 'sin-acceso' && (
          <section className="pp-panel">
            <h1>Acceso profesional</h1>
            <p>Debes iniciar sesi&oacute;n con una cuenta profesional.</p>
            <a className="pp-boton" href="/acceso-profesional">
              Iniciar sesi&oacute;n
            </a>
          </section>
        )}

        {estado === 'error' && (
          <section className="pp-panel">
            <h1>No fue posible verificar tu sesi&oacute;n</h1>
            <p>Comprueba que el servidor de Skilly est&eacute; funcionando.</p>
            <button type="button" className="pp-boton"
              onClick={() => window.location.reload()}>
              Reintentar
            </button>
          </section>
        )}

        {estado === 'autorizado' && (
          <>
            <ReagendamientosProfesional />
            <div className="pp-introduccion">
              <span className="pp-etiqueta">ESPACIO PROFESIONAL</span>
              <h1>Mi portal profesional</h1>
              <p>
                Sesi&oacute;n activa
                {usuario?.correo ? `: ${usuario.correo}` : ''}.
                Administra tu disponibilidad para recibir solicitudes
                de servicios en Skilly.
              </p>
            </div>

            
            <nav className="pp-menu-modulos" aria-label="Módulos del portal profesional">
              {[
                {
                  id: 'servicios',
                  icono: '▤',
                  titulo: 'Mis servicios',
                  descripcion: 'Propuestas, revisión y publicación',
                },
                {
                  id: 'cuenta',
                  icono: '✓',
                  titulo: 'Perfil y validación',
                  descripcion: 'Datos, antecedentes y entrevista',
                },
                {
                  id: 'actividad',
                  icono: '◷',
                  titulo: 'Trabajo y pagos',
                  descripcion: 'Coordinación, entregas y pagos',
                },
                {
                  id: 'desarrollo',
                  icono: '◇',
                  titulo: 'Explorar y desarrollo',
                  descripcion: 'Recomendaciones y disponibilidad',
                },
              ].map((modulo) => (
                <button
                  type="button"
                  key={modulo.id}
                  className={`pp-menu-tarjeta${moduloPortal === modulo.id ? ' activa' : ''}`}
                  aria-pressed={moduloPortal === modulo.id}
                  onClick={() => {
                    setModuloPortal(modulo.id)
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }}
                >
                  <span className="pp-menu-icono" aria-hidden="true">
                    {modulo.icono}
                  </span>
                  <strong>{modulo.titulo}</strong>
                  <span className="pp-menu-descripcion">{modulo.descripcion}</span>
                  <small>
                    {moduloPortal === modulo.id ? 'Módulo actual' : 'Abrir módulo →'}
                  </small>
                </button>
              ))}
            </nav>

            <div className="pp-opciones-secciones" aria-label="Acciones del módulo">
              {opcionesPorModulo[moduloPortal].map(([id, titulo, descripcion, icono]) => (
                <button type="button" className="pp-opcion-seccion" key={id}
                  onClick={() => abrirOpcion(id)}>
                  <span className="pp-opcion-icono" aria-hidden="true">{icono}</span>
                  <strong>{titulo}</strong>
                  <span>{descripcion}</span>
                  <small>Abrir ventana →</small>
                </button>
              ))}
            </div>

            <div className="pp-modulo-grupo" hidden={moduloPortal !== 'servicios'}>
              <VentanaProfesional abierta={ventanaPortal === 'mis-servicios'} titulo="Mis servicios" onCerrar={cerrarVentana}>
              <section className="pp-panel pp-mis-servicios">
              <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('nueva-propuesta')}>
                + Nueva propuesta de servicio
              </button>
              <div className="pp-servicios-cabecera">
                <div>
                  <p>Consulta los servicios y propuestas asociados a tu cuenta.</p>
                </div>
                <button
                  type="button"
                  className="pp-boton"
                  onClick={cargarServicios}
                  disabled={cargandoServicios}
                >
                  {cargandoServicios ? 'Consultando...' : '↻ Recargar lista'}
                </button>
              </div>

              {ultimaConsulta.servicios && (
                <p className="pp-ultima-consulta" role="status">
                  Última consulta al servidor: {ultimaConsulta.servicios}.
                </p>
              )}

              {errorServicios && (
                <p role="alert" className="pp-error">{errorServicios}</p>
              )}

              {!cargandoServicios && !errorServicios && servicios.length === 0 && (
                <p>No tienes servicios o propuestas registrados.</p>
              )}

              {servicios.length > 0 && (
                <div className="pp-listado-servicios">
                  {servicios.map((servicio, indice) => (
                    <article
                      className="pp-servicio"
                      key={servicio.id_servicio ?? indice}
                    >
                      <div>
                        <h3>
                          {servicio.nombre ?? servicio.nombre_servicio ??
                            `Servicio #${servicio.id_servicio ?? indice + 1}`}
                        </h3>
                        <p>
                          Estado: {servicio.estado_publicacion ?? servicio.estado ?? 'Sin estado informado'}
                        </p>

                        {servicio.id_servicio && (
                          <button
                            type="button"
                            className="pp-boton pp-secundario"
                            disabled={cargandoDetalleServicio}
                            onClick={() =>
                              consultarDetalleServicio(servicio.id_servicio)
                            }
                          >
                            Ver detalle
                          </button>
                        )}
                        {servicio.descripcion && <p>{servicio.descripcion}</p>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
              </VentanaProfesional>

            
            </div>

            <div className="pp-modulo-grupo" hidden={moduloPortal !== 'cuenta'}>
              <VentanaProfesional abierta={ventanaPortal === 'centro-validacion'}
                titulo="Documentos y validación" onCerrar={cerrarVentana}>
                <p className="pp-centro-descripcion">Selecciona lo que necesitas gestionar. Cada opción conserva su funcionamiento original.</p>
                <div className="pp-centro-acciones">
                  {[
                    ['validacion', 'Mis documentos y validación', 'Consultar antecedentes y estado de validación', '✓'],
                    ['documentos', 'Adjuntar documentos', 'Administrar documentos profesionales', '▣'],
                    ['entrevista', 'Mi entrevista', 'Consultar la entrevista profesional', '◷'],
                    ['reserva', 'Reservar entrevista', 'Consultar horarios disponibles', '▦'],
                    ['solicitar-validacion', 'Solicitar validación', 'Enviar antecedentes a revisión', '➤'],
                  ].map(([id, titulo, descripcion, icono]) => (
                    <button type="button" className="pp-opcion-seccion" key={id}
                      onClick={() => abrirOpcion(id)}>
                      <span className="pp-opcion-icono" aria-hidden="true">{icono}</span>
                      <strong>{titulo}</strong>
                      <span>{descripcion}</span>
                      <small>Abrir ventana →</small>
                    </button>
                  ))}
                </div>
              </VentanaProfesional>
              <VentanaProfesional abierta={ventanaPortal === 'perfil'} titulo="Mi perfil" onCerrar={cerrarVentana}>
              <section className="pp-panel pp-mi-perfil">
              <div className="pp-servicios-cabecera">
                <div>
                  <p>Consulta la información asociada a tu cuenta.</p>
                </div>
                <button
                  type="button"
                  className="pp-boton"
                  disabled={cargandoPerfil}
                  onClick={cargarPerfil}
                >
                  {cargandoPerfil ? 'Consultando...' : '↻ Recargar datos'}
                </button>
              </div>

              {ultimaConsulta.perfil && (
                <p className="pp-ultima-consulta" role="status">
                  Última consulta al servidor: {ultimaConsulta.perfil}.
                </p>
              )}

              {errorPerfil && (
                <p role="alert" className="pp-error">{errorPerfil}</p>
              )}

              {cargandoPerfil && <p role="status">Cargando perfil...</p>}

              <button type="button" className="pp-boton pp-secundario"
                disabled={cargandoPerfil}
                onClick={() => abrirOpcion('completar-perfil')}>
                {perfil ? 'Editar perfil' : 'Crear mi perfil'}
              </button>

              {perfil && (
                <dl className="pp-datos-perfil">
                  {Object.entries(perfil)
                    .filter(([, valor]) =>
                      valor !== null &&
                      valor !== undefined &&
                      typeof valor !== 'object'
                    )
                    .filter(([campo]) =>
                      !/clave|token|secret|password|hash/i.test(campo)
                    )
                    .map(([campo, valor]) => (
                      <div key={campo}>
                        <dt>{campo.replaceAll('_', ' ')}</dt>
                        <dd>{String(valor)}</dd>
                      </div>
                    ))}
                </dl>
              )}
            </section>
              </VentanaProfesional>

            
            <VentanaProfesional abierta={ventanaPortal === 'validacion'} titulo="Documentos y validación" onCerrar={cerrarVentana}>
              <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-validacion')}>← Volver a Documentos y validación</button>
              <section className="pp-panel pp-validacion">
              <div className="pp-servicios-cabecera">
                <div>
                  <p>
                    Consulta tus antecedentes y el estado del proceso
                    de validaci&oacute;n de Skilly.
                  </p>
                </div>
                <button
                  type="button"
                  className="pp-boton"
                  onClick={cargarValidacion}
                  disabled={cargandoValidacion}
                >
                  {cargandoValidacion
                    ? 'Consultando...'
                    : 'Actualizar validaci\u00f3n'}
                </button>
              </div>

              {ultimaConsulta.validacion && (
                <p className="pp-ultima-consulta" role="status">
                  Última consulta al servidor: {ultimaConsulta.validacion}.
                </p>
              )}

              {errorValidacion && (
                <p role="alert" className="pp-error">
                  {errorValidacion}
                </p>
              )}

              {cargandoValidacion && <p role="status">Cargando validación...</p>}

              {validacion && (
                <div className="pp-resultado-validacion">
                  <h3>Estado de validaci&oacute;n</h3>
                  <DatosValidacion titulo="Estado de validacion" datos={validacion} />
                </div>
              )}

              {documentos && (
                <div className="pp-resultado-validacion">
                  <h3>Documentos registrados</h3>
                  <DatosValidacion titulo="Documentos profesionales" datos={documentos} />
                </div>
              )}
            </section>
              </VentanaProfesional>

            
            <VentanaProfesional abierta={ventanaPortal === 'entrevista'} titulo="Mi entrevista" onCerrar={cerrarVentana}>
              <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-validacion')}>← Volver a Documentos y validación</button>
              <section className="pp-panel pp-entrevista">
              <div className="pp-servicios-cabecera">
                <div>
                  <p>
                    Consulta los detalles de la entrevista asociada
                    a tu proceso de validaci&oacute;n.
                  </p>
                </div>

                <button
                  type="button"
                  className="pp-boton"
                  onClick={cargarEntrevista}
                  disabled={cargandoEntrevista}
                >
                  {cargandoEntrevista
                    ? 'Consultando...'
                    : '↻ Recargar entrevista'}
                </button>
              </div>

              {ultimaConsulta.entrevista && (
                <p className="pp-ultima-consulta" role="status">
                  Última consulta al servidor: {ultimaConsulta.entrevista}.
                </p>
              )}

              {errorEntrevista && (
                <p className="pp-error" role="alert">
                  {errorEntrevista}
                </p>
              )}

              {entrevistaConsultada && !cargandoEntrevista &&
                !errorEntrevista && !entrevista && (
                  <p>No hay una entrevista registrada.</p>
                )}

              {cargandoEntrevista && <p role="status">Cargando entrevista...</p>}

              {entrevista && (
                <ResumenEntrevista datos={entrevista} />
              )}
              {avisoEntrevista && <p className="pp-exito" role="status">{avisoEntrevista}</p>}
              {entrevista?.estado === 'AGENDADA' && (
                <form onSubmit={cancelarEntrevista} className="pp-formulario-reserva">
                  <h3>Cancelar entrevista de validación</h3>
                  <p>Se conservará la reserva anterior en el historial. Si faltan menos de 24 horas, SKILLY revisará el motivo. No hay sanciones automáticas.</p>
                  <label htmlFor="pp-motivo-cancelacion">Motivo de cancelación</label>
                  <textarea
                    id="pp-motivo-cancelacion"
                    rows={3} minLength={10} maxLength={500} required
                    value={motivoCancelacion}
                    onChange={(evento) => setMotivoCancelacion(evento.target.value)}
                    disabled={cancelandoEntrevista}
                    placeholder="Indica por qué necesitas cancelar la entrevista"
                    style={{ width: '100%', boxSizing: 'border-box' }}
                  />
                  <button type="submit" className="pp-boton" disabled={cancelandoEntrevista}>
                    {cancelandoEntrevista ? 'Cancelando...' : 'Cancelar entrevista'}
                  </button>
                </form>
              )}
              {entrevista?.estado === 'CANCELADA' && (
                <button type="button" className="pp-boton" onClick={() => abrirOpcion('reserva')}>
                  Consultar horarios para nueva reserva
                </button>
              )}
            </section>
              </VentanaProfesional>

            
            <VentanaProfesional abierta={ventanaPortal === 'reserva'} titulo="Reservar entrevista" onCerrar={cerrarVentana}>
              <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-validacion')}>← Volver a Documentos y validación</button>
              <section className="pp-panel pp-reserva-entrevista">
              <div className="pp-servicios-cabecera">
                <div>
                  <p>
                    Selecciona uno de los horarios disponibles para
                    tu proceso de validaci&oacute;n profesional.
                  </p>
                </div>

                <button
                  type="button"
                  className="pp-boton"
                  onClick={consultarBloquesEntrevista}
                  disabled={cargandoBloques || reservandoEntrevista}
                >
                  {cargandoBloques
                    ? 'Consultando...'
                    : '↻ Recargar horarios'}
                </button>
              </div>

              {ultimaConsulta.reserva && (
                <p className="pp-ultima-consulta" role="status">
                  Última consulta al servidor: {ultimaConsulta.reserva}.
                </p>
              )}

              {errorReserva && (
                <p className="pp-error" role="alert">{errorReserva}</p>
              )}

              {avisoReserva && (
                <p className="pp-exito" role="status">{avisoReserva}</p>
              )}

              {bloquesConsultados && bloquesEntrevista.length === 0 && (
                <p>No hay bloques de entrevista disponibles actualmente.</p>
              )}

              {bloquesEntrevista.length > 0 && (
                <form
                  className="pp-formulario-reserva"
                  onSubmit={reservarEntrevista}
                >
                  <label htmlFor="pp-bloque-entrevista">
                    Selecciona fecha y horario
                  </label>

                  <select
                    id="pp-bloque-entrevista"
                    value={bloqueSeleccionado}
                    required
                    disabled={reservandoEntrevista}
                    onChange={(evento) =>
                      setBloqueSeleccionado(evento.target.value)
                    }
                  >
                    <option value="">Selecciona un horario</option>
                    {bloquesEntrevista.map((bloque) => (
                      <option
                        key={bloque.id_bloque_entrevista}
                        value={bloque.id_bloque_entrevista}
                      >
                        {bloque.fecha}
                        {' | '}
                        {String(bloque.hora_inicio).slice(0, 5)}
                        {' - '}
                        {String(bloque.hora_fin).slice(0, 5)}
                        {' | Cupos: '}
                        {bloque.cupos_disponibles}
                      </option>
                    ))}
                  </select>

                  <button
                    type="submit"
                    className="pp-boton"
                    disabled={reservandoEntrevista || !bloqueSeleccionado}
                  >
                    {reservandoEntrevista
                      ? 'Reservando...'
                      : 'Confirmar reserva'}
                  </button>
                </form>
              )}
            </section>
              </VentanaProfesional>

            
            </div>

            <div className="pp-modulo-grupo" hidden={moduloPortal !== 'actividad'}>
              <VentanaProfesional abierta={ventanaPortal === 'centro-actividad'}
                titulo="Mi trabajo y pagos" onCerrar={cerrarVentana}>
                <p className="pp-centro-descripcion">Consulta tus oportunidades, revisa tus prestaciones y accede a los pagos registrados por Skilly.</p>
                <div className="pp-centro-acciones">
                  {[
                    ['oportunidades', 'Mis oportunidades', 'Solicitudes empresariales asociadas a mi perfil', '◇'],
                    ['coordinados', 'Mis servicios coordinados', 'Seguimiento, avances y entregas por prestación', '▤'],
                    ['pagos', 'Mis pagos', 'Consultar pagos, retenciones y liberaciones', '$'],
                    ['cuenta-cobro', 'Cuenta para recibir pagos', 'Cuenta bancaria y abonos registrados', '▣'],
                  ].map(([id, titulo, descripcion, icono]) => (
                    <button type="button" className="pp-opcion-seccion" key={id}
                      onClick={() => abrirOpcion(id)}>
                      <span className="pp-opcion-icono" aria-hidden="true">{icono}</span>
                      <strong>{titulo}</strong>
                      <span>{descripcion}</span>
                      <small>Abrir ventana →</small>
                    </button>
                  ))}
                </div>
              </VentanaProfesional>
              <VentanaProfesional
                abierta={ventanaPortal === 'oportunidades'}
                titulo="Mis oportunidades"
                onCerrar={cerrarVentana}
              >
                <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-actividad')}>← Volver a Mi trabajo y pagos</button>
                <OportunidadesProfesional />
              </VentanaProfesional>

              <VentanaProfesional abierta={ventanaPortal === 'coordinados'} titulo="Servicios coordinados" onCerrar={cerrarVentana}>
              <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-actividad')}>← Volver a Mi trabajo y pagos</button>
              <section className="pp-panel pp-coordinados">
              <div className="pp-servicios-cabecera">
                <div>
                  <p>Consulta las prestaciones asociadas a tu cuenta profesional.</p>
                </div>
                <button
                  type="button"
                  className="pp-boton"
                  onClick={cargarCoordinados}
                  disabled={cargandoCoordinados}
                >
                  {cargandoCoordinados
                    ? 'Consultando...'
                    : '↻ Recargar lista'}
                </button>
              </div>

              {ultimaConsulta.coordinados && (
                <p className="pp-ultima-consulta" role="status">
                  Última consulta al servidor: {ultimaConsulta.coordinados}.
                </p>
              )}

              {errorCoordinados && (
                <p role="alert" className="pp-error">{errorCoordinados}</p>
              )}

              {coordinadosConsultados &&
                coordinados.length === 0 &&
                !errorCoordinados && (
                  <p>No tienes servicios coordinados registrados.</p>
                )}

              {coordinados.length > 0 && (
                <div className="pp-listado-servicios">
                  {coordinados.map((item, indice) => (
                    <article
                      className="pp-servicio"
                      key={
                        item.id_prestacion ??
                        item.id_solicitud ??
                        indice
                      }
                    >
                      <h3>
                        {(
                          typeof item.nombre_servicio === 'string' &&
                          item.nombre_servicio.trim()
                        ) || (
                          typeof item.servicio === 'string' &&
                          item.servicio.trim()
                        ) || (
                          item.servicio &&
                          typeof item.servicio === 'object' &&
                          typeof item.servicio.nombre === 'string' &&
                          item.servicio.nombre.trim()
                        ) || `Prestación #${item.id_prestacion ?? indice + 1}`}
                      </h3>
                      <p>
                        Estado: {String(item.estado ?? 'No informado')}
                      </p>
                      {item.fecha_inicio && (
                        <p>Inicio: {String(item.fecha_inicio).slice(0, 10)}</p>
                      )}

                      {item.id_prestacion && (
                        <button
                          type="button"
                          className="pp-boton"
                          disabled={cargandoSeguimiento}
                          onClick={() =>
                            cargarSeguimientoProfesional(item.id_prestacion)
                          }
                        >
                          {cargandoSeguimiento &&
                            seguimientoSeleccionado === item.id_prestacion
                            ? 'Consultando...'
                            : 'Ver seguimiento'}
                        </button>
                      )}

                      {item.id_prestacion && (
                        <button
                          type="button"
                          className="pp-boton pp-secundario"
                          disabled={cargandoEntregas}
                          onClick={() =>
                            cargarEntregasProfesional(item.id_prestacion)
                          }
                        >
                          {cargandoEntregas &&
                            entregasSeleccionadas === item.id_prestacion
                            ? 'Consultando...'
                            : 'Ver entregas'}
                        </button>
                      )}


                    </article>
                  ))}
                </div>
              )}
            </section>
              </VentanaProfesional>

            
            {seguimientoSeleccionado !== null && (
              <VentanaProfesional abierta={ventanaPortal === 'seguimiento'} titulo={`Seguimiento de prestación #${seguimientoSeleccionado}`} onCerrar={volverACoordinados}>
              <section className="pp-panel pp-seguimiento">

                {errorSeguimiento && (
                  <p className="pp-error" role="alert">
                    {errorSeguimiento}
                  </p>
                )}

                {cargandoSeguimiento && (
                  <p role="status">Consultando seguimiento...</p>
                )}

                {seguimientoProfesional && (
                  <div className="pp-resultado-validacion">
                    <h3>Informaci&oacute;n de seguimiento</h3>
                    <DetalleSeguimientoProfesional datos={seguimientoProfesional} />
                  </div>
                )}

                {['CONTRATADA', 'EN_EJECUCION', 'EN_PROGRESO'].includes(
                  coordinados.find((item) => Number(item.id_prestacion) === Number(seguimientoSeleccionado))?.estado,
                ) && (
                  <button type="button" className="pp-boton"
                    onClick={() => setVentanaPortal('avance')}>
                    Registrar avance
                  </button>
                )}
                <button
                  type="button"
                  className="pp-boton pp-secundario"
                  onClick={() => {
                    setSeguimientoSeleccionado(null)
                    setSeguimientoProfesional(null)
                    setErrorSeguimiento('')
                    setVentanaPortal('coordinados')
                  }}
                >
                  Volver a servicios coordinados
                </button>
              </section>
              </VentanaProfesional>
            )}

            
            {entregasSeleccionadas !== null && (
              <VentanaProfesional abierta={ventanaPortal === 'entregas'} titulo={`Entregas de prestación #${entregasSeleccionadas}`} onCerrar={volverACoordinados}>
              <section className="pp-panel pp-entregas-profesional">

                {cargandoEntregas && (
                  <p role="status">Consultando entregas...</p>
                )}

                {errorEntregas && (
                  <p role="alert" className="pp-error">
                    {errorEntregas}
                  </p>
                )}

                {!cargandoEntregas && !errorEntregas &&
                  entregasProfesional.length === 0 && (
                    <p>No hay entregas registradas en esta prestaci&oacute;n.</p>
                  )}

                {entregasProfesional.length > 0 && (
                  <div className="pp-listado-servicios">
                    {entregasProfesional.map((entrega, indice) => (
                      <article
                        className="pp-servicio"
                        key={entrega.id_entrega ?? indice}
                      >
                        <h3>Entrega #{entrega.id_entrega ?? indice + 1}</h3>
                        <p>Estado: {entrega.estado ?? 'No informado'}</p>
                        {entrega.descripcion && <p>{entrega.descripcion}</p>}
                        {entrega.fecha_entrega && (
                          <p>
                            Fecha: {formatearFechaChile(entrega.fecha_entrega)}
                          </p>
                        )}
                        {entrega.referencia_entrega && (
                          <p>Referencia: {entrega.referencia_entrega}</p>
                        )}
                        {archivosEntregaE3.filter((a) => Number(a.id_entrega) === Number(entrega.id_entrega)).map((a) => (
                          <p key={a.id_archivo}>
                            <a href={`/api/seguimiento/profesional/entregables/archivos/${a.id_archivo}/`}>
                              Descargar respaldo: {a.nombre}
                            </a>
                          </p>
                        ))}
                        {observacionesEntregas
                          .filter((observacion) =>
                            Number(observacion.id_entrega) === Number(entrega.id_entrega),
                          )
                          .map((observacion) => (
                            <section
                              key={observacion.id_observacion}
                              aria-label={`Observación de la entrega #${entrega.id_entrega}`}
                              style={{
                                marginTop: 16,
                                padding: '14px 16px',
                                border: '1px solid #cddfd5',
                                borderLeft: '4px solid #376958',
                                borderRadius: 12,
                                background: '#f0f6f2',
                              }}
                            >
                              <strong style={{ color: '#285445' }}>
                                Observaciones de la organización
                              </strong>
                              <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', margin: '10px 0' }}>
                                {observacion.detalle}
                              </p>
                              {observacion.fecha && (
                                <small style={{ color: '#516c60' }}>
                                  Recibidas: {formatearFechaChile(observacion.fecha, true)}
                                </small>
                              )}
                            </section>
                          ))}
                      </article>
                    ))}
                  </div>
                )}


                {!['PENDIENTE_CONTRATACION', 'FINALIZADA', 'CANCELADA', 'POSTERGADA'].includes(
                  coordinados.find(
                    (item) =>
                      Number(item.id_prestacion) === Number(entregasSeleccionadas),
                  )?.estado,
                ) && (
                  <form
                    className="pp-formulario-entrega"
                    onSubmit={registrarEntregaProfesional}
                  >
                    <h3>Registrar nueva entrega</h3>

                    <label htmlFor="pp-descripcion-entrega">
                      Descripci&oacute;n de la entrega
                    </label>
                    <textarea
                      id="pp-descripcion-entrega"
                      rows={4}
                      required
                      value={descripcionNuevaEntrega}
                      disabled={registrandoEntrega}
                      onChange={(evento) =>
                        setDescripcionNuevaEntrega(evento.target.value)
                      }
                      placeholder="Describe el trabajo que entregas"
                    />

                    <label htmlFor="pp-referencia-entrega">
                      Referencia de entrega (opcional)
                    </label>
                    <input
                      id="pp-referencia-entrega"
                      type="text"
                      value={referenciaNuevaEntrega}
                      disabled={registrandoEntrega}
                      onChange={(evento) =>
                        setReferenciaNuevaEntrega(evento.target.value)
                      }
                      placeholder="Referencia del documento o entrega"
                    />

                    {habilitaArchivoEntrega && (
                      <div className="pp-adjuntos-entrega-e3">
                        <label htmlFor="pp-archivos-entrega-e3">Documentos o archivos de esta entrega (opcional)</label>
                        <input
                          key={`archivos-${entregasSeleccionadas}-${exitoNuevaEntrega}`}
                          id="pp-archivos-entrega-e3"
                          type="file"
                          multiple
                          accept={formatosEntrega.join(',')}
                          disabled={registrandoEntrega}
                          onChange={(e) => setArchivosNuevaEntrega(Array.from(e.target.files || []))}
                        />
                        <small>{orientacionEntrega} Hasta 3 archivos, máximo 10 MB cada uno y 25 MB en total.</small>
                      </div>
                    )}
                    {errorAdjuntosE3 && <p className="pp-nota-operativa" role="status">{errorAdjuntosE3}</p>}
                    <button
                      type="submit"
                      className="pp-boton"
                      disabled={
                        registrandoEntrega ||
                        !descripcionNuevaEntrega.trim()
                      }
                    >
                      {registrandoEntrega
                        ? 'Registrando...'
                        : 'Registrar entrega'}
                    </button>
                  </form>
                )}

                {coordinados.find(
                  (item) => Number(item.id_prestacion) === Number(entregasSeleccionadas),
                )?.estado === 'PENDIENTE_CONTRATACION' && (
                  <p className="pp-nota-operativa">
                    Esta prestación aún está pendiente de contratación. No se pueden registrar
                    entregas hasta que se cumplan las condiciones de contratación.
                  </p>
                )}

                {errorNuevaEntrega && (
                  <p role="alert" className="pp-error">
                    {errorNuevaEntrega}
                  </p>
                )}

                {exitoNuevaEntrega && (
                  <p role="status" className="pp-exito">
                    {exitoNuevaEntrega}
                  </p>
                )}

                <button
                  type="button"
                  className="pp-boton pp-secundario"
                  onClick={() => {
                    setEntregasSeleccionadas(null)
                    setEntregasProfesional([])
                    setObservacionesEntregas([])
                    setErrorEntregas('')
                    setVentanaPortal('coordinados')
                  }}
                >
                  Volver a servicios coordinados
                </button>
              </section>
              </VentanaProfesional>
            )}

            
            <VentanaProfesional abierta={ventanaPortal === 'cuenta-cobro'} titulo="Cuenta para recibir pagos" onCerrar={cerrarVentana}>
              <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-actividad')}>← Volver a Mi trabajo y pagos</button>
              <CuentaCobroProfesional />
            </VentanaProfesional>

            <VentanaProfesional abierta={ventanaPortal === 'pagos'} titulo="Mis pagos" onCerrar={cerrarVentana}>
              <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-actividad')}>← Volver a Mi trabajo y pagos</button>
              <section className="pp-panel pp-pagos-profesional">
              <div className="pp-servicios-cabecera">
                <div>
                  <p>
                    Consulta los pagos de tus prestaciones.
                    La retenci&oacute;n y liberaci&oacute;n de fondos
                    es administrada por Skilly.
                  </p>
                </div>

                <button
                  type="button"
                  className="pp-boton"
                  onClick={cargarPagosProfesional}
                  disabled={cargandoPagos}
                >
                  {cargandoPagos
                    ? 'Consultando...'
                    : '↻ Recargar pagos'}
                </button>
              </div>

              {ultimaConsulta.pagos && (
                <p className="pp-ultima-consulta" role="status">
                  Última consulta al servidor: {ultimaConsulta.pagos}.
                </p>
              )}

              {errorPagos && (
                <p className="pp-error" role="alert">
                  {errorPagos}
                </p>
              )}

              {cargandoPagos && (
                <p role="status">Cargando informaci&oacute;n econ&oacute;mica...</p>
              )}

              {pagosConsultados && !cargandoPagos && !errorPagos &&
                pagosProfesional.length === 0 && (
                  <p>No tienes pagos asociados actualmente.</p>
                )}

              {pagosProfesional.length > 0 && (
                <ResumenPagosProfesional pagos={pagosProfesional} />
              )}
            </section>
              </VentanaProfesional>

            
            </div>

            {(detalleServicio || errorDetalleServicio ||
              cargandoDetalleServicio) && createPortal(
              <div className="pp-modal-fondo" onMouseDown={(e) => {
                if (e.target === e.currentTarget) cerrarDetalleServicio()
              }}>
                <section className="pp-panel pp-detalle-servicio"
                  role="dialog" aria-modal="true" aria-labelledby="pp-titulo-detalle">
                  <div className="pp-modal-cabecera">
                    <h2 id="pp-titulo-detalle">Detalle de mi servicio</h2>
                    <button type="button" className="pp-modal-cerrar" autoFocus
                      aria-label="Cerrar ventana de detalle"
                      disabled={cargandoDetalleServicio || Boolean(accionServicio) || cargandoVersion}
                      onClick={cerrarDetalleServicio}>&times;</button>
                  </div>

                {cargandoDetalleServicio && (
                  <p role="status">Consultando servicio...</p>
                )}

                {errorDetalleServicio && (
                  <p role="alert" className="pp-error">
                    {errorDetalleServicio}
                  </p>
                )}

                {detalleServicio && (
                  <div className="pp-datos-detalle">
                    {[
                      ['Servicio', detalleServicio.nombre ??
                        detalleServicio.nombre_servicio],
                      ['Estado', detalleServicio.estado_publicacion ?? detalleServicio.estado],
                      ['Descripci\u00f3n', detalleServicio.descripcion],
                      ['Precio', detalleServicio.precio_final ??
                        detalleServicio.precio],
                      ['Modalidad', detalleServicio.modalidad],
                      ['Alcance', detalleServicio.alcance],
                    ].filter(([, valor]) =>
                      valor !== undefined &&
                      valor !== null &&
                      typeof valor !== 'object'
                    ).map(([campo, valor]) => (
                      <div key={campo}>
                        <strong>{campo}</strong>
                        <p>{String(valor)}</p>
                      </div>
                    ))}
                  </div>
                )}

                

                {detalleServicio && idServicioDetalle &&
                  ['BORRADOR', 'CORRECCION_SOLICITADA'].includes(
                    detalleServicio.estado_publicacion,
                  ) && (
                    <EditarPropuesta
                      key={`${idServicioDetalle}-${detalleServicio.fecha_actualizacion ?? ''}`}
                      idServicio={idServicioDetalle}
                      servicio={detalleServicio}
                      onActualizada={async () => {
                        await consultarDetalleServicio(idServicioDetalle)
                        await cargarServicios()
                      }}
                    />
                  )}

                {detalleServicio && idServicioDetalle && (
                  <div className="pp-acciones-comerciales">
                    <h3>Gesti&oacute;n de publicaci&oacute;n</h3>
                    <p>
                      Estado:
                      {' '}
                      <strong>
                        {detalleServicio.estado_publicacion ??
                          'No informado'}
                      </strong>
                    </p>

                    {['BORRADOR', 'CORRECCION_SOLICITADA'].includes(
                      detalleServicio.estado_publicacion,
                    ) && (
                      <button
                        type="button"
                        className="pp-boton"
                        disabled={Boolean(accionServicio)}
                        onClick={() => ejecutarAccionServicio('revisar')}
                      >
                        Enviar a revisi&oacute;n
                      </button>
                    )}

                    {detalleServicio.estado_publicacion ===
                      'PEND_APROBACION_PROFESIONAL' && (
                      <div className="pp-grupo-aprobacion">
                        <button
                          type="button"
                          className="pp-boton pp-secundario"
                          disabled={cargandoVersion || Boolean(accionServicio)}
                          onClick={() =>
                            consultarVersionRevisada(idServicioDetalle)
                          }
                        >
                          {cargandoVersion
                            ? 'Consultando...'
                            : 'Consultar versi\u00f3n revisada'}
                        </button>

                        {versionRevisada && (
                          <>
                            <div className="pp-resultado-validacion">
                              <h4>Propuesta revisada por Skilly</h4>
                              <DetalleRevision revision={versionRevisada} />
                            </div>
                            <button
                              type="button"
                              className="pp-boton"
                              disabled={Boolean(accionServicio)}
                              onClick={() => ejecutarAccionServicio('aprobar')}
                            >
                              Aceptar versi&oacute;n revisada
                            </button>
                            <section className="pp-resultado-validacion" style={{ marginTop: 16 }}>
                              <h4>¿No estás de acuerdo con las condiciones finales?</h4>
                              <p>El rechazo requiere justificación. SKILLY podrá reconsiderar las condiciones una única vez; si rechazas esa segunda versión, la propuesta se cerrará sin acuerdo y conservará su historial.</p>
                              <label style={{ display: 'block', marginTop: 12 }}>
                                Motivo del rechazo *
                                <select
                                  required
                                  value={motivoCategoriaComercial}
                                  onChange={(evento) => setMotivoCategoriaComercial(evento.target.value)}
                                  style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 6 }}
                                >
                                  <option value="">Selecciona un motivo</option>
                                  <option value="TARIFA_INSUFICIENTE">Tarifa insuficiente</option>
                                  <option value="DESACUERDO_ALCANCE">Desacuerdo con el alcance</option>
                                  <option value="CONDICIONES_EJECUCION">Condiciones de ejecución</option>
                                  <option value="OTRO">Otro</option>
                                </select>
                              </label>
                              <label style={{ display: 'block', marginTop: 12 }}>
                                Explica el motivo * (10 a 600 caracteres)
                                <textarea
                                  required
                                  rows={3}
                                  minLength={10}
                                  maxLength={600}
                                  value={motivoDetalleComercial}
                                  onChange={(evento) => setMotivoDetalleComercial(evento.target.value)}
                                  placeholder="Describe por qué no puedes aceptar las condiciones propuestas."
                                  style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 6 }}
                                />
                              </label>
                              <button
                                type="button"
                                className="pp-boton pp-secundario"
                                disabled={Boolean(accionServicio) || !motivoCategoriaComercial || motivoDetalleComercial.trim().length < 10}
                                onClick={() => ejecutarAccionServicio('rechazar_comercial')}
                              >
                                Rechazar condiciones finales
                              </button>
                              <p>El rechazo no elimina el servicio. No genera una contraoferta económica ni promete contacto automático.</p>
                            </section>
                          </>
                        )}
                      </div>
                    )}

                    {['EN_REVISION', 'CERRADA_SIN_ACUERDO'].includes(detalleServicio.estado_publicacion) &&
                      Array.isArray(detalleServicio.historial_rechazos_comerciales) &&
                      detalleServicio.historial_rechazos_comerciales.length > 0 && (
                        <section className="pp-resultado-validacion">
                          <h4>Historial de decisiones comerciales</h4>
                          {detalleServicio.historial_rechazos_comerciales.map((rechazo, i) => (
                            <div key={`${rechazo.ronda}-${i}`} style={{ marginBottom: 12 }}>
                              <p><strong>Decisión {rechazo.ronda}:</strong> {rechazo.motivo_categoria}</p>
                              <p>{rechazo.observacion}</p>
                              <p>Estado: {rechazo.estado}</p>
                            </div>
                          ))}
                          {detalleServicio.estado_publicacion === 'EN_REVISION' && (
                            <p>SKILLY podrá evaluar una única reconsideración, sin obligación de cambiar el precio.</p>
                          )}
                          {detalleServicio.estado_publicacion === 'CERRADA_SIN_ACUERDO' && (
                            <p>Propuesta cerrada sin acuerdo. Su historial permanece disponible y no se publicará.</p>
                          )}
                        </section>
                      )}

                    {detalleServicio.estado_publicacion ===
                      'APROBADA_PARA_PUBLICAR' && (
                      <button
                        type="button"
                        className="pp-boton"
                        disabled={Boolean(accionServicio)}
                        onClick={() => ejecutarAccionServicio('publicar')}
                      >
                        Publicar servicio
                      </button>
                    )}

                    {errorAccionServicio && (
                      <p role="alert" className="pp-error">
                        {errorAccionServicio}
                      </p>
                    )}

                    {avisoAccionServicio && (
                      <p role="status" className="pp-exito">
                        {avisoAccionServicio}
                      </p>
                    )}
                  </div>
                )}

<button
                  type="button"
                  className="pp-boton pp-secundario"
                  onClick={cerrarDetalleServicio}
                  disabled={cargandoDetalleServicio || Boolean(accionServicio) || cargandoVersion}
                >
                  Cerrar detalle
                </button>
                </section>
              </div>,
              document.body,
            )}

            <div className="pp-modulo-grupo" hidden={moduloPortal !== 'servicios'}>
              <VentanaProfesional abierta={ventanaPortal === 'nueva-propuesta'}
                titulo="Nueva propuesta de servicio" onCerrar={cerrarVentana}>
                <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('mis-servicios')}>
                  ← Volver a Mis servicios
                </button>
                <NuevaPropuesta onCreada={async () => {
                  await cargarServicios()
                  setVentanaPortal('mis-servicios')
                }} />
              </VentanaProfesional>
            </div>

            <div className="pp-modulo-grupo" hidden={moduloPortal !== 'desarrollo'}>
              <VentanaProfesional abierta={ventanaPortal === 'centro-desarrollo'}
                titulo="Explorar y desarrollo" onCerrar={cerrarVentana}>
                <p className="pp-centro-descripcion">Consulta tus recomendaciones y accede a la disponibilidad o al catálogo público sin cambiar sus funciones originales.</p>
                <div className="pp-centro-acciones">
                  <button type="button" className="pp-opcion-seccion" onClick={() => abrirOpcion('recomendaciones')}>
                    <span className="pp-opcion-icono" aria-hidden="true">◇</span>
                    <strong>Mis recomendaciones</strong>
                    <span>Consultar recomendaciones comunicadas por Skilly</span>
                    <small>Abrir ventana →</small>
                  </button>
                  <a className="pp-opcion-seccion" href="/disponibilidad">
                    <span className="pp-opcion-icono" aria-hidden="true">▦</span>
                    <strong>Mi disponibilidad</strong>
                    <span>Administrar bloques horarios en su página independiente</span>
                    <small>Ir a disponibilidad →</small>
                  </a>
                  <a className="pp-opcion-seccion" href="/#marketplace">
                    <span className="pp-opcion-icono" aria-hidden="true">✧</span>
                    <strong>Explorar Marketplace</strong>
                    <span>Ver el catálogo público de SKILLY</span>
                    <small>Ir al catálogo →</small>
                  </a>
                </div>
              </VentanaProfesional>
              <VentanaProfesional abierta={ventanaPortal === 'recomendaciones'}
                titulo="Mis recomendaciones" onCerrar={cerrarVentana}>
                <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-desarrollo')}>
                  ← Volver a Explorar y desarrollo
                </button>
                <RecomendacionesProfesional />
              </VentanaProfesional>
            </div>

            
            <div className="pp-modulo-grupo" hidden={moduloPortal !== 'actividad'}>
              {seguimientoSeleccionado != null && (
                <VentanaProfesional abierta={ventanaPortal === 'avance'}
                  titulo={`Registrar avance de prestación #${seguimientoSeleccionado}`}
                  onCerrar={() => setVentanaPortal('seguimiento')}>
                <RegistrarAvanceProfesional
                key={seguimientoSeleccionado}
                idPrestacion={seguimientoSeleccionado}
                estadoPrestacion={
                  coordinados.find(
                    (item) =>
                      Number(item.id_prestacion) ===
                      Number(seguimientoSeleccionado),
                  )?.estado
                }
                  onRegistrado={() =>
                    cargarSeguimientoProfesional(seguimientoSeleccionado)
                  }
                />
                </VentanaProfesional>
              )}
            </div>

            <div className="pp-modulo-grupo" hidden={moduloPortal !== 'cuenta'}>
              <VentanaProfesional abierta={ventanaPortal === 'completar-perfil'}
                titulo="Crear o editar mi perfil" onCerrar={cerrarVentana}>
                <CompletarPerfilProfesional
                  onCreado={cargarPerfil}
                  onVerPerfil={() => abrirOpcion('perfil')}
                />
              </VentanaProfesional>
              <VentanaProfesional abierta={ventanaPortal === 'documentos'}
                titulo="Mis documentos profesionales" onCerrar={cerrarVentana}>
                <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-validacion')}>← Volver a Documentos y validación</button>
                <DocumentosCarga />
              </VentanaProfesional>
              <VentanaProfesional abierta={ventanaPortal === 'solicitar-validacion'}
                titulo="Estado y solicitud de validación" onCerrar={cerrarVentana}>
                <button type="button" className="pp-volver-centro" onClick={() => abrirOpcion('centro-validacion')}>← Volver a Documentos y validación</button>
                <SolicitarValidacionProfesional />
              </VentanaProfesional>
            </div>

          </>
        )}
      </main>
    </div>
  )
}

export default PortalProfesional
