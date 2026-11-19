"""Valida datos de perfiles, documentos y entrevistas profesionales."""

from rest_framework import serializers
from backoffice.models import EventoTrazabilidad

from .models import (
    BloqueEntrevistaValidacion,
    DocumentoProfesional,
    EntrevistaValidacion,
    Profesional,
    ProfesionalCompetencia,
    SolicitudValidacion,
    ValidacionDocumento,
)


class PerfilProfesionalSerializer(serializers.ModelSerializer):
    correo = serializers.CharField(
        source="id_usuario.correo",
        read_only=True,
    )

    estado_validacion = serializers.CharField(
        read_only=True,
    )

    fecha_registro = serializers.DateTimeField(
        read_only=True,
    )

    competencias = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de Profesional y protege sus campos de solo lectura."""

        model = Profesional

        fields = [
            "id_profesional",
            "correo",
            "nombres",
            "apellidos",
            "telefono",
            "titulo_profesional",
            "resumen",
            "ubicacion",
            "estado_validacion",
            "fecha_registro",
            "competencias",
        ]

        read_only_fields = [
            "id_profesional",
            "correo",
            "estado_validacion",
            "fecha_registro",
            "competencias",
        ]

    def get_competencias(self, profesional):
        relaciones = (
            ProfesionalCompetencia.objects
            .filter(
                id_profesional=profesional
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
                    relacion.id_competencia.nombre
                ),
                "estado": (
                    relacion.id_competencia.estado
                ),
            }
            for relacion in relaciones
        ]

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        if validated_data:
            instance.save(
                update_fields=list(
                    validated_data.keys()
                )
            )

        return instance


class DocumentoProfesionalSerializer(
    serializers.ModelSerializer
):
    estado_revision = serializers.SerializerMethodField()
    observacion_revision = serializers.SerializerMethodField()

    def _ultima_revision(self, obj):
        return (ValidacionDocumento.objects
            .filter(id_documento=obj)
            .order_by('-id_validacion_id').first())

    def get_estado_revision(self, obj):
        v = self._ultima_revision(obj)
        return v.estado_revision if v else None

    def get_observacion_revision(self, obj):
        v = self._ultima_revision(obj)
        return v.observacion if v else None

    class Meta:
        """Define la representación de DocumentoProfesional y protege sus campos de solo lectura."""

        model = DocumentoProfesional

        fields = [
            "id_documento",
            "tipo_documento",
            "nombre_archivo",
            "visibilidad",
            "estado",
            "fecha_carga",
            "estado_revision",
            "observacion_revision",
        ]

        read_only_fields = fields


class EstadoValidacionSerializer(serializers.ModelSerializer):
    class Meta:
        """Define la representación de SolicitudValidacion y protege sus campos de solo lectura."""

        model = SolicitudValidacion

        fields = [
            "id_validacion",
            "estado",
            "fecha_solicitud",
            "fecha_asignacion",
            "fecha_revision",
        ]

        read_only_fields = fields


class RevisionValidacionAdministracionSerializer(
    serializers.ModelSerializer
):
    profesional = serializers.SerializerMethodField()
    documentos = serializers.SerializerMethodField()
    entrevista = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de SolicitudValidacion y protege sus campos de solo lectura."""

        model = SolicitudValidacion

        fields = [
            "id_validacion",
            "profesional",
            "id_revisor_skilly",
            "estado",
            "observacion_resultado",
            "fecha_solicitud",
            "fecha_asignacion",
            "fecha_revision",
            "documentos",
            "entrevista",
        ]

        read_only_fields = fields

    def get_profesional(self, solicitud):
        profesional = solicitud.id_profesional

        return {
            "id_profesional": profesional.id_profesional,
            "correo": profesional.id_usuario.correo,
            "nombres": profesional.nombres,
            "apellidos": profesional.apellidos,
            "telefono": profesional.telefono,
            "titulo_profesional": (
                profesional.titulo_profesional
            ),
            "estado_validacion": (
                profesional.estado_validacion
            ),
        }

    def get_documentos(self, solicitud):
        vinculos = (
            ValidacionDocumento.objects
            .filter(id_validacion=solicitud)
            .select_related("id_documento")
            .order_by("id_documento_id")
        )
        return [
            {
                **DocumentoProfesionalSerializer(v.id_documento).data,
                "estado_revision": v.estado_revision,
                "observacion": v.observacion,
            }
            for v in vinculos
        ]

    def get_entrevista(self, solicitud):
        entrevista = (
            EntrevistaValidacion.objects
            .select_related(
                "id_bloque_entrevista"
            )
            .filter(
                id_validacion=solicitud
            )
            .order_by(
                "-fecha_reserva",
                "-id_entrevista",
            )
            .first()
        )

        if entrevista is None:
            return None

        bloque = entrevista.id_bloque_entrevista

        return {
            "id_entrevista": entrevista.id_entrevista,
            "id_validacion": entrevista.id_validacion_id,
            "id_bloque_entrevista": (
                entrevista.id_bloque_entrevista_id
            ),
            "estado": entrevista.estado,
            "fecha_reserva": entrevista.fecha_reserva,
            "fecha": bloque.fecha,
            "hora_inicio": bloque.hora_inicio,
            "hora_fin": bloque.hora_fin,
            "observacion": entrevista.observacion,
        }


