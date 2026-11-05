from seguimiento.aceptacion_politica_e3 import bloquear_pago_sin_aceptacion
from datetime import datetime
from uuid import uuid4
from django.core.files.storage import default_storage
from django.db import connection
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.db import transaction, connection
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import (
    EsAdministracionSkilly,
    EsProfesional,
)
from backoffice.models import (
    EventoTrazabilidad,
    ParametroSistema,
)
from backoffice.services import registrar_evento_trazabilidad
from coordinacion.models import PrestacionServicio
from marketplace.serializers import normalizar_precio_clp
from profesionales.models import Profesional
from seguimiento.models import (
    Entrega,
    ReclamoPrestacion,
    ResolucionReclamo,
)
from solicitudes.models import (
    Disponibilidad,
    ReservaDisponibilidad,
)
from solicitudes.referencias import (
    leer_referencia_seguimiento,
)
from .models import (
    HistorialEstadoPago,
    Pago,
    ReversaPago,
)
from .serializers import (
    HistorialEstadoPagoAdministracionSerializer,
    IniciarPagoTransferenciaSerializer,
    IniciarReversaPagoSerializer,
    LiberarPagoSerializer,
    VerificarPagoTransferenciaSerializer,
    PagoAdministracionSerializer,
    PagoEstadoComunicableSerializer,
    PagoResumenProfesionalSerializer,
    ReversaPagoSerializer,
)
class IniciarPagoTransferenciaEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    def post(self, request, referencia):
        datos_referencia = leer_referencia_seguimiento(
            referencia
        )
        if datos_referencia is None:
            return Response(
                {
                    "mensaje": (
                        "La referencia de seguimiento "
                        "no es válida."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        entrada_serializer = (
            IniciarPagoTransferenciaSerializer(
                data=request.data
            )
        )
        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        datos = entrada_serializer.validated_data
        comprobante_archivo = datos["comprobante_transferencia"]
        referencia_transaccion = datos.get(
            "referencia_transaccion"
        )
        if referencia_transaccion == "":
            referencia_transaccion = None
        with transaction.atomic():
            prestacion = (
                PrestacionServicio.objects
                .select_for_update()
                .select_related(
                    "id_solicitud",
                    "id_profesional",
                )
                .filter(
                    id_solicitud_id=(
                        datos_referencia[
                            "id_solicitud"
                        ]
                    ),
                    id_solicitud__id_contacto_id=(
                        datos_referencia[
                            "id_contacto"
                        ]
                    ),
                )
                .first()
            )
            if prestacion is None:
                return Response(
                    {
                        "mensaje": (
                            "No existe una prestación "
                            "autorizada para esta referencia."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            pago_existente = (
                Pago.objects
                .select_for_update()
                .filter(
                    id_prestacion=prestacion
                )
                .first()
            )
            if pago_existente is not None:
                if (
                    pago_existente.metodo_pago
                    != "TRANSFERENCIA"
                ):
                    return Response(
                        {
                            "mensaje": (
                                "La prestación ya posee "
                                "un pago iniciado con otro "
                                "medio de pago."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                pago_data = dict(
                    PagoEstadoComunicableSerializer(
                        pago_existente
                    ).data
                )
                pago_data["metodo_pago"] = (
                    pago_existente.metodo_pago
                )
                pago_data["estado_verificacion"] = (
                    pago_existente.estado_verificacion
                )
                return Response(
                    {
                        "mensaje": (
                            "La transferencia ya se "
                            "encontraba registrada."
                        ),
                        "pago": pago_data,
                    },
                    status=status.HTTP_200_OK,
                )
            try:
                bloquear_pago_sin_aceptacion(prestacion)
            except ValueError as exc:
                return Response({'mensaje': str(exc)}, status=status.HTTP_409_CONFLICT)
            if (
                prestacion.estado
                != "PENDIENTE_CONTRATACION"
            ):
                return Response(
                    {
                        "mensaje": (
                            "La prestación no se encuentra "
                            "pendiente de contratación."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            condiciones = str(
                prestacion.condiciones_comunicadas
                or ""
            ).strip()
            if not condiciones:
                return Response(
                    {
                        "mensaje": (
                            "Skilly debe comunicar las "
                            "condiciones de la prestación "
                            "antes de iniciar el pago."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            servicio = (
                prestacion.id_solicitud.id_servicio
            )
            if servicio is None:
                return Response(
                    {
                        "mensaje": (
                            "La solicitud no posee un "
                            "servicio asociado para "
                            "determinar el precio."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if (
                servicio.id_profesional_id
                != prestacion.id_profesional_id
            ):
                return Response(
                    {
                        "mensaje": (
                            "El profesional de la prestación "
                            "no coincide con el profesional "
                            "del servicio."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            reserva = (
                ReservaDisponibilidad.objects
                .select_for_update()
                .filter(
                    id_solicitud=(
                        prestacion.id_solicitud
                    ),
                    estado="PENDIENTE_PAGO",
                )
                .order_by(
                    "-fecha_reserva",
                    "-id_reserva",
                )
                .first()
            )
            if reserva is None:
                return Response(
                    {
                        "mensaje": (
                            "La solicitud no posee un horario "
                            "seleccionado pendiente de pago."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            bloque = (
                Disponibilidad.objects
                .select_for_update()
                .filter(
                    id_disponibilidad=(
                        reserva.id_disponibilidad_id
                    )
                )
                .first()
            )
            if bloque is None:
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya no "
                            "se encuentra disponible."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if (
                bloque.id_profesional_id
                != prestacion.id_profesional_id
            ):
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado no "
                            "corresponde al profesional "
                            "de la prestación."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if bloque.estado != "DISPONIBLE":
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya no "
                            "está disponible. Debe elegir "
                            "otro horario antes de pagar."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            reserva_activa_otra = (
                ReservaDisponibilidad.objects
                .filter(
                    id_disponibilidad=bloque,
                    estado="ACTIVA",
                )
                .exists()
            )
            if reserva_activa_otra:
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya fue "
                            "reservado. Debe elegir otro "
                            "horario antes de pagar."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            inicio_bloque = timezone.make_aware(
                datetime.combine(
                    bloque.fecha,
                    bloque.hora_inicio,
                ),
                timezone.get_current_timezone(),
            )
            if inicio_bloque <= timezone.now():
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya "
                            "comenzó o quedó en el pasado. "
                            "Debe elegir otro horario."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                precio_normalizado = (
                    normalizar_precio_clp(
                        servicio.referencia_precio,
                        permitir_vacio=False,
                    )
                )
            except ValidationError:
                return Response(
                    {
                        "mensaje": (
                            "El servicio no posee un precio "
                            "final válido para iniciar "
                            "el pago."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            partes_precio = (
                precio_normalizado.split()
            )
            if len(partes_precio) != 2:
                return Response(
                    {
                        "mensaje": (
                            "El precio final del servicio "
                            "no pudo interpretarse."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                monto_total = Decimal(
                    partes_precio[0]
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            except InvalidOperation:
                return Response(
                    {
                        "mensaje": (
                            "El monto final del servicio "
                            "no es válido."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            moneda = partes_precio[1]
            parametro_comision = (
                ParametroSistema.objects
                .filter(
                    clave="comision_porcentaje"
                )
                .first()
            )
            if parametro_comision is None:
                return Response(
                    {
                        "mensaje": (
                            "La comisión del sistema no se "
                            "encuentra configurada."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                porcentaje_comision = Decimal(
                    str(
                        parametro_comision.valor_actual
                    ).strip()
                )
            except (
                InvalidOperation,
                TypeError,
                ValueError,
            ):
                return Response(
                    {
                        "mensaje": (
                            "La configuración de comisión "
                            "del sistema no es válida."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if (
                not porcentaje_comision.is_finite()
                or porcentaje_comision < Decimal("0")
                or porcentaje_comision > Decimal("100")
            ):
                return Response(
                    {
                        "mensaje": (
                            "La configuración de comisión "
                            "del sistema está fuera del "
                            "rango permitido."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            porcentaje_comision = (
                porcentaje_comision.quantize(
                    Decimal("0.0001"),
                    rounding=ROUND_HALF_UP,
                )
            )
            monto_comision = (
                monto_total
                * porcentaje_comision
                / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            monto_neto_profesional = (
                monto_total - monto_comision
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            # La organización ya recibió la cuenta principal al abrir la pantalla.
            # Nunca aceptar una cuenta distinta a la mostrada. El bloqueo
            # impide cambiarla mientras se registra este pago.
            id_cuenta_mostrada = request.data.get('id_cuenta_receptora')
            try:
                id_cuenta_mostrada = int(id_cuenta_mostrada)
                if id_cuenta_mostrada <= 0:
                    raise ValueError()
            except (TypeError, ValueError):
                return Response(
                    {'mensaje': 'Actualiza los datos bancarios antes de informar la transferencia.'},
                    status=status.HTTP_409_CONFLICT,
                )
            with connection.cursor() as cursor:
                cursor.execute('SELECT current_database(), current_schema(), current_user')
                if cursor.fetchone() != ('skilly', 'skilly', 'skilly_app'):
                    return Response({'mensaje': 'Transferencias bancarias no disponibles en esta instalación.'}, status=503)
                cursor.execute(
                    'LOCK TABLE skilly.cuenta_bancaria_skilly IN SHARE ROW EXCLUSIVE MODE'
                )
                cursor.execute('''SELECT id_cuenta, titular, rut_titular, banco,
                                   tipo_cuenta, numero_cuenta, correo
                                  FROM skilly.cuenta_bancaria_skilly
                                  WHERE activa IS TRUE AND principal IS TRUE''')
                cuenta_receptora = cursor.fetchone()
                if not cuenta_receptora or cuenta_receptora[0] != id_cuenta_mostrada:
                    return Response({
                        'mensaje': 'Los datos bancarios cambiaron. Actualiza la página y comprueba la cuenta antes de continuar.'
                    }, status=status.HTTP_409_CONFLICT)

            # La ruta privada se guarda en el campo de texto existente.
            # No se usa el nombre original aportado por el navegador.
            nombre_archivo = (
                f"comprobantes_transferencia_privados/"
                f"{uuid4().hex}.{datos['extension_comprobante']}"
            )
            ruta_archivo = default_storage.save(nombre_archivo, comprobante_archivo)
            try:
                ahora = timezone.now()
                pago = Pago.objects.create(
                    id_prestacion=prestacion,
                    monto_total=monto_total,
                    moneda=moneda,
                    porcentaje_comision_aplicado=(
                        porcentaje_comision
                    ),
                    monto_comision=monto_comision,
                    monto_neto_profesional=(
                        monto_neto_profesional
                    ),
                    estado_pago=(
                        "PENDIENTE_VERIFICACION"
                    ),
                    metodo_pago="TRANSFERENCIA",
                    proveedor_pago=None,
                    estado_verificacion="PENDIENTE",
                    comprobante_transferencia=(
                        ruta_archivo
                    ),
                    fecha_pago=None,
                    fecha_retencion=None,
                    fecha_liberacion=None,
                    referencia_transaccion=(
                        referencia_transaccion
                    ),
                )
                # Instrucción histórica: se fija dentro de la misma transacción
                # que creó el pago, sin modificar pagos anteriores.
                with connection.cursor() as cursor:
                    cursor.execute("""INSERT INTO skilly.instruccion_transferencia_skilly
                        (id_pago, id_cuenta, titular_fijado, rut_titular_fijado,
                         banco_fijado, tipo_cuenta_fijado, numero_cuenta_fijado, correo_fijado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        [pago.id_pago, *cuenta_receptora])
                HistorialEstadoPago.objects.create(
                    id_pago=pago,
                    id_usuario_skilly=None,
                    estado_anterior=None,
                    estado_nuevo=(
                        "PENDIENTE_VERIFICACION"
                    ),
                    fecha_cambio=ahora,
                    observacion=(
                        "Transferencia informada por la "
                        "empresa y pendiente de verificación "
                        "por Skilly."
                    ),
                )
                EventoTrazabilidad.objects.create(
                    entidad_tipo="pago",
                    entidad_id=pago.id_pago,
                    accion="INICIAR_PAGO_TRANSFERENCIA",
                    detalle_resumido=(
                        f"Pago {pago.id_pago} iniciado para "
                        f"prestación "
                        f"{prestacion.id_prestacion}. "
                        f"Estado: "
                        f"PENDIENTE_VERIFICACION."
                    )[:255],
                    fecha_evento=ahora,
                )
            except Exception:
                default_storage.delete(ruta_archivo)
                raise
        pago_data = dict(
            PagoEstadoComunicableSerializer(
                pago
            ).data
        )
        pago_data["metodo_pago"] = (
            pago.metodo_pago
        )
        pago_data["estado_verificacion"] = (
            pago.estado_verificacion
        )
        return Response(
            {
                "mensaje": (
                    "Transferencia registrada. "
                    "El pago quedó pendiente de "
                    "verificación por Skilly."
                ),
                "pago": pago_data,
                "reserva_confirmada": False,
                "prestacion_contratada": False,
            },
            status=status.HTTP_201_CREATED,
        )
class PagoEstadoEmpresaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    def get(self, request, referencia):
        datos_referencia = leer_referencia_seguimiento(
            referencia
        )
        if datos_referencia is None:
            return Response(
                {
                    "mensaje": (
                        "La referencia de seguimiento "
                        "no es valida."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        prestacion = (
            PrestacionServicio.objects
            .select_related(
                "id_solicitud",
            )
            .filter(
                id_solicitud_id=(
                    datos_referencia[
                        "id_solicitud"
                    ]
                ),
                id_solicitud__id_contacto_id=(
                    datos_referencia[
                        "id_contacto"
                    ]
                ),
            )
            .first()
        )
        if prestacion is None:
            return Response(
                {
                    "mensaje": (
                        "No existe una prestacion "
                        "autorizada para esta referencia."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        pago = (
            Pago.objects
            .filter(
                id_prestacion=prestacion
            )
            .first()
        )
        if pago is None:
            return Response(
                {
                    "mensaje": (
                        "Todavia no existe un pago "
                        "registrado para esta prestacion."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = (
            PagoEstadoComunicableSerializer(
                pago
            )
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
class PagoPrestacionProfesionalView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsProfesional
    ]
    def get(self, request, id_prestacion):
        profesional = Profesional.objects.filter(
            id_usuario=request.user
        ).first()
        if profesional is None:
            return Response(
                {
                    "mensaje": (
                        "El perfil profesional todavía "
                        "no se encuentra registrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        pago = (
            Pago.objects
            .select_related(
                "id_prestacion",
            )
            .filter(
                id_prestacion=id_prestacion,
                id_prestacion__id_profesional=profesional,
            )
            .first()
        )
        if pago is None:
            return Response(
                {
                    "mensaje": (
                        "No existe un pago disponible "
                        "para la prestación indicada."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PagoResumenProfesionalSerializer(
            pago
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
class MisPagosProfesionalView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsProfesional
    ]
    def get(self, request):
        profesional = Profesional.objects.filter(
            id_usuario=request.user
        ).first()
        if profesional is None:
            return Response(
                {
                    "mensaje": (
                        "El perfil profesional todavía "
                        "no se encuentra registrado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        pagos = (
            Pago.objects
            .filter(
                id_prestacion__id_profesional=profesional
            )
            .order_by(
                "-id_pago"
            )
        )
        serializer = PagoResumenProfesionalSerializer(
            pagos,
            many=True,
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
class PagosAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsAdministracionSkilly
    ]
    def get(self, request):
        pagos = (
            Pago.objects
            .select_related(
                "id_prestacion",
            )
            .order_by(
                "-id_pago"
            )
        )
        serializer = PagoAdministracionSerializer(
            pagos,
            many=True,
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
class DetallePagoAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsAdministracionSkilly
    ]
    def get(self, request, id_pago):
        pago = (
            Pago.objects
            .select_related(
                "id_prestacion",
            )
            .filter(
                id_pago=id_pago
            )
            .first()
        )
        if pago is None:
            return Response(
                {
                    "mensaje": (
                        "El pago solicitado no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        historial = (
            HistorialEstadoPago.objects
            .select_related(
                "id_usuario_skilly",
            )
            .filter(
                id_pago=pago
            )
            .order_by(
                "fecha_cambio",
                "id_historial_pago",
            )
        )
        return Response(
            {
                "pago": (
                    PagoAdministracionSerializer(
                        pago
                    ).data
                ),
                "historial": (
                    HistorialEstadoPagoAdministracionSerializer(
                        historial,
                        many=True,
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )
    def post(self, request, id_pago):
        entrada_serializer = (
            VerificarPagoTransferenciaSerializer(
                data=request.data
            )
        )
        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        observacion = (
            entrada_serializer.validated_data.get(
                "observacion"
            )
        )
        if observacion is not None:
            observacion = observacion.strip()
        if not observacion:
            observacion = (
                "Transferencia verificada por Skilly."
            )
        with transaction.atomic():
            pago = (
                Pago.objects
                .select_for_update()
                .filter(
                    id_pago=id_pago
                )
                .first()
            )
            if pago is None:
                return Response(
                    {
                        "mensaje": (
                            "El pago solicitado no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            if pago.metodo_pago != "TRANSFERENCIA":
                return Response(
                    {
                        "mensaje": (
                            "Esta operación solo permite "
                            "verificar pagos realizados "
                            "mediante transferencia."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if (
                pago.estado_pago == "RETENIDO"
                and pago.estado_verificacion
                == "VERIFICADO"
            ):
                return Response(
                    {
                        "mensaje": (
                            "La transferencia ya se "
                            "encontraba verificada."
                        ),
                        "pago": (
                            PagoAdministracionSerializer(
                                pago
                            ).data
                        ),
                    },
                    status=status.HTTP_200_OK,
                )
            if (
                pago.estado_pago
                != "PENDIENTE_VERIFICACION"
                or pago.estado_verificacion
                != "PENDIENTE"
            ):
                return Response(
                    {
                        "mensaje": (
                            "El pago no se encuentra en "
                            "un estado válido para verificar "
                            "la transferencia."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            prestacion = (
                PrestacionServicio.objects
                .select_for_update()
                .filter(
                    id_prestacion=(
                        pago.id_prestacion_id
                    )
                )
                .first()
            )
            if prestacion is None:
                return Response(
                    {
                        "mensaje": (
                            "La prestación asociada al pago "
                            "no existe."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if (
                prestacion.estado
                != "PENDIENTE_CONTRATACION"
            ):
                return Response(
                    {
                        "mensaje": (
                            "La prestación no se encuentra "
                            "pendiente de contratación."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            reserva = (
                ReservaDisponibilidad.objects
                .select_for_update()
                .filter(
                    id_solicitud_id=(
                        prestacion.id_solicitud_id
                    ),
                    estado="PENDIENTE_PAGO",
                )
                .order_by(
                    "-fecha_reserva",
                    "-id_reserva",
                )
                .first()
            )
            if reserva is None:
                return Response(
                    {
                        "mensaje": (
                            "No existe una selección de "
                            "horario pendiente de pago "
                            "para esta prestación."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            bloque = (
                Disponibilidad.objects
                .select_for_update()
                .filter(
                    id_disponibilidad=(
                        reserva.id_disponibilidad_id
                    )
                )
                .first()
            )
            if bloque is None:
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya no "
                            "existe."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if (
                bloque.id_profesional_id
                != prestacion.id_profesional_id
            ):
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado no "
                            "corresponde al profesional "
                            "de la prestación."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if bloque.estado != "DISPONIBLE":
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya "
                            "no se encuentra disponible. "
                            "La transferencia no puede "
                            "confirmarse automáticamente."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            reserva_activa = (
                ReservaDisponibilidad.objects
                .filter(
                    id_disponibilidad=bloque,
                    estado="ACTIVA",
                )
                .exclude(
                    id_reserva=reserva.id_reserva
                )
                .exists()
            )
            if reserva_activa:
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya "
                            "posee una reserva activa. "
                            "La transferencia requiere "
                            "gestión manual."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            inicio_bloque = timezone.make_aware(
                datetime.combine(
                    bloque.fecha,
                    bloque.hora_inicio,
                ),
                timezone.get_current_timezone(),
            )
            if inicio_bloque <= timezone.now():
                return Response(
                    {
                        "mensaje": (
                            "El horario seleccionado ya "
                            "comenz? o qued? en el pasado. "
                            "La transferencia requiere "
                            "gestión manual."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            ahora = timezone.now()
            estado_anterior = pago.estado_pago
            pago.estado_pago = "RETENIDO"
            pago.estado_verificacion = "VERIFICADO"
            pago.fecha_pago = ahora
            pago.fecha_retencion = ahora
            pago.save(
                update_fields=[
                    "estado_pago",
                    "estado_verificacion",
                    "fecha_pago",
                    "fecha_retencion",
                ]
            )
            reserva.estado = "ACTIVA"
            reserva.fecha_cambio = ahora
            reserva.motivo_cambio = (
                "Reserva confirmada después de "
                "verificar el pago."
            )
            reserva.save(
                update_fields=[
                    "estado",
                    "fecha_cambio",
                    "motivo_cambio",
                ]
            )
            bloque.estado = "RESERVADA"
            bloque.save(
                update_fields=[
                    "estado",
                ]
            )
            HistorialEstadoPago.objects.create(
                id_pago=pago,
                id_usuario_skilly=request.user,
                estado_anterior=estado_anterior,
                estado_nuevo="RETENIDO",
                fecha_cambio=ahora,
                observacion=observacion,
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="pago",
                entidad_id=pago.id_pago,
                accion="VERIFICAR_TRANSFERENCIA",
                detalle_resumido=(
                    f"Pago {pago.id_pago} verificado. "
                    f"Estado: RETENIDO. "
                    f"Prestación "
                    f"{prestacion.id_prestacion}."
                )[:255],
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo=(
                    "reserva_disponibilidad"
                ),
                entidad_id=reserva.id_reserva,
                accion="CONFIRMAR_RESERVA_PAGO",
                detalle_resumido=(
                    f"Reserva {reserva.id_reserva} "
                    f"activada tras verificar el "
                    f"pago {pago.id_pago}. "
                    f"Bloque "
                    f"{bloque.id_disponibilidad} "
                    f"marcado RESERVADA."
                )[:255],
            )
        pago = (
            Pago.objects
            .get(
                id_pago=id_pago
            )
        )
        return Response(
            {
                "mensaje": (
                    "Transferencia verificada "
                    "correctamente. El pago qued? "
                    "retenido y el horario reservado."
                ),
                "pago": (
                    PagoAdministracionSerializer(
                        pago
                    ).data
                ),
                "reserva": {
                    "id_reserva": (
                        reserva.id_reserva
                    ),
                    "estado": reserva.estado,
                    "id_disponibilidad": (
                        bloque.id_disponibilidad
                    ),
                    "estado_disponibilidad": (
                        bloque.estado
                    ),
                },
                "prestacion_estado": (
                    prestacion.estado
                ),
                "prestacion_contratada": False,
            },
            status=status.HTTP_200_OK,
        )
class LiberarPagoAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsAdministracionSkilly
    ]
    def post(self, request, id_pago):
        entrada_serializer = (
            LiberarPagoSerializer(
                data=request.data
            )
        )
        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        observacion = (
            entrada_serializer.validated_data.get(
                "observacion"
            )
        )
        if observacion is not None:
            observacion = observacion.strip()
        if not observacion:
            observacion = (
                "Pago liberado al profesional "
                "tras validar la entrega."
            )
        with transaction.atomic():
            pago = (
                Pago.objects
                .select_for_update()
                .filter(
                    id_pago=id_pago
                )
                .first()
            )
            if pago is None:
                return Response(
                    {
                        "mensaje": (
                            "El pago solicitado no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            if pago.estado_pago == "LIBERADO":
                return Response(
                    {
                        "mensaje": (
                            "El pago ya se encontraba "
                            "liberado."
                        ),
                        "pago": (
                            PagoAdministracionSerializer(
                                pago
                            ).data
                        ),
                    },
                    status=status.HTTP_200_OK,
                )
            if pago.estado_pago != "RETENIDO":
                return Response(
                    {
                        "mensaje": (
                            "El pago debe encontrarse "
                            "retenido antes de liberarlo."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            reversa_pendiente = ReversaPago.objects.filter(
                id_pago=pago,
                estado_reversa="SOLICITADA",
            ).exists()

            if reversa_pendiente:
                return Response(
                    {
                        "mensaje": (
                            "El pago posee una reversa solicitada. "
                            "Debe permanecer retenido hasta que "
                            "la reversa sea resuelta."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            prestacion = (
                PrestacionServicio.objects
                .select_for_update()
                .filter(
                    id_prestacion=(
                        pago.id_prestacion_id
                    )
                )
                .first()
            )
            if prestacion is None:
                return Response(
                    {
                        "mensaje": (
                            "La prestacion asociada al "
                            "pago no existe."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if prestacion.estado in ["CANCELADA", "POSTERGADA"]:
                return Response(
                    {
                        "mensaje": (
                            "No se puede liberar un pago "
                            "de una prestacion cancelada o postergada."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            ultima_entrega = (
                Entrega.objects
                .select_for_update()
                .filter(
                    id_prestacion=prestacion
                )
                .order_by(
                    "-version",
                    "-fecha_entrega",
                    "-id_entrega",
                )
                .first()
            )
            if ultima_entrega is None:
                return Response(
                    {
                        "mensaje": (
                            "La prestacion todavia no "
                            "posee una entrega registrada."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if (
                ultima_entrega.estado
                != "ACEPTADA"
            ):
                return Response(
                    {
                        "mensaje": (
                            "La ultima entrega debe estar "
                            "aceptada por la empresa antes "
                            "de liberar el pago."
                        ),
                        "estado_entrega": (
                            ultima_entrega.estado
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            reclamos = (
                ReclamoPrestacion.objects
                .filter(
                    id_prestacion=prestacion
                )
            )
            if reclamos.filter(
                fecha_cierre__isnull=True
            ).exists():
                return Response(
                    {
                        "mensaje": (
                            "Existe un reclamo abierto. "
                            "El pago debe permanecer "
                            "retenido hasta su resolucion."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            cantidad_reclamos = (
                reclamos.count()
            )
            resoluciones = (
                ResolucionReclamo.objects
                .filter(
                    id_reclamo__id_prestacion=(
                        prestacion
                    )
                )
            )
            cantidad_resoluciones = (
                resoluciones.count()
            )
            if (
                cantidad_reclamos
                != cantidad_resoluciones
            ):
                return Response(
                    {
                        "mensaje": (
                            "Existe un reclamo sin una "
                            "resolucion economica completa."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            resolucion_bloqueante = (
                resoluciones
                .exclude(
                    efecto_economico="LIBERACION"
                )
                .order_by(
                    "-fecha_resolucion",
                    "-id_resolucion",
                )
                .first()
            )
            if resolucion_bloqueante is not None:
                return Response(
                    {
                        "mensaje": (
                            "La resolucion economica "
                            "registrada no permite liberar "
                            "este pago."
                        ),
                        "efecto_economico": (
                            resolucion_bloqueante
                            .efecto_economico
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            ahora = timezone.now()
            estado_anterior = (
                pago.estado_pago
            )
            pago.estado_pago = "LIBERADO"
            pago.fecha_liberacion = ahora
            pago.save(
                update_fields=[
                    "estado_pago",
                    "fecha_liberacion",
                ]
            )
            HistorialEstadoPago.objects.create(
                id_pago=pago,
                id_usuario_skilly=request.user,
                estado_anterior=estado_anterior,
                estado_nuevo="LIBERADO",
                fecha_cambio=ahora,
                observacion=observacion,
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="pago",
                entidad_id=pago.id_pago,
                accion=(
                    "LIBERAR_PAGO_PROFESIONAL"
                ),
                detalle_resumido=(
                    f"Pago {pago.id_pago} liberado. "
                    f"Prestacion "
                    f"{prestacion.id_prestacion}. "
                    f"Neto profesional: "
                    f"{pago.monto_neto_profesional} "
                    f"{pago.moneda}."
                )[:255],
            )
        pago = (
            Pago.objects
            .get(
                id_pago=id_pago
            )
        )
        return Response(
            {
                "mensaje": (
                    "Pago liberado correctamente "
                    "al profesional."
                ),
                "pago": (
                    PagoAdministracionSerializer(
                        pago
                    ).data
                ),
                "entrega_aceptada": {
                    "id_entrega": (
                        ultima_entrega.id_entrega
                    ),
                    "version": (
                        ultima_entrega.version
                    ),
                    "estado": (
                        ultima_entrega.estado
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )
class ReversasPagoAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]
    permission_classes = [
        EsAdministracionSkilly
    ]
    def get(self, request, id_pago):
        pago = (
            Pago.objects
            .select_related(
                "id_prestacion",
            )
            .filter(
                id_pago=id_pago
            )
            .first()
        )
        if pago is None:
            return Response(
                {
                    "mensaje": (
                        "El pago solicitado no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        reversas = (
            ReversaPago.objects
            .select_related(
                "id_usuario_skilly",
                "id_resolucion_reclamo",
            )
            .filter(
                id_pago=pago
            )
            .order_by(
                "-fecha_solicitud",
                "-id_reversa",
            )
        )
        return Response(
            {
                "pago": (
                    PagoAdministracionSerializer(
                        pago
                    ).data
                ),
                "reversas": (
                    ReversaPagoSerializer(
                        reversas,
                        many=True,
                    ).data
                ),
            },
            status=status.HTTP_200_OK,
        )
    def post(self, request, id_pago):
        entrada_serializer = IniciarReversaPagoSerializer(
            data=request.data
        )
        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        motivo = (
            entrada_serializer.validated_data.get(
                "motivo"
            )
        )
        if motivo is not None:
            motivo = motivo.strip()
        if not motivo:
            return Response(
                {
                    "motivo": [
                        (
                            "Debe indicar el motivo para "
                            "iniciar la reversa."
                        )
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            pago = (
                Pago.objects
                .select_related(
                    "id_prestacion",
                )
                .select_for_update()
                .filter(
                    id_pago=id_pago
                )
                .first()
            )
            if pago is None:
                return Response(
                    {
                        "mensaje": (
                            "El pago solicitado no existe."
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            reversa_pendiente = (
                ReversaPago.objects
                .filter(
                    id_pago=pago,
                    estado_reversa="SOLICITADA",
                )
                .exists()
            )
            if reversa_pendiente:
                return Response(
                    {
                        "mensaje": (
                            "El pago ya posee una reversa "
                            "pendiente de resolución."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if pago.estado_pago != "RETENIDO":
                return Response(
                    {
                        "mensaje": (
                            "Este flujo de reversa solo admite "
                            "pagos en estado RETENIDO."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if pago.estado_verificacion != "VERIFICADO":
                return Response(
                    {
                        "mensaje": (
                            "El pago debe estar VERIFICADO "
                            "antes de solicitar una reversa."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if pago.monto_total is None or pago.monto_total <= 0:
                return Response(
                    {
                        "mensaje": (
                            "El pago no posee un monto total "
                            "valido para solicitar una reversa."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            prestacion_cancelada = (
                pago.id_prestacion.estado
                == "CANCELADA"
            )
            resolucion = (
                ResolucionReclamo.objects
                .filter(
                    id_reclamo__id_prestacion=(
                        pago.id_prestacion
                    ),
                    efecto_economico="REVERSA",
                )
                .order_by(
                    "-fecha_resolucion",
                    "-id_resolucion",
                )
                .first()
            )
            if (
                not prestacion_cancelada
                and resolucion is None
            ):
                return Response(
                    {
                        "mensaje": (
                            "El pago no posee actualmente "
                            "una condición documentada que "
                            "autorice iniciar una reversa."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if resolucion is not None:
                reversa_resolucion_existente = (
                    ReversaPago.objects
                    .filter(
                        id_resolucion_reclamo=resolucion
                    )
                    .exists()
                )
                if reversa_resolucion_existente:
                    return Response(
                        {
                            "mensaje": (
                                "La resolución del reclamo "
                                "ya posee una reversa "
                                "asociada."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
            monto_reversa = None
            if (
                resolucion is not None
                and resolucion.monto_afectado
                is not None
            ):
                monto_reversa = (
                    resolucion.monto_afectado
                )
            if monto_reversa is not None:
                if (
                    monto_reversa <= 0
                    or monto_reversa > pago.monto_total
                ):
                    return Response(
                        {
                            "mensaje": (
                                "El monto autorizado para la reversa "
                                "debe ser mayor que cero y no superar "
                                "el monto total del pago."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

            reversa = ReversaPago.objects.create(
                id_pago=pago,
                id_usuario_skilly=request.user,
                id_resolucion_reclamo=resolucion,
                monto_reversa=monto_reversa,
                estado_reversa="SOLICITADA",
                motivo=motivo,
                referencia_externa=None,
                fecha_solicitud=timezone.now(),
                fecha_resolucion=None,
            )
            detalle_evento = (
                f"Reversa {reversa.id_reversa} solicitada "
                f"para pago {pago.id_pago}. "
                f"Prestación "
                f"{pago.id_prestacion_id}. "
            )
            if resolucion is not None:
                detalle_evento += (
                    f"Resolución de reclamo "
                    f"{resolucion.id_resolucion}. "
                )
            else:
                detalle_evento += (
                    "Origen: prestación cancelada. "
                )
            detalle_evento += (
                f"Motivo: {motivo}"
            )
            registrar_evento_trazabilidad(
                usuario=request.user,
                entidad_tipo="reversa_pago",
                entidad_id=reversa.id_reversa,
                accion="SOLICITAR_REVERSA",
                detalle_resumido=detalle_evento[:255],
            )
        reversa = (
            ReversaPago.objects
            .select_related(
                "id_usuario_skilly",
                "id_resolucion_reclamo",
            )
            .get(
                id_reversa=reversa.id_reversa
            )
        )
        return Response(
            {
                "mensaje": (
                    "Solicitud de reversa registrada "
                    "correctamente."
                ),
                "reversa": (
                    ReversaPagoSerializer(
                        reversa
                    ).data
                ),
                "nota": (
                    "La reversa quedó registrada como "
                    "SOLICITADA. El resultado definitivo "
                    "depende del medio de pago y de la "
                    "integración correspondiente."
                ),
            },
            status=status.HTTP_201_CREATED,
        )
