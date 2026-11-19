"""Expone las rutas del flujo bilateral según el actor autenticado."""

from django.urls import path
from .views import (
    AdministracionReagendamientoView,
    EvidenciaReagendamientoAdministracionView,
    OrganizacionReagendamientoView,
    ProfesionalReagendamientoView,
)

urlpatterns = [
    path("organizacion/<str:referencia>/", OrganizacionReagendamientoView.as_view(), name="reagenda_organizacion"),
    path("administracion/", AdministracionReagendamientoView.as_view(), name="reagenda_administracion"),
    path("administracion/<int:pk>/evidencia/", EvidenciaReagendamientoAdministracionView.as_view(), name="reagenda_evidencia_administracion"),
    path("profesional/", ProfesionalReagendamientoView.as_view(), name="reagenda_profesional"),
]
