"""Vinculo privado de las sesiones nuevas con la contrasena que las autorizo."""
from django.utils.crypto import constant_time_compare, salted_hmac


_CLAVE_VINCULO_CONTRASENA = "_skilly_password_hmac"


def _huella_contrasena(usuario):
    return salted_hmac(
        "skilly.acceso.sesion.contrasena",
        f"{usuario.pk}:{usuario.password_hash}",
        algorithm="sha256",
    ).hexdigest()


def _vincular_sesion_con_contrasena(sesion, usuario):
    # La sesion guarda un HMAC, nunca el hash de contrasena ni su valor original.
    sesion[_CLAVE_VINCULO_CONTRASENA] = _huella_contrasena(usuario)


def _sesion_contrasena_vigente(sesion, usuario):
    if _CLAVE_VINCULO_CONTRASENA not in sesion:
        # Compatibilidad: las sesiones anteriores se revocan al restablecer por BD.
        return True

    marca = sesion[_CLAVE_VINCULO_CONTRASENA]
    return isinstance(marca, str) and constant_time_compare(
        marca, _huella_contrasena(usuario),
    )
