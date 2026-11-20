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
    """Acepta rutas internas conocidas del documento y determina su tipo MIME.

    El prefijo legado se conserva para registros sintéticos antiguos y no
    acredita la existencia física del archivo. Esta función valida la ruta;
    la vista debe comprobar previamente quién puede consultar el documento.

    Args:
        documento: Registro con referencia_archivo e id_profesional_id.

    Returns:
        tuple[str, str]: Referencia relativa y tipo MIME permitido.

    Raises:
        Http404: Si la ruta contiene segmentos inseguros, no pertenece a un
            prefijo admitido o no termina en .pdf, .jpg o .png.
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
    """Abre un documento autorizado sin exponer una URL pública del almacén.

    Args:
        documento: Registro cuyo acceso ya fue autorizado por la vista.
        visualizar (bool): Si es True, solicita presentación en línea;
            de lo contrario, devuelve el archivo como adjunto.

    Returns:
        FileResponse: Flujo binario con nombre original, tipo MIME y cabeceras
        que impiden su almacenamiento en caché y la inferencia de contenido.

    Raises:
        Http404: Si la referencia no es válida, el archivo no existe o su
            apertura produce FileNotFoundError u OSError.
    """
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
