"""Parametro independiente para cargo de gestión por cancelación no justificada.

Este endpoint NO aplica cargos ni ejecuta reembolsos. El porcentaje vigente se
consultará y congelará en una resolución económica futura, con sus salvaguardas.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from .models import HistorialParametro, ParametroSistema
from .serializers import HistorialParametroSerializer, ParametroSistemaSerializer

CLAVE_CARGO_CANCELACION = "cancelacion_injustificada_porcentaje"


class ActualizarCargoCancelacionSerializer(serializers.Serializer):
    """Valida el porcentaje configurable aplicado a cancelaciones injustificadas."""

    valor_nuevo = serializers.DecimalField(
        max_digits=7,
        decimal_places=4,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
    )


@method_decorator(csrf_protect, name='dispatch')
class ConfiguracionCargoCancelacionView(APIView):
    """Consulta y actualiza el cargo de cancelación con trazabilidad administrativa."""

    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        """Consulta el porcentaje de cancelación y su historial administrativo.

        Args:
            request: Petición administrativa autenticada.

        Returns:
            Response: 200 con parámetro e historial; si no está configurado,
            devuelve parametro None e historial vacío, sin fijar un valor por defecto.
        """
        parametro = (
            ParametroSistema.objects
            .select_related("id_usuario_actualiza")
            .filter(clave=CLAVE_CARGO_CANCELACION)
            .first()
        )
        if parametro is None:
            return Response({
                "mensaje": "El cargo por cancelación injustificada aún no está configurado.",
                "parametro": None,
                "historial": [],
            }, status=status.HTTP_200_OK)

        historial = (
            HistorialParametro.objects
            .select_related("id_usuario_skilly")
            .filter(id_parametro=parametro)
            .order_by("-fecha_cambio", "-id_historial_parametro")
        )
        return Response({
            "parametro": ParametroSistemaSerializer(parametro).data,
            "historial": HistorialParametroSerializer(historial, many=True).data,
        })

    def patch(self, request):
        """Actualiza el porcentaje independiente de cancelación con historial.

        Args:
            request: Petición con valor_nuevo entre 0 y 100, hasta cuatro decimales.

        Returns:
            Response: 200 con el parámetro guardado o 409 si el valor numérico ya
            era el vigente. Conserva el valor anterior y el responsable dentro de
            la transacción, sin aplicar cargos ni modificar liquidaciones existentes.

        Raises:
            serializers.ValidationError: Si el porcentaje es inválido; DRF devuelve 400.
        """
        entrada = ActualizarCargoCancelacionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        valor = entrada.validated_data["valor_nuevo"]
        texto = format(valor, "f")

        with transaction.atomic():
            ahora = timezone.now()
            parametro = (
                ParametroSistema.objects
                .select_for_update()
                .filter(clave=CLAVE_CARGO_CANCELACION)
                .first()
            )
            if parametro is None:
                parametro, creado = ParametroSistema.objects.get_or_create(
                    clave=CLAVE_CARGO_CANCELACION,
                    defaults={
                        "valor_actual": texto,
                        "tipo_dato": "DECIMAL",
                        "descripcion": (
                            "Cargo configurable por cancelación injustificada; "
                            "independiente de la comisión final de servicio"
                        ),
                        "id_usuario_actualiza": request.user,
                        "fecha_actualizacion": ahora,
                    },
                )
                if not creado:
                    parametro = ParametroSistema.objects.select_for_update().get(pk=parametro.pk)
            else:
                creado = False

            if creado:
                anterior = None
            else:
                anterior = parametro.valor_actual
                try:
                    sin_cambio = Decimal(anterior) == valor
                except (InvalidOperation, ValueError, TypeError):
                    sin_cambio = anterior == texto
                if sin_cambio:
                    return Response(
                        {"mensaje": "El porcentaje ya corresponde al valor vigente."},
                        status=status.HTTP_409_CONFLICT,
                    )
                parametro.valor_actual = texto
                parametro.id_usuario_actualiza = request.user
                parametro.fecha_actualizacion = ahora
                parametro.save(update_fields=[
                    "valor_actual", "id_usuario_actualiza", "fecha_actualizacion"
                ])

            HistorialParametro.objects.create(
                id_parametro=parametro,
                valor_anterior=anterior,
                valor_nuevo=texto,
                id_usuario_skilly=request.user,
                fecha_cambio=ahora,
            )

        parametro = ParametroSistema.objects.select_related(
            "id_usuario_actualiza"
        ).get(clave=CLAVE_CARGO_CANCELACION)
        return Response({
            "mensaje": "Porcentaje de cancelación guardado; cambio registrado en historial.",
            "parametro": ParametroSistemaSerializer(parametro).data,
        }, status=status.HTTP_200_OK)
