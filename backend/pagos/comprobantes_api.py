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
        ruta_normalizada = PurePosixPath(ruta)
        if (not ruta.startswith("comprobantes_transferencia_privados/")
                or ".." in ruta_normalizada.parts
                or len(ruta_normalizada.parts) != 2):
            raise Http404()
        if not default_storage.exists(ruta):
            raise Http404()
        extension = ruta_normalizada.suffix.lower()
        if extension not in {".pdf", ".jpg", ".png"}:
            raise Http404()
        tipo = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".png": "image/png"}[extension]
        return FileResponse(default_storage.open(ruta, "rb"), as_attachment=True,
                            filename=f"comprobante_pago_{id_pago}{extension}", content_type=tipo)
