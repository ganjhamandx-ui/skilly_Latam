"""Implementa catálogo, propuestas y administración del marketplace."""

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import (
    EsAdministracionSkilly,
    EsProfesional,
)
from backoffice.services import registrar_evento_trazabilidad
from profesionales.models import (
    Competencia,
    Profesional,
)
from solicitudes.models import Disponibilidad
from .models import (
    CategoriaServicio,
    RevisionServicio,
    Servicio,
    ServicioCompetencia,
)
from .serializers import (
    ActualizarPropuestaServicioSerializer,
    CrearPropuestaServicioSerializer,
    RevisarPropuestaServicioSerializer,
    RevisionServicioAdministracionSerializer,
    ServicioMarketplaceSerializer,
    ServicioProfesionalSerializer,
    VersionPropuestaServicioSerializer,
    VersionRevisadaProfesionalSerializer,
    extraer_version_propuesta_revision,
)


def obtener_profesional(usuario):
    """Devuelve el primer perfil del usuario recibido, o None si todavía no existe.

    No comprueba aquí el estado de validación ni sustituye los permisos de la vista.
    """
    return Profesional.objects.filter(
        id_usuario=usuario
    ).first()


def obtener_competencias(ids_competencias):
    """Resuelve competencias y detecta identificadores inexistentes.

    Args:
        ids_competencias (list[int]): Identificadores previamente validados por DRF.

    Returns:
        tuple[list[Competencia], list[int]]: Modelos por id ascendente y ids faltantes
        en el orden de entrada. No filtra el estado de las competencias.
    """
    competencias = list(
        Competencia.objects.filter(
            id_competencia__in=ids_competencias
        ).order_by(
            "id_competencia"
        )
    )
    ids_encontrados = {
        competencia.id_competencia
        for competencia in competencias
    }
    ids_faltantes = [
        id_competencia
        for id_competencia in ids_competencias
        if id_competencia not in ids_encontrados
    ]
    return competencias, ids_faltantes


