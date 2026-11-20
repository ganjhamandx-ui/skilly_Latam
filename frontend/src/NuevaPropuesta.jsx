// Crea propuestas con categorías y competencias válidas antes de enviarlas a revisión.
import { useState } from 'react'
import './NuevaPropuesta.css'

const formularioInicial = {
  nombre: '',
  descripcion: '',
  id_categoria: '',
  modalidad: '',
  alcance: '',
  referencia_precio: '',
  ids_competencias: [],
}

/**
 * Compone un mensaje de rechazo a partir del detalle general o los errores de campo.
 * @param {Object} datos Cuerpo JSON recibido de la API.
 * @param {number} codigo Estado HTTP usado si el cuerpo no aporta detalles.
 * @returns {string} Explicación del error al crear la propuesta.
 */
function obtenerError(datos, codigo) {
  if (typeof datos.mensaje === 'string') return datos.mensaje
  if (typeof datos.detail === 'string') return datos.detail

  const campos = Object.entries(datos)
    .map(([campo, valor]) => {
      // Conserva el nombre del campo para identificar qué dato rechazó el servidor.
      const texto = Array.isArray(valor)
        ? valor.join(', ')
        : typeof valor === 'string'
          ? valor
          : JSON.stringify(valor)

      return `${campo}: ${texto}`
    })
    .join(' | ')

  return campos || `Error HTTP ${codigo}`
}

/**
 * Carga catálogos al abrir y permite crear la primera versión del servicio como borrador.
 * @param {Object} props Integración con el listado del portal profesional.
 * @param {function(): (void|Promise<void>)} [props.onCreada] Refresca el listado después del alta;
 * un fallo de este callback no se presenta como un fallo al crear el servicio.
 * @returns {import('react').ReactElement} Formulario desplegable y mensajes de resultado.
 */
