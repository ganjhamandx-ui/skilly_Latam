from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from pagos.views import (
    LiberarPagoAdministracionView,
    ReversasPagoAdministracionView,
)


class CU040ProteccionesEconomicasTests(SimpleTestCase):

    def test_no_liberar_pago_con_reversa_solicitada(self):
        pago = MagicMock()
        pago.id_pago = 900801
        pago.estado_pago = "RETENIDO"
        pago.estado_verificacion = "VERIFICADO"

        request = SimpleNamespace(
            data={"observacion": "Prueba CU040"},
        )

        with (
            patch("pagos.views.LiberarPagoSerializer") as serializer,
            patch("pagos.views.Pago.objects") as pagos,
            patch("pagos.views.ReversaPago.objects") as reversas,
            patch(
                "pagos.views.transaction.atomic",
                return_value=nullcontext(),
            ),
        ):
            serializer.return_value.is_valid.return_value = True
            serializer.return_value.validated_data = {
                "observacion": "Prueba CU040",
            }

            pagos.select_for_update.return_value.filter.return_value.first.return_value = pago

            reversas.filter.return_value.exists.return_value = True

            respuesta = LiberarPagoAdministracionView().post(
                request,
                id_pago=900801,
            )

            self.assertEqual(respuesta.status_code, 409)

            reversas.filter.assert_called_once_with(
                id_pago=pago,
                estado_reversa="SOLICITADA",
            )

            pago.save.assert_not_called()

        print(
            "CU040 - LIBERACION CON REVERSA PENDIENTE: BLOQUEADA"
        )

    def test_no_duplicar_reversa_solicitada(self):
        pago = MagicMock()
        pago.id_pago = 900801

        request = SimpleNamespace(
            data={"motivo": "Prueba de duplicidad CU040"},
        )

        with (
            patch("pagos.views.IniciarReversaPagoSerializer") as serializer,
            patch("pagos.views.Pago.objects") as pagos,
            patch("pagos.views.ReversaPago.objects") as reversas,
            patch(
                "pagos.views.transaction.atomic",
                return_value=nullcontext(),
            ),
        ):
            serializer.return_value.is_valid.return_value = True
            serializer.return_value.validated_data = {
                "motivo": "Prueba de duplicidad CU040",
            }

            pagos.select_related.return_value.select_for_update.return_value.filter.return_value.first.return_value = pago

            reversas.filter.return_value.exists.return_value = True

            respuesta = ReversasPagoAdministracionView().post(
                request,
                id_pago=900801,
            )

            self.assertEqual(respuesta.status_code, 409)

            reversas.filter.assert_called_once_with(
                id_pago=pago,
                estado_reversa="SOLICITADA",
            )

            reversas.create.assert_not_called()

        print(
            "CU040 - REVERSA SOLICITADA DUPLICADA: BLOQUEADA"
        )
