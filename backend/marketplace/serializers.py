"""Valida publicaciones, propuestas y datos visibles del marketplace."""

import json
import re

from django.utils import timezone

from rest_framework import serializers

from .models import (
    RevisionServicio,
    Servicio,
    ServicioCompetencia,
)


FORMATO_REVISION_SERVICIO = (
    "SKILLY_REVISION_SERVICIO_V1"
)


def normalizar_precio_clp(
    value,
    permitir_vacio=True,
):
    """Normaliza un precio positivo de hasta diez dígitos seguido de CLP.

    Args:
        value (str | None): Precio sin separadores de miles, decimales ni símbolos.
        permitir_vacio (bool): Permite ausencia o texto vacío.

    Returns:
        str | None: Importe y CLP separados por un espacio, o ausencia admitida.

    Raises:
        serializers.ValidationError: Si falta el precio requerido o su formato es inválido.

    Example:
        >>> normalizar_precio_clp(" 140000clp ")
        '140000 CLP'
    """
    if value is None:
        if permitir_vacio:
            return None

        raise serializers.ValidationError(
            "Debe indicar el precio final del servicio."
        )

    texto = str(value).strip().upper()

    if not texto:
        if permitir_vacio:
            return None

        raise serializers.ValidationError(
            "Debe indicar el precio final del servicio."
        )

    coincidencia = re.fullmatch(
        r"([1-9]\d{0,9})\s*CLP",
        texto,
    )

    if coincidencia is None:
        raise serializers.ValidationError(
            "El precio debe tener un formato exacto "
            "como '140000 CLP', sin puntos, comas, "
            "símbolos ni expresiones aproximadas."
        )

    monto = coincidencia.group(1)

    return f"{monto} CLP"


def construir_contenido_revision_servicio(
    version_propuesta,
    resumen=None,
):
    """Codifica la versión comercial con su marcador de formato y resumen.

    Args:
        version_propuesta (dict): Datos previamente validados de la versión final.
        resumen (str | None): Texto opcional de administración, vacío por defecto.

    Returns:
        str: JSON compacto que conserva Unicode, sin validar sus campos.

    Raises:
        TypeError: Si algún valor no puede serializarse a JSON.
    """
    contenido = {
        "formato": FORMATO_REVISION_SERVICIO,
        "resumen": resumen or "",
        "version_propuesta": version_propuesta,
    }

    return json.dumps(
        contenido,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def leer_contenido_revision_servicio(
    contenido_revisado,
):
    """Reconoce una revisión estructurada sin interpretar texto histórico como contrato.

    Args:
        contenido_revisado (str): Contenido persistido, normalmente JSON o texto heredado.

    Returns:
        dict | None: Objeto con formato reconocido y version_propuesta de tipo dict;
        None si está vacío, no es JSON válido o no cumple esa estructura.
        No valida los campos internos de la propuesta.
    """
    if not contenido_revisado:
        return None

    try:
        contenido = json.loads(
            contenido_revisado
        )
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        contenido,
        dict,
    ):
        return None

    if (
        contenido.get("formato")
        != FORMATO_REVISION_SERVICIO
    ):
        return None

    version_propuesta = contenido.get(
        "version_propuesta"
    )

    if not isinstance(
        version_propuesta,
        dict,
    ):
        return None

    return contenido


def extraer_version_propuesta_revision(
    contenido_revisado,
):
    """Extrae la versión final de un contenido reconocido.

    Args:
        contenido_revisado (str): Contenido persistido de la revisión.

    Returns:
        dict | None: Versión propuesta sin validar su contenido comercial;
        None si no se reconoce el formato.
    """
    contenido = leer_contenido_revision_servicio(
        contenido_revisado
    )

    if contenido is None:
        return None

    return contenido.get(
        "version_propuesta"
    )


