from pathlib import Path
import unittest
R = Path(__file__).resolve().parents[1]
API = (R / 'backend/backoffice/cuentas_bancarias_api.py').read_text(encoding='utf-8')
UI = (R / 'frontend/src/CuentaReceptoraOrganizacion.jsx').read_text(encoding='utf-8')
ROUTES = (R / 'backend/backoffice/cuentas_bancarias_urls.py').read_text(encoding='utf-8')
class PruebaPrivacidad(unittest.TestCase):
    def test_tarjeta_recibe_cuenta_fijada(self):
        self.assertIn('cuentaFijada', UI)
        self.assertIn('if (!cuentaFijada) return null', UI)
    def test_tarjeta_no_presenta_historial(self):
        self.assertNotIn('Cuentas registradas', UI)
        self.assertNotIn('Establecer principal', UI)
        self.assertNotIn('activa', UI)
    def test_sin_endpoint_publico_prematuro(self):
        self.assertNotIn('cuenta-para-transferir', ROUTES)
        self.assertNotIn('CuentaReceptoraOrganizacionView', API)
    def test_api_admin_protegida(self):
        self.assertIn('EsAdministracionSkilly', API)
if __name__ == '__main__': unittest.main()
