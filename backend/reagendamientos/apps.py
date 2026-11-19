"""Declara la aplicación Django del reagendamiento bilateral."""

from django.apps import AppConfig


class ReagendamientosConfig(AppConfig):
    """Declara la aplicación del flujo bilateral de reagendamiento."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "reagendamientos"
