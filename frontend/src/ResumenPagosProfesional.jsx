import './ResumenPagosProfesional.css'

const etiquetas = {
  id_pago: 'Pago',
  id_prestacion: 'Prestación',
  estado: 'Estado',
  estado_pago: 'Estado del pago',
  estado_liberacion: 'Estado de liberación',
  fecha_pago: 'Fecha de pago',
  fecha_verificacion: 'Fecha de verificación',
  fecha_retencion: 'Fecha de retención',
  fecha_liberacion: 'Fecha de liberación',
  fecha_registro: 'Fecha de registro',
  moneda: 'Moneda',
  referencia: 'Referencia',
  observacion: 'Observación',
}

const camposEconomicos = new Set([
  'monto_total', 'monto', 'porcentaje_comision_aplicado',
  'monto_comision', 'comision', 'monto_neto_profesional',
])

const orden = [
  'id_prestacion', 'estado_pago', 'estado_liberacion', 'estado',
  'fecha_pago', 'fecha_verificacion', 'fecha_retencion',
  'fecha_liberacion', 'fecha_registro', 'moneda',
  'referencia', 'observacion',
]

function esRestringido(clave) {
  return /password|contrasena|token|secret|hash|csrf|credential/i.test(clave)
}

function etiqueta(clave) {
  return etiquetas[clave] ?? clave.replaceAll('_', ' ')
    .replace(/^./, (letra) => letra.toUpperCase())
}

function representar(valor) {
  if (valor == null || valor === '') return 'No informado'
  if (typeof valor === 'boolean') return valor ? 'Sí' : 'No'
  if (typeof valor === 'object') {
    if (Array.isArray(valor)) return valor.map(representar).join(', ')
    return Object.entries(valor)
      .filter(([clave]) => !esRestringido(clave))
      .map(([clave, dato]) => `${etiqueta(clave)}: ${representar(dato)}`)
      .join(' | ')
  }
  return String(valor)
}

function valorNumerico(valor) {
  if (typeof valor === 'number') return Number.isFinite(valor) ? valor : null
  if (typeof valor !== 'string' || !/^-?\d+(?:\.\d+)?$/.test(valor.trim())) return null
  const numero = Number(valor)
  return Number.isFinite(numero) ? numero : null
}

function monedaDe(pago) {
  const codigo = String(pago.moneda || 'CLP').toUpperCase()
  return /^[A-Z]{3}$/.test(codigo) ? codigo : 'CLP'
}

function dinero(valor, moneda) {
  const numero = valorNumerico(valor)
  if (numero === null) return 'No informado'
  return `${new Intl.NumberFormat('es-CL', {
    maximumFractionDigits: 2,
  }).format(numero)} ${moneda}`
}

function tasa(valor) {
  const numero = valorNumerico(valor)
  if (numero === null) return 'No informada'
  return `${new Intl.NumberFormat('es-CL', {
    maximumFractionDigits: 4,
  }).format(numero)} %`
}

function fechaChile(valor) {
  if (valor == null || valor === '') return 'No informada'
  const texto = String(valor)
  if (/^\d{4}-\d{2}-\d{2}$/.test(texto)) {
    const [anio, mes, dia] = texto.split('-')
    return `${dia}-${mes}-${anio}`
  }
  const fecha = new Date(texto)
  if (Number.isNaN(fecha.getTime())) return texto
  return new Intl.DateTimeFormat('es-CL', {
    timeZone: 'America/Santiago',
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(fecha)
}

function clasificarEstado(estado) {
  const valor = String(estado ?? '').toUpperCase()
  if (/LIBERAD|PAGADO|COMPLETAD|APROBAD/.test(valor)) return 'positivo'
  if (/RECHAZ|REVERS|CANCELAD|FALLID/.test(valor)) return 'negativo'
  return 'pendiente'
}

export default function ResumenPagosProfesional({ pagos }) {
  if (!Array.isArray(pagos) || pagos.length === 0) {
    return <p>No hay pagos para mostrar.</p>
  }

  return (
    <div className="rpp-contenedor">
      <p className="rpp-aviso">
        Consulta el precio del servicio, la comisión de Skilly y el importe neto
        registrado para cada pago.
      </p>
      <div className="rpp-listado">
        {pagos.map((pago, indice) => {
          if (!pago || typeof pago !== 'object') {
            return <article className="rpp-tarjeta" key={indice}><p>{representar(pago)}</p></article>
          }

          const estado = pago.estado_liberacion ?? pago.estado_pago ?? pago.estado
          const moneda = monedaDe(pago)
          const montoTotal = pago.monto_total ?? pago.monto
          const montoComision = pago.monto_comision ?? pago.comision
          const netoProfesional = pago.monto_neto_profesional
          const porcentaje = pago.porcentaje_comision_aplicado

          const campos = [
            ...orden.filter((clave) => Object.prototype.hasOwnProperty.call(pago, clave)),
            ...Object.keys(pago).filter((clave) => !orden.includes(clave) && clave !== 'id_pago'),
          ].filter((clave) => !esRestringido(clave) && !camposEconomicos.has(clave))

          return (
            <article className="rpp-tarjeta" key={pago.id_pago ?? indice}>
              <div className="rpp-cabecera">
                <h3>Pago #{pago.id_pago ?? indice + 1}</h3>
                {estado != null && (
                  <span className={`rpp-estado rpp-${clasificarEstado(estado)}`}>
                    {representar(estado)}
                  </span>
                )}
              </div>

              <section className="rpp-desglose" aria-label={`Desglose económico del pago #${pago.id_pago ?? indice + 1}`}>
                <div className="rpp-linea">
                  <span>Precio del servicio</span>
                  <strong>{dinero(montoTotal, moneda)}</strong>
                </div>
                <div className="rpp-linea">
                  <span>Comisión SKILLY ({tasa(porcentaje)})</span>
                  <strong>{valorNumerico(montoComision) === null ? 'No informada' : `−${dinero(montoComision, moneda)}`}</strong>
                </div>
                <div className="rpp-neto">
                  <span>Neto correspondiente al profesional</span>
                  <strong>{dinero(netoProfesional, moneda)}</strong>
                </div>
              </section>

              <dl className="rpp-campos">
                {campos.map((clave) => (
                  <div className="rpp-campo" key={clave}>
                    <dt>{etiqueta(clave)}</dt>
                    <dd>{clave.startsWith('fecha_') ? fechaChile(pago[clave]) : representar(pago[clave])}</dd>
                  </div>
                ))}
              </dl>

              <p className="rpp-nota">
                La liberación se registra en SKILLY. El abono en una cuenta bancaria
                se gestiona por separado.
              </p>
            </article>
          )
        })}
      </div>
    </div>
  )
}
