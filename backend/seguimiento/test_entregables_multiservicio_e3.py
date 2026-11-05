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
    def test_entrega_tecnica_automatica_por_descripcion_servicio(self):
        from types import SimpleNamespace
        serv=SimpleNamespace(nombre='Desarrollo de paginas web para pequenas empresas',
            descripcion='Sitio web corporativo',alcance='Entrega de codigo fuente',
            id_categoria=SimpleNamespace(nombre='Tecnologia e Informatica'))
        p=politica_entrega_servicio(serv)
        self.assertEqual(p['tipo'],'TECNICO')
        self.assertIn('.zip',p['formatos_permitidos'])
    def test_asesoria_documental_no_solicita_codigo(self):
        from types import SimpleNamespace
        serv=SimpleNamespace(nombre='Asesoria contable',descripcion='Informe tributario',
            alcance='Excel y PDF',id_categoria=SimpleNamespace(nombre='Finanzas'))
        p=politica_entrega_servicio(serv)
        self.assertEqual(p['tipo'],'DOCUMENTAL')
        self.assertNotIn('.zip',p['formatos_permitidos'])
    def test_sesion_sin_documentos_es_descriptiva(self):
        from types import SimpleNamespace
        serv=SimpleNamespace(nombre='Mentoria de liderazgo',descripcion='Sesion virtual',
            alcance='Reunion por videollamada',id_categoria=SimpleNamespace(nombre='Recursos Humanos'))
        p=politica_entrega_servicio(serv)
        self.assertFalse(p['permitir_archivos'])
    def test_adjunto_doc_no_acepta_zip(self):
        f=SimpleUploadedFile('codigo.zip',b'PK\x03\x04contenido',content_type='application/zip')
        with self.assertRaises(ValueError): validar_archivo(f,['.pdf','.docx'])
    def test_archivo_pdf_valido(self):
        f=SimpleUploadedFile('informe.pdf',b'%PDF-1.7\nprueba',content_type='application/pdf')
        self.assertEqual(validar_archivo(f)[1],'.pdf')
    def test_rechaza_extension_ejecutable(self):
        f=SimpleUploadedFile('ejecutable.exe',b'ABCD')
        with self.assertRaises(ValueError): validar_archivo(f)
    def test_rechaza_pdf_con_firma_invalida(self):
        f=SimpleUploadedFile('informe.pdf',b'NO ES PDF')
        with self.assertRaises(ValueError): validar_archivo(f)
    def test_rechaza_jpg_con_firma_invalida(self):
        f=SimpleUploadedFile('foto.jpg',b'NO ES JPG')
        with self.assertRaises(ValueError): validar_archivo(f)
    def test_limites(self):
        self.assertEqual(MAX_ARCHIVOS,3)
        self.assertEqual(MAX_BYTES,10*1024*1024)
    def test_archivos_profesional_requieren_sesion_y_rol(self):
        self.assertIn(EsProfesional,RegistrarEntregaConArchivosE3View.permission_classes)
        self.assertIn(EsProfesional,DescargaEntregaProfesionalE3View.permission_classes)
    def test_descarga_empresa_valida_referencia_en_vista(self):
        import inspect
        self.assertIn('leer_referencia_seguimiento',inspect.getsource(DescargaEntregaEmpresaE3View.get))
