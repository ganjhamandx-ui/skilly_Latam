"""Descarga protegida de comprobantes de transferencia bancarios nuevos."""
from pathlib import PurePosixPath
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly
from pagos.models import Pago

class ComprobanteTransferenciaAdministracionView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request, id_pago):
        pago = Pago.objects.filter(id_pago=id_pago, metodo_pago="TRANSFERENCIA").first()
        if pago is None:
            raise Http404()
        ruta = pago.comprobante_transferencia or ""
        # PurePosixPath no interpreta las barras de Windows. No permitir que
        # una referencia antigua/invalida salga de la carpeta de comprobantes,
        # ni abrir flujos alternativos NTFS mediante dos puntos.
        if not isinstance(ruta, str) or any(c in ruta for c in ("\\", "\x00", ":")):
            raise Http404()
        ruta_normalizada = PurePosixPath(ruta)
        if (not ruta.startswith("comprobantes_transferencia_privados/")
                or any(p in {"", ".", ".."} for p in ruta.split("/"))
                or len(ruta_normalizada.parts) != 2):
            raise Http404()
        if not default_storage.exists(ruta):
            raise Http404()
        extension = ruta_normalizada.suffix.lower()
        if extension not in {".pdf", ".jpg", ".png"}:
            raise Http404()
        tipo = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".png": "image/png"}[extension]
        try:
            archivo = default_storage.open(ruta, "rb")
        except (FileNotFoundError, OSError):
            # El almacenamiento puede cambiar entre exists() y open().
            raise Http404() from None
        respuesta = FileResponse(archivo, as_attachment=True,
                                 filename=f"comprobante_pago_{id_pago}{extension}", content_type=tipo)
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        respuesta["Referrer-Policy"] = "no-referrer"
        return respuesta
