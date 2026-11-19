"""Vincula las sesiones nuevas con la contraseña que las autorizó.

La autenticación compara una huella HMAC para detectar cambios de contraseña.
Las sesiones antiguas sin huella se admiten por compatibilidad y su revocación
depende del borrado de sesiones realizado durante la recuperación de acceso.
"""
from django.utils.crypto import constant_time_compare, salted_hmac


_CLAVE_VINCULO_CONTRASENA = "_skilly_password_hmac"


def _huella_contrasena(usuario):
    """Deriva un HMAC para vincular la sesión con la contraseña vigente.

    Args:
        usuario (Usuario): Identidad con clave primaria y ``password_hash``.

    Returns:
        str: Huella hexadecimal SHA-256 autenticada con la clave de Django.
    """

    return salted_hmac(
        "skilly.acceso.sesion.contrasena",
        f"{usuario.pk}:{usuario.password_hash}",
        algorithm="sha256",
    ).hexdigest()


def _vincular_sesion_con_contrasena(sesion, usuario):
    """Registra en la sesión la huella de la contraseña vigente del usuario.

    Args:
        sesion (SessionBase): Sesión modificada mediante asignación de su huella.
        usuario (Usuario): Identidad cuya contraseña autoriza la sesión.

    Returns:
        None: La persistencia queda a cargo del mecanismo de sesiones de Django.
    """

    # La sesión guarda un HMAC, nunca el hash de contraseña ni su valor original.
    sesion[_CLAVE_VINCULO_CONTRASENA] = _huella_contrasena(usuario)


def _sesion_contrasena_vigente(sesion, usuario):
    """Valida la huella de contraseña, admitiendo sesiones antiguas sin marca.

    Args:
        sesion (SessionBase): Sesión que se está autenticando; no se modifica.
        usuario (Usuario): Identidad con el hash vigente en la base de datos.

    Returns:
        bool: ``True`` si no existe marca o si coincide en tiempo constante;
        ``False`` si la marca tiene otro tipo o corresponde a otra contraseña.
    """

    if _CLAVE_VINCULO_CONTRASENA not in sesion:
        # Compatibilidad: las sesiones anteriores se revocan al restablecer por BD.
        return True

    marca = sesion[_CLAVE_VINCULO_CONTRASENA]
    return isinstance(marca, str) and constant_time_compare(
        marca, _huella_contrasena(usuario),
    )
