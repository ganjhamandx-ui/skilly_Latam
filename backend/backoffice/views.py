from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly

from .models import (
    EventoTrazabilidad,
    HistorialParametro,
    ParametroSistema,
)
from .serializers import (
    ActualizarComisionSerializer,
    EventoTrazabilidadSerializer,
    FiltroTrazabilidadSerializer,
    HistorialParametroSerializer,
    ParametroSistemaSerializer,
)


from django.db.models import Count, Sum
from coordinacion.models import PrestacionServicio
from pagos.models import Pago
from profesionales.models import Profesional
from solicitudes.models import SolicitudServicio

class PanelIndicadoresView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        def agrupar_estados(modelo, campo):
            registros = (
                modelo.objects
                .values(campo)
                .annotate(cantidad=Count("pk"))
                .order_by(campo)
            )

            return [
                {
                    "estado": registro[campo],
                    "cantidad": registro["cantidad"],
                }
                for registro in registros
            ]

        def formato_clp(valor):
            return format(valor if valor is not None else 0, ".2f")

        indicadores = {
            "profesionales": Profesional.objects.count(),
            "solicitudes": SolicitudServicio.objects.count(),
            "prestaciones": PrestacionServicio.objects.count(),
            "pagos": Pago.objects.count(),
        }

        estados = {
            "profesionales": agrupar_estados(
                Profesional,
                "estado_validacion",
            ),
            "solicitudes": agrupar_estados(
                SolicitudServicio,
                "estado",
            ),
            "prestaciones": agrupar_estados(
                PrestacionServicio,
                "estado",
            ),
        }

        resumen_pagos = (
            Pago.objects
            .values("estado_pago")
            .annotate(
                cantidad=Count("pk"),
                suma_total=Sum("monto_total"),
                suma_comision=Sum("monto_comision"),
                suma_neto=Sum("monto_neto_profesional"),
            )
            .order_by("estado_pago")
        )

        pagos_por_estado = []

        monto_retenido = 0
        monto_liberado = 0
        comision_pagos_liberados = 0
        neto_pagos_liberados = 0

        for fila in resumen_pagos:
            estado_pago = fila["estado_pago"]

            pagos_por_estado.append(
                {
                    "estado": estado_pago,
                    "cantidad": fila["cantidad"],
                    "monto_total_clp": formato_clp(
                        fila["suma_total"]
                    ),
                    "comision_calculada_clp": formato_clp(
                        fila["suma_comision"]
                    ),
                    "neto_profesional_calculado_clp": formato_clp(
                        fila["suma_neto"]
                    ),
                }
            )

            if estado_pago == "RETENIDO":
                monto_retenido += fila["suma_total"] or 0

            if estado_pago == "LIBERADO":
                monto_liberado += fila["suma_total"] or 0

                comision_pagos_liberados += (
                    fila["suma_comision"] or 0
                )

                neto_pagos_liberados += (
                    fila["suma_neto"] or 0
                )

        # Desglose de solo lectura; usa el mismo criterio del indicador.
        # No modifica pagos, retenciones ni la distribución económica.
        pagos_retenidos = (
            Pago.objects
            .filter(estado_pago="RETENIDO")
            .select_related(
                "id_prestacion__id_profesional",
                "id_prestacion__id_solicitud",
            )
            .order_by("-id_pago")
        )
        detalle_retenciones = []
        for pago in pagos_retenidos:
            prestacion = pago.id_prestacion
            profesional = prestacion.id_profesional
            detalle_retenciones.append({
                "id_pago": pago.id_pago,
                "id_prestacion": prestacion.id_prestacion,
                "id_solicitud": prestacion.id_solicitud_id,
                "id_profesional": profesional.id_profesional,
                "profesional": (
                    f"{profesional.nombres} {profesional.apellidos}"
                ).strip(),
                "estado_pago": pago.estado_pago,
                "moneda": pago.moneda,
                "monto_total_clp": formato_clp(pago.monto_total),
                "monto_comision_clp": formato_clp(pago.monto_comision),
                "monto_neto_profesional_clp": formato_clp(
                    pago.monto_neto_profesional
                ),
            })

        estados["pagos"] = pagos_por_estado

        resumen_financiero = {
            "moneda": "CLP",
            "monto_retenido_clp": formato_clp(
                monto_retenido
            ),
            "monto_liberado_clp": formato_clp(
                monto_liberado
            ),
            "comision_pagos_liberados_clp": formato_clp(
                comision_pagos_liberados
            ),
            "neto_pagos_liberados_clp": formato_clp(
                neto_pagos_liberados
            ),
        }

        return Response(
            {
                "indicadores": indicadores,
                "estados": estados,
                "resumen_financiero": resumen_financiero,
                "detalle_retenciones": detalle_retenciones,
            },
            status=status.HTTP_200_OK,
        )


