import unittest
from decimal import Decimal
from seguimiento.politica_liquidacion_final_e3 import calcular_liquidacion

class PoliticaLiquidacionFinalE3Test(unittest.TestCase):
    def calc(self, **override):
        datos=dict(total=250000,trabajo=0,porcentaje=5,decision='INJUSTIFICADA',
                   origen='ORGANIZACION',cargo_solicitado=12500,aceptacion_previa=True)
        datos.update(override)
        return calcular_liquidacion(**datos)
    def test_cargo_5(self):
        x=self.calc();self.assertEqual(x['cargo_autorizado'],Decimal('12500'))
        self.assertEqual(x['devolucion_autorizada'],Decimal('237500'))
    def test_config_no_recalcula_aceptado(self):
        self.assertEqual(self.calc()['porcentaje_contratado'],Decimal('5'))
    def test_justificada_sin_cargo(self):
        self.assertEqual(self.calc(decision='JUSTIFICADA',cargo_solicitado=0)['devolucion_autorizada'],Decimal('250000'))
    def test_justificada_bloquea_cargo(self):
        with self.assertRaises(ValueError):self.calc(decision='JUSTIFICADA')
    def test_profesional_sin_cargo(self):
        with self.assertRaises(ValueError):self.calc(origen='PROFESIONAL')
    def test_no_aceptado_sin_cargo(self):
        with self.assertRaises(ValueError):self.calc(aceptacion_previa=False)
    def test_excepcion_legal(self):
        with self.assertRaises(ValueError):self.calc(excepcion_legal=True)
    def test_trabajo_parcial(self):
        x=self.calc(trabajo=100000,cargo_solicitado=7500)
        self.assertEqual(x['devolucion_autorizada'],Decimal('142500'))
    def test_cargo_bajo_el_tope(self):
        self.assertEqual(self.calc(cargo_solicitado=5000)['devolucion_autorizada'],Decimal('245000'))
    def test_maximo_bloqueado(self):
        with self.assertRaises(ValueError):self.calc(cargo_solicitado=12501)
    def test_valores_negativos(self):
        with self.assertRaises(ValueError):self.calc(total=-250000)
    def test_nan(self):
        with self.assertRaises(ValueError):self.calc(porcentaje='NaN')
    def test_trabajo_superior_al_total(self):
        with self.assertRaises(ValueError):self.calc(trabajo=300000)
    def test_rechazo_no_liquidable(self):
        with self.assertRaises(ValueError):self.calc(decision='RECHAZAR_SOLICITUD')
