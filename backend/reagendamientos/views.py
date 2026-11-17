"""Reagendamiento bilateral y trazable de la primera reunión en SKILLY.

La agenda solo cambia en la confirmación administrativa final. Este módulo no
cancela prestaciones, no modifica pagos y no ejecuta cobros o devoluciones.
"""
from datetime import datetime
import hashlib
import json
import os
from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
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

from .models import (
    ESTADOS_ABIERTOS,
    AlternativaReagendamiento,
    EventoReagendamiento,
    SolicitudReagendamiento,
)


POLITICA_VERSION = "PRT-33-35-v1-2026-11-17"
POLITICA_TEXTO = (
    "Al solicitar el reagendamiento de la primera reunión, quien inicia el "
    "procedimiento acepta que la nueva fecha se coordine conforme a la "
    "disponibilidad válida del profesional. SKILLY revisará la solicitud y "
    "coordinará un horario disponible. La solicitud no modifica inmediatamente "
    "la reserva ni genera cobros, sanciones o reembolsos automáticos."
)
MAX_ALTERNATIVAS = 10
MAX_EVIDENCIA = 5 * 1024 * 1024
MIME_EVIDENCIA = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class BloqueNuevoSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    hora_inicio = serializers.TimeField()
    hora_fin = serializers.TimeField()

    def validate(self, data):
        if data["hora_inicio"] >= data["hora_fin"]:
            raise serializers.ValidationError(
                "La hora de inicio debe ser anterior a la hora de término."
            )
        candidato = SimpleNamespace(
            fecha=data["fecha"], hora_inicio=data["hora_inicio"]
        )
        if comienzo(candidato) <= timezone.now():
            raise serializers.ValidationError("Todos los bloques deben ser futuros.")
        return data


def error(mensaje, codigo=status.HTTP_409_CONFLICT):
    return Response({"mensaje": mensaje}, status=codigo)


def primer_error_validacion(exc):
    detalle = exc.detail
    for _ in range(3):
        if isinstance(detalle, dict):
            detalle = next(iter(detalle.values()), "Datos inválidos.")
        elif isinstance(detalle, (list, tuple)):
            detalle = detalle[0] if detalle else "Datos inválidos."
        else:
            break
    return str(detalle)


def politica():
    return {"version": POLITICA_VERSION, "texto": POLITICA_TEXTO}


def politica_aceptada(data):
    aceptada = data.get("acepta_politica")
    if isinstance(aceptada, str):
        aceptada = aceptada.strip().lower() in {"1", "true", "si", "sí", "on"}
    return aceptada is True and data.get("politica_version") == POLITICA_VERSION


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
        datetime.combine(bloque.fecha, bloque.hora_inicio),
        timezone.get_current_timezone(),
    )


def disponible(bloque, prestacion, original_id):
    return bool(
        bloque is not None
        and bloque.id_profesional_id == prestacion.id_profesional_id
        and bloque.pk != original_id
        and bloque.estado == "DISPONIBLE"
        and bloque.hora_inicio < bloque.hora_fin
        and comienzo(bloque) > timezone.now()
        and not ReservaDisponibilidad.objects.filter(
            id_disponibilidad_id=bloque.pk, estado="ACTIVA"
        ).exists()
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
        id_profesional_id=prestacion.id_profesional_id,
        estado="DISPONIBLE",
        fecha__gte=timezone.localdate(),
    ).order_by("fecha", "hora_inicio", "id_disponibilidad")[:250]
    return [horario(bloque) for bloque in bloques if disponible(bloque, prestacion, original_id)]


def reserva_vigente(prestacion):
    reservas = list(
        ReservaDisponibilidad.objects.filter(
            id_solicitud_id=prestacion.id_solicitud_id, estado="ACTIVA"
        )
        .select_related("id_disponibilidad")
        .order_by("id_reserva")[:2]
    )
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
        return "La primera reunión ya comenzó o su horario pasó."
    if SolicitudReagendamiento.objects.filter(
        prestacion_id=prestacion.pk, estado__in=ESTADOS_ABIERTOS
    ).exists():
        return "Ya existe una solicitud de reagendamiento abierta."
    return None


def evento(obj, actor, accion, detalle):
    EventoReagendamiento.objects.create(
        reagendamiento=obj,
        actor=actor,
        accion=accion,
        detalle=str(detalle)[:2000],
    )


def texto_motivo(valor):
    return valor.strip() if isinstance(valor, str) else ""


def prestar(solicitud_id):
    return (
        PrestacionServicio.objects.filter(id_solicitud_id=solicitud_id)
        .select_related("id_solicitud")
        .first()
    )


