"""Descarga controlada de documentos profesionales.

No publica MEDIA_URL: todas las descargas exigen autenticacion en sus vistas.
No mueve ni renombra archivos previamente cargados.
"""

from pathlib import PurePosixPath

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404

PREFIJO_PRIVADO = "skilly/documentos_profesionales/"
PREFIJO_LEGADO = "demo/documentos/"
TIPOS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}


def referencia_autorizada(documento):
    """Acepta solo rutas internas conocidas asociadas al profesional propietario.

    El prefijo legado existe unicamente para registros sinteticos antiguos;
    no implica que el archivo exista realmente en el almacenamiento.
    """
    referencia = str(documento.referencia_archivo or "")
    if not referencia or "\\" in referencia or "\x00" in referencia:
        raise Http404("Referencia de archivo invalida.")

    ruta = PurePosixPath(referencia)
    if ruta.is_absolute() or any(p in {".", "..", ""} for p in referencia.split("/")):
        raise Http404("Referencia de archivo invalida.")

    prefijo = f"{PREFIJO_PRIVADO}{documento.id_profesional_id}/"
    nueva = referencia.startswith(prefijo) and len(referencia) > len(prefijo)

    # Solo los documentos legados con un nombre simple, sin subcarpetas.
    legado = False
    if referencia.startswith(PREFIJO_LEGADO):
        nombre = referencia[len(PREFIJO_LEGADO):]
        legado = bool(nombre) and all(
            letra.isascii() and (letra.isalnum() or letra in "-_.")
            for letra in nombre
        ) and nombre not in {".", ".."} and referencia.count("/") == 2

    if not (nueva or legado) or ruta.suffix.lower() not in TIPOS:
        raise Http404("Referencia de archivo no permitida.")

    return referencia, TIPOS[ruta.suffix.lower()]


def respuesta_documento_privado(documento, *, visualizar=False):
    referencia, tipo = referencia_autorizada(documento)
    if not default_storage.exists(referencia):
        raise Http404("El archivo fisico de este registro no esta disponible.")

    try:
        archivo = default_storage.open(referencia, "rb")
    except (FileNotFoundError, OSError):
        raise Http404("El archivo fisico de este registro no esta disponible.")

    respuesta = FileResponse(
        archivo,
        as_attachment=not visualizar,
        filename=documento.nombre_archivo,
        content_type=tipo,
    )
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Referrer-Policy"] = "no-referrer"
    return respuesta
