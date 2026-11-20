"""Declara la aplicación Django responsable del ciclo de pagos."""

from django.apps import AppConfig


class PagosConfig(AppConfig):
    """Configura la aplicación de pagos y el tipo predeterminado de clave primaria."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pagos'
