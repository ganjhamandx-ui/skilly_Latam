"""Reagendamiento solicitado por la organización y coordinado en SKILLY.

No libera pagos. La operación final usa la agenda segura existente y queda
bloqueada hasta recibir las confirmaciones exigidas.
"""
from datetime import datetime
from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsAdministracionSkilly, EsProfesional
from coordinacion.agenda_segura import GestionAgendaPrestacionSeguraAdministracionView
from coordinacion.control_responsable import _verificar_responsable
from coordinacion.models import PrestacionServicio
from profesionales.models import Profesional
from solicitudes.models import Disponibilidad, ReservaDisponibilidad, SolicitudServicio
from solicitudes.referencias import leer_referencia_seguimiento

from .models import ESTADOS_ABIERTOS, EventoReagendamiento, SolicitudReagendamiento


def error(mensaje, codigo=status.HTTP_409_CONFLICT):
    return Response({"mensaje": mensaje}, status=codigo)


def horario(bloque):
    if bloque is None:
        return None
    return {
        "id_disponibilidad": bloque.pk,
        "fecha": bloque.fecha.isoformat(),
        "hora_inicio": bloque.hora_inicio.strftime("%H:%M"),
        "hora_fin": bloque.hora_fin.strftime("%H:%M"),
    }


def comienzo(bloque):
    return timezone.make_aware(
        datetime.combine(bloque.fecha, bloque.hora_inicio), timezone.get_current_timezone()
    )


def disponible(bloque, prestacion, original_id):
    return bool(
        bloque is not None
        and bloque.id_profesional_id == prestacion.id_profesional_id
        and bloque.pk != original_id
        and bloque.estado == "DISPONIBLE"
        and bloque.hora_inicio < bloque.hora_fin
        and comienzo(bloque) > timezone.now()
        and not ReservaDisponibilidad.objects.filter(id_disponibilidad_id=bloque.pk, estado="ACTIVA").exists()
        # Evita reasignar un horario superpuesto a otra reserva activa del profesional.
        and not ReservaDisponibilidad.objects.filter(
            estado="ACTIVA",
            id_disponibilidad__id_profesional_id=prestacion.id_profesional_id,
            id_disponibilidad__fecha=bloque.fecha,
            id_disponibilidad__hora_inicio__lt=bloque.hora_fin,
            id_disponibilidad__hora_fin__gt=bloque.hora_inicio,
        ).exclude(id_disponibilidad_id=original_id).exists()
    )


def opciones(prestacion, original_id):
    bloques = Disponibilidad.objects.filter(
        id_profesional_id=prestacion.id_profesional_id, estado="DISPONIBLE",
        fecha__gte=timezone.localdate(),
    ).order_by("fecha", "hora_inicio", "id_disponibilidad")[:250]
    return [horario(b) for b in bloques if disponible(b, prestacion, original_id)]


def reserva_vigente(prestacion):
    reservas = list(ReservaDisponibilidad.objects.filter(
        id_solicitud_id=prestacion.id_solicitud_id, estado="ACTIVA"
    ).select_related("id_disponibilidad").order_by("id_reserva")[:2])
    return reservas[0] if len(reservas) == 1 else None


def inicio_vencido(prestacion, reserva=None):
    reserva = reserva if reserva is not None else reserva_vigente(prestacion)
    return reserva is not None and comienzo(reserva.id_disponibilidad) <= timezone.now()


def acceso_solicitud(prestacion):
    if prestacion.estado != "CONTRATADA":
        return "Solo una prestación contratada admite solicitar este cambio."
    reserva = reserva_vigente(prestacion)
    if reserva is None:
        return "No existe una única reserva activa de primera reunión."
    if inicio_vencido(prestacion, reserva):
        return "La primera reunión ya comenzó o su horario pasó. No se puede solicitar su reagendamiento."
    if SolicitudReagendamiento.objects.filter(
        prestacion_id=prestacion.pk, estado__in=ESTADOS_ABIERTOS
    ).exists():
        return "Ya existe una solicitud de reagendamiento abierta."
    return None


