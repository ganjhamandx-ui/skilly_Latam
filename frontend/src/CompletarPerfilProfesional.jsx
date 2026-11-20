// Crea o actualiza los datos de presentación y contacto del perfil profesional.
import { useEffect, useState } from 'react'
import './CompletarPerfilProfesional.css'

const inicial = {
  nombres: '',
  apellidos: '',
  telefono: '',
  titulo_profesional: '',
  resumen: '',
  ubicacion: '',
}

/**
 * Selecciona el mensaje de la API o combina los errores por campo del perfil.
 * @param {Object|null} datos Respuesta JSON.
 * @param {number} codigo Estado HTTP usado si faltan detalles.
 * @returns {string} Explicación para el formulario.
 */
function mensajeError(datos, codigo) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const errores = Object.entries(datos)
      .map(([campo, valor]) =>
        `${campo}: ${Array.isArray(valor)
          ? valor.join(', ')
          : String(valor)}`,
      )
      .join(' | ')

    if (errores) return errores
  }

  return `No fue posible completar la operaci\u00f3n (HTTP ${codigo}).`
}

/**
 * Consulta si existe perfil y elige creación por POST o actualización por PATCH.
 * @param {Object} props Acciones del portal que contiene el formulario.
 * @param {function(): (void|Promise<void>)} [props.onCreado] Refresca el contenedor después de guardar,
 * tanto al crear como al actualizar; su fallo no revierte el perfil guardado.
 * @param {function(): void} [props.onVerPerfil] Navega a la consulta del perfil desde la confirmación.
 * @returns {import('react').ReactElement} Consulta inicial, formulario o resultado.
 */
