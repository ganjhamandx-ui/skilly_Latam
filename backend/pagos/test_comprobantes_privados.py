"""Descargas privadas: despacho DRF y almacenamiento temporal, ORM simulado."""
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from pagos.comprobantes_api import ComprobanteTransferenciaAdministracionView


class ComprobantesPrivadosTests(SimpleTestCase):
    """Comprueba autorización y aislamiento de comprobantes con almacenamiento temporal y ORM simulado."""
    def setUp(self):
        """Prepara un administrador ficticio y un PDF sintético en almacenamiento temporal."""
        self.factory = APIRequestFactory()
        self.usuario = SimpleNamespace(pk=901, estado="ACTIVO", rol="ADMIN_SKILLY")
        self.ruta = "comprobantes_transferencia_privados/prueba.pdf"
        self.temporal = tempfile.TemporaryDirectory(prefix="skilly_comprobante_test_")
        self.addCleanup(self.temporal.cleanup)
        self.storage = FileSystemStorage(location=self.temporal.name)
        self.storage.save(self.ruta, ContentFile(b"%PDF-1.7\nPrueba sintetica"))

    def descargar(self, *, ruta=None, sesion=True, pago=True, fallo_apertura=False):
        """Despacha la descarga real sustituyendo identidad, pago y almacenamiento.

        Args:
            ruta: Referencia almacenada alternativa; None usa el PDF de preparación.
            sesion: Indica si la petición contiene identidad en una sesión firmada.
            pago: Indica si la consulta simulada encuentra el pago.
            fallo_apertura: Simula que el archivo desaparece antes de abrirlo.

        Returns:
            HttpResponse: Respuesta de descarga o rechazo de la vista.
        """
        request = self.factory.get("/api/pagos/administracion/902/comprobante/")
        request.session = SessionStore()
        if sesion:
            request.session["id_usuario"] = self.usuario.pk
        with (
            patch("acceso.authentication.Usuario.objects") as usuarios,
            patch("pagos.comprobantes_api.Pago.objects") as pagos,
            patch("pagos.comprobantes_api.default_storage", self.storage),
        ):
            usuarios.filter.return_value.first.return_value = self.usuario
            pagos.filter.return_value.first.return_value = (
                SimpleNamespace(comprobante_transferencia=self.ruta if ruta is None else ruta)
                if pago else None
            )
            if fallo_apertura:
                with patch.object(self.storage, "open", side_effect=FileNotFoundError()):
                    return ComprobanteTransferenciaAdministracionView.as_view()(request, id_pago=902)
            response = ComprobanteTransferenciaAdministracionView.as_view()(request, id_pago=902)
            if response.status_code == 200:
                pagos.filter.assert_called_once_with(id_pago=902, metodo_pago="TRANSFERENCIA")
            return response

    def test_admin_descarga_contenido_y_cabeceras_privadas(self):
        """Comprueba contenido sintético, descarga como adjunto y cabeceras de privacidad."""
        response = self.descargar()
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "private, no-store")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
            self.assertEqual(response["Referrer-Policy"], "no-referrer")
            self.assertIn("attachment", response["Content-Disposition"])
            self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.7\nPrueba sintetica")
        finally:
            response.close()

    def test_anonimo_y_profesional_no_descargan(self):
        """Comprueba que la descarga requiera una sesión administrativa."""
        self.assertEqual(self.descargar(sesion=False).status_code, 403)
        self.usuario.rol = "PROFESIONAL"
        self.assertEqual(self.descargar().status_code, 403)

    def test_pago_inexistente_no_descarga(self):
        """Comprueba el 404 cuando no se encuentra el pago solicitado."""
        self.assertEqual(self.descargar(pago=False).status_code, 404)

    def test_referencias_invalidas_no_abren_almacenamiento(self):
        """Rechaza rutas ambiguas, ajenas o no admitidas antes de abrir el almacenamiento."""
        rutas = (
            "comprobantes_transferencia_privados/../otro.pdf",
            "comprobantes_transferencia_privados/..\\otro.pdf",
            "comprobantes_transferencia_privados//prueba.pdf",
            "comprobantes_transferencia_privados/./prueba.pdf",
            "comprobantes_transferencia_privados/prueba.pdf:oculto.pdf",
            "comprobantes_transferencia_privados/prueba\x00.pdf",
            "/comprobantes_transferencia_privados/prueba.pdf",
            "skilly/documentos_profesionales/901/prueba.pdf",
            "comprobantes_transferencia_privados/prueba.html",
        )
        for ruta in rutas:
            with self.subTest(caso=rutas.index(ruta)), patch.object(self.storage, "open") as abrir:
                self.assertEqual(self.descargar(ruta=ruta).status_code, 404)
                abrir.assert_not_called()

    def test_archivo_ausente_o_desaparecido_responde_404(self):
        """Comprueba el 404 tanto ante ausencia como ante desaparición durante la apertura."""
        self.assertEqual(self.descargar(ruta="comprobantes_transferencia_privados/ausente.pdf").status_code, 404)
        self.assertEqual(self.descargar(fallo_apertura=True).status_code, 404)
