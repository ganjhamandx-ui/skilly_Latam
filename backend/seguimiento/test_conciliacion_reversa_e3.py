"""Pruebas focalizadas puras: sin PostgreSQL, cobros ni Webpay."""
import unittest
from decimal import Decimal
from .politica_conciliacion_e3 import desglose_parcial, ConciliacionInvalida

class DesgloseParcialE3Tests(unittest.TestCase):
    """Cubre consistencia e incompatibilidades del desglose de reversa parcial."""

    def caso(self,**cambio):
        """Construye un desglose base y permite reemplazar valores del escenario."""
        datos=dict(total='250000.00', trabajo='100000.00', cargo='7500.00',
            devolucion='142500.00', monto_reversa='142500.00',
            metodo_pago='TRANSFERENCIA',estado_pago='RETENIDO',
            estado_verificacion='VERIFICADO',estado_reversa='SOLICITADA')
        datos.update(cambio)
        return desglose_parcial(**datos)
    def test_desglose_cuadra(self):
        """Verifica el escenario: desglose cuadra."""
        p=self.caso()
        self.assertEqual(p['remanente_pendiente_distribucion'],Decimal('107500.00'))
        self.assertEqual(p['devolucion_pendiente'],Decimal('142500.00'))
    def test_cargo_sin_trabajo(self):
        """Verifica el escenario: cargo sin trabajo."""
        p=self.caso(trabajo='0',cargo='12500',devolucion='237500',monto_reversa='237500')
        self.assertEqual(p['remanente_pendiente_distribucion'],Decimal('12500.00'))
    def test_webpay_documental(self):
        """Verifica el escenario: Webpay documental."""
        self.assertEqual(self.caso(metodo_pago='WEBPAY_PLUS')['metodo_pago'],'WEBPAY_PLUS')
    def test_no_dev_total(self):
        """Verifica el escenario: no dev total."""
        with self.assertRaises(ConciliacionInvalida):self.caso(trabajo=0,cargo=0,devolucion=250000,monto_reversa=250000)
    def test_no_dev_cero(self):
        """Verifica el escenario: no dev cero."""
        with self.assertRaises(ConciliacionInvalida):self.caso(devolucion=0,monto_reversa=0)
    def test_no_admite_total_incorrecto(self):
        """Verifica el escenario: no admite total incorrecto."""
        with self.assertRaises(ConciliacionInvalida):self.caso(cargo=7501)
    def test_no_admite_reversa_monto_diferente(self):
        """Verifica el escenario: no admite reversa monto diferente."""
        with self.assertRaises(ConciliacionInvalida):self.caso(monto_reversa=142499)
    def test_pago_debe_retenido(self):
        """Verifica el escenario: pago debe retenido."""
        with self.assertRaises(ConciliacionInvalida):self.caso(estado_pago='LIBERADO')
    def test_reversa_debe_pendiente(self):
        """Verifica el escenario: reversa debe pendiente."""
        with self.assertRaises(ConciliacionInvalida):self.caso(estado_reversa='SIMULADA')
    def test_valores_negativos(self):
        """Verifica el escenario: valores negativos."""
        with self.assertRaises(ConciliacionInvalida):self.caso(trabajo=-1)
    def test_nan(self):
        """Verifica el escenario: NaN."""
        with self.assertRaises(ConciliacionInvalida):self.caso(cargo='NaN')
    def test_decimales_invalidos(self):
        """Verifica el escenario: decimales invalidos."""
        with self.assertRaises(ConciliacionInvalida):self.caso(cargo='7500.001')
    def test_metodo_no_permitido(self):
        """Verifica el escenario: método no permitido."""
        with self.assertRaises(ConciliacionInvalida):self.caso(metodo_pago='EFECTIVO')
    def test_monto_retenido_verificado(self):
        """Verifica el escenario: monto retenido verificado."""
        with self.assertRaises(ConciliacionInvalida):self.caso(estado_verificacion='PENDIENTE')
