import AdminNavegacion from './AdminNavegacion.jsx'
import { ReagendamientosAdministracion } from './ReagendamientosSkilly.jsx'
import ComunicarCondicionesAdministracion from './ComunicarCondicionesAdministracion.jsx'
import SeguimientoPrestacionAdministracion from './SeguimientoPrestacionAdministracion.jsx'
import AgendaPrestacionAdministracionE3 from './AgendaPrestacionAdministracionE3.jsx'
import VentanaAdministracion from './VentanaAdministracion.jsx'
import RegistroAbonoAdministracion from './RegistroAbonoAdministracion.jsx'
import GestionReversasPagoE3 from './GestionReversasPagoE3.jsx'
import { useCallback, useEffect, useState } from 'react'
import './Administracion.css'

const API = '/api'
const estadosCerrados = new Set([
  'RESUELTA', 'RESUELTO', 'CERRADA', 'CERRADO',
  'FINALIZADA', 'FINALIZADO', 'CANCELADA',
  'CANCELADO', 'RECHAZADA', 'RECHAZADO',
])

function mensajeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail
  return `La operación no se completó (HTTP ${codigo}).`
}

async function obtenerCsrf() {
  const respuesta = await fetch(`${API}/acceso/csrf/`, {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  const datos = await respuesta.json().catch(() => ({}))
  if (!respuesta.ok || !datos.csrfToken) {
    throw new Error('No se pudo obtener el token de seguridad.')
  }
  return datos.csrfToken
}

async function obtenerJson(ruta, opciones = {}) {
  const respuesta = await fetch(`${API}${ruta}`, {
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json', ...opciones.headers },
    ...opciones,
  })
  const datos = await respuesta.json().catch(() => ({}))
  if (!respuesta.ok) throw new Error(mensajeError(datos, respuesta.status))
  return datos
}


function formatoMonto(valor, moneda) {
  if (valor == null || valor === '') return 'No informado'

  const numero = Number(valor)
  if (!Number.isFinite(numero)) return String(valor)

  return new Intl.NumberFormat('es-CL', {
    minimumFractionDigits: moneda === 'CLP' ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(numero) + ' ' + (moneda || '')
}


function Administracion() {
  const [usuario, setUsuario] = useState(null)
  const [vistaGestion, setVistaGestion] = useState('solicitudes')
  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [solicitudes, setSolicitudes] = useState([])
  const [asignaciones, setAsignaciones] = useState({})
  const [seleccion, setSeleccion] = useState(null)
  const [pestana, setPestana] = useState('sin')
  const [busqueda, setBusqueda] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [asignando, setAsignando] = useState(false)
  const [coordinacion, setCoordinacion] = useState(null)
  const [cargandoCoordinacion, setCargandoCoordinacion] = useState(false)
  const [errorCoordinacion, setErrorCoordinacion] = useState('')
  const [proponiendo, setProponiendo] = useState(false)
  const [confirmandoAsociacion, setConfirmandoAsociacion] = useState(false)
  const [preparandoPrestacion, setPreparandoPrestacion] = useState(false)
  const [agendandoPrimeraReunion, setAgendandoPrimeraReunion] = useState(false)

  const [pagos, setPagos] = useState([])
  const [cargandoPagos, setCargandoPagos] = useState(false)
  const [errorPagos, setErrorPagos] = useState('')
  const [filtroPagos, setFiltroPagos] = useState('pendientes')
  const [detallePago, setDetallePago] = useState(null)
  const [cargandoDetallePago, setCargandoDetallePago] = useState(false)
  const [errorDetallePago, setErrorDetallePago] = useState('')
  const [recepcionComprobada, setRecepcionComprobada] = useState(false)
  const [observacionVerificacion, setObservacionVerificacion] = useState('')
  const [verificandoPago, setVerificandoPago] = useState(false)
  const [liberandoPago, setLiberandoPago] = useState(false)
  const [observacionLiberacion, setObservacionLiberacion] = useState('')
  const [avisoPago, setAvisoPago] = useState('')




  const cargar = useCallback(async () => {
    setCargando(true)
    setError('')
    try {
      const datos = await obtenerJson(
        '/coordinacion/administracion/solicitudes/',
      )
      const lista = Array.isArray(datos.solicitudes) ? datos.solicitudes : []
      const pares = await Promise.all(
        lista.map(async (item) => {
          try {
            const respuesta = await obtenerJson(
              `/coordinacion/administracion/solicitudes/${item.id_solicitud}/asignacion/`,
            )
            return [item.id_solicitud, {
              actual: respuesta.asignacion_actual ?? respuesta.asignacion ?? null,
              respuesta,
            }]
          } catch (fallo) {
            return [item.id_solicitud, {
              actual: null,
              error: fallo.message,
            }]
          }
        }),
      )
      setSolicitudes(lista)
      setAsignaciones(Object.fromEntries(pares))
      setSeleccion((anterior) => {
        if (!anterior) return null
        return lista.find((x) => x.id_solicitud === anterior.id_solicitud) ?? null
      })
    } catch (fallo) {
      setError(fallo.message)
      setSolicitudes([])
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    let vigente = true
    async function verificar() {
      try {
        const datos = await obtenerJson(
          '/coordinacion/administracion/solicitudes/',
        )
        if (!vigente) return
        if (Array.isArray(datos.solicitudes)) {
          const sesion = await obtenerJson('/acceso/sesion-actual/')
          if (!vigente) return
          if (sesion.usuario?.rol !== 'ADMIN_SKILLY') return
          setUsuario(sesion.usuario)
          await cargar()
        }
      } catch {
        // La pantalla de acceso se mantiene disponible.
      }
    }
    verificar()
    return () => { vigente = false }
  }, [cargar])

  useEffect(() => {
    if (!seleccion || !usuario) return undefined

    let vigente = true

    async function consultarCoordinacion() {
      setCoordinacion(null)
      setErrorCoordinacion('')
      setCargandoCoordinacion(true)

      try {
        const datos = await obtenerJson(
          `/coordinacion/administracion/solicitudes/${seleccion.id_solicitud}/coordinacion/`,
        )
        if (vigente) setCoordinacion(datos)
      } catch (fallo) {
        if (vigente) setErrorCoordinacion(fallo.message)
      } finally {
        if (vigente) setCargandoCoordinacion(false)
      }
    }

    consultarCoordinacion()

    return () => { vigente = false }
  }, [seleccion, usuario])





  const cargarPagos = useCallback(async () => {
    setCargandoPagos(true)
    setErrorPagos('')

    try {
      const datos = await obtenerJson('/pagos/administracion/')

      if (!Array.isArray(datos)) {
        throw new Error('La API devolvio un listado de pagos no valido.')
      }

      setPagos(datos)
    } catch (fallo) {
      setErrorPagos(fallo.message)
      setPagos([])
    } finally {
      setCargandoPagos(false)
    }
  }, [])

  useEffect(() => {
    if (!usuario) return undefined

    let vigente = true

    async function consultarPagosIniciales() {
      try {
        const datos = await obtenerJson('/pagos/administracion/')

        if (!vigente) return

        if (!Array.isArray(datos)) {
          throw new Error('La API devolvio un listado de pagos no valido.')
        }

        setPagos(datos)
        setErrorPagos('')
      } catch (fallo) {
        if (vigente) {
          setErrorPagos(fallo.message)
          setPagos([])
        }
      }
    }

    consultarPagosIniciales()

    return () => { vigente = false }
  }, [usuario])



  async function verificarTransferencia() {
    const pago = detallePago?.pago
    if (!pago || verificandoPago || !recepcionComprobada) return

    const pendiente =
      pago.metodo_pago === 'TRANSFERENCIA' &&
      pago.estado_pago === 'PENDIENTE_VERIFICACION' &&
      pago.estado_verificacion === 'PENDIENTE'

    if (!pendiente) {
      setErrorDetallePago('El pago no admite verificación.')
      return
    }

    if (!observacionVerificacion.trim()) {
      setErrorDetallePago('Debes registrar una observación administrativa.')
      return
    }

    const confirmado = window.confirm(
      `Confirma que Skilly comprobó la recepción efectiva ` +
      `del dinero del pago #${pago.id_pago}. ` +
      'Esta operación retendrá el pago y activará la reserva. ' +
      'No contratará automáticamente la prestación.'
    )

    if (!confirmado) return

    setVerificandoPago(true)
    setErrorDetallePago('')
    setAvisoPago('')

    try {
      const token = await obtenerCsrf()

      const datos = await obtenerJson(
        `/pagos/administracion/${pago.id_pago}/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': token,
          },
          body: JSON.stringify({
            accion: 'VERIFICAR_TRANSFERENCIA',
            observacion: observacionVerificacion.trim(),
          }),
        },
      )

      if (
        datos.pago?.estado_pago !== 'RETENIDO' ||
        datos.pago?.estado_verificacion !== 'VERIFICADO'
      ) {
        throw new Error('No se confirmó el estado del pago.')
      }

      const actualizado = await obtenerJson(
        `/pagos/administracion/${pago.id_pago}/`,
      )

      setDetallePago(actualizado)
      setRecepcionComprobada(false)
      setObservacionVerificacion('')
      setAvisoPago('Transferencia verificada administrativamente.')
      await cargarPagos()
    } catch (fallo) {
      setErrorDetallePago(fallo.message)
    } finally {
      setVerificandoPago(false)
    }
  }

  async function liberarPagoProfesional() {
    const pago = detallePago?.pago
    if (!pago || liberandoPago || verificandoPago) return

    const idPago = Number(pago.id_pago)
    if (!Number.isSafeInteger(idPago) || idPago <= 0) {
      setErrorDetallePago('El identificador del pago no es válido.')
      return
    }

    if (
      pago.estado_pago !== 'RETENIDO' ||
      pago.estado_verificacion !== 'VERIFICADO'
    ) {
      setErrorDetallePago('Solo se pueden liberar pagos verificados y retenidos.')
      return
    }

    const confirmado = window.confirm(
      `¿Confirmas liberar el pago #${idPago} al profesional?\n\n` +
      `Neto del profesional: ${formatoMonto(pago.monto_neto_profesional, pago.moneda)}.\n` +
      `Comisión de SKILLY: ${formatoMonto(pago.monto_comision, pago.moneda)}.\n\n` +
      'Se registrará la liberación y quedará constancia en el historial. ' +
      'El servidor comprobará las condiciones pendientes antes de autorizarla.'
    )

    if (!confirmado) return

    setLiberandoPago(true)
    setErrorDetallePago('')
    setAvisoPago('')

    try {
      const csrfToken = await obtenerCsrf()
      const respuesta = await obtenerJson(
        `/pagos/administracion/${idPago}/liberar/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            accion: 'LIBERAR_PAGO',
            observacion: observacionLiberacion.trim(),
          }),
        },
      )

      if (respuesta.pago?.estado_pago !== 'LIBERADO') {
        throw new Error('La respuesta del servidor no confirmó la liberación.')
      }

      // Reflejar el resultado confirmado sin esperar otra petición.
      setDetallePago((anterior) => anterior
        ? { ...anterior, pago: respuesta.pago }
        : anterior
      )
      setPagos((anteriores) => anteriores.map((item) =>
        Number(item.id_pago) === idPago ? respuesta.pago : item
      ))
      setObservacionLiberacion('')
      setAvisoPago('Pago liberado correctamente al profesional.')

      // Volver a consultar para mostrar la nueva entrada del historial.
      try {
        const actualizado = await obtenerJson(`/pagos/administracion/${idPago}/`)
        if (!actualizado.pago || !Array.isArray(actualizado.historial)) {
          throw new Error('Respuesta de historial no válida.')
        }
        setDetallePago(actualizado)
      } catch {
        setErrorDetallePago(
          'El pago quedó liberado, pero no se pudo actualizar su historial. ' +
          'Cierra el detalle y vuelve a abrirlo para consultar los movimientos.'
        )
      }
      await cargarPagos()
    } catch (fallo) {
      setErrorDetallePago(fallo.message)
    } finally {
      setLiberandoPago(false)
    }
  }

  async function consultarDetallePago(idPago) {
    if (!Number.isSafeInteger(idPago) || idPago <= 0) {
      setErrorDetallePago('Identificador de pago no valido.')
      return
    }

    setRecepcionComprobada(false)
    setObservacionVerificacion('')
    setObservacionLiberacion('')
    setAvisoPago('')
    setCargandoDetallePago(true)
    setErrorDetallePago('')
    setDetallePago(null)

    try {
      const datos = await obtenerJson(
        `/pagos/administracion/${idPago}/`,
      )

      if (!datos.pago || !Array.isArray(datos.historial)) {
        throw new Error('La respuesta del detalle de pago no es valida.')
      }

      setDetallePago(datos)
    } catch (fallo) {
      setErrorDetallePago(fallo.message)
    } finally {
      setCargandoDetallePago(false)
    }
  }


  async function agendarPrimeraReunion() {
    const prestacion = coordinacion?.prestacion

    if (!seleccion || !prestacion || agendandoPrimeraReunion) {
      return
    }

    const pagoValido = pagos.some((pago) =>
      Number(pago.id_prestacion) === Number(prestacion.id_prestacion) &&
      pago.estado_pago === 'RETENIDO' &&
      pago.estado_verificacion === 'VERIFICADO'
    )

    const reservaValida = (coordinacion.reservas ?? []).some(
      (reserva) =>
        reserva.estado === 'ACTIVA' &&
        reserva.disponibilidad?.estado === 'RESERVADA'
    )

    const reunionExistente = (coordinacion.reuniones ?? []).some(
      (reunion) => reunion.estado === 'AGENDADA'
    )

    if (
      prestacion.estado !== 'PENDIENTE_CONTRATACION' ||
      !pagoValido ||
      !reservaValida ||
      reunionExistente
    ) {
      setErrorCoordinacion(
        'No se cumplen las condiciones para agendar la primera reunión.'
      )
      return
    }

    const confirmado = window.confirm(
      `¿Confirmas agendar la primera reunión de la ` +
      `prestación #${prestacion.id_prestacion}? ` +
      'Se utilizará el horario ya reservado. ' +
      'Si el backend valida todas las condiciones, ' +
      'la prestación pasará a CONTRATADA.'
    )

    if (!confirmado) return

    setAgendandoPrimeraReunion(true)
    setErrorCoordinacion('')
    setAviso('')

    try {
      const csrfToken = await obtenerCsrf()

      const resultado = await obtenerJson(
        `/coordinacion/administracion/prestaciones/${prestacion.id_prestacion}/agenda/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            accion: 'AGENDAR_PRIMERA_REUNION',
          }),
        },
      )

      if (
        resultado.prestacion_contratada !== true ||
        resultado.prestacion?.estado !== 'CONTRATADA' ||
        resultado.reunion?.estado !== 'AGENDADA'
      ) {
        throw new Error(
          'La respuesta requiere revisión administrativa.'
        )
      }

      const actualizado = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${seleccion.id_solicitud}/coordinacion/`,
      )

      setCoordinacion(actualizado)
      setAviso(
        'Primera reunión agendada. Prestación CONTRATADA.'
      )
    } catch (fallo) {
      setErrorCoordinacion(fallo.message)
    } finally {
      setAgendandoPrimeraReunion(false)
    }
  }

  async function prepararPrestacion(idProfesional) {
    if (!seleccion || preparandoPrestacion || !coordinacion) return

    if (!Number.isSafeInteger(idProfesional) || idProfesional <= 0) {
      setErrorCoordinacion(
        'No se pudo identificar al profesional asociado.'
      )
      return
    }

    const id = seleccion.id_solicitud

    const aceptado = window.confirm(
      `Confirmas preparar la prestacion de la solicitud #${id} para el profesional #${idProfesional}? Permanecera pendiente de contratacion y no confirma pagos.`
    )

    if (!aceptado) return

    setPreparandoPrestacion(true)
    setErrorCoordinacion('')
    setAviso('')

    try {
      const csrfToken = await obtenerCsrf()

      const datos = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${id}/profesionales/${idProfesional}/preparar-prestacion/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({}),
        },
      )

      if (datos.prestacion?.estado !== 'PENDIENTE_CONTRATACION') {
        throw new Error('La API no confirmo la preparacion.')
      }

      const actualizado = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${id}/coordinacion/`,
      )

      setCoordinacion(actualizado)
      setAviso('Prestacion preparada. Sigue pendiente de contratacion.')
    } catch (fallo) {
      setErrorCoordinacion(fallo.message)
    } finally {
      setPreparandoPrestacion(false)
    }
  }

  async function confirmarAsociacion(idProfesional) {
    if (!seleccion || confirmandoAsociacion || proponiendo) return

    if (!Number.isSafeInteger(idProfesional) || idProfesional <= 0) {
      setErrorCoordinacion(
        'No se pudo identificar al profesional asociado.'
      )
      return
    }

    const id = seleccion.id_solicitud

    const aceptado = window.confirm(
      `Confirmas la asociacion del profesional #${idProfesional} con la solicitud #${id}? Esta accion no confirma pagos ni contrataciones.`
    )

    if (!aceptado) return

    setConfirmandoAsociacion(true)
    setErrorCoordinacion('')
    setAviso('')

    try {
      const csrfToken = await obtenerCsrf()

      const datos = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${id}/asociaciones/${idProfesional}/confirmar/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({}),
        },
      )

      if (datos.asociacion?.estado !== 'ACEPTADO') {
        throw new Error('La API no confirmo la asociacion.')
      }

      const actualizado = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${id}/coordinacion/`,
      )

      setCoordinacion(actualizado)
      setAviso('Asociacion profesional confirmada correctamente.')
    } catch (fallo) {
      setErrorCoordinacion(fallo.message)
    } finally {
      setConfirmandoAsociacion(false)
    }
  }

  async function proponerAsociacion() {
    if (!seleccion || proponiendo || !coordinacion) return

    const id = seleccion.id_solicitud

    const confirmado = window.confirm(
      `Confirmas la propuesta de asociacion profesional para la solicitud #${id}? No confirma pago ni contratacion.`
    )

    if (!confirmado) return

    setProponiendo(true)
    setErrorCoordinacion('')
    setAviso('')

    try {
      const csrfToken = await obtenerCsrf()

      const datos = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${id}/asociaciones/proponer/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({}),
        },
      )

      if (datos.asociacion?.estado !== 'PENDIENTE') {
        throw new Error('La API no confirmo la propuesta.')
      }

      const actualizado = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${id}/coordinacion/`,
      )

      setCoordinacion(actualizado)
      setAviso('Asociacion profesional propuesta correctamente.')
    } catch (fallo) {
      setErrorCoordinacion(fallo.message)
    } finally {
      setProponiendo(false)
    }
  }

  async function iniciarSesion(evento) {
    evento.preventDefault()
    setCargando(true)
    setError('')
    setAviso('')
    try {
      const csrfToken = await obtenerCsrf()
      const datos = await obtenerJson('/acceso/iniciar-sesion/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          correo: correo.trim(),
          contrasena,
        }),
      })
      setContrasena('')
      if (datos.usuario?.rol !== 'ADMIN_SKILLY') {
        throw new Error('Esta cuenta no tiene permisos de administración Skilly.')
      }
      setUsuario(datos.usuario)
      setAviso('Sesión administrativa iniciada.')
      await cargar()
    } catch (fallo) {
      setContrasena('')
      setError(fallo.message)
    } finally {
      setCargando(false)
    }
  }

  async function autoasignar(solicitud) {
    if (asignando || !solicitud) return

    const id = solicitud.id_solicitud

    if (!window.confirm(
      `?Confirmas que deseas asumir la solicitud #${id} como responsable interno?`
    )) return

    setAsignando(true)
    setError('')
    setAviso('')

    try {
      const csrfToken = await obtenerCsrf()
      const datos = await obtenerJson(
        `/coordinacion/administracion/solicitudes/${id}/asignacion/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({ modo: 'AUTOASIGNAR' }),
        },
      )

      if (!datos.asignacion || datos.asignacion.estado !== 'ACTIVA') {
        throw new Error('La API no confirmó la asignación.')
      }

      setAsignaciones((anteriores) => ({
        ...anteriores,
        [id]: {
          actual: datos.asignacion,
          respuesta: datos,
        },
      }))

      setAviso(`Solicitud #${id} asignada correctamente.`)
      setPestana('gestion')
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setAsignando(false)
    }
  }

  async function cerrarSesion() {
    setError('')
    try {
      const csrfToken = await obtenerCsrf()
      await obtenerJson('/acceso/cerrar-sesion/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
      })
      setUsuario(null)
      setSolicitudes([])
      setAsignaciones({})
      setSeleccion(null)
      setPagos([])
      setErrorPagos('')
      setDetallePago(null)
      setErrorDetallePago('')
      setAviso('')
    } catch (fallo) {
      setError(fallo.message)
    }
  }

  function responsable(item) {
    return asignaciones[item.id_solicitud]?.actual?.responsable ?? null
  }

  function cerrada(item) {
    return estadosCerrados.has(String(item.estado ?? '').toUpperCase())
  }


  const pagosVisibles = pagos.filter((pago) => {
    const pendiente =
      pago.metodo_pago === 'TRANSFERENCIA' &&
      pago.estado_pago === 'PENDIENTE_VERIFICACION' &&
      pago.estado_verificacion === 'PENDIENTE'

    if (filtroPagos === 'pendientes') return pendiente
    if (filtroPagos === 'verificados') {
      return pago.estado_verificacion === 'VERIFICADO'
    }

    return true
  })

  const visibles = solicitudes.filter((item) => {
    const asignacion = asignaciones[item.id_solicitud]
    const actual = asignacion?.actual
    const idResponsable = actual?.responsable?.id_usuario
    const esMia = usuario?.id_usuario != null &&
      String(idResponsable) === String(usuario.id_usuario)
    const sinAsignar = !actual && !asignacion?.error &&
      String(item.estado ?? '').toUpperCase() !== 'COORDINADA' 

    const coincide =
      pestana === 'todas' ||
      (pestana === 'sin' && sinAsignar && !cerrada(item)) ||
      (pestana === 'mias' && esMia && !cerrada(item)) ||
      (pestana === 'gestion' && Boolean(actual) && !cerrada(item)) ||
      (pestana === 'cerradas' && cerrada(item))

    const texto = [
      item.id_solicitud,
      item.empresa?.nombre_organizacion,
      item.servicio?.nombre,
      item.objetivo,
      item.estado,
    ].join(' ').toLowerCase()

    return coincide && texto.includes(busqueda.toLowerCase().trim())
  })

  return (
    <div className="adm-pagina">
      <header className="adm-header">
        <a href="/" className="adm-logo"><span className="adm-estrella">✦</span> Skilly</a>
        <nav>
          <a href="/#marketplace">Marketplace</a>
          <a href="/seguimiento">Seguimiento</a>
          {usuario && <button type="button" onClick={cerrarSesion}>Cerrar sesión</button>}
        </nav>
      </header>

      <AdminNavegacion activo="solicitudes" />

      <main className="adm-contenedor">
        <div className="adm-intro">
          <span className="adm-eyebrow">BACK-OFFICE / SKILLY LATAM</span>
          <h1>Gestión de solicitudes</h1>
          <p>Control interno de solicitudes empresariales y responsables administrativos.</p>
        </div>

        {error && <div className="adm-error" role="alert">{error}</div>}
        {aviso && <div className="adm-aviso">{aviso}</div>}

        {!usuario ? (
          <section className="adm-login">
            <span className="adm-eyebrow">ACCESO RESTRINGIDO</span>
            <h2>Ingreso administrativo</h2>
            <p>Solo cuentas internas con rol ADMIN_SKILLY.</p>
            <form onSubmit={iniciarSesion}>
              <label>Correo institucional
                <input type="email" value={correo}
                  onChange={(e) => setCorreo(e.target.value)}
                  autoComplete="username" required />
              </label>
              <label>Contraseña
                <input type="password" value={contrasena}
                  onChange={(e) => setContrasena(e.target.value)}
                  autoComplete="current-password" required />
              </label>
              <button type="submit" disabled={cargando}>
                {cargando ? 'Ingresando...' : 'Ingresar al panel'}
              </button>
            </form>
          </section>
        ) : (
          <>
            <ReagendamientosAdministracion />
            <section className="adm-resumen">
              <div><span>Solicitudes registradas</span><strong>{solicitudes.length}</strong></div>
              <div><span>Sin asignar</span><strong>{solicitudes.filter(
                (x) => !asignaciones[x.id_solicitud]?.actual &&
                  !asignaciones[x.id_solicitud]?.error && !cerrada(x) &&
                  String(x.estado ?? '').toUpperCase() !== 'COORDINADA',
              ).length}</strong></div>
              <div><span>En gestión</span><strong>{solicitudes.filter(
                (x) => asignaciones[x.id_solicitud]?.actual && !cerrada(x),
              ).length}</strong></div>
            </section>


            <nav className="adm-accesos-gestion" aria-label="Secciones de gestión de solicitudes">
              <button type="button" className={`adm-acceso-gestion${vistaGestion === 'solicitudes' ? ' activa' : ''}`}
                aria-pressed={vistaGestion === 'solicitudes'} onClick={() => setVistaGestion('solicitudes')}>
                <span className="adm-acceso-icono" aria-hidden="true">▤</span>
                <strong>Solicitudes empresariales</strong>
                <span>Coordinación, asignaciones y contratación</span>
              </button>
              <button type="button" className={`adm-acceso-gestion${vistaGestion === 'pagos' ? ' activa' : ''}`}
                aria-pressed={vistaGestion === 'pagos'} onClick={() => {setVistaGestion('pagos'); void cargarPagos()}}>
                <span className="adm-acceso-icono" aria-hidden="true">$</span>
                <strong>Pagos y transferencias</strong>
                <span>Verificación, retenciones e historial</span>
              </button>
            </nav>

            <section className="adm-panel" hidden={vistaGestion !== 'pagos'}>
              <div className="adm-panel-header">
                <div>
                  <span className="adm-eyebrow">
                    CONTROL ECONÓMICO
                  </span>
                  <h2>Pagos y transferencias</h2>
                </div>
                <button
                  type="button"
                  className="adm-secundario"
                  onClick={cargarPagos}
                  disabled={cargandoPagos}
                >
                  {cargandoPagos ? 'Consultando...' : '↻ Recargar pagos'}
                </button>
              </div>

              <p className="adm-nota">
                Las transferencias informadas requieren verificación
                administrativa. Solo administradores autorizados pueden verificar transferencias tras comprobar la recepción efectiva del dinero. La contratación requiere además agendar la primera reunión.
              </p>

              {errorPagos && (
                <div className="adm-error" role="alert">
                  No se pudieron consultar los pagos: {errorPagos}
                </div>
              )}


              <div className="adm-pestanas">
                {[
                  ['pendientes', 'Pendientes de verificación'],
                  ['verificados', 'Verificados'],
                  ['todos', 'Todos'],
                ].map(([clave, titulo]) => (
                  <button
                    key={clave}
                    type="button"
                    className={filtroPagos === clave ? 'activa' : ''}
                    onClick={() => setFiltroPagos(clave)}
                  >
                    {titulo}
                  </button>
                ))}
              </div>

              {!errorPagos && !cargandoPagos && pagosVisibles.length === 0 && (
                <p className="adm-vacio">
                  {filtroPagos === 'pendientes'
                    ? 'No hay transferencias pendientes de verificación.'
                    : filtroPagos === 'verificados'
                      ? 'No hay pagos verificados.'
                      : 'Todavía no existen pagos registrados.'}
                </p>
              )}

              {!errorPagos && pagosVisibles.length > 0 && (
                <div className="adm-lista">
                  {pagosVisibles.map((pago) => (
                    <article
                      key={pago.id_pago}
                      className="adm-item"
                      style={{ cursor: 'default' }}
                    >
                      <span className="adm-item-cuerpo">
                        <strong>
                          Pago #{pago.id_pago} | Prestación #{pago.id_prestacion}
                        </strong>

                        <span>
                          Total: {formatoMonto(pago.monto_total, pago.moneda)}
                        </span>

                        <span>
                          Comisión: {formatoMonto(pago.monto_comision, pago.moneda)}
                          {' | '}
                          Neto profesional: {formatoMonto(
                            pago.monto_neto_profesional,
                            pago.moneda,
                          )}
                        </span>

                        <span>
                          Método: {pago.metodo_pago || 'No informado'}
                          {' | '}
                          Verificación: {pago.estado_verificacion || 'No informada'}
                        </span>
                      </span>

                      <span className="adm-estado">
                        {pago.estado_pago}
                      </span>

                      <button
                        type="button"
                        className="adm-secundario"
                        disabled={cargandoDetallePago}
                        onClick={() => consultarDetallePago(pago.id_pago)}
                      >
                        Ver detalle
                      </button>
                    </article>
                  ))}
                </div>
              )}

              {(cargandoDetallePago || errorDetallePago || detallePago) && (
                <VentanaAdministracion abierta titulo="Detalle e historial del pago"
                  bloqueado={verificandoPago || liberandoPago}
                  onCerrar={() => { setDetallePago(null); setErrorDetallePago(''); setCargandoDetallePago(false) }}>
                <div className="adm-detalle-pago">
                  <div className="adm-panel-header">
                    <h3>Detalle e historial del pago</h3>
                    <button
                      type="button"
                      className="adm-secundario"
                      onClick={() => {
                        setDetallePago(null)
                        setErrorDetallePago('')
                      }}
                      disabled={verificandoPago || liberandoPago}
                    >
                      Cerrar detalle
                    </button>
                  </div>

                  {cargandoDetallePago && (
                    <p>Consultando detalle del pago...</p>
                  )}

                  {errorDetallePago && (
                    <div className="adm-error" role="alert">
                      {errorDetallePago}
                    </div>
                  )}

                  {detallePago && (
                    <>
                      <p>
                        <strong>Pago #{detallePago.pago.id_pago}</strong>
                        {' | '}
                        Prestación #{detallePago.pago.id_prestacion}
                      </p>
                      <p>
                        Estado: {detallePago.pago.estado_pago}
                        {' | '}
                        Verificación: {detallePago.pago.estado_verificacion}
                      </p>
                      <p>
                        Total: {formatoMonto(
                          detallePago.pago.monto_total,
                          detallePago.pago.moneda,
                        )}
                      </p>
                      <p>
                        Comisión: {formatoMonto(
                          detallePago.pago.monto_comision,
                          detallePago.pago.moneda,
                        )}
                        {' | '}
                        Neto profesional: {formatoMonto(
                          detallePago.pago.monto_neto_profesional,
                          detallePago.pago.moneda,
                        )}
                      </p>
                      <p>
                        Referencia: {
                          detallePago.pago.referencia_transaccion || 'No informada'
                        }
                      </p>
                      <section
                        aria-label="Comprobante de transferencia"
                        style={{
                          display: 'grid',
                          gap: 12,
                          margin: '20px 0',
                          padding: '18px 20px',
                          border: '1px solid #d7e4dc',
                          borderRadius: 14,
                          background: '#f7faf8',
                        }}
                      >
                        <strong>Comprobante de transferencia</strong>
                        {detallePago.pago.comprobante_transferencia?.startsWith('comprobantes_transferencia_privados/') ? (
                          <a
                            className="adm-accion"
                            href={`/api/pagos/administracion/${detallePago.pago.id_pago}/comprobante/`}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: 10,
                              width: 'fit-content',
                              minHeight: 46,
                              padding: '12px 20px',
                              border: '1px solid #285845',
                              borderRadius: 11,
                              background: '#285845',
                              color: '#fff',
                              font: 'inherit',
                              fontWeight: 700,
                              textDecoration: 'none',
                              boxSizing: 'border-box',
                            }}
                          >
                            <span aria-hidden="true">↓</span>
                            Descargar comprobante adjunto
                          </a>
                        ) : (
                          <span>{detallePago.pago.comprobante_transferencia || 'No informado'}</span>
                        )}
                      </section>

                      {detallePago.pago.metodo_pago === 'TRANSFERENCIA' &&
                        detallePago.pago.estado_pago === 'PENDIENTE_VERIFICACION' &&
                        detallePago.pago.estado_verificacion === 'PENDIENTE' && (
                          <div
                            className="adm-verificacion"
                            style={{
                              display: 'grid',
                              gap: 18,
                              marginTop: 22,
                              padding: '20px',
                              border: '1px solid #d7e4dc',
                              borderRadius: 14,
                            }}
                          >
                            <h4 style={{ margin: 0 }}>Verificación administrativa</h4>

                            <p className="adm-nota" style={{ margin: 0 }}>
                              El comprobante informado no acredita por sí solo
                              la recepción del dinero. Confirma esta operación
                              solamente después de verificar la transferencia
                              mediante los registros financieros de Skilly.
                            </p>

                            <label style={{ display: 'grid', gap: 9, fontWeight: 600 }}>
                              Observación administrativa
                              <textarea
                                style={{
                                  display: 'block',
                                  width: '100%',
                                  minHeight: 110,
                                  padding: 12,
                                  border: '1px solid #b9d2c4',
                                  borderRadius: 10,
                                  font: 'inherit',
                                  boxSizing: 'border-box',
                                  resize: 'vertical',
                                }}
                                value={observacionVerificacion}
                                onChange={(evento) => setObservacionVerificacion(
                                  evento.target.value
                                )}
                                rows={3}
                                placeholder="Indica cómo se comprobó la recepción"
                              />
                            </label>

                            <label
                              style={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: 12,
                                padding: '14px 16px',
                                border: '1px solid #d7e4dc',
                                borderRadius: 10,
                                background: '#f7faf8',
                                lineHeight: 1.5,
                                cursor: 'pointer',
                              }}
                            >
                              <input
                                style={{ marginTop: 4, flexShrink: 0 }}
                                type="checkbox"
                                checked={recepcionComprobada}
                                onChange={(evento) => setRecepcionComprobada(
                                  evento.target.checked
                                )}
                              />
                              <span>
                                Confirmo que comprobé la recepción efectiva
                                del dinero en los registros de Skilly.
                              </span>
                            </label>

                            <button
                              type="button"
                              className="adm-accion"
                              style={{
                                justifySelf: 'start',
                                minHeight: 44,
                                padding: '11px 20px',
                              }}
                              onClick={verificarTransferencia}
                              disabled={
                                verificandoPago ||
                                !recepcionComprobada ||
                                !observacionVerificacion.trim()
                              }
                            >
                              {verificandoPago
                                ? 'Verificando...'
                                : 'Verificar transferencia'}
                            </button>
                          </div>
                        )}

                      {detallePago.pago.estado_pago === 'RETENIDO' &&
                        detallePago.pago.estado_verificacion === 'VERIFICADO' && (
                          <section
                            aria-label="Liberación administrativa del pago"
                            style={{
                              display: 'grid',
                              gap: 16,
                              margin: '20px 0',
                              padding: '20px',
                              border: '1px solid #d7e4dc',
                              borderRadius: 14,
                              background: '#f7faf8',
                            }}
                          >
                            <h4 style={{ margin: 0 }}>Liberación del pago al profesional</h4>
                            <p style={{ margin: 0, lineHeight: 1.5 }}>
                              Pago retenido y verificado. Neto a liberar:{' '}
                              <strong>
                                {formatoMonto(
                                  detallePago.pago.monto_neto_profesional,
                                  detallePago.pago.moneda,
                                )}
                              </strong>
                              . Comisión de SKILLY:{' '}
                              {formatoMonto(
                                detallePago.pago.monto_comision,
                                detallePago.pago.moneda,
                              )}.
                            </p>
                            <label style={{ display: 'grid', gap: 9, fontWeight: 600 }}>
                              Observación administrativa (opcional)
                              <textarea
                                value={observacionLiberacion}
                                onChange={(evento) => setObservacionLiberacion(evento.target.value)}
                                rows={3}
                                placeholder="Indica una observación para el historial"
                                disabled={liberandoPago}
                                style={{
                                  width: '100%',
                                  minHeight: 90,
                                  padding: 12,
                                  border: '1px solid #b9d2c4',
                                  borderRadius: 10,
                                  font: 'inherit',
                                  boxSizing: 'border-box',
                                  resize: 'vertical',
                                }}
                              />
                            </label>
                            <button
                              type="button"
                              className="adm-accion"
                              onClick={liberarPagoProfesional}
                              disabled={liberandoPago || verificandoPago}
                              style={{
                                justifySelf: 'start',
                                minHeight: 44,
                                padding: '11px 20px',
                              }}
                            >
                              {liberandoPago
                                ? 'Registrando liberación...'
                                : 'Liberar pago al profesional'}
                            </button>
                          </section>
                        )}

                      {detallePago.pago.estado_pago === 'LIBERADO' && (
                        <div className="adm-aviso" role="status" style={{ margin: '18px 0' }}>
                          Pago liberado al profesional.
                          {detallePago.pago.fecha_liberacion && (
                            <span style={{ display: 'block', marginTop: 6 }}>
                              Fecha de liberación:{' '}
                              {new Date(detallePago.pago.fecha_liberacion).toLocaleString('es-CL')}
                            </span>
                          )}
                        </div>
                      )}

                      {avisoPago && detallePago.pago.estado_pago !== 'LIBERADO' && (
                        <div className="adm-aviso" role="status">
                          {avisoPago}
                        </div>
                      )}

                      {detallePago.pago.estado_pago === 'LIBERADO' && (
                        <RegistroAbonoAdministracion pago={detallePago.pago} />
                      )}
                      <GestionReversasPagoE3
                        pago={detallePago.pago}
                        alActualizar={() => {
                          void consultarDetallePago(detallePago.pago.id_pago)
                          void cargarPagos()
                        }}
                      />
                      <h4>Historial de estados</h4>
                      {detallePago.historial.length === 0 ? (
                        <p className="adm-vacio">
                          No existen cambios de estado registrados.
                        </p>
                      ) : (
                        <div className="adm-lista">
                          {detallePago.historial.map((evento) => (
                            <div
                              key={evento.id_historial_pago}
                              className="adm-item"
                            >
                              <span className="adm-item-cuerpo">
                                <strong>
                                  {evento.estado_anterior || 'INICIAL'}
                                  {' | '}
                                  {evento.estado_nuevo}
                                </strong>
                                <span>
                                  {evento.fecha_cambio
                                    ? new Date(
                                      evento.fecha_cambio,
                                    ).toLocaleString('es-CL')
                                    : 'Sin fecha'}
                                </span>
                                <span>
                                  {evento.observacion || 'Sin observaciones'}
                                </span>
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
                </VentanaAdministracion>
              )}
            </section>

            <section className="adm-panel" hidden={vistaGestion !== 'solicitudes'}>
              <div className="adm-panel-header">
                <div>
                  <span className="adm-eyebrow">BANDEJA ADMINISTRATIVA</span>
                  <h2>Solicitudes empresariales</h2>
                </div>
                <button type="button" className="adm-secundario"
                  onClick={cargar} disabled={cargando}>
                  {cargando ? 'Consultando...' : '↻ Recargar bandeja'}
                </button>
              </div>

              <div className="adm-pestanas">
                {[
                  ['sin', 'Sin asignar'],
                  ['mias', 'Asignadas a mí'],
                  ['gestion', 'En gestión'],
                  ['cerradas', 'Resueltas / cerradas'],
                  ['todas', 'Todas'],
                ].map(([clave, titulo]) => (
                  <button key={clave} type="button"
                    className={pestana === clave ? 'activa' : ''}
                    onClick={() => setPestana(clave)}>
                    {titulo}
                  </button>
                ))}
              </div>

              <input className="adm-busqueda" value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar empresa, servicio, objetivo o estado..."
                aria-label="Buscar solicitudes" />

              {visibles.length === 0 ? (
                <p className="adm-vacio">No hay solicitudes en esta vista.</p>
              ) : (
                <div className="adm-lista">
                  {visibles.map((item) => (
                    <button type="button" className="adm-item"
                      key={item.id_solicitud}
                      onClick={() => setSeleccion(item)}>
                      <span className="adm-item-cuerpo">
                        <strong>#{item.id_solicitud} · {item.empresa?.nombre_organizacion || 'Empresa'}</strong>
                        <small>{item.servicio?.nombre || 'Servicio sin especificar'}</small>
                        <small>{item.objetivo}</small>
                        {asignaciones[item.id_solicitud]?.error
                          ? <small>Asignación: no disponible</small>
                          : <small>Responsable: {responsable(item)?.correo || 'Sin asignar'}</small>}
                      </span>
                      <span className="adm-estado">{item.estado}</span>
                    </button>
                  ))}
                </div>
              )}
            </section>

            {seleccion && (
              <VentanaAdministracion abierta titulo={`Solicitud empresarial #${seleccion.id_solicitud}`}
                bloqueado={asignando || proponiendo || confirmandoAsociacion || preparandoPrestacion || agendandoPrimeraReunion}
                onCerrar={() => setSeleccion(null)}>
              <section className="adm-panel adm-detalle">
                <div className="adm-panel-header">
                  <div>
                    <span className="adm-eyebrow">DETALLE EMPRESARIAL</span>
                    <h2>Solicitud #{seleccion.id_solicitud}</h2>
                  </div>
                  <button className="adm-secundario" type="button"
                    onClick={() => setSeleccion(null)}>Cerrar detalle</button>
                </div>
                <div className="adm-datos">
                  <div><small>Empresa</small><strong>{seleccion.empresa?.nombre_organizacion || 'No indicada'}</strong></div>
                  <div><small>Servicio</small><strong>{seleccion.servicio?.nombre || 'No indicado'}</strong></div>
                  <div><small>Contacto</small><strong>{seleccion.contacto?.nombre || 'No indicado'}</strong></div>
                  <div><small>Correo</small><strong>{seleccion.contacto?.correo || 'No indicado'}</strong></div>
                  <div><small>Estado</small><strong>{seleccion.estado}</strong></div>
                  <div><small>Responsable interno</small><strong>{responsable(seleccion)?.correo || 'Sin asignar'}</strong></div>
                </div>
                <section className="adm-coordinacion">
                  <h3>Coordinación y contratación</h3>
                  <p>Consulta administrativa del avance de esta solicitud.</p>

                  {cargandoCoordinacion && (
                    <p>Consultando coordinación...</p>
                  )}

                  {errorCoordinacion && (
                    <p role="alert">
                      No se pudo consultar la coordinación: {errorCoordinacion}
                    </p>
                  )}

                  {coordinacion && (
                    <>
                      <div className="adm-datos">
                        <div>
                          <small>Profesionales asociados</small>
                          <strong>{coordinacion.asociaciones?.length ?? 0}</strong>
                        </div>
                        <div>
                          <small>Reservas registradas</small>
                          <strong>{coordinacion.reservas?.length ?? 0}</strong>
                        </div>
                        <div>
                          <small>Reuniones registradas</small>
                          <strong>{coordinacion.reuniones?.length ?? 0}</strong>
                        </div>
                        <div>
                          <small>Eventos de coordinación</small>
                          <strong>{coordinacion.historial_coordinacion?.length ?? 0}</strong>
                        </div>
                        <div>
                          <small>Prestación</small>
                          <strong>
                            {coordinacion.prestacion?.estado || 'No preparada'}
                          </strong>
                        </div>
                      </div>


                      {seleccion.estado === 'RECIBIDA' &&
                        (coordinacion.asociaciones?.length ?? 0) === 0 &&
                        (coordinacion.reservas ?? []).some(
                          (reserva) => (
                            reserva.estado === 'PENDIENTE_PAGO' ||
                            reserva.estado === 'ACTIVA'
                          ),
                        ) &&
                        !coordinacion.prestacion && (
                          <button
                            type="button"
                            className="adm-accion"
                            disabled={proponiendo}
                            onClick={proponerAsociacion}
                          >
                            {proponiendo
                              ? 'Registrando propuesta...'
                              : 'Proponer asociación'}
                          </button>
                        )}

                      {(coordinacion.asociaciones ?? []).map(
                        (asociacion, indice) => (
                          <div key={indice}>
                            <p>
                              Profesional asociado:
                              {' '}{asociacion.estado}
                            </p>
                            {asociacion.estado === 'ACEPTADO' &&
                              !coordinacion.prestacion && (
                                <button
                                  type="button"
                                  className="adm-accion"
                                  disabled={preparandoPrestacion}
                                  onClick={() => prepararPrestacion(
                                    asociacion.profesional?.id_profesional,
                                  )}
                                >
                                  {preparandoPrestacion
                                    ? 'Preparando...'
                                    : 'Preparar prestación'}
                                </button>
                              )}
                            {asociacion.estado === 'PENDIENTE' &&
                              asignaciones[seleccion.id_solicitud]?.actual &&
                              !coordinacion.prestacion && (
                                <button
                                  type="button"
                                  className="adm-accion"
                                  disabled={confirmandoAsociacion}
                                  onClick={() => confirmarAsociacion(
                                    asociacion.profesional?.id_profesional,
                                  )}
                                >
                                  {confirmandoAsociacion
                                    ? 'Confirmando...'
                                    : 'Confirmar asociación'}
                                </button>
                              )}
                          </div>
                        ),
                      )}


                      {coordinacion.prestacion && (
                        <ComunicarCondicionesAdministracion
                          key={coordinacion.prestacion.id_prestacion}
                          idSolicitud={seleccion.id_solicitud}
                          prestacion={coordinacion.prestacion}
                          onRegistrado={(prestacionActualizada) => {
                            setCoordinacion((anterior) =>
                              anterior?.prestacion?.id_prestacion ===
                              prestacionActualizada.id_prestacion
                                ? {
                                    ...anterior,
                                    prestacion: prestacionActualizada,
                                  }
                                : anterior
                            )
                          }}
                        />
                      )}

                      {coordinacion.prestacion?.estado ===
                        'PENDIENTE_CONTRATACION' && (
                          <div className="adm-detalle-pago">
                            <h4>Estado del agendamiento inicial</h4>

                            {(coordinacion.reservas ?? []).some(
                              (reserva) =>
                                reserva.estado === 'ACTIVA' &&
                                reserva.disponibilidad?.estado === 'RESERVADA'
                            ) ? (
                              <p>
                                Existe una reserva activa. Antes de agendar
                                la primera reunión debe confirmarse que
                                el pago de esta prestación esté RETENIDO.
                                El backend verificará también el horario
                                y las demás condiciones.
                              </p>
                            ) : (
                              <p>
                                La primera reunión no puede agendarse
                                todavía. Se requiere pago verificado y
                                retenido, con reserva ACTIVA y horario
                                RESERVADA.
                              </p>
                            )}
                          </div>
                        )}

                      {coordinacion.prestacion?.estado === 'CONTRATADA' && (
                        <div className="adm-detalle-pago">
                          <h4>Contratación confirmada</h4>
                          <p>
                            La prestación figura CONTRATADA.
                            Revisa las reuniones registradas para consultar
                            su agendamiento.
                          </p>
                        </div>
                      )}


                      {coordinacion.prestacion?.estado ===
                        'PENDIENTE_CONTRATACION' &&
                        pagos.some((pago) =>
                          Number(pago.id_prestacion) ===
                            Number(coordinacion.prestacion.id_prestacion) &&
                          pago.estado_pago === 'RETENIDO' &&
                          pago.estado_verificacion === 'VERIFICADO'
                        ) &&
                        (coordinacion.reservas ?? []).some(
                          (reserva) =>
                            reserva.estado === 'ACTIVA' &&
                            reserva.disponibilidad?.estado === 'RESERVADA'
                        ) &&
                        !(coordinacion.reuniones ?? []).some(
                          (reunion) => reunion.estado === 'AGENDADA'
                        ) && (
                          <button
                            type="button"
                            className="adm-accion"
                            disabled={agendandoPrimeraReunion}
                            onClick={agendarPrimeraReunion}
                          >
                            {agendandoPrimeraReunion
                              ? 'Agendando primera reunión...'
                              : 'Agendar primera reunión'}
                          </button>
                        )}

                      {(coordinacion.reservas ?? []).map((reserva) => (
                        <p key={reserva.id_reserva}>
                          Reserva #{reserva.id_reserva}:
                          {' '}{reserva.estado}
                        </p>
                      ))}

                      {!coordinacion.prestacion && (
                        <p className="adm-nota">
                          La solicitud todavía no posee una prestación
                          preparada. No hay contratación confirmada.
                        </p>
                      )}
                    </>
                  )}
                </section>

                <h3>Objetivo</h3>
                <p>{seleccion.objetivo}</p>
                <h3>Necesidad empresarial</h3>
                <p>{seleccion.descripcion_necesidad}</p>
                {coordinacion?.prestacion?.id_prestacion != null &&
                  ['CONTRATADA', 'POSTERGADA'].includes(coordinacion.prestacion.estado) && (
                    <AgendaPrestacionAdministracionE3
                      key={coordinacion.prestacion.id_prestacion}
                      idPrestacion={coordinacion.prestacion.id_prestacion}
                      estadoPrestacion={coordinacion.prestacion.estado}
                      onActualizado={async () => {
                        const actualizado = await obtenerJson(
                          `/coordinacion/administracion/solicitudes/${seleccion.id_solicitud}/coordinacion/`,
                        )
                        setCoordinacion(actualizado)
                      }}
                    />
                )}
                {coordinacion?.prestacion?.id_prestacion != null && (
                  <section
                    aria-label="Seguimiento del servicio"
                    style={{
                      marginTop: 24,
                      padding: '18px 20px',
                      border: '1px solid #dce8df',
                      borderRadius: 16,
                      background: '#f7faf8',
                    }}
                  >
                    <h3 style={{ marginTop: 0 }}>Seguimiento del servicio</h3>
                    {coordinacion.prestacion.estado === 'PENDIENTE_CONTRATACION' ? (
                      <p style={{ marginBottom: 0, color: '#596e64' }}>
                        La prestación está preparada, pero todavía no contratada.
                        El seguimiento de avances se habilitará después de
                        confirmar el pago y la primera reunión.
                      </p>
                    ) : (
                      <SeguimientoPrestacionAdministracion
                        key={coordinacion.prestacion.id_prestacion}
                        idPrestacion={coordinacion.prestacion.id_prestacion}
                        estadoPrestacion={coordinacion.prestacion.estado}
                      />
                    )}
                  </section>
                )}
                {!asignaciones[seleccion.id_solicitud]?.actual &&
                  !asignaciones[seleccion.id_solicitud]?.error &&
                  seleccion.estado !== 'COORDINADA' &&
                  !cerrada(seleccion) && (
                    <div
                      style={{
                        marginTop: 24,
                        padding: '20px 22px',
                        border: '1px solid #dfe9e3',
                        borderRadius: 16,
                        background: '#f7faf8',
                        display: 'grid',
                        gap: 14,
                      }}
                    >
                      <div style={{ display: 'grid', gap: 5 }}>
                        <strong style={{ color: '#294b40', fontSize: 16 }}>
                          Responsable de la solicitud
                        </strong>
                        <span style={{ color: '#627a6e', fontSize: 14, lineHeight: 1.5 }}>
                          Asigna esta solicitud a tu gestión administrativa
                          para continuar con su seguimiento.
                        </span>
                      </div>
                      <div>
                        <button
                          type="button"
                          className="adm-accion"
                          disabled={asignando}
                          onClick={() => autoasignar(seleccion)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 9,
                            minHeight: 44,
                            padding: '11px 20px',
                            border: '1px solid #315f50',
                            borderRadius: 11,
                            background: '#315f50',
                            color: '#fff',
                            font: 'inherit',
                            fontWeight: 700,
                            cursor: asignando ? 'wait' : 'pointer',
                            opacity: asignando ? 0.65 : 1,
                          }}
                        >
                          <span aria-hidden="true">✓</span>
                          {asignando ? 'Asignando...' : 'Asignarme esta solicitud'}
                        </button>
                      </div>
                      <small style={{ color: '#657c70', lineHeight: 1.5 }}>
                        La asignación requiere confirmación y permisos administrativos.
                        No confirma pagos ni contrataciones.
                      </small>
                    </div>
                  )}
              </section>
              </VentanaAdministracion>
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default Administracion