def evento(obj, actor, accion, detalle):
    EventoReagendamiento.objects.create(
        reagendamiento=obj, actor=actor, accion=accion, detalle=detalle[:2000]
    )


def serializar(obj, mostrar_eventos=True):
    propuesto = Disponibilidad.objects.filter(pk=obj.bloque_propuesto_id).first() if obj.bloque_propuesto_id else None
    original = Disponibilidad.objects.filter(pk=obj.bloque_original_id).first()
    datos = {
        "id": obj.pk, "id_prestacion": obj.prestacion_id,
        "estado": obj.estado, "motivo": obj.motivo_organizacion,
        "motivo_profesional": obj.motivo_profesional,
        "bloque_original": horario(original), "bloque_propuesto": horario(propuesto),
        "fecha_creacion": obj.fecha_creacion.isoformat(),
        "fecha_actualizacion": obj.fecha_actualizacion.isoformat(),
        "plazo_vencido": bool(original and comienzo(original) <= timezone.now()),
    }
    if mostrar_eventos:
        datos["historial"] = [
            {"actor": e.actor, "accion": e.accion, "detalle": e.detalle, "fecha": e.fecha.isoformat()}
            for e in obj.eventos.all()
        ]
    return datos


def texto_motivo(valor):
    return valor.strip() if isinstance(valor, str) else ""


def prestar(solicitud_id):
    return PrestacionServicio.objects.filter(
        id_solicitud_id=solicitud_id
    ).select_related("id_solicitud").first()