class CrearPropuestaServicioSerializer(
    serializers.Serializer
):
    """Valida la propuesta inicial; permite omitir precio y competencias."""
    nombre = serializers.CharField(
        max_length=150,
        allow_blank=False,
        trim_whitespace=True,
    )

    descripcion = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )

    id_categoria = serializers.IntegerField(
        min_value=1
    )

    ids_competencias = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1
        ),
        required=False,
        default=list,
    )

    modalidad = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    alcance = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    referencia_precio = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_ids_competencias(
        self,
        value,
    ):
        """Devuelve los ids recibidos sin duplicados, conservando su primer orden."""
        return list(
            dict.fromkeys(value)
        )

    def validate_referencia_precio(
        self,
        value,
    ):
        """Devuelve precio CLP normalizado o None; lanza ValidationError por formato inválido."""
        return normalizar_precio_clp(
            value,
            permitir_vacio=True,
        )


class ActualizarPropuestaServicioSerializer(
    serializers.Serializer
):
    """Valida campos opcionales de edición y exige al menos un cambio reconocido."""
    nombre = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=False,
        trim_whitespace=True,
    )

    descripcion = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=True,
    )

    id_categoria = serializers.IntegerField(
        min_value=1,
        required=False,
    )

    ids_competencias = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1
        ),
        required=False,
    )

    modalidad = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    alcance = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    referencia_precio = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_ids_competencias(
        self,
        value,
    ):
        """Deduplica los ids de competencias sin alterar su orden de entrada."""
        return list(
            dict.fromkeys(value)
        )

    def validate_referencia_precio(
        self,
        value,
    ):
        """Normaliza el precio opcional; devuelve None si está vacío y rechaza formatos inválidos."""
        return normalizar_precio_clp(
            value,
            permitir_vacio=True,
        )

    def validate(self, attrs):
        """Rechaza una edición sin campos reconocidos.

        Args:
            attrs (dict): Campos de edición validados por DRF.

        Returns:
            dict: Mismos campos recibidos, sin completar valores desde el modelo.

        Raises:
            serializers.ValidationError: Si el diccionario está vacío.
        """
        if not attrs:
            raise serializers.ValidationError(
                "Debe indicar al menos un campo "
                "para actualizar."
            )

        return attrs


class VersionPropuestaServicioSerializer(
    serializers.Serializer
):
    """Valida la versión final con precio obligatorio.

    Las vistas comprueban la existencia de categoría y competencias; los campos
    IntegerField solo validan la forma y el rango de sus identificadores.
    """
    nombre = serializers.CharField(
        max_length=150,
        allow_blank=False,
        trim_whitespace=True,
    )

    descripcion = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
    )

    id_categoria = serializers.IntegerField(
        min_value=1
    )

    ids_competencias = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1
        ),
        required=False,
        default=list,
    )

    modalidad = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    alcance = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    referencia_precio = serializers.CharField(
        max_length=120,
        allow_blank=False,
        allow_null=False,
    )

    def validate_ids_competencias(
        self,
        value,
    ):
        """Devuelve ids únicos conservando el orden de la propuesta recibida."""
        return list(
            dict.fromkeys(value)
        )

    def validate_referencia_precio(
        self,
        value,
    ):
        """Exige precio CLP válido; devuelve su forma canónica o lanza ValidationError."""
        return normalizar_precio_clp(
            value,
            permitir_vacio=False,
        )


