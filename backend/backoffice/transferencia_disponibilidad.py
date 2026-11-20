"""Consulta limitada de habilitación bancaria para el flujo empresarial.

No crea pagos ni registra comprobantes. La cuenta principal solo se entrega
si la referencia firmada corresponde a una prestación habilitada para contratar.
"""
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from coordinacion.models import PrestacionServicio
from config.identidad_bancaria import identidad_bancaria_autorizada
from solicitudes.referencias import leer_referencia_seguimiento
from pagos.models import Pago


class DisponibilidadTransferenciaEmpresaView(APIView):
    """Consulta habilitación y cuenta principal para una referencia empresarial válida.

    Este adaptador se conserva en las pruebas de identidad bancaria; la ruta
    empresarial está vinculada al adaptador del módulo pagos.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, referencia):
        """Comprueba requisitos de contratación antes de devolver la cuenta principal.

        Args:
            request: Petición HTTP; la autorización utiliza la referencia firmada.
            referencia: Referencia que vincula la solicitud y su contacto empresarial.

        Returns:
            Response: Disponibilidad y cuenta principal activa cuando corresponde;
            400 para referencia inválida, 404 si falta la prestación y 503 cuando
            la identidad de la conexión no está autorizada.

        Raises:
            DatabaseError: Si falla una consulta de prestación, pago o cuenta.
        """
        datos = leer_referencia_seguimiento(referencia)
        if datos is None:
            return Response({'mensaje': 'Referencia de seguimiento no válida.'}, status=400)

        prestacion = (PrestacionServicio.objects
            .filter(id_solicitud_id=datos['id_solicitud'],
                    id_solicitud__id_contacto_id=datos['id_contacto'])
            .first())
        if prestacion is None:
            return Response({'mensaje': 'Prestación no encontrada para esta referencia.'}, status=404)

        if (prestacion.estado != 'PENDIENTE_CONTRATACION'
                or not prestacion.condiciones_comunicadas):
            return Response({'disponible': False,
                'mensaje': 'La contratación todavía no habilita pagos por transferencia.'})

        if Pago.objects.filter(id_prestacion=prestacion).exists():
            return Response({'disponible': False,
                'mensaje': 'Ya existe una operación de pago; consulta su estado.'})

        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database(), current_schema(), current_user')
            identidad = cursor.fetchone()
            if not identidad_bancaria_autorizada(connection, identidad):
                return Response({'disponible': False,
                    'mensaje': 'Transferencia no disponible en esta instalación.'}, status=503)
            cursor.execute("""SELECT EXISTS (
                SELECT 1 FROM skilly.cuenta_bancaria_skilly
                WHERE activa = TRUE AND principal = TRUE)""")
            principal_disponible = bool(cursor.fetchone()[0])

        if not principal_disponible:
            return Response({'disponible': False,
                'mensaje': 'Transferencia no disponible: SKILLY no tiene una cuenta bancaria principal activa.'})

        with connection.cursor() as cursor:
            cursor.execute("""SELECT id_cuenta, titular, rut_titular, banco,
                              tipo_cuenta, numero_cuenta, correo
                              FROM skilly.cuenta_bancaria_skilly
                              WHERE activa IS TRUE AND principal IS TRUE""")
            fila = cursor.fetchone()
        if not fila:
            return Response({'disponible': False,
                'mensaje': 'No hay una cuenta bancaria principal disponible.'})
        return Response({'disponible': True,
            'cuenta': dict(zip(('id_cuenta', 'titular', 'rut_titular', 'banco',
                                'tipo_cuenta', 'numero_cuenta', 'correo'), fila))})
