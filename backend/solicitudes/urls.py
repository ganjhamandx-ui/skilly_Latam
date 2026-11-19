"""Define las rutas de solicitudes, agenda y seguimiento firmado."""

from django.urls import path

from .seguimiento import (
    SeguimientoSolicitudServicioPublicaView,
)
from .views import (
    DetalleDisponibilidadProfesionalView,
    EnviarSolicitudServicioPublicaView,
    MiDisponibilidadProfesionalView,
)


urlpatterns = [
    path(
        "mi-disponibilidad/",
        MiDisponibilidadProfesionalView.as_view(),
        name="mi_disponibilidad_profesional",
    ),
    path(
        "mi-disponibilidad/<int:id_disponibilidad>/",
        DetalleDisponibilidadProfesionalView.as_view(),
        name="detalle_disponibilidad_profesional",
    ),
    path(
        "enviar/",
        EnviarSolicitudServicioPublicaView.as_view(),
        name="enviar_solicitud_servicio_publica",
    ),
    path(
        "seguimiento/<str:referencia>/",
        SeguimientoSolicitudServicioPublicaView.as_view(),
        name="seguimiento_solicitud_servicio_publica",
    ),
]
