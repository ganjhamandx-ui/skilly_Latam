"""Configura la aplicación del marketplace de servicios profesionales."""

from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    """Registra marketplace y utiliza claves primarias automáticas de 64 bits."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'
