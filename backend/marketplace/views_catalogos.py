"""Expone catálogos de apoyo usados por formularios del marketplace."""

from rest_framework.response import Response
from rest_framework.views import APIView

from marketplace.models import CategoriaServicio
from profesionales.models import Competencia

# Se reutiliza la autenticacion y el permiso profesional
# que ya funcionan en el modulo de servicios.
from marketplace.views import (
    SesionSkillyAuthentication,
    EsProfesional,
)


class CatalogosPropuestasView(APIView):

    # Reconocer la sesion propia de SKILLY.
    authentication_classes = [
        SesionSkillyAuthentication,
    ]

    # Solo un profesional autenticado puede consultar
    # los catalogos utilizados en sus propuestas.
    permission_classes = [
        EsProfesional,
    ]

    # Este endpoint solo permite consultas.
    http_method_names = [
        "get",
        "head",
        "options",
    ]

    def get(self, request):

        # Obtener categorias habilitadas.
        categorias = (
            CategoriaServicio.objects
            .exclude(estado__iexact="INACTIVO")
            .exclude(estado__iexact="INACTIVA")
            .exclude(estado__iexact="DESHABILITADO")
            .exclude(estado__iexact="DESHABILITADA")
            .order_by("nombre", "id_categoria")
            .values(
                "id_categoria",
                "nombre",
                "descripcion",
                "estado",
            )
        )

        # Obtener competencias habilitadas.
        competencias = (
            Competencia.objects
            .exclude(estado__iexact="INACTIVO")
            .exclude(estado__iexact="INACTIVA")
            .exclude(estado__iexact="DESHABILITADO")
            .exclude(estado__iexact="DESHABILITADA")
            .order_by("nombre", "id_competencia")
            .values(
                "id_competencia",
                "nombre",
                "descripcion",
                "estado",
            )
        )

        categorias_lista = list(categorias)
        competencias_lista = list(competencias)

        return Response(
            {
                "categorias": categorias_lista,
                "competencias": competencias_lista,
                "total_categorias": len(categorias_lista),
                "total_competencias": len(competencias_lista),
            }
        )
