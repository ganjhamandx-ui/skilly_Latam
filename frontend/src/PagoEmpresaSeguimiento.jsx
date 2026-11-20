
import { useEffect, useState } from 'react'
import AvisoPoliticaCancelacionE3 from './AvisoPoliticaCancelacionE3.jsx'
import { mostrarAvisoPolitica, mostrarBloquePolitica, claveAvisoPolitica } from './avisoPoliticaCancelacionE3.mjs'
import CuentaReceptoraOrganizacion from './CuentaReceptoraOrganizacion.jsx'
import './CuentaReceptoraOrganizacion.css'

const estiloCampo = {
  width: '100%',
  padding: '13px',
  border: '1px solid #d5e0da',
  borderRadius: '10px',
  boxSizing: 'border-box',
}

const estiloBoton = {
  padding: '13px 18px',
  border: 'none',
  borderRadius: '10px',
  background: '#285d55',
  color: '#fff',
  fontWeight: 700,
  cursor: 'pointer',
}

/**
 * Convierte el valor a número y lo presenta con hasta dos decimales.
 * @param {number|string|null} valor Importe; se aplica la conversión Number de JavaScript.
 * @param {string} [moneda='CLP'] Moneda que acompaña al importe.
 * @returns {string} Importe formateado o «No informado» si no es finito.
 */
function formatoDinero(valor, moneda = 'CLP') {
  const numero = Number(valor)

  if (!Number.isFinite(numero)) {
    return 'No informado'
  }

  return (
    new Intl.NumberFormat('es-CL', {
      maximumFractionDigits: 2,
    }).format(numero) +
    ' ' +
    (moneda || 'CLP')
  )
}

/**
 * Presenta la fecha en la zona local del navegador, conservando valores inválidos.
 * @param {string|null} valor Fecha o marca temporal recibida.
 * @returns {string} Fecha y hora, valor original inválido o «No registrada».
 */
