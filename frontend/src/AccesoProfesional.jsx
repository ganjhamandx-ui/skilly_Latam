import { useState } from 'react'
import RegistroProfesional from './RegistroProfesional'
import './AccesoProfesional.css'

const API = '/api/acceso/'

/**
 * Prioriza el mensaje del servidor y reúne errores de campo cuando no hay un detalle general.
 * @param {Object|null} datos Cuerpo JSON del rechazo.
 * @param {number} estado Código HTTP usado como diagnóstico alternativo.
 * @returns {string} Explicación apta para el formulario de acceso.
 */
function obtenerError(datos, estado) {
  if (typeof datos?.mensaje === 'string') return datos.mensaje
  if (typeof datos?.detail === 'string') return datos.detail

  if (datos && typeof datos === 'object') {
    const errores = Object.entries(datos)
      .map(([campo, valor]) => {
        // Aplana los errores por campo para explicar el rechazo del formulario.
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

  return `La operación no pudo completarse (HTTP ${estado}).`
}

/**
 * Solicita un token CSRF mediante las cookies del mismo origen.
 * @returns {Promise<string>} Token recibido de la API.
 * @throws {Error} Si falla fetch, el estado HTTP o falta csrfToken.
 */
async function obtenerCsrf() {
  const respuesta = await fetch(`${API}csrf/`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  })

  const datos = await respuesta.json().catch(() => ({}))

  if (!respuesta.ok || !datos.csrfToken) {
    throw new Error(
      'No se pudo obtener el token de seguridad CSRF.',
    )
  }

  return datos.csrfToken
}

/**
 * Obtiene CSRF y envía datos JSON a una ruta relativa del módulo de acceso.
 * @param {string} ruta Sufijo del endpoint bajo /api/acceso/.
 * @param {Object} contenido Campos del formulario aceptados por el endpoint.
 * @returns {Promise<Object>} JSON del servidor o un objeto vacío si no puede leerse.
 * @throws {Error} Si falla CSRF, la conexión o la respuesta HTTP.
 */
async function enviarFormulario(ruta, contenido) {
  const csrfToken = await obtenerCsrf()

  const respuesta = await fetch(`${API}${ruta}`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(contenido),
  })

  const datos = await respuesta.json().catch(() => ({}))

  if (!respuesta.ok) {
    throw new Error(obtenerError(datos, respuesta.status))
  }

  return datos
}

/**
 * Selecciona el destino de interfaz del rol devuelto por el inicio de sesión.
 * @param {string|undefined} rol Rol confirmado por el servidor.
 * @returns {string|null} Ruta profesional o administrativa, o null para roles no contemplados.
 */
function destinoPorRol(rol) {
  switch (rol) {
    case 'PROFESIONAL':
      return '/portal-profesional'
    case 'ADMIN_SKILLY':
      return '/administracion'
    default:
      return null
  }
}

/**
 * Coordina inicio de sesión, registro y restablecimiento con token de recuperación.
 * El rol devuelto por la API determina la navegación posterior; no se persiste la contraseña.
 * @returns {import('react').ReactElement} Pantalla de acceso y formularios asociados.
 */
export default function AccesoProfesional() {
  const [vista, setVista] = useState('acceso')
  const [mostrarRegistro, setMostrarRegistro] = useState(false)

  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [mostrarContrasena, setMostrarContrasena] = useState(false)

  const [correoRecuperacion, setCorreoRecuperacion] = useState('')
  const [codigo, setCodigo] = useState('')
  const [nuevaContrasena, setNuevaContrasena] = useState('')
  const [confirmarContrasena, setConfirmarContrasena] = useState('')
  const [mostrarNuevaContrasena, setMostrarNuevaContrasena] =
    useState(false)

  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')

  /**
   * Cambia de formulario cuando no hay petición activa y limpia mensajes y secretos escritos.
   * @param {'acceso'|'solicitar'|'restablecer'} siguiente Vista solicitada por la interfaz.
   * @returns {void} Conserva los correos previamente introducidos.
   */
  function cambiarVista(siguiente) {
    if (cargando) return

    setVista(siguiente)
    setMostrarRegistro(false)
    setError('')
    setMensaje('')
    setContrasena('')
    setCodigo('')
    setNuevaContrasena('')
    setConfirmarContrasena('')
  }

  /**
   * Inicia sesión con correo normalizado y navega según el rol confirmado por el backend.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Limpia la contraseña tanto al completar como al fallar la petición.
   */
  async function iniciarSesion(evento) {
    evento.preventDefault()

    if (cargando) return

    setCargando(true)
    setError('')
    setMensaje('')

    try {
      const datos = await enviarFormulario('iniciar-sesion/', {
        correo: correo.trim().toLowerCase(),
        contrasena,
      })

      const destino = destinoPorRol(datos.usuario?.rol)

      setContrasena('')

      if (!destino) {
        setError(
          'La cuenta no tiene un acceso habilitado en esta interfaz.',
        )
        return
      }

      window.location.assign(destino)
    } catch (error) {
      setContrasena('')
      setError(
        error instanceof Error
          ? error.message
          : 'No fue posible iniciar sesión.',
      )
    } finally {
      setCargando(false)
    }
  }

  /**
   * Solicita recuperación para el correo y abre la entrada del token tras una respuesta válida.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Muestra el mensaje genérico del servidor sin confirmar existencia de cuenta.
   */
  async function solicitarRecuperacion(evento) {
    evento.preventDefault()

    if (cargando) return

    setCargando(true)
    setError('')
    setMensaje('')

    try {
      const datos = await enviarFormulario(
        'solicitar-recuperacion/',
        {
          correo: correoRecuperacion.trim().toLowerCase(),
        },
      )

      setMensaje(
        datos.mensaje ||
          'Si la cuenta existe y está activa, se iniciará su recuperación.',
      )

      setVista('restablecer')
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : 'No fue posible solicitar la recuperación.',
      )
    } finally {
      setCargando(false)
    }
  }

  /**
   * Valida longitud y coincidencia local antes de enviar token y contraseña nueva.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Vuelve al acceso tras guardar; elimina las contraseñas también al fallar.
   */
  async function cambiarContrasena(evento) {
    evento.preventDefault()

    if (cargando) return

    setError('')
    setMensaje('')

    if (nuevaContrasena.length < 15) {
      setError(
        'La contraseña nueva debe tener al menos 15 caracteres.',
      )
      return
    }

    if (nuevaContrasena !== confirmarContrasena) {
      setError('Las contraseñas nuevas no coinciden.')
      return
    }

    setCargando(true)

    try {
      const datos = await enviarFormulario(
        'restablecer-contrasena/',
        {
          token: codigo.trim(),
          nueva_contrasena: nuevaContrasena,
          confirmar_contrasena: confirmarContrasena,
        },
      )

      setCodigo('')
      setNuevaContrasena('')
      setConfirmarContrasena('')
      setContrasena('')
      setVista('acceso')

      setMensaje(
        datos.mensaje ||
          'Contraseña actualizada. Ahora puedes iniciar sesión.',
      )
    } catch (error) {
      setNuevaContrasena('')
      setConfirmarContrasena('')

      setError(
        error instanceof Error
          ? error.message
          : 'No fue posible cambiar la contraseña.',
      )
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="ap-pagina">
      <header className="ap-cabecera">
        <a href="/" className="ap-marca">
          <svg
            width="25"
            height="25"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M12 1L14.7 9.3L23 12L14.7 14.7L12 23L9.3 14.7L1 12L9.3 9.3L12 1Z"
              fill="#447D69"
            />
          </svg>
          SKILLY
        </a>

        <a href="/#marketplace">
          Volver al marketplace
        </a>
      </header>

      <main className="ap-contenido">
        <div className="ap-presentacion">
          <span className="ap-etiqueta">
            BIENVENIDO A SKILLY
          </span>

          <h1>Tu espacio en Skilly</h1>

          <p>
            Gestiona tu acceso y continúa con tus
            actividades en la plataforma.
          </p>
        </div>

        <section className="ap-tarjeta">

          {/* El registro se abre aquí sin abandonar la pantalla de acceso. */}
          {vista === 'acceso' && (
            <>
              <h2>Iniciar sesión</h2>

              <p className="ap-ayuda">
                Ingresa el correo electrónico y la
                contraseña de tu cuenta.
              </p>

              {mensaje && (
                <div className="ap-nota">
                  <output aria-live="polite" aria-atomic="true">{mensaje}</output>
                </div>
              )}

              <form
                className="ap-formulario"
                onSubmit={iniciarSesion}
              >
                <label htmlFor="ap-correo">
                  Correo electrónico
                </label>

                <input
                  id="ap-correo"
                  type="email"
                  autoComplete="username"
                  maxLength={150}
                  placeholder="correo@ejemplo.cl"
                  value={correo}
                  onChange={(evento) =>
                    setCorreo(evento.target.value)
                  }
                  required
                  disabled={cargando}
                />

                <label htmlFor="ap-contrasena">
                  Contraseña
                </label>

                <div className="ap-contrasena-contenedor">
                  <input
                    id="ap-contrasena"
                    type={
                      mostrarContrasena
                        ? 'text'
                        : 'password'
                    }
                    autoComplete="current-password"
                    maxLength={128}
                    placeholder="Ingresa tu contraseña"
                    value={contrasena}
                    onChange={(evento) =>
                      setContrasena(evento.target.value)
                    }
                    required
                    disabled={cargando}
                  />

                  <button
                    type="button"
                    className="ap-mostrar"
                    aria-pressed={mostrarContrasena}
                    aria-controls="ap-contrasena"
                    aria-label={mostrarContrasena ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    onClick={() =>
                      setMostrarContrasena(
                        (actual) => !actual,
                      )
                    }
                    disabled={cargando}
                  >
                    {mostrarContrasena
                      ? 'Ocultar'
                      : 'Mostrar'}
                  </button>
                </div>

                {error && (
                  <div
                    className="ap-error"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="ap-enviar"
                  disabled={cargando}
                >
                  {cargando
                    ? 'Iniciando sesión...'
                    : 'Iniciar sesión'}
                </button>
              </form>

              <div className="rp-enlace-acceso">
                <button
                  type="button"
                  className="rp-boton-alternar"
                  onClick={() => {
                    setCorreoRecuperacion(correo)
                    cambiarVista('solicitar')
                  }}
                  disabled={cargando}
                >
                  ¿Olvidaste tu contraseña?
                </button>
              </div>

              <div className="rp-enlace-acceso">
                <p>
                  ¿Todavía no tienes una cuenta profesional?
                </p>

                <button
                  type="button"
                  className="rp-boton-alternar"
                  onClick={() => {
                    setMostrarRegistro(
                      (actual) => !actual,
                    )
                    setError('')
                    setMensaje('')
                  }}
                  disabled={cargando}
                >
                  {mostrarRegistro
                    ? 'Ocultar registro'
                    : 'Crear cuenta profesional'}
                </button>
              </div>

              {mostrarRegistro && (
                <RegistroProfesional
                  onRegistrado={() =>
                    setMostrarRegistro(false)
                  }
                />
              )}
            </>
          )}

          {/* El mensaje de recuperación no confirma si el correo tiene una cuenta. */}
          {vista === 'solicitar' && (
            <>
              <h2>Recuperar contraseña</h2>

              <p className="ap-ayuda">
                Ingresa el correo electrónico de tu cuenta
                Skilly. Si existe una cuenta activa y el envío
                de correos está configurado, recibirás un
                código temporal.
              </p>

              <form
                className="ap-formulario"
                onSubmit={solicitarRecuperacion}
              >
                <label htmlFor="ap-correo-recuperacion">
                  Correo electrónico
                </label>

                <input
                  id="ap-correo-recuperacion"
                  type="email"
                  autoComplete="email"
                  maxLength={150}
                  value={correoRecuperacion}
                  onChange={(evento) =>
                    setCorreoRecuperacion(
                      evento.target.value,
                    )
                  }
                  placeholder="correo@ejemplo.cl"
                  required
                  disabled={cargando}
                />

                {error && (
                  <div
                    className="ap-error"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="ap-enviar"
                  disabled={cargando}
                >
                  {cargando
                    ? 'Procesando solicitud...'
                    : 'Solicitar código'}
                </button>
              </form>

              <div className="rp-enlace-acceso">
                <button
                  type="button"
                  className="rp-boton-alternar"
                  onClick={() =>
                    cambiarVista('restablecer')
                  }
                  disabled={cargando}
                >
                  Ya tengo un código
                </button>

                <button
                  type="button"
                  className="rp-boton-alternar"
                  onClick={() =>
                    cambiarVista('acceso')
                  }
                  disabled={cargando}
                >
                  Volver a iniciar sesión
                </button>
              </div>
            </>
          )}

          {/* El código se envía como token; no se inicia sesión tras cambiar la contraseña. */}
          {vista === 'restablecer' && (
            <>
              <h2>Establecer nueva contraseña</h2>

              <p className="ap-ayuda">
                Escribe el código recibido en tu correo y
                elige una contraseña nueva. El código caduca
                a los 10 minutos y se utiliza una sola vez.
              </p>

              {mensaje && (
                <p
                  className="ap-nota"
                >
                  <output aria-live="polite" aria-atomic="true">{mensaje}</output>
                </p>
              )}

              <form
                className="ap-formulario"
                onSubmit={cambiarContrasena}
              >
                <label htmlFor="ap-codigo">
                  Código de recuperación
                </label>

                <input
                  id="ap-codigo"
                  type="text"
                  autoComplete="off"
                  spellCheck={false}
                  maxLength={255}
                  placeholder="Pega aquí el código del correo"
                  value={codigo}
                  onChange={(evento) =>
                    setCodigo(evento.target.value)
                  }
                  required
                  disabled={cargando}
                />

                <label htmlFor="ap-nueva-contrasena">
                  Contraseña nueva (mínimo 15 caracteres)
                </label>

                <input
                  id="ap-nueva-contrasena"
                  type={
                    mostrarNuevaContrasena
                      ? 'text'
                      : 'password'
                  }
                  autoComplete="new-password"
                  minLength={15}
                  maxLength={128}
                  value={nuevaContrasena}
                  onChange={(evento) =>
                    setNuevaContrasena(
                      evento.target.value,
                    )
                  }
                  required
                  disabled={cargando}
                />

                <label htmlFor="ap-confirmar-contrasena">
                  Confirmar contraseña nueva
                </label>

                <input
                  id="ap-confirmar-contrasena"
                  type={
                    mostrarNuevaContrasena
                      ? 'text'
                      : 'password'
                  }
                  autoComplete="new-password"
                  minLength={15}
                  maxLength={128}
                  value={confirmarContrasena}
                  onChange={(evento) =>
                    setConfirmarContrasena(
                      evento.target.value,
                    )
                  }
                  required
                  disabled={cargando}
                />

                <button
                  type="button"
                  className="ap-mostrar"
                  aria-pressed={mostrarNuevaContrasena}
                  aria-controls="ap-nueva-contrasena ap-confirmar-contrasena"
                  onClick={() =>
                    setMostrarNuevaContrasena(
                      (actual) => !actual,
                    )
                  }
                  disabled={cargando}
                >
                  {mostrarNuevaContrasena
                    ? 'Ocultar contraseñas'
                    : 'Mostrar contraseñas'}
                </button>

                {error && (
                  <div
                    className="ap-error"
                    role="alert"
                  >
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="ap-enviar"
                  disabled={cargando}
                >
                  {cargando
                    ? 'Actualizando...'
                    : 'Actualizar contraseña'}
                </button>
              </form>

              <div className="rp-enlace-acceso">
                <button
                  type="button"
                  className="rp-boton-alternar"
                  onClick={() =>
                    cambiarVista('solicitar')
                  }
                  disabled={cargando}
                >
                  Solicitar otro código
                </button>

                <button
                  type="button"
                  className="rp-boton-alternar"
                  onClick={() =>
                    cambiarVista('acceso')
                  }
                  disabled={cargando}
                >
                  Volver a iniciar sesión
                </button>
              </div>
            </>
          )}

          <p className="ap-nota">
            La sesión se administra mediante una cookie
            de Django. Las contraseñas y el código de
            recuperación no se guardan en el almacenamiento
            del navegador.
          </p>
        </section>
      </main>
    </div>
  )
}
