"""Pruebas focalizadas, sin acceso a PostgreSQL ni a proveedores externos."""
import unittest
from pagos.politicas_reversas_e3 import plan_cierre, ReversaInvalida


class CierreReversasE3Tests(unittest.TestCase):
    def parametros(self, **extra):
        base = dict(accion="REGISTRAR_DEVOLUCION_SIMULADA", estado_pago="RETENIDO",
                    estado_verificacion="VERIFICADO", estado_reversa="SOLICITADA",
                    metodo_pago="TRANSFERENCIA", monto_total="25000.00",
                    monto_reversa=None, confirmado=True)
        base.update(extra)
        return base

    def test_cierre_total_se_identifica_como_simulacion(self):
        self.assertEqual(plan_cierre(**self.parametros()), ("SIMULADA", "REVERSA_SIMULADA"))

    def test_rechazo_no_modifica_estado_economico(self):
        self.assertEqual(plan_cierre(**self.parametros(accion="RECHAZAR_SOLICITUD", confirmado=False)),
                         ("RECHAZADA", "RETENIDO"))

    def test_imposible_simular_sin_confirmacion(self):
        with self.assertRaises(ReversaInvalida):
            plan_cierre(**self.parametros(confirmado=False))

    def test_solicitud_cerrada_no_se_resuelve_dos_veces(self):
        with self.assertRaises(ReversaInvalida):
            plan_cierre(**self.parametros(estado_reversa="SIMULADA"))

    def test_imposible_cerrar_pago_liberado(self):
        with self.assertRaises(ReversaInvalida):
            plan_cierre(**self.parametros(estado_pago="LIBERADO"))

    def test_no_se_simula_refund_de_webpay(self):
        with self.assertRaises(ReversaInvalida):
            plan_cierre(**self.parametros(metodo_pago="WEBPAY_PLUS"))

    def test_no_se_cierra_parcial_sin_conciliacion(self):
        with self.assertRaises(ReversaInvalida):
            plan_cierre(**self.parametros(monto_reversa="5000.00"))

    def test_monto_superior_rechazado(self):
        with self.assertRaises(ReversaInvalida):
            plan_cierre(**self.parametros(monto_reversa="27000.00"))

    def test_no_rechazar_pago_no_verificado(self):
        with self.assertRaises(ReversaInvalida):
            plan_cierre(**self.parametros(accion="RECHAZAR_SOLICITUD", estado_verificacion="PENDIENTE"))
