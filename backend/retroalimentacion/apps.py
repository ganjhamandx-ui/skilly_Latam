"""Declara la aplicación Django de evaluaciones y recomendaciones."""

from django.apps import AppConfig


class RetroalimentacionConfig(AppConfig):
    """Declara la aplicación de evaluaciones y recomendaciones profesionales."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'retroalimentacion'
