"""Implementa el ciclo de solicitudes y reservas con control transaccional."""

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsProfesional
from backoffice.models import EventoTrazabilidad
from marketplace.models import (
    Servicio,
    ServicioCompetencia,
)
from profesionales.models import Profesional

from .models import (
    ContactoEmpresa,
    Disponibilidad,
    EmpresaSolicitante,
    ReservaDisponibilidad,
    SolicitudCompetencia,
    SolicitudServicio,
)
from .serializers import (
    DisponibilidadProfesionalSerializer,
    EnviarSolicitudServicioSerializer,
    GuardarDisponibilidadProfesionalSerializer,
    SolicitudServicioPublicaSerializer,
)


def obtener_profesional(usuario):
    """Resuelve el perfil profesional activo del usuario autenticado."""

    return Profesional.objects.filter(
        id_usuario=usuario
    ).first()


def existe_conflicto_disponibilidad(
    profesional,
    fecha,
    hora_inicio,
    hora_fin,
    excluir_id=None,
):
    """Detecta solapamientos de bloques vigentes para un mismo profesional."""

    bloques = Disponibilidad.objects.filter(
        id_profesional=profesional,
        fecha=fecha,
        hora_inicio__lt=hora_fin,
        hora_fin__gt=hora_inicio,
    )

    if excluir_id is not None:
        bloques = bloques.exclude(
            id_disponibilidad=excluir_id
        )

    return bloques.exists()


