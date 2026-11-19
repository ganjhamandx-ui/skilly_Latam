"""Reserva entrevistas evitando solapamientos y cupos concurrentes."""

from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsProfesional
from backoffice.services import registrar_evento_trazabilidad

from .models import (
    Profesional,
    SolicitudValidacion,
    BloqueEntrevistaValidacion,
    EntrevistaValidacion,
)

from .serializers import EntrevistaProfesionalSerializer
from .revision_documental import revision_completa


class ReservarEntrevistaSerializer(serializers.Serializer):
    id_bloque_entrevista = serializers.IntegerField(
        min_value=1
    )


@method_decorator(csrf_protect, name="dispatch")
class ReservaEntrevistaProfesionalView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def obtener_validacion(self, usuario, bloquear=False):
        profesional = Profesional.objects.filter(
            id_usuario=usuario
        ).first()

        if profesional is None:
            return None, None

        solicitudes = SolicitudValidacion.objects.filter(
            id_profesional=profesional
        )

        if bloquear:
            solicitudes = solicitudes.select_for_update()

        solicitud = solicitudes.order_by(
            "-fecha_solicitud",
            "-id_validacion",
        ).first()

        return profesional, solicitud

    def validar_solicitud(self, profesional, solicitud):
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

        if solicitud.estado != "APROBADA":
            return Response(
                {
                    "mensaje": (
                        "La solicitud de validación no "
                        "está habilitada para agendar "
                        "una entrevista."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not revision_completa(solicitud):
            return Response(
                {"mensaje": "Hay documentos vigentes sin aprobación individual."},
                status=status.HTTP_409_CONFLICT,
            )

        # Las cancelaciones permanecen en el historial, pero no impiden
        # reservar un nuevo bloque ni consumen cupo.
        if EntrevistaValidacion.objects.filter(
            id_validacion=solicitud
        ).exclude(estado="CANCELADA").exists():
            return Response(
                {
                    "mensaje": (
                        "Esta solicitud de validación "
                        "ya tiene una entrevista registrada."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return None

    def bloque_en_horario_valido(self, bloque, ahora):
        if bloque.fecha < ahora.date():
            return False

        if bloque.hora_inicio >= bloque.hora_fin:
            return False

        if bloque.fecha == ahora.date():
            hora_actual = ahora.time().replace(
                tzinfo=None
            )

            if bloque.hora_inicio <= hora_actual:
                return False

        return True

    def get(self, request):
        profesional, solicitud = self.obtener_validacion(
            request.user
        )

        error = self.validar_solicitud(
            profesional,
            solicitud,
        )

        if error is not None:
            return error

        ahora = timezone.localtime()

        bloques = BloqueEntrevistaValidacion.objects.filter(
            estado="DISPONIBLE",
            capacidad__gt=0,
            fecha__gte=ahora.date(),
        ).order_by(
            "fecha",
            "hora_inicio",
            "id_bloque_entrevista",
        )

        reservas = (
            EntrevistaValidacion.objects
            .exclude(estado="CANCELADA")
            .values("id_bloque_entrevista")
            .annotate(total=Count("id_entrevista"))
        )

        ocupacion = {
            registro["id_bloque_entrevista"]: registro["total"]
            for registro in reservas
        }

        disponibles = []

        for bloque in bloques:
            if not self.bloque_en_horario_valido(
                bloque,
                ahora,
            ):
                continue

            ocupados = ocupacion.get(
                bloque.id_bloque_entrevista,
                0,
            )

            cupos_restantes = bloque.capacidad - ocupados

            if cupos_restantes <= 0:
                continue

            disponibles.append(
                {
                    "id_bloque_entrevista": (
                        bloque.id_bloque_entrevista
                    ),
                    "fecha": bloque.fecha,
                    "hora_inicio": bloque.hora_inicio,
                    "hora_fin": bloque.hora_fin,
                    "cupos_disponibles": cupos_restantes,
                }
            )

        return Response(
            {
                "id_validacion": solicitud.id_validacion,
                "bloques_disponibles": disponibles,
                "total": len(disponibles),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        entrada = ReservarEntrevistaSerializer(
            data=request.data
        )

        if not entrada.is_valid():
            return Response(
                entrada.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        id_bloque = entrada.validated_data[
            "id_bloque_entrevista"
        ]

        with transaction.atomic():
            profesional, solicitud = self.obtener_validacion(
                request.user,
                bloquear=True,
            )

            error = self.validar_solicitud(
                profesional,
                solicitud,
            )

            if error is not None:
                return error

            bloque = (
                BloqueEntrevistaValidacion.objects
                .select_for_update()
                .filter(
                    id_bloque_entrevista=id_bloque
                )
                .first()
            )

            if bloque is None:
                return Response(
                    {
                        "mensaje": (
                            "El bloque solicitado no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            ahora = timezone.localtime()

            if (
                bloque.estado != "DISPONIBLE"
                or bloque.capacidad <= 0
                or not self.bloque_en_horario_valido(
                    bloque,
                    ahora,
                )
            ):
                return Response(
                    {
                        "mensaje": (
                            "El bloque seleccionado no "
                            "está disponible para reservas."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            reservas_actuales = (
                EntrevistaValidacion.objects
                .filter(
                    id_bloque_entrevista=bloque
                )
                .exclude(estado="CANCELADA")
                .count()
            )

            if reservas_actuales >= bloque.capacidad:
                return Response(
                    {
                        "mensaje": (
                            "El bloque seleccionado "
                            "ya no tiene cupos disponibles."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            entrevista = EntrevistaValidacion.objects.create(
                id_validacion=solicitud,
                id_bloque_entrevista=bloque,
                estado="AGENDADA",
                fecha_reserva=timezone.now(),
            )

            resultado = EntrevistaProfesionalSerializer(
                entrevista
            )

        return Response(
            {
                "mensaje": (
                    "Entrevista de validación "
                    "agendada correctamente."
                ),
                "entrevista": resultado.data,
            },
            status=status.HTTP_201_CREATED,
        )


class CancelarEntrevistaProfesionalSerializer(serializers.Serializer):
    motivo = serializers.CharField(
        trim_whitespace=True, min_length=10, max_length=500
    )


@method_decorator(csrf_protect, name="dispatch")
class CancelarEntrevistaProfesionalView(APIView):
    """Cancelación voluntaria de entrevista de validación, con historial.

    No cambia la validación documental, los pagos ni las prestaciones.
    Una cancelación tardía queda registrada para revisión, sin sanción
    económica o suspensión automática.
    """

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    http_method_names = ["post", "options"]

    def post(self, request):
        entrada = CancelarEntrevistaProfesionalSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)

        motivo = entrada.validated_data["motivo"]
        with transaction.atomic():
            profesional = Profesional.objects.filter(
                id_usuario=request.user
            ).first()
            if profesional is None:
                return Response({"mensaje": "Perfil profesional inexistente."},
                                status=status.HTTP_404_NOT_FOUND)

            # El orden de bloqueo es el mismo que al reservar una entrevista.
            solicitud = (SolicitudValidacion.objects.select_for_update()
                         .filter(id_profesional=profesional)
                         .order_by("-fecha_solicitud", "-id_validacion").first())
            if solicitud is None:
                return Response({"mensaje": "Solicitud de validación inexistente."},
                                status=status.HTTP_404_NOT_FOUND)
            if solicitud.estado != "APROBADA":
                return Response({"mensaje": "La validación no permite cambios de entrevista."},
                                status=status.HTTP_409_CONFLICT)

            entrevista = (EntrevistaValidacion.objects.select_for_update()
                          .select_related("id_bloque_entrevista")
                          .filter(id_validacion=solicitud, estado="AGENDADA")
                          .order_by("-fecha_reserva", "-id_entrevista").first())
            if entrevista is None:
                return Response({"mensaje": "No existe una entrevista agendada para cancelar."},
                                status=status.HTTP_409_CONFLICT)

            bloque = entrevista.id_bloque_entrevista
            inicio = timezone.make_aware(
                datetime.combine(bloque.fecha, bloque.hora_inicio),
                timezone.get_current_timezone(),
            )
            ahora = timezone.now()
            if inicio <= ahora:
                return Response({
                    "mensaje": "La entrevista ya comenzó o pasó. Solicita revisión a SKILLY."
                }, status=status.HTTP_409_CONFLICT)

            tardia = inicio - ahora < timedelta(hours=24)
            entrevista.estado = "CANCELADA"
            entrevista.observacion = (
                f"Cancelación solicitada por el profesional. "
                f"{'Menos de 24 horas; pendiente de revisión administrativa. ' if tardia else ''}"
                f"Motivo: {motivo}"
            )
            entrevista.save(update_fields=["estado", "observacion"])
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="entrevista_validacion",
                entidad_id=entrevista.pk,
                accion="CANCELACION_PROFESIONAL",
                detalle_resumido=(
                    f"Entrevista #{entrevista.pk} cancelada; "
                    f"{'TARDIA' if tardia else 'ANTICIPADA'}. "
                    f"Motivo: {motivo}"
                )[:255],
            )

            return Response({
                "mensaje": (
                    "Entrevista cancelada. SKILLY revisará la cancelación tardía. "
                    "Puedes solicitar otro horario."
                    if tardia else
                    "Entrevista cancelada. Puedes reservar otro horario."
                ),
                "entrevista": EntrevistaProfesionalSerializer(entrevista).data,
                "requiere_revision": tardia,
            }, status=status.HTTP_200_OK)
