
"""Bandeja de propuestas pendientes de revision de Skilly."""

from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly

from profesionales.models import Competencia

from .models import CategoriaServicio, RevisionServicio, Servicio
from .serializers import ServicioProfesionalSerializer


class PropuestasPendientesAdministracionView(APIView):

    # Solo administradores autenticados de SKILLY.
    authentication_classes = [
        SesionSkillyAuthentication,
    ]

    permission_classes = [
        EsAdministracionSkilly,
    ]

    # Consulta de solo lectura.
    http_method_names = [
        "get",
        "head",
        "options",
    ]

    def get(self, request):

        # Servicios enviados por profesionales a revision.
        servicios = (
            Servicio.objects
            .filter(
                estado_publicacion="EN_REVISION"
            )
            .select_related(
                "id_profesional",
                "id_categoria",
            )
            .order_by(
                "fecha_actualizacion",
                "id_servicio",
            )
        )

        resultados = []

        for servicio in servicios:

            datos = ServicioProfesionalSerializer(
                servicio
            ).data

            profesional = servicio.id_profesional

            datos["profesional"] = {
                "id_profesional": (
                    profesional.id_profesional
                ),
                "nombres": profesional.nombres,
                "apellidos": profesional.apellidos,
            }

            # Muestra el desacuerdo al responsable sin exponer datos ajenos.
            ultima = (RevisionServicio.objects.filter(id_servicio=servicio)
                      .order_by("-numero_version", "-fecha_revision", "-id_revision_servicio").first())
            if ultima is not None and ultima.estado_revision == "RECHAZO_COMERCIAL":
                import json
                try:
                    info = json.loads(ultima.contenido_revisado or "{}")
                except (ValueError, TypeError):
                    info = {}
                datos["reconsideracion_comercial"] = {
                    "motivo": ultima.observacion or "",
                    "categoria": info.get("motivo_etiqueta", "Otro"),
                    "ronda": 1,
                    "fecha": ultima.fecha_revision,
                }
            resultados.append(datos)

        # Categorias disponibles para la version
        # que SKILLY propone al profesional.
        categorias = list(
            CategoriaServicio.objects
            .exclude(estado__iexact="INACTIVO")
            .exclude(estado__iexact="INACTIVA")
            .exclude(estado__iexact="DESHABILITADO")
            .exclude(estado__iexact="DESHABILITADA")
            .order_by(
                "nombre",
                "id_categoria",
            )
            .values(
                "id_categoria",
                "nombre",
            )
        )

        # Competencias para la revision administrativa.
        competencias = list(
            Competencia.objects
            .exclude(estado__iexact="INACTIVO")
            .exclude(estado__iexact="INACTIVA")
            .exclude(estado__iexact="DESHABILITADO")
            .exclude(estado__iexact="DESHABILITADA")
            .order_by(
                "nombre",
                "id_competencia",
            )
            .values(
                "id_competencia",
                "nombre",
            )
        )

        return Response(
            {
                "servicios": resultados,
                "total": len(resultados),
                "categorias": categorias,
                "competencias": competencias,
            }
        )