@method_decorator(csrf_protect, name="dispatch")
class OrganizacionReagendamientoView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def _prestacion(self, referencia):
        datos = leer_referencia_seguimiento(referencia)
        if not datos:
            return None
        solicitud = SolicitudServicio.objects.filter(
            pk=datos["id_solicitud"], id_contacto_id=datos["id_contacto"]
        ).first()
        return prestar(solicitud.pk) if solicitud else None

    def get(self, request, referencia):
        prestacion = self._prestacion(referencia)
        if prestacion is None:
            return error("Referencia de seguimiento no válida.", 404)
        items = SolicitudReagendamiento.objects.filter(
            prestacion_id=prestacion.pk
        ).order_by("-fecha_creacion")[:20]
        impedimento = acceso_solicitud(prestacion)
        return Response({
            "solicitudes": [serializar(x) for x in items],
            "permite_solicitar": impedimento is None,
            "motivo_no_disponible": impedimento,
        })

    def post(self, request, referencia):
        prestacion = self._prestacion(referencia)
        if prestacion is None:
            return error("Referencia de seguimiento no válida.", 404)
        accion = request.data.get("accion", "SOLICITAR")
        with transaction.atomic():
            prestacion = PrestacionServicio.objects.select_for_update().get(pk=prestacion.pk)
            if accion == "SOLICITAR":
                motivo = texto_motivo(request.data.get("motivo"))
                if not (15 <= len(motivo) <= 1000):
                    return error("Indica un motivo de entre 15 y 1000 caracteres.", 400)
                impedimento = acceso_solicitud(prestacion)
                if impedimento:
                    return error(impedimento)
                reserva = reserva_vigente(prestacion)
                obj = SolicitudReagendamiento.objects.create(
                    prestacion_id=prestacion.pk, solicitud_id=prestacion.id_solicitud_id,
                    profesional_id=prestacion.id_profesional_id,
                    bloque_original_id=reserva.id_disponibilidad_id,
                    motivo_organizacion=motivo,
                )
                evento(obj, "ORGANIZACION", "SOLICITAR", motivo)
                return Response({"mensaje": "Solicitud enviada a administración dentro de SKILLY.", "solicitud": serializar(obj)}, status=201)
            if accion in {"ACEPTAR_ALTERNATIVA", "NO_ACEPTAR_ALTERNATIVA"}:
                try:
                    caso_id = int(request.data.get("id"))
                except (TypeError, ValueError):
                    return error("Identificador de solicitud inválido.", 400)
                obj = SolicitudReagendamiento.objects.select_for_update().filter(
                    pk=caso_id, prestacion_id=prestacion.pk
                ).first()
                if obj is None or obj.estado != "PENDIENTE_ORGANIZACION":
                    return error("La alternativa ya no está pendiente de aceptación.")
                reserva = reserva_vigente(prestacion)
                if reserva is None or reserva.id_disponibilidad_id != obj.bloque_original_id:
                    return error("La reserva original cambió. Administración debe revisar el caso.")
                if inicio_vencido(prestacion, reserva):
                    return error("La primera reunión ya comenzó. Administración debe cerrar el caso sin cambiar la reserva.")
                if accion == "NO_ACEPTAR_ALTERNATIVA":
                    razon = texto_motivo(request.data.get("motivo"))
                    if not (10 <= len(razon) <= 500):
                        return error("Explica por qué no puedes aceptar la alternativa (10 a 500 caracteres).", 400)
                    propuesta_anterior = obj.bloque_propuesto_id
                    obj.estado = "PENDIENTE_ADMIN"
                    obj.bloque_propuesto_id = None
                    obj.requiere_confirmacion_organizacion = False
                    obj.save(update_fields=[
                        "estado", "bloque_propuesto_id", "requiere_confirmacion_organizacion",
                        "fecha_actualizacion",
                    ])
                    evento(obj, "ORGANIZACION", "NO_ACEPTAR_ALTERNATIVA", f"Bloque #{propuesta_anterior} no aceptado. Motivo: {razon}")
                    return Response({"mensaje": "Alternativa rechazada. Administración revisará una nueva propuesta dentro de SKILLY; la reserva original no cambia.", "solicitud": serializar(obj)})
                bloque = Disponibilidad.objects.filter(pk=obj.bloque_propuesto_id).first()
                if not disponible(bloque, prestacion, obj.bloque_original_id):
                    return error("La alternativa dejó de estar disponible; administración debe revisarla.")
                if not obj.requiere_confirmacion_organizacion:
                    return error("La alternativa todavía no está preparada para confirmación de la organización.")
                obj.estado = "LISTO_CONFIRMAR"
                obj.save(update_fields=["estado", "fecha_actualizacion"])
                evento(obj, "ORGANIZACION", "ACEPTAR_ALTERNATIVA", f"Aceptado bloque #{bloque.pk}: {bloque.fecha} {bloque.hora_inicio}–{bloque.hora_fin}; falta aplicación administrativa.")
                return Response({"mensaje": "Alternativa aceptada. Pendiente de confirmación administrativa.", "solicitud": serializar(obj)})
            return error("Acción no permitida.", 400)


