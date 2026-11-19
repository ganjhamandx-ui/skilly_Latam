"""Configura la aplicación de operaciones administrativas internas."""

from django.apps import AppConfig


class BackofficeConfig(AppConfig):
    """Declara la aplicación que agrupa configuración y auditoría administrativa."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backoffice'