class RevisarPropuestaServicioSerializer(
    serializers.Serializer
):
    """Distingue devolución para correcciones de versión final para aprobación profesional."""
    DECISION_APROBAR = (
        "APROBAR_REVISION"
    )

    DECISION_CORREGIR = (
        "SOLICITAR_CORRECCIONES"
    )

    decision = serializers.ChoiceField(
        choices=[
            DECISION_APROBAR,
            DECISION_CORREGIR,
        ]
    )

    contenido_revisado = (
        serializers.CharField(
            required=False,
            allow_blank=True,
            allow_null=True,
            trim_whitespace=True,
        )
    )

    version_propuesta = (
        VersionPropuestaServicioSerializer(
            required=False
        )
    )

    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        """Construye el contenido de revisión según la decisión administrativa.

        Args:
            attrs (dict): Decisión y campos previamente validados por DRF.

        Returns:
            dict: Datos con contenido_revisado. Para corrección usa observación si falta
            contenido; para aprobación codifica la versión en JSON estructurado.

        Raises:
            serializers.ValidationError: Si la corrección carece de observación o incluye
                versión final, o la aprobación no contiene una versión.
        """
        decision = attrs.get(
            "decision"
        )

        observacion = attrs.get(
            "observacion"
        )

        contenido_revisado = attrs.get(
            "contenido_revisado"
        )

        version_propuesta = attrs.get(
            "version_propuesta"
        )

        if (
            decision
            == self.DECISION_CORREGIR
        ):
            if not observacion:
                raise serializers.ValidationError(
                    {
                        "observacion": (
                            "Debe indicar la corrección "
                            "solicitada al profesional."
                        )
                    }
                )

            if version_propuesta is not None:
                raise serializers.ValidationError(
                    {
                        "version_propuesta": (
                            "No debe enviar una versión "
                            "final cuando la decisión es "
                            "solicitar correcciones."
                        )
                    }
                )

            if not contenido_revisado:
                attrs["contenido_revisado"] = (
                    observacion
                )

            return attrs

        if version_propuesta is None:
            raise serializers.ValidationError(
                {
                    "version_propuesta": (
                        "Debe indicar la versión final "
                        "propuesta por Skilly para que "
                        "el profesional pueda revisarla "
                        "y aprobarla."
                    )
                }
            )

        attrs["contenido_revisado"] = (
            construir_contenido_revision_servicio(
                version_propuesta=(
                    version_propuesta
                ),
                resumen=contenido_revisado,
            )
        )

        return attrs


class ServicioProfesionalSerializer(
    serializers.ModelSerializer
):
    """Presenta la oferta actual con categoría, competencias y resumen de última revisión."""
    categoria = (
        serializers.SerializerMethodField()
    )

    competencias = (
        serializers.SerializerMethodField()
    )

    revision_actual = (
        serializers.SerializerMethodField()
    )

    class Meta:
        """Define la representación de Servicio y protege sus campos de solo lectura."""

        model = Servicio

        fields = [
            "id_servicio",
            "nombre",
            "descripcion",
            "modalidad",
            "alcance",
            "referencia_precio",
            "estado_publicacion",
            "fecha_publicacion",
            "fecha_actualizacion",
            "categoria",
            "competencias",
            "revision_actual",
        ]

        read_only_fields = fields

    def get_categoria(
        self,
        servicio,
    ):
        """Devuelve id, nombre y estado de la categoría del servicio recibido."""
        categoria = servicio.id_categoria

        return {
            "id_categoria": (
                categoria.id_categoria
            ),
            "nombre": categoria.nombre,
            "estado": categoria.estado,
        }

    def get_competencias(
        self,
        servicio,
    ):
        """Devuelve ids y nombres de competencias del servicio ordenadas por nombre."""
        relaciones = (
            ServicioCompetencia.objects
            .filter(
                id_servicio=servicio
            )
            .select_related(
                "id_competencia"
            )
            .order_by(
                "id_competencia__nombre"
            )
        )

        return [
            {
                "id_competencia": (
                    relacion.id_competencia_id
                ),
                "nombre": (
                    relacion
                    .id_competencia
                    .nombre
                ),
            }
            for relacion in relaciones
        ]

    def get_revision_actual(
        self,
        servicio,
    ):
        """Devuelve el resumen de la revisión de mayor versión, o None si no existe.

        Incluye id, versión, estado y fechas; desempata por fecha e id descendentes.
        """
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

        if revision is None:
            return None

        return {
            "id_revision_servicio": (
                revision
                .id_revision_servicio
            ),
            "numero_version": (
                revision.numero_version
            ),
            "estado_revision": (
                revision.estado_revision
            ),
            "fecha_revision": (
                revision.fecha_revision
            ),
            "fecha_aprobacion_profesional": (
                revision
                .fecha_aprobacion_profesional
            ),
        }


