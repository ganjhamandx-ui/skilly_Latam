"""Crea de forma interactiva una cuenta administrativa local de SKILLY."""

from getpass import getpass

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.utils import timezone

from acceso.models import Usuario


class Command(BaseCommand):
    """Crea de forma interactiva una cuenta administrativa interna sin exponer claves."""

    help = "Crea una cuenta interna con rol ADMIN_SKILLY."

    def handle(self, *args, **options):
        self.stdout.write("Creación interna de cuenta ADMIN_SKILLY")
        self.stdout.write("")

        correo = input("Correo del administrador: ").strip().lower()

        try:
            validate_email(correo)
        except ValidationError:
            self.stderr.write(
                self.style.ERROR("El correo ingresado no es válido.")
            )
            return

        if Usuario.objects.filter(correo__iexact=correo).exists():
            self.stderr.write(
                self.style.ERROR(
                    "Ya existe una cuenta registrada con ese correo."
                )
            )
            return

        contrasena = getpass("Contraseña: ")
        confirmar = getpass("Confirmar contraseña: ")

        if contrasena != confirmar:
            self.stderr.write(
                self.style.ERROR("Las contraseñas no coinciden.")
            )
            return

        try:
            validate_password(contrasena)
        except ValidationError as error:
            self.stderr.write(
                self.style.ERROR("La contraseña no cumple las políticas:")
            )

            for mensaje in error.messages:
                self.stderr.write(f"- {mensaje}")

            return

        ahora = timezone.now()

        usuario = Usuario.objects.create(
            correo=correo,
            password_hash=make_password(contrasena),
            rol="ADMIN_SKILLY",
            estado="ACTIVO",
            fecha_creacion=ahora,
            fecha_actualizacion=ahora,
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Cuenta ADMIN_SKILLY creada correctamente."
            )
        )
        self.stdout.write(f"ID: {usuario.id_usuario}")
        self.stdout.write(f"CORREO: {usuario.correo}")
        self.stdout.write(f"ROL: {usuario.rol}")
        self.stdout.write(f"ESTADO: {usuario.estado}")