export default function CompletarPerfilProfesional({ onCreado, onVerPerfil }) {
  const [consultando, setConsultando] = useState(true)
  const [sinPerfil, setSinPerfil] = useState(false)
  const [editando, setEditando] = useState(false)
  const [formulario, setFormulario] = useState(inicial)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  useEffect(() => {
    // Cancela la verificación de perfil cuando se abandona la pantalla.
    const controlador = new AbortController()

    /**
     * Trata 404 como perfil ausente y carga los campos editables cuando ya existe.
     * @returns {Promise<void>} Refleja carga y errores; la petición utiliza la señal del efecto.
     */
    async function comprobarPerfil() {
      try {
        const respuesta = await fetch(
          '/api/profesionales/mi-perfil/',
          {
            credentials: 'same-origin',
            cache: 'no-store',
            headers: { Accept: 'application/json' },
            signal: controlador.signal,
          },
        )

        if (controlador.signal.aborted) return

        if (respuesta.status === 404) {
          setSinPerfil(true)
        } else if (!respuesta.ok) {
          const datos = await respuesta.json().catch(() => ({}))
          setError(mensajeError(datos, respuesta.status))
        } else {
          const datos = await respuesta.json()
          setFormulario(Object.fromEntries(
            Object.keys(inicial).map((campo) => [campo, datos[campo] ?? '']),
          ))
          setEditando(true)
        }
      } catch (fallo) {
        if (!controlador.signal.aborted) {
          setError(
            fallo instanceof Error
              ? fallo.message
              : 'No se pudo comprobar el perfil.',
          )
        }
      } finally {
        if (!controlador.signal.aborted) {
          setConsultando(false)
        }
      }
    }

    void comprobarPerfil()

    return () => controlador.abort()
  }, [])

  /**
   * Reemplaza el campo editado sin descartar el resto del formulario.
   * @param {string} campo Nombre del dato del perfil.
   * @param {string} valor Texto introducido.
   * @returns {void}
   */
  function cambiar(campo, valor) {
    setFormulario((actual) => ({
      ...actual,
      [campo]: valor,
    }))
  }

  /**
   * Normaliza los datos y crea o actualiza el perfil con protección CSRF.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Espera onCreado si existe y presenta por separado un fallo de refresco.
   */
  async function guardar(evento) {
    evento.preventDefault()

    if (enviando || (!sinPerfil && !editando)) return

    const nombres = formulario.nombres.trim()
    const apellidos = formulario.apellidos.trim()

    if (!nombres || !apellidos) {
      setError('Debes completar tus nombres y apellidos.')
      return
    }

    setEnviando(true)
    setError('')
    setExito('')

    try {
      const respuestaCsrf = await fetch('/api/acceso/csrf/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const csrf = await respuestaCsrf.json().catch(() => ({}))

      if (!respuestaCsrf.ok || !csrf.csrfToken) {
        throw new Error('No se pudo obtener el token de seguridad.')
      }

      const respuesta = await fetch(
        editando ? '/api/profesionales/mi-perfil/' : '/api/profesionales/mi-perfil/crear/',
        {
          method: editando ? 'PATCH' : 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify({
            nombres,
            apellidos,
            telefono: formulario.telefono.trim(),
            titulo_profesional: formulario.titulo_profesional.trim(),
            resumen: formulario.resumen.trim(),
            ubicacion: formulario.ubicacion.trim(),
          }),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(mensajeError(datos, respuesta.status))
      }

      setSinPerfil(false)
      setEditando(false)
      setExito(
        datos.mensaje ?? (editando ? 'Perfil actualizado correctamente.' : 'Perfil creado correctamente.'),
      )

      if (typeof onCreado === 'function') {
        try {
          await onCreado()
        } catch {
          setExito(
            'Perfil creado. Consulta nuevamente Mi perfil para actualizarlo.',
          )
        }
      }
    } catch (fallo) {
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudo guardar el perfil.',
      )
    } finally {
      setEnviando(false)
    }
  }

  if (consultando) {
    return <p role="status">Comprobando el estado del perfil...</p>
  }

  return (
    <section className="pp-panel cpp-panel">
      {sinPerfil && (
        <>
          <p>
            Tu cuenta ya est&aacute; creada. Ahora completa
            tus datos profesionales para continuar
            con el proceso de validaci&oacute;n de Skilly.
          </p>
        </>
      )}

      {error && (
        <p className="pp-error" role="alert">{error}</p>
      )}

      {exito && (
        <div className="cpp-exito" role="status">
          <p>{exito}</p>
          {typeof onVerPerfil === 'function' && (
            <button type="button" className="pp-boton pp-secundario" onClick={onVerPerfil}>
              Volver a Mi perfil
            </button>
          )}
        </div>
      )}

      {(sinPerfil || editando) && (
        <form className="cpp-formulario" onSubmit={guardar}>
          <div className="cpp-grid">
            <div className="cpp-campo">
              <label htmlFor="cpp-nombres">Nombres *</label>
              <input
                id="cpp-nombres"
                required
                value={formulario.nombres}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('nombres', evento.target.value)
                }
              />
            </div>

            <div className="cpp-campo">
              <label htmlFor="cpp-apellidos">Apellidos *</label>
              <input
                id="cpp-apellidos"
                required
                value={formulario.apellidos}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('apellidos', evento.target.value)
                }
              />
            </div>

            <div className="cpp-campo">
              <label htmlFor="cpp-telefono">Tel&eacute;fono</label>
              <input
                id="cpp-telefono"
                type="tel"
                value={formulario.telefono}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('telefono', evento.target.value)
                }
              />
            </div>

            <div className="cpp-campo">
              <label htmlFor="cpp-titulo">T&iacute;tulo profesional</label>
              <input
                id="cpp-titulo"
                value={formulario.titulo_profesional}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('titulo_profesional', evento.target.value)
                }
              />
            </div>
          </div>

          <div className="cpp-campo">
            <label htmlFor="cpp-ubicacion">Ubicaci&oacute;n</label>
            <input
              id="cpp-ubicacion"
              value={formulario.ubicacion}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('ubicacion', evento.target.value)
              }
            />
          </div>

          <div className="cpp-campo">
            <label htmlFor="cpp-resumen">Resumen profesional</label>
            <textarea
              id="cpp-resumen"
              rows={4}
              value={formulario.resumen}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('resumen', evento.target.value)
              }
            />
          </div>

          <button
            type="submit"
            className="pp-boton"
            disabled={
              enviando ||
              !formulario.nombres.trim() ||
              !formulario.apellidos.trim()
            }
          >
            {enviando
              ? 'Guardando perfil...'
              : editando ? 'Guardar cambios' : 'Completar mi perfil'}
          </button>
        </form>
      )}
    </section>
  )
}
