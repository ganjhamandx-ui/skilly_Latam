"""Gestiona bloques de entrevista con validación transaccional de disponibilidad."""

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.models import Usuario
from acceso.permissions import EsAdministracionSkilly
from backoffice.services import registrar_evento_trazabilidad

from .models import (
    BloqueEntrevistaValidacion,
    EntrevistaValidacion,
)
from .serializers import (
    BloqueEntrevistaAdministracionSerializer,
)


ESTADOS_BLOQUE = [
    "DISPONIBLE",
    "DESHABILITADO",
]

CAMPOS_BLOQUE = {
    "fecha",
    "hora_inicio",
    "hora_fin",
    "capacidad",
    "estado",
}


class DatosBloqueEntrevistaSerializer(serializers.Serializer):
    fecha = serializers.DateField()

    hora_inicio = serializers.TimeField()

    hora_fin = serializers.TimeField()

    capacidad = serializers.IntegerField(
        min_value=1
    )

    estado = serializers.ChoiceField(
        choices=ESTADOS_BLOQUE,
        default="DISPONIBLE",
    )


def respuesta_error(mensaje, codigo):
    return Response(
        {"mensaje": mensaje},
        status=codigo,
    )


def validar_campos(datos):
    if not isinstance(datos, dict) or not datos:
        return respuesta_error(
            "Debe enviar los datos del bloque.",
            status.HTTP_400_BAD_REQUEST,
        )

    desconocidos = set(datos.keys()) - CAMPOS_BLOQUE

    if desconocidos:
        return respuesta_error(
            "La solicitud contiene campos no permitidos: "
            + ", ".join(sorted(desconocidos)),
            status.HTTP_400_BAD_REQUEST,
        )

    return None


def validar_horario(fecha, hora_inicio, hora_fin):
    if hora_inicio >= hora_fin:
        return respuesta_error(
            "La hora de término debe ser posterior "
            "a la hora de inicio.",
            status.HTTP_400_BAD_REQUEST,
        )

    ahora = timezone.localtime()

    if fecha < ahora.date():
        return respuesta_error(
            "No se pueden programar bloques en el pasado.",
            status.HTTP_400_BAD_REQUEST,
        )

    hora_actual = ahora.time().replace(
        tzinfo=None
    )

    if (
        fecha == ahora.date()
        and hora_inicio <= hora_actual
    ):
        return respuesta_error(
            "El horario seleccionado ya comenzó "
            "o se encuentra en el pasado.",
            status.HTTP_400_BAD_REQUEST,
        )

    return None


def existe_conflicto_horario(
    gestor_id,
    fecha,
    hora_inicio,
    hora_fin,
    excluir_id=None,
):
    bloques = BloqueEntrevistaValidacion.objects.filter(
        id_usuario_gestor_id=gestor_id,
        fecha=fecha,
        estado="DISPONIBLE",
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    )

    if excluir_id is not None:
        bloques = bloques.exclude(
            id_bloque_entrevista=excluir_id
        )

    return bloques.exists()


