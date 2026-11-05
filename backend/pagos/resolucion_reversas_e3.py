"""Cierre administrativo de reversas para la demostración académica E3.
No genera ni declara reembolsos reales.
"""
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from backoffice.services import registrar_evento_trazabilidad
from .models import HistorialEstadoPago, Pago, ReversaPago
from .serializers import PagoAdministracionSerializer, ReversaPagoSerializer
from .politicas_reversas_e3 import plan_cierre, ReversaInvalida


class CierreReversaSerializer(serializers.Serializer):
    accion = serializers.ChoiceField(choices=[
        "RECHAZAR_SOLICITUD", "REGISTRAR_DEVOLUCION_SIMULADA",
    ])
    fundamento = serializers.CharField(min_length=20, max_length=1000, trim_whitespace=True)
    confirma_sin_dinero_real = serializers.BooleanField(default=False)


@method_decorator(csrf_protect, name="dispatch")
class ResolverReversaE3AdministracionView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def post(self, request, id_pago, id_reversa):
        entrada = CierreReversaSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)
        datos = entrada.validated_data
        with transaction.atomic():
            # Siempre bloquear primero Pago, igual que CU040, para evitar interbloqueos.
            pago = (Pago.objects.select_for_update()
                    .filter(id_pago=id_pago).first())
            if pago is None:
                return Response({"mensaje": "El pago no existe."}, status=404)
            reversa = (ReversaPago.objects.select_for_update()
                       .filter(id_pago=pago, id_reversa=id_reversa).first())
            if reversa is None:
                return Response({"mensaje": "La reversa no corresponde a este pago."}, status=404)
            from seguimiento.conciliacion_reversas_e3 import ConciliacionReversaE3
            if ConciliacionReversaE3.objects.filter(id_reversa=reversa).exists():
                return Response({"mensaje": "La reversa tiene una conciliación parcial documental. No puede resolverse con el cierre académico de devolución total ni rechazarse sin una revisión específica."}, status=409)
            try:
                estado_reversa, estado_pago = plan_cierre(
                    accion=datos["accion"],
                    estado_pago=pago.estado_pago,
                    estado_verificacion=pago.estado_verificacion,
                    estado_reversa=reversa.estado_reversa,
                    metodo_pago=pago.metodo_pago,
                    monto_total=pago.monto_total,
                    monto_reversa=reversa.monto_reversa,
                    confirmado=datos["confirma_sin_dinero_real"],
                )
            except ReversaInvalida as error:
                return Response({"mensaje": str(error)}, status=409)
            ahora = timezone.now()
            original = (reversa.motivo or "").strip()
            etiqueta = ("SIMULACIÓN ACADÉMICA: SIN DEVOLUCIÓN DE DINERO" if
                        estado_reversa == "SIMULADA" else "SOLICITUD DE REVERSA RECHAZADA")
            reversa.estado_reversa = estado_reversa
            reversa.fecha_resolucion = ahora
            reversa.motivo = f"{original}\n\n[{etiqueta}]\n{datos['fundamento']}".strip()
            campos = ["estado_reversa", "fecha_resolucion", "motivo"]
            if estado_reversa == "SIMULADA":
                reversa.referencia_externa = f"DEMO-E3-R{reversa.id_reversa}"
                campos.append("referencia_externa")
            reversa.save(update_fields=campos)
            if estado_pago != pago.estado_pago:
                anterior = pago.estado_pago
                pago.estado_pago = estado_pago
                pago.save(update_fields=["estado_pago"])
                HistorialEstadoPago.objects.create(
                    id_pago=pago, id_usuario_skilly=request.user,
                    estado_anterior=anterior, estado_nuevo=estado_pago,
                    fecha_cambio=ahora,
                    observacion=("Simulación académica del reembolso total. "
                                 "No se transfirió dinero ni se usó el banco."),
                )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="reversa_pago", entidad_id=reversa.id_reversa,
                accion=("SIMULAR_REVERSA_E3" if estado_reversa == "SIMULADA"
                        else "RECHAZAR_REVERSA_E3"),
                detalle_resumido=f"Pago #{pago.id_pago}. {etiqueta}. {datos['fundamento']}"[:255],
            )
        return Response({
            "mensaje": ("Registro académico completado: SIN transferencia ni devolución real."
                        if estado_reversa == "SIMULADA" else
                        "Solicitud rechazada mediante resolución administrativa."),
            "reversa": ReversaPagoSerializer(reversa).data,
            "pago": PagoAdministracionSerializer(pago).data,
            "ambiente": "SIMULACION_ACADEMICA",
        }, status=status.HTTP_200_OK)
