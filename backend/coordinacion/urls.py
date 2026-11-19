
"""Declara rutas administrativas de coordinación, agenda y asociaciones."""

from django.urls import path

from .asociaciones import (
    ConfirmarAsociacionSolicitudProfesionalView,
)

from .prestaciones import (
    PrepararPrestacionServicioAdministracionView,
)

from .asignacion_segura import (
    AsignacionSolicitudSeguraAdministracionView,
)

from .agenda_segura import (
    GestionAgendaPrestacionSeguraAdministracionView,
)

from .views import (
    AsociacionesSolicitudProfesionalView,
    CoordinacionSolicitudAdministracionView,
    DetalleSolicitudEmpresarialAdministracionView,
    MisOportunidadesProfesionalView,
    MisServiciosCoordinadosProfesionalView,
    SolicitudesEmpresarialesAdministracionView,
)


from .crear_asociacion import CrearAsociacionSolicitudProfesionalView

from .crear_asociacion import ProponerAsociacionSolicitudProfesionalView

urlpatterns = [
    path(
        (
            "administracion/solicitudes/"
            "<int:id_solicitud>/asociaciones/proponer/"
        ),
        ProponerAsociacionSolicitudProfesionalView.as_view(),
        name="proponer_asociacion_solicitud_profesional",
    ),

    path(
        (
            "administracion/solicitudes/"
            "<int:id_solicitud>/asociaciones/"
            "<int:id_profesional>/crear/"
        ),
        CrearAsociacionSolicitudProfesionalView.as_view(),
        name="crear_asociacion_solicitud_profesional",
    ),

    path(
        "administracion/solicitudes/",
        SolicitudesEmpresarialesAdministracionView.as_view(),
        name="solicitudes_empresariales_administracion",
    ),

    path(
        "administracion/solicitudes/<int:id_solicitud>/",
        DetalleSolicitudEmpresarialAdministracionView.as_view(),
        name="detalle_solicitud_empresarial_administracion",
    ),

    path(
        "administracion/solicitudes/<int:id_solicitud>/asignacion/",
        AsignacionSolicitudSeguraAdministracionView.as_view(),
        name="asignacion_solicitud_administracion",
    ),

    path(
        "administracion/solicitudes/<int:id_solicitud>/asociaciones/",
        AsociacionesSolicitudProfesionalView.as_view(),
        name="asociaciones_solicitud_profesional",
    ),

    path(
        (
            "administracion/solicitudes/"
            "<int:id_solicitud>/asociaciones/"
            "<int:id_profesional>/confirmar/"
        ),
        ConfirmarAsociacionSolicitudProfesionalView.as_view(),
        name="confirmar_asociacion_solicitud_profesional",
    ),

    path(
        (
            "administracion/solicitudes/"
            "<int:id_solicitud>/profesionales/"
            "<int:id_profesional>/preparar-prestacion/"
        ),
        PrepararPrestacionServicioAdministracionView.as_view(),
        name="preparar_prestacion_servicio_administracion",
    ),

    path(
        "administracion/solicitudes/<int:id_solicitud>/coordinacion/",
        CoordinacionSolicitudAdministracionView.as_view(),
        name="coordinacion_solicitud_administracion",
    ),

    path(
        "administracion/prestaciones/<int:id_prestacion>/agenda/",
        GestionAgendaPrestacionSeguraAdministracionView.as_view(),
        name="gestion_agenda_prestacion_administracion",
    ),

    path(
        "mis-oportunidades/",
        MisOportunidadesProfesionalView.as_view(),
        name="mis_oportunidades_profesional",
    ),

    path(
        "mis-servicios-coordinados/",
        MisServiciosCoordinadosProfesionalView.as_view(),
        name="mis_servicios_coordinados_profesional",
    ),
]