@method_decorator(csrf_protect, name="dispatch")
class CrearBloqueEntrevistaAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def post(self, request):
        error = validar_campos(request.data)

        if error is not None:
            return error

        entrada = DatosBloqueEntrevistaSerializer(
            data=request.data
        )

        if not entrada.is_valid():
            return Response(
                entrada.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        datos = entrada.validated_data

        error = validar_horario(
            datos["fecha"],
            datos["hora_inicio"],
            datos["hora_fin"],
        )

        if error is not None:
            return error

        with transaction.atomic():
            # Evita creaciones simultáneas conflictivas
            # para el mismo gestor.
            Usuario.objects.select_for_update().get(
                pk=request.user.pk
            )

            if (
                datos["estado"] == "DISPONIBLE"
                and existe_conflicto_horario(
                    gestor_id=request.user.pk,
                    fecha=datos["fecha"],
                    hora_inicio=datos["hora_inicio"],
                    hora_fin=datos["hora_fin"],
                )
            ):
                return respuesta_error(
                    "El gestor ya tiene un bloque "
                    "disponible que se superpone "
                    "con este horario.",
                    status.HTTP_409_CONFLICT,
                )

            bloque = (
                BloqueEntrevistaValidacion.objects.create(
                    id_usuario_gestor=request.user,
                    fecha=datos["fecha"],
                    hora_inicio=datos["hora_inicio"],
                    hora_fin=datos["hora_fin"],
                    capacidad=datos["capacidad"],
                    estado=datos["estado"],
                )
            )

            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="bloque_entrevista_validacion",
                entidad_id=bloque.pk,
                accion="CREAR_BLOQUE_ENTREVISTA",
                detalle_resumido=(
                    f"Bloque {bloque.pk} creado "
                    f"para {bloque.fecha}, "
                    f"de {bloque.hora_inicio} "
                    f"a {bloque.hora_fin}. "
                    f"Capacidad: {bloque.capacidad}."
                )[:255],
            )

        resultado = (
            BloqueEntrevistaAdministracionSerializer(
                bloque
            )
        )

        return Response(
            {
                "mensaje": (
                    "Bloque de entrevista creado "
                    "correctamente."
                ),
                "bloque": resultado.data,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class ModificarBloqueEntrevistaAdministracionView(
    APIView
):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def patch(
        self,
        request,
        id_bloque_entrevista,
    ):
        error = validar_campos(request.data)

        if error is not None:
            return error

        entrada = DatosBloqueEntrevistaSerializer(
            data=request.data,
            partial=True,
        )

        if not entrada.is_valid():
            return Response(
                entrada.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        cambios = entrada.validated_data

        with transaction.atomic():
            bloque = (
                BloqueEntrevistaValidacion.objects
                .select_for_update()
                .filter(
                    id_bloque_entrevista=id_bloque_entrevista
                )
                .first()
            )

            if bloque is None:
                return respuesta_error(
                    "El bloque de entrevista no existe.",
                    status.HTTP_404_NOT_FOUND,
                )

            # Conserva el gestor original del bloque.
            gestor_id = bloque.id_usuario_gestor_id

            if gestor_id is not None:
                Usuario.objects.select_for_update().get(
                    pk=gestor_id
                )

            fecha = cambios.get(
                "fecha",
                bloque.fecha,
            )

            hora_inicio = cambios.get(
                "hora_inicio",
                bloque.hora_inicio,
            )

            hora_fin = cambios.get(
                "hora_fin",
                bloque.hora_fin,
            )

            capacidad = cambios.get(
                "capacidad",
                bloque.capacidad,
            )

            estado_nuevo = cambios.get(
                "estado",
                bloque.estado,
            )

            if estado_nuevo not in ESTADOS_BLOQUE:
                return respuesta_error(
                    "El estado actual del bloque "
                    "no permite esta modificación.",
                    status.HTTP_409_CONFLICT,
                )

            cambio_horario = (
                fecha != bloque.fecha
                or hora_inicio != bloque.hora_inicio
                or hora_fin != bloque.hora_fin
            )

            reservas = (
                EntrevistaValidacion.objects
                .filter(
                    id_bloque_entrevista=bloque
                )
                .exclude(estado="CANCELADA")
                .count()
            )

            # No cambia el horario de entrevistas
            # que ya están registradas.
            if reservas > 0 and cambio_horario:
                return respuesta_error(
                    "No se puede cambiar la fecha "
                    "ni el horario de un bloque "
                    "que ya tiene entrevistas.",
                    status.HTTP_409_CONFLICT,
                )

            if reservas > 0 and estado_nuevo == "DESHABILITADO":
                return respuesta_error(
                    "No se puede deshabilitar un bloque con entrevistas reservadas.",
                    status.HTTP_409_CONFLICT,
                )

            # La capacidad nunca puede ser menor
            # que las entrevistas registradas.
            if capacidad < reservas:
                return respuesta_error(
                    "La capacidad no puede ser menor "
                    "que la cantidad de entrevistas "
                    "registradas en el bloque.",
                    status.HTTP_409_CONFLICT,
                )

            # Los horarios nuevos o habilitados
            # deben ser futuros y válidos.
            if (
                cambio_horario
                or estado_nuevo == "DISPONIBLE"
            ):
                error = validar_horario(
                    fecha,
                    hora_inicio,
                    hora_fin,
                )

                if error is not None:
                    return error

            if estado_nuevo == "DISPONIBLE":
                if existe_conflicto_horario(
                    gestor_id=gestor_id,
                    fecha=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    excluir_id=bloque.pk,
                ):
                    return respuesta_error(
                        "El horario se superpone "
                        "con otro bloque disponible "
                        "del mismo gestor.",
                        status.HTTP_409_CONFLICT,
                    )

            bloque.fecha = fecha
            bloque.hora_inicio = hora_inicio
            bloque.hora_fin = hora_fin
            bloque.capacidad = capacidad
            bloque.estado = estado_nuevo

            bloque.save(
                update_fields=[
                    "fecha",
                    "hora_inicio",
                    "hora_fin",
                    "capacidad",
                    "estado",
                ]
            )

            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="bloque_entrevista_validacion",
                entidad_id=bloque.pk,
                accion="MODIFICAR_BLOQUE_ENTREVISTA",
                detalle_resumido=(
                    f"Bloque {bloque.pk} actualizado. "
                    f"Fecha: {bloque.fecha}. "
                    f"Horario: {bloque.hora_inicio} "
                    f"a {bloque.hora_fin}. "
                    f"Capacidad: {bloque.capacidad}. "
                    f"Estado: {bloque.estado}. "
                    f"Reservas registradas: {reservas}."
                )[:255],
            )

        resultado = (
            BloqueEntrevistaAdministracionSerializer(
                bloque
            )
        )

        return Response(
            {
                "mensaje": (
                    "Bloque de entrevista actualizado "
                    "correctamente."
                ),
                "bloque": resultado.data,
            },
            status=status.HTTP_200_OK,
        )
