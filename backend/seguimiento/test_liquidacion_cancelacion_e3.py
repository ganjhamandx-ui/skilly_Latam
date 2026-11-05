import unittest
from decimal import Decimal
from .politica_liquidacion_cancelacion_e3 import proyectar_liquidacion


class LiquidacionCancelacionE3Tests(unittest.TestCase):
    def calc(self, **kwargs):
        datos = dict(monto_total='250000', monto_trabajo='0', porcentaje='5',
                     origen='ORGANIZACION', decision='INJUSTIFICADA')
        datos.update(kwargs)
        return proyectar_liquidacion(**datos)

    def test_5_por_ciento_proyectado_sin_cobro(self):
        resultado = self.calc()
        self.assertEqual(resultado['cargo_teorico'], Decimal('12500'))
        self.assertEqual(resultado['cargo_ejecutado'], Decimal('0'))
        self.assertEqual(resultado['devolucion_propuesta'], Decimal('250000'))

    def test_justificada_sin_penalizacion(self):
        self.assertEqual(self.calc(decision='JUSTIFICADA')['cargo_teorico'], 0)

    def test_profesional_sin_descuento_monetario(self):
        self.assertEqual(self.calc(origen='PROFESIONAL')['cargo_teorico'], 0)

    def test_trabajo_probado_reduce_base(self):
        resultado = self.calc(monto_trabajo='100000')
        self.assertEqual(resultado['cargo_teorico'], Decimal('7500'))
        self.assertEqual(resultado['devolucion_propuesta'], Decimal('150000'))

    def test_sin_pago_no_hay_cargo(self):
        self.assertEqual(self.calc(monto_total='0')['cargo_teorico'], 0)

    def test_rechazo_sin_devolucion_propuesta(self):
        self.assertIsNone(self.calc(decision='RECHAZAR_SOLICITUD')['devolucion_propuesta'])

    def test_impide_monto_trabajo_superior_a_total(self):
        with self.assertRaises(ValueError): self.calc(monto_trabajo='250001')

    def test_rechaza_porcentaje_fuera_de_rango(self):
        with self.assertRaises(ValueError): self.calc(porcentaje='110')

    def test_rechaza_nan(self):
        with self.assertRaises(ValueError): self.calc(monto_total='NaN')

    def test_nuevo_porcentaje_no_modifica_historicos_calculados(self):
        anterior = self.calc()
        nuevo = self.calc(porcentaje='7')
        self.assertEqual(anterior['cargo_teorico'], Decimal('12500'))
        self.assertEqual(nuevo['cargo_teorico'], Decimal('17500'))
