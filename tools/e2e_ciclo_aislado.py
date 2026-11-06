"""Ciclos HTTP de negocio: solo para actores que verifican un entorno aislado.

No abre conexiones de base de datos, no carga .env y no realiza pagos externos.
El llamador debe validar cluster/puerto/BD y bloquear pagos y envios reales antes
de construir los actores. Actor.expect conserva estados/etiquetas, nunca cuerpos
ni cabeceras. Las referencias firmadas se usan solo en memoria y no se retornan.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from uuid import uuid4


def _rut_sintetico(semilla):
    cuerpo = str(80000000 + int(hashlib.sha256(semilla.encode()).hexdigest()[:8], 16) % 19999999)
    suma = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(cuerpo)))
    resto = 11 - suma % 11
    dv = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return f"{cuerpo}-{dv}"


def _numero(body, clave, ident):
    valor = ident(body, clave)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise AssertionError(f"Respuesta sin identificador positivo: {clave}")
    return valor


def _nodo(body, clave):
    if isinstance(body, dict):
        if clave in body:
            return body[clave]
        for value in body.values():
            encontrado = _nodo(value, clave)
            if encontrado is not None:
                return encontrado
    elif isinstance(body, list):
        for value in body:
            encontrado = _nodo(value, clave)
            if encontrado is not None:
                return encontrado
    return None


def _ids(body, clave):
    if isinstance(body, dict):
        propios = [body[clave]] if clave in body else []
        return propios + [i for value in body.values() for i in _ids(value, clave)]
    if isinstance(body, list):
        return [i for value in body for i in _ids(value, clave)]
    return []


def ejecutar_ciclos(admin, profesional, empresa, anonimo, sid, pid,
                    fecha_futura, pdf, check, ident):
    """Ejecuta dos ciclos sobre un servicio ya PUBLICADO y devuelve solo IDs.

    admin/profesional/empresa/anonimo son actores HTTP reales con cookies
    separadas. La seguridad de destino aislado es precondicion del llamador.
    pdf contiene bytes de una fixture sintetica, nunca un documento operativo.
    """
    prefijo = uuid4().hex[:12]
    fecha = fecha_futura.date() if isinstance(fecha_futura, datetime) else fecha_futura
    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)
    if not isinstance(fecha, date):
        raise ValueError("fecha_futura debe ser date o ISO date")
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-"):
        raise ValueError("Se requiere fixture PDF sintetica con firma valida")

    def ex(actor, name, method, path, data=None, files=None, expected=(200,)):
        return actor.expect(
            f"ciclo_{name}", method, path, data=data, files=files,
            expected=expected, csrf=True,
        )

    servicio = ex(anonimo, "servicio_publicado", "GET", f"/api/marketplace/servicios/{sid}/")
    check("ciclo_servicio_corresponde", ident(servicio, "id_servicio") == sid)
    modalidad = servicio.get("modalidad") or "REMOTA"

    # Inicializar parametros solo cuando falten o sean invalidos en la copia.
    for nombre, valor in (("comision", "10.0000"), ("cancelaciones", "5.0000")):
        ruta = f"/api/backoffice/configuracion/{nombre}/"
        estado = ex(admin, f"parametro_{nombre}", "GET", ruta)
        actual = _nodo(estado, "valor_actual")
        try:
            numero = Decimal(str(actual))
            valido = numero.is_finite() and Decimal(0) <= numero <= Decimal(100)
        except (InvalidOperation, ValueError, TypeError):
            valido = False
        if not valido:
            ex(admin, f"inicializar_{nombre}", "PATCH", ruta, {"valor_nuevo": valor})

    cuentas = ex(admin, "cuentas_receptoras", "GET", "/api/backoffice/configuracion/cuentas-bancarias/")
    principales = [c for c in cuentas.get("cuentas", []) if c.get("principal") and c.get("activa")]
    check("ciclo_principal_no_ambigua", len(principales) <= 1)
    if not principales:
        datos = {
            "titular": "SKILLY PRUEBA AISLADA SpA",
            "rut_titular": _rut_sintetico(prefijo + "banco"),
            "banco": "BANCO SIMULADO DE PRUEBAS",
            "tipo_cuenta": "CORRIENTE",
            "numero_cuenta": str(int(prefijo, 16)).zfill(16),
            "correo": f"banco-{prefijo}@example.invalid",
        }
        nueva = ex(admin, "crear_cuenta_sintetica", "POST", "/api/backoffice/configuracion/cuentas-bancarias/", datos, expected=(201,))
        cid = _numero(nueva, "id_cuenta", ident)
        for accion in ("ACTIVAR", "PRINCIPAL"):
            ex(admin, f"cuenta_{accion.lower()}", "PATCH", f"/api/backoffice/configuracion/cuentas-bancarias/{cid}/", {"accion": accion})

    def disponibilidad(nombre, dia):
        respuesta = ex(
            profesional, nombre, "POST", "/api/solicitudes/mi-disponibilidad/",
            {"fecha": dia.isoformat(), "hora_inicio": "10:00", "hora_fin": "11:00"},
            expected=(201,),
        )
        return _numero(respuesta, "id_disponibilidad", ident)

    def contratar(etiqueta, dia):
        bloque = disponibilidad(f"{etiqueta}_disponibilidad", dia)
        datos = {
            "id_servicio": sid, "id_disponibilidad": bloque,
            "nombre_organizacion": f"ORGANIZACION SINTETICA {prefijo} {etiqueta}",
            "rut": _rut_sintetico(prefijo + etiqueta),
            "nombre_contacto": "CONTACTO DE PRUEBA AISLADA",
            "correo_contacto": f"empresa-{prefijo}-{etiqueta}@example.invalid",
            "objetivo": "Verificar un ciclo sintetico en copia aislada",
            "descripcion_necesidad": "Ejercicio de integracion aislado sin operacion comercial real.",
        }
        enviada = ex(empresa, f"{etiqueta}_solicitud_empresa", "POST", "/api/solicitudes/enviar/", datos, expected=(201,))
        sol = _numero(enviada, "id_solicitud", ident)
        referencia = _nodo(enviada, "referencia_seguimiento")
        if not isinstance(referencia, str) or not referencia:
            raise AssertionError("Solicitud sin referencia de seguimiento")
        base = f"/api/coordinacion/administracion/solicitudes/{sol}"
        ex(admin, f"{etiqueta}_autoasignacion", "POST", base + "/asignacion/", {"modo": "AUTOASIGNAR"}, expected=(200, 201))
        ex(admin, f"{etiqueta}_autoasignacion_duplicada_bloqueada", "POST", base + "/asignacion/", {"modo": "AUTOASIGNAR"}, expected=(409,))
        ex(admin, f"{etiqueta}_proponer_asociacion", "POST", base + "/asociaciones/proponer/", {}, expected=(201,))
        ex(admin, f"{etiqueta}_confirmar_asociacion", "POST", base + f"/asociaciones/{pid}/confirmar/", {})
        preparada = ex(admin, f"{etiqueta}_preparar_prestacion", "POST", base + f"/profesionales/{pid}/preparar-prestacion/", {}, expected=(200, 201))
        prest = _numero(preparada, "id_prestacion", ident)
        ex(admin, f"{etiqueta}_comunicar_condiciones", "POST", base + "/coordinacion/", {
            "accion": "COMUNICAR_CONDICIONES",
            "condiciones_comunicadas": "Servicio sintetico aprobado; alcance y precio publicados sin cambios. Entrega documental en copia aislada.",
        })
        politica_path = f"/api/seguimiento/empresa/{referencia}/politica-cancelacion/"
        politica = ex(empresa, f"{etiqueta}_politica", "GET", politica_path)
        version = politica.get("version")
        if not isinstance(version, str) or len(version) != 64:
            raise AssertionError("Politica sin version valida para aceptar")
        aceptada = ex(empresa, f"{etiqueta}_aceptar_politica", "POST", politica_path, {"acepto": True, "version": version}, expected=(200, 201))
        check(f"ciclo_{etiqueta}_politica_aceptada", aceptada.get("aceptada") is True)
        destino = ex(empresa, f"{etiqueta}_destino_transferencia", "GET", f"/api/pagos/empresa/{referencia}/transferencia/disponibilidad/")
        check(f"ciclo_{etiqueta}_transferencia_disponible", destino.get("disponible") is True)
        cuenta_id = _numero(destino, "id_cuenta", ident)
        pagada = ex(empresa, f"{etiqueta}_pago_academico", "POST", f"/api/pagos/empresa/{referencia}/transferencia/", {
            "metodo_pago": "TRANSFERENCIA", "id_cuenta_receptora": cuenta_id,
            "referencia_transaccion": f"SIMULACION-{prefijo}-{etiqueta}",
        }, files={"comprobante_transferencia": ("comprobante-sintetico.pdf", pdf, "application/pdf")}, expected=(201,))
        pago = _numero(pagada, "id_pago", ident)
        verificada = ex(admin, f"{etiqueta}_verificar_comprobante_academico", "POST", f"/api/pagos/administracion/{pago}/", {
            "accion": "VERIFICAR_TRANSFERENCIA", "observacion": "Comprobante sintetico en copia aislada; no existe movimiento de dinero.",
        })
        check(f"ciclo_{etiqueta}_pago_retenido", _nodo(verificada, "estado_pago") == "RETENIDO")
        agenda = f"/api/coordinacion/administracion/prestaciones/{prest}/agenda/"
        contratada = ex(admin, f"{etiqueta}_contratar_primera_reunion", "POST", agenda, {
            "accion": "AGENDAR_PRIMERA_REUNION", "modalidad": modalidad,
            "enlace_reunion": "https://reunion.example.invalid/prueba-aislada",
        }, expected=(200, 201))
        check(f"ciclo_{etiqueta}_contratada", _nodo(contratada, "prestacion_contratada") is True or _nodo(contratada.get("prestacion", {}), "estado") == "CONTRATADA")
        return {"id_solicitud": sol, "id_prestacion": prest, "id_pago": pago,
                "id_disponibilidad": bloque, "referencia": referencia, "agenda": agenda}

    exitoso = contratar("cierre", fecha)
    ref = exitoso["referencia"]
    prest = exitoso["id_prestacion"]
    pago = exitoso["id_pago"]

    alternativo = disponibilidad("reagendamiento_bloque_alternativo", fecha + timedelta(days=1))
    reagenda_org = f"/api/reagendamientos/organizacion/{ref}/"
    pedida = ex(empresa, "reagendamiento_solicitar", "POST", reagenda_org, {
        "accion": "SOLICITAR", "motivo": "La organizacion de prueba necesita cambiar la primera reunion futura.",
    }, expected=(201,))
    caso = _numero(pedida, "id", ident)
    ex(admin, "reagendamiento_proponer", "POST", "/api/reagendamientos/administracion/", {"id": caso, "accion": "PROPONER", "id_disponibilidad": alternativo})
    ex(profesional, "reagendamiento_profesional_aceptar", "POST", "/api/reagendamientos/profesional/", {"id": caso, "accion": "ACEPTAR"})
    ex(empresa, "reagendamiento_organizacion_aceptar", "POST", reagenda_org, {"id": caso, "accion": "ACEPTAR_ALTERNATIVA"})
    confirmada = ex(admin, "reagendamiento_confirmar", "POST", "/api/reagendamientos/administracion/", {"id": caso, "accion": "CONFIRMAR"})
    check("ciclo_reagendamiento_consenso_confirmado", _nodo(confirmada.get("solicitud", {}), "estado") == "CONFIRMADO")

    seguimiento_prof = f"/api/seguimiento/profesional/prestaciones/{prest}/"
    ex(profesional, "avance", "POST", seguimiento_prof, {"estado": "EN_DESARROLLO", "detalle": "Avance sintetico del servicio en copia aislada."}, expected=(201,))
    entrega_1 = ex(profesional, "primera_entrega", "POST", seguimiento_prof + "entregas/", {"descripcion": "Primera entrega sintetica para observar y corregir.", "referencia_entrega": "https://entrega.example.invalid/version-1"}, expected=(201,))
    eid1 = _numero(entrega_1, "id_entrega", ident)
    observada = ex(empresa, "observar_entrega", "POST", f"/api/seguimiento/empresa/{ref}/entregas/{eid1}/", {"accion": "OBSERVAR", "detalle": "Corregir la seccion de prueba antes de aceptar la entrega."}, expected=(201,))
    check("ciclo_entrega_observada", _nodo(observada, "estado") == "CON_OBSERVACIONES")
    ex(admin, "liberacion_bloqueada_por_entrega_observada", "POST", f"/api/pagos/administracion/{pago}/liberar/", {"accion": "LIBERAR_PAGO"}, expected=(409,))
    entrega_2 = ex(profesional, "entrega_corregida", "POST", seguimiento_prof + "entregas/", {"descripcion": "Segunda version sintetica que corrige la observacion empresarial.", "referencia_entrega": "https://entrega.example.invalid/version-2"}, expected=(201,))
    eid2 = _numero(entrega_2, "id_entrega", ident)
    check("ciclo_entrega_version_incremental", _nodo(entrega_2, "version") == _nodo(entrega_1, "version") + 1)
    aceptada = ex(empresa, "aceptar_entrega_corregida", "POST", f"/api/seguimiento/empresa/{ref}/entregas/{eid2}/", {"accion": "ACEPTAR"})
    check("ciclo_entrega_aceptada", _nodo(aceptada, "estado") == "ACEPTADA")

    reclamo = ex(empresa, "reclamo_empresa", "POST", f"/api/seguimiento/empresa/{ref}/reclamos/", {"motivo": "Revision sintetica del resultado", "descripcion": "La organizacion solicita una revision formal en este ensayo sin datos reales."}, expected=(201,))
    reclamo_id = _numero(reclamo, "id_reclamo", ident)
    ex(admin, "liberacion_bloqueada_por_reclamo", "POST", f"/api/pagos/administracion/{pago}/liberar/", {"accion": "LIBERAR_PAGO"}, expected=(409,))
    resuelta = ex(admin, "resolver_reclamo_para_liberacion", "POST", f"/api/seguimiento/administracion/reclamos/{reclamo_id}/", {"decision": "ACEPTAR_CIERRE_PRUEBA", "efecto_economico": "LIBERACION", "observacion": "Revision completada en copia aislada; no se ordena transferencia real."}, expected=(201,))
    check("ciclo_reclamo_resuelto", _nodo(resuelta.get("reclamo", {}), "estado") == "RESUELTO")
    cerrada = ex(admin, "finalizar_prestacion", "POST", f"/api/seguimiento/administracion/prestaciones/{prest}/", {"accion": "FINALIZAR_PRESTACION"})
    check("ciclo_prestacion_finalizada", _nodo(cerrada.get("prestacion", {}), "estado") == "FINALIZADA")
    contenido = f"RETROALIMENTACION PRIVADA SINTETICA {prefijo}; no publicar en marketplace."
    feedback = ex(empresa, "retroalimentacion_privada", "POST", f"/api/retroalimentacion/empresa/{ref}/", {"contenido": contenido}, expected=(201,))
    feedback_id = _numero(feedback, "id_feedback", ident)
    check("ciclo_feedback_visibilidad_privada", _nodo(feedback, "visibilidad") == "PRIVADA")
    privada_admin = ex(admin, "retroalimentacion_admin", "GET", "/api/retroalimentacion/administracion/")
    check("ciclo_admin_ve_feedback", feedback_id in _ids(privada_admin, "id_feedback"))
    ex(anonimo, "retroalimentacion_admin_anonimo_rechazado", "GET", "/api/retroalimentacion/administracion/", expected=(403,))
    publico = ex(anonimo, "marketplace_sin_feedback_privado", "GET", f"/api/marketplace/servicios/{sid}/")
    check("ciclo_feedback_no_publicado", contenido not in json.dumps(publico, ensure_ascii=False))
    liberado = ex(admin, "liberar_pago_academico", "POST", f"/api/pagos/administracion/{pago}/liberar/", {"accion": "LIBERAR_PAGO", "observacion": "Liberacion contable de prueba; sin transferencia real."})
    check("ciclo_pago_liberado", _nodo(liberado, "estado_pago") == "LIBERADO")

    cancelado = contratar("cancelacion", fecha + timedelta(days=2))
    p_cancel = cancelado["id_prestacion"]
    pago_cancel = cancelado["id_pago"]
    ex(admin, "cancelar_segundo_contrato", "POST", cancelado["agenda"], {"accion": "CANCELAR", "motivo": "Cancelacion sintetica del segundo escenario en copia aislada."})
    agenda_cancel = ex(admin, "leer_estado_contrato_cancelado", "GET", cancelado["agenda"])
    check("ciclo_segundo_contrato_cancelado", _nodo(agenda_cancel.get("prestacion", {}), "estado") == "CANCELADA")
    ex(admin, "pago_cancelado_no_liberable", "POST", f"/api/pagos/administracion/{pago_cancel}/liberar/", {"accion": "LIBERAR_PAGO"}, expected=(409,))
    reversa = ex(admin, "solicitar_reversa_academica", "POST", f"/api/pagos/administracion/{pago_cancel}/reversas/", {"motivo": "Prestacion cancelada en ensayo aislado; solicitar reversa documental."}, expected=(201,))
    reversa_id = _numero(reversa, "id_reversa", ident)
    ex(admin, "reversa_duplicada_bloqueada", "POST", f"/api/pagos/administracion/{pago_cancel}/reversas/", {"motivo": "Intento duplicado sintetico que debe rechazarse."}, expected=(409,))
    simulada = ex(admin, "resolver_reversa_sin_dinero", "POST", f"/api/pagos/administracion/{pago_cancel}/reversas/{reversa_id}/resolver/", {"accion": "REGISTRAR_DEVOLUCION_SIMULADA", "fundamento": "Se registra exclusivamente una simulacion academica en la copia aislada.", "confirma_sin_dinero_real": True})
    check("ciclo_reversa_explicitamente_simulada", simulada.get("ambiente") == "SIMULACION_ACADEMICA" and _nodo(simulada.get("reversa", {}), "estado_reversa") == "SIMULADA")
    check("ciclo_pago_reversa_simulada", _nodo(simulada.get("pago", {}), "estado_pago") == "REVERSA_SIMULADA")

    return {
        "integracion": "HTTP_DJANGO_POSTGRESQL_AISLADO",
        "movimiento_financiero": "SIMULACION_ACADEMICA_SIN_DINERO_REAL",
        "escenario_cierre": {
            "id_solicitud": exitoso["id_solicitud"], "id_prestacion": prest,
            "id_pago": pago, "id_reagendamiento": caso,
            "id_entrega_observada": eid1, "id_entrega_aceptada": eid2,
            "id_reclamo": reclamo_id, "id_feedback": feedback_id,
            "finalizada": True, "pago_liberado": True,
        },
        "escenario_cancelacion": {
            "id_solicitud": cancelado["id_solicitud"], "id_prestacion": p_cancel,
            "id_pago": pago_cancel, "id_reversa": reversa_id,
            "cancelada": True, "reversa_simulada": True,
        },
    }
