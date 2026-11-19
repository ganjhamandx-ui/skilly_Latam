"""Configura la aplicación que coordina solicitudes y prestaciones."""

from django.apps import AppConfig


class CoordinacionConfig(AppConfig):
    """Declara la aplicación que gestiona coordinación, agenda y prestaciones."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'coordinacion'
