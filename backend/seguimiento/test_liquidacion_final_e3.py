"""Comprueba reglas de la liquidación final sin efectuar operaciones de pago."""

import unittest
from decimal import Decimal
from seguimiento.politica_liquidacion_final_e3 import calcular_liquidacion

class PoliticaLiquidacionFinalE3Test(unittest.TestCase):
    """Cubre límites y excepciones de la liquidación final calculada."""

    def calc(self, **override):
        """Ejecuta la política con valores base y reemplazos controlados."""
        datos=dict(total=250000,trabajo=0,porcentaje=5,decision='INJUSTIFICADA',
                   origen='ORGANIZACION',cargo_solicitado=12500,aceptacion_previa=True)
        datos.update(override)
        return calcular_liquidacion(**datos)
    def test_cargo_5(self):
        """Verifica el escenario: cargo 5."""
        x=self.calc();self.assertEqual(x['cargo_autorizado'],Decimal('12500'))
        self.assertEqual(x['devolucion_autorizada'],Decimal('237500'))
    def test_config_no_recalcula_aceptado(self):
        """Verifica el escenario: config no recalcula aceptado."""
        self.assertEqual(self.calc()['porcentaje_contratado'],Decimal('5'))
    def test_justificada_sin_cargo(self):
        """Verifica el escenario: justificada sin cargo."""
        self.assertEqual(self.calc(decision='JUSTIFICADA',cargo_solicitado=0)['devolucion_autorizada'],Decimal('250000'))
    def test_justificada_bloquea_cargo(self):
        """Verifica el escenario: justificada bloquea cargo."""
        with self.assertRaises(ValueError):self.calc(decision='JUSTIFICADA')
    def test_profesional_sin_cargo(self):
        """Verifica el escenario: profesional sin cargo."""
        with self.assertRaises(ValueError):self.calc(origen='PROFESIONAL')
    def test_no_aceptado_sin_cargo(self):
        """Verifica el escenario: no aceptado sin cargo."""
        with self.assertRaises(ValueError):self.calc(aceptacion_previa=False)
    def test_excepcion_legal(self):
        """Verifica el escenario: excepcion legal."""
        with self.assertRaises(ValueError):self.calc(excepcion_legal=True)
    def test_trabajo_parcial(self):
        """Verifica el escenario: trabajo parcial."""
        x=self.calc(trabajo=100000,cargo_solicitado=7500)
        self.assertEqual(x['devolucion_autorizada'],Decimal('142500'))
    def test_cargo_bajo_el_tope(self):
        """Verifica el escenario: cargo bajo el tope."""
        self.assertEqual(self.calc(cargo_solicitado=5000)['devolucion_autorizada'],Decimal('245000'))
    def test_maximo_bloqueado(self):
        """Verifica el escenario: máximo bloqueado."""
        with self.assertRaises(ValueError):self.calc(cargo_solicitado=12501)
    def test_valores_negativos(self):
        """Verifica el escenario: valores negativos."""
        with self.assertRaises(ValueError):self.calc(total=-250000)
    def test_nan(self):
        """Verifica el escenario: NaN."""
        with self.assertRaises(ValueError):self.calc(porcentaje='NaN')
    def test_trabajo_superior_al_total(self):
        """Verifica el escenario: trabajo superior al total."""
        with self.assertRaises(ValueError):self.calc(trabajo=300000)
    def test_rechazo_no_liquidable(self):
        """Verifica el escenario: rechazo no liquidable."""
        with self.assertRaises(ValueError):self.calc(decision='RECHAZAR_SOLICITUD')
