"""Define las rutas del seguimiento privado y administrativo."""

from .expedientes_cancelacion_e3 import EstadoCancelacionOrganizacionView
from .aceptacion_politica_e3 import PoliticaCancelacionEmpresaView
from .expedientes_cancelacion_e3 import (CancelacionOrganizacionView, CancelacionProfesionalView, ExpedientesCancelacionAdminView, ExpedienteCancelacionAdminView, EvidenciaCancelacionAdminView)

from django.urls import path

from .reportes_profesional import AvisoIncidenciaProfesionalView

from .listado_reclamos import (
    ListadoReclamosAdministracionView,
)

from .views import (
    EntregasPrestacionProfesionalView,
    GestionReclamoAdministracionView,
    RegistrarReclamoEmpresaView,
    RevisionEntregaEmpresaView,
    SeguimientoPrestacionAdministracionView,
    SeguimientoPrestacionEmpresaView,
    SeguimientoPrestacionProfesionalView,
)


urlpatterns = [
    path(
        (
            "empresa/"
            "<str:referencia>/"
            "prestacion/"
        ),
        SeguimientoPrestacionEmpresaView.as_view(),
        name="seguimiento_prestacion_empresa",
    ),
    path(
        (
            "empresa/"
            "<str:referencia>/"
            "entregas/"
            "<int:id_entrega>/"
        ),
        RevisionEntregaEmpresaView.as_view(),
        name="revision_entrega_empresa",
    ),
    path(
        (
            "empresa/"
            "<str:referencia>/"
            "reclamos/"
        ),
        RegistrarReclamoEmpresaView.as_view(),
        name="registrar_reclamo_empresa",
    ),
    path(
        "profesional/prestaciones/<int:id_prestacion>/",
        SeguimientoPrestacionProfesionalView.as_view(),
        name="seguimiento_prestacion_profesional",
    ),
    path(
        "profesional/prestaciones/<int:id_prestacion>/incidencias/",
        AvisoIncidenciaProfesionalView.as_view(),
        name="aviso_incidencia_profesional",
    ),
    path(
        "profesional/prestaciones/<int:id_prestacion>/entregas/",
        EntregasPrestacionProfesionalView.as_view(),
        name="entregas_prestacion_profesional",
    ),
    path(
        "administracion/prestaciones/<int:id_prestacion>/",
        SeguimientoPrestacionAdministracionView.as_view(),
        name="seguimiento_prestacion_administracion",
    ),

    # NUEVA: bandeja administrativa, solo GET.
    path(
        "administracion/reclamos/",
        ListadoReclamosAdministracionView.as_view(),
        name="listado_reclamos_administracion",
    ),

    # ORIGINAL: detalle y resolución. Sin modificaciones.
    path(
        "administracion/reclamos/<int:id_reclamo>/",
        GestionReclamoAdministracionView.as_view(),
        name="gestion_reclamo_administracion",
    ),
]

# Expedientes E3: adjuntos privados y evaluación, sin movimientos bancarios.
urlpatterns += [
    path('empresa/<str:referencia>/cancelaciones/', CancelacionOrganizacionView.as_view(), name='cancelacion_empresa_e3'),
    path('profesional/prestaciones/<int:id_prestacion>/cancelaciones/', CancelacionProfesionalView.as_view(), name='cancelacion_profesional_e3'),
    path('administracion/cancelaciones/', ExpedientesCancelacionAdminView.as_view(), name='expedientes_cancelacion_e3'),
    path('administracion/cancelaciones/<int:id_expediente>/', ExpedienteCancelacionAdminView.as_view(), name='expediente_cancelacion_e3'),
    path('administracion/cancelaciones/<int:id_expediente>/evidencia/', EvidenciaCancelacionAdminView.as_view(), name='evidencia_cancelacion_e3'),
]

urlpatterns += [path('empresa/<str:referencia>/politica-cancelacion/', PoliticaCancelacionEmpresaView.as_view(), name='politica_cancelacion_empresa_e3')]
urlpatterns += [path('empresa/<str:referencia>/cancelaciones/estado/', EstadoCancelacionOrganizacionView.as_view(), name='estado_cancelacion_empresa_e3')]


# Primero se autoriza la liquidación; esta ruta no ejecuta el reembolso.
from .liquidacion_cancelacion_e3 import LiquidarCancelacionE3View
urlpatterns += [path('administracion/cancelaciones/<int:id_expediente>/liquidacion/', LiquidarCancelacionE3View.as_view(), name='liquidacion_cancelacion_e3')]

# Ruta documental conservada por compatibilidad; el Video B la integra en el cierre único.
from .conciliacion_reversas_e3 import ConciliarReversaParcialE3View
urlpatterns += [path('administracion/cancelaciones/<int:id_expediente>/conciliacion/', ConciliarReversaParcialE3View.as_view(), name='conciliacion_parcial_e3')]

# Respaldo documental por servicio: rutas independientes del flujo original.
from .entregables_multiservicio_e3 import (EntregablesProfesionalE3View,
    RegistrarEntregaConArchivosE3View, EntregablesEmpresaE3View, DescargaEntregaEmpresaE3View,
    DescargaEntregaProfesionalE3View, DescargaEntregaAdminE3View)
urlpatterns += [
    path('administracion/entregables/archivos/<int:id_archivo>/',DescargaEntregaAdminE3View.as_view()),
    path('profesional/prestaciones/<int:id_prestacion>/entregables/',EntregablesProfesionalE3View.as_view()),
    path('profesional/prestaciones/<int:id_prestacion>/entregas-con-archivos/',RegistrarEntregaConArchivosE3View.as_view()),
    path('profesional/entregables/archivos/<int:id_archivo>/',DescargaEntregaProfesionalE3View.as_view()),
    path('empresa/<str:referencia>/entregables/',EntregablesEmpresaE3View.as_view()),
    path('empresa/<str:referencia>/entregables/archivos/<int:id_archivo>/',DescargaEntregaEmpresaE3View.as_view()),
]

# Cierre único del Video B: el POST concilia y registra la distribución simulada en una transacción.
from .cierre_simulado_cancelacion_e3 import CierreSimuladoCancelacionE3View
urlpatterns += [path('administracion/cancelaciones/<int:id_expediente>/cierre-simulado/',
    CierreSimuladoCancelacionE3View.as_view(), name='cierre_simulado_cancelacion_e3')]
