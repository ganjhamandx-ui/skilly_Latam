
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
    if timezone.is_naive(fecha):
        return timezone.make_aware(
            fecha,
            datetime_timezone.utc,
        )

    return fecha


def crear_recuperacion_acceso(usuario):
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
    """Revoca solo sesiones DB vigentes del usuario que restablece su acceso."""
    claves = []
    sesiones = Session.objects.filter(expire_date__gt=ahora)

    for sesion in sesiones.iterator(chunk_size=500):
        if str(sesion.get_decoded().get("id_usuario")) == str(id_usuario):
            claves.append(sesion.session_key)

    if claves:
        Session.objects.filter(session_key__in=claves).delete()


def restablecer_contrasena(token, nueva_contrasena):
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
