
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from acceso.authentication import SesionSkillyAuthentication
from profesionales.models import (
    DocumentoProfesional,
    SolicitudValidacion,
    Profesional,
)

from acceso.permissions import EsAdministracionSkilly


class DescargarDocumentoValidacionAdminView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]
    http_method_names = ["get", "options"]

    def get(self, request, id_validacion, id_documento):

        if getattr(request.user, "rol", None) != "ADMIN_SKILLY":
            return Response(
                {"mensaje": "Acceso exclusivo de administracion."},
                status=status.HTTP_403_FORBIDDEN,
            )

        solicitud = SolicitudValidacion.objects.filter(
            id_validacion=id_validacion
        ).first()

        if solicitud is None:
            raise Http404

        # El documento debe pertenecer al profesional
        # de la solicitud consultada.
        #
        # No exigimos una asociacion antigua en
        # ValidacionDocumento para permitir descargar
        # versiones subidas posteriormente.
        documento = DocumentoProfesional.objects.filter(
            id_documento=id_documento,
            id_profesional=solicitud.id_profesional,
        ).first()

        if documento is None:
            raise Http404

        referencia = documento.referencia_archivo or ""

        # Mantener la proteccion del almacenamiento privado.
        prefijo = (
            "skilly/documentos_profesionales/"
            + str(solicitud.id_profesional_id)
            + "/"
        )

        if (
            not referencia.startswith(prefijo)
            or ".." in referencia.split("/")
            or chr(92) in referencia
        ):
            raise Http404

        extension = referencia.rsplit(".", 1)[-1].lower()

        tipos = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

        tipo = tipos.get(extension)

        if tipo is None or not default_storage.exists(referencia):
            raise Http404

        respuesta = FileResponse(
            default_storage.open(referencia, "rb"),
            as_attachment=True,
            filename=documento.nombre_archivo,
            content_type=tipo,
        )

        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"

        return respuesta
