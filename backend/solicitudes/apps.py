"""Declara la aplicación Django de solicitudes y disponibilidad."""

from django.apps import AppConfig


class SolicitudesConfig(AppConfig):
    """Declara la aplicación de solicitudes, empresas y disponibilidad."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'solicitudes'