def evidencia_validada(archivo, obligatoria=True):
    if archivo is None:
        if obligatoria:
            raise serializers.ValidationError("Adjunta una evidencia justificativa.")
        return {}
    nombre = os.path.basename(str(archivo.name or "").replace("\\", "/"))[:150]
    extension = os.path.splitext(nombre)[1].lower()
    if extension not in MIME_EVIDENCIA or archivo.size <= 0 or archivo.size > MAX_EVIDENCIA:
        raise serializers.ValidationError("Solo se admite PDF, JPG o PNG de 1 byte a 5 MB.")
    contenido = archivo.read(MAX_EVIDENCIA + 1)
    if len(contenido) > MAX_EVIDENCIA:
        raise serializers.ValidationError("La evidencia supera 5 MB.")
    if extension == ".pdf":
        contenido_valido = contenido.startswith(b"%PDF-")
    elif extension == ".png":
        contenido_valido = contenido.startswith(b"\x89PNG\r\n\x1a\n")
    else:
        contenido_valido = contenido.startswith(b"\xff\xd8\xff") and contenido.endswith(b"\xff\xd9")
    if not contenido_valido:
        raise serializers.ValidationError("El contenido no coincide con la extensión de la evidencia.")
    if archivo.content_type not in {MIME_EVIDENCIA[extension], "application/octet-stream"}:
        raise serializers.ValidationError("El tipo MIME de la evidencia no es válido.")
    return {
        "evidencia_nombre": nombre,
        "evidencia_mime": MIME_EVIDENCIA[extension],
        "evidencia_sha256": hashlib.sha256(contenido).hexdigest(),
        "evidencia_contenido": contenido,
    }


def _lista_json(data, nombre):
    valor = data.get(nombre, [])
    if valor in (None, ""):
        return []
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError(f"{nombre} no contiene JSON válido.") from exc
    if not isinstance(valor, list):
        raise serializers.ValidationError(f"{nombre} debe ser una lista.")
    return valor


def alternativas_validadas(data):
    existentes = _lista_json(data, "alternativas_existentes")
    nuevas = _lista_json(data, "alternativas_nuevas")
    try:
        existentes = [int(valor) for valor in existentes]
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError("Las alternativas existentes deben ser identificadores.") from exc
    if any(valor < 1 for valor in existentes) or len(set(existentes)) != len(existentes):
        raise serializers.ValidationError("Las alternativas existentes no son válidas o están repetidas.")
    serializer = BloqueNuevoSerializer(data=nuevas, many=True)
    serializer.is_valid(raise_exception=True)
    total = len(existentes) + len(serializer.validated_data)
    if not 1 <= total <= MAX_ALTERNATIVAS:
        raise serializers.ValidationError(
            f"Debes proponer entre 1 y {MAX_ALTERNATIVAS} bloques."
        )
    return existentes, serializer.validated_data


def _crear_bloque(profesional, datos):
    conflicto = (
        Disponibilidad.objects.select_for_update()
        .filter(
            id_profesional=profesional,
            fecha=datos["fecha"],
            hora_inicio__lt=datos["hora_fin"],
            hora_fin__gt=datos["hora_inicio"],
        )
        .exclude(estado="DESHABILITADO")
        .exists()
    )
    if conflicto:
        raise serializers.ValidationError(
            "Uno de los bloques nuevos se superpone con disponibilidad existente."
        )
    return Disponibilidad.objects.create(
        id_profesional=profesional,
        estado="DISPONIBLE",
        fecha=datos["fecha"],
        hora_inicio=datos["hora_inicio"],
        hora_fin=datos["hora_fin"],
    )


def registrar_alternativas(obj, prestacion, profesional, data, origen, estado):
    existentes, nuevas = alternativas_validadas(data)
    bloques = []
    for bloque_id in existentes:
        bloque = Disponibilidad.objects.select_for_update().filter(pk=bloque_id).first()
        if not disponible(bloque, prestacion, obj.bloque_original_id):
            raise serializers.ValidationError(
                "Uno de los bloques seleccionados ya no está disponible."
            )
        bloques.append(bloque)
    for datos in nuevas:
        bloque = _crear_bloque(profesional, datos)
        if not disponible(bloque, prestacion, obj.bloque_original_id):
            raise serializers.ValidationError("No fue posible habilitar un bloque nuevo.")
        bloques.append(bloque)
    for bloque in bloques:
        AlternativaReagendamiento.objects.create(
            reagendamiento=obj,
            bloque_id=bloque.pk,
            origen=origen,
            estado=estado,
            fecha=bloque.fecha,
            hora_inicio=bloque.hora_inicio,
            hora_fin=bloque.hora_fin,
        )
    return bloques


def detalle_bloques(bloques):
    return "; ".join(
        f"#{bloque.pk}: {bloque.fecha} {bloque.hora_inicio:%H:%M}–{bloque.hora_fin:%H:%M}"
        for bloque in bloques
    )


def serializar_alternativa(alternativa, prestacion, original_id):
    bloque = Disponibilidad.objects.filter(pk=alternativa.bloque_id).first()
    if alternativa.fecha and alternativa.hora_inicio and alternativa.hora_fin:
        datos = {
            "id_disponibilidad": alternativa.bloque_id,
            "fecha": alternativa.fecha.isoformat(),
            "hora_inicio": alternativa.hora_inicio.strftime("%H:%M"),
            "hora_fin": alternativa.hora_fin.strftime("%H:%M"),
        }
    else:
        datos = horario(bloque) or {"id_disponibilidad": alternativa.bloque_id}
    datos.update({
        "origen": alternativa.origen,
        "estado": alternativa.estado,
        "disponible": disponible(bloque, prestacion, original_id),
    })
    return datos


