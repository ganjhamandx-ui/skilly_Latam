
import { useEffect, useRef } from 'react'
import './AdminNavegacion.css'

const modulos = [
  {
    id: 'solicitudes',
    numero: '01',
    titulo: 'Gestión de solicitudes',
    descripcion: 'Empresas, coordinación y control de pagos.',
    ruta: '/administracion',
    icono: '▤',
  },
  {
    id: 'validaciones',
    numero: '02',
    titulo: 'Validaciones profesionales',
    descripcion: 'Revisión documental y antecedentes.',
    ruta: '/administracion/validaciones',
    icono: '✓',
  },
  {
    id: 'propuestas',
    numero: '03',
    titulo: 'Revisión de propuestas',
    descripcion: 'Servicios enviados por profesionales.',
    ruta: '/administracion/propuestas',
    icono: '◇',
  },
  {
    id: 'indicadores',
    numero: '04',
    titulo: 'Indicadores administrativos',
    descripcion: 'Resumen, estados y cifras del sistema.',
    ruta: '/administracion/indicadores',
    icono: '▥',
  },
  {
    id: 'comision',
    numero: '05',
    titulo: 'Comisión configurable',
    descripcion: 'Porcentaje vigente e historial de cambios.',
    ruta: '/administracion/comision',
    icono: '%',
  },
  {
    id: 'cancelaciones',
    numero: '05C',
    titulo: 'Cargo por cancelación',
    descripcion: 'Porcentaje configurable e historial separado de la comisión.',
    ruta: '/administracion/cancelaciones',
    icono: '%',
  },
  {
    id: 'expedientes',
    numero: '05D',
    titulo: 'Expedientes de cancelación',
    descripcion: 'Solicitudes, evidencia privada y evaluación.',
    ruta: '/administracion/expedientes-cancelacion',
    icono: '⚑',
  },
  {
    id: 'cuentas',
    numero: '05B',
    titulo: 'Cuentas bancarias',
    descripcion: 'Cuentas receptoras e historial administrativo.',
    ruta: '/administracion/cuentas-bancarias',
    icono: '▣',
  },
  {
    id: 'trazabilidad',
    numero: '06',
    titulo: 'Trazabilidad operacional',
    descripcion: 'Historial de eventos y acciones del sistema.',
    ruta: '/administracion/trazabilidad',
    icono: '◎',
  },
  {
    id: 'reclamos',
    numero: '07',
    titulo: 'Gestión de reclamos',
    descripcion: 'Bandeja de reclamos, antecedentes y resoluciones.',
    ruta: '/administracion/reclamos',
    icono: '⚑',
  },
  {
    id: 'retroalimentacion',
    numero: '08',
    titulo: 'Retroalimentación privada',
    descripcion: 'Comentarios empresariales y recomendaciones profesionales.',
    ruta: '/administracion/retroalimentacion',
    icono: '✉',
  },
]

export default function AdminNavegacion({ activo }) {
  const activoRef = useRef(null)
  useEffect(() => {
    const enlace = activoRef.current
    const fila = enlace?.parentElement
    if (fila && fila.scrollWidth > fila.clientWidth) {
      fila.scrollLeft = enlace.offsetLeft - fila.offsetLeft - (fila.clientWidth - enlace.offsetWidth) / 2
    }
  }, [activo])

  return (
    <nav
      className="sk-admin-menu sk-admin-menu--uniforme"
      aria-label="Módulos de administración"
    >

      <div className="sk-admin-menu__grid">
        {modulos.map((modulo) => (
          <a
            ref={activo === modulo.id ? activoRef : null}
            key={modulo.id}
            href={modulo.ruta}
            className={
              `sk-admin-menu__tarjeta${
                activo === modulo.id ? ' is-active' : ''
              }`
            }
            aria-current={
              activo === modulo.id ? 'page' : undefined
            }
          >
            <div className="sk-admin-menu__superior">
              <span
                className="sk-admin-menu__icono"
                aria-hidden="true"
              >
                {modulo.icono}
              </span>

              <span className="sk-admin-menu__numero">
                {modulo.numero}
              </span>
            </div>

            <strong>{modulo.titulo}</strong>

            <span className="sk-admin-menu__descripcion">
              {modulo.descripcion}
            </span>

            <span className="sk-admin-menu__abrir">
              {activo === modulo.id
                ? 'Módulo actual'
                : 'Abrir módulo'}

              <span aria-hidden="true"> →</span>
            </span>
          </a>
        ))}
      </div>
    </nav>
  )
}
