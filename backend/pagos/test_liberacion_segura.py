"""Transiciones de liberacion con ORM simulado; sin pagos ni conexiones reales."""
from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from pagos.views import LiberarPagoAdministracionView


class LiberacionSeguraTests(SimpleTestCase):
    """Comprueba condiciones de liberación y ausencia de movimientos duplicados."""
    def ejecutar(self, *, verificacion="VERIFICADO", estado_pago="RETENIDO",
                 estado_prestacion="CONTRATADA", reversa=False, reclamo=False,
                 estado_entrega="ACEPTADA"):
        """Despacha la liberación con registros, transacción y trazabilidad simulados.

        Args:
            verificacion: Estado de verificación del pago.
            estado_pago: Estado inicial del pago.
            estado_prestacion: Estado de la prestación vinculada.
            reversa: Indica si existe una reversa que bloquea la liberación.
            reclamo: Indica si existe un reclamo que bloquea la liberación.
            estado_entrega: Estado de la última entrega simulada.

        Returns:
            tuple: Respuesta, pago y cantidades de entradas de historial y trazabilidad.
        """
        pago = SimpleNamespace(
            id_pago=901, id_prestacion_id=902, estado_pago=estado_pago,
            estado_verificacion=verificacion, monto_neto_profesional=Decimal("9000"),
            moneda="CLP", save=MagicMock(),
        )
        prestacion = SimpleNamespace(id_prestacion=902, estado=estado_prestacion)
        entrega = SimpleNamespace(id_entrega=903, version=2, estado=estado_entrega)
        request = SimpleNamespace(data={"accion": "LIBERAR_PAGO"}, user=SimpleNamespace(pk=904))
        with (
            patch("pagos.views.Pago.objects") as pagos,
            patch("pagos.views.PrestacionServicio.objects") as prestaciones,
            patch("pagos.views.Entrega.objects") as entregas,
            patch("pagos.views.ReversaPago.objects") as reversas,
            patch("pagos.views.ReclamoPrestacion.objects") as reclamos,
            patch("pagos.views.ResolucionReclamo.objects") as resoluciones,
            patch("pagos.views.HistorialEstadoPago.objects") as historial,
            patch("pagos.views.PagoAdministracionSerializer") as salida,
            patch("pagos.views.registrar_evento_trazabilidad") as evento,
            patch("pagos.views.transaction.atomic", return_value=nullcontext()),
        ):
            pagos.select_for_update.return_value.filter.return_value.first.return_value = pago
            pagos.get.return_value = pago
            prestaciones.select_for_update.return_value.filter.return_value.first.return_value = prestacion
            entregas.select_for_update.return_value.filter.return_value.order_by.return_value.first.return_value = entrega
            reversas.filter.return_value.exists.return_value = reversa
            reclamos.filter.return_value.filter.return_value.exists.return_value = reclamo
            reclamos.filter.return_value.count.return_value = 0
            resoluciones.filter.return_value.count.return_value = 0
            resoluciones.filter.return_value.exclude.return_value.order_by.return_value.first.return_value = None
            salida.return_value.data = {"id_pago": pago.id_pago, "estado_pago": pago.estado_pago}
            respuesta = LiberarPagoAdministracionView().post(request, id_pago=pago.id_pago)
            return respuesta, pago, historial.create.call_count, evento.call_count

    def test_pago_retenido_no_verificado_no_puede_liberarse(self):
        """Exige verificación sin modificar pago, historial ni trazabilidad ante rechazo."""
        for verificacion in ("PENDIENTE", "RECHAZADO", None):
            with self.subTest(verificacion=verificacion):
                respuesta, pago, historial, eventos = self.ejecutar(verificacion=verificacion)
                self.assertEqual(respuesta.status_code, 409)
                self.assertIn("VERIFICADO", respuesta.data["mensaje"])
                self.assertEqual(pago.estado_pago, "RETENIDO")
                pago.save.assert_not_called()
                self.assertEqual((historial, eventos), (0, 0))

    def test_verificado_sin_bloqueos_se_libera_una_vez(self):
        """Comprueba una única escritura y una entrada de historial y evento al liberar."""
        respuesta, pago, historial, eventos = self.ejecutar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(pago.estado_pago, "LIBERADO")
        pago.save.assert_called_once_with(update_fields=["estado_pago", "fecha_liberacion"])
        self.assertEqual((historial, eventos), (1, 1))

    def test_reintento_liberado_no_duplica_movimientos(self):
        """Comprueba respuesta idempotente sin escrituras cuando el pago ya está liberado."""
        respuesta, pago, historial, eventos = self.ejecutar(estado_pago="LIBERADO")
        self.assertEqual(respuesta.status_code, 200)
        pago.save.assert_not_called()
        self.assertEqual((historial, eventos), (0, 0))

    def test_bloqueos_existentes_impiden_liberacion(self):
        """Comprueba bloqueos por reversa, reclamo, entrega o estados incompatibles."""
        escenarios = (
            {"reversa": True}, {"reclamo": True},
            {"estado_entrega": "CON_OBSERVACIONES"},
            {"estado_prestacion": "CANCELADA"},
            {"estado_prestacion": "POSTERGADA"},
            {"estado_pago": "PENDIENTE_VERIFICACION"},
        )
        for escenario in escenarios:
            with self.subTest(escenario=escenario):
                respuesta, pago, historial, eventos = self.ejecutar(**escenario)
                self.assertEqual(respuesta.status_code, 409)
                pago.save.assert_not_called()
                self.assertEqual((historial, eventos), (0, 0))
