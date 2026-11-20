/**
 * Presenta los datos receptores entregados por el flujo de pago empresarial.
 * No determina si la cuenta quedó fijada: esa condición depende de la respuesta de la API.
 * @param {Object} props Datos seleccionados por el contenedor.
 * @param {Object|null} props.cuentaFijada Titular, RUT, banco, tipo, número y correo.
 * @returns {import('react').ReactElement|null} Datos bancarios o null si no hay cuenta.
 */
export default function CuentaReceptoraOrganizacion({ cuentaFijada }) {
  if (!cuentaFijada) return null
  const campos = [
    ['Titular', cuentaFijada.titular],
    ['RUT', cuentaFijada.rut_titular],
    ['Banco', cuentaFijada.banco],
    ['Tipo de cuenta', cuentaFijada.tipo_cuenta],
    ['Número de cuenta', cuentaFijada.numero_cuenta],
    ['Correo', cuentaFijada.correo],
  ]
  return <section aria-label="Datos bancarios para esta transferencia" className="cuenta-transferencia">
    <h3>Datos para realizar la transferencia</h3>
    <p>Realiza la transferencia a esta cuenta principal indicada por SKILLY.</p>
    <dl>{campos.map(([etiqueta, valor]) => <div key={etiqueta}>
      <dt>{etiqueta}</dt><dd>{valor}</dd>
    </div>)}</dl>
    <p>SKILLY verificará la recepción efectiva del pago.</p>
  </section>
}
