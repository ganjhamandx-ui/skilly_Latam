"""Orígenes HTTP(S) explícitos, sin Django ni lectura del entorno."""
from urllib.parse import urlsplit


ORIGEN_FRONTEND_POR_DEFECTO = "http://127.0.0.2:57744"


def _url_http(valor):
    """Interpreta un origen HTTP(S) y rechaza credenciales o caracteres de control."""

    if (not isinstance(valor, str) or not valor
            or any(ord(caracter) <= 32 or ord(caracter) == 127 for caracter in valor)
            or any(caracter in valor for caracter in ("\\", "?", "#"))):
        raise ValueError("URL HTTP(S) inválida.")
    try:
        partes = urlsplit(valor)
        puerto = partes.port
        host = partes.hostname
        if (partes.scheme not in {"http", "https"} or not host
                or partes.username is not None or partes.password is not None
                or (puerto is not None and not 1 <= puerto <= 65535) or "%" in host):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("URL HTTP(S) inválida.") from None
    return partes


def normalizar_origen_frontend(valor):
    """Devuelve el origen frontend canónico sin ruta, consulta ni fragmento."""

    partes = _url_http(valor)
    if partes.path not in {"", "/"}:
        raise ValueError("El origen frontend no debe contener una ruta.")
    host = partes.hostname
    if ":" in host:
        host = f"[{host}]"
    puerto = partes.port
    if puerto is not None and puerto != {"http": 80, "https": 443}[partes.scheme]:
        host += f":{puerto}"
    return f"{partes.scheme}://{host}"
