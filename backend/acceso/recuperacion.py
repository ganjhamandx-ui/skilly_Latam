
"""Gestiona tokens y límites del flujo seguro de recuperación de acceso."""

import hashlib
import secrets
from datetime import timedelta, timezone as datetime_timezone

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import RecuperacionAcceso, Usuario


def convertir_fecha_bd(fecha):
    """Interpreta en UTC las fechas heredadas que carecen de zona horaria.

    Args:
        fecha (datetime): Fecha de expiración obtenida de la base de datos.

    Returns:
        datetime: Fecha con zona UTC si era ingenua; la original si ya tenía zona.
    """

    if timezone.is_naive(fecha):
        return timezone.make_aware(
            fecha,
            datetime_timezone.utc,
        )

    return fecha


def crear_recuperacion_acceso(usuario):
    """Crea una recuperación con caducidad y almacena solo la huella del token.

    Args:
        usuario (Usuario): Identidad persistida que solicita recuperar el acceso.

    Returns:
        tuple[str, RecuperacionAcceso]: Token para comunicar al usuario y registro
        creado, con vencimiento según ``RECUPERACION_MINUTOS``. Esta función no
        invalida recuperaciones anteriores ni envía el correo.
    """

    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    ahora = timezone.now()

    recuperacion = RecuperacionAcceso.objects.create(
        id_usuario=usuario,
        token_hash=token_hash,
        fecha_solicitud=ahora,
        fecha_expiracion=(
            ahora
            + timedelta(
                minutes=settings.RECUPERACION_MINUTOS
            )
        ),
        usado=False,
    )

    return token, recuperacion


def enviar_correo_recuperacion(usuario, token):
    """Envía por correo el código temporal de recuperación y su vigencia.

    Args:
        usuario (Usuario): Destinatario, identificado por su atributo ``correo``.
        token (str): Código original; no debe sustituirse por su huella almacenada.

    Returns:
        int: Número de mensajes enviados según el backend de correo de Django.

    Note:
        Los errores del backend de correo se propagan porque el envío usa
        ``fail_silently=False``; la vista decide cómo informar el fallo.
    """

    asunto = "Skilly - Recuperacion de contraseña"

    mensaje = (
        "Hola:\n\n"
        "Hemos recibido una solicitud para restablecer "
        "la contraseña de tu cuenta Skilly.\n\n"
        "Tu codigo temporal de recuperacion es:\n\n"
        f"{token}\n\n"
        "Este codigo es valido durante "
        f"{settings.RECUPERACION_MINUTOS} minutos "
        "y solo puede utilizarse una vez.\n\n"
        "No compartas este codigo con otras personas.\n\n"
        "Si no solicitaste recuperar tu contraseña, "
        "puedes ignorar este mensaje.\n\n"
        "Equipo Skilly"
    )

    return send_mail(
        subject=asunto,
        message=mensaje,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.correo],
        fail_silently=False,
    )


def _revocar_sesiones_usuario(id_usuario, ahora):
    """Elimina las sesiones de base de datos vigentes de una identidad.

    Args:
        id_usuario (int): Identificador comparado como texto con el dato de sesión.
        ahora (datetime): Umbral de vigencia; las sesiones vencidas se conservan.

    Returns:
        None: Elimina los registros coincidentes después de recorrerlos en lotes.
    """
    claves = []
    sesiones = Session.objects.filter(expire_date__gt=ahora)

    for sesion in sesiones.iterator(chunk_size=500):
        if str(sesion.get_decoded().get("id_usuario")) == str(id_usuario):
            claves.append(sesion.session_key)

    if claves:
        Session.objects.filter(session_key__in=claves).delete()


def restablecer_contrasena(token, nueva_contrasena):
    """Consume un token vigente y cambia la contraseña en una sola transacción.

    Bloquea primero al usuario y luego su recuperación para serializar cambios
    concurrentes. Al completar, inutiliza todos sus tokens pendientes y elimina
    sus sesiones de base de datos vigentes. La política de complejidad de la
    nueva contraseña debe validarse antes de invocar esta función.

    Args:
        token (str): Código original recibido por correo.
        nueva_contrasena (str): Contraseña en claro que se guarda mediante hash.

    Returns:
        tuple[bool, str]: Éxito y ``CONTRASENA_ACTUALIZADA``, o rechazo con
        ``TOKEN_INVALIDO_O_UTILIZADO`` o ``TOKEN_EXPIRADO``. Los rechazos no
        cambian la contraseña ni consumen el token.

    Raises:
        Usuario.DoesNotExist: Si la identidad referenciada desaparece antes
            de adquirir el bloqueo del usuario.
    """

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    with transaction.atomic():
        id_usuario = (
            RecuperacionAcceso.objects
            .filter(token_hash=token_hash, usado=False)
            .values_list("id_usuario_id", flat=True)
            .first()
        )

        if id_usuario is None:
            return False, "TOKEN_INVALIDO_O_UTILIZADO"

        # Serializar todos los tokens del mismo usuario antes de bloquear uno.
        # Evita bloqueos cruzados al invalidar otros tokens tras un cambio.
        usuario = Usuario.objects.select_for_update().get(pk=id_usuario)

        recuperacion = (
            RecuperacionAcceso.objects
            .select_for_update()
            .filter(
                token_hash=token_hash,
                usado=False,
                id_usuario=usuario,
            )
            .first()
        )

        if recuperacion is None:
            return False, "TOKEN_INVALIDO_O_UTILIZADO"

        fecha_expiracion = convertir_fecha_bd(
            recuperacion.fecha_expiracion
        )

        if fecha_expiracion <= timezone.now():
            return False, "TOKEN_EXPIRADO"

        usuario.password_hash = make_password(
            nueva_contrasena
        )

        usuario.fecha_actualizacion = timezone.now()

        usuario.save(
            update_fields=[
                "password_hash",
                "fecha_actualizacion",
            ]
        )

        recuperacion.usado = True

        recuperacion.save(
            update_fields=[
                "usado",
            ]
        )

        RecuperacionAcceso.objects.filter(
            id_usuario=usuario,
            usado=False,
        ).update(usado=True)

        _revocar_sesiones_usuario(usuario.pk, timezone.now())

    return True, "CONTRASENA_ACTUALIZADA"
