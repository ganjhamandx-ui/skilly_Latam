from django.urls import path

from .views import (
    AgendaEntrevistasAdministracionView,
    BandejaValidacionesAdministracionView,
    DetalleValidacionAdministracionView,
    DocumentosProfesionalesPropiosView,
    EstadoValidacionPropiaView,
    MiEntrevistaValidacionView,
    PerfilProfesionalPropioView,
)

from .reserva_entrevista import (
    ReservaEntrevistaProfesionalView,
    CancelarEntrevistaProfesionalView,
)

from .gestion_bloques import (
    CrearBloqueEntrevistaAdministracionView,
    ModificarBloqueEntrevistaAdministracionView,
)


urlpatterns = [
    path(
        "mi-perfil/",
        PerfilProfesionalPropioView.as_view(),
        name="perfil_profesional_propio",
    ),
    path(
        "mis-documentos/",
        DocumentosProfesionalesPropiosView.as_view(),
        name="documentos_profesionales_propios",
    ),
    path(
        "mi-validacion/",
        EstadoValidacionPropiaView.as_view(),
        name="estado_validacion_propia",
    ),
    path(
        "mi-entrevista/",
        MiEntrevistaValidacionView.as_view(),
        name="mi_entrevista_validacion",
    ),
    path(
        "mi-entrevista/reservar/",
        ReservaEntrevistaProfesionalView.as_view(),
        name="reserva_entrevista_profesional",
    ),
    path(
        "mi-entrevista/cancelar/",
        CancelarEntrevistaProfesionalView.as_view(),
        name="cancelar_entrevista_profesional",
    ),
    path(
        "administracion/validaciones/",
        BandejaValidacionesAdministracionView.as_view(),
        name="bandeja_validaciones_administracion",
    ),
    path(
        "administracion/validaciones/<int:id_validacion>/",
        DetalleValidacionAdministracionView.as_view(),
        name="detalle_validacion_administracion",
    ),
    path(
        "administracion/entrevistas/",
        AgendaEntrevistasAdministracionView.as_view(),
        name="agenda_entrevistas_administracion",
    ),
    path(
        "administracion/entrevistas/bloques/",
        CrearBloqueEntrevistaAdministracionView.as_view(),
        name="crear_bloque_entrevista_administracion",
    ),
    path(
        "administracion/entrevistas/bloques/<int:id_bloque_entrevista>/",
        ModificarBloqueEntrevistaAdministracionView.as_view(),
        name="modificar_bloque_entrevista_administracion",
    ),
]

from django.urls import path as perfil_creacion_path
from .views_crear_perfil import CrearMiPerfilProfesionalView

urlpatterns += [
    perfil_creacion_path(
        "mi-perfil/crear/",
        CrearMiPerfilProfesionalView.as_view(),
        name="crear-mi-perfil-profesional",
    ),
]

from django.urls import path as documentos_path
from .views_documentos_carga import (
    SubirDocumentoProfesionalView,
    DescargarDocumentoProfesionalView,
)

urlpatterns += [
    documentos_path(
        "mis-documentos/subir/",
        SubirDocumentoProfesionalView.as_view(),
        name="subir-documento-profesional",
    ),
    documentos_path(
        "mis-documentos/<int:id_documento>/descargar/",
        DescargarDocumentoProfesionalView.as_view(),
        name="descargar-documento-profesional",
    ),
]

from django.urls import path as validacion_path
from .views_solicitar_validacion import SolicitarMiValidacionView

urlpatterns += [
    validacion_path(
        "mi-validacion/solicitar/",
        SolicitarMiValidacionView.as_view(),
        name="solicitar-mi-validacion",
    ),
]

from django.urls import path as descarga_admin_path
from .views_descarga_admin import DescargarDocumentoValidacionAdminView

urlpatterns += [
    descarga_admin_path(
        "administracion/validaciones/<int:id_validacion>/documentos/"
        "<int:id_documento>/descargar/",
        DescargarDocumentoValidacionAdminView.as_view(),
        name="descargar-documento-validacion-admin",
    ),
]

from .views_revision_admin import ResolverValidacionDocumentalAdminView
from django.urls import path as revision_admin_path

urlpatterns += [
    revision_admin_path(
        "administracion/validaciones/"
        "<int:id_validacion>/resolver/",
        ResolverValidacionDocumentalAdminView.as_view(),
        name="resolver-validacion-documental-admin",
    ),
]

from .views_resultado_entrevista_admin import ResolverEntrevistaYValidacionAdminView

urlpatterns += [
    path(
        "administracion/validaciones/<int:id_validacion>/resultado-entrevista/",
        ResolverEntrevistaYValidacionAdminView.as_view(),
        name="resolver-entrevista-validacion-admin",
    ),
]

from .contacto_entrevista_admin import ConfirmarContactoEntrevistaAdminView
urlpatterns += [
    path(
        "administracion/entrevistas/<int:id_entrevista>/contacto/",
        ConfirmarContactoEntrevistaAdminView.as_view(),
        name="confirmar_contacto_entrevista_admin",
    ),
]


from django.urls import include as cuentas_include
urlpatterns += [path("", cuentas_include("profesionales.cuentas_pago_urls"))]
