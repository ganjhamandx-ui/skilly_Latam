"""Pruebas focalizadas puras: sin PostgreSQL, cobros ni Webpay."""
import unittest
from decimal import Decimal
from .politica_conciliacion_e3 import desglose_parcial, ConciliacionInvalida

class DesgloseParcialE3Tests(unittest.TestCase):
    def caso(self,**cambio):
        datos=dict(total='250000.00', trabajo='100000.00', cargo='7500.00',
            devolucion='142500.00', monto_reversa='142500.00',
            metodo_pago='TRANSFERENCIA',estado_pago='RETENIDO',
            estado_verificacion='VERIFICADO',estado_reversa='SOLICITADA')
        datos.update(cambio)
        return desglose_parcial(**datos)
    def test_desglose_cuadra(self):
        p=self.caso()
        self.assertEqual(p['remanente_pendiente_distribucion'],Decimal('107500.00'))
        self.assertEqual(p['devolucion_pendiente'],Decimal('142500.00'))
    def test_cargo_sin_trabajo(self):
        p=self.caso(trabajo='0',cargo='12500',devolucion='237500',monto_reversa='237500')
        self.assertEqual(p['remanente_pendiente_distribucion'],Decimal('12500.00'))
    def test_webpay_documental(self):
        self.assertEqual(self.caso(metodo_pago='WEBPAY_PLUS')['metodo_pago'],'WEBPAY_PLUS')
    def test_no_dev_total(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(trabajo=0,cargo=0,devolucion=250000,monto_reversa=250000)
    def test_no_dev_cero(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(devolucion=0,monto_reversa=0)
    def test_no_admite_total_incorrecto(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(cargo=7501)
    def test_no_admite_reversa_monto_diferente(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(monto_reversa=142499)
    def test_pago_debe_retenido(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(estado_pago='LIBERADO')
    def test_reversa_debe_pendiente(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(estado_reversa='SIMULADA')
    def test_valores_negativos(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(trabajo=-1)
    def test_nan(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(cargo='NaN')
    def test_decimales_invalidos(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(cargo='7500.001')
    def test_metodo_no_permitido(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(metodo_pago='EFECTIVO')
    def test_monto_retenido_verificado(self):
        with self.assertRaises(ConciliacionInvalida):self.caso(estado_verificacion='PENDIENTE')