def serializar(obj, actor="ADMINISTRACION", mostrar_eventos=True):
    prestacion = PrestacionServicio.objects.filter(pk=obj.prestacion_id).first()
    propuesto = (
        Disponibilidad.objects.filter(pk=obj.bloque_propuesto_id).first()
        if obj.bloque_propuesto_id else None
    )
    original = Disponibilidad.objects.filter(pk=obj.bloque_original_id).first()
    motivo_principal = (
        obj.motivo_organizacion if obj.iniciador == "ORGANIZACION" else obj.motivo_profesional
    )
    datos = {
        "id": obj.pk,
        "id_prestacion": obj.prestacion_id,
        "iniciador": obj.iniciador,
        "estado": obj.estado,
        "motivo": motivo_principal,
        "motivo_organizacion": obj.motivo_organizacion,
        "motivo_profesional": obj.motivo_profesional,
        "bloque_original": horario(original),
        "bloque_propuesto": horario(propuesto),
        "alternativas": [
            serializar_alternativa(item, prestacion, obj.bloque_original_id)
            for item in obj.alternativas.all()
            if actor != "ORGANIZACION" or item.estado in {"HABILITADA", "SELECCIONADA"}
        ] if prestacion is not None else [],
        "contrapropuesta_profesional_usada": obj.contrapropuesta_profesional_usada,
        "organizacion_autorizo_cambio": obj.organizacion_autorizo_cambio,
        "profesional_confirmo_bloque": obj.profesional_confirmo_bloque,
        "politica_version": obj.politica_version,
        "politica_aceptada_en": (
            obj.politica_aceptada_en.isoformat() if obj.politica_aceptada_en else None
        ),
        "fecha_creacion": obj.fecha_creacion.isoformat(),
        "fecha_actualizacion": obj.fecha_actualizacion.isoformat(),
        "plazo_vencido": bool(original and comienzo(original) <= timezone.now()),
    }
    if actor in {"ADMINISTRACION", "PROFESIONAL"}:
        datos["evidencia_disponible"] = bool(obj.evidencia_sha256)
        datos["evidencia_nombre"] = obj.evidencia_nombre
    if actor == "ADMINISTRACION" and obj.evidencia_sha256:
        datos["evidencia_url"] = f"/api/reagendamientos/administracion/{obj.pk}/evidencia/"
    if mostrar_eventos:
        datos["historial"] = [
            {
                "actor": item.actor,
                "accion": item.accion,
                "detalle": item.detalle,
                "fecha": item.fecha.isoformat(),
            }
            for item in obj.eventos.all()
        ]
    return datos


