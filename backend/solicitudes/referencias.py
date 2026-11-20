"""Firma referencias privadas que vinculan una solicitud y su contacto empresarial.

La firma impide alterar identificadores sin invalidarlos; no cifra el contenido.
Quien posee una referencia válida puede consultar los endpoints de seguimiento
que la aceptan. Este módulo no configura una caducidad temporal de lectura.
"""

from django.core import signing


SEGUIMIENTO_SOLICITUD_SALT = (
    "skilly.solicitudes.seguimiento"
)


def crear_referencia_seguimiento(solicitud):
    """Firma los identificadores de solicitud y contacto para el seguimiento.

    Args:
        solicitud (SolicitudServicio): Solicitud persistida con contacto asociado.

    Returns:
        str: Referencia firmada y opcionalmente comprimida por Django. Su contenido
        es decodificable; la protección es de integridad, no de confidencialidad.
    """

    return signing.dumps(
        {
            "id_solicitud": solicitud.id_solicitud,
            "id_contacto": solicitud.id_contacto_id,
        },
        salt=SEGUIMIENTO_SOLICITUD_SALT,
        compress=True,
    )


def leer_referencia_seguimiento(referencia):
    """Verifica la firma y la estructura de los identificadores de seguimiento.

    Args:
        referencia (str): Referencia emitida con el salt de seguimiento de solicitudes.

    Returns:
        dict | None: Id de solicitud y contacto si cumplen la comprobación de
        enteros positivos; ``None`` ante BadSignature o estructura inválida.
        No consulta la base de datos ni aplica max_age a la firma.
    """

    try:
        datos = signing.loads(
            referencia,
            salt=SEGUIMIENTO_SOLICITUD_SALT,
        )
    except signing.BadSignature:
        return None

    if not isinstance(datos, dict):
        return None

    id_solicitud = datos.get(
        "id_solicitud"
    )

    id_contacto = datos.get(
        "id_contacto"
    )

    if (
        not isinstance(id_solicitud, int)
        or id_solicitud <= 0
        or not isinstance(id_contacto, int)
        or id_contacto <= 0
    ):
        return None

    return {
        "id_solicitud": id_solicitud,
        "id_contacto": id_contacto,
    }