function formatoFecha(valor) {
  if (!valor) return 'No registrada'

  const fecha = new Date(valor)

  if (Number.isNaN(fecha.getTime())) {
    return String(valor)
  }

  return fecha.toLocaleString('es-CL', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

/**
 * Prioriza un mensaje general o reúne errores de campos representados como listas.
 * @param {Object|null} datos Cuerpo de respuesta.
 * @param {number} codigo Estado HTTP usado como respaldo.
 * @returns {string} Explicación del fallo.
 */
function obtenerMensaje(datos, codigo) {
  if (typeof datos?.mensaje === 'string') {
    return datos.mensaje
  }

  if (typeof datos?.detail === 'string') {
    return datos.detail
  }

  if (datos && typeof datos === 'object') {
    const errores = Object.entries(datos).flatMap(
      ([campo, valor]) =>
        Array.isArray(valor)
          ? valor.map((mensaje) => `${campo}: ${mensaje}`)
          : [],
    )

    if (errores.length) {
      return errores.join(' | ')
    }
  }

  return `Operación no completada (HTTP ${codigo}).`
}

/**
 * Describe el estado registrado, distinguiendo operaciones de integración y simuladas.
 * @param {string} estado Estado de pago recibido del servidor.
 * @returns {string} Descripción para la organización.
 */
function descripcionPago(estado) {
  switch (estado) {
    case 'RETENIDO':
      return 'El pago está retenido por SKILLY y todavía no ha sido liberado al profesional.'

    case 'REVERSA_SIMULADA':
      return 'SIMULACIÓN ACADÉMICA: se registró una devolución de prueba. No representa una transferencia ni un reembolso bancario real.'

    case 'LIBERADO':
      return 'El pago figura como liberado en SKILLY.'

    case 'PENDIENTE_WEBPAY':
      return 'Pago Webpay de prueba iniciado. Completa la operación en Transbank y luego actualiza el estado.'

    case 'RETENIDO_REVISION_AGENDA':
      return 'Webpay confirmó pago de integración; SKILLY debe regularizar el horario antes de continuar.'

    case 'WEBPAY_RECHAZADO':
    case 'WEBPAY_ANULADO':
      return 'La transacción Webpay no fue autorizada o fue cancelada.'

    case 'WEBPAY_REVISION_MANUAL':
      return 'Webpay informó autorización con datos discordantes. Administración debe revisarlos.'

    case 'PENDIENTE_VERIFICACION':
      return 'La transferencia fue informada. SKILLY debe verificarla antes de confirmar la contratación.'

    default:
      return 'Este es el estado actual registrado por SKILLY.'
  }
}

/**
 * Reinicia el estado interno del pago cuando cambia la referencia empresarial.
 * @param {Object} props Propiedades del seguimiento.
 * @param {string} props.referencia Referencia privada de la solicitud.
 * @param {Object} props.prestacion Prestación con estado y condiciones comunicadas.
 * @returns {import('react').ReactElement} Panel de pago asociado a esa referencia.
 */
export default function PagoEmpresaSeguimiento({
  referencia,
  prestacion,
}) {
  return <PagoEmpresa key={referencia} referencia={referencia} prestacion={prestacion} />
}

/**
 * Consulta pago, política y cuenta receptora para la referencia empresarial.
 * Separa cerrar el aviso de política de registrar su aceptación expresa.
 * @param {Object} props Propiedades del panel.
 * @param {string} props.referencia Referencia privada para las consultas y escrituras.
 * @param {Object} props.prestacion Estado y condiciones que habilitan el formulario.
 * @returns {import('react').ReactElement} Estado de pago y operaciones disponibles.
 */
function PagoEmpresa({ referencia, prestacion }) {
  const [pago, setPago] = useState(null)
  const [sinPago, setSinPago] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [revision, setRevision] = useState(0)
  const [politica, setPolitica] = useState(null)
  const [politicaError, setPoliticaError] = useState('')
  const [acepto, setAcepto] = useState(false)
  const [aceptando, setAceptando] = useState(false)
  const [resolucionCancelacion, setResolucionCancelacion] = useState(null)
  const [claveAvisoCerrado, setClaveAvisoCerrado] = useState('')
  const [claveAvisoAbierto, setClaveAvisoAbierto] = useState('')


  const [comprobante, setComprobante] = useState(null)
  const [metodoElegido, setMetodoElegido] = useState('TRANSFERENCIA')
  const [referenciaTransaccion, setReferenciaTransaccion] =
    useState('')
  const [consultaCuenta, setConsultaCuenta] = useState(null)

  const condicionesComunicadas =
    prestacion?.condiciones_comunicadas === true ||
    (typeof prestacion?.condiciones_comunicadas === 'string' &&
      prestacion.condiciones_comunicadas.trim().length > 0)

  const pendienteContratacion =
    prestacion?.estado === 'PENDIENTE_CONTRATACION'

  const habilitarFormulario =
    sinPago &&
    condicionesComunicadas &&
    pendienteContratacion

  const clavePolitica = politica?.version ? claveAvisoPolitica(referencia, politica.version) : ''
  const avisoPoliticaVisible = mostrarAvisoPolitica({ referencia, habilitarFormulario, cargando, politica }) &&
    (claveAvisoCerrado !== clavePolitica || claveAvisoAbierto === clavePolitica)
  const consultarCuenta = Boolean(referencia && habilitarFormulario && !cargando && metodoElegido === 'TRANSFERENCIA')
  const cuentaConsultada = consultaCuenta?.revision === revision
  const cuentaReceptora = consultarCuenta && cuentaConsultada ? consultaCuenta.cuenta : null
  const avisoBancario = consultarCuenta && cuentaConsultada ? consultaCuenta.mensaje : ''
  const cargandoCuenta = consultarCuenta && !cuentaConsultada

  /**
   * Recuerda el cierre del aviso para esta referencia y versión durante el montaje.
   * No registra por sí mismo la aceptación de la política.
   * @returns {void}
   */
  function cerrarAvisoPolitica() { setClaveAvisoCerrado(clavePolitica); setClaveAvisoAbierto('') }
  /**
   * Cambia el método elegido e invalida la consulta previa de cuenta receptora.
   * @param {string} metodo Método seleccionado por la organización.
   * @returns {void}
   */
  function elegirMetodo(metodo) { setMetodoElegido(metodo); setConsultaCuenta(null) }
  /**
   * Descarta los datos consultados y solicita una nueva lectura mediante la revisión.
   * @returns {void}
   */
  function actualizarPago() {
    setCargando(true); setError(''); setPago(null); setSinPago(false)
    setPolitica(null); setPoliticaError(''); setAcepto(false); setConsultaCuenta(null)
    setRevision(actual => actual + 1)
  }

  useEffect(() => {
    // Lee la política vinculada a la referencia de la prestación.
    if (!referencia) return undefined
    const controller = new AbortController()
    fetch(`/api/seguimiento/empresa/${encodeURIComponent(referencia)}/politica-cancelacion/`, {
      credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
    }).then(async r => {
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(obtenerMensaje(d,r.status))
      return d
    }).then(d => { if (!controller.signal.aborted) setPolitica(d) })
      .catch(e => { if (!controller.signal.aborted) setPoliticaError(e.message || 'No se consultó la política.') })
    return () => controller.abort()
  }, [referencia, revision])

  useEffect(() => {
    // Consulta el estado de cancelación que puede limitar las opciones de pago.
    if (!referencia) return undefined
    const controller = new AbortController()
    fetch(`/api/seguimiento/empresa/${encodeURIComponent(referencia)}/cancelaciones/estado/`, {
      credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
    }).then(r => r.ok ? r.json() : Promise.resolve({}))
      .then(d => { if (!controller.signal.aborted) setResolucionCancelacion(d.expediente || null) })
      .catch(() => {})
    return () => controller.abort()
  }, [referencia, revision])

  /**
   * Registra la aceptación expresa de la versión visible y exige su confirmación.
   * Los fallos se muestran junto a la política y el bloqueo se libera al terminar.
   * @returns {Promise<void>} Finalización del registro de aceptación.
   */
  async function aceptarPolitica() {
    if (!politica?.version || aceptando || !acepto) return
    setAceptando(true); setPoliticaError('')
    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials:'same-origin', cache:'no-store', headers:{Accept:'application/json'},
      })
      const token = await csrfRespuesta.json().catch(() => ({}))
      if (!csrfRespuesta.ok || !token.csrfToken) throw new Error('No se obtuvo el token CSRF.')
      const r = await fetch(`/api/seguimiento/empresa/${encodeURIComponent(referencia)}/politica-cancelacion/`, {
        method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':token.csrfToken},
        body:JSON.stringify({acepto:true,version:politica.version}),
      })
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(obtenerMensaje(d,r.status))
      if (d.aceptada !== true) throw new Error('No se confirmó la aceptación. Consulta el estado antes de continuar.')
      setPolitica(d); setAcepto(false); cerrarAvisoPolitica()
    } catch(e) { setPoliticaError(e.message || 'No se pudo registrar la aceptación.') }
    finally { setAceptando(false) }
  }

  useEffect(() => {
    // Vincula la consulta de pago a la referencia y cancela respuestas anteriores.
    if (!referencia) return undefined

    const controlador = new AbortController()

    /**
     * Distingue el 404 de pago inexistente de otros errores de consulta.
     * Comprueba identificador y estado antes de mostrar el pago; ignora respuestas canceladas.
     * @returns {Promise<void>} Finalización de la consulta con errores visibles.
     */
    async function consultarPago() {
      try {
        const respuesta = await fetch(
          `/api/pagos/empresa/${encodeURIComponent(referencia)}/estado/`,
          {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: {
              Accept: 'application/json',
            },
            signal: controlador.signal,
          },
        )

        const datos = await respuesta
          .json()
          .catch(() => ({}))

        const pagoNoExiste =
          respuesta.status === 404 &&
          typeof datos.mensaje === 'string' &&
          datos.mensaje.toLowerCase().includes(
            'no existe un pago',
          )

        if (pagoNoExiste) {
          if (!controlador.signal.aborted) {
            setSinPago(true)
          }
          return
        }

        if (!respuesta.ok) {
          throw new Error(
            obtenerMensaje(datos, respuesta.status),
          )
        }

        if (
          !datos.id_pago ||
          typeof datos.estado_pago !== 'string'
        ) {
          throw new Error(
            'La API devolvió información de pago incompleta.',
          )
        }

        if (!controlador.signal.aborted) {
          setPago(datos)
        }
      } catch (fallo) {
        if (!controlador.signal.aborted) {
          setError(
            fallo instanceof Error
              ? fallo.message
              : 'No fue posible consultar el pago.',
          )
        }
      } finally {
        if (!controlador.signal.aborted) {
          setCargando(false)
        }
      }
    }

    void consultarPago()

    return () => controlador.abort()
  }, [referencia, revision])

  useEffect(() => {
    // Consulta la cuenta receptora cuando está habilitada la transferencia.
    if (!referencia || !habilitarFormulario || cargando || metodoElegido !== 'TRANSFERENCIA') {
      return undefined
    }
    const controlador = new AbortController()
    fetch(`/api/pagos/empresa/${encodeURIComponent(referencia)}/transferencia/disponibilidad/`, {
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: controlador.signal,
    })
      .then(async (respuesta) => {
        const datos = await respuesta.json().catch(() => ({}))
        if (!respuesta.ok) throw new Error(obtenerMensaje(datos, respuesta.status))
        return datos
      })
      .then((datos) => {
        // Aplica la cuenta devuelta solo si la consulta corresponde a la revisión activa.
        if (controlador.signal.aborted) return
        if (datos.disponible && datos.cuenta) {
          setConsultaCuenta({ revision, cuenta: datos.cuenta, mensaje: '' })
        } else {
          setConsultaCuenta({ revision, cuenta: null, mensaje: datos.mensaje || 'Transferencia no disponible.' })
        }
      })
      .catch((fallo) => {
        if (!controlador.signal.aborted) {
          setConsultaCuenta({ revision, cuenta: null, mensaje: fallo.message || 'No fue posible consultar la cuenta receptora.' })
        }
      })
    return () => controlador.abort()
  }, [referencia, habilitarFormulario, cargando, revision, metodoElegido])

  /**
   * Solicita una transacción y envía su token al dominio HTTPS de integración permitido.
   * El bloqueo permanece activo al iniciar la navegación y se libera ante un fallo local.
   * @returns {Promise<void>} Preparación del formulario de redirección o presentación del error.
   */
  async function iniciarWebpay() {
    if (guardando || cargando || !referencia) return
    if (!politica?.aceptada) { setError('Debes aceptar la política de cancelación antes de iniciar Webpay.'); return }
    setGuardando(true); setError(''); setAviso('')
    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' },
      })
      const csrf = await csrfRespuesta.json().catch(() => ({}))
      if (!csrfRespuesta.ok || !csrf.csrfToken) throw new Error('No se obtuvo token CSRF.')
      const respuesta = await fetch(
        `/api/pagos/empresa/${encodeURIComponent(referencia)}/webpay/iniciar/`, {
          method: 'POST', credentials: 'same-origin',
          headers: { Accept: 'application/json', 'X-CSRFToken': csrf.csrfToken },
        },
      )
      const datos = await respuesta.json().catch(() => ({}))
      if (!respuesta.ok) throw new Error(obtenerMensaje(datos, respuesta.status))
      const destino = new URL(datos.url)
      if (destino.protocol !== 'https:' || destino.hostname !== 'webpay3gint.transbank.cl') {
        throw new Error('La URL de Webpay no corresponde al ambiente de integración.')
      }
      if (!datos.token || typeof datos.token !== 'string') throw new Error('Token Webpay ausente.')
      const formulario = document.createElement('form')
      formulario.method = 'POST'; formulario.action = destino.toString()
      const campo = document.createElement('input')
      campo.type = 'hidden'; campo.name = 'token_ws'; campo.value = datos.token
      formulario.appendChild(campo); document.body.appendChild(formulario)
      formulario.submit()
      // La navegación externa reemplaza la pantalla. No almacenar tarjetas ni credenciales.
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No fue posible iniciar Webpay.')
      setGuardando(false)
    }
  }

  /**
   * Valida referencia y comprobante antes de informar una transferencia pendiente.
   * Envía el archivo y la cuenta receptora en multipart, y exige un identificador de pago
   * para actualizar la vista. La verificación administrativa se realiza por separado.
   * @param {import('react').FormEvent<HTMLFormElement>} evento Envío del formulario.
   * @returns {Promise<void>} Finalización del registro con errores visibles.
   */
  async function informarTransferencia(evento) {
    evento.preventDefault()

    if (
      guardando ||
      cargando ||
      !habilitarFormulario ||
      !cuentaReceptora
    ) {
      return
    }

    if (!politica?.aceptada && !politica?.contrato_previo) { setError('Debes aceptar la política de cancelación antes de informar la transferencia.'); return }
    const textoReferencia = referenciaTransaccion.trim()

    if (!comprobante) {
      setError('Debes adjuntar tu comprobante PDF, JPG o PNG.')
      return
    }
    if (comprobante.size > 5 * 1024 * 1024 || comprobante.size === 0) {
      setError('El comprobante debe tener contenido y pesar como máximo 5 MB.')
      return
    }
    if (!/\.(pdf|jpe?g|png)$/i.test(comprobante.name)) {
      setError('Formato no permitido. Adjunta PDF, JPG o PNG.')
      return
    }

    if (textoReferencia.length > 255) {
      setError(
        'La referencia de transacción supera los 255 caracteres.',
      )
      return
    }

    setGuardando(true)
    setError('')
    setAviso('')

    try {
      const respuestaCsrf = await fetch(
        '/api/acceso/csrf/',
        {
          method: 'GET',
          credentials: 'same-origin',
          cache: 'no-store',
          headers: {
            Accept: 'application/json',
          },
        },
      )

      const datosCsrf = await respuestaCsrf
        .json()
        .catch(() => ({}))

      if (
        !respuestaCsrf.ok ||
        !datosCsrf.csrfToken
      ) {
        throw new Error(
          'No se pudo obtener el token de seguridad CSRF.',
        )
      }

      const datosEnvio = new FormData()
      datosEnvio.append('metodo_pago', 'TRANSFERENCIA')
      datosEnvio.append('comprobante_transferencia', comprobante)
      datosEnvio.append('id_cuenta_receptora', String(cuentaReceptora.id_cuenta))
      if (textoReferencia) {
        datosEnvio.append('referencia_transaccion', textoReferencia)
      }

      const respuesta = await fetch(
        `/api/pagos/empresa/${encodeURIComponent(referencia)}/transferencia/`,
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'X-CSRFToken': datosCsrf.csrfToken,
          },
          body: datosEnvio,
        },
      )

      const datos = await respuesta
        .json()
        .catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(
          obtenerMensaje(datos, respuesta.status),
        )
      }

      if (!datos.pago?.id_pago) {
        throw new Error(
          'No se pudo confirmar la respuesta del servidor. Consulta el estado del pago antes de intentar nuevamente.',
        )
      }

      setPago(datos.pago)
      setSinPago(false)
      setComprobante(null)
      setReferenciaTransaccion('')

      setAviso(
        datos.mensaje ||
        'La transferencia quedó informada a SKILLY.',
      )
    } catch (fallo) {
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible informar la transferencia.',
      )
    } finally {
      setGuardando(false)
    }
  }

  return (
    <section className="sg-tarjeta sg-panel-prestacion">
      <span className="sg-etiqueta">
        PAGO EMPRESARIAL
      </span>

      <h2>Estado del pago</h2>

      <p>Consulta el estado del pago. Puedes transferir a SKILLY o pagar con Webpay Plus en ambiente académico de pruebas.</p>

      <button
        type="button"
        style={estiloBoton}
        disabled={cargando || guardando}
        onClick={actualizarPago}
      >
        {cargando
          ? 'Consultando…'
          : '↻ Actualizar estado del pago'}
      </button>

      {cargando && (
        <p role="status">
          Consultando el estado del pago…
        </p>
      )}

      {error && (
        <div className="sg-error" role="alert">
          {error}
        </div>
      )}

      {aviso && (
        <div className="sg-nota" role="status">
          {aviso}
        </div>
      )}

      {!cargando && sinPago && (
        <div className="sg-nota">
          Todavía no existe un pago registrado
          para esta prestación.
        </div>
      )}

      {!cargando &&
        sinPago &&
        !condicionesComunicadas && (
          <div className="sg-nota">
            <strong>
              Transferencia todavía no habilitada.
            </strong>

            <p>
              SKILLY debe comunicar primero
              las condiciones de contratación.
              No se puede informar una transferencia
              mientras ese requisito esté pendiente.
            </p>
          </div>
        )}

      {!cargando &&
        sinPago &&
        condicionesComunicadas &&
        !pendienteContratacion && (
          <div className="sg-nota">
            Esta prestación no está pendiente de
            contratación. No se puede iniciar
            una transferencia desde este formulario.
          </div>
        )}

      {resolucionCancelacion && (
        <section className="sg-nota" style={{marginTop:16}} aria-label="Resultado de cancelación">
          <h3>Solicitud de cancelación — {resolucionCancelacion.estado}</h3>
          <p>{resolucionCancelacion.mensaje}</p>
          {resolucionCancelacion.estado === 'RESUELTO' && <>
            <p><strong>Decisión:</strong> {resolucionCancelacion.decision}</p>
            <p><strong>Motivo de la decisión:</strong> {resolucionCancelacion.motivo_publico}</p>
            <p><strong>Porcentaje de tu contrato:</strong> {resolucionCancelacion.porcentaje_contratado}%</p>
            <p>Pago considerado: {formatoDinero(resolucionCancelacion.monto_total)} · Trabajo acreditado: {formatoDinero(resolucionCancelacion.monto_trabajo)}</p>
            <p>Cargo calculado: {formatoDinero(resolucionCancelacion.cargo_teorico)} · <strong>Cargo realmente aplicado: {formatoDinero(resolucionCancelacion.cargo_aplicado)}</strong></p>
            <p>Devolución propuesta: {resolucionCancelacion.devolucion_propuesta === null ? 'No procede aún' : formatoDinero(resolucionCancelacion.devolucion_propuesta)}</p>
            <p>Una devolución propuesta no significa que el dinero haya sido reintegrado.</p>
          </>}
        </section>
      )}
      {mostrarBloquePolitica({ habilitarFormulario, cargando, politica }) && (
        <section className="sg-nota" style={{ display: 'grid', gap: 12, marginTop: 16 }} aria-label="Política de cancelación previa al pago">
          {politicaError && <p className="sg-error" role="alert">{politicaError}</p>}
          {!politica && !politicaError && <p role="status">Consultando las condiciones de cancelación…</p>}
          {politica?.contrato_previo && <p>{politica.mensaje}</p>}
          {politica && !politica.contrato_previo && (
            <>
              <strong>Antes de pagar</strong>
              <p>Revisa las condiciones de cancelación y registra tu aceptación.</p>
              <button type="button" style={estiloBoton} onClick={() => setClaveAvisoAbierto(clavePolitica)}>
                Ver y aceptar condiciones
              </button>
            </>
          )}
        </section>
      )}
      {avisoPoliticaVisible && habilitarFormulario && politica && !politica.contrato_previo && !politica.aceptada && (
        <AvisoPoliticaCancelacionE3
          politica={politica}
          acepto={acepto}
          onCambiarAceptacion={setAcepto}
          guardando={aceptando}
          error={politicaError}
          onAceptar={aceptarPolitica}
          onCerrar={cerrarAvisoPolitica}
        />
      )}
      {!cargando && habilitarFormulario && (
        <div className="sg-nota" style={{ display: 'grid', gap: 10, marginTop: 16 }}>
          <strong>Seleccionar medio de pago</strong>
          <label><input type="radio" name="metodo-e3" checked={metodoElegido === 'TRANSFERENCIA'}
            onChange={() => elegirMetodo('TRANSFERENCIA')} /> Transferencia bancaria a SKILLY</label>
          <label><input type="radio" name="metodo-e3" checked={metodoElegido === 'WEBPAY_PLUS'}
            onChange={() => elegirMetodo('WEBPAY_PLUS')} /> Webpay Plus (solo pruebas, sin dinero real)</label>
        </div>
      )}
      {!cargando && habilitarFormulario && metodoElegido === 'WEBPAY_PLUS' && (
        <div className="sg-nota" style={{ display: 'grid', gap: 12, marginTop: 14 }}>
          <strong>Webpay Plus — Ambiente de integración</strong>
          <p>Usa únicamente los datos de prueba oficiales de Transbank. No ingreses tarjetas reales.</p>
          <button type="button" style={estiloBoton} disabled={guardando || (!politica?.aceptada && !politica?.contrato_previo)} onClick={iniciarWebpay}>
            {guardando ? 'Conectando con Webpay…' : 'Pagar mediante Webpay de prueba'}
          </button>
        </div>
      )}
      {!cargando && pago && ['WEBPAY_RECHAZADO','WEBPAY_ANULADO'].includes(pago.estado_pago) && (
        <div className="sg-nota" style={{ display: 'grid', gap: 10, marginTop: 15 }}>
          <p>La operación Webpay anterior no fue autorizada o se canceló. Puedes iniciar otra prueba.</p>
          <button type="button" style={estiloBoton} disabled={guardando || (!politica?.aceptada && !politica?.contrato_previo)} onClick={iniciarWebpay}>
            Reintentar Webpay de prueba
          </button>
        </div>
      )}
      {!cargando && habilitarFormulario && metodoElegido === 'TRANSFERENCIA' && (
        <form
          onSubmit={informarTransferencia}
          style={{
            display: 'grid',
            gap: 12,
            marginTop: 22,
          }}
        >
          <h3>Transferencia bancaria</h3>
          {cargandoCuenta && <p role="status">Consultando la cuenta principal de SKILLY…</p>}
          {avisoBancario && <div className="sg-nota" role="status">{avisoBancario}</div>}
          {cuentaReceptora && <CuentaReceptoraOrganizacion cuentaFijada={cuentaReceptora} />}
          {cuentaReceptora && <h3>Adjuntar comprobante</h3>}

          {cuentaReceptora && <>
          <p>
            Adjunta el comprobante de transferencia para su revisión.
            SKILLY verificará posteriormente el pago.
          </p>

          <label htmlFor="comprobante-transferencia">
            Adjuntar comprobante PDF, JPG o PNG (máximo 5 MB) *
          </label>

          <input
            id="comprobante-transferencia"
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            required
            style={estiloCampo}
            disabled={guardando}
            onChange={(evento) =>
              setComprobante(evento.target.files?.[0] || null)
            }
          />

          <label htmlFor="referencia-transferencia">
            Referencia bancaria (opcional)
          </label>

          <input
            id="referencia-transferencia"
            type="text"
            maxLength={255}
            style={estiloCampo}
            value={referenciaTransaccion}
            disabled={guardando}
            placeholder="Código de operación bancaria"
            onChange={(evento) =>
              setReferenciaTransaccion(
                evento.target.value,
              )
            }
          />

          <button
            type="submit"
            style={estiloBoton}
            disabled={
              guardando ||
              !cuentaReceptora ||
              cargandoCuenta ||
              !comprobante ||
              !politica?.aceptada
            }
          >
            {guardando
              ? 'Informando transferencia…'
              : 'Enviar comprobante para verificación'}
          </button>
          </>}
        </form>
      )}

      {!cargando && pago && (
        <>
          <div
            className="sg-grilla"
            style={{ marginTop: 20 }}
          >
            <div>
              <span>Número de pago</span>
              <strong>#{pago.id_pago}</strong>
            </div>

            <div>
              <span>Estado actual</span>
              <strong>{pago.estado_pago}</strong>
            </div>

            <div>
              <span>Monto registrado</span>
              <strong>
                {formatoDinero(
                  pago.monto_total,
                  pago.moneda,
                )}
              </strong>
            </div>

            <div>
              <span>Fecha de pago</span>
              <strong>
                {formatoFecha(pago.fecha_pago)}
              </strong>
            </div>

            <div>
              <span>Fecha de retención</span>
              <strong>
                {formatoFecha(pago.fecha_retencion)}
              </strong>
            </div>

            <div>
              <span>Fecha de liberación</span>
              <strong>
                {formatoFecha(pago.fecha_liberacion)}
              </strong>
            </div>
          </div>

          <div className="sg-nota">
            {descripcionPago(pago.estado_pago)}
          </div>
        </>
      )}
    </section>
  )
}