@method_decorator(csrf_protect, name="dispatch")
class AdministracionReagendamientoView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        items = SolicitudReagendamiento.objects.all().order_by("-fecha_creacion")[:100]
        registros = []
        for obj in items:
            prestacion = PrestacionServicio.objects.filter(pk=obj.prestacion_id).first()
            if prestacion is None:
                continue
            data = serializar(obj)
            data["bloques_disponibles"] = opciones(prestacion, obj.bloque_original_id)
            registros.append(data)
        return Response({"solicitudes": registros})

    def post(self, request):
        try:
            pk = int(request.data.get("id"))
        except (TypeError, ValueError):
            return error("Identificador inválido.", 400)
        accion = request.data.get("accion")
        with transaction.atomic():
            obj_base = SolicitudReagendamiento.objects.filter(pk=pk).first()
            if obj_base is None:
                return error("Solicitud no encontrada.", 404)
            permiso = _verificar_responsable(request, obj_base.solicitud_id)
            if permiso is not None:
                return permiso
            prestacion = PrestacionServicio.objects.select_for_update().filter(pk=obj_base.prestacion_id).first()
            if prestacion is None:
                return error("La prestación no se encuentra disponible.")
            obj = SolicitudReagendamiento.objects.select_for_update().get(pk=pk)
            if obj.estado not in ESTADOS_ABIERTOS:
                return error("Esta solicitud ya está cerrada.")
            # Cierre administrativo trazable, sin tocar la agenda ni el pago.
            if accion in {"CERRAR_SIN_ACUERDO", "CERRAR_VENCIDA"}:
                original = Disponibilidad.objects.filter(pk=obj.bloque_original_id).first()
                if accion == "CERRAR_VENCIDA" and (original is None or comienzo(original) > timezone.now()):
                    return error("El horario original todavía no ha comenzado.")
                motivo = texto_motivo(request.data.get("motivo"))
                if accion == "CERRAR_SIN_ACUERDO" and not (10 <= len(motivo) <= 500):
                    return error("Indica el motivo de cierre (10 a 500 caracteres).", 400)
                obj.estado = "VENCIDA" if accion == "CERRAR_VENCIDA" else "SIN_ACUERDO"
                obj.save(update_fields=["estado", "fecha_actualizacion"])
                evento(obj, "ADMINISTRACION", accion, motivo or "La hora de inicio original ya transcurrió; no se modifica la reserva.")
                return Response({"mensaje": "Solicitud cerrada sin modificar la reserva original ni el pago.", "solicitud": serializar(obj)})
            if prestacion.estado != "CONTRATADA":
                return error("La prestación ya no admite este reagendamiento.")
            reserva = reserva_vigente(prestacion)
            if reserva is None or reserva.id_disponibilidad_id != obj.bloque_original_id:
                return error("La reserva original cambió. Debe revisarse la solicitud antes de actuar.")
            if inicio_vencido(prestacion, reserva):
                return error("La primera reunión ya comenzó; cierra la solicitud vencida sin modificar la reserva.")
            if accion == "SOLICITAR_BLOQUE" and obj.estado == "PENDIENTE_ADMIN":
                obj.estado = "ESPERANDO_NUEVO_BLOQUE"
                obj.save(update_fields=["estado", "fecha_actualizacion"])
                evento(obj, "ADMINISTRACION", "SOLICITAR_BLOQUE", "No hay un bloque adecuado; el profesional debe crear uno.")
                return Response({"mensaje": "Se solicitó disponibilidad al profesional.", "solicitud": serializar(obj)})
            if accion == "PROPONER" and obj.estado == "PENDIENTE_ADMIN":
                try:
                    bloque_id = int(request.data.get("id_disponibilidad"))
                except (TypeError, ValueError):
                    return error("Selecciona un bloque disponible.", 400)
                bloque = Disponibilidad.objects.select_for_update().filter(pk=bloque_id).first()
                if not disponible(bloque, prestacion, obj.bloque_original_id):
                    return error("El bloque ya no está disponible.")
                obj.bloque_propuesto_id = bloque.pk
                obj.requiere_confirmacion_organizacion = True
                obj.motivo_profesional = ""
                obj.estado = "PENDIENTE_PROFESIONAL"
                obj.save(update_fields=["bloque_propuesto_id", "requiere_confirmacion_organizacion", "motivo_profesional", "estado", "fecha_actualizacion"])
                evento(obj, "ADMINISTRACION", "PROPONER", f"Bloque #{bloque.pk}: {bloque.fecha} {bloque.hora_inicio}–{bloque.hora_fin}. Esperando aceptación profesional.")
                return Response({"mensaje": "Propuesta notificada al profesional dentro de SKILLY.", "solicitud": serializar(obj)})
            if accion == "CONFIRMAR" and obj.estado == "LISTO_CONFIRMAR":
                if not obj.requiere_confirmacion_organizacion:
                    return error("Falta la aceptación explícita de la organización para el horario propuesto.")
                # El único camino a LISTO_CONFIRMAR pasa por la aceptación de la organización;
                # tras propuesta administrativa, antes debe aceptar el profesional.
                bloque = Disponibilidad.objects.select_for_update().filter(pk=obj.bloque_propuesto_id).first()
                if not disponible(bloque, prestacion, obj.bloque_original_id):
                    return error("El bloque confirmado dejó de estar disponible.")
                # Misma operación y validaciones utilizadas por la agenda segura.
                solicitud_interna = SimpleNamespace(
                    user=request.user,
                    data={
                        "accion": "REAGENDAR", "motivo": f"Solicitud interna #{obj.pk}: {obj.motivo_organizacion[:300]}",
                        "id_disponibilidad_nueva": bloque.pk,
                    },
                )
                respuesta = GestionAgendaPrestacionSeguraAdministracionView().post(
                    solicitud_interna, prestacion.pk
                )
                if respuesta.status_code != 200:
                    transaction.set_rollback(True)
                    return respuesta
                obj.estado = "CONFIRMADO"
                obj.save(update_fields=["estado", "fecha_actualizacion"])
                evento(obj, "ADMINISTRACION", "CONFIRMAR", f"Reagendamiento confirmado en bloque #{bloque.pk}, mediante agenda segura.")
                return Response({"mensaje": "Reagendamiento confirmado. El nuevo horario está disponible para ambas partes en SKILLY.", "solicitud": serializar(obj), "agenda": respuesta.data})
            return error("Operación no válida para el estado actual.", 409)


