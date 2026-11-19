"""Declara la aplicación Django de seguimiento de prestaciones."""

from django.apps import AppConfig


class SeguimientoConfig(AppConfig):
    """Declara la aplicación de avances, entregas, reclamos y cancelaciones."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seguimiento'
