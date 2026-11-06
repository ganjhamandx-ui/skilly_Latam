"""Permisos reales de las vistas y firmas, con filas en memoria y archivos temporales.

No sustituye las consultas/HTTP de PostgreSQL aislado. El filtro en memoria aplica
los campos enviados por la vista para detectar la omision de una condicion de pertenencia.
"""
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from solicitudes.referencias import SEGUIMIENTO_SOLICITUD_SALT
from seguimiento.entregables_multiservicio_e3 import (
    DescargaEntregaAdminE3View, DescargaEntregaEmpresaE3View,
    DescargaEntregaProfesionalE3View,
)


class FilasEnMemoria:
    def __init__(self, *filas):
        self.filas = filas

    def select_related(self, *campos):
        return self

    def filter(self, **condiciones):
        def valor(fila, campo):
            for parte in campo.split("__"):
                fila = getattr(fila, parte)
            return fila
        return FilasEnMemoria(*(fila for fila in self.filas
            if all(valor(fila, campo) == esperado for campo, esperado in condiciones.items())))

    def first(self):
        return next(iter(self.filas), None)


class DescargasPorObjetoTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.usuario = SimpleNamespace(pk=901, estado="ACTIVO", rol="PROFESIONAL")
        self.propietario = SimpleNamespace(pk=902, id_usuario=self.usuario)
        self.otro_usuario = SimpleNamespace(pk=903, estado="ACTIVO", rol="PROFESIONAL")
        self.otro_perfil = SimpleNamespace(pk=904, id_usuario=self.otro_usuario)
        prestacion = SimpleNamespace(
            id_profesional=self.propietario, id_solicitud_id=905,
            id_solicitud=SimpleNamespace(id_contacto_id=906),
        )
        self.archivo = SimpleNamespace(
            id_archivo=907, id_entrega=SimpleNamespace(id_prestacion=prestacion),
            ruta_privada="respaldo.pdf", nombre_original="informe.pdf",
        )
        self.temporal = tempfile.TemporaryDirectory(prefix="skilly_entrega_test_")
        self.addCleanup(self.temporal.cleanup)
        self.storage = FileSystemStorage(location=self.temporal.name)
        self.storage.save(self.archivo.ruta_privada, ContentFile(b"%PDF-1.7\nEntrega sintetica"))

    def referencia(self, *, solicitud=905, contacto=906):
        return signing.dumps({"id_solicitud": solicitud, "id_contacto": contacto},
                             salt=SEGUIMIENTO_SOLICITUD_SALT, compress=True)

    def descargar(self, vista, *, usuario=None, referencia=None, id_archivo=907):
        request = self.factory.get("/descarga-de-prueba/")
        request.session = SessionStore()
        if usuario is not None:
            request.session["id_usuario"] = usuario.pk
        kwargs = {"id_archivo": id_archivo}
        if referencia is not None:
            kwargs["referencia"] = referencia
        with (
            patch("acceso.authentication.Usuario.objects") as usuarios,
            patch("seguimiento.entregables_multiservicio_e3.Profesional.objects",
                  FilasEnMemoria(self.propietario, self.otro_perfil)),
            patch("seguimiento.entregables_multiservicio_e3.ArchivoEntregaE3.objects",
                  FilasEnMemoria(self.archivo)),
            patch("seguimiento.entregables_multiservicio_e3.RAIZ_PRIVADA", Path(self.temporal.name)),
        ):
            usuarios.filter.return_value.first.return_value = usuario
            response = vista.as_view()(request, **kwargs)
            if response.status_code == 200:
                try:
                    self.assertTrue({"private", "no-store"}.issubset(
                        {directiva.strip() for directiva in response["Cache-Control"].split(",")}))
                    self.assertEqual(response["Referrer-Policy"], "no-referrer")
                    self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.7\nEntrega sintetica")
                finally:
                    response.close()
            return response.status_code

    def test_profesional_propietario_descarga_y_ajeno_no(self):
        self.assertEqual(self.descargar(DescargaEntregaProfesionalE3View, usuario=self.usuario), 200)
        self.assertEqual(self.descargar(DescargaEntregaProfesionalE3View, usuario=self.otro_usuario), 404)
        self.assertEqual(self.descargar(DescargaEntregaProfesionalE3View), 403)

    def test_empresa_solo_accede_a_objeto_de_su_solicitud_y_contacto(self):
        self.assertEqual(self.descargar(DescargaEntregaEmpresaE3View, referencia=self.referencia()), 200)
        for referencia in (self.referencia(solicitud=908), self.referencia(contacto=909)):
            self.assertEqual(self.descargar(DescargaEntregaEmpresaE3View, referencia=referencia), 404)

    def test_firma_alterada_y_archivo_inexistente_no_descargan(self):
        self.assertEqual(self.descargar(DescargaEntregaEmpresaE3View, referencia=self.referencia() + "x"), 404)
        self.assertEqual(self.descargar(DescargaEntregaEmpresaE3View, referencia=self.referencia(), id_archivo=999), 404)

    def test_solo_administracion_accede_a_descarga_administrativa(self):
        self.assertEqual(self.descargar(DescargaEntregaAdminE3View, usuario=self.usuario), 403)
        self.assertEqual(self.descargar(DescargaEntregaAdminE3View), 403)
        admin = SimpleNamespace(pk=910, estado="ACTIVO", rol="ADMIN_SKILLY")
        self.assertEqual(self.descargar(DescargaEntregaAdminE3View, usuario=admin), 200)
