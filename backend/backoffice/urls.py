from .configuracion_cargo_cancelacion_e3 import ConfiguracionCargoCancelacionView
from django.urls import include, path

from .views import (
    ConfiguracionComisionAdministracionView,
    DetalleEventoTrazabilidadView,
    PanelIndicadoresView,
    TrazabilidadOperacionalView,
)


urlpatterns = [
    path(
        "indicadores/",
        PanelIndicadoresView.as_view(),
        name="panel_indicadores",
    ),
    path(
        "configuracion/comision/",
        ConfiguracionComisionAdministracionView.as_view(),
        name="configuracion_comision_administracion",
    ),
    path(
        "configuracion/cancelaciones/",
        ConfiguracionCargoCancelacionView.as_view(),
        name="configuracion_cargo_cancelacion_e3",
    ),
    path(
        "trazabilidad/",
        TrazabilidadOperacionalView.as_view(),
        name="trazabilidad_operacional",
    ),
    path(
        "trazabilidad/<int:id_evento>/",
        DetalleEventoTrazabilidadView.as_view(),
        name="detalle_evento_trazabilidad",
    ),
]
# Rutas bancarias solo para administracion, sin rutas publicas de cuentas.
urlpatterns += [path("", include("backoffice.cuentas_bancarias_urls"))]
