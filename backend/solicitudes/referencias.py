from django.core import signing


SEGUIMIENTO_SOLICITUD_SALT = (
    "skilly.solicitudes.seguimiento"
)


def crear_referencia_seguimiento(solicitud):
    return signing.dumps(
        {
            "id_solicitud": solicitud.id_solicitud,
            "id_contacto": solicitud.id_contacto_id,
        },
        salt=SEGUIMIENTO_SOLICITUD_SALT,
        compress=True,
    )


def leer_referencia_seguimiento(referencia):
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