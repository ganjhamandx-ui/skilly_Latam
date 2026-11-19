"""Recibe y valida nuevas versiones de documentos profesionales."""

from acceso.authentication import SesionSkillyAuthentication

import uuid
import zipfile

from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, Http404
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.utils import timezone

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from acceso.permissions import EsProfesional
from rest_framework.response import Response
from rest_framework.views import APIView

from profesionales.models import Profesional, DocumentoProfesional, SolicitudValidacion, ValidacionDocumento
from profesionales.serializers import DocumentoProfesionalSerializer


LIMITE_BYTES = 10 * 1024 * 1024
DIRECTORIO_PRIVADO = "skilly/documentos_profesionales/"


def obtener_profesional(request):
    if getattr(request.user, "rol", None) != "PROFESIONAL":
        return None

    return Profesional.objects.filter(
        id_usuario=request.user
    ).first()


def detectar_extension(archivo):
    """Confirma firma y extension, sin ejecutar ni interpretar macros."""
    nombre = str(archivo.name).replace("\\", "/").split("/")[-1]
    extension = ("." + nombre.rsplit(".", 1)[-1].lower()) if "." in nombre else ""
    admitidas = {".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc"}
    if extension not in admitidas:
        return None
    cabecera = archivo.read(16)
    archivo.seek(0)
    if extension == ".pdf" and cabecera.startswith(b"%PDF-"):
        return extension
    if extension in (".jpg", ".jpeg") and cabecera.startswith(bytes.fromhex("FFD8FF")):
        return extension
    if extension == ".png" and cabecera.startswith(bytes.fromhex("89504E470D0A1A0A")):
        return extension
    if extension == ".doc" and cabecera.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return extension
    if extension == ".docx" and zipfile.is_zipfile(archivo):
        try:
            with zipfile.ZipFile(archivo) as paquete:
                nombres = set(paquete.namelist())
                if ("[Content_Types].xml" in nombres and
                        "word/document.xml" in nombres and
                        not any(n.lower().endswith(("vbaproject.bin", ".exe")) for n in nombres) and
                        len(nombres) <= 2000 and
                        sum(x.file_size for x in paquete.infolist()) <= 100 * 1024 * 1024):
                    return extension
        except (zipfile.BadZipFile, OSError, ValueError):
            pass
        finally:
            archivo.seek(0)
    return None


