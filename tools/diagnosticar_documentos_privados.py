r"""Auditoria no destructiva de referencias y archivos privados.

Ejecutar desde la raiz: python .\tools\diagnosticar_documentos_privados.py
Requiere el entorno virtual y las variables habituales del backend.
No descarga, crea, restaura ni modifica archivos o filas de PostgreSQL.
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.core.files.storage import default_storage  # noqa: E402
from django.http import Http404  # noqa: E402
from profesionales.archivos_privados import referencia_autorizada  # noqa: E402
from profesionales.models import DocumentoProfesional, ValidacionDocumento  # noqa: E402

print("\n===== SKILLY - AUDITORIA DE DOCUMENTOS REALES =====")
print("ALMACENAMIENTO:", type(default_storage).__name__)
print("OPERACION: SOLO LECTURA")

documentos = DocumentoProfesional.objects.order_by("id_documento")
for doc in documentos.iterator():
    print("\nDOCUMENTO:", doc.id_documento)
    print("PROFESIONAL:", doc.id_profesional_id)
    print("TIPO / ESTADO:", doc.tipo_documento, "/", doc.estado)
    print("NOMBRE ORIGINAL:", doc.nombre_archivo)
    print("REFERENCIA:", doc.referencia_archivo)
    asociaciones = list(
        ValidacionDocumento.objects.filter(id_documento=doc)
        .values_list("id_validacion_id", "estado_revision")
    )
    print("REVISIONES:", asociaciones)
    try:
        referencia, _ = referencia_autorizada(doc)
        print("RUTA AUTORIZADA: SI")
        print("ARCHIVO FISICO EXISTE:", bool(default_storage.exists(referencia)))
    except Http404:
        print("RUTA AUTORIZADA: NO (referencia fuera del almacenamiento permitido)")

print("\nCAMBIOS POSTGRESQL: 0")
print("CAMBIOS DE ARCHIVOS: 0")
