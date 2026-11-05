from pathlib import Path
from datetime import datetime
import shutil

base = Path('frontend/src')
jsx = base / 'PortalProfesional.jsx'
css = base / 'PortalProfesional.css'
original = jsx.read_text(encoding='utf-8-sig')
estilos = css.read_text(encoding='utf-8-sig')

if 'SKILLY_MODAL_SERVICIOS_V1' in original:
    print('Este cambio ya fue aplicado. No se modifico nada.')
    raise SystemExit

# Cerramos sin ocultar la ventana durante procesos de carga o publicacion.
extra = '''
  // SKILLY_MODAL_SERVICIOS_V1
  function cerrarDetalleServicio() {
    if (cargandoDetalleServicio || accionServicio || cargandoVersion) return
    setDetalleServicio(null)
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
'''

cambios = [
    ("import { useEffect, useState } from 'react'",
     "import { useEffect, useState } from 'react'\nimport { createPortal } from 'react-dom'"),
    ("  const [errorSesion, setErrorSesion] = useState('')",
     "  const [errorSesion, setErrorSesion] = useState('')\n" + extra),
    ("Estado: {servicio.estado ?? 'Sin estado informado'}",
     "Estado: {servicio.estado_publicacion ?? servicio.estado ?? 'Sin estado informado'}"),
    ("['Estado', detalleServicio.estado],",
     "['Estado', detalleServicio.estado_publicacion ?? detalleServicio.estado],"),
    ('''            {(detalleServicio || errorDetalleServicio ||
              cargandoDetalleServicio) && (
              <section className="pp-panel pp-detalle-servicio">
                <h2>Detalle de mi servicio</h2>''',
     '''            {(detalleServicio || errorDetalleServicio ||
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
                  </div>'''),
    ('''                  onClick={() => {
                    setDetalleServicio(null)
                    setErrorDetalleServicio('')
                  }}
                >
                  Cerrar detalle''',
     '''                  onClick={cerrarDetalleServicio}
                  disabled={cargandoDetalleServicio || Boolean(accionServicio) || cargandoVersion}
                >
                  Cerrar detalle'''),
    ('''              </section>
            )}

<NuevaPropuesta onCreada={cargarServicios} />''',
     '''                </section>
              </div>,
              document.body,
            )}

<NuevaPropuesta onCreada={cargarServicios} />'''),
]

# Comprobar todas las referencias antes de modificar archivos.
for anterior, nuevo in cambios:
    if original.count(anterior) != 1:
        raise SystemExit('SEGURIDAD: Estructura distinta; no se modifico ningun archivo. Patron: ' + repr(anterior[:60]))
    original = original.replace(anterior, nuevo, 1)

if 'SKILLY_MODAL_SERVICIOS_V1' in estilos:
    raise SystemExit('SEGURIDAD: El estilo del modal ya existe; no se modifico nada.')

css_nuevo = '''

/* SKILLY_MODAL_SERVICIOS_V1 */
.pp-modal-fondo {
  position: fixed; inset: 0; z-index: 10000;
  display: flex; justify-content: center; align-items: center;
  padding: 20px; box-sizing: border-box;
  background: rgba(12, 32, 27, .72); backdrop-filter: blur(3px);
}
.pp-modal-fondo .pp-detalle-servicio {
  width: min(880px, 100%); max-height: calc(100dvh - 40px);
  margin: 0; overflow-y: auto; overscroll-behavior: contain;
  box-sizing: border-box; box-shadow: 0 24px 70px rgba(0, 0, 0, .3);
}
.pp-modal-cabecera {
  display: flex; justify-content: space-between; align-items: center; gap: 16px;
}
.pp-modal-cabecera h2 { margin: 0; }
.pp-modal-cerrar {
  width: 42px; height: 42px; flex-shrink: 0; border: 0;
  border-radius: 50%; background: #e6f0ea; color: #285d55;
  font: inherit; font-size: 27px; cursor: pointer;
}
.pp-modal-cerrar:disabled { opacity: .5; cursor: wait; }
@media (max-width: 700px) {
  .pp-modal-fondo { padding: 10px; }
  .pp-modal-fondo .pp-detalle-servicio {
    max-height: calc(100dvh - 20px); padding: 20px;
  }
}
'''

respaldo = Path('frontend') / ('respaldo_modal_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
respaldo.mkdir(parents=True)
shutil.copy2(jsx, respaldo / jsx.name)
shutil.copy2(css, respaldo / css.name)
jsx.write_text(original, encoding='utf-8')
css.write_text(estilos + css_nuevo, encoding='utf-8')
print('CORRECCION APLICADA: Ventana flotante y estado de servicio coherente.')
print('RESPALDO:', respaldo)
print('ARCHIVOS MODIFICADOS: 2; BASE DE DATOS: 0')