def _prestaciones_habilitadas(profesional):
    resultado = []
    prestaciones = (
        PrestacionServicio.objects.filter(
            id_profesional=profesional, estado="CONTRATADA"
        )
        .select_related("id_solicitud")
        .order_by("id_prestacion")[:100]
    )
    for prestacion in prestaciones:
        if acceso_solicitud(prestacion) is not None:
            continue
        reserva = reserva_vigente(prestacion)
        resultado.append({
            "id_prestacion": prestacion.pk,
            "objetivo": prestacion.id_solicitud.objetivo,
            "bloque_original": horario(reserva.id_disponibilidad),
            "bloques_disponibles": opciones(prestacion, reserva.id_disponibilidad_id),
        })
    return resultado


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
        items = (
            SolicitudReagendamiento.objects.filter(prestacion_id=prestacion.pk)
            .defer("evidencia_contenido")
            .order_by("-fecha_creacion")[:20]
        )
        impedimento = acceso_solicitud(prestacion)
        registros = [serializar(item, "ORGANIZACION") for item in items]
        for datos in registros:
            if datos["estado"] == "ESPERANDO_SELECCION":
                original = datos.get("bloque_original") or {}
                original_id = original.get("id_disponibilidad")
                datos["bloques_disponibles"] = (
                    opciones(prestacion, original_id) if original_id else []
                )
        return Response({
            "solicitudes": registros,
            "permite_solicitar": impedimento is None,
            "motivo_no_disponible": impedimento,
            "politica": politica(),
        })

    def post(self, request, referencia):
        prestacion = self._prestacion(referencia)
        if prestacion is None:
            return error("Referencia de seguimiento no válida.", 404)
        accion = str(request.data.get("accion", "SOLICITAR")).strip().upper()
        try:
            with transaction.atomic():
                prestacion = PrestacionServicio.objects.select_for_update().get(pk=prestacion.pk)
                if accion == "SOLICITAR":
                    motivo = texto_motivo(request.data.get("motivo"))
                    if not 15 <= len(motivo) <= 1000:
                        return error("Indica un motivo de entre 15 y 1000 caracteres.", 400)
                    if not politica_aceptada(request.data):
                        return error("Debes leer y aceptar la política vigente.", 400)
                    impedimento = acceso_solicitud(prestacion)
                    if impedimento:
                        return error(impedimento)
                    reserva = reserva_vigente(prestacion)
                    obj = SolicitudReagendamiento.objects.create(
                        prestacion_id=prestacion.pk,
                        solicitud_id=prestacion.id_solicitud_id,
                        profesional_id=prestacion.id_profesional_id,
                        bloque_original_id=reserva.id_disponibilidad_id,
                        iniciador="ORGANIZACION",
                        motivo_organizacion=motivo,
                        organizacion_autorizo_cambio=True,
                        profesional_confirmo_bloque=False,
                        politica_version=POLITICA_VERSION,
                        politica_actor="ORGANIZACION",
                        politica_aceptada_en=timezone.now(),
                    )
                    evento(obj, "ORGANIZACION", "SOLICITAR", motivo)
                    return Response({
                        "mensaje": "Solicitud enviada a administración dentro de SKILLY.",
                        "solicitud": serializar(obj, "ORGANIZACION"),
                    }, status=201)

                try:
                    caso_id = int(request.data.get("id"))
                except (TypeError, ValueError):
                    return error("Identificador de solicitud inválido.", 400)
                obj = SolicitudReagendamiento.objects.select_for_update().filter(
                    pk=caso_id, prestacion_id=prestacion.pk
                ).first()
                if obj is None or obj.estado not in ESTADOS_ABIERTOS:
                    return error("La solicitud ya no admite esta acción.")
                reserva = reserva_vigente(prestacion)
                if reserva is None or reserva.id_disponibilidad_id != obj.bloque_original_id:
                    return error("La reserva original cambió. Administración debe revisar el caso.")
                if inicio_vencido(prestacion, reserva):
                    return error("La primera reunión ya comenzó. Administración debe gestionar el vencimiento.")

                if accion == "ESPERAR_SELECCION" and obj.estado == "PENDIENTE_ORGANIZACION":
                    obj.estado = "ESPERANDO_SELECCION"
                    obj.save(update_fields=["estado", "fecha_actualizacion"])
                    evento(
                        obj,
                        "ORGANIZACION",
                        "ESPERAR_SELECCION",
                        "Ninguna alternativa fue seleccionada; el expediente continúa abierto sin reiniciar la negociación.",
                    )
                    return Response({
                        "mensaje": "El caso quedó pendiente de selección de horario.",
                        "solicitud": serializar(obj, "ORGANIZACION"),
                    })

                if accion == "SELECCIONAR" and obj.estado in {"PENDIENTE_ORGANIZACION", "ESPERANDO_SELECCION"}:
                    try:
                        bloque_id = int(request.data.get("id_disponibilidad"))
                    except (TypeError, ValueError):
                        return error("Selecciona un horario válido.", 400)
                    alternativa = AlternativaReagendamiento.objects.select_for_update().filter(
                        reagendamiento=obj, bloque_id=bloque_id, estado="HABILITADA"
                    ).first()
                    bloque = None
                    if alternativa is None and obj.estado == "ESPERANDO_SELECCION":
                        bloque = Disponibilidad.objects.select_for_update().filter(pk=bloque_id).first()
                        if not disponible(bloque, prestacion, obj.bloque_original_id):
                            return error("El horario ya no se encuentra disponible.")
                        alternativa, _ = AlternativaReagendamiento.objects.update_or_create(
                            reagendamiento=obj,
                            bloque_id=bloque_id,
                            defaults={
                                "origen": "DISPONIBILIDAD_POSTERIOR",
                                "estado": "HABILITADA",
                                "fecha": bloque.fecha,
                                "hora_inicio": bloque.hora_inicio,
                                "hora_fin": bloque.hora_fin,
                            },
                        )
                    elif alternativa is not None:
                        bloque = Disponibilidad.objects.select_for_update().filter(pk=bloque_id).first()
                    else:
                        return error("El horario no pertenece a las alternativas habilitadas.")
                    if not disponible(bloque, prestacion, obj.bloque_original_id):
                        return error("El horario ya no se encuentra disponible.")
                    if not obj.profesional_confirmo_bloque:
                        return error("El horario todavía no cuenta con autorización profesional.")
                    obj.alternativas.exclude(pk=alternativa.pk).filter(
                        estado="HABILITADA"
                    ).update(estado="NO_SELECCIONADA")
                    alternativa.estado = "SELECCIONADA"
                    alternativa.save(update_fields=["estado"])
                    obj.bloque_propuesto_id = bloque.pk
                    obj.organizacion_autorizo_cambio = True
                    obj.requiere_confirmacion_organizacion = False
                    obj.estado = "LISTO_CONFIRMAR"
                    obj.save(update_fields=[
                        "bloque_propuesto_id",
                        "organizacion_autorizo_cambio",
                        "requiere_confirmacion_organizacion",
                        "estado",
                        "fecha_actualizacion",
                    ])
                    evento(
                        obj,
                        "ORGANIZACION",
                        "SELECCIONAR",
                        f"Seleccionado bloque #{bloque.pk}; queda pendiente la aplicación administrativa.",
                    )
                    return Response({
                        "mensaje": "Horario seleccionado. Administración debe aplicar el cambio.",
                        "solicitud": serializar(obj, "ORGANIZACION"),
                    })
                return error("Acción no permitida para el estado actual.", 400)
        except IntegrityError:
            return error("Ya existe una solicitud abierta o la acción fue procesada previamente.")