export default function NuevaPropuesta({ onCreada }) {
  const [formulario, setFormulario] = useState(formularioInicial)
  const [abierto, setAbierto] = useState(false)
  const [categorias, setCategorias] = useState([])
  const [competencias, setCompetencias] = useState([])
  const [cargandoCatalogos, setCargandoCatalogos] = useState(false)
  const [catalogosCargados, setCatalogosCargados] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  /**
   * Actualiza un dato del borrador preservando los demás campos.
   * @param {string} campo Clave del formulario.
   * @param {string|number[]} valor Valor introducido o selección de identificadores.
   * @returns {void}
   */
  function cambiar(campo, valor) {
    setFormulario((actual) => ({
      ...actual,
      [campo]: valor,
    }))
  }

  /**
   * Consulta categorías y competencias y exige que ambas colecciones sean listas.
   * @returns {Promise<void>} Conserva catálogos válidos o muestra el fallo para permitir reintentar.
   */
  async function cargarCatalogos() {
    if (cargandoCatalogos) return

    setCargandoCatalogos(true)
    setError('')

    try {
      const respuesta = await fetch('/api/marketplace/catalogos/', {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerError(datos, respuesta.status))
      }

      if (!Array.isArray(datos.categorias) ||
          !Array.isArray(datos.competencias)) {
        throw new Error('La API devolvi\u00f3 cat\u00e1logos incompletos.')
      }

      setCategorias(datos.categorias)
      setCompetencias(datos.competencias)
      setCatalogosCargados(true)
    } catch (fallo) {
      setCatalogosCargados(false)
      setError(
        fallo instanceof Error
          ? fallo.message
          : 'No se pudieron cargar los cat\u00e1logos.',
      )
    } finally {
      setCargandoCatalogos(false)
    }
  }

  /**
   * Alterna el formulario e inicia la carga de catálogos al abrir si todavía no están disponibles.
   * @returns {void} No espera la consulta ni envía el borrador.
   */
  function alternarFormulario() {
    if (!abierto && !catalogosCargados) {
      void cargarCatalogos()
    }
    setAbierto((actual) => !actual)
  }

  /**
   * Agrega la competencia marcada o elimina todas sus coincidencias al desmarcar.
   * @param {number} idCompetencia Identificador del control de selección.
   * @param {boolean} seleccionado Estado de la casilla; la rama de alta no elimina duplicados previos.
   * @returns {void}
   */
  function alternarCompetencia(idCompetencia, seleccionado) {
    setFormulario((actual) => ({
      ...actual,
      ids_competencias: seleccionado
        ? [...actual.ids_competencias, idCompetencia]
        : actual.ids_competencias.filter((id) => id !== idCompetencia),
    }))
  }

  /**
   * Valida nombre, descripción y categoría local antes de confirmar y crear el borrador con CSRF.
   * @param {import('react').FormEvent} evento Envío del formulario que se cancela.
   * @returns {Promise<void>} Limpia el borrador y espera onCreada al guardar; los errores se muestran localmente.
   */
  async function guardar(evento) {
    evento.preventDefault()

    if (enviando) return

    const nombre = formulario.nombre.trim()
    const descripcion = formulario.descripcion.trim()
    const idCategoria = Number(formulario.id_categoria)

    if (!nombre || !descripcion ||
        !Number.isSafeInteger(idCategoria) || idCategoria <= 0 ||
        !categorias.some((item) =>
          Number(item.id_categoria) === idCategoria
        )) {
      setError('Selecciona una categor\u00eda v\u00e1lida y completa los campos obligatorios.')
      return
    }

    if (!window.confirm(
      'Confirmas crear la propuesta como borrador? No se publicara todavia.',
    )) return

    setEnviando(true)
    setError('')
    setExito('')

    let creada = false

    try {
      const csrfRespuesta = await fetch('/api/acceso/csrf/', {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      })

      const csrfDatos = await csrfRespuesta.json().catch(() => ({}))

      if (!csrfRespuesta.ok || !csrfDatos.csrfToken) {
        throw new Error('No se pudo obtener el token CSRF.')
      }

      const entrada = {
        nombre,
        descripcion,
        id_categoria: idCategoria,
        ids_competencias: formulario.ids_competencias,
      }

      for (const campo of [
        'modalidad',
        'alcance',
        'referencia_precio',
      ]) {
        const valor = formulario[campo].trim()
        if (valor) entrada[campo] = valor
      }

      const respuesta = await fetch('/api/marketplace/mis-servicios/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfDatos.csrfToken,
        },
        body: JSON.stringify(entrada),
      })

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(obtenerError(datos, respuesta.status))
      }

      creada = true
      setFormulario(formularioInicial)
      setAbierto(false)
      setExito(
        typeof datos.mensaje === 'string'
          ? datos.mensaje
          : 'Propuesta creada correctamente.',
      )

      if (typeof onCreada === 'function') {
        try {
          await onCreada()
        } catch {
          setExito(
            'Propuesta creada. Consulta Mis servicios para actualizar el listado.',
          )
        }
      }
    } catch (fallo) {
      if (!creada) {
        setError(
          fallo instanceof Error
            ? fallo.message
            : 'No fue posible registrar la propuesta.',
        )
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="pp-panel np-panel">
      <div className="np-encabezado">
        <div>
          <span className="pp-etiqueta">MARKETPLACE PROFESIONAL</span>
          <p>
            Prop&oacute;n tu servicio a Skilly. Se guardar&aacute;
            como borrador hasta completar el proceso de revisi&oacute;n.
          </p>
        </div>

        <button
          type="button"
          className="pp-boton"
          onClick={alternarFormulario}
          disabled={enviando}
        >
          {abierto ? 'Ocultar formulario' : 'Nueva propuesta'}
        </button>
      </div>

      {error && (
        <div className="np-error">
          <p role="alert">{error}</p>
          {abierto && !catalogosCargados && (
            <button
              type="button"
              className="pp-boton pp-secundario"
              onClick={cargarCatalogos}
              disabled={cargandoCatalogos}
            >
              Reintentar carga de cat&aacute;logos
            </button>
          )}
        </div>
      )}

      {exito && (
        <p role="status" className="np-exito">{exito}</p>
      )}

      {abierto && (
        <form className="np-formulario" onSubmit={guardar}>
          {cargandoCatalogos && (
            <p role="status">Cargando categor&iacute;as y competencias...</p>
          )}

          <div className="np-campo">
            <label htmlFor="np-nombre">Nombre del servicio *</label>
            <input
              id="np-nombre"
              type="text"
              required
              value={formulario.nombre}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('nombre', evento.target.value)
              }
              placeholder="Nombre del servicio"
            />
          </div>

          <div className="np-campo">
            <label htmlFor="np-descripcion">Descripci&oacute;n *</label>
            <textarea
              id="np-descripcion"
              rows={5}
              required
              value={formulario.descripcion}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('descripcion', evento.target.value)
              }
              placeholder="Describe el servicio propuesto"
            />
          </div>

          <div className="np-dos-columnas">
            <div className="np-campo">
              <label htmlFor="np-categoria">Categor&iacute;a *</label>
              <select
                id="np-categoria"
                required
                value={formulario.id_categoria}
                disabled={enviando || !catalogosCargados}
                onChange={(evento) =>
                  cambiar('id_categoria', evento.target.value)
                }
              >
                <option value="">Selecciona una categor&iacute;a</option>
                {categorias.map((categoria) => (
                  <option
                    key={categoria.id_categoria}
                    value={categoria.id_categoria}
                  >
                    {categoria.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="np-campo">
              <label htmlFor="np-modalidad">Modalidad</label>
              <input
                id="np-modalidad"
                type="text"
                value={formulario.modalidad}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('modalidad', evento.target.value)
                }
                placeholder="Remota, presencial u otra"
              />
            </div>
          </div>

          <div className="np-campo">
            <label htmlFor="np-alcance">Alcance</label>
            <textarea
              id="np-alcance"
              rows={3}
              value={formulario.alcance}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('alcance', evento.target.value)
              }
              placeholder="Alcance y entregables"
            />
          </div>

          <div className="np-dos-columnas">
            <div className="np-campo">
              <label htmlFor="np-precio">Precio referencial</label>
              <input
                id="np-precio"
                type="text"
                value={formulario.referencia_precio}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('referencia_precio', evento.target.value)
                }
                placeholder="Precio propuesto"
              />
              <small>
                Skilly revisar&aacute; el precio antes de publicar.
              </small>
            </div>

            <fieldset className="np-competencias">
              <legend>Competencias (opcional)</legend>

              <div className="np-opciones">
                {competencias.map((competencia) => (
                  <label
                    key={competencia.id_competencia}
                    className="np-opcion"
                  >
                    <input
                      type="checkbox"
                      disabled={enviando}
                      checked={formulario.ids_competencias.includes(
                        Number(competencia.id_competencia),
                      )}
                      onChange={(evento) =>
                        alternarCompetencia(
                          Number(competencia.id_competencia),
                          evento.target.checked,
                        )
                      }
                    />
                    <span>{competencia.nombre}</span>
                  </label>
                ))}

                {catalogosCargados && competencias.length === 0 && (
                  <p>No hay competencias disponibles.</p>
                )}
              </div>
            </fieldset>
          </div>

          {catalogosCargados && categorias.length === 0 && (
            <p role="status">
              No hay categor&iacute;as disponibles para crear propuestas.
            </p>
          )}

          <button
            type="submit"
            className="pp-boton"
            disabled={
              enviando ||
              !catalogosCargados ||
              categorias.length === 0 ||
              !formulario.nombre.trim() ||
              !formulario.descripcion.trim() ||
              !formulario.id_categoria
            }
          >
            {enviando
              ? 'Guardando propuesta...'
              : 'Guardar propuesta como borrador'}
          </button>
        </form>
      )}
    </section>
  )
}
