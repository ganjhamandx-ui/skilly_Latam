"""Configura la aplicación de autenticación y acceso de SKILLY."""

from django.apps import AppConfig


class AccesoConfig(AppConfig):
    """Inicializa la aplicación de acceso y registra sus comprobaciones de seguridad."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'acceso'

    def ready(self):
        from . import checks  # noqa: F401