class MarketplaceServiciosPublicosView(
    APIView
):
    """Expone tarjetas de servicios publicados con filtros de catálogo y disponibilidad."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """Busca servicios publicados y devuelve tarjetas resumidas del catálogo.

        Args:
            request (Request): Petición pública con q, id_categoria, id_competencia,
                modalidad, fecha y pareja hora_inicio/hora_fin opcionales.

        Returns:
            Response: HTTP 200 con cantidad y servicios por publicación e id descendentes;
            HTTP 400 por ids no convertibles, filtros temporales inválidos o franja incoherente.

        Raises:
            ValueError: Si parse_date o parse_time recibe una fecha/hora bien formada
                pero imposible; esas excepciones no se capturan en este método.

        Note:
            La búsqueda textual cubre nombre, descripción y competencias. El filtro horario
            exige bloques que contengan toda la franja y excluye reservas pendientes/activas.
            La selección final vuelve a validar el inicio; la tarjeta no constituye reserva.
        """
        servicios = (
            Servicio.objects
            .filter(
                estado_publicacion="PUBLICADO"
            )
            .select_related(
                "id_profesional",
                "id_categoria",
            )
            .order_by(
                "-fecha_publicacion",
                "-id_servicio",
            )
        )
        termino = str(
            request.query_params.get(
                "q",
                "",
            )
        ).strip()
        if termino:
            servicios_competencia = (
                ServicioCompetencia.objects
                .filter(
                    id_competencia__nombre__icontains=(
                        termino
                    )
                )
                .values_list(
                    "id_servicio_id",
                    flat=True,
                )
            )
            servicios = servicios.filter(
                Q(
                    nombre__icontains=termino
                )
                | Q(
                    descripcion__icontains=termino
                )
                | Q(
                    id_servicio__in=(
                        servicios_competencia
                    )
                )
            )
        id_categoria = (
            request.query_params.get(
                "id_categoria"
            )
        )
        if id_categoria not in [
            None,
            "",
        ]:
            try:
                id_categoria = int(
                    id_categoria
                )
            except (
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "id_categoria": [
                            (
                                "Debe indicar una "
                                "categoría válida."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
            servicios = servicios.filter(
                id_categoria_id=id_categoria
            )
        id_competencia = (
            request.query_params.get(
                "id_competencia"
            )
        )
        if id_competencia not in [
            None,
            "",
        ]:
            try:
                id_competencia = int(
                    id_competencia
                )
            except (
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "id_competencia": [
                            (
                                "Debe indicar una "
                                "competencia válida."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
            servicios_con_competencia = (
                ServicioCompetencia.objects
                .filter(
                    id_competencia_id=(
                        id_competencia
                    )
                )
                .values_list(
                    "id_servicio_id",
                    flat=True,
                )
            )
            servicios = servicios.filter(
                id_servicio__in=(
                    servicios_con_competencia
                )
            )
        modalidad = str(
            request.query_params.get(
                "modalidad",
                "",
            )
        ).strip()
        if modalidad:
            servicios = servicios.filter(
                modalidad__iexact=modalidad
            )
        fecha_texto = str(
            request.query_params.get(
                "fecha",
                "",
            )
        ).strip()
        hora_inicio_texto = str(
            request.query_params.get(
                "hora_inicio",
                "",
            )
        ).strip()
        hora_fin_texto = str(
            request.query_params.get(
                "hora_fin",
                "",
            )
        ).strip()
        if bool(
            hora_inicio_texto
        ) != bool(
            hora_fin_texto
        ):
            return Response(
                {
                    "disponibilidad": [
                        (
                            "Para filtrar por horario "
                            "debe indicar hora_inicio "
                            "y hora_fin."
                        )
                    ]
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )
        fecha = None
        hora_inicio = None
        hora_fin = None
        if fecha_texto:
            fecha = parse_date(
                fecha_texto
            )
            if fecha is None:
                return Response(
                    {
                        "fecha": [
                            (
                                "La fecha debe tener "
                                "formato YYYY-MM-DD."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
            if fecha < timezone.localdate():
                return Response(
                    {
                        "fecha": [
                            (
                                "La fecha de "
                                "disponibilidad no puede "
                                "estar en el pasado."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
        if (
            hora_inicio_texto
            and hora_fin_texto
        ):
            hora_inicio = parse_time(
                hora_inicio_texto
            )
            hora_fin = parse_time(
                hora_fin_texto
            )
            if (
                hora_inicio is None
                or hora_fin is None
            ):
                return Response(
                    {
                        "disponibilidad": [
                            (
                                "Las horas deben tener "
                                "un formato válido, por "
                                "ejemplo 15:00 y 18:00."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
            if hora_inicio >= hora_fin:
                return Response(
                    {
                        "hora_fin": [
                            (
                                "La hora de término "
                                "debe ser posterior a "
                                "la hora de inicio."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
            if (
                fecha
                == timezone.localdate()
                and hora_inicio
                <= timezone.localtime().time()
            ):
                return Response(
                    {
                        "hora_inicio": [
                            (
                                "La franja solicitada "
                                "ya comenzó o se "
                                "encuentra en el pasado."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
        filtrar_disponibilidad = bool(
            fecha is not None
            or (
                hora_inicio is not None
                and hora_fin is not None
            )
        )
        if filtrar_disponibilidad:
            from solicitudes.models import ReservaDisponibilidad
            bloques = (
                Disponibilidad.objects
                .filter(
                    estado="DISPONIBLE",
                    fecha__gte=(
                        timezone.localdate()
                    ),
                )
            )
            bloques = bloques.exclude(
                id_disponibilidad__in=(
                    ReservaDisponibilidad.objects
                    .filter(estado__in=["PENDIENTE_PAGO", "ACTIVA"])
                    .values_list("id_disponibilidad_id", flat=True)
                )
            )
            if fecha is not None:
                bloques = bloques.filter(
                    fecha=fecha
                )
            if (
                hora_inicio is not None
                and hora_fin is not None
            ):
                bloques = bloques.filter(
                    hora_inicio__lte=(
                        hora_inicio
                    ),
                    hora_fin__gte=(
                        hora_fin
                    ),
                )
            ids_profesionales = (
                bloques.values_list(
                    "id_profesional_id",
                    flat=True,
                )
            )
            servicios = servicios.filter(
                id_profesional_id__in=(
                    ids_profesionales
                )
            )
        serializer = (
            ServicioMarketplaceSerializer(
                servicios,
                many=True,
            )
        )
        return Response(
            {
                "cantidad": len(
                    serializer.data
                ),
                "servicios": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class DetalleServicioMarketplaceView(
    APIView
):
    """Expone la ficha pública solo si el servicio permanece PUBLICADO."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(
        self,
        request,
        id_servicio,
    ):
        """Consulta una oferta publicada con profesional, competencias y disponibilidad.

        Args:
            request (Request): Petición pública sin sesión obligatoria.
            id_servicio (int): Identificador del servicio solicitado.

        Returns:
            Response: HTTP 200 con ficha completa o 404 si falta el servicio publicado.
        """
        servicio = (
            Servicio.objects
            .select_related(
                "id_profesional",
                "id_categoria",
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
                        "se encuentra publicado en "
                        "el marketplace."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )
        serializer = (
            ServicioMarketplaceSerializer(
                servicio
            )
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")


class MisServiciosProfesionalesView(
    APIView
):
    """Consulta ofertas propias y permite crear borradores a profesionales aprobados."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsProfesional
    ]

    def get(self, request):
        """Lista todos los estados de ofertas del perfil autenticado.

        Args:
            request (Request): Sesión con permiso profesional.

        Returns:
            Response: HTTP 200 con servicios por actualización e id descendentes;
            HTTP 404 si falta el perfil profesional.
        """
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
        servicios = (
            Servicio.objects
            .filter(
                id_profesional=profesional
            )
            .select_related(
                "id_categoria"
            )
            .order_by(
                "-fecha_actualizacion",
                "-id_servicio",
            )
        )
        serializer = (
            ServicioProfesionalSerializer(
                servicios,
                many=True,
            )
        )
        return Response(
            {
                "servicios": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """Crea un borrador con categoría y competencias existentes.

        Args:
            request (Request): Sesión profesional con CSRF, nombre, descripción, categoría
                y campos comerciales opcionales; el perfil debe estar APROBADO.

        Returns:
            Response: HTTP 201 con BORRADOR y trazabilidad, 400 por entrada o relaciones
            inexistentes, 404 si falta perfil y 409 si no está aprobado.

        Raises:
            Servicio.DoesNotExist: Si desaparece antes de recargar la respuesta.
        """
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
        if (
            profesional.estado_validacion
            != "APROBADO"
        ):
            return Response(
                {
                    "mensaje": (
                        "El profesional debe "
                        "encontrarse validado para "
                        "proponer servicios."
                    )
                },
                status=(
                    status.HTTP_409_CONFLICT
                ),
            )
        entrada_serializer = (
            CrearPropuestaServicioSerializer(
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
        id_categoria = datos.pop(
            "id_categoria"
        )
        ids_competencias = datos.pop(
            "ids_competencias",
            [],
        )
        categoria = (
            CategoriaServicio.objects
            .filter(
                id_categoria=id_categoria
            )
            .first()
        )
        if categoria is None:
            return Response(
                {
                    "id_categoria": [
                        (
                            "La categoría indicada "
                            "no existe."
                        )
                    ]
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )
        (
            competencias,
            ids_faltantes,
        ) = obtener_competencias(
            ids_competencias
        )
        if ids_faltantes:
            return Response(
                {
                    "ids_competencias": [
                        (
                            "No existen las siguientes "
                            "competencias: "
                            + ", ".join(
                                str(valor)
                                for valor
                                in ids_faltantes
                            )
                            + "."
                        )
                    ]
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )
        with transaction.atomic():
            servicio = Servicio.objects.create(
                id_profesional=profesional,
                id_categoria=categoria,
                nombre=datos["nombre"],
                descripcion=datos[
                    "descripcion"
                ],
                modalidad=datos.get(
                    "modalidad"
                ),
                alcance=datos.get(
                    "alcance"
                ),
                referencia_precio=datos.get(
                    "referencia_precio"
                ),
                estado_publicacion="BORRADOR",
                fecha_publicacion=None,
                fecha_actualizacion=(
                    timezone.now()
                ),
            )
            for competencia in competencias:
                (
                    ServicioCompetencia.objects
                    .create(
                        id_servicio=servicio,
                        id_competencia=(
                            competencia
                        ),
                    )
                )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="servicio",
                entidad_id=(
                    servicio.id_servicio
                ),
                accion=(
                    "CREAR_PROPUESTA_SERVICIO"
                ),
                detalle_resumido=(
                    f"El profesional creó la "
                    f"propuesta del servicio "
                    f"{servicio.id_servicio}."
                )[:255],
            )
        servicio = (
            Servicio.objects
            .select_related(
                "id_categoria"
            )
            .get(
                id_servicio=(
                    servicio.id_servicio
                )
            )
        )
        serializer = (
            ServicioProfesionalSerializer(
                servicio
            )
        )
        return Response(
            {
                "mensaje": (
                    "Propuesta de servicio creada "
                    "correctamente."
                ),
                "servicio": serializer.data,
            },
            status=(
                status.HTTP_201_CREATED
            ),
        )


@method_decorator(csrf_protect, name="dispatch")


class DetalleServicioProfesionalPropioView(
    APIView
):
    """Consulta la oferta propia y permite correcciones antes de la revisión final."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsProfesional
    ]

    def get(
        self,
        request,
        id_servicio,
    ):
        """Obtiene la oferta propia y el historial de rechazos comerciales.

        Args:
            request (Request): Sesión con permiso profesional.
            id_servicio (int): Servicio que debe pertenecer a su perfil.

        Returns:
            Response: HTTP 200 con oferta e historial de rechazos/cierre sin acuerdo;
            HTTP 404 si no existe perfil o servicio propio.
        """
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
        servicio = (
            Servicio.objects
            .select_related(
                "id_categoria"
            )
            .filter(
                id_servicio=id_servicio,
                id_profesional=profesional,
            )
            .first()
        )
        if servicio is None:
            return Response(
                {
                    "mensaje": (
                        "El servicio no existe o no "
                        "pertenece al profesional "
                        "autenticado."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )
        serializer = (
            ServicioProfesionalSerializer(
                servicio
            )
        )
        datos = dict(serializer.data)
        revisiones_comerciales = (RevisionServicio.objects.filter(
            id_servicio=servicio,
            estado_revision__in=["RECHAZO_COMERCIAL", "CIERRE_SIN_ACUERDO"],
        ).order_by("numero_version", "id_revision_servicio"))
        datos["historial_rechazos_comerciales"] = []
        for rev in revisiones_comerciales:
            import json
            try:
                info = json.loads(rev.contenido_revisado or "{}")
            except (ValueError, TypeError):
                info = {}
            datos["historial_rechazos_comerciales"].append({
                "ronda": info.get("ronda"),
                "motivo_categoria": info.get("motivo_etiqueta", "Otro"),
                "observacion": rev.observacion or "",
                "estado": rev.estado_revision,
                "fecha": rev.fecha_revision,
            })
        return Response(datos, status=status.HTTP_200_OK)

    def patch(
        self,
        request,
        id_servicio,
    ):
        """Actualiza un borrador o propuesta devuelta para corrección bajo bloqueo.

        Args:
            request (Request): Sesión profesional con CSRF y al menos un campo editable.
            id_servicio (int): Servicio propio BORRADOR o CORRECCION_SOLICITADA.

        Returns:
            Response: HTTP 200 con oferta actualizada, 400 por campos o relaciones inválidos,
            404 por perfil/servicio propio ausente y 409 por estado incompatible. Si se envían
            competencias, reemplaza el conjunto completo, incluso para dejarlo vacío.

        Raises:
            Servicio.DoesNotExist: Si desaparece antes de recargar la respuesta.
        """
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
        entrada_serializer = (
            ActualizarPropuestaServicioSerializer(
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
        categoria = None
        if "id_categoria" in datos:
            id_categoria = datos.pop(
                "id_categoria"
            )
            categoria = (
                CategoriaServicio.objects
                .filter(
                    id_categoria=id_categoria
                )
                .first()
            )
            if categoria is None:
                return Response(
                    {
                        "id_categoria": [
                            (
                                "La categoría indicada "
                                "no existe."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
        competencias = None
        if "ids_competencias" in datos:
            ids_competencias = datos.pop(
                "ids_competencias"
            )
            (
                competencias,
                ids_faltantes,
            ) = obtener_competencias(
                ids_competencias
            )
            if ids_faltantes:
                return Response(
                    {
                        "ids_competencias": [
                            (
                                "No existen las "
                                "siguientes competencias: "
                                + ", ".join(
                                    str(valor)
                                    for valor
                                    in ids_faltantes
                                )
                                + "."
                            )
                        ]
                    },
                    status=(
                        status.HTTP_400_BAD_REQUEST
                    ),
                )
        with transaction.atomic():
            servicio = (
                Servicio.objects
                .select_for_update()
                .select_related(
                    "id_categoria"
                )
                .filter(
                    id_servicio=id_servicio,
                    id_profesional=profesional,
                )
                .first()
            )
            if servicio is None:
                return Response(
                    {
                        "mensaje": (
                            "El servicio no existe o "
                            "no pertenece al profesional "
                            "autenticado."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )
            if (
                servicio.estado_publicacion
                not in [
                    "BORRADOR",
                    "CORRECCION_SOLICITADA",
                ]
            ):
                return Response(
                    {
                        "mensaje": (
                            "El servicio no se "
                            "encuentra habilitado para "
                            "corrección."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            campos_actualizados = []
            for campo, valor in datos.items():
                setattr(
                    servicio,
                    campo,
                    valor,
                )
                campos_actualizados.append(
                    campo
                )
            if categoria is not None:
                servicio.id_categoria = (
                    categoria
                )
                campos_actualizados.append(
                    "id_categoria"
                )
            if competencias is not None:
                (
                    ServicioCompetencia.objects
                    .filter(
                        id_servicio=servicio
                    )
                    .delete()
                )
                for competencia in competencias:
                    (
                        ServicioCompetencia.objects
                        .create(
                            id_servicio=servicio,
                            id_competencia=(
                                competencia
                            ),
                        )
                    )
            servicio.fecha_actualizacion = (
                timezone.now()
            )
            campos_actualizados.append(
                "fecha_actualizacion"
            )
            servicio.save(
                update_fields=(
                    campos_actualizados
                )
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="servicio",
                entidad_id=(
                    servicio.id_servicio
                ),
                accion=(
                    "ACTUALIZAR_PROPUESTA_SERVICIO"
                ),
                detalle_resumido=(
                    f"El profesional actualizó la "
                    f"propuesta del servicio "
                    f"{servicio.id_servicio}."
                )[:255],
            )
        servicio = (
            Servicio.objects
            .select_related(
                "id_categoria"
            )
            .get(
                id_servicio=(
                    servicio.id_servicio
                )
            )
        )
        serializer = (
            ServicioProfesionalSerializer(
                servicio
            )
        )
        return Response(
            {
                "mensaje": (
                    "Propuesta actualizada "
                    "correctamente."
                ),
                "servicio": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")


class EnviarServicioRevisionProfesionalView(
    APIView
):
    """Envía propuestas propias a revisión administrativa conservando su contenido."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsProfesional
    ]

    def post(
        self,
        request,
        id_servicio,
    ):
        """Pasa un borrador o corrección solicitada a EN_REVISION.

        Args:
            request (Request): Sesión profesional con CSRF; no requiere contenido adicional.
            id_servicio (int): Servicio propio que se bloqueará durante la transición.

        Returns:
            Response: HTTP 200 con oferta y trazabilidad; 404 por perfil/servicio ausente
            y 409 si el estado no permite enviar. No crea todavía una RevisionServicio.
        """
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
            servicio = (
                Servicio.objects
                .select_for_update()
                .select_related(
                    "id_categoria"
                )
                .filter(
                    id_servicio=id_servicio,
                    id_profesional=profesional,
                )
                .first()
            )
            if servicio is None:
                return Response(
                    {
                        "mensaje": (
                            "El servicio no existe o "
                            "no pertenece al profesional "
                            "autenticado."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )
            if (
                servicio.estado_publicacion
                not in [
                    "BORRADOR",
                    "CORRECCION_SOLICITADA",
                ]
            ):
                return Response(
                    {
                        "mensaje": (
                            "El servicio no puede "
                            "enviarse a revisión desde "
                            "su estado actual."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            servicio.estado_publicacion = (
                "EN_REVISION"
            )
            servicio.fecha_actualizacion = (
                timezone.now()
            )
            servicio.save(
                update_fields=[
                    "estado_publicacion",
                    "fecha_actualizacion",
                ]
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="servicio",
                entidad_id=(
                    servicio.id_servicio
                ),
                accion=(
                    "ENVIAR_PROPUESTA_REVISION"
                ),
                detalle_resumido=(
                    f"Servicio "
                    f"{servicio.id_servicio} "
                    f"enviado a revisión de Skilly."
                )[:255],
            )
        serializer = (
            ServicioProfesionalSerializer(
                servicio
            )
        )
        return Response(
            {
                "mensaje": (
                    "Propuesta enviada a revisión "
                    "correctamente."
                ),
                "servicio": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")


class VersionRevisadaProfesionalView(
    APIView
):
    """Consulta la última revisión y aplica su versión final tras el visto bueno del propietario."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsProfesional
    ]

    def get(
        self,
        request,
        id_servicio,
    ):
        """Consulta la revisión de mayor versión del servicio propio.

        Args:
            request (Request): Sesión con permiso profesional.
            id_servicio (int): Servicio del perfil autenticado.

        Returns:
            Response: HTTP 200 con revisión, propuesta estructurada y oferta actual;
            HTTP 404 si falta perfil, servicio propio o revisión.
        """
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
        servicio = (
            Servicio.objects
            .filter(
                id_servicio=id_servicio,
                id_profesional=profesional,
            )
            .first()
        )
        if servicio is None:
            return Response(
                {
                    "mensaje": (
                        "El servicio no existe o no "
                        "pertenece al profesional "
                        "autenticado."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )
        revision = (
            RevisionServicio.objects
            .select_related(
                "id_servicio"
            )
            .filter(
                id_servicio=servicio
            )
            .order_by(
                "-numero_version",
                "-fecha_revision",
                "-id_revision_servicio",
            )
            .first()
        )
        if revision is None:
            return Response(
                {
                    "mensaje": (
                        "No existe una versión "
                        "revisada para este servicio."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )
        serializer = (
            VersionRevisadaProfesionalSerializer(
                revision
            )
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(
        self,
        request,
        id_servicio,
    ):
        """Aplica la versión comercial aprobada sin publicarla todavía.

        Args:
            request (Request): Sesión profesional con CSRF; aprueba la última versión persistida.
            id_servicio (int): Servicio propio PEND_APROBACION_PROFESIONAL.

        Returns:
            Response: HTTP 200 con revisión APROBADA y servicio APROBADA_PARA_PUBLICAR;
            404 si falta perfil, servicio o revisión; 409 si el estado, contenido estructurado
            o relaciones de la versión ya no son válidos.

        Raises:
            RevisionServicio.DoesNotExist: Si desaparece antes de recargar la respuesta.

        Note:
            Bloquea servicio y revisión, revalida la propuesta y sustituye campos comerciales
            y competencias en una transacción. No toma una versión nueva del cuerpo HTTP.
        """
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
            servicio = (
                Servicio.objects
                .select_for_update()
                .filter(
                    id_servicio=id_servicio,
                    id_profesional=profesional,
                )
                .first()
            )
            if servicio is None:
                return Response(
                    {
                        "mensaje": (
                            "El servicio no existe o "
                            "no pertenece al profesional "
                            "autenticado."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )
            if (
                servicio.estado_publicacion
                != "PEND_APROBACION_PROFESIONAL"
            ):
                return Response(
                    {
                        "mensaje": (
                            "El servicio no se encuentra "
                            "pendiente de aprobación del "
                            "profesional."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            revision = (
                RevisionServicio.objects
                .select_for_update()
                .filter(
                    id_servicio=servicio
                )
                .order_by(
                    "-numero_version",
                    "-fecha_revision",
                    "-id_revision_servicio",
                )
                .first()
            )
            if revision is None:
                return Response(
                    {
                        "mensaje": (
                            "No existe una versión "
                            "revisada para aprobar."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )
            if (
                revision.estado_revision
                != "PEND_APROBACION_PROFESIONAL"
            ):
                return Response(
                    {
                        "mensaje": (
                            "La versión revisada no se "
                            "encuentra pendiente de "
                            "aprobación del profesional."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            version_propuesta = (
                extraer_version_propuesta_revision(
                    revision.contenido_revisado
                )
            )
            if version_propuesta is None:
                return Response(
                    {
                        "mensaje": (
                            "La revisión pendiente no "
                            "contiene una versión "
                            "estructurada válida de "
                            "Skilly y no puede aprobarse."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            propuesta_serializer = (
                VersionPropuestaServicioSerializer(
                    data=version_propuesta
                )
            )
            if not propuesta_serializer.is_valid():
                return Response(
                    {
                        "mensaje": (
                            "La versión propuesta por "
                            "Skilly contiene datos que "
                            "ya no son válidos."
                        ),
                        "errores": (
                            propuesta_serializer.errors
                        ),
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            datos_propuesta = dict(
                propuesta_serializer.validated_data
            )
            id_categoria = (
                datos_propuesta.pop(
                    "id_categoria"
                )
            )
            ids_competencias = (
                datos_propuesta.pop(
                    "ids_competencias",
                    [],
                )
            )
            categoria = (
                CategoriaServicio.objects
                .filter(
                    id_categoria=id_categoria
                )
                .first()
            )
            if categoria is None:
                return Response(
                    {
                        "mensaje": (
                            "La categoría incluida en "
                            "la versión de Skilly ya "
                            "no existe."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            (
                competencias,
                ids_faltantes,
            ) = obtener_competencias(
                ids_competencias
            )
            if ids_faltantes:
                return Response(
                    {
                        "mensaje": (
                            "Una o más competencias de "
                            "la versión propuesta por "
                            "Skilly ya no existen."
                        ),
                        "ids_competencias": (
                            ids_faltantes
                        ),
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            ahora = timezone.now()
            servicio.nombre = (
                datos_propuesta["nombre"]
            )
            servicio.descripcion = (
                datos_propuesta["descripcion"]
            )
            servicio.modalidad = (
                datos_propuesta.get(
                    "modalidad"
                )
            )
            servicio.alcance = (
                datos_propuesta.get(
                    "alcance"
                )
            )
            servicio.referencia_precio = (
                datos_propuesta[
                    "referencia_precio"
                ]
            )
            servicio.id_categoria = (
                categoria
            )
            (
                ServicioCompetencia.objects
                .filter(
                    id_servicio=servicio
                )
                .delete()
            )
            for competencia in competencias:
                (
                    ServicioCompetencia.objects
                    .create(
                        id_servicio=servicio,
                        id_competencia=(
                            competencia
                        ),
                    )
                )
            servicio.estado_publicacion = (
                "APROBADA_PARA_PUBLICAR"
            )
            servicio.fecha_actualizacion = (
                ahora
            )
            servicio.save(
                update_fields=[
                    "nombre",
                    "descripcion",
                    "modalidad",
                    "alcance",
                    "referencia_precio",
                    "id_categoria",
                    "estado_publicacion",
                    "fecha_actualizacion",
                ]
            )
            revision.estado_revision = (
                "APROBADA"
            )
            (
                revision
                .fecha_aprobacion_profesional
            ) = ahora
            revision.save(
                update_fields=[
                    "estado_revision",
                    (
                        "fecha_aprobacion_"
                        "profesional"
                    ),
                ]
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo=(
                    "revision_servicio"
                ),
                entidad_id=(
                    revision
                    .id_revision_servicio
                ),
                accion=(
                    "APROBAR_VERSION_SERVICIO"
                ),
                detalle_resumido=(
                    f"El profesional aprobó la "
                    f"versión "
                    f"{revision.numero_version} "
                    f"del servicio "
                    f"{servicio.id_servicio}. "
                    f"La versión propuesta por "
                    f"Skilly fue aplicada al "
                    f"servicio."
                )[:255],
            )
        revision = (
            RevisionServicio.objects
            .select_related(
                "id_servicio"
            )
            .get(
                id_revision_servicio=(
                    revision.id_revision_servicio
                )
            )
        )
        serializer = (
            VersionRevisadaProfesionalSerializer(
                revision
            )
        )
        return Response(
            {
                "mensaje": (
                    "Versión revisada aprobada "
                    "correctamente. Los cambios "
                    "propuestos por Skilly fueron "
                    "aplicados y el servicio quedó "
                    "habilitado para publicación."
                ),
                "revision": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")


class PublicarServicioProfesionalView(
    APIView
):
    """Publica una oferta propia únicamente tras la aprobación de su última revisión."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsProfesional
    ]

    def post(
        self,
        request,
        id_servicio,
    ):
        """Hace visible la oferta aprobada y registra la fecha de publicación.

        Args:
            request (Request): Sesión profesional con CSRF válido.
            id_servicio (int): Servicio propio APROBADA_PARA_PUBLICAR.

        Returns:
            Response: HTTP 200 con servicio PUBLICADO; 404 por perfil o servicio propio
            ausente y 409 si falta estado habilitante o revisión APROBADA con fecha de visto bueno.
            Repetir la publicación sobre PUBLICADO devuelve conflicto.
        """
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
            servicio = (
                Servicio.objects
                .select_for_update()
                .select_related(
                    "id_categoria"
                )
                .filter(
                    id_servicio=id_servicio,
                    id_profesional=profesional,
                )
                .first()
            )
            if servicio is None:
                return Response(
                    {
                        "mensaje": (
                            "El servicio no existe o "
                            "no pertenece al profesional "
                            "autenticado."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )
            if (
                servicio.estado_publicacion
                != "APROBADA_PARA_PUBLICAR"
            ):
                return Response(
                    {
                        "mensaje": (
                            "El servicio todavía no "
                            "cuenta con la aprobación "
                            "necesaria para publicarse."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            revision = (
                RevisionServicio.objects
                .filter(
                    id_servicio=servicio
                )
                .order_by(
                    "-numero_version",
                    "-fecha_revision",
                    "-id_revision_servicio",
                )
                .first()
            )
            if (
                revision is None
                or revision.estado_revision
                != "APROBADA"
                or (
                    revision
                    .fecha_aprobacion_profesional
                    is None
                )
            ):
                return Response(
                    {
                        "mensaje": (
                            "La última versión revisada "
                            "no posee el visto bueno "
                            "del profesional."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            ahora = timezone.now()
            servicio.estado_publicacion = (
                "PUBLICADO"
            )
            servicio.fecha_publicacion = (
                ahora
            )
            servicio.fecha_actualizacion = (
                ahora
            )
            servicio.save(
                update_fields=[
                    "estado_publicacion",
                    "fecha_publicacion",
                    "fecha_actualizacion",
                ]
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="servicio",
                entidad_id=(
                    servicio.id_servicio
                ),
                accion=(
                    "PUBLICAR_SERVICIO"
                ),
                detalle_resumido=(
                    f"Servicio "
                    f"{servicio.id_servicio} "
                    f"publicado después de la "
                    f"revisión de Skilly y "
                    f"aprobación profesional."
                )[:255],
            )
        serializer = (
            ServicioProfesionalSerializer(
                servicio
            )
        )
        return Response(
            {
                "mensaje": (
                    "Servicio publicado "
                    "correctamente."
                ),
                "servicio": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class RevisionesServicioAdministracionView(
    APIView
):
    """Consulta el historial general de revisiones con permiso administrativo."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        """Lista revisiones por fecha e id descendentes, sin filtrar estado.

        Args:
            request (Request): Sesión administrativa activa.

        Returns:
            Response: HTTP 200 con revisiones y relaciones actuales del servicio.
        """
        revisiones = (
            RevisionServicio.objects
            .select_related(
                "id_servicio",
                (
                    "id_servicio__"
                    "id_profesional"
                ),
                (
                    "id_servicio__"
                    "id_categoria"
                ),
                "id_usuario_skilly",
            )
            .order_by(
                "-fecha_revision",
                "-id_revision_servicio",
            )
        )
        serializer = (
            RevisionServicioAdministracionSerializer(
                revisiones,
                many=True,
            )
        )
        return Response(
            {
                "revisiones": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")


class RevisarServicioAdministracionView(
    APIView
):
    """Versiona correcciones o condiciones finales sin publicarlas ni aplicarlas aún."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsAdministracionSkilly
    ]

    def post(
        self,
        request,
        id_servicio,
    ):
        """Registra la revisión administrativa y el siguiente estado de la oferta.

        Args:
            request (Request): Sesión administrativa con CSRF, decisión, observación y
                versión final estructurada cuando corresponde aprobar la revisión.
            id_servicio (int): Oferta que debe encontrarse EN_REVISION.

        Returns:
            Response: HTTP 201 con nueva revisión y estado CORRECCION_SOLICITADA o
            PEND_APROBACION_PROFESIONAL; 400 por datos, relaciones o justificación inválidos;
            404 si falta servicio y 409 por estado o reconsideración agotada.

        Raises:
            RevisionServicio.DoesNotExist: Si desaparece antes de recargar la respuesta.

        Note:
            Bloquea el servicio para numerar versiones. Tras un rechazo comercial solo
            admite una segunda versión final, sin otra ronda de correcciones. Cambiar tarifa
            o reconsiderar exige observación de al menos 15 caracteres. Los campos comerciales
            se aplican después del visto bueno profesional, no durante esta revisión.
        """
        entrada_serializer = (
            RevisarPropuestaServicioSerializer(
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
        with transaction.atomic():
            servicio = (
                Servicio.objects
                .select_for_update()
                .select_related(
                    "id_profesional",
                    "id_categoria",
                )
                .filter(
                    id_servicio=id_servicio
                )
                .first()
            )
            if servicio is None:
                return Response(
                    {
                        "mensaje": (
                            "El servicio solicitado "
                            "no existe."
                        )
                    },
                    status=(
                        status.HTTP_404_NOT_FOUND
                    ),
                )
            if (
                servicio.estado_publicacion
                != "EN_REVISION"
            ):
                return Response(
                    {
                        "mensaje": (
                            "La propuesta no se "
                            "encuentra pendiente de "
                            "revisión."
                        )
                    },
                    status=(
                        status.HTTP_409_CONFLICT
                    ),
                )
            decision = (
                entrada_serializer
                .validated_data[
                    "decision"
                ]
            )
            # Regla anti-bucle: tras el primer rechazo, únicamente se admite
            # una segunda versión comercial final; nunca correcciones indefinidas.
            rechazos_previos = RevisionServicio.objects.filter(
                id_servicio=servicio,
                estado_revision__in=["RECHAZO_COMERCIAL", "CIERRE_SIN_ACUERDO"],
            ).count()
            if rechazos_previos:
                ultima_negociacion = (RevisionServicio.objects.filter(id_servicio=servicio)
                    .order_by("-numero_version", "-fecha_revision", "-id_revision_servicio").first())
                if rechazos_previos != 1 or ultima_negociacion is None or (
                    ultima_negociacion.estado_revision != "RECHAZO_COMERCIAL"
                ):
                    return Response({"mensaje": "La reconsideración comercial ya fue utilizada o está cerrada."},
                                    status=status.HTTP_409_CONFLICT)
                if decision != RevisarPropuestaServicioSerializer.DECISION_APROBAR:
                    return Response({"mensaje": "La reconsideración admite únicamente una segunda versión final, no nuevas rondas de correcciones."},
                                    status=status.HTTP_409_CONFLICT)
            version_propuesta = (
                entrada_serializer
                .validated_data
                .get(
                    "version_propuesta"
                )
            )
            if decision == RevisarPropuestaServicioSerializer.DECISION_APROBAR:
                tarifa_anterior = (servicio.referencia_precio or "").strip().upper()
                if rechazos_previos == 1:
                    propuesta_previa = (RevisionServicio.objects.filter(
                        id_servicio=servicio,
                        estado_revision="RECHAZADA_PROFESIONAL",
                    ).order_by("-numero_version", "-id_revision_servicio").first())
                    if propuesta_previa is not None:
                        version_previa = extraer_version_propuesta_revision(
                            propuesta_previa.contenido_revisado
                        ) or {}
                        tarifa_anterior = str(version_previa.get("referencia_precio") or tarifa_anterior).strip().upper()
                tarifa_nueva = str((version_propuesta or {}).get("referencia_precio") or "").strip().upper()
                if (tarifa_anterior != tarifa_nueva or rechazos_previos == 1) and (
                    len(str(entrada_serializer.validated_data.get("observacion") or "").strip()) < 15
                ):
                    return Response({"mensaje": "Justifica el ajuste comercial con una observación de al menos 15 caracteres."},
                                    status=status.HTTP_400_BAD_REQUEST)
            if (
                decision
                == (
                    RevisarPropuestaServicioSerializer
                    .DECISION_APROBAR
                )
            ):
                id_categoria = (
                    version_propuesta[
                        "id_categoria"
                    ]
                )
                categoria = (
                    CategoriaServicio.objects
                    .filter(
                        id_categoria=id_categoria
                    )
                    .first()
                )
                if categoria is None:
                    return Response(
                        {
                            "version_propuesta": {
                                "id_categoria": [
                                    (
                                        "La categoría "
                                        "propuesta por "
                                        "Skilly no existe."
                                    )
                                ]
                            }
                        },
                        status=(
                            status.HTTP_400_BAD_REQUEST
                        ),
                    )
                ids_competencias = (
                    version_propuesta.get(
                        "ids_competencias",
                        [],
                    )
                )
                (
                    competencias,
                    ids_faltantes,
                ) = obtener_competencias(
                    ids_competencias
                )
                if ids_faltantes:
                    return Response(
                        {
                            "version_propuesta": {
                                "ids_competencias": [
                                    (
                                        "No existen las "
                                        "siguientes "
                                        "competencias: "
                                        + ", ".join(
                                            str(valor)
                                            for valor
                                            in ids_faltantes
                                        )
                                        + "."
                                    )
                                ]
                            }
                        },
                        status=(
                            status.HTTP_400_BAD_REQUEST
                        ),
                    )
            ultima_version = (
                RevisionServicio.objects
                .filter(
                    id_servicio=servicio
                )
                .aggregate(
                    ultima=Max(
                        "numero_version"
                    )
                )
                .get(
                    "ultima"
                )
            )
            if ultima_version is None:
                nueva_version = 1
            else:
                nueva_version = (
                    ultima_version + 1
                )
            contenido_revisado = (
                entrada_serializer
                .validated_data[
                    "contenido_revisado"
                ]
            )
            observacion = (
                entrada_serializer
                .validated_data
                .get(
                    "observacion"
                )
            )
            if observacion == "":
                observacion = None
            if (
                decision
                == (
                    RevisarPropuestaServicioSerializer
                    .DECISION_CORREGIR
                )
            ):
                estado_revision = (
                    "CORRECCION_SOLICITADA"
                )
                nuevo_estado_servicio = (
                    "CORRECCION_SOLICITADA"
                )
                accion_evento = (
                    "SOLICITAR_CORRECCIONES_"
                    "SERVICIO"
                )
            else:
                estado_revision = (
                    "PEND_APROBACION_PROFESIONAL"
                )
                nuevo_estado_servicio = (
                    "PEND_APROBACION_PROFESIONAL"
                )
                accion_evento = (
                    "APROBAR_REVISION_SERVICIO"
                )
            ahora = timezone.now()
            revision = (
                RevisionServicio.objects
                .create(
                    id_servicio=servicio,
                    id_usuario_skilly=(
                        request.user
                    ),
                    numero_version=(
                        nueva_version
                    ),
                    contenido_revisado=(
                        contenido_revisado
                    ),
                    observacion=observacion,
                    estado_revision=(
                        estado_revision
                    ),
                    fecha_revision=ahora,
                    fecha_aprobacion_profesional=(
                        None
                    ),
                )
            )
            servicio.estado_publicacion = (
                nuevo_estado_servicio
            )
            servicio.fecha_actualizacion = (
                ahora
            )
            servicio.save(
                update_fields=[
                    "estado_publicacion",
                    "fecha_actualizacion",
                ]
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo=(
                    "revision_servicio"
                ),
                entidad_id=(
                    revision
                    .id_revision_servicio
                ),
                accion=accion_evento,
                detalle_resumido=(
                    f"Revisión versión "
                    f"{nueva_version} del "
                    f"servicio "
                    f"{servicio.id_servicio}. "
                    f"Resultado: "
                    f"{estado_revision}."
                )[:255],
            )
        revision = (
            RevisionServicio.objects
            .select_related(
                "id_servicio",
                (
                    "id_servicio__"
                    "id_profesional"
                ),
                (
                    "id_servicio__"
                    "id_categoria"
                ),
                "id_usuario_skilly",
            )
            .get(
                id_revision_servicio=(
                    revision
                    .id_revision_servicio
                )
            )
        )
        serializer = (
            RevisionServicioAdministracionSerializer(
                revision
            )
        )
        if (
            revision.estado_revision
            == "CORRECCION_SOLICITADA"
        ):
            mensaje = (
                "La propuesta fue devuelta "
                "al profesional con "
                "correcciones solicitadas."
            )
        else:
            mensaje = (
                "La revisión final propuesta "
                "por Skilly fue enviada al "
                "profesional para su "
                "visto bueno."
            )
        return Response(
            {
                "mensaje": mensaje,
                "revision": serializer.data,
            },
            status=(
                status.HTTP_201_CREATED
            ),
        )


class DetalleRevisionServicioAdministracionView(
    APIView
):
    """Consulta una revisión concreta con sus datos de servicio y autor administrativo."""
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(
        self,
        request,
        id_revision_servicio,
    ):
        """Recupera una revisión por identificador sin restringir su estado histórico.

        Args:
            request (Request): Sesión administrativa activa.
            id_revision_servicio (int): Revisión que se consultará.

        Returns:
            Response: HTTP 200 con la revisión serializada o 404 si no existe.
        """
        revision = (
            RevisionServicio.objects
            .select_related(
                "id_servicio",
                (
                    "id_servicio__"
                    "id_profesional"
                ),
                (
                    "id_servicio__"
                    "id_categoria"
                ),
                "id_usuario_skilly",
            )
            .filter(
                id_revision_servicio=(
                    id_revision_servicio
                )
            )
            .first()
        )
        if revision is None:
            return Response(
                {
                    "mensaje": (
                        "La revisión de servicio "
                        "no existe."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )
        serializer = (
            RevisionServicioAdministracionSerializer(
                revision
            )
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
