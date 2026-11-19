"""Define las rutas de retroalimentación para cada actor autorizado."""

from django.urls import path

from .recomendaciones_profesional import (
    DetalleRecomendacionProfesionalView,
    MisRecomendacionesProfesionalView,
)

from .views import (
    ComunicarRecomendacionAdministracionView,
    GestionRetroalimentacionAdministracionView,
    RetroalimentacionPrivadaEmpresaView,
    RetroalimentacionesAdministracionView,
)


urlpatterns = [
    path(
        "empresa/<str:referencia>/",
        RetroalimentacionPrivadaEmpresaView.as_view(),
        name="retroalimentacion_privada_empresa",
    ),
    path(
        "administracion/",
        RetroalimentacionesAdministracionView.as_view(),
        name="retroalimentaciones_administracion",
    ),
    path(
        "administracion/<int:id_feedback>/",
        GestionRetroalimentacionAdministracionView.as_view(),
        name="gestion_retroalimentacion_administracion",
    ),
    path(
        "administracion/recomendaciones/<int:id_recomendacion>/comunicar/",
        ComunicarRecomendacionAdministracionView.as_view(),
        name="comunicar_recomendacion_administracion",
    ),
    path(
        "profesional/recomendaciones/",
        MisRecomendacionesProfesionalView.as_view(),
        name="mis_recomendaciones_profesional",
    ),
    path(
        "profesional/recomendaciones/<int:id_recomendacion>/",
        DetalleRecomendacionProfesionalView.as_view(),
        name="detalle_recomendacion_profesional",
    ),
]