@method_decorator(csrf_protect, name="dispatch")
class SubirDocumentoProfesionalView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post", "options"]

    def post(self, request):
        profesional = obtener_profesional(request)

        if profesional is None:
            return Response(
                {"mensaje": "No existe un perfil profesional autorizado."},
                status=status.HTTP_403_FORBIDDEN,
            )

        archivo = request.FILES.get("archivo")
        tipo = str(request.data.get("tipo_documento") or "").strip()

        if archivo is None:
            return Response(
                {"archivo": ["Selecciona un documento."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not tipo or len(tipo) > 60:
            return Response(
                {"tipo_documento": ["Indica un tipo de documento valido."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if archivo.size <= 0 or archivo.size > LIMITE_BYTES:
            return Response(
                {"archivo": ["El documento debe tener entre 1 byte y 10 MB."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extension = detectar_extension(archivo)

        if extension is None:
            return Response(
                {"archivo": ["Solo se admiten PDF, JPG, PNG, DOCX y DOC validos."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reemplazado_raw = request.data.get("id_documento_reemplazado")
        reemplazado_id = None
        if reemplazado_raw not in (None, ""):
            try:
                reemplazado_id = int(reemplazado_raw)
                if reemplazado_id < 1:
                    raise ValueError
            except (TypeError, ValueError):
                return Response({"mensaje": "Documento a reemplazar inválido."}, status=400)

        nombre_original = str(archivo.name).replace(chr(92), "/").split("/")[-1]

        if not nombre_original or len(nombre_original) > 255:
            return Response(
                {"archivo": ["El nombre del archivo no es valido."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nombre_privado = (
            DIRECTORIO_PRIVADO
            + str(profesional.id_profesional)
            + "/"
            + uuid.uuid4().hex
            + extension
        )

        referencia = None

        # El candado se comprueba dentro de la transacción y sobre el perfil
        # bloqueado, de modo que otra petición concurrente no eluda la regla.
        try:
            with transaction.atomic():
                perfil = (Profesional.objects.select_for_update()
                    .get(pk=profesional.pk))
                solicitud = (SolicitudValidacion.objects
                    .filter(id_profesional=perfil)
                    .order_by("-fecha_solicitud", "-id_validacion")
                    .first())
                validado = perfil.estado_validacion == "APROBADO"

                anterior = None
                if reemplazado_id is not None:
                    # Ninguna sustitución de documentos aprobados ni de archivos
                    # ajenos: solo correcciones rechazadas de la solicitud inicial.
                    if solicitud is None or validado or solicitud.estado == "APROBADA":
                        raise ValueError(
                            "Solo se pueden corregir documentos rechazados durante la revisión inicial."
                        )
                    anterior = (ValidacionDocumento.objects.select_for_update()
                        .select_related("id_documento")
                        .filter(id_validacion=solicitud,
                                id_documento_id=reemplazado_id).first())
                    if (anterior is None
                        or anterior.id_documento.id_profesional_id != perfil.pk
                        or anterior.estado_revision != "RECHAZADA"
                        or anterior.id_documento.tipo_documento != tipo):
                        raise ValueError(
                            "Solo puedes reemplazar el documento rechazado indicado, del mismo tipo."
                        )
                elif solicitud is not None and not validado:
                    raise ValueError(
                        "La documentación inicial ya fue enviada. No puedes agregar documentos nuevos hasta completar la validación profesional. Solo puedes corregir archivos rechazados."
                    )

                # Solo guardamos el archivo una vez comprobados los permisos.
                referencia = default_storage.save(nombre_privado, archivo)
                documento = DocumentoProfesional.objects.create(
                    id_profesional=perfil,
                    tipo_documento=tipo,
                    nombre_archivo=nombre_original,
                    referencia_archivo=referencia,
                    visibilidad="PRIVADO",
                    estado="PENDIENTE",
                    fecha_carga=timezone.now(),
                )

                if anterior is not None:
                    ValidacionDocumento.objects.create(
                        id_validacion=solicitud,
                        id_documento=documento,
                        estado_revision="PENDIENTE",
                        observacion=None,
                    )
                    anterior.estado_revision = "REEMPLAZADA"
                    anterior.save(update_fields=["estado_revision"])
                    anterior.id_documento.estado = "REEMPLAZADO"
                    anterior.id_documento.save(update_fields=["estado"])
                    solicitud.estado = "EN_REVISION"
                    solicitud.fecha_revision = None
                    solicitud.save(update_fields=["estado", "fecha_revision"])

        except ValueError as error:
            if referencia:
                default_storage.delete(referencia)
            return Response({"mensaje": str(error)}, status=status.HTTP_409_CONFLICT)
        except Exception:
            if referencia:
                try:
                    default_storage.delete(referencia)
                except Exception:
                    pass
            raise

        salida = DocumentoProfesionalSerializer(documento)

        return Response(
            {
                "mensaje": "Documento cargado correctamente.",
                "documento": salida.data,
            },
            status=status.HTTP_201_CREATED,
        )


class DescargarDocumentoProfesionalView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    http_method_names = ["get", "head", "options"]

    def get(self, request, id_documento):
        profesional = obtener_profesional(request)

        if profesional is None:
            return Response(
                {"mensaje": "Acceso no autorizado."},
                status=status.HTTP_403_FORBIDDEN,
            )

        documento = DocumentoProfesional.objects.filter(
            id_documento=id_documento,
            id_profesional=profesional,
        ).first()

        if documento is None:
            raise Http404

        referencia = documento.referencia_archivo or ""

        prefijo = (
            DIRECTORIO_PRIVADO
            + str(profesional.id_profesional)
            + "/"
        )

        if (
            not referencia.startswith(prefijo)
            or ".." in referencia.split("/")
            or chr(92) in referencia
        ):
            raise Http404

        if not default_storage.exists(referencia):
            raise Http404

        extension = referencia.rsplit(".", 1)[-1].lower()
        tipos = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "png": "image/png",
            "jpeg": "image/jpeg",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
        }

        tipo_contenido = tipos.get(extension)

        if tipo_contenido is None:
            raise Http404

        respuesta = FileResponse(
            default_storage.open(referencia, "rb"),
            as_attachment=True,
            filename=documento.nombre_archivo,
            content_type=tipo_contenido,
        )

        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"

        return respuesta
