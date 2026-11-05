from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import (
    SesionSkillyAuthentication,
)
from acceso.permissions import (
    EsAdministracionSkilly,
)
from backoffice.models import EventoTrazabilidad
from coordinacion.models import PrestacionServicio
from solicitudes.referencias import (
    leer_referencia_seguimiento,
)

from .models import (
    RecomendacionDesarrollo,
    Retroalimentacion,
)
from .serializers import (
    RegistrarRecomendacionDesarrolloSerializer,
    RegistrarRetroalimentacionSerializer,
    RecomendacionDesarrolloSerializer,
    RetroalimentacionAdministracionSerializer,
    RetroalimentacionSerializer,
)


class RetroalimentacionPrivadaEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(
        self,
        request,
        referencia,
    ):
        datos_referencia = (
            leer_referencia_seguimiento(
                referencia
            )
        )

        if datos_referencia is None:
            return Response(
                {
                    "mensaje": (
                        "La referencia de seguimiento "
                        "no es valida."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        prestacion = (
            PrestacionServicio.objects
            .select_related(
                "id_solicitud",
            )
            .filter(
                id_solicitud_id=(
                    datos_referencia[
                        "id_solicitud"
                    ]
                ),
                id_solicitud__id_contacto_id=(
                    datos_referencia[
                        "id_contacto"
                    ]
                ),
            )
            .order_by(
                "-id_prestacion"
            )
            .first()
        )

        if prestacion is None:
            return Response(
                {
                    "mensaje": (
                        "La prestacion solicitada "
                        "no existe o no corresponde "
                        "a esta empresa."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        feedback_habilitado = (
            prestacion.estado
            == "FINALIZADA"
        )

        return Response(
            {
                "prestacion": {
                    "id_prestacion": (
                        prestacion.id_prestacion
                    ),
                    "id_solicitud": (
                        prestacion.id_solicitud_id
                    ),
                    "estado": (
                        prestacion.estado
                    ),
                    "fecha_cierre": (
                        prestacion.fecha_cierre
                    ),
                },
                "feedback_habilitado": (
                    feedback_habilitado
                ),
                "caracter_privado": True,
                "mensaje_privacidad": (
                    "La retroalimentacion es "
                    "privada para Skilly y no "
                    "se publica como ranking ni "
                    "como calificacion publica "
                    "del profesional."
                ),
                "campos": {
                    "contenido": {
                        "tipo": "texto",
                        "requerido": True,
                    }
                },
            },
            status=status.HTTP_200_OK,
        )

    def post(
        self,
        request,
        referencia,
    ):
        datos_referencia = (
            leer_referencia_seguimiento(
                referencia
            )
        )

        if datos_referencia is None:
            return Response(
                {
                    "mensaje": (
                        "La referencia de seguimiento "
                        "no es valida."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        entrada_serializer = (
            RegistrarRetroalimentacionSerializer(
                data=request.data
            )
        )

        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        contenido = (
            entrada_serializer.validated_data[
                "contenido"
            ]
        )

        with transaction.atomic():
            prestacion = (
                PrestacionServicio.objects
                .select_for_update()
                .select_related(
                    "id_solicitud",
                )
                .filter(
                    id_solicitud_id=(
                        datos_referencia[
                            "id_solicitud"
                        ]
                    ),
                    id_solicitud__id_contacto_id=(
                        datos_referencia[
                            "id_contacto"
                        ]
                    ),
                )
                .order_by(
                    "-id_prestacion"
                )
                .first()
            )

            if prestacion is None:
                return Response(
                    {
                        "mensaje": (
                            "La prestacion solicitada "
                            "no existe o no corresponde "
                            "a esta empresa."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if (
                prestacion.estado
                != "FINALIZADA"
            ):
                return Response(
                    {
                        "mensaje": (
                            "La prestacion aun no se "
                            "encuentra habilitada para "
                            "registrar retroalimentacion."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            ahora = timezone.now()

            feedback = (
                Retroalimentacion.objects.create(
                    id_prestacion=prestacion,
                    id_contacto_id=(
                        datos_referencia[
                            "id_contacto"
                        ]
                    ),
                    contenido=contenido,
                    visibilidad="PRIVADA",
                    estado="REGISTRADA",
                    fecha_registro=ahora,
                )
            )

            EventoTrazabilidad.objects.create(
                id_usuario=None,
                entidad_tipo=(
                    "retroalimentacion"
                ),
                entidad_id=(
                    feedback.id_feedback
                ),
                accion=(
                    "REGISTRAR_"
                    "RETROALIMENTACION_PRIVADA"
                ),
                detalle_resumido=(
                    (
                        "Feedback privado registrado "
                        "para prestacion "
                        f"{prestacion.id_prestacion} "
                        "por contacto empresa "
                        f"{datos_referencia['id_contacto']}."
                    )[:255]
                ),
                fecha_evento=ahora,
            )

        return Response(
            {
                "mensaje": (
                    "Retroalimentacion privada "
                    "registrada correctamente."
                ),
                "retroalimentacion": (
                    RetroalimentacionSerializer(
                        feedback
                    ).data
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class RetroalimentacionesAdministracionView(
    APIView
):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(
        self,
        request,
    ):
        retroalimentaciones = (
            Retroalimentacion.objects
            .select_related(
                "id_prestacion",
                "id_prestacion__id_profesional",
                "id_contacto",
            )
            .filter(
                visibilidad="PRIVADA"
            )
            .order_by(
                "-fecha_registro",
                "-id_feedback",
            )
        )

        resultado = []

        for feedback in retroalimentaciones:
            resultado.append(
                {
                    "retroalimentacion": (
                        RetroalimentacionAdministracionSerializer(
                            feedback
                        ).data
                    ),
                    "prestacion": {
                        "id_prestacion": (
                            feedback.id_prestacion_id
                        ),
                        "estado": (
                            feedback.id_prestacion.estado
                        ),
                    },
                    "profesional": {
                        "id_profesional": (
                            feedback
                            .id_prestacion
                            .id_profesional_id
                        ),
                    },
                }
            )

        return Response(
            {
                "retroalimentaciones": resultado,
            },
            status=status.HTTP_200_OK,
        )


class GestionRetroalimentacionAdministracionView(
    APIView
):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(
        self,
        request,
        id_feedback,
    ):
        feedback = (
            Retroalimentacion.objects
            .select_related(
                "id_prestacion",
                "id_prestacion__id_profesional",
                "id_contacto",
            )
            .filter(
                id_feedback=id_feedback,
                visibilidad="PRIVADA",
            )
            .first()
        )

        if feedback is None:
            return Response(
                {
                    "mensaje": (
                        "La retroalimentacion privada "
                        "solicitada no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        recomendaciones = (
            RecomendacionDesarrollo.objects
            .select_related(
                "id_profesional",
                "id_usuario_skilly",
            )
            .filter(
                id_feedback=feedback
            )
            .order_by(
                "fecha_creacion",
                "id_recomendacion",
            )
        )

        return Response(
            {
                "retroalimentacion": (
                    RetroalimentacionAdministracionSerializer(
                        feedback
                    ).data
                ),
                "prestacion": {
                    "id_prestacion": (
                        feedback.id_prestacion_id
                    ),
                    "estado": (
                        feedback.id_prestacion.estado
                    ),
                },
                "profesional": {
                    "id_profesional": (
                        feedback
                        .id_prestacion
                        .id_profesional_id
                    ),
                },
                "recomendaciones": (
                    RecomendacionDesarrolloSerializer(
                        recomendaciones,
                        many=True,
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )

    def post(
        self,
        request,
        id_feedback,
    ):
        entrada_serializer = (
            RegistrarRecomendacionDesarrolloSerializer(
                data=request.data
            )
        )

        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        titulo = (
            entrada_serializer.validated_data[
                "titulo"
            ]
        )

        descripcion = (
            entrada_serializer.validated_data[
                "descripcion"
            ]
        )

        with transaction.atomic():
            feedback = (
                Retroalimentacion.objects
                .select_for_update()
                .select_related(
                    "id_prestacion",
                    "id_prestacion__id_profesional",
                )
                .filter(
                    id_feedback=id_feedback,
                    visibilidad="PRIVADA",
                )
                .first()
            )

            if feedback is None:
                return Response(
                    {
                        "mensaje": (
                            "La retroalimentacion privada "
                            "solicitada no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            ahora = timezone.now()

            recomendacion = (
                RecomendacionDesarrollo.objects.create(
                    id_profesional=(
                        feedback
                        .id_prestacion
                        .id_profesional
                    ),
                    id_feedback=feedback,
                    id_usuario_skilly=request.user,
                    titulo=titulo,
                    descripcion=descripcion,
                    estado=(
                        RecomendacionDesarrollo
                        .Estado
                        .REGISTRADA
                    ),
                    fecha_creacion=ahora,
                    fecha_comunicacion=None,
                )
            )

            EventoTrazabilidad.objects.create(
                id_usuario=request.user,
                entidad_tipo=(
                    "recomendacion_desarrollo"
                ),
                entidad_id=(
                    recomendacion.id_recomendacion
                ),
                accion=(
                    "REGISTRAR_"
                    "RECOMENDACION_DESARROLLO"
                ),
                detalle_resumido=(
                    (
                        "Recomendacion de desarrollo "
                        "registrada para profesional "
                        f"{recomendacion.id_profesional_id} "
                        "a partir del feedback "
                        f"{feedback.id_feedback}."
                    )[:255]
                ),
                fecha_evento=ahora,
            )

        return Response(
            {
                "mensaje": (
                    "Recomendacion de desarrollo "
                    "registrada correctamente."
                ),
                "recomendacion": (
                    RecomendacionDesarrolloSerializer(
                        recomendacion
                    ).data
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class ComunicarRecomendacionAdministracionView(
    APIView
):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def post(
        self,
        request,
        id_recomendacion,
    ):
        with transaction.atomic():
            recomendacion = (
                RecomendacionDesarrollo.objects
                .select_for_update(of=("self",))
                .select_related(
                    "id_profesional",
                    "id_feedback",
                    "id_usuario_skilly",
                )
                .filter(
                    id_recomendacion=(
                        id_recomendacion
                    )
                )
                .first()
            )

            if recomendacion is None:
                return Response(
                    {
                        "mensaje": (
                            "La recomendacion de "
                            "desarrollo no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if (
                recomendacion.estado
                ==
                RecomendacionDesarrollo
                .Estado
                .COMUNICADA
            ):
                return Response(
                    {
                        "mensaje": (
                            "La recomendacion ya se "
                            "encuentra comunicada."
                        ),
                        "recomendacion": (
                            RecomendacionDesarrolloSerializer(
                                recomendacion
                            ).data
                        ),
                    },
                    status=status.HTTP_200_OK,
                )

            if (
                recomendacion.estado
                !=
                RecomendacionDesarrollo
                .Estado
                .REGISTRADA
            ):
                return Response(
                    {
                        "mensaje": (
                            "La recomendacion no se "
                            "encuentra en un estado "
                            "que permita comunicarla."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            ahora = timezone.now()

            recomendacion.estado = (
                RecomendacionDesarrollo
                .Estado
                .COMUNICADA
            )

            recomendacion.fecha_comunicacion = (
                ahora
            )

            recomendacion.save(
                update_fields=[
                    "estado",
                    "fecha_comunicacion",
                ]
            )

            EventoTrazabilidad.objects.create(
                id_usuario=request.user,
                entidad_tipo=(
                    "recomendacion_desarrollo"
                ),
                entidad_id=(
                    recomendacion.id_recomendacion
                ),
                accion=(
                    "COMUNICAR_"
                    "RECOMENDACION_DESARROLLO"
                ),
                detalle_resumido=(
                    (
                        "Recomendacion de desarrollo "
                        f"{recomendacion.id_recomendacion} "
                        "comunicada al profesional "
                        f"{recomendacion.id_profesional_id}."
                    )[:255]
                ),
                fecha_evento=ahora,
            )

        return Response(
            {
                "mensaje": (
                    "Recomendacion comunicada "
                    "correctamente."
                ),
                "recomendacion": (
                    RecomendacionDesarrolloSerializer(
                        recomendacion
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )
