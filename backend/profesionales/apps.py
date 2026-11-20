"""Declara la aplicación Django de profesionales y validación documental."""

from django.apps import AppConfig


class ProfesionalesConfig(AppConfig):
    """Registra la aplicación profesionales con claves primarias automáticas de 64 bits."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profesionales'
