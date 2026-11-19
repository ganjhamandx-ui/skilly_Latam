
"""Declara las rutas públicas y privadas del marketplace."""

from django.urls import path
from .views_decision_comercial import RechazarVersionComercialProfesionalView

from .views import (
    DetalleRevisionServicioAdministracionView,
    DetalleServicioMarketplaceView,
    DetalleServicioProfesionalPropioView,
    EnviarServicioRevisionProfesionalView,
    MarketplaceServiciosPublicosView,
    MisServiciosProfesionalesView,
    PublicarServicioProfesionalView,
    RevisarServicioAdministracionView,
    RevisionesServicioAdministracionView,
    VersionRevisadaProfesionalView,
)

from .views_catalogos import (
    CatalogosPropuestasView,
)

from .views_pendientes_admin import (
    PropuestasPendientesAdministracionView,
)


urlpatterns = [

    # Marketplace publico.
    path(
        "servicios/",
        MarketplaceServiciosPublicosView.as_view(),
        name="marketplace_servicios_publicos",
    ),

    path(
        "servicios/<int:id_servicio>/",
        DetalleServicioMarketplaceView.as_view(),
        name="detalle_servicio_marketplace",
    ),

    # Servicios del profesional.
    path(
        "mis-servicios/",
        MisServiciosProfesionalesView.as_view(),
        name="mis_servicios_profesionales",
    ),

    path(
        "mis-servicios/<int:id_servicio>/",
        DetalleServicioProfesionalPropioView.as_view(),
        name="detalle_servicio_profesional_propio",
    ),

    path(
        "mis-servicios/<int:id_servicio>/enviar-revision/",
        EnviarServicioRevisionProfesionalView.as_view(),
        name="enviar_servicio_revision_profesional",
    ),

    path(
        "mis-servicios/<int:id_servicio>/version-revisada/",
        VersionRevisadaProfesionalView.as_view(),
        name="version_revisada_profesional",
    ),

    path(
        "mis-servicios/<int:id_servicio>/rechazar-version-comercial/",
        RechazarVersionComercialProfesionalView.as_view(),
        name="rechazar_version_comercial_profesional",
    ),

    path(
        "mis-servicios/<int:id_servicio>/publicar/",
        PublicarServicioProfesionalView.as_view(),
        name="publicar_servicio_profesional",
    ),

    # Catalogos profesionales.
    path(
        "catalogos/",
        CatalogosPropuestasView.as_view(),
        name="catalogos-propuestas",
    ),

    # Nueva bandeja administrativa de propuestas.
    path(
        "administracion/servicios/pendientes/",
        PropuestasPendientesAdministracionView.as_view(),
        name="propuestas_pendientes_administracion",
    ),

    # Historial administrativo de revisiones.
    path(
        "administracion/revisiones/",
        RevisionesServicioAdministracionView.as_view(),
        name="revisiones_servicio_administracion",
    ),

    # Decision administrativa sobre una propuesta.
    path(
        "administracion/servicios/<int:id_servicio>/revisar/",
        RevisarServicioAdministracionView.as_view(),
        name="revisar_servicio_administracion",
    ),

    # Detalle de una revision existente.
    path(
        "administracion/revisiones/<int:id_revision_servicio>/",
        DetalleRevisionServicioAdministracionView.as_view(),
        name="detalle_revision_servicio_administracion",
    ),
]
