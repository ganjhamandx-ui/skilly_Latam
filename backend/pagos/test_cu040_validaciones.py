from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from pagos.views import ReversasPagoAdministracionView


class CU040ValidacionesEconomicasTests(SimpleTestCase):

    def comprobar_rechazo(
        self,
        estado_pago="RETENIDO",
        verificacion="VERIFICADO",
        monto_total=Decimal("100000.00"),
        monto_autorizado=None,
        mensaje_esperado="",
    ):
        pago = SimpleNamespace(
            id_pago=900801,
            estado_pago=estado_pago,
            estado_verificacion=verificacion,
            monto_total=monto_total,
            id_prestacion=SimpleNamespace(
                estado="CANCELADA",
            ),
        )

        resolucion = None

        if monto_autorizado is not None:
            resolucion = SimpleNamespace(
                id_resolucion=900901,
                monto_afectado=monto_autorizado,
            )

        solicitud = SimpleNamespace(
            data={
                "motivo": "Prueba automatizada CU040",
            },
            user=SimpleNamespace(pk=900101),
        )

        with (
            patch("pagos.views.IniciarReversaPagoSerializer") as serializer,
            patch("pagos.views.Pago.objects") as pagos,
            patch("pagos.views.ReversaPago.objects") as reversas,
            patch("pagos.views.ResolucionReclamo.objects") as resoluciones,
            patch(
                "pagos.views.transaction.atomic",
                return_value=nullcontext(),
            ),
        ):
            serializer.return_value.is_valid.return_value = True

            serializer.return_value.validated_data = {
                "motivo": "Prueba automatizada CU040",
            }

            pagos.select_related.return_value.select_for_update.return_value.filter.return_value.first.return_value = pago

            reversas.filter.return_value.exists.return_value = False

            resoluciones.filter.return_value.order_by.return_value.first.return_value = resolucion

            respuesta = ReversasPagoAdministracionView().post(
                solicitud,
                id_pago=900801,
            )

            self.assertEqual(
                respuesta.status_code,
                409,
            )

            self.assertIn(
                mensaje_esperado,
                respuesta.data["mensaje"],
            )

            reversas.create.assert_not_called()

    def test_rechaza_pago_liberado(self):
        self.comprobar_rechazo(
            estado_pago="LIBERADO",
            mensaje_esperado="RETENIDO",
        )
        print("CU040 PAGO LIBERADO: BLOQUEADO")

    def test_rechaza_pago_no_verificado(self):
        self.comprobar_rechazo(
            verificacion="PENDIENTE",
            mensaje_esperado="VERIFICADO",
        )
        print("CU040 PAGO NO VERIFICADO: BLOQUEADO")

    def test_rechaza_pago_monto_cero(self):
        self.comprobar_rechazo(
            monto_total=Decimal("0.00"),
            mensaje_esperado="monto total",
        )
        print("CU040 PAGO SIN MONTO VALIDO: BLOQUEADO")

    def test_rechaza_reversa_superior_al_pago(self):
        self.comprobar_rechazo(
            monto_autorizado=Decimal("100000.01"),
            mensaje_esperado="no superar",
        )
        print("CU040 REVERSA MAYOR AL PAGO: BLOQUEADA")

    def test_rechaza_reversa_monto_cero(self):
        self.comprobar_rechazo(
            monto_autorizado=Decimal("0.00"),
            mensaje_esperado="mayor que cero",
        )
        print("CU040 REVERSA DE MONTO CERO: BLOQUEADA")

    def test_rechaza_reversa_monto_negativo(self):
        self.comprobar_rechazo(
            monto_autorizado=Decimal("-5000.00"),
            mensaje_esperado="mayor que cero",
        )
        print("CU040 REVERSA DE MONTO NEGATIVO: BLOQUEADA")