@method_decorator(csrf_protect, name="dispatch")
class AdministracionReagendamientoView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]

    def get(self, request):
        items = (
            SolicitudReagendamiento.objects.defer("evidencia_contenido")
            .order_by("-fecha_creacion")[:100]
        )
        registros = []
        for obj in items:
            prestacion = PrestacionServicio.objects.filter(pk=obj.prestacion_id).first()
            if prestacion is None:
                continue
            datos = serializar(obj, "ADMINISTRACION")
            datos["bloques_disponibles"] = opciones(prestacion, obj.bloque_original_id)
            registros.append(datos)
        return Response({"solicitudes": registros})

    def post(self, request):
        try:
            pk = int(request.data.get("id"))
        except (TypeError, ValueError):
            return error("Identificador inválido.", 400)
        accion = str(request.data.get("accion", "")).strip().upper()
        with transaction.atomic():
            obj_base = SolicitudReagendamiento.objects.filter(pk=pk).first()
            if obj_base is None:
                return error("Solicitud no encontrada.", 404)
            permiso = _verificar_responsable(request, obj_base.solicitud_id)
            if permiso is not None:
                return permiso
            prestacion = PrestacionServicio.objects.select_for_update().filter(
                pk=obj_base.prestacion_id
            ).first()
            if prestacion is None:
                return error("La prestación no se encuentra disponible.")
            obj = SolicitudReagendamiento.objects.select_for_update().get(pk=pk)
            if obj.estado not in ESTADOS_ABIERTOS:
                return error("Esta solicitud ya está cerrada.")

            if accion in {"CERRAR_SIN_ACUERDO", "CERRAR_VENCIDA"}:
                original = Disponibilidad.objects.filter(pk=obj.bloque_original_id).first()
                if accion == "CERRAR_VENCIDA" and (
                    original is None or comienzo(original) > timezone.now()
                ):
                    return error("El horario original todavía no ha comenzado.")
                motivo = texto_motivo(request.data.get("motivo"))
                if accion == "CERRAR_SIN_ACUERDO" and not 10 <= len(motivo) <= 500:
                    return error("Indica el motivo de cierre (10 a 500 caracteres).", 400)
                obj.estado = "VENCIDA" if accion == "CERRAR_VENCIDA" else "SIN_ACUERDO"
                obj.save(update_fields=["estado", "fecha_actualizacion"])
                evento(
                    obj,
                    "ADMINISTRACION",
                    accion,
                    motivo or "El horario original transcurrió; no se modifica la reserva.",
                )
                return Response({
                    "mensaje": "Solicitud cerrada sin modificar la reserva original ni el pago.",
                    "solicitud": serializar(obj, "ADMINISTRACION"),
                })

            if prestacion.estado != "CONTRATADA":
                return error("La prestación ya no admite este reagendamiento.")
            reserva = reserva_vigente(prestacion)
            if reserva is None or reserva.id_disponibilidad_id != obj.bloque_original_id:
                return error("La reserva original cambió. Debe revisarse la solicitud.")
            if inicio_vencido(prestacion, reserva):
                return error("La primera reunión ya comenzó; gestiona el vencimiento sin cambiar la reserva.")

            if accion == "SOLICITAR_BLOQUE" and obj.estado == "PENDIENTE_ADMIN":
                if obj.eventos.filter(accion="SOLICITAR_BLOQUE").exists():
                    return error("Ya se solicitó disponibilidad adicional para este expediente.")
                obj.estado = "ESPERANDO_NUEVO_BLOQUE"
                obj.save(update_fields=["estado", "fecha_actualizacion"])
                evento(obj, "ADMINISTRACION", "SOLICITAR_BLOQUE", "Se requiere una única entrega adicional de bloques del profesional.")
                return Response({
                    "mensaje": "Se solicitó disponibilidad al profesional.",
                    "solicitud": serializar(obj, "ADMINISTRACION"),
                })

            if accion == "PROPONER" and obj.estado == "PENDIENTE_ADMIN" and obj.iniciador == "ORGANIZACION":
                try:
                    bloque_id = int(request.data.get("id_disponibilidad"))
                except (TypeError, ValueError):
                    return error("Selecciona un bloque disponible.", 400)
                bloque = Disponibilidad.objects.select_for_update().filter(pk=bloque_id).first()
                if not disponible(bloque, prestacion, obj.bloque_original_id):
                    return error("El bloque ya no está disponible.")
                obj.alternativas.filter(estado__in=["PROPUESTA_ADMIN", "HABILITADA"]).update(estado="DESCARTADA")
                AlternativaReagendamiento.objects.update_or_create(
                    reagendamiento=obj,
                    bloque_id=bloque.pk,
                    defaults={
                        "origen": "ADMINISTRACION",
                        "estado": "PROPUESTA_ADMIN",
                        "fecha": bloque.fecha,
                        "hora_inicio": bloque.hora_inicio,
                        "hora_fin": bloque.hora_fin,
                    },
                )
                obj.bloque_propuesto_id = bloque.pk
                obj.profesional_confirmo_bloque = False
                obj.requiere_confirmacion_organizacion = False
                obj.estado = "PENDIENTE_PROFESIONAL"
                obj.save(update_fields=[
                    "bloque_propuesto_id",
                    "profesional_confirmo_bloque",
                    "requiere_confirmacion_organizacion",
                    "estado",
                    "fecha_actualizacion",
                ])
                evento(
                    obj,
                    "ADMINISTRACION",
                    "PROPONER",
                    f"Bloque enviado al profesional: {detalle_bloques([bloque])}.",
                )
                return Response({
                    "mensaje": "Propuesta notificada al profesional dentro de SKILLY.",
                    "solicitud": serializar(obj, "ADMINISTRACION"),
                })

            if accion == "VALIDAR_ALTERNATIVAS" and obj.estado == "PENDIENTE_ADMIN" and obj.iniciador == "PROFESIONAL":
                habilitadas = 0
                for alternativa in obj.alternativas.select_for_update().filter(
                    estado__in=["PENDIENTE_VALIDACION", "HABILITADA"]
                ):
                    bloque = Disponibilidad.objects.select_for_update().filter(
                        pk=alternativa.bloque_id
                    ).first()
                    alternativa.estado = (
                        "HABILITADA" if disponible(bloque, prestacion, obj.bloque_original_id)
                        else "INVALIDA"
                    )
                    alternativa.save(update_fields=["estado"])
                    habilitadas += alternativa.estado == "HABILITADA"
                if habilitadas == 0:
                    return error("No queda ningún bloque válido; solicita nueva disponibilidad.")
                obj.estado = "PENDIENTE_ORGANIZACION"
                obj.organizacion_autorizo_cambio = False
                obj.profesional_confirmo_bloque = True
                obj.requiere_confirmacion_organizacion = True
                obj.save(update_fields=[
                    "estado",
                    "organizacion_autorizo_cambio",
                    "profesional_confirmo_bloque",
                    "requiere_confirmacion_organizacion",
                    "fecha_actualizacion",
                ])
                evento(obj, "ADMINISTRACION", "VALIDAR_ALTERNATIVAS", f"{habilitadas} bloque(s) habilitado(s) para selección de la organización.")
                return Response({
                    "mensaje": "Alternativas validadas y notificadas a la organización.",
                    "solicitud": serializar(obj, "ADMINISTRACION"),
                })

            if accion == "CONFIRMAR" and obj.estado == "LISTO_CONFIRMAR":
                if not (obj.organizacion_autorizo_cambio and obj.profesional_confirmo_bloque):
                    return error("Faltan autorizaciones para aplicar este horario.")
                bloque = Disponibilidad.objects.select_for_update().filter(
                    pk=obj.bloque_propuesto_id
                ).first()
                if not disponible(bloque, prestacion, obj.bloque_original_id):
                    return error("El bloque confirmado dejó de estar disponible.")
                solicitud_interna = SimpleNamespace(
                    user=request.user,
                    data={
                        "accion": "REAGENDAR",
                        "motivo": f"Solicitud bilateral #{obj.pk}: {(obj.motivo_organizacion or obj.motivo_profesional)[:300]}",
                        "id_disponibilidad_nueva": bloque.pk,
                    },
                    _solicitud_reagendamiento_id=obj.pk,
                )
                respuesta = GestionAgendaPrestacionSeguraAdministracionView().post(
                    solicitud_interna, prestacion.pk
                )
                if respuesta.status_code != 200:
                    transaction.set_rollback(True)
                    return respuesta
                obj.estado = "CONFIRMADO"
                obj.save(update_fields=["estado", "fecha_actualizacion"])
                evento(obj, "ADMINISTRACION", "CONFIRMAR", f"Reagendamiento confirmado en bloque #{bloque.pk} mediante agenda segura.")
                return Response({
                    "mensaje": "Reagendamiento confirmado para ambas partes.",
                    "solicitud": serializar(obj, "ADMINISTRACION"),
                    "agenda": respuesta.data,
                })
            return error("Operación no válida para el estado actual.")