class ActualizarObservacionValidacionSerializer(
    serializers.Serializer
):
    observacion_resultado = serializers.CharField(
        required=True,
        allow_blank=True,
        allow_null=True,
    )


class EntrevistaValidacionResumenSerializer(
    serializers.ModelSerializer
):
    contactado = serializers.SerializerMethodField()
    fecha_contacto = serializers.SerializerMethodField()

    def _evento(self, entrevista):
        cache = self.context.get("contactos_por_entrevista")
        if cache is not None:
            return cache.get(entrevista.pk)
        return (EventoTrazabilidad.objects.filter(
            entidad_tipo="entrevista_validacion",
            entidad_id=entrevista.pk,
            accion="CONTACTO_PREENTREVISTA_REALIZADO",
        ).order_by("-id_evento").first())

    def get_contactado(self, entrevista):
        return self._evento(entrevista) is not None

    def get_fecha_contacto(self, entrevista):
        evento = self._evento(entrevista)
        return evento.fecha_evento if evento else None

    class Meta:
        """Define la representación de EntrevistaValidacion y protege sus campos de solo lectura."""

        model = EntrevistaValidacion

        fields = [
            "id_entrevista",
            "id_validacion",
            "estado",
            "fecha_reserva",
            "observacion",
            "contactado",
            "fecha_contacto",
        ]

        read_only_fields = fields


class BloqueEntrevistaAdministracionSerializer(
    serializers.ModelSerializer
):
    reservas = serializers.SerializerMethodField()
    disponibilidad = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de BloqueEntrevistaValidacion y protege sus campos de solo lectura."""

        model = BloqueEntrevistaValidacion

        fields = [
            "id_bloque_entrevista",
            "id_usuario_gestor",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "capacidad",
            "estado",
            "reservas",
            "disponibilidad",
        ]

        read_only_fields = fields

    def get_disponibilidad(self, bloque):
        ocupados = (EntrevistaValidacion.objects
                    .filter(id_bloque_entrevista=bloque)
                    .exclude(estado="CANCELADA").count())
        if bloque.estado != "DISPONIBLE":
            return "DESHABILITADO"
        return "COMPLETO" if ocupados >= bloque.capacidad else "DISPONIBLE"

    def get_reservas(self, bloque):
        entrevistas = (
            EntrevistaValidacion.objects
            .filter(
                id_bloque_entrevista=bloque
            )
            .order_by(
                "fecha_reserva",
                "id_entrevista",
            )
        )

        lista = list(entrevistas)
        ids = [entrevista.pk for entrevista in lista]
        contactos = {}
        if ids:
            for evento in (EventoTrazabilidad.objects.filter(
                entidad_tipo="entrevista_validacion",
                entidad_id__in=ids,
                accion="CONTACTO_PREENTREVISTA_REALIZADO",
            ).order_by("-id_evento")):
                contactos.setdefault(evento.entidad_id, evento)
        return EntrevistaValidacionResumenSerializer(
            lista, many=True, context={"contactos_por_entrevista": contactos}
        ).data


class EntrevistaProfesionalSerializer(
    serializers.ModelSerializer
):
    bloque = serializers.SerializerMethodField()

    class Meta:
        """Define la representación de EntrevistaValidacion y protege sus campos de solo lectura."""

        model = EntrevistaValidacion

        fields = [
            "id_entrevista",
            "id_validacion",
            "estado",
            "fecha_reserva",
            "bloque",
        ]

        read_only_fields = fields

    def get_bloque(self, entrevista):
        bloque = entrevista.id_bloque_entrevista

        return {
            "id_bloque_entrevista": (
                bloque.id_bloque_entrevista
            ),
            "fecha": bloque.fecha,
            "hora_inicio": bloque.hora_inicio,
            "hora_fin": bloque.hora_fin,
        }
