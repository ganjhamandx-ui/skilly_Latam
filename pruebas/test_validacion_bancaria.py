import unittest
from backend.backoffice.validacion_bancaria import (
    validar_cuenta, DatosBancariosInvalidos, normalizar_rut
)
BASE = dict(titular='SKILLY DEMOSTRACION SpA', rut_titular='12.345.678-5',
            banco='BANCO DE PRUEBAS', tipo_cuenta='CORRIENTE',
            numero_cuenta='0000012345', correo='pagos@example.invalid')
class Pruebas(unittest.TestCase):
    def test_valida(self):
        self.assertEqual(validar_cuenta(BASE)['numero_cuenta'], '0000012345')
    def test_obligatorios(self):
        for campo in BASE:
            d=dict(BASE);d[campo]='  '
            with self.assertRaises(DatosBancariosInvalidos):validar_cuenta(d)
    def test_rut(self):
        self.assertEqual(normalizar_rut('12.345.678-5'),'12345678-5')
        with self.assertRaises(DatosBancariosInvalidos):normalizar_rut('12.345.678-0')
    def test_tipo(self):
        with self.assertRaises(DatosBancariosInvalidos): validar_cuenta({**BASE,'tipo_cuenta':'OTRO'})
    def test_numero(self):
        with self.assertRaises(DatosBancariosInvalidos): validar_cuenta({**BASE,'numero_cuenta':'12AB'})
    def test_correo(self):
        with self.assertRaises(DatosBancariosInvalidos): validar_cuenta({**BASE,'correo':'sin-arroba'})
if __name__=='__main__':unittest.main()