@method_decorator(csrf_protect, name="dispatch")
class ProfesionalReagendamientoView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]

    def _profesional(self, request):
        return Profesional.objects.filter(id_usuario=request.user).first()

    def get(self, request):
        profesional = self._profesional(request)
        if profesional is None:
            return error("Perfil profesional no encontrado.", 404)
        items = SolicitudReagendamiento.objects.filter(
            profesional_id=profesional.pk
        ).order_by("-fecha_creacion")[:50]
        return Response({"solicitudes": [serializar(x) for x in items]})

    def post(self, request):
        profesional = self._profesional(request)
        if profesional is None:
            return error("Perfil profesional no encontrado.", 404)
        try:
            pk = int(request.data.get("id"))
        except (TypeError, ValueError):
            return error("Identificador inválido.", 400)
        with transaction.atomic():
            obj_base = SolicitudReagendamiento.objects.filter(pk=pk, profesional_id=profesional.pk).first()
            if obj_base is None:
                return error("Solicitud no encontrada.", 404)
            prestacion = PrestacionServicio.objects.select_for_update().filter(pk=obj_base.prestacion_id).first()
            if prestacion is None or prestacion.estado != "CONTRATADA":
                return error("La prestación no permite este cambio.")
            obj = SolicitudReagendamiento.objects.select_for_update().get(pk=pk)
            accion = request.data.get("accion")
            if obj.estado not in ESTADOS_ABIERTOS:
                return error("Esta solicitud ya está cerrada.")
            reserva = reserva_vigente(prestacion)
            if reserva is None or reserva.id_disponibilidad_id != obj.bloque_original_id:
                return error("La reserva original cambió. Administración debe revisar el caso.")
            if inicio_vencido(prestacion, reserva):
                return error("La primera reunión ya comenzó. Administración debe cerrar la solicitud vencida.")
            if obj.estado == "PENDIENTE_PROFESIONAL" and accion == "ACEPTAR":
                bloque = Disponibilidad.objects.select_for_update().filter(pk=obj.bloque_propuesto_id).first()
                if not disponible(bloque, prestacion, obj.bloque_original_id):
                    return error("El bloque ya no se encuentra disponible.")
                obj.estado = "PENDIENTE_ORGANIZACION"
                obj.requiere_confirmacion_organizacion = True
                obj.save(update_fields=["estado", "requiere_confirmacion_organizacion", "fecha_actualizacion"])
                evento(obj, "PROFESIONAL", "ACEPTAR", f"Aceptado bloque #{bloque.pk}: {bloque.fecha} {bloque.hora_inicio}–{bloque.hora_fin}; esperando confirmación de la organización.")
                return Response({"mensaje": "Horario aceptado. SKILLY solicitará a la organización confirmar exactamente este bloque.", "solicitud": serializar(obj)})
            if obj.estado == "PENDIENTE_PROFESIONAL" and accion == "RECHAZAR":
                motivo = texto_motivo(request.data.get("motivo"))
                if not (10 <= len(motivo) <= 500):
                    return error("Indica por qué ya no puedes usar el bloque (10 a 500 caracteres).", 400)
                obj.estado = "ESPERANDO_NUEVO_BLOQUE"
                obj.bloque_propuesto_id = None
                obj.requiere_confirmacion_organizacion = False
                obj.motivo_profesional = motivo
                obj.save(update_fields=["estado", "bloque_propuesto_id", "requiere_confirmacion_organizacion", "motivo_profesional", "fecha_actualizacion"])
                evento(obj, "PROFESIONAL", "RECHAZAR", motivo)
                return Response({"mensaje": "Horario rechazado. Debes ofrecer una alternativa desde SKILLY.", "solicitud": serializar(obj)})
            if obj.estado == "ESPERANDO_NUEVO_BLOQUE" and accion == "CREAR_ALTERNATIVA":
                from rest_framework import serializers

                class BloqueDatos(serializers.Serializer):
                    fecha = serializers.DateField()
                    hora_inicio = serializers.TimeField()
                    hora_fin = serializers.TimeField()

                entrada = BloqueDatos(data=request.data)
                if not entrada.is_valid():
                    return Response(entrada.errors, status=400)
                d = entrada.validated_data
                if d["hora_inicio"] >= d["hora_fin"]:
                    return error("La hora de inicio debe ser anterior a la de término.", 400)
                bloque_fecha = SimpleNamespace(fecha=d["fecha"], hora_inicio=d["hora_inicio"])
                if comienzo(bloque_fecha) <= timezone.now():
                    return error("El nuevo bloque debe estar en el futuro.", 400)
                # Evita horarios solapados incluso con bloques reservados o pendientes.
                conflicto = Disponibilidad.objects.select_for_update().filter(
                    id_profesional=profesional, fecha=d["fecha"],
                    hora_inicio__lt=d["hora_fin"], hora_fin__gt=d["hora_inicio"],
                ).exclude(estado="DESHABILITADO").exists()
                if conflicto:
                    return error("Ya existe un bloque del profesional que se superpone a este horario.")
                bloque = Disponibilidad.objects.create(
                    id_profesional=profesional, estado="DISPONIBLE",
                    fecha=d["fecha"], hora_inicio=d["hora_inicio"], hora_fin=d["hora_fin"],
                )
                obj.bloque_propuesto_id = bloque.pk
                obj.requiere_confirmacion_organizacion = True
                obj.estado = "PENDIENTE_ORGANIZACION"
                obj.save(update_fields=["bloque_propuesto_id", "requiere_confirmacion_organizacion", "estado", "fecha_actualizacion"])
                evento(obj, "PROFESIONAL", "CREAR_ALTERNATIVA", f"Nueva alternativa #{bloque.pk}: {bloque.fecha} {bloque.hora_inicio}–{bloque.hora_fin}. Enviada al seguimiento de la organización.")
                return Response({"mensaje": "Disponibilidad creada. La organización debe aceptar esta alternativa.", "solicitud": serializar(obj)})
            return error("Operación no permitida en el estado actual.")
