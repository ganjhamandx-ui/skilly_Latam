import { useState } from 'react'
import './EditarPropuesta.css'

function texto(valor) {
  if (valor === null || valor === undefined) return ''
  if (typeof valor === 'string' || typeof valor === 'number') {
    return String(valor)
  }
  return ''
}

function obtenerCategoria(servicio) {
  const valor = servicio.id_categoria

  if (typeof valor === 'number' || typeof valor === 'string') {
    return String(valor)
  }

  if (valor && typeof valor === 'object') {
    return texto(valor.id_categoria)
  }

  return ''
}

function obtenerCompetencias(servicio) {
  const valores = servicio.ids_competencias ?? servicio.competencias

  if (!Array.isArray(valores)) return null

  const ids = valores
    .map((valor) => {
      if (typeof valor === 'number') return valor
      if (typeof valor === 'string') return Number(valor)

      if (valor && typeof valor === 'object') {
        return Number(valor.id_competencia ?? valor.id)
      }

      return NaN
    })
    .filter((id) => Number.isSafeInteger(id) && id > 0)

  return [...new Set(ids)]
}

function mensajeError(datos, codigo) {
  if (typeof datos.mensaje === 'string') return datos.mensaje
  if (typeof datos.detail === 'string') return datos.detail

  const textoErrores = Object.entries(datos)
    .map(([campo, valor]) => {
      const detalle = Array.isArray(valor)
        ? valor.join(', ')
        : typeof valor === 'string'
          ? valor
          : JSON.stringify(valor)

      return `${campo}: ${detalle}`
    })
    .join(' | ')

  return textoErrores || `Error HTTP ${codigo}`
}