class ConfiguracionComisionAdministracionView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        parametro = (
            ParametroSistema.objects
            .select_related(
                "id_usuario_actualiza"
            )
            .filter(
                clave="comision_porcentaje"
            )
            .first()
        )

        if parametro is None:
            return Response(
                {
                    "mensaje": (
                        "El parametro de comision "
                        "no se encuentra configurado."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        historial = (
            HistorialParametro.objects
            .select_related(
                "id_usuario_skilly"
            )
            .filter(
                id_parametro=parametro
            )
            .order_by(
                "-fecha_cambio",
                "-id_historial_parametro",
            )
        )

        parametro_serializer = (
            ParametroSistemaSerializer(
                parametro
            )
        )

        historial_serializer = (
            HistorialParametroSerializer(
                historial,
                many=True,
            )
        )

        return Response(
            {
                "parametro": parametro_serializer.data,
                "historial": historial_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        entrada_serializer = ActualizarComisionSerializer(
            data=request.data
        )

        if not entrada_serializer.is_valid():
            return Response(
                entrada_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        valor_nuevo = entrada_serializer.validated_data[
            "valor_nuevo"
        ]

        valor_nuevo_texto = format(
            valor_nuevo,
            "f",
        )

        with transaction.atomic():
            parametro = (
                ParametroSistema.objects
                .select_for_update()
                .filter(
                    clave="comision_porcentaje"
                )
                .first()
            )

            ahora = timezone.now()

            parametro_faltante = parametro is None
            creado = False
            if parametro_faltante:
                # Inicializa la clave en la tabla existente y la deja
                # registrada en el mismo historial que las actualizaciones.
                # La unicidad de clave impide dos parametros concurrentes.
                parametro, creado = ParametroSistema.objects.get_or_create(
                    clave="comision_porcentaje",
                    defaults={
                        "valor_actual": valor_nuevo_texto,
                        "tipo_dato": "DECIMAL",
                        "descripcion": "Porcentaje de comisión de SKILLY",
                        "id_usuario_actualiza": request.user,
                        "fecha_actualizacion": ahora,
                    },
                )
                if creado:
                    HistorialParametro.objects.create(
                        id_parametro=parametro,
                        valor_anterior=None,
                        valor_nuevo=valor_nuevo_texto,
                        id_usuario_skilly=request.user,
                        fecha_cambio=ahora,
                    )
                else:
                    # Si otro administrador lo creó en simultáneo,
                    # continuar con la validación de cambio habitual.
                    parametro = (
                        ParametroSistema.objects
                        .select_for_update()
                        .get(pk=parametro.pk)
                    )

            creado_en_esta_peticion = creado if parametro_faltante else False

            if not creado_en_esta_peticion:
                valor_anterior = parametro.valor_actual

                try:
                    mismo_valor = (
                        Decimal(valor_anterior)
                        == valor_nuevo
                    )
                except InvalidOperation:
                    mismo_valor = (
                        valor_anterior
                        == valor_nuevo_texto
                    )

                if mismo_valor:
                    return Response(
                        {
                            "mensaje": (
                                "El porcentaje informado "
                                "ya corresponde al valor vigente."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                parametro.valor_actual = valor_nuevo_texto
                parametro.id_usuario_actualiza = request.user
                parametro.fecha_actualizacion = ahora

                parametro.save(
                    update_fields=[
                        "valor_actual",
                        "id_usuario_actualiza",
                        "fecha_actualizacion",
                    ]
                )

                HistorialParametro.objects.create(
                    id_parametro=parametro,
                    valor_anterior=valor_anterior,
                    valor_nuevo=valor_nuevo_texto,
                    id_usuario_skilly=request.user,
                    fecha_cambio=ahora,
                )

        parametro = (
            ParametroSistema.objects
            .select_related(
                "id_usuario_actualiza"
            )
            .get(
                clave="comision_porcentaje"
            )
        )

        parametro_serializer = (
            ParametroSistemaSerializer(
                parametro
            )
        )

        return Response(
            {
                "mensaje": (
                    "Porcentaje de comisión "
                    "guardado correctamente."
                ),
                "parametro": parametro_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class TrazabilidadOperacionalView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request):
        filtro_serializer = FiltroTrazabilidadSerializer(
            data=request.query_params
        )

        if not filtro_serializer.is_valid():
            return Response(
                filtro_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        filtros = filtro_serializer.validated_data

        eventos = (
            EventoTrazabilidad.objects
            .select_related(
                "id_usuario"
            )
            .all()
        )

        entidad_tipo = filtros.get(
            "entidad_tipo"
        )

        entidad_id = filtros.get(
            "entidad_id"
        )

        accion = filtros.get(
            "accion"
        )

        if entidad_tipo is not None:
            eventos = eventos.filter(
                entidad_tipo__iexact=entidad_tipo
            )

        if entidad_id is not None:
            eventos = eventos.filter(
                entidad_id=entidad_id
            )

        if accion is not None:
            eventos = eventos.filter(
                accion__iexact=accion
            )

        eventos = eventos.order_by(
            "-fecha_evento",
            "-id_evento",
        )

        serializer = EventoTrazabilidadSerializer(
            eventos,
            many=True,
        )

        if not eventos.exists():
            return Response(
                {
                    "mensaje": (
                        "No existen eventos de trazabilidad "
                        "para los criterios consultados."
                    ),
                    "eventos": [],
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "eventos": serializer.data
            },
            status=status.HTTP_200_OK,
        )


class DetalleEventoTrazabilidadView(APIView):
    authentication_classes = [
        SesionSkillyAuthentication
    ]

    permission_classes = [
        EsAdministracionSkilly
    ]

    def get(self, request, id_evento):
        evento = (
            EventoTrazabilidad.objects
            .select_related(
                "id_usuario"
            )
            .filter(
                id_evento=id_evento
            )
            .first()
        )

        if evento is None:
            return Response(
                {
                    "mensaje": (
                        "El evento de trazabilidad "
                        "solicitado no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EventoTrazabilidadSerializer(
            evento
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )