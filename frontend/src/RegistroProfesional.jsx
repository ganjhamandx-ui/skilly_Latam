// Registra la cuenta profesional con validaciones locales complementarias a las del servidor.
import { useState } from 'react'
import './RegistroProfesional.css'

const inicial = {
  correo: '',
  contrasena: '',
  confirmar_contrasena: '',
  nombres: '',
  apellidos: '',
  telefono: '',
  titulo_profesional: '',
  ubicacion: '',
  resumen: '',
}

/**
 * Convierte mensajes generales o errores por campo en una explicación del rechazo.
 * @param {Object|null} datos Respuesta JSON del registro.
 * @param {number} estado Código HTTP si no hay detalle del servidor.
 * @returns {string} Mensaje de error para el formulario.
 */
function obtenerError(datos, estado) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const errores = Object.entries(datos)
      .map(([campo, valor]) => {
        // Compone errores por campo para orientar la corrección del registro.
        const detalle = Array.isArray(valor)
          ? valor.join(', ')
          : typeof valor === 'string'
            ? valor
            : JSON.stringify(valor)

        return `${campo}: ${detalle}`
      })
      .join(' | ')

    if (errores) return errores
  }

  return `No se pudo crear la cuenta (HTTP ${estado}).`
}

/**
 * Registra cuenta y perfil mediante el endpoint de alta profesional.
 * @param {Object} props Acciones del contenedor del formulario.
 * @param {function(): void} [props.onRegistrado] Se invoca al pulsar el botón para volver al acceso,
 * no automáticamente al completar el registro.
 * @returns {import('react').ReactElement} Formulario o confirmación del alta.
 */
