"""Implementa operaciones administrativas de coordinación y agenda segura."""

from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.models import Usuario
from acceso.permissions import (
    EsAdministracionSkilly,
    EsProfesional,
)
from backoffice.services import registrar_evento_trazabilidad
from pagos.models import Pago
from profesionales.models import Profesional
from solicitudes.models import (
    Disponibilidad,
    ReservaDisponibilidad,
    SolicitudServicio,
)

from .control_responsable import requiere_responsable_solicitud
from .vigencia_asignacion import asignaciones_vigentes

from .models import (
    AsignacionSolicitud,
    CoordinacionSolicitud,
    PrestacionServicio,
    ReunionSolicitud,
    SolicitudProfesional,
)
from .serializers import (
    AgendarPrimeraReunionSerializer,
    AsignacionSolicitudAdministracionSerializer,
    AsociacionSolicitudProfesionalSerializer,
    ComunicarCondicionesPrestacionSerializer,
    CoordinacionSolicitudAdministracionSerializer,
    OportunidadProfesionalSerializer,
    PrestacionServicioAdministracionSerializer,
    ReservaDisponibilidadAdministracionSerializer,
    ReunionSolicitudAdministracionSerializer,
    ServicioCoordinadoProfesionalSerializer,
    SolicitudEmpresarialAdministracionSerializer,
)


class SolicitudesEmpresarialesAdministracionView(APIView):
    """Lista solicitudes y contactos empresariales bajo permiso administrativo."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        """Consulta la bandeja completa de solicitudes, sin paginación.

        Args:
            request (Request): Sesión administrativa; no se aplican filtros de consulta.

        Returns:
            Response: HTTP 200 con ``solicitudes`` por fecha e id descendentes,
            incluidas organización y contacto; la colección puede estar vacía.
        """
        solicitudes = (
            SolicitudServicio.objects
            .select_related(
                "id_empresa",
                "id_contacto",
                "id_servicio",
            )
            .order_by(
                "-fecha_solicitud",
                "-id_solicitud",
            )
        )

        serializer = (
            SolicitudEmpresarialAdministracionSerializer(
                solicitudes,
                many=True,
            )
        )

        return Response(
            {
                "solicitudes": serializer.data,
            }
        )


class DetalleSolicitudEmpresarialAdministracionView(
    APIView
):
    """Expone a administración el detalle empresarial de una solicitud."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request, id_solicitud):
        """Recupera una solicitud con organización, contacto y servicio.

        Args:
            request (Request): Petición administrativa autenticada.
            id_solicitud (int): Solicitud que se consultará.

        Returns:
            Response: HTTP 200 con el detalle serializado, sin envoltorio adicional.

        Raises:
            Http404: Si no existe la solicitud.
        """
        solicitud = get_object_or_404(
            SolicitudServicio.objects.select_related(
                "id_empresa",
                "id_contacto",
                "id_servicio",
            ),
            id_solicitud=id_solicitud,
        )

        serializer = (
            SolicitudEmpresarialAdministracionSerializer(
                solicitud
            )
        )

        return Response(serializer.data)


class AsignacionSolicitudAdministracionView(APIView):
    """Consulta responsables y aporta la implementación base de asignación.

    asignacion_segura conserva el GET y sustituye el POST con controles de
    concurrencia. No atribuir esos bloqueos a la escritura de esta clase base.
    """
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request, id_solicitud):
        """Consulta el historial y la asignación vigente más reciente.

        Args:
            request (Request): Sesión administrativa autenticada.
            id_solicitud (int): Solicitud que debe existir.

        Returns:
            Response: HTTP 200 con historial descendente y asignación o ``None``.
            Si hay varias vigentes, presenta la última sin corregir la inconsistencia.

        Raises:
            Http404: Si no existe la solicitud.
        """
        get_object_or_404(
            SolicitudServicio,
            id_solicitud=id_solicitud,
        )

        asignaciones = (
            AsignacionSolicitud.objects
            .select_related(
                "id_usuario_skilly"
            )
            .filter(
                id_solicitud_id=id_solicitud
            )
            .order_by(
                "-fecha_asignacion",
                "-id_asignacion",
            )
        )

        asignacion_actual = (
            asignaciones_vigentes(id_solicitud)
            .select_related("id_usuario_skilly")
            .order_by("-fecha_asignacion", "-id_asignacion")
            .first()
        )

        asignacion_data = None

        if asignacion_actual is not None:
            asignacion_serializer = (
                AsignacionSolicitudAdministracionSerializer(
                    asignacion_actual
                )
            )

            asignacion_data = asignacion_serializer.data

        historial_serializer = (
            AsignacionSolicitudAdministracionSerializer(
                asignaciones,
                many=True,
            )
        )

        return Response(
            {
                "id_solicitud": id_solicitud,
                "asignacion": asignacion_data,
                "historial_asignaciones": (
                    historial_serializer.data
                ),
            }
        )

    def post(self, request, id_solicitud):
        """Crea una asignación MANUAL mediante el contrato base de coordinación.

        Args:
            request (Request): Sesión administrativa, modo AUTOASIGNAR o ASIGNAR
                y, para este último, ``id_usuario_skilly`` de un administrador activo.
            id_solicitud (int): Solicitud que recibirá la asignación.

        Returns:
            Response: HTTP 201 con asignación, 400 por modo o destino inválidos,
            o 409 si ya hay una asignación ACTIVA. La comprobación previa no toma
            bloqueos; el endpoint seguro utiliza la subclase correspondiente.

        Raises:
            Http404: Si no existe la solicitud.
        """
        solicitud = get_object_or_404(
            SolicitudServicio,
            id_solicitud=id_solicitud,
        )

        asignacion_activa = (
            AsignacionSolicitud.objects
            .filter(
                id_solicitud=solicitud,
                estado="ACTIVA",
            )
            .first()
        )

        if asignacion_activa is not None:
            return Response(
                {
                    "mensaje": (
                        "La solicitud ya tiene un responsable "
                        "interno asignado. La regla de "
                        "reasignación permanece pendiente."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        modo = str(
            request.data.get("modo", "")
        ).strip().upper()

        if modo == "AUTOASIGNAR":
            usuario_destino = request.user
            tipo_asignacion = "MANUAL"

        elif modo == "ASIGNAR":
            id_usuario_skilly = request.data.get(
                "id_usuario_skilly"
            )

            if not id_usuario_skilly:
                return Response(
                    {
                        "mensaje": (
                            "Debe indicar id_usuario_skilly "
                            "para asignar la solicitud."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            usuario_destino = Usuario.objects.filter(
                id_usuario=id_usuario_skilly,
                rol="ADMIN_SKILLY",
                estado="ACTIVO",
            ).first()

            if usuario_destino is None:
                return Response(
                    {
                        "mensaje": (
                            "El usuario indicado no corresponde "
                            "a un usuario interno Skilly activo."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            tipo_asignacion = "MANUAL"

        else:
            return Response(
                {
                    "mensaje": (
                        "El modo debe ser AUTOASIGNAR o ASIGNAR."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            asignacion = AsignacionSolicitud.objects.create(
                id_solicitud=solicitud,
                id_usuario_skilly=usuario_destino,
                tipo_asignacion=tipo_asignacion,
                fecha_asignacion=timezone.now(),
                fecha_fin=None,
                estado="ACTIVA",
            )

            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="asignacion_solicitud",
                entidad_id=asignacion.id_asignacion,
                accion=modo,
                detalle_resumido=(
                    f"Solicitud {solicitud.id_solicitud} "
                    f"asignada al usuario interno "
                    f"{usuario_destino.id_usuario}."
                )[:255],
            )

        serializer = (
            AsignacionSolicitudAdministracionSerializer(
                asignacion
            )
        )

        return Response(
            {
                "mensaje": (
                    "Solicitud asignada correctamente."
                ),
                "asignacion": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class AsociacionesSolicitudProfesionalView(APIView):
    """Consulta asociaciones profesionales sin modificar sus estados."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request, id_solicitud):
        """Lista asociaciones de una solicitud por fecha descendente.

        Args:
            request (Request): Sesión administrativa autenticada.
            id_solicitud (int): Solicitud que agrupa las asociaciones.

        Returns:
            Response: HTTP 200 con id de solicitud y lista de asociaciones.

        Raises:
            Http404: Si no existe la solicitud.
        """
        get_object_or_404(
            SolicitudServicio,
            id_solicitud=id_solicitud,
        )

        asociaciones = (
            SolicitudProfesional.objects
            .select_related(
                "id_solicitud__id_servicio",
                "id_profesional",
            )
            .filter(
                id_solicitud_id=id_solicitud
            )
            .order_by(
                "-fecha_asociacion",
            )
        )

        serializer = (
            AsociacionSolicitudProfesionalSerializer(
                asociaciones,
                many=True,
            )
        )

        return Response(
            {
                "id_solicitud": id_solicitud,
                "asociaciones": serializer.data,
            }
        )


class CoordinacionSolicitudAdministracionView(APIView):
    """Reúne el expediente de coordinación y registra condiciones previas al contrato."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request, id_solicitud):
        """Reúne solicitud, asociaciones, historial, reservas, reuniones y prestación.

        Args:
            request (Request): Sesión administrativa; la lectura no exige asignación.
            id_solicitud (int): Solicitud que agrupa los registros.

        Returns:
            Response: HTTP 200 con expediente e historiales cronológicos; la
            prestación es ``None`` si aún no se ha preparado.

        Raises:
            Http404: Si no existe la solicitud.
        """
        solicitud = get_object_or_404(
            SolicitudServicio.objects.select_related(
                "id_empresa",
                "id_contacto",
                "id_servicio",
            ),
            id_solicitud=id_solicitud,
        )

        asociaciones = (
            SolicitudProfesional.objects
            .select_related(
                "id_solicitud__id_servicio",
                "id_profesional",
            )
            .filter(
                id_solicitud_id=id_solicitud
            )
            .order_by(
                "-fecha_asociacion",
            )
        )

        coordinaciones = (
            CoordinacionSolicitud.objects
            .select_related(
                "id_usuario_skilly"
            )
            .filter(
                id_solicitud_id=id_solicitud
            )
            .order_by(
                "fecha_registro",
                "id_coordinacion",
            )
        )

        reservas = (
            ReservaDisponibilidad.objects
            .select_related(
                "id_disponibilidad"
            )
            .filter(
                id_solicitud_id=id_solicitud
            )
            .order_by(
                "fecha_reserva",
                "id_reserva",
            )
        )

        reuniones = (
            ReunionSolicitud.objects
            .select_related(
                "id_profesional",
                "id_usuario_skilly",
            )
            .filter(
                id_solicitud_id=id_solicitud
            )
            .order_by(
                "fecha_hora",
                "id_reunion",
            )
        )

        prestacion = (
            PrestacionServicio.objects
            .select_related(
                "id_profesional"
            )
            .filter(
                id_solicitud_id=id_solicitud
            )
            .first()
        )

        solicitud_serializer = (
            SolicitudEmpresarialAdministracionSerializer(
                solicitud
            )
        )

        asociaciones_serializer = (
            AsociacionSolicitudProfesionalSerializer(
                asociaciones,
                many=True,
            )
        )

        coordinaciones_serializer = (
            CoordinacionSolicitudAdministracionSerializer(
                coordinaciones,
                many=True,
            )
        )

        reservas_serializer = (
            ReservaDisponibilidadAdministracionSerializer(
                reservas,
                many=True,
            )
        )

        reuniones_serializer = (
            ReunionSolicitudAdministracionSerializer(
                reuniones,
                many=True,
            )
        )

        prestacion_data = None

        if prestacion is not None:
            prestacion_serializer = (
                PrestacionServicioAdministracionSerializer(
                    prestacion
                )
            )

            prestacion_data = prestacion_serializer.data

        return Response(
            {
                "solicitud": solicitud_serializer.data,
                "asociaciones": asociaciones_serializer.data,
                "historial_coordinacion": (
                    coordinaciones_serializer.data
                ),
                "reservas": reservas_serializer.data,
                "reuniones": reuniones_serializer.data,
                "prestacion": prestacion_data,
            }
        )

    @requiere_responsable_solicitud
    def post(self, request, id_solicitud):
        """Guarda condiciones y trazabilidad antes de formalizar la contratación.

        Args:
            request (Request): Sesión administrativa responsable, acción
                COMUNICAR_CONDICIONES y ``condiciones_comunicadas`` no vacías.
            id_solicitud (int): Solicitud con prestación preparada.

        Returns:
            Response: HTTP 200 con prestación actualizada, 400 por acción o texto
            inválidos y 409 si no hay prestación PENDIENTE_CONTRATACION.
            Persiste condiciones y coordinación; no envía correo.

        Raises:
            Http404: Si no existe la solicitud.
        """
        accion = str(
            request.data.get("accion", "")
        ).strip().upper()

        if accion != "COMUNICAR_CONDICIONES":
            return Response(
                {
                    "mensaje": (
                        "La acción debe ser "
                        "COMUNICAR_CONDICIONES."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        get_object_or_404(
            SolicitudServicio,
            id_solicitud=id_solicitud,
        )

        entrada_serializer = (
            ComunicarCondicionesPrestacionSerializer(
                data={
                    "condiciones_comunicadas": (
                        request.data.get(
                            "condiciones_comunicadas"
                        )
                    )
                }
            )
        )

        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        condiciones = (
            entrada_serializer.validated_data[
                "condiciones_comunicadas"
            ]
        )

        ahora = timezone.now()

        with transaction.atomic():
            prestacion = (
                PrestacionServicio.objects
                .select_for_update()
                .select_related(
                    "id_solicitud"
                )
                .filter(
                    id_solicitud_id=id_solicitud
                )
                .first()
            )

            if prestacion is None:
                return Response(
                    {
                        "mensaje": (
                            "La solicitud todavía no posee una "
                            "prestación preparada."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if (
                prestacion.estado
                != "PENDIENTE_CONTRATACION"
            ):
                return Response(
                    {
                        "mensaje": (
                            "Las condiciones solo pueden "
                            "comunicarse mientras la prestación "
                            "se encuentre pendiente de "
                            "contratación."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            prestacion.condiciones_comunicadas = condiciones

            prestacion.save(
                update_fields=[
                    "condiciones_comunicadas",
                ]
            )

            CoordinacionSolicitud.objects.create(
                id_solicitud=prestacion.id_solicitud,
                id_usuario_skilly=request.user,
                tipo="COMUNICAR_CONDICIONES",
                detalle=condiciones,
                estado_resultante=prestacion.estado,
                fecha_registro=ahora,
            )

            prestacion.id_solicitud.fecha_actualizacion = (
                ahora
            )

            prestacion.id_solicitud.save(
                update_fields=[
                    "fecha_actualizacion",
                ]
            )

            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="prestacion_servicio",
                entidad_id=prestacion.id_prestacion,
                accion="COMUNICAR_CONDICIONES",
                detalle_resumido=(
                    f"Condiciones comunicadas para la "
                    f"prestación {prestacion.id_prestacion} "
                    f"de la solicitud {id_solicitud}."
                )[:255],
            )

        prestacion_serializer = (
            PrestacionServicioAdministracionSerializer(
                prestacion
            )
        )

        return Response(
            {
                "mensaje": (
                    "Condiciones comunicadas correctamente."
                ),
                "prestacion": prestacion_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class GestionAgendaPrestacionAdministracionView(APIView):
    """Implementa la primera reunión y las operaciones base de agenda.

    agenda_segura amplía esta clase con responsable, bloqueos y sincronización
    bilateral. La implementación base conserva los contratos usados por super().
    """
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request, id_prestacion):
        """Consulta prestación, reservas, coordinación y bloques del profesional.

        Args:
            request (Request): Sesión administrativa autenticada.
            id_prestacion (int): Prestación cuya agenda se presenta.

        Returns:
            Response: HTTP 200 con agenda y marca de reserva activa por bloque.
            No filtra fechas pasadas ni garantiza disponibilidad para cambios.

        Raises:
            Http404: Si no existe la prestación.
        """
        prestacion = get_object_or_404(
            PrestacionServicio.objects.select_related(
                "id_solicitud__id_empresa",
                "id_solicitud__id_servicio",
                "id_profesional",
            ),
            id_prestacion=id_prestacion,
        )

        reservas = (
            ReservaDisponibilidad.objects
            .select_related(
                "id_disponibilidad"
            )
            .filter(
                id_solicitud=prestacion.id_solicitud
            )
            .order_by(
                "fecha_reserva",
                "id_reserva",
            )
        )

        coordinaciones = (
            CoordinacionSolicitud.objects
            .select_related(
                "id_usuario_skilly"
            )
            .filter(
                id_solicitud=prestacion.id_solicitud
            )
            .order_by(
                "fecha_registro",
                "id_coordinacion",
            )
        )

        bloques = (
            Disponibilidad.objects
            .filter(
                id_profesional=prestacion.id_profesional
            )
            .order_by(
                "fecha",
                "hora_inicio",
                "id_disponibilidad",
            )
        )

        prestacion_serializer = (
            PrestacionServicioAdministracionSerializer(
                prestacion
            )
        )

        reservas_serializer = (
            ReservaDisponibilidadAdministracionSerializer(
                reservas,
                many=True,
            )
        )

        coordinaciones_serializer = (
            CoordinacionSolicitudAdministracionSerializer(
                coordinaciones,
                many=True,
            )
        )

        bloques_data = []

        for bloque in bloques:
            reserva_activa = (
                ReservaDisponibilidad.objects
                .filter(
                    id_disponibilidad=bloque,
                    estado="ACTIVA",
                )
                .exists()
            )

            bloques_data.append(
                {
                    "id_disponibilidad": (
                        bloque.id_disponibilidad
                    ),
                    "fecha": bloque.fecha,
                    "hora_inicio": bloque.hora_inicio,
                    "hora_fin": bloque.hora_fin,
                    "estado": bloque.estado,
                    "tiene_reserva_activa": reserva_activa,
                }
            )

        return Response(
            {
                "prestacion": prestacion_serializer.data,
                "reservas": reservas_serializer.data,
                "historial_coordinacion": (
                    coordinaciones_serializer.data
                ),
                "bloques_profesional": bloques_data,
            }
        )

    def post(self, request, id_prestacion):
        """Agenda la primera reunión o aplica una operación base sobre la reserva.

        La primera reunión exige pago retenido y reserva activa futura del
        profesional; pasa la prestación a CONTRATADA. Si ya está contratada,
        devuelve su reunión AGENDADA existente. REAGENDAR y POSTERGAR con fecha
        sustituyen la reserva. CANCELAR cierra prestación y reserva sin reversa económica.

        Args:
            request (Request): Sesión administrativa con acción; modalidad y enlace
                opcionales para primera reunión; motivo y bloque nuevo para cambios
                de fecha, o motivo para cancelación.
            id_prestacion (int): Prestación que no debe estar FINALIZADA ni CANCELADA.

        Returns:
            Response: HTTP 201 al contratar, 200 en reintento o cambio de agenda,
            400 por datos inválidos y 409 por estados, pago, reunión o reserva incompatibles.

        Raises:
            Http404: Si falta la prestación o el bloque nuevo solicitado.
            PrestacionServicio.DoesNotExist: Si desaparece antes de bloquearla
                durante la primera contratación.

        Note:
            La subclase segura revalida los cambios y sincroniza las reuniones;
            esas garantías no se aplican al invocar este método aisladamente.
        """
        prestacion = get_object_or_404(
            PrestacionServicio.objects.select_related(
                "id_solicitud",
                "id_profesional",
            ),
            id_prestacion=id_prestacion,
        )

        if prestacion.estado in [
            "FINALIZADA",
            "CANCELADA",
        ]:
            return Response(
                {
                    "mensaje": (
                        "La prestación se encuentra cerrada "
                        "y no admite cambios de agenda."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        accion = str(
            request.data.get("accion", "")
        ).strip().upper()

        if accion == "AGENDAR_PRIMERA_REUNION":
            with transaction.atomic():
                pago = (
                    Pago.objects
                    .select_for_update()
                    .filter(
                        id_prestacion_id=id_prestacion
                    )
                    .first()
                )

                if pago is None:
                    return Response(
                        {
                            "mensaje": (
                                "La prestación todavía no "
                                "posee un pago asociado."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                if pago.estado_pago != "RETENIDO":
                    return Response(
                        {
                            "mensaje": (
                                "La primera reunión solo puede "
                                "agendarse cuando el pago se "
                                "encuentra retenido."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                prestacion = (
                    PrestacionServicio.objects
                    .select_for_update()
                    .select_related(
                        "id_solicitud",
                        "id_profesional",
                    )
                    .get(
                        id_prestacion=id_prestacion
                    )
                )

                if prestacion.estado == "CONTRATADA":
                    reunion_existente = (
                        ReunionSolicitud.objects
                        .filter(
                            id_solicitud=(
                                prestacion.id_solicitud
                            ),
                            id_profesional=(
                                prestacion.id_profesional
                            ),
                            estado="AGENDADA",
                        )
                        .order_by(
                            "fecha_hora",
                            "id_reunion",
                        )
                        .first()
                    )

                    if reunion_existente is None:
                        return Response(
                            {
                                "mensaje": (
                                    "La prestación figura "
                                    "contratada, pero no existe "
                                    "una primera reunión agendada. "
                                    "Se requiere revisión."
                                )
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                    return Response(
                        {
                            "mensaje": (
                                "La primera reunión ya se "
                                "encontraba agendada."
                            ),
                            "reunion": (
                                ReunionSolicitudAdministracionSerializer(
                                    reunion_existente
                                ).data
                            ),
                            "prestacion": (
                                PrestacionServicioAdministracionSerializer(
                                    prestacion
                                ).data
                            ),
                            "prestacion_contratada": True,
                        },
                        status=status.HTTP_200_OK,
                    )

                if (
                    prestacion.estado
                    != "PENDIENTE_CONTRATACION"
                ):
                    return Response(
                        {
                            "mensaje": (
                                "La prestación no se encuentra "
                                "en estado pendiente de "
                                "contratación."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                reserva = (
                    ReservaDisponibilidad.objects
                    .select_for_update()
                    .filter(
                        id_solicitud=(
                            prestacion.id_solicitud
                        ),
                        estado="ACTIVA",
                    )
                    .order_by(
                        "-fecha_reserva",
                        "-id_reserva",
                    )
                    .first()
                )

                if reserva is None:
                    return Response(
                        {
                            "mensaje": (
                                "La prestación no posee una "
                                "reserva activa."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                bloque = (
                    Disponibilidad.objects
                    .select_for_update()
                    .filter(
                        id_disponibilidad=(
                            reserva.id_disponibilidad_id
                        )
                    )
                    .first()
                )

                if bloque is None:
                    return Response(
                        {
                            "mensaje": (
                                "El bloque reservado ya no "
                                "existe."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                if (
                    bloque.id_profesional_id
                    != prestacion.id_profesional_id
                ):
                    return Response(
                        {
                            "mensaje": (
                                "El bloque reservado no "
                                "corresponde al profesional "
                                "de la prestación."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                if bloque.estado != "RESERVADA":
                    return Response(
                        {
                            "mensaje": (
                                "El bloque asociado todavía "
                                "no se encuentra reservado."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                fecha_hora_reunion = (
                    timezone.make_aware(
                        datetime.combine(
                            bloque.fecha,
                            bloque.hora_inicio,
                        ),
                        timezone.get_current_timezone(),
                    )
                )

                if (
                    fecha_hora_reunion
                    <= timezone.now()
                ):
                    return Response(
                        {
                            "mensaje": (
                                "El horario reservado ya "
                                "comenz? o qued? en el pasado."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                reunion_existente = (
                    ReunionSolicitud.objects
                    .filter(
                        id_solicitud=(
                            prestacion.id_solicitud
                        ),
                        id_profesional=(
                            prestacion.id_profesional
                        ),
                        estado="AGENDADA",
                    )
                    .order_by(
                        "fecha_hora",
                        "id_reunion",
                    )
                    .first()
                )

                if reunion_existente is not None:
                    return Response(
                        {
                            "mensaje": (
                                "Ya existe una primera reunión "
                                "agendada para esta prestación."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                modalidad = (
                    request.data.get("modalidad")
                    or prestacion.id_solicitud.modalidad
                )

                entrada_serializer = (
                    AgendarPrimeraReunionSerializer(
                        data={
                            "fecha_hora": (
                                fecha_hora_reunion
                            ),
                            "modalidad": modalidad,
                            "enlace_reunion": (
                                request.data.get(
                                    "enlace_reunion"
                                )
                            ),
                        }
                    )
                )

                if not entrada_serializer.is_valid():
                    return Response(
                        entrada_serializer.errors,
                        status=(
                            status.HTTP_400_BAD_REQUEST
                        ),
                    )

                datos = (
                    entrada_serializer.validated_data
                )

                ahora = timezone.now()

                reunion = (
                    ReunionSolicitud.objects.create(
                        id_solicitud=(
                            prestacion.id_solicitud
                        ),
                        id_profesional=(
                            prestacion.id_profesional
                        ),
                        id_usuario_skilly=request.user,
                        fecha_hora=(
                            datos["fecha_hora"]
                        ),
                        modalidad=(
                            datos["modalidad"]
                        ),
                        estado="AGENDADA",
                        enlace_reunion=(
                            datos.get(
                                "enlace_reunion"
                            )
                        ),
                    )
                )

                prestacion.estado = "CONTRATADA"
                prestacion.fecha_confirmacion = ahora

                prestacion.save(
                    update_fields=[
                        "estado",
                        "fecha_confirmacion",
                    ]
                )

                CoordinacionSolicitud.objects.create(
                    id_solicitud=(
                        prestacion.id_solicitud
                    ),
                    id_usuario_skilly=request.user,
                    tipo="AGENDAR_PRIMERA_REUNION",
                    detalle=(
                        f"Primera reunión agendada para "
                        f"{fecha_hora_reunion.isoformat()}. "
                        f"Bloque reservado: "
                        f"{bloque.id_disponibilidad}."
                    ),
                    estado_resultante="CONTRATADA",
                    fecha_registro=ahora,
                )

                prestacion.id_solicitud.fecha_actualizacion = (
                    ahora
                )

                prestacion.id_solicitud.save(
                    update_fields=[
                        "fecha_actualizacion",
                    ]
                )

                registrar_evento_trazabilidad(
                    usuario=request.user,
                    entidad_tipo="reunion_solicitud",
                    entidad_id=reunion.id_reunion,
                    accion="AGENDAR_PRIMERA_REUNION",
                    detalle_resumido=(
                        f"Primera reunión agendada para "
                        f"prestación "
                        f"{prestacion.id_prestacion}. "
                        f"Bloque "
                        f"{bloque.id_disponibilidad}."
                    )[:255],
                )

                registrar_evento_trazabilidad(
                    usuario=request.user,
                    entidad_tipo="prestacion_servicio",
                    entidad_id=(
                        prestacion.id_prestacion
                    ),
                    accion="CONTRATAR_PRESTACION",
                    detalle_resumido=(
                        f"Prestación "
                        f"{prestacion.id_prestacion} "
                        f"contratada después de pago "
                        f"retenido y primera reunión "
                        f"agendada."
                    )[:255],
                )

            return Response(
                {
                    "mensaje": (
                        "Primera reunión agendada "
                        "correctamente. La prestación "
                        "qued? formalmente contratada."
                    ),
                    "reunion": (
                        ReunionSolicitudAdministracionSerializer(
                            reunion
                        ).data
                    ),
                    "prestacion": (
                        PrestacionServicioAdministracionSerializer(
                            prestacion
                        ).data
                    ),
                    "prestacion_contratada": True,
                },
                status=status.HTTP_201_CREATED,
            )

        motivo = str(
            request.data.get("motivo", "")
        ).strip()

        if not motivo:
            return Response(
                {
                    "mensaje": (
                        "Debe indicar el motivo del cambio."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if accion in [
            "REAGENDAR",
            "POSTERGAR",
        ]:
            id_disponibilidad_nueva = request.data.get(
                "id_disponibilidad_nueva"
            )

            if not id_disponibilidad_nueva:
                return Response(
                    {
                        "mensaje": (
                            "Debe indicar "
                            "id_disponibilidad_nueva."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            reserva_actual = (
                ReservaDisponibilidad.objects
                .select_related(
                    "id_disponibilidad"
                )
                .filter(
                    id_solicitud=prestacion.id_solicitud,
                    estado="ACTIVA",
                )
                .order_by(
                    "-fecha_reserva",
                    "-id_reserva",
                )
                .first()
            )

            if reserva_actual is None:
                return Response(
                    {
                        "mensaje": (
                            "La prestación no posee una "
                            "reserva activa para reagendar."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            bloque_nuevo = get_object_or_404(
                Disponibilidad,
                id_disponibilidad=(
                    id_disponibilidad_nueva
                ),
            )

            if (
                bloque_nuevo.id_profesional_id
                != prestacion.id_profesional_id
            ):
                return Response(
                    {
                        "mensaje": (
                            "El nuevo bloque no pertenece "
                            "al profesional de la prestación."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                bloque_nuevo.id_disponibilidad
                == reserva_actual.id_disponibilidad_id
            ):
                return Response(
                    {
                        "mensaje": (
                            "El nuevo bloque debe ser distinto "
                            "del bloque actualmente reservado."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            bloque_ocupado = (
                ReservaDisponibilidad.objects
                .filter(
                    id_disponibilidad=bloque_nuevo,
                    estado="ACTIVA",
                )
                .exists()
            )

            if bloque_ocupado:
                return Response(
                    {
                        "mensaje": (
                            "El nuevo bloque ya posee una "
                            "reserva activa."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            ahora = timezone.now()

            with transaction.atomic():
                bloque_anterior = (
                    reserva_actual.id_disponibilidad
                )

                reserva_actual.estado = "REAGENDADA"
                reserva_actual.fecha_cambio = ahora
                reserva_actual.motivo_cambio = motivo
                reserva_actual.save(
                    update_fields=[
                        "estado",
                        "fecha_cambio",
                        "motivo_cambio",
                    ]
                )

                bloque_anterior.estado = "DISPONIBLE"
                bloque_anterior.save(
                    update_fields=[
                        "estado",
                    ]
                )

                bloque_nuevo.estado = "RESERVADA"
                bloque_nuevo.save(
                    update_fields=[
                        "estado",
                    ]
                )

                nueva_reserva = (
                    ReservaDisponibilidad.objects.create(
                        id_disponibilidad=bloque_nuevo,
                        id_solicitud=prestacion.id_solicitud,
                        estado="ACTIVA",
                        fecha_reserva=ahora,
                        fecha_cambio=None,
                        motivo_cambio=motivo,
                    )
                )

                CoordinacionSolicitud.objects.create(
                    id_solicitud=prestacion.id_solicitud,
                    id_usuario_skilly=request.user,
                    tipo=accion,
                    detalle=(
                        f"Bloque anterior: "
                        f"{bloque_anterior.id_disponibilidad}. "
                        f"Nuevo bloque: "
                        f"{bloque_nuevo.id_disponibilidad}. "
                        f"Motivo: {motivo}"
                    ),
                    estado_resultante=(
                        prestacion.id_solicitud.estado
                    ),
                    fecha_registro=ahora,
                )

                prestacion.id_solicitud.fecha_actualizacion = (
                    ahora
                )

                prestacion.id_solicitud.save(
                    update_fields=[
                        "fecha_actualizacion",
                    ]
                )

                registrar_evento_trazabilidad(
                    usuario=request.user,
                    entidad_tipo="reserva_disponibilidad",
                    entidad_id=nueva_reserva.id_reserva,
                    accion=accion,
                    detalle_resumido=(
                        f"Prestacion {prestacion.id_prestacion}. "
                        f"Reserva anterior "
                        f"{reserva_actual.id_reserva}; "
                        f"bloque anterior "
                        f"{bloque_anterior.id_disponibilidad}; "
                        f"nuevo bloque "
                        f"{bloque_nuevo.id_disponibilidad}. "
                        f"Motivo: {motivo}"
                    )[:255],
                )

            serializer = (
                ReservaDisponibilidadAdministracionSerializer(
                    nueva_reserva
                )
            )

            return Response(
                {
                    "mensaje": (
                        "Agenda actualizada correctamente."
                    ),
                    "reserva": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        if accion == "CANCELAR":
            ahora = timezone.now()

            reserva_actual = (
                ReservaDisponibilidad.objects
                .select_related(
                    "id_disponibilidad"
                )
                .filter(
                    id_solicitud=prestacion.id_solicitud,
                    estado="ACTIVA",
                )
                .order_by(
                    "-fecha_reserva",
                    "-id_reserva",
                )
                .first()
            )

            with transaction.atomic():
                if reserva_actual is not None:
                    reserva_actual.estado = "CANCELADA"
                    reserva_actual.fecha_cambio = ahora
                    reserva_actual.motivo_cambio = motivo

                    reserva_actual.save(
                        update_fields=[
                            "estado",
                            "fecha_cambio",
                            "motivo_cambio",
                        ]
                    )

                    bloque_anterior = (
                        reserva_actual.id_disponibilidad
                    )

                    bloque_anterior.estado = "DISPONIBLE"

                    bloque_anterior.save(
                        update_fields=[
                            "estado",
                        ]
                    )

                prestacion.estado = "CANCELADA"
                prestacion.fecha_cierre = ahora

                prestacion.save(
                    update_fields=[
                        "estado",
                        "fecha_cierre",
                    ]
                )

                CoordinacionSolicitud.objects.create(
                    id_solicitud=prestacion.id_solicitud,
                    id_usuario_skilly=request.user,
                    tipo="CANCELACION",
                    detalle=motivo,
                    estado_resultante="CANCELADA",
                    fecha_registro=ahora,
                )

                prestacion.id_solicitud.fecha_actualizacion = (
                    ahora
                )

                prestacion.id_solicitud.save(
                    update_fields=[
                        "fecha_actualizacion",
                    ]
                )

                if reserva_actual is not None:
                    registrar_evento_trazabilidad(
                        usuario=request.user,
                        entidad_tipo="reserva_disponibilidad",
                        entidad_id=reserva_actual.id_reserva,
                        accion="CANCELAR",
                        detalle_resumido=(
                            f"Reserva cancelada por cierre de "
                            f"prestacion "
                            f"{prestacion.id_prestacion}. "
                            f"Motivo: {motivo}"
                        )[:255],
                    )

                registrar_evento_trazabilidad(
                    usuario=request.user,
                    entidad_tipo="prestacion_servicio",
                    entidad_id=prestacion.id_prestacion,
                    accion="CANCELAR",
                    detalle_resumido=(
                        f"Prestacion cancelada. "
                        f"Solicitud "
                        f"{prestacion.id_solicitud_id}. "
                        f"Motivo: {motivo}"
                    )[:255],
                )

            return Response(
                {
                    "mensaje": (
                        "Prestación cancelada con "
                        "trazabilidad registrada."
                    ),
                    "siguiente_flujo": (
                        "Si existe un pago asociado, "
                        "corresponde gestionar CU040."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "mensaje": (
                    "La acción debe ser REAGENDAR, "
                    "POSTERGAR o CANCELAR."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class MisOportunidadesProfesionalView(APIView):
    """Restringe oportunidades a las asociaciones del perfil profesional autenticado."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
        """Lista oportunidades propias sin filtrar el estado de la asociación.

        Args:
            request (Request): Petición autenticada con rol profesional.

        Returns:
            Response: HTTP 200 con oportunidades por fecha descendente o 404
            si falta el perfil. No expone contactos empresariales.
        """
        profesional = Profesional.objects.filter(
            id_usuario=request.user
        ).first()

        if profesional is None:
            return Response(
                {
                    "mensaje": (
                        "El perfil profesional todavía "
                        "no se encuentra registrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        oportunidades = (
            SolicitudProfesional.objects
            .select_related(
                "id_solicitud__id_empresa",
                "id_solicitud__id_servicio",
                "id_profesional",
            )
            .filter(
                id_profesional=profesional
            )
            .order_by(
                "-fecha_asociacion",
            )
        )

        serializer = OportunidadProfesionalSerializer(
            oportunidades,
            many=True,
        )

        return Response(
            {
                "oportunidades": serializer.data,
            }
        )


class MisServiciosCoordinadosProfesionalView(APIView):
    """Consulta prestaciones propias con datos empresariales acotados al profesional."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
        """Lista prestaciones propias por confirmación e id descendentes.

        Args:
            request (Request): Sesión activa con rol profesional.

        Returns:
            Response: HTTP 200 con ``servicios_coordinados`` sin filtro por estado;
            HTTP 404 si la cuenta no tiene perfil profesional.
        """
        profesional = Profesional.objects.filter(
            id_usuario=request.user
        ).first()

        if profesional is None:
            return Response(
                {
                    "mensaje": (
                        "El perfil profesional todavía "
                        "no se encuentra registrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        prestaciones = (
            PrestacionServicio.objects
            .select_related(
                "id_solicitud__id_empresa",
                "id_solicitud__id_servicio",
                "id_profesional",
            )
            .filter(
                id_profesional=profesional
            )
            .order_by(
                "-fecha_confirmacion",
                "-id_prestacion",
            )
        )

        serializer = (
            ServicioCoordinadoProfesionalSerializer(
                prestaciones,
                many=True,
            )
        )

        return Response(
            {
                "servicios_coordinados": serializer.data,
            }
        )
