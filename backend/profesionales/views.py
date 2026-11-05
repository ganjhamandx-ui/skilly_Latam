from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import (
    EsAdministracionSkilly,
    EsProfesional,
)

from .models import (
    BloqueEntrevistaValidacion,
    DocumentoProfesional,
    EntrevistaValidacion,
    Profesional,
    SolicitudValidacion,
    ValidacionDocumento,
)
from .serializers import (
    ActualizarObservacionValidacionSerializer,
    BloqueEntrevistaAdministracionSerializer,
    DocumentoProfesionalSerializer,
    EntrevistaProfesionalSerializer,
    EstadoValidacionSerializer,
    PerfilProfesionalSerializer,
    RevisionValidacionAdministracionSerializer,
)


@method_decorator(csrf_protect, name="dispatch")
class PerfilProfesionalPropioView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def obtener_perfil(self, usuario):
        return Profesional.objects.filter(
            id_usuario=usuario
        ).first()

    def get(self, request):
        profesional = self.obtener_perfil(
            request.user
        )

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

        serializer = PerfilProfesionalSerializer(
            profesional
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        profesional = self.obtener_perfil(
            request.user
        )

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

        serializer = PerfilProfesionalSerializer(
            profesional,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        return Response(
            {
                "mensaje": (
                    "Perfil profesional actualizado "
                    "correctamente."
                ),
                "perfil": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class DocumentosProfesionalesPropiosView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
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

        documentos = (
            DocumentoProfesional.objects
            .filter(
                id_profesional=profesional
            )
            .order_by(
                "-fecha_carga",
                "-id_documento",
            )
        )

        serializer = DocumentoProfesionalSerializer(
            documentos,
            many=True,
        )

        solicitud = (SolicitudValidacion.objects
            .filter(id_profesional=profesional)
            .order_by("-fecha_solicitud", "-id_validacion")
            .first())
        validado = profesional.estado_validacion == "APROBADO"
        # Es una indicación visual; la restricción real se aplica en POST.
        carga_nueva_permitida = solicitud is None or validado
        ids_rechazados = []
        if solicitud is not None and not validado and solicitud.estado != "APROBADA":
            ids_rechazados = list(
                ValidacionDocumento.objects.filter(
                    id_validacion=solicitud,
                    estado_revision="RECHAZADA",
                ).values_list("id_documento_id", flat=True)
            )

        return Response(
            {
                "documentos": serializer.data,
                "politica_carga": {
                    "nuevos_permitidos": carga_nueva_permitida,
                    "ids_rechazados": ids_rechazados,
                    "etapa": (
                        "VALIDADO" if validado else
                        "INICIAL" if solicitud is None else
                        "REVISION_INICIAL"
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )


class EstadoValidacionPropiaView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
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

        solicitud = (
            SolicitudValidacion.objects
            .filter(
                id_profesional=profesional
            )
            .order_by(
                "-fecha_solicitud",
                "-id_validacion",
            )
            .first()
        )

        if solicitud is None:
            return Response(
                {
                    "mensaje": (
                        "No existe una solicitud de "
                        "validación asociada al perfil."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EstadoValidacionSerializer(
            solicitud
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class MiEntrevistaValidacionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
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

        entrevista = (
            EntrevistaValidacion.objects
            .select_related(
                "id_validacion",
                "id_bloque_entrevista",
            )
            .filter(
                id_validacion__id_profesional=profesional
            )
            .order_by(
                "-fecha_reserva",
                "-id_entrevista",
            )
            .first()
        )

        if entrevista is None:
            return Response(
                {
                    "mensaje": (
                        "No existe una entrevista de "
                        "validación asociada al perfil."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EntrevistaProfesionalSerializer(
            entrevista
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class BandejaValidacionesAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        solicitudes = (
            SolicitudValidacion.objects
            .select_related(
                "id_profesional",
                "id_profesional__id_usuario",
            )
            .order_by(
                "-fecha_solicitud",
                "-id_validacion",
            )
        )

        serializer = RevisionValidacionAdministracionSerializer(
            solicitudes,
            many=True,
        )

        return Response(
            {
                "solicitudes": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class DetalleValidacionAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def obtener_solicitud(self, id_validacion):
        return (
            SolicitudValidacion.objects
            .select_related(
                "id_profesional",
                "id_profesional__id_usuario",
            )
            .filter(
                id_validacion=id_validacion
            )
            .first()
        )

    def get(self, request, id_validacion):
        solicitud = self.obtener_solicitud(
            id_validacion
        )

        if solicitud is None:
            return Response(
                {
                    "mensaje": (
                        "La solicitud de validación "
                        "no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RevisionValidacionAdministracionSerializer(
            solicitud
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, id_validacion):
        solicitud = self.obtener_solicitud(
            id_validacion
        )

        if solicitud is None:
            return Response(
                {
                    "mensaje": (
                        "La solicitud de validación "
                        "no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ActualizarObservacionValidacionSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        solicitud.observacion_resultado = (
            serializer.validated_data[
                "observacion_resultado"
            ]
        )

        solicitud.save(
            update_fields=[
                "observacion_resultado"
            ]
        )

        resultado = (
            RevisionValidacionAdministracionSerializer(
                solicitud
            )
        )

        return Response(
            {
                "mensaje": (
                    "Observación interna actualizada "
                    "correctamente."
                ),
                "solicitud": resultado.data,
            },
            status=status.HTTP_200_OK,
        )


class AgendaEntrevistasAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        bloques = (
            BloqueEntrevistaValidacion.objects
            .select_related(
                "id_usuario_gestor"
            )
            .order_by(
                "fecha",
                "hora_inicio",
                "id_bloque_entrevista",
            )
        )

        serializer = BloqueEntrevistaAdministracionSerializer(
            bloques,
            many=True,
        )

        return Response(
            {
                "bloques": serializer.data,
            },
            status=status.HTTP_200_OK,
        )