@method_decorator(csrf_protect, name="dispatch")
class ProfesionalReagendamientoView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _profesional(self, request):
        return Profesional.objects.filter(id_usuario=request.user).first()

    def get(self, request):
        profesional = self._profesional(request)
        if profesional is None:
            return error("Perfil profesional no encontrado.", 404)
        items = (
            SolicitudReagendamiento.objects.filter(profesional_id=profesional.pk)
            .defer("evidencia_contenido")
            .order_by("-fecha_creacion")[:50]
        )
        registros = []
        for item in items:
            datos = serializar(item, "PROFESIONAL")
            prestacion = PrestacionServicio.objects.filter(pk=item.prestacion_id).first()
            datos["bloques_disponibles"] = (
                opciones(prestacion, item.bloque_original_id)
                if prestacion is not None and item.estado in {
                    "PENDIENTE_PROFESIONAL",
                    "ESPERANDO_NUEVO_BLOQUE",
                }
                else []
            )
            registros.append(datos)
        return Response({
            "solicitudes": registros,
            "prestaciones_disponibles": _prestaciones_habilitadas(profesional),
            "politica": politica(),
        })

    def post(self, request):
        profesional = self._profesional(request)
        if profesional is None:
            return error("Perfil profesional no encontrado.", 404)
        accion = str(request.data.get("accion", "")).strip().upper()

        if accion == "SOLICITAR_PROFESIONAL":
            motivo = texto_motivo(request.data.get("motivo"))
            if not 20 <= len(motivo) <= 2000:
                return error("Describe el impedimento en 20 a 2000 caracteres.", 400)
            if not politica_aceptada(request.data):
                return error("Debes leer y aceptar la política vigente.", 400)
            try:
                prestacion_id = int(request.data.get("id_prestacion"))
                evidencia = evidencia_validada(request.FILES.get("evidencia"), obligatoria=True)
                alternativas_validadas(request.data)
            except (TypeError, ValueError):
                return error("Selecciona una prestación válida.", 400)
            except serializers.ValidationError as exc:
                return error(primer_error_validacion(exc), 400)
            try:
                with transaction.atomic():
                    prestacion = PrestacionServicio.objects.select_for_update().filter(
                        pk=prestacion_id, id_profesional=profesional
                    ).first()
                    if prestacion is None:
                        return error("La prestación no pertenece al profesional.", 404)
                    impedimento = acceso_solicitud(prestacion)
                    if impedimento:
                        return error(impedimento)
                    reserva = reserva_vigente(prestacion)
                    obj = SolicitudReagendamiento.objects.create(
                        prestacion_id=prestacion.pk,
                        solicitud_id=prestacion.id_solicitud_id,
                        profesional_id=profesional.pk,
                        bloque_original_id=reserva.id_disponibilidad_id,
                        iniciador="PROFESIONAL",
                        motivo_profesional=motivo,
                        organizacion_autorizo_cambio=False,
                        profesional_confirmo_bloque=True,
                        requiere_confirmacion_organizacion=True,
                        politica_version=POLITICA_VERSION,
                        politica_actor="PROFESIONAL",
                        politica_aceptada_en=timezone.now(),
                        **evidencia,
                    )
                    bloques = registrar_alternativas(
                        obj,
                        prestacion,
                        profesional,
                        request.data,
                        "PROFESIONAL_INICIADOR",
                        "PENDIENTE_VALIDACION",
                    )
                    evento(
                        obj,
                        "PROFESIONAL",
                        "SOLICITAR_PROFESIONAL",
                        f"Motivo: {motivo}. Alternativas: {detalle_bloques(bloques)}.",
                    )
                    return Response({
                        "mensaje": "Solicitud profesional enviada a administración.",
                        "solicitud": serializar(obj, "PROFESIONAL"),
                    }, status=201)
            except serializers.ValidationError as exc:
                return error(primer_error_validacion(exc), 400)
            except IntegrityError:
                return error("Ya existe una solicitud abierta para esta prestación.")

        try:
            pk = int(request.data.get("id"))
        except (TypeError, ValueError):
            return error("Identificador inválido.", 400)
        try:
            with transaction.atomic():
                obj_base = SolicitudReagendamiento.objects.filter(
                    pk=pk, profesional_id=profesional.pk
                ).first()
                if obj_base is None:
                    return error("Solicitud no encontrada.", 404)
                prestacion = PrestacionServicio.objects.select_for_update().filter(
                    pk=obj_base.prestacion_id
                ).first()
                if prestacion is None or prestacion.estado != "CONTRATADA":
                    return error("La prestación no permite este cambio.")
                obj = SolicitudReagendamiento.objects.select_for_update().get(pk=pk)
                if obj.estado not in ESTADOS_ABIERTOS:
                    return error("Esta solicitud ya está cerrada.")
                reserva = reserva_vigente(prestacion)
                if reserva is None or reserva.id_disponibilidad_id != obj.bloque_original_id:
                    return error("La reserva original cambió. Administración debe revisar el caso.")
                if inicio_vencido(prestacion, reserva):
                    return error("La primera reunión ya comenzó. Administración debe gestionar el vencimiento.")

                if obj.estado == "PENDIENTE_PROFESIONAL" and accion == "ACEPTAR" and obj.iniciador == "ORGANIZACION":
                    if not obj.organizacion_autorizo_cambio:
                        return error(
                            "La solicitud no conserva la autorización de la organización."
                        )
                    bloque = Disponibilidad.objects.select_for_update().filter(
                        pk=obj.bloque_propuesto_id
                    ).first()
                    if not disponible(bloque, prestacion, obj.bloque_original_id):
                        return error("El bloque ya no se encuentra disponible.")
                    obj.profesional_confirmo_bloque = True
                    obj.estado = "LISTO_CONFIRMAR"
                    obj.save(update_fields=[
                        "profesional_confirmo_bloque", "estado", "fecha_actualizacion"
                    ])
                    obj.alternativas.filter(bloque_id=bloque.pk).update(estado="SELECCIONADA")
                    evento(obj, "PROFESIONAL", "ACEPTAR", f"Aceptado bloque #{bloque.pk}; no se requiere otra aceptación empresarial.")
                    return Response({
                        "mensaje": "Horario aceptado. Administración puede aplicar el cambio.",
                        "solicitud": serializar(obj, "PROFESIONAL"),
                    })

                if obj.estado == "PENDIENTE_PROFESIONAL" and accion == "RECHAZAR_CON_ALTERNATIVAS" and obj.iniciador == "ORGANIZACION":
                    if obj.contrapropuesta_profesional_usada:
                        return error("La única contrapropuesta profesional ya fue utilizada.")
                    motivo = texto_motivo(request.data.get("motivo"))
                    if not 10 <= len(motivo) <= 500:
                        return error("Indica el motivo del rechazo (10 a 500 caracteres).", 400)
                    obj.alternativas.filter(estado="PROPUESTA_ADMIN").update(estado="DESCARTADA")
                    bloques = registrar_alternativas(
                        obj, prestacion, profesional, request.data,
                        "CONTRAPROPUESTA_PROFESIONAL", "HABILITADA",
                    )
                    obj.bloque_propuesto_id = None
                    obj.motivo_profesional = motivo
                    obj.contrapropuesta_profesional_usada = True
                    obj.profesional_confirmo_bloque = True
                    obj.organizacion_autorizo_cambio = False
                    obj.requiere_confirmacion_organizacion = True
                    obj.estado = "PENDIENTE_ORGANIZACION"
                    obj.save(update_fields=[
                        "bloque_propuesto_id", "motivo_profesional",
                        "contrapropuesta_profesional_usada", "profesional_confirmo_bloque",
                        "organizacion_autorizo_cambio", "requiere_confirmacion_organizacion",
                        "estado", "fecha_actualizacion",
                    ])
                    evento(
                        obj,
                        "PROFESIONAL",
                        "RECHAZAR_CON_ALTERNATIVAS",
                        f"Motivo: {motivo}. Única contrapropuesta: {detalle_bloques(bloques)}.",
                    )
                    return Response({
                        "mensaje": "Contrapropuesta única enviada a la organización.",
                        "solicitud": serializar(obj, "PROFESIONAL"),
                    })

                if obj.estado == "ESPERANDO_NUEVO_BLOQUE" and accion == "OFRECER_ALTERNATIVAS":
                    if obj.eventos.filter(accion="OFRECER_ALTERNATIVAS").exists():
                        return error("Ya se entregó la disponibilidad adicional permitida.")
                    estado_alternativa = (
                        "HABILITADA" if obj.iniciador == "ORGANIZACION"
                        else "PENDIENTE_VALIDACION"
                    )
                    bloques = registrar_alternativas(
                        obj, prestacion, profesional, request.data,
                        "DISPONIBILIDAD_SOLICITADA", estado_alternativa,
                    )
                    obj.profesional_confirmo_bloque = True
                    obj.organizacion_autorizo_cambio = False
                    obj.requiere_confirmacion_organizacion = True
                    if obj.iniciador == "ORGANIZACION":
                        obj.contrapropuesta_profesional_usada = True
                        obj.estado = "PENDIENTE_ORGANIZACION"
                    else:
                        obj.estado = "PENDIENTE_ADMIN"
                    obj.save(update_fields=[
                        "profesional_confirmo_bloque", "organizacion_autorizo_cambio",
                        "requiere_confirmacion_organizacion", "contrapropuesta_profesional_usada",
                        "estado", "fecha_actualizacion",
                    ])
                    evento(
                        obj,
                        "PROFESIONAL",
                        "OFRECER_ALTERNATIVAS",
                        "Disponibilidad adicional dentro del mismo expediente: "
                        f"{detalle_bloques(bloques)}.",
                    )
                    return Response({
                        "mensaje": "Alternativas enviadas dentro del mismo expediente.",
                        "solicitud": serializar(obj, "PROFESIONAL"),
                    })
                return error("Operación no permitida en el estado actual.")
        except serializers.ValidationError as exc:
            return error(primer_error_validacion(exc), 400)
        except IntegrityError:
            return error("La respuesta fue procesada o contiene una alternativa repetida.")


