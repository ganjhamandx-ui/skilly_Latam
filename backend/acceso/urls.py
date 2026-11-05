from django.urls import path
from .sesion_actual import SesionActualView

from .views import (
    CerrarSesionView,
    CsrfTokenView,
    InicioSesionView,
    RegistroProfesionalView,
    RestablecerContrasenaView,
    SolicitarRecuperacionView,
)


urlpatterns = [
    path(
        "sesion-actual/",
        SesionActualView.as_view(),
        name="sesion_actual",
    ),
    path(
        "csrf/",
        CsrfTokenView.as_view(),
        name="csrf_token",
    ),
    path(
        "registro-profesional/",
        RegistroProfesionalView.as_view(),
        name="registro_profesional",
    ),
    path(
        "iniciar-sesion/",
        InicioSesionView.as_view(),
        name="iniciar_sesion",
    ),
    path(
        "solicitar-recuperacion/",
        SolicitarRecuperacionView.as_view(),
        name="solicitar_recuperacion",
    ),
    path(
        "restablecer-contrasena/",
        RestablecerContrasenaView.as_view(),
        name="restablecer_contrasena",
    ),
    path(
        "cerrar-sesion/",
        CerrarSesionView.as_view(),
        name="cerrar_sesion",
    ),
]