class MiDisponibilidadProfesionalView(
    APIView
):
    """Lista y registra disponibilidad del profesional autenticado."""

    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
        """Lista los bloques de disponibilidad del profesional autenticado."""
        profesional = obtener_profesional(
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

        bloques = (
            Disponibilidad.objects
            .filter(
                id_profesional=profesional
            )
            .order_by(
                "fecha",
                "hora_inicio",
                "id_disponibilidad",
            )
        )

        serializer = (
            DisponibilidadProfesionalSerializer(
                bloques,
                many=True,
            )
        )

        return Response(
            {
                "disponibilidad": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """Crea un bloque profesional tras validar conflictos y fechas."""
        profesional = obtener_profesional(
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

        entrada_serializer = (
            GuardarDisponibilidadProfesionalSerializer(
                data=request.data
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

        if existe_conflicto_disponibilidad(
            profesional=profesional,
            fecha=datos["fecha"],
            hora_inicio=datos["hora_inicio"],
            hora_fin=datos["hora_fin"],
        ):
            return Response(
                {
                    "mensaje": (
                        "El nuevo bloque se superpone "
                        "con otro bloque de "
                        "disponibilidad del "
                        "profesional."
                    )
                },
                status=(
                    status.HTTP_409_CONFLICT
                ),
            )

        with transaction.atomic():
            bloque = (
                Disponibilidad.objects
                .create(
                    id_profesional=profesional,
                    fecha=datos["fecha"],
                    hora_inicio=(
                        datos["hora_inicio"]
                    ),
                    hora_fin=(
                        datos["hora_fin"]
                    ),
                    estado="DISPONIBLE",
                )
            )

            EventoTrazabilidad.objects.create(
                id_usuario=request.user,
                entidad_tipo="disponibilidad",
                entidad_id=(
                    bloque.id_disponibilidad
                ),
                accion=(
                    "CREAR_BLOQUE_DISPONIBILIDAD"
                ),
                detalle_resumido=(
                    f"El profesional creó el bloque "
                    f"{bloque.id_disponibilidad} "
                    f"para {bloque.fecha} entre "
                    f"{bloque.hora_inicio} y "
                    f"{bloque.hora_fin}."
                )[:255],
                fecha_evento=timezone.now(),
            )

        serializer = (
            DisponibilidadProfesionalSerializer(
                bloque
            )
        )

        return Response(
            {
                "mensaje": (
                    "Bloque de disponibilidad "
                    "creado correctamente."
                ),
                "disponibilidad": (
                    serializer.data
                ),
            },
            status=(
                status.HTTP_201_CREATED
            ),
        )


class DetalleDisponibilidadProfesionalView(
    APIView
):
    """Actualiza o deshabilita un bloque propio cuando no está reservado."""

    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsProfesional
    ]

    def get(
        self,
        request,
        id_disponibilidad,
    ):
        """Obtiene un bloque que pertenece al profesional autenticado."""
        profesional = obtener_profesional(
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
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        bloque = (
            Disponibilidad.objects
            .filter(
                id_disponibilidad=(
                    id_disponibilidad
                ),
                id_profesional=profesional,
            )
            .first()
        )

        if bloque is None:
            return Response(
                {
                    "mensaje": (
                        "El bloque de disponibilidad "
                        "no existe o no pertenece al "
                        "profesional autenticado."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        serializer = (
            DisponibilidadProfesionalSerializer(
                bloque
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(
        self,
        request,
        id_disponibilidad,
    ):
        """Actualiza un bloque propio si no existe reserva ni conflicto horario."""
        profesional = obtener_profesional(
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
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        with transaction.atomic():
            bloque = (
                Disponibilidad.objects
                .select_for_update()
                .filter(
                    id_disponibilidad=(
                        id_disponibilidad
                    ),
                    id_profesional=profesional,
                )
                .first()
            )

            if bloque is None:
                return Response(
                    {
                        "mensaje": (
                            "El bloque de disponibilidad "
                            "no existe o no pertenece al "
                            "profesional autenticado."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )

            if (
                bloque.estado != "DISPONIBLE"
                or ReservaDisponibilidad.objects.filter(
                    id_disponibilidad=bloque,
                    estado__in=[
                        "PENDIENTE_PAGO",
                        "ACTIVA",
                    ],
                ).exists()
            ):
                return Response(
                    {
                        "mensaje": (
                            "Un bloque reservado no "
                            "puede ser modificado por "
                            "el profesional."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            entrada_serializer = (
                GuardarDisponibilidadProfesionalSerializer(
                    data=request.data,
                    partial=True,
                    context={
                        "bloque_actual": bloque
                    },
                )
            )

            if not entrada_serializer.is_valid():
                return Response(
                    entrada_serializer.errors,
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

            if not (
                entrada_serializer
                .validated_data
            ):
                return Response(
                    {
                        "mensaje": (
                            "Debe indicar al menos "
                            "un campo para actualizar."
                        )
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )

            datos = (
                entrada_serializer
                .validated_data
            )

            fecha = datos.get(
                "fecha",
                bloque.fecha,
            )

            hora_inicio = datos.get(
                "hora_inicio",
                bloque.hora_inicio,
            )

            hora_fin = datos.get(
                "hora_fin",
                bloque.hora_fin,
            )

            if existe_conflicto_disponibilidad(
                profesional=profesional,
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                excluir_id=(
                    bloque.id_disponibilidad
                ),
            ):
                return Response(
                    {
                        "mensaje": (
                            "El bloque actualizado se "
                            "superpone con otro bloque "
                            "del profesional."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            bloque.fecha = fecha
            bloque.hora_inicio = (
                hora_inicio
            )
            bloque.hora_fin = hora_fin

            bloque.save(
                update_fields=[
                    "fecha",
                    "hora_inicio",
                    "hora_fin",
                ]
            )

            EventoTrazabilidad.objects.create(
                id_usuario=request.user,
                entidad_tipo="disponibilidad",
                entidad_id=(
                    bloque.id_disponibilidad
                ),
                accion=(
                    "ACTUALIZAR_BLOQUE_"
                    "DISPONIBILIDAD"
                ),
                detalle_resumido=(
                    f"El profesional actualizó el "
                    f"bloque "
                    f"{bloque.id_disponibilidad} "
                    f"para {bloque.fecha} entre "
                    f"{bloque.hora_inicio} y "
                    f"{bloque.hora_fin}."
                )[:255],
                fecha_evento=timezone.now(),
            )

        serializer = (
            DisponibilidadProfesionalSerializer(
                bloque
            )
        )

        return Response(
            {
                "mensaje": (
                    "Bloque de disponibilidad "
                    "actualizado correctamente."
                ),
                "disponibilidad": (
                    serializer.data
                ),
            },
            status=status.HTTP_200_OK,
        )

    def delete(
        self,
        request,
        id_disponibilidad,
    ):
        """Retira un bloque propio solo cuando no mantiene reservas protegidas."""
        profesional = obtener_profesional(
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
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        with transaction.atomic():
            bloque = (
                Disponibilidad.objects
                .select_for_update()
                .filter(
                    id_disponibilidad=(
                        id_disponibilidad
                    ),
                    id_profesional=profesional,
                )
                .first()
            )

            if bloque is None:
                return Response(
                    {
                        "mensaje": (
                            "El bloque de disponibilidad "
                            "no existe o no pertenece al "
                            "profesional autenticado."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )

            if (
                bloque.estado != "DISPONIBLE"
                or ReservaDisponibilidad.objects.filter(
                    id_disponibilidad=bloque,
                    estado__in=[
                        "PENDIENTE_PAGO",
                        "ACTIVA",
                    ],
                ).exists()
            ):
                return Response(
                    {
                        "mensaje": (
                            "Un bloque reservado no "
                            "puede ser eliminado por "
                            "el profesional."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            id_bloque = (
                bloque.id_disponibilidad
            )

            EventoTrazabilidad.objects.create(
                id_usuario=request.user,
                entidad_tipo="disponibilidad",
                entidad_id=id_bloque,
                accion=(
                    "ELIMINAR_BLOQUE_"
                    "DISPONIBILIDAD"
                ),
                detalle_resumido=(
                    f"El profesional eliminó el "
                    f"bloque {id_bloque} de "
                    f"disponibilidad."
                )[:255],
                fecha_evento=timezone.now(),
            )

            bloque.delete()

        return Response(
            {
                "mensaje": (
                    "Bloque de disponibilidad "
                    "eliminado correctamente."
                )
            },
            status=status.HTTP_200_OK,
        )


class EnviarSolicitudServicioPublicaView(
    APIView
):
    """Recibe una solicitud pública y devuelve una referencia privada de seguimiento."""

    authentication_classes = []
    permission_classes = [
        AllowAny
    ]

    def post(
        self,
        request,
    ):
        """Crea solicitud y reserva pendiente de pago dentro de una transacción."""
        entrada_serializer = (
            EnviarSolicitudServicioSerializer(
                data=request.data
            )
        )

        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        datos = dict(
            entrada_serializer.validated_data
        )

        id_servicio = datos.pop(
            "id_servicio"
        )

        id_disponibilidad = datos.pop(
            "id_disponibilidad"
        )

        servicio = (
            Servicio.objects
            .select_related(
                "id_profesional"
            )
            .filter(
                id_servicio=id_servicio,
                estado_publicacion="PUBLICADO",
            )
            .first()
        )

        if servicio is None:
            return Response(
                {
                    "mensaje": (
                        "El servicio no existe o no "
                        "se encuentra publicado."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        ahora = timezone.now()

        ahora_local = (
            timezone.localtime(
                ahora
            )
        )

        with transaction.atomic():
            bloque = (
                Disponibilidad.objects
                .select_for_update()
                .filter(
                    id_disponibilidad=(
                        id_disponibilidad
                    )
                )
                .first()
            )

            if bloque is None:
                return Response(
                    {
                        "mensaje": (
                            "El bloque de "
                            "disponibilidad seleccionado "
                            "no existe."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )

            if (
                bloque.id_profesional_id
                != servicio.id_profesional_id
            ):
                return Response(
                    {
                        "mensaje": (
                            "El bloque seleccionado no "
                            "corresponde al profesional "
                            "del servicio."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            if (
                bloque.estado
                != "DISPONIBLE"
            ):
                return Response(
                    {
                        "mensaje": (
                            "El bloque seleccionado ya "
                            "no se encuentra disponible."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            reserva_activa_existente = (
                ReservaDisponibilidad.objects
                .filter(
                    id_disponibilidad=bloque,
                    estado__in=["PENDIENTE_PAGO", "ACTIVA"],
                )
                .exists()
            )

            if reserva_activa_existente:
                return Response(
                    {
                        "mensaje": (
                            "El bloque seleccionado ya "
                            "posee una reserva pendiente o activa."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            if (
                bloque.fecha
                < ahora_local.date()
            ):
                return Response(
                    {
                        "mensaje": (
                            "El bloque seleccionado "
                            "corresponde a una fecha "
                            "pasada."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            if (
                bloque.fecha
                == ahora_local.date()
                and bloque.hora_inicio
                <= ahora_local.time()
            ):
                return Response(
                    {
                        "mensaje": (
                            "El bloque seleccionado "
                            "ya comenzó y no puede "
                            "seleccionarse."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )

            rut = datos.get(
                "rut"
            )

            nombre_organizacion = datos[
                "nombre_organizacion"
            ]

            empresa = None

            if rut:
                empresa = (
                    EmpresaSolicitante.objects
                    .filter(
                        rut__iexact=rut,
                        estado="ACTIVA",
                    )
                    .order_by(
                        "id_empresa"
                    )
                    .first()
                )

            else:
                empresa = (
                    EmpresaSolicitante.objects
                    .filter(
                        nombre_organizacion__iexact=(
                            nombre_organizacion
                        ),
                        estado="ACTIVA",
                    )
                    .order_by(
                        "id_empresa"
                    )
                    .first()
                )

            if empresa is None:
                empresa = (
                    EmpresaSolicitante.objects
                    .create(
                        nombre_organizacion=(
                            nombre_organizacion
                        ),
                        rut=rut,
                        rubro=datos.get(
                            "rubro"
                        ),
                        sitio_web=datos.get(
                            "sitio_web"
                        ),
                        estado="ACTIVA",
                        fecha_registro=ahora,
                    )
                )

            correo_contacto = datos[
                "correo_contacto"
            ]

            contacto = (
                ContactoEmpresa.objects
                .filter(
                    id_empresa=empresa,
                    correo__iexact=(
                        correo_contacto
                    ),
                )
                .order_by(
                    "id_contacto"
                )
                .first()
            )

            if contacto is None:
                contacto = (
                    ContactoEmpresa.objects
                    .create(
                        id_empresa=empresa,
                        nombre=datos[
                            "nombre_contacto"
                        ],
                        cargo=datos.get(
                            "cargo_contacto"
                        ),
                        correo=(
                            correo_contacto
                        ),
                        telefono=datos.get(
                            "telefono_contacto"
                        ),
                        fecha_registro=ahora,
                    )
                )

            solicitud = (
                SolicitudServicio.objects
                .create(
                    id_empresa=empresa,
                    id_contacto=contacto,
                    id_servicio=servicio,
                    objetivo=datos[
                        "objetivo"
                    ],
                    descripcion_necesidad=(
                        datos[
                            "descripcion_necesidad"
                        ]
                    ),
                    modalidad=(
                        servicio.modalidad
                    ),
                    fecha_preferida=(
                        bloque.fecha
                    ),
                    # Campo legado: conserva una copia del precio publicado,
                    # jamas un presupuesto entregado por la organizacion.
                    referencia_presupuesto=servicio.referencia_precio,
                    urgencia=datos.get(
                        "urgencia"
                    ),
                    estado="RECIBIDA",
                    fecha_solicitud=ahora,
                    fecha_actualizacion=ahora,
                )
            )

            relaciones_competencias = (
                ServicioCompetencia.objects
                .filter(
                    id_servicio=servicio
                )
                .select_related(
                    "id_competencia"
                )
            )

            for relacion in (
                relaciones_competencias
            ):
                (
                    SolicitudCompetencia.objects
                    .create(
                        id_solicitud=solicitud,
                        id_competencia=(
                            relacion.id_competencia
                        ),
                    )
                )

            reserva = (
                ReservaDisponibilidad.objects
                .create(
                    id_disponibilidad=bloque,
                    id_solicitud=solicitud,
                    estado="PENDIENTE_PAGO",
                    fecha_reserva=ahora,
                    fecha_cambio=None,
                    motivo_cambio=None,
                )
            )

            EventoTrazabilidad.objects.create(
                entidad_tipo=(
                    "solicitud_servicio"
                ),
                entidad_id=(
                    solicitud.id_solicitud
                ),
                accion=(
                    "ENVIAR_SOLICITUD_SERVICIO"
                ),
                detalle_resumido=(
                    f"Solicitud "
                    f"{solicitud.id_solicitud} "
                    f"registrada desde el "
                    f"marketplace para el servicio "
                    f"{servicio.id_servicio}."
                )[:255],
                fecha_evento=ahora,
            )

            EventoTrazabilidad.objects.create(
                entidad_tipo=(
                    "reserva_disponibilidad"
                ),
                entidad_id=(
                    reserva.id_reserva
                ),
                accion=(
                    "SELECCIONAR_DISPONIBILIDAD"
                ),
                detalle_resumido=(
                    f"Bloque "
                    f"{bloque.id_disponibilidad} "
                    f"seleccionado por la solicitud "
                    f"{solicitud.id_solicitud}. "
                    f"La reserva permanece pendiente "
                    f"hasta la confirmación del pago."
                )[:255],
                fecha_evento=ahora,
            )

        solicitud = (
            SolicitudServicio.objects
            .select_related(
                "id_empresa",
                "id_contacto",
                "id_servicio",
            )
            .get(
                id_solicitud=(
                    solicitud.id_solicitud
                )
            )
        )

        serializer = (
            SolicitudServicioPublicaSerializer(
                solicitud
            )
        )

        return Response(
            {
                "mensaje": (
                    "Solicitud enviada correctamente "
                    "a Skilly. El horario seleccionado "
                    "quedó asociado a la solicitud y "
                    "será reservado una vez confirmado "
                    "el pago."
                ),
                "solicitud": serializer.data,
                "id_reserva": (
                    reserva.id_reserva
                ),
            },
            status=(
                status.HTTP_201_CREATED
            ),
        )