class EvidenciaReagendamientoAdministracionView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsAdministracionSkilly]
    http_method_names = ["get", "head", "options"]

    def get(self, request, pk):
        with transaction.atomic():
            obj = (
                SolicitudReagendamiento.objects.defer("evidencia_contenido")
                .filter(pk=pk)
                .first()
            )
            if obj is None:
                return error("Solicitud no encontrada.", 404)
            permiso = _verificar_responsable(request, obj.solicitud_id)
            if permiso is not None:
                return permiso
            if not obj.evidencia_nombre or not obj.evidencia_sha256:
                return error("No existe evidencia para este expediente.", 404)
            extension = os.path.splitext(obj.evidencia_nombre)[1].lower()
            if extension not in MIME_EVIDENCIA:
                return error("La referencia de evidencia no es válida.", 404)
            contenido = (
                SolicitudReagendamiento.objects.filter(pk=pk)
                .values_list("evidencia_contenido", flat=True)
                .first()
            )
            if not contenido:
                return error("No existe evidencia para este expediente.", 404)
        respuesta = HttpResponse(
            bytes(contenido), content_type="application/octet-stream"
        )
        respuesta["Content-Disposition"] = (
            f'attachment; filename="reagendamiento-{obj.pk}{extension}"'
        )
        respuesta["X-Content-Type-Options"] = "nosniff"
        respuesta["Cache-Control"] = "private, no-store"
        return respuesta
