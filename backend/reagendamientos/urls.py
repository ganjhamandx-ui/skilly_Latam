from django.urls import path
from .views import OrganizacionReagendamientoView, AdministracionReagendamientoView, ProfesionalReagendamientoView

urlpatterns = [
    path("organizacion/<str:referencia>/", OrganizacionReagendamientoView.as_view(), name="reagenda_organizacion"),
    path("administracion/", AdministracionReagendamientoView.as_view(), name="reagenda_administracion"),
    path("profesional/", ProfesionalReagendamientoView.as_view(), name="reagenda_profesional"),
]
