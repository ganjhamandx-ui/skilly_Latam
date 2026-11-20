"""Entrega documentos privados solo a personal administrativo autorizado."""

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
    """Permite descargar documentos del profesional asociado a una solicitud de validación."""
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]
    http_method_names = ["get", "options"]

    def get(self, request, id_validacion, id_documento):

        """Entrega un documento privado al personal con rol ADMIN_SKILLY.

        La pertenencia se comprueba contra el profesional de la solicitud; no se
        exige un vínculo ValidacionDocumento concreto ni un estado de revisión.

        Args:
            request: Petición administrativa autenticada.
            id_validacion (int): Solicitud que determina el propietario esperado.
            id_documento (int): Documento de ese profesional.

        Returns:
            FileResponse | Response: Adjunto privado sin caché o respuesta 403 si
            el rol del usuario no es ADMIN_SKILLY.

        Raises:
            Http404: Si faltan registros, la ruta es inválida, la extensión no
                está admitida o el archivo no existe.
            OSError: Si falla la apertura en el almacenamiento.
        """
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