export default function EditarPropuesta({
  servicio,
  idServicio,
  onActualizada,
}) {
  const categoriaOriginal = obtenerCategoria(servicio)
  const competenciasOriginales = obtenerCompetencias(servicio)

  const [abierto, setAbierto] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [cargandoCatalogos, setCargandoCatalogos] = useState(false)
  const [catalogosCargados, setCatalogosCargados] = useState(false)
  const [categorias, setCategorias] = useState([])
  const [competencias, setCompetencias] = useState([])
  const [competenciasModificadas, setCompetenciasModificadas] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  const [formulario, setFormulario] = useState(() => ({
    nombre: texto(servicio.nombre ?? servicio.nombre_servicio),
    descripcion: texto(servicio.descripcion),
    id_categoria: obtenerCategoria(servicio),
    modalidad: texto(servicio.modalidad),
    alcance: texto(servicio.alcance),
    referencia_precio: texto(servicio.referencia_precio),
    ids_competencias: obtenerCompetencias(servicio) ?? [],
  }))

  function cambiar(campo, valor) {
    setFormulario((actual) => ({
      ...actual,
      [campo]: valor,
    }))
  }

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
        throw new Error(mensajeError(datos, respuesta.status))
      }

      if (
        !Array.isArray(datos.categorias) ||
        !Array.isArray(datos.competencias)
      ) {
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

  function alternarFormulario() {
    if (!abierto && !catalogosCargados) {
      void cargarCatalogos()
    }

    setAbierto((actual) => !actual)
  }

  function alternarCompetencia(idCompetencia, seleccionado) {
    setCompetenciasModificadas(true)

    setFormulario((actual) => ({
      ...actual,
      ids_competencias: seleccionado
        ? [...new Set([...actual.ids_competencias, idCompetencia])]
        : actual.ids_competencias.filter((id) => id !== idCompetencia),
    }))
  }

  async function guardar(evento) {
    evento.preventDefault()

    if (enviando) return

    if (!['BORRADOR', 'CORRECCION_SOLICITADA'].includes(
      servicio.estado_publicacion,
    )) {
      setError('El servicio no se encuentra habilitado para edici\u00f3n.')
      return
    }

    const nombre = formulario.nombre.trim()
    const descripcion = formulario.descripcion.trim()
    const idCategoria = formulario.id_categoria.trim()

    if (!nombre || !descripcion) {
      setError('El nombre y la descripci\u00f3n son obligatorios.')
      return
    }

    if (idCategoria && (
      !Number.isSafeInteger(Number(idCategoria)) ||
      Number(idCategoria) <= 0
    )) {
      setError('Selecciona una categor\u00eda v\u00e1lida.')
      return
    }

    if (
      idCategoria !== categoriaOriginal &&
      !categorias.some((categoria) =>
        String(categoria.id_categoria) === idCategoria
      )
    ) {
      setError('Selecciona una categor\u00eda existente.')
      return
    }

    if (competenciasModificadas && !catalogosCargados) {
      setError('Debes cargar las competencias antes de modificarlas.')
      return
    }

    if (!window.confirm(
      'Confirmas guardar los cambios de esta propuesta? ' +
      'El servicio no se publicara automaticamente.',
    )) return

    setEnviando(true)
    setError('')
    setExito('')

    let actualizado = false

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
      }

      for (const campo of [
        'modalidad',
        'alcance',
        'referencia_precio',
      ]) {
        const valor = formulario[campo].trim()
        if (valor) entrada[campo] = valor
      }

      if (idCategoria && idCategoria !== categoriaOriginal) {
        entrada.id_categoria = Number(idCategoria)
      }

      if (competenciasModificadas) {
        entrada.ids_competencias = formulario.ids_competencias
      }

      const respuesta = await fetch(
        `/api/marketplace/mis-servicios/${encodeURIComponent(idServicio)}/`,
        {
          method: 'PATCH',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfDatos.csrfToken,
          },
          body: JSON.stringify(entrada),
        },
      )

      const datos = await respuesta.json().catch(() => ({}))

      if (!respuesta.ok) {
        throw new Error(mensajeError(datos, respuesta.status))
      }

      actualizado = true
      setAbierto(false)
      setCompetenciasModificadas(false)
      setExito(
        typeof datos.mensaje === 'string'
          ? datos.mensaje
          : 'Propuesta actualizada correctamente.',
      )

      if (typeof onActualizada === 'function') {
        try {
          await onActualizada()
        } catch {
          setExito(
            'Cambios guardados. Vuelve a consultar el detalle para actualizarlos.',
          )
        }
      }
    } catch (fallo) {
      if (!actualizado) {
        setError(
          fallo instanceof Error
            ? fallo.message
            : 'No se pudo actualizar la propuesta.',
        )
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="ep-contenedor">
      <div className="ep-cabecera">
        <div>
          <h3>Editar propuesta</h3>
          <p>
            Corrige el servicio antes de enviarlo a revisi&oacute;n.
            Los cambios no publican el servicio.
          </p>
        </div>

        <button
          type="button"
          className="pp-boton pp-secundario"
          disabled={enviando}
          onClick={alternarFormulario}
        >
          {abierto ? 'Ocultar edici\u00f3n' : 'Editar propuesta'}
        </button>
      </div>

      {error && (
        <div className="ep-error">
          <p role="alert">{error}</p>
          {abierto && !catalogosCargados && (
            <button
              type="button"
              className="pp-boton pp-secundario"
              disabled={cargandoCatalogos}
              onClick={cargarCatalogos}
            >
              Reintentar cat&aacute;logos
            </button>
          )}
        </div>
      )}

      {exito && (
        <p role="status" className="ep-exito">{exito}</p>
      )}

      {abierto && (
        <form className="ep-formulario" onSubmit={guardar}>
          {cargandoCatalogos && (
            <p role="status">Cargando categor&iacute;as y competencias...</p>
          )}

          <div className="ep-campo">
            <label htmlFor="ep-nombre">Nombre del servicio *</label>
            <input
              id="ep-nombre"
              type="text"
              required
              value={formulario.nombre}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('nombre', evento.target.value)
              }
            />
          </div>

          <div className="ep-campo">
            <label htmlFor="ep-descripcion">Descripci&oacute;n *</label>
            <textarea
              id="ep-descripcion"
              rows={5}
              required
              value={formulario.descripcion}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('descripcion', evento.target.value)
              }
            />
          </div>

          <div className="ep-grid">
            <div className="ep-campo">
              <label htmlFor="ep-categoria">Categor&iacute;a</label>
              <select
                id="ep-categoria"
                value={formulario.id_categoria}
                disabled={enviando || !catalogosCargados}
                onChange={(evento) =>
                  cambiar('id_categoria', evento.target.value)
                }
              >
                <option value="">Conservar categor&iacute;a actual</option>
                {formulario.id_categoria &&
                  !categorias.some((categoria) =>
                    String(categoria.id_categoria) ===
                      String(formulario.id_categoria)
                  ) && (
                    <option value={formulario.id_categoria}>
                      Categor&iacute;a actual #{formulario.id_categoria}
                    </option>
                  )}
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

            <div className="ep-campo">
              <label htmlFor="ep-modalidad">Modalidad</label>
              <input
                id="ep-modalidad"
                type="text"
                value={formulario.modalidad}
                disabled={enviando}
                onChange={(evento) =>
                  cambiar('modalidad', evento.target.value)
                }
              />
            </div>
          </div>

          <div className="ep-campo">
            <label htmlFor="ep-alcance">Alcance</label>
            <textarea
              id="ep-alcance"
              rows={3}
              value={formulario.alcance}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('alcance', evento.target.value)
              }
            />
          </div>

          <div className="ep-campo">
            <label htmlFor="ep-precio">Precio referencial propuesto</label>
            <input
              id="ep-precio"
              type="text"
              value={formulario.referencia_precio}
              disabled={enviando}
              onChange={(evento) =>
                cambiar('referencia_precio', evento.target.value)
              }
            />
            <small>
              El precio final requiere la revisi&oacute;n de Skilly.
            </small>
          </div>

          <fieldset className="ep-competencias">
            <legend>Competencias asociadas</legend>

            {competenciasOriginales === null && (
              <p className="ep-aviso">
                El detalle no informa las competencias actuales.
                Si no modificas estas opciones, se conservar&aacute;n
                las asociaciones registradas.
              </p>
            )}

            <div className="ep-opciones">
              {competencias.map((competencia) => {
                const id = Number(competencia.id_competencia)

                return (
                  <label
                    key={competencia.id_competencia}
                    className="ep-opcion"
                  >
                    <input
                      type="checkbox"
                      disabled={enviando || !catalogosCargados}
                      checked={formulario.ids_competencias.includes(id)}
                      onChange={(evento) =>
                        alternarCompetencia(id, evento.target.checked)
                      }
                    />
                    <span>{competencia.nombre}</span>
                  </label>
                )
              })}

              {catalogosCargados && competencias.length === 0 && (
                <p>No hay competencias disponibles.</p>
              )}
            </div>
          </fieldset>

          <button
            type="submit"
            className="pp-boton"
            disabled={
              enviando ||
              !formulario.nombre.trim() ||
              !formulario.descripcion.trim() ||
              !catalogosCargados
            }
          >
            {enviando
              ? 'Guardando cambios...'
              : 'Guardar cambios de propuesta'}
          </button>
        </form>
      )}
    </section>
  )
}
