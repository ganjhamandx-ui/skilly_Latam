from .control_responsable import requiere_responsable_prestacion
from datetime import datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.response import Response

from pagos.models import Pago
from solicitudes.models import Disponibilidad, ReservaDisponibilidad, SolicitudServicio

from .models import CoordinacionSolicitud, PrestacionServicio, ReunionSolicitud
from .serializers import ReservaDisponibilidadAdministracionSerializer
from .views import (
    GestionAgendaPrestacionAdministracionView,
    registrar_evento_trazabilidad,
)


def conflicto(mensaje, codigo=status.HTTP_409_CONFLICT):
    return Response({"mensaje": mensaje}, status=codigo)


def inicio_bloque(bloque):
    return timezone.make_aware(
        datetime.combine(bloque.fecha, bloque.hora_inicio),
        timezone.get_current_timezone(),
    )


def registrar_cambio(usuario, tipo, identificador, accion, detalle):
    registrar_evento_trazabilidad(
        usuario=usuario,
        entidad_tipo=tipo,
        entidad_id=identificador,
        accion=accion,
        detalle_resumido=detalle[:255],
    )


@method_decorator(csrf_protect, name="dispatch")
class GestionAgendaPrestacionSeguraAdministracionView(
    GestionAgendaPrestacionAdministracionView
):
    # GET y AGENDAR_PRIMERA_REUNION conservan su funcionamiento original.
    @requiere_responsable_prestacion
    def post(self, request, id_prestacion):
        accion = str(request.data.get("accion", "")).strip().upper()
        if accion not in {"REAGENDAR", "POSTERGAR", "CANCELAR"}:
            return super().post(request, id_prestacion)

        motivo_dato = request.data.get("motivo", "")
        motivo = motivo_dato.strip() if isinstance(motivo_dato, str) else ""
        if not motivo:
            return conflicto(
                "Debe indicar un motivo para modificar la agenda.",
                status.HTTP_400_BAD_REQUEST,
            )

        # El bloqueo principal ordena los cambios simultáneos de la misma prestación.
        with transaction.atomic():
            prestacion = get_object_or_404(
                PrestacionServicio.objects.select_for_update(),
                pk=id_prestacion,
            )
            if prestacion.estado in {"FINALIZADA", "CANCELADA"}:
                return conflicto(
                    "La prestación está cerrada y no admite cambios de agenda."
                )

            reservas = list(
                ReservaDisponibilidad.objects.select_for_update()
                .filter(
                    id_solicitud_id=prestacion.id_solicitud_id,
                    estado="ACTIVA",
                )
                .order_by("id_reserva")[:2]
            )
            if len(reservas) > 1:
                return conflicto(
                    "La solicitud tiene varias reservas activas. "
                    "Requiere revisión administrativa."
                )
            reserva_actual = reservas[0] if reservas else None

            reuniones = list(
                ReunionSolicitud.objects.select_for_update()
                .filter(
                    id_solicitud_id=prestacion.id_solicitud_id,
                    id_profesional_id=prestacion.id_profesional_id,
                    estado="AGENDADA",
                )
                .order_by("id_reunion")[:2]
            )
            if len(reuniones) > 1:
                return conflicto(
                    "Existen varias reuniones AGENDADAS. "
                    "Requiere revisión administrativa."
                )
            reunion = reuniones[0] if reuniones else None

            # La cancelación es definitiva; la reversa económica corresponde a CU040.
            if accion == "CANCELAR":
                if reserva_actual is not None:
                    bloque = Disponibilidad.objects.select_for_update().filter(
                        pk=reserva_actual.id_disponibilidad_id
                    ).first()
                    if bloque is None or bloque.estado != "RESERVADA":
                        return conflicto(
                            "El estado del bloque reservado no es consistente."
                        )
                    if ReservaDisponibilidad.objects.filter(
                        id_disponibilidad_id=bloque.pk,
                        estado="ACTIVA",
                    ).exclude(pk=reserva_actual.pk).exists():
                        return conflicto("El bloque tiene otra reserva activa.")

                resultado = super().post(request, id_prestacion)
                if resultado.status_code != status.HTTP_200_OK:
                    transaction.set_rollback(True)
                    return resultado

                if reunion is not None:
                    reunion.estado = "CANCELADA"
                    reunion.save(update_fields=["estado"])
                    registrar_cambio(
                        request.user,
                        "reunion_solicitud",
                        reunion.pk,
                        "CANCELAR",
                        f"Reunión {reunion.pk} cancelada junto con prestación "
                        f"{prestacion.pk}. Fecha original conservada. Motivo: {motivo}",
                    )
                return resultado

            valor_nuevo = request.data.get("id_disponibilidad_nueva")
            sin_nueva_fecha = valor_nuevo is None or (
                isinstance(valor_nuevo, str) and not valor_nuevo.strip()
            )

            # POSTERGAR sin fecha suspende la prestación y libera el horario.
            if accion == "POSTERGAR" and sin_nueva_fecha:
                if prestacion.estado != "CONTRATADA":
                    return conflicto(
                        "Solo una prestación CONTRATADA puede postergarse sin fecha."
                    )
                if reserva_actual is None:
                    return conflicto("La prestación no posee una reserva activa.")
                pago = Pago.objects.filter(id_prestacion_id=prestacion.pk).first()
                if pago is None or pago.estado_pago != "RETENIDO":
                    return conflicto(
                        "Para postergar, el pago debe permanecer RETENIDO."
                    )
                bloque = Disponibilidad.objects.select_for_update().filter(
                    pk=reserva_actual.id_disponibilidad_id
                ).first()
                if bloque is None or bloque.estado != "RESERVADA":
                    return conflicto("El bloque reservado no está consistente.")
                if bloque.id_profesional_id != prestacion.id_profesional_id:
                    return conflicto("El bloque no pertenece al profesional.")
                if ReservaDisponibilidad.objects.filter(
                    id_disponibilidad_id=bloque.pk,
                    estado="ACTIVA",
                ).exclude(pk=reserva_actual.pk).exists():
                    return conflicto("El bloque tiene otra reserva activa.")
                if reunion is not None and reunion.fecha_hora != inicio_bloque(bloque):
                    return conflicto(
                        "La reunión AGENDADA no coincide con el bloque reservado. "
                        "Debe revisarse antes de postergar."
                    )

                ahora = timezone.now()
                reserva_actual.estado = "POSTERGADA"
                reserva_actual.fecha_cambio = ahora
                reserva_actual.motivo_cambio = motivo
                reserva_actual.save(update_fields=[
                    "estado", "fecha_cambio", "motivo_cambio"
                ])
                bloque.estado = "DISPONIBLE"
                bloque.save(update_fields=["estado"])
                prestacion.estado = "POSTERGADA"
                prestacion.save(update_fields=["estado"])
                if reunion is not None:
                    reunion.estado = "POSTERGADA"
                    reunion.save(update_fields=["estado"])
                    registrar_cambio(
                        request.user,
                        "reunion_solicitud",
                        reunion.pk,
                        "POSTERGAR",
                        f"Reunión {reunion.pk} postergada, conservando la fecha "
                        f"original. Prestación {prestacion.pk}. Motivo: {motivo}",
                    )

                SolicitudServicio.objects.filter(
                    pk=prestacion.id_solicitud_id
                ).update(fecha_actualizacion=ahora)
                CoordinacionSolicitud.objects.create(
                    id_solicitud_id=prestacion.id_solicitud_id,
                    id_usuario_skilly=request.user,
                    tipo="POSTERGAR",
                    detalle=(
                        f"Postergación sin nueva fecha. Bloque liberado: "
                        f"{bloque.pk}. Motivo: {motivo}"
                    ),
                    estado_resultante="POSTERGADA",
                    fecha_registro=ahora,
                )
                registrar_cambio(
                    request.user,
                    "reserva_disponibilidad",
                    reserva_actual.pk,
                    "POSTERGAR",
                    f"Reserva {reserva_actual.pk} postergada; bloque "
                    f"{bloque.pk} liberado. Motivo: {motivo}",
                )
                registrar_cambio(
                    request.user,
                    "prestacion_servicio",
                    prestacion.pk,
                    "POSTERGAR",
                    f"Prestación {prestacion.pk} POSTERGADA sin fecha. "
                    f"Pago {pago.pk} continúa {pago.estado_pago}.",
                )
                return Response({
                    "mensaje": "Prestación postergada sin nueva fecha.",
                    "prestacion_estado": "POSTERGADA",
                    "reserva_estado": "POSTERGADA",
                    "id_disponibilidad_liberada": bloque.pk,
                    "reunion_estado": reunion.estado if reunion is not None else None,
                    "pago_estado": pago.estado_pago,
                    "siguiente_flujo": "REAGENDAR con un nuevo bloque disponible.",
                }, status=status.HTTP_200_OK)

            # Si se recibió nueva disponibilidad, debe ser un entero válido.
            if isinstance(valor_nuevo, bool):
                return conflicto(
                    "El identificador del nuevo bloque debe ser un entero positivo.",
                    status.HTTP_400_BAD_REQUEST,
                )
            try:
                id_nuevo = int(valor_nuevo)
            except (TypeError, ValueError):
                return conflicto(
                    "El identificador del nuevo bloque debe ser un entero positivo.",
                    status.HTTP_400_BAD_REQUEST,
                )
            if id_nuevo < 1:
                return conflicto(
                    "El identificador del nuevo bloque debe ser un entero positivo.",
                    status.HTTP_400_BAD_REQUEST,
                )

            # REAGENDAR desde POSTERGADA reactiva sin volver a cobrar.
            if prestacion.estado == "POSTERGADA":
                if accion != "REAGENDAR":
                    return conflicto(
                        "La prestación está POSTERGADA. "
                        "Debe usar REAGENDAR para reanudarla."
                    )
                if reserva_actual is not None or reunion is not None:
                    return conflicto(
                        "La prestación POSTERGADA conserva una reserva o reunión "
                        "activa. Requiere revisión administrativa."
                    )
                pago = Pago.objects.filter(id_prestacion_id=prestacion.pk).first()
                if pago is None or pago.estado_pago != "RETENIDO":
                    return conflicto(
                        "La prestación solo puede reanudarse con pago RETENIDO."
                    )
                bloque = Disponibilidad.objects.select_for_update().filter(
                    pk=id_nuevo
                ).first()
                if bloque is None:
                    return conflicto(
                        "El nuevo bloque no existe.",
                        status.HTTP_404_NOT_FOUND,
                    )
                if bloque.id_profesional_id != prestacion.id_profesional_id:
                    return conflicto(
                        "El bloque no pertenece al profesional de la prestación.",
                        status.HTTP_400_BAD_REQUEST,
                    )
                if bloque.estado != "DISPONIBLE":
                    return conflicto("El nuevo bloque no está disponible.")
                if bloque.hora_inicio >= bloque.hora_fin:
                    return conflicto(
                        "El horario del bloque es inválido.",
                        status.HTTP_400_BAD_REQUEST,
                    )
                fecha_nueva = inicio_bloque(bloque)
                if fecha_nueva <= timezone.now():
                    return conflicto("El nuevo horario está en el pasado.")
                if ReservaDisponibilidad.objects.filter(
                    id_disponibilidad_id=id_nuevo,
                    estado="ACTIVA",
                ).exists():
                    return conflicto("El bloque ya tiene una reserva activa.")

                reunion_previa = (
                    ReunionSolicitud.objects.filter(
                        id_solicitud_id=prestacion.id_solicitud_id,
                        id_profesional_id=prestacion.id_profesional_id,
                        estado="POSTERGADA",
                    ).order_by("-id_reunion").first()
                )
                modalidad = (
                    reunion_previa.modalidad if reunion_previa is not None
                    else SolicitudServicio.objects.filter(
                        pk=prestacion.id_solicitud_id
                    ).values_list("modalidad", flat=True).first()
                )
                ahora = timezone.now()
                nueva_reserva = ReservaDisponibilidad.objects.create(
                    id_disponibilidad=bloque,
                    id_solicitud_id=prestacion.id_solicitud_id,
                    estado="ACTIVA",
                    fecha_reserva=ahora,
                    fecha_cambio=None,
                    motivo_cambio=None,
                )
                bloque.estado = "RESERVADA"
                bloque.save(update_fields=["estado"])
                nueva_reunion = ReunionSolicitud.objects.create(
                    id_solicitud_id=prestacion.id_solicitud_id,
                    id_profesional_id=prestacion.id_profesional_id,
                    id_usuario_skilly=request.user,
                    fecha_hora=fecha_nueva,
                    modalidad=modalidad,
                    estado="AGENDADA",
                    enlace_reunion=None,
                )
                prestacion.estado = "CONTRATADA"
                prestacion.fecha_cierre = None
                prestacion.save(update_fields=["estado", "fecha_cierre"])
                SolicitudServicio.objects.filter(
                    pk=prestacion.id_solicitud_id
                ).update(fecha_actualizacion=ahora)
                CoordinacionSolicitud.objects.create(
                    id_solicitud_id=prestacion.id_solicitud_id,
                    id_usuario_skilly=request.user,
                    tipo="REAGENDAR",
                    detalle=(
                        f"Reanudación de prestación {prestacion.pk} desde "
                        f"POSTERGADA. Nueva reserva {nueva_reserva.pk}, "
                        f"bloque {bloque.pk}, reunión {nueva_reunion.pk}. "
                        f"Motivo: {motivo}"
                    ),
                    estado_resultante="CONTRATADA",
                    fecha_registro=ahora,
                )
                registrar_cambio(
                    request.user,
                    "reserva_disponibilidad",
                    nueva_reserva.pk,
                    "REAGENDAR",
                    f"Nueva reserva {nueva_reserva.pk} para bloque {bloque.pk}. "
                    f"Prestación reanudada {prestacion.pk}.",
                )
                registrar_cambio(
                    request.user,
                    "reunion_solicitud",
                    nueva_reunion.pk,
                    "REAGENDAR",
                    f"Nueva reunión {nueva_reunion.pk} AGENDADA para "
                    f"{fecha_nueva.isoformat()}, tras postergación.",
                )
                registrar_cambio(
                    request.user,
                    "prestacion_servicio",
                    prestacion.pk,
                    "REANUDAR",
                    f"Prestación {prestacion.pk} nuevamente CONTRATADA. "
                    f"Pago {pago.pk} continúa {pago.estado_pago}.",
                )
                return Response({
                    "mensaje": "Prestación reanudada y reunión agendada.",
                    "prestacion_estado": "CONTRATADA",
                    "pago_estado": pago.estado_pago,
                    "reserva": ReservaDisponibilidadAdministracionSerializer(
                        nueva_reserva
                    ).data,
                    "reunion": {
                        "id_reunion": nueva_reunion.pk,
                        "estado": nueva_reunion.estado,
                        "fecha_hora": nueva_reunion.fecha_hora,
                    },
                }, status=status.HTTP_200_OK)

            # REAGENDAR normal (y POSTERGAR con fecha) mantiene el flujo original.
            if reserva_actual is None:
                return conflicto("La prestación no tiene una reserva activa.")
            id_anterior = reserva_actual.id_disponibilidad_id
            if id_nuevo == id_anterior:
                return conflicto(
                    "El bloque nuevo debe ser diferente del actual.",
                    status.HTTP_400_BAD_REQUEST,
                )
            bloques = {
                bloque.pk: bloque
                for bloque in Disponibilidad.objects.select_for_update()
                .filter(pk__in=[id_anterior, id_nuevo])
                .order_by("id_disponibilidad")
            }
            anterior = bloques.get(id_anterior)
            nuevo = bloques.get(id_nuevo)
            if anterior is None or nuevo is None:
                return conflicto(
                    "El bloque anterior o nuevo no existe.",
                    status.HTTP_404_NOT_FOUND,
                )
            if (
                anterior.id_profesional_id != prestacion.id_profesional_id
                or nuevo.id_profesional_id != prestacion.id_profesional_id
            ):
                return conflicto(
                    "Los bloques deben pertenecer al profesional.",
                    status.HTTP_400_BAD_REQUEST,
                )
            if anterior.estado != "RESERVADA":
                return conflicto("El bloque anterior no figura como reservado.")
            if nuevo.estado != "DISPONIBLE":
                return conflicto("El nuevo bloque no está disponible.")
            if nuevo.hora_inicio >= nuevo.hora_fin:
                return conflicto(
                    "El horario del bloque nuevo es inválido.",
                    status.HTTP_400_BAD_REQUEST,
                )
            if ReservaDisponibilidad.objects.filter(
                id_disponibilidad_id=id_nuevo, estado="ACTIVA"
            ).exists():
                return conflicto("El bloque nuevo ya tiene reserva activa.")
            if ReservaDisponibilidad.objects.filter(
                id_disponibilidad_id=id_anterior, estado="ACTIVA"
            ).exclude(pk=reserva_actual.pk).exists():
                return conflicto("El bloque anterior tiene otra reserva activa.")
            fecha_nueva = inicio_bloque(nuevo)
            if fecha_nueva <= timezone.now():
                return conflicto("El nuevo horario está en el pasado.")
            if reunion is not None and reunion.fecha_hora != inicio_bloque(anterior):
                return conflicto(
                    "La reunión AGENDADA no coincide con el bloque anterior. "
                    "No se modificará automáticamente."
                )

            resultado = super().post(request, id_prestacion)
            if resultado.status_code != status.HTTP_200_OK:
                transaction.set_rollback(True)
                return resultado
            if reunion is not None:
                fecha_previa = reunion.fecha_hora
                reunion.fecha_hora = fecha_nueva
                reunion.save(update_fields=["fecha_hora"])
                registrar_cambio(
                    request.user,
                    "reunion_solicitud",
                    reunion.pk,
                    accion,
                    f"Reunión {reunion.pk} actualizada de "
                    f"{fecha_previa.isoformat()} a {fecha_nueva.isoformat()}. "
                    f"Prestación {prestacion.pk}.",
                )
            return resultado