class RevisionServicioAdministracionSerializer(
    serializers.ModelSerializer
):
    """Presenta revisión histórica y relaciones actuales del servicio a administración.

    propuesta_skilly procede del contenido revisado; servicio, categoría y
    competencias reflejan el modelo actual, no una copia de aquella versión.
    """
    servicio = (
        serializers.SerializerMethodField()
    )

    profesional = (
        serializers.SerializerMethodField()
    )

    categoria = (
        serializers.SerializerMethodField()
    )

    competencias = (
        serializers.SerializerMethodField()
    )

    propuesta_skilly = (
        serializers.SerializerMethodField()
    )

    class Meta:
        """Define la representación de RevisionServicio y protege sus campos de solo lectura."""

        model = RevisionServicio

        fields = [
            "id_revision_servicio",
            "numero_version",
            "estado_revision",
            "contenido_revisado",
            "propuesta_skilly",
            "observacion",
            "fecha_revision",
            "fecha_aprobacion_profesional",
            "id_usuario_skilly",
            "servicio",
            "profesional",
            "categoria",
            "competencias",
        ]

        read_only_fields = fields

    def get_propuesta_skilly(
        self,
        revision,
    ):
        """Extrae el dict de versión final, o None si el contenido no es reconocido."""
        return (
            extraer_version_propuesta_revision(
                revision.contenido_revisado
            )
        )

    def get_servicio(
        self,
        revision,
    ):
        """Devuelve datos comerciales, estado y fechas actuales del servicio revisado."""
        servicio = revision.id_servicio

        return {
            "id_servicio": (
                servicio.id_servicio
            ),
            "nombre": servicio.nombre,
            "descripcion": (
                servicio.descripcion
            ),
            "modalidad": (
                servicio.modalidad
            ),
            "alcance": servicio.alcance,
            "referencia_precio": (
                servicio.referencia_precio
            ),
            "estado_publicacion": (
                servicio.estado_publicacion
            ),
            "fecha_publicacion": (
                servicio.fecha_publicacion
            ),
            "fecha_actualizacion": (
                servicio.fecha_actualizacion
            ),
        }

    def get_profesional(
        self,
        revision,
    ):
        """Devuelve id, nombres, apellidos y validación del profesional del servicio."""
        profesional = (
            revision
            .id_servicio
            .id_profesional
        )

        return {
            "id_profesional": (
                profesional.id_profesional
            ),
            "nombres": (
                profesional.nombres
            ),
            "apellidos": (
                profesional.apellidos
            ),
            "estado_validacion": (
                profesional.estado_validacion
            ),
        }

    def get_categoria(
        self,
        revision,
    ):
        """Devuelve id, nombre y estado de la categoría actual del servicio revisado."""
        categoria = (
            revision
            .id_servicio
            .id_categoria
        )

        return {
            "id_categoria": (
                categoria.id_categoria
            ),
            "nombre": categoria.nombre,
            "estado": categoria.estado,
        }

    def get_competencias(
        self,
        revision,
    ):
        """Lista ids, nombres y estados de competencias actuales por nombre ascendente."""
        relaciones = (
            ServicioCompetencia.objects
            .filter(
                id_servicio=(
                    revision.id_servicio
                )
            )
            .select_related(
                "id_competencia"
            )
            .order_by(
                "id_competencia__nombre"
            )
        )

        return [
            {
                "id_competencia": (
                    relacion.id_competencia_id
                ),
                "nombre": (
                    relacion
                    .id_competencia
                    .nombre
                ),
                "estado": (
                    relacion
                    .id_competencia
                    .estado
                ),
            }
            for relacion in relaciones
        ]


class VersionRevisadaProfesionalSerializer(
    serializers.ModelSerializer
):
    """Muestra la revisión propuesta y la oferta actual al profesional para compararlas."""
    servicio = (
        serializers.SerializerMethodField()
    )

    propuesta_skilly = (
        serializers.SerializerMethodField()
    )

    class Meta:
        """Define la representación de RevisionServicio y protege sus campos de solo lectura."""

        model = RevisionServicio

        fields = [
            "id_revision_servicio",
            "numero_version",
            "estado_revision",
            "contenido_revisado",
            "propuesta_skilly",
            "observacion",
            "fecha_revision",
            "fecha_aprobacion_profesional",
            "servicio",
        ]

        read_only_fields = fields

    def get_propuesta_skilly(
        self,
        revision,
    ):
        """Extrae la versión estructurada de la revisión o devuelve None para texto heredado."""
        return (
            extraer_version_propuesta_revision(
                revision.contenido_revisado
            )
        )

    def get_servicio(
        self,
        revision,
    ):
        """Devuelve datos comerciales actuales y estado de publicación del servicio revisado."""
        servicio = revision.id_servicio

        return {
            "id_servicio": (
                servicio.id_servicio
            ),
            "nombre": servicio.nombre,
            "descripcion": (
                servicio.descripcion
            ),
            "modalidad": (
                servicio.modalidad
            ),
            "alcance": servicio.alcance,
            "referencia_precio": (
                servicio.referencia_precio
            ),
            "estado_publicacion": (
                servicio.estado_publicacion
            ),
        }


class ServicioMarketplaceSerializer(
    serializers.ModelSerializer
):
    """Distingue fichas públicas completas de tarjetas resumidas del catálogo.

    La vista debe filtrar servicios PUBLICADO; el serializador no autoriza objetos.
    """
    categoria = (
        serializers.SerializerMethodField()
    )

    competencias = (
        serializers.SerializerMethodField()
    )

    profesional = (
        serializers.SerializerMethodField()
    )

    disponibilidad = (
        serializers.SerializerMethodField()
    )

    class Meta:
        """Define la representación de Servicio y protege sus campos de solo lectura."""

        model = Servicio

        fields = [
            "id_servicio",
            "nombre",
            "descripcion",
            "modalidad",
            "alcance",
            "referencia_precio",
            "fecha_publicacion",
            "categoria",
            "competencias",
            "profesional",
            "disponibilidad",
        ]

        read_only_fields = fields

    def to_representation(
        self,
        instance,
    ):
        """Resume tarjetas en many=True y conserva el detalle individual.

        Args:
            instance (Servicio): Servicio cuya publicación ya comprobó la vista.

        Returns:
            dict: Id, nombre, categoría, modalidad y marca de disponibilidad en listas;
            representación completa declarada por el serializador en una ficha individual.
        """
        if isinstance(
            self.parent,
            serializers.ListSerializer,
        ):
            categoria = (
                instance.id_categoria
            )

            return {
                "id_servicio": (
                    instance.id_servicio
                ),
                "nombre": instance.nombre,
                "categoria": {
                    "id_categoria": (
                        categoria.id_categoria
                    ),
                    "nombre": (
                        categoria.nombre
                    ),
                },
                "modalidad": (
                    instance.modalidad
                ),
                "tiene_disponibilidad": (
                    self._tiene_disponibilidad(
                        instance
                    )
                ),
            }

        return super().to_representation(
            instance
        )

    def _tiene_disponibilidad(
        self,
        servicio,
    ):
        """Comprueba bloques visibles sin reservas PENDIENTE_PAGO o ACTIVA.

        Args:
            servicio (Servicio): Oferta cuyo profesional aporta los bloques.

        Returns:
            bool: Si existe un bloque DISPONIBLE desde hoy cuyo término aún no pasó.
            Puede incluir un bloque ya iniciado; el alta de solicitud revalida el inicio.
        """
        from solicitudes.models import (
            Disponibilidad,
            ReservaDisponibilidad,
        )

        ahora = timezone.localtime()
        fecha_actual = ahora.date()
        hora_actual = ahora.time()

        return (
            Disponibilidad.objects
            .filter(
                id_profesional=(
                    servicio.id_profesional
                ),
                estado="DISPONIBLE",
                fecha__gte=fecha_actual,
            )
            .exclude(
                fecha=fecha_actual,
                hora_fin__lte=hora_actual,
            )

            .exclude(
                id_disponibilidad__in=(
                    ReservaDisponibilidad.objects
                    .filter(estado__in=["PENDIENTE_PAGO", "ACTIVA"])
                    .values_list("id_disponibilidad_id", flat=True)
                )
            )
            .exists()
        )

    def get_categoria(
        self,
        servicio,
    ):
        """Devuelve id y nombre de categoría para la ficha pública del servicio."""
        categoria = servicio.id_categoria

        return {
            "id_categoria": (
                categoria.id_categoria
            ),
            "nombre": categoria.nombre,
        }

    def get_competencias(
        self,
        servicio,
    ):
        """Lista ids y nombres de competencias asociadas en orden alfabético."""
        relaciones = (
            ServicioCompetencia.objects
            .filter(
                id_servicio=servicio
            )
            .select_related(
                "id_competencia"
            )
            .order_by(
                "id_competencia__nombre"
            )
        )

        return [
            {
                "id_competencia": (
                    relacion.id_competencia_id
                ),
                "nombre": (
                    relacion
                    .id_competencia
                    .nombre
                ),
            }
            for relacion in relaciones
        ]

    def get_profesional(
        self,
        servicio,
    ):
        """Resume identidad, nombres, título y validación sin datos privados de contacto."""
        profesional = (
            servicio.id_profesional
        )

        return {
            "id_profesional": (
                profesional.id_profesional
            ),
            "nombres": (
                profesional.nombres
            ),
            "apellidos": (
                profesional.apellidos
            ),
            "titulo_profesional": (
                profesional.titulo_profesional
            ),
            "estado_validacion": (
                profesional.estado_validacion
            ),
        }

    def get_disponibilidad(
        self,
        servicio,
    ):
        """Lista bloques visibles del profesional sin reservas pendientes o activas.

        Args:
            servicio (Servicio): Servicio que aporta el profesional consultado.

        Returns:
            list[dict]: Id, fecha y horas por orden cronológico. Excluye días pasados
            y bloques de hoy terminados, pero no los que comenzaron y aún no terminan.
            La disponibilidad definitiva se comprueba al enviar la solicitud.
        """
        from solicitudes.models import (
            Disponibilidad,
            ReservaDisponibilidad,
        )

        ahora = timezone.localtime()
        fecha_actual = ahora.date()
        hora_actual = ahora.time()

        bloques = (
            Disponibilidad.objects
            .filter(
                id_profesional=(
                    servicio.id_profesional
                ),
                estado="DISPONIBLE",
                fecha__gte=fecha_actual,
            )

            .exclude(
                id_disponibilidad__in=(
                    ReservaDisponibilidad.objects
                    .filter(estado__in=["PENDIENTE_PAGO", "ACTIVA"])
                    .values_list("id_disponibilidad_id", flat=True)
                )
            )
            .order_by(
                "fecha",
                "hora_inicio",
                "id_disponibilidad",
            )
        )

        resultado = []

        for bloque in bloques:
            if (
                bloque.fecha
                == fecha_actual
                and bloque.hora_fin
                <= hora_actual
            ):
                continue

            resultado.append(
                {
                    "id_disponibilidad": (
                        bloque
                        .id_disponibilidad
                    ),
                    "fecha": bloque.fecha,
                    "hora_inicio": (
                        bloque.hora_inicio
                    ),
                    "hora_fin": (
                        bloque.hora_fin
                    ),
                }
            )

        return resultado
