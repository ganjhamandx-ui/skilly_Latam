"""Pruebas focalizadas, no destructivas. Sin conectar a PostgreSQL."""
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from acceso.permissions import EsProfesional, EsAdministracionSkilly
from .entregables_multiservicio_e3 import (
    politica_entrega_servicio, validar_archivo,
    RegistrarEntregaConArchivosE3View, DescargaEntregaEmpresaE3View,
    DescargaEntregaProfesionalE3View, MAX_ARCHIVOS, MAX_BYTES,
)

class EntregasMultiservicioTests(SimpleTestCase):
    """Cubre clasificación de servicios y validación de archivos de entrega."""

    def test_entrega_tecnica_automatica_por_descripcion_servicio(self):
        """Verifica el escenario: entrega tecnica automatica por descripción servicio."""
        from types import SimpleNamespace
        serv=SimpleNamespace(nombre='Desarrollo de paginas web para pequenas empresas',
            descripcion='Sitio web corporativo',alcance='Entrega de codigo fuente',
            id_categoria=SimpleNamespace(nombre='Tecnologia e Informatica'))
        p=politica_entrega_servicio(serv)
        self.assertEqual(p['tipo'],'TECNICO')
        self.assertIn('.zip',p['formatos_permitidos'])
    def test_asesoria_documental_no_solicita_codigo(self):
        """Verifica el escenario: asesoria documental no solicita código."""
        from types import SimpleNamespace
        serv=SimpleNamespace(nombre='Asesoria contable',descripcion='Informe tributario',
            alcance='Excel y PDF',id_categoria=SimpleNamespace(nombre='Finanzas'))
        p=politica_entrega_servicio(serv)
        self.assertEqual(p['tipo'],'DOCUMENTAL')
        self.assertNotIn('.zip',p['formatos_permitidos'])
    def test_sesion_sin_documentos_es_descriptiva(self):
        """Verifica el escenario: sesión sin documentos es descriptiva."""
        from types import SimpleNamespace
        serv=SimpleNamespace(nombre='Mentoria de liderazgo',descripcion='Sesion virtual',
            alcance='Reunion por videollamada',id_categoria=SimpleNamespace(nombre='Recursos Humanos'))
        p=politica_entrega_servicio(serv)
        self.assertFalse(p['permitir_archivos'])
    def test_adjunto_doc_no_acepta_zip(self):
        """Verifica el escenario: adjunto doc no acepta ZIP."""
        f=SimpleUploadedFile('codigo.zip',b'PK\x03\x04contenido',content_type='application/zip')
        with self.assertRaises(ValueError): validar_archivo(f,['.pdf','.docx'])
    def test_archivo_pdf_valido(self):
        """Verifica el escenario: archivo PDF válido."""
        f=SimpleUploadedFile('informe.pdf',b'%PDF-1.7\nprueba',content_type='application/pdf')
        self.assertEqual(validar_archivo(f)[1],'.pdf')
    def test_rechaza_extension_ejecutable(self):
        """Verifica el escenario: rechaza extension ejecutable."""
        f=SimpleUploadedFile('ejecutable.exe',b'ABCD')
        with self.assertRaises(ValueError): validar_archivo(f)
    def test_rechaza_pdf_con_firma_invalida(self):
        """Verifica el escenario: rechaza PDF con firma inválida."""
        f=SimpleUploadedFile('informe.pdf',b'NO ES PDF')
        with self.assertRaises(ValueError): validar_archivo(f)
    def test_rechaza_jpg_con_firma_invalida(self):
        """Verifica el escenario: rechaza JPG con firma inválida."""
        f=SimpleUploadedFile('foto.jpg',b'NO ES JPG')
        with self.assertRaises(ValueError): validar_archivo(f)
    def test_limites(self):
        """Verifica el escenario: límites."""
        self.assertEqual(MAX_ARCHIVOS,3)
        self.assertEqual(MAX_BYTES,10*1024*1024)
    def test_archivos_profesional_requieren_sesion_y_rol(self):
        """Verifica el escenario: archivos profesional requieren sesión y rol."""
        self.assertIn(EsProfesional,RegistrarEntregaConArchivosE3View.permission_classes)
        self.assertIn(EsProfesional,DescargaEntregaProfesionalE3View.permission_classes)
    def test_descarga_empresa_valida_referencia_en_vista(self):
        """Verifica el escenario: descarga empresa válida referencia en vista."""
        import inspect
        self.assertIn('leer_referencia_seguimiento',inspect.getsource(DescargaEntregaEmpresaE3View.get))