export default function RegistroProfesional({ onRegistrado }) {
  const [formulario, setFormulario] = useState(inicial)
  const [mostrarClave, setMostrarClave] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  /**
   * Actualiza un campo conservando los demás datos introducidos.
   * @param {string} campo Clave del formulario.
   * @param {string} valor Texto recibido del control.
   * @returns {void}
   */
  function cambiar(campo, valor) {
    setFormulario((actual) => ({
      ...actual,
      [campo]: valor,
    }))
  }

  /**
   * Comprueba campos obligatorios y coincidencia de contraseñas antes del alta protegida por CSRF.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Vacía el formulario al guardar o muestra el rechazo del servidor.
   */
  async function registrar(evento) {
    evento.preventDefault()

    if (enviando) return

    if (
      !formulario.correo.trim() ||
      !formulario.nombres.trim() ||
      !formulario.apellidos.trim() ||
      !formulario.contrasena ||
      !formulario.confirmar_contrasena
    ) {
      setError('Completa todos los campos obligatorios.')
      return
    }

    if (
      formulario.contrasena !==
      formulario.confirmar_contrasena
    ) {
      setError('Las contrase\u00f1as no coinciden.')
      return
    }

    setEnviando(true)
    setError('')
    setExito('')

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const csrf = await csrfRespuesta.json().catch(() => ({}))

      if (!csrfRespuesta.ok || !csrf.csrfToken) {
        throw new Error('No se pudo obtener el token CSRF.')
      }

      const entrada = {
        correo: formulario.correo.trim().toLowerCase(),
        contrasena: formulario.contrasena,
        confirmar_contrasena: formulario.confirmar_contrasena,
        nombres: formulario.nombres.trim(),
        apellidos: formulario.apellidos.trim(),
        telefono: formulario.telefono.trim(),
        titulo_profesional: formulario.titulo_profesional.trim(),
        ubicacion: formulario.ubicacion.trim(),
        resumen: formulario.resumen.trim(),
      }

      const respuesta = await fetch(
        '/api/acceso/registro-profesional/',
        {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf.csrfToken,
          },
          body: JSON.stringify(entrada),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerError(datos, respuesta.status))
      }

      setFormulario(inicial)
      setExito(
        typeof datos.mensaje === 'string'
          ? datos.mensaje
          : 'Cuenta profesional creada correctamente.',
      )
    } catch (fallo) {
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No fue posible crear la cuenta.',
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="rp-registro">
      <h2>Crear cuenta profesional</h2>

      <p>
        Registra tus datos personales y profesionales.
        Tu perfil comenzar&aacute; pendiente de validaci&oacute;n
        por parte de Skilly.
      </p>

      {error && (
        <p className="rp-error" role="alert">{error}</p>
      )}

      {exito ? (
        <div className="rp-exito" role="status">
          <p>{exito}</p>
          <p>
            Tu cuenta y tu perfil profesional ya est&aacute;n
            registrados. Puedes iniciar sesi&oacute;n.
          </p>

          <button
            type="button"
            className="rp-boton-principal"
            onClick={() => onRegistrado?.()}
          >
            Ir al inicio de sesi&oacute;n
          </button>
        </div>
      ) : (
        <form className="rp-formulario" onSubmit={registrar}>
          <h3>Datos de acceso</h3>

          <label htmlFor="rp-correo">Correo electr&oacute;nico *</label>
          <input
            id="rp-correo"
            type="email"
            required
            maxLength={150}
            autoComplete="email"
            value={formulario.correo}
            disabled={enviando}
            onChange={(evento) =>
              cambiar('correo', evento.target.value)
            }
          />

          <div className="rp-dos-columnas">
            <div className="rp-campo">
              <label htmlFor="rp-clave">Contrase&ntilde;a *</label>
              <input
                id="rp-clave"
                type={mostrarClave ? 'text' : 'password'}
                required
                maxLength={128}
                autoComplete="new-password"
                value={formulario.contrasena}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('contrasena', evento.target.value)
                }
              />
            </div>

            <div className="rp-campo">
              <label htmlFor="rp-confirmar">
                Confirmar contrase&ntilde;a *
              </label>
              <input
                id="rp-confirmar"
                type={mostrarClave ? 'text' : 'password'}
                required
                maxLength={128}
                autoComplete="new-password"
                value={formulario.confirmar_contrasena}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('confirmar_contrasena', evento.target.value)
                }
              />
            </div>
          </div>

          <label className="rp-mostrar">
            <input
              type="checkbox"
              checked={mostrarClave}
              onChange={(evento) =>
                setMostrarClave(evento.target.checked)
              }
            />
            Mostrar contrase&ntilde;as
          </label>

          <h3>Datos personales</h3>

          <div className="rp-dos-columnas">
            <div className="rp-campo">
              <label htmlFor="rp-nombres">Nombres *</label>
              <input
                id="rp-nombres"
                required
                value={formulario.nombres}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('nombres', evento.target.value)
                }
              />
            </div>

            <div className="rp-campo">
              <label htmlFor="rp-apellidos">Apellidos *</label>
              <input
                id="rp-apellidos"
                required
                value={formulario.apellidos}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('apellidos', evento.target.value)
                }
              />
            </div>
          </div>

          <label htmlFor="rp-telefono">Tel&eacute;fono</label>
          <input
            id="rp-telefono"
            type="tel"
            value={formulario.telefono}
            disabled={enviando}
            onChange={(evento) =>
              cambiar('telefono', evento.target.value)
            }
          />

          <h3>Datos profesionales</h3>

          <label htmlFor="rp-titulo">T&iacute;tulo profesional</label>
          <input
            id="rp-titulo"
            value={formulario.titulo_profesional}
            disabled={enviando}
            onChange={(evento) =>
              cambiar('titulo_profesional', evento.target.value)
            }
          />

          <label htmlFor="rp-ubicacion">Ubicaci&oacute;n</label>
          <input
            id="rp-ubicacion"
            value={formulario.ubicacion}
            disabled={enviando}
            onChange={(evento) =>
              cambiar('ubicacion', evento.target.value)
            }
          />

          <label htmlFor="rp-resumen">Resumen profesional</label>
          <textarea
            id="rp-resumen"
            rows={4}
            value={formulario.resumen}
            disabled={enviando}
            onChange={(evento) =>
              cambiar('resumen', evento.target.value)
            }
            placeholder="Describe tu experiencia y especialidad"
          />

          <p className="rp-nota">
            Los campos con * son obligatorios.
            La creaci&oacute;n de la cuenta no implica
            aprobaci&oacute;n profesional autom&aacute;tica.
          </p>

          <button
            type="submit"
            className="rp-boton-principal"
            disabled={
              enviando ||
              !formulario.correo.trim() ||
              !formulario.nombres.trim() ||
              !formulario.apellidos.trim() ||
              !formulario.contrasena ||
              !formulario.confirmar_contrasena
            }
          >
            {enviando
              ? 'Creando cuenta...'
              : 'Crear mi cuenta profesional'}
          </button>
        </form>
      )}
    </section>
  )
}
