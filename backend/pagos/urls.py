"""Define las rutas HTTP del módulo de pagos y conciliación."""

from .comprobantes_api import ComprobanteTransferenciaAdministracionView

from django.urls import path
from .webpay_empresa_e3 import IniciarWebpayPlusEmpresaView, RetornoWebpayPlusEmpresaView
from .resolucion_reversas_e3 import ResolverReversaE3AdministracionView
from .transferencia_disponibilidad import DisponibilidadTransferenciaEmpresaView

from .operaciones_seguras import (
    DetallePagoSeguroAdministracionView,
    LiberarPagoSeguroAdministracionView,
    ReversasPagoSegurasAdministracionView,
)

from .views import (
    IniciarPagoTransferenciaEmpresaView,
    MisPagosProfesionalView,
    PagoEstadoEmpresaView,
    PagoPrestacionProfesionalView,
    PagosAdministracionView,
)


urlpatterns = [
    path("empresa/<str:referencia>/webpay/iniciar/", IniciarWebpayPlusEmpresaView.as_view(), name="webpay_iniciar_empresa_e3"),
    path("webpay/retorno/", RetornoWebpayPlusEmpresaView.as_view(), name="webpay_retorno_empresa_e3"),
    path(
        "administracion/<int:id_pago>/reversas/<int:id_reversa>/resolver/",
        ResolverReversaE3AdministracionView.as_view(),
        name="resolver_reversa_e3_administracion",
    ),
    path("administracion/<int:id_pago>/comprobante/", ComprobanteTransferenciaAdministracionView.as_view(), name="comprobante_transferencia_administracion"),
    path("empresa/<str:referencia>/transferencia/disponibilidad/", DisponibilidadTransferenciaEmpresaView.as_view(), name="disponibilidad_transferencia_empresa"),
    path(
        (
            "empresa/"
            "<str:referencia>/"
            "transferencia/"
        ),
        IniciarPagoTransferenciaEmpresaView.as_view(),
        name="iniciar_pago_transferencia_empresa",
    ),

    path(
        (
            "empresa/"
            "<str:referencia>/"
            "estado/"
        ),
        PagoEstadoEmpresaView.as_view(),
        name="estado_pago_empresa",
    ),

    path(
        "profesional/",
        MisPagosProfesionalView.as_view(),
        name="mis_pagos_profesional",
    ),

    path(
        "profesional/prestaciones/<int:id_prestacion>/",
        PagoPrestacionProfesionalView.as_view(),
        name="pago_prestacion_profesional",
    ),

    path(
        "administracion/",
        PagosAdministracionView.as_view(),
        name="pagos_administracion",
    ),

    path(
        "administracion/<int:id_pago>/",
        DetallePagoSeguroAdministracionView.as_view(),
        name="detalle_pago_administracion",
    ),

    path(
        "administracion/<int:id_pago>/liberar/",
        LiberarPagoSeguroAdministracionView.as_view(),
        name="liberar_pago_administracion",
    ),

    path(
        "administracion/<int:id_pago>/reversas/",
        ReversasPagoSegurasAdministracionView.as_view(),
        name="reversas_pago_administracion",
    ),
]
