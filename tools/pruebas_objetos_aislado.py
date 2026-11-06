"""Matriz de permisos y transiciones usando Django/API/archivos/PostgreSQL reales.

Solo admite la copia independiente ya creada: valida puerto, identidad y
data_directory antes de crear fixtures sinteticas nuevas. No altera esquemas ni
datos anteriores. Usa APIClient dentro del proceso (no navegador ni HTTP TCP),
CSRF/sesiones reales y correo en memoria; bloquea la red salvo PostgreSQL aislado.
Las fixtures ORM preparan estados de prueba: no acreditan contratacion ni pago
externo reales. Ningun cuerpo, enlace firmado o credencial se escribe en salida.
"""
import argparse
from decimal import Decimal
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import sys
from unittest.mock import patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def ejecutar(context_path):
    from dotenv import dotenv_values

    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    run = Path(context["run_dir"]).resolve()
    port = context["database_port"]
    if (not context.get("isolated") or not run.is_dir() or run.is_relative_to(ROOT)
            or isinstance(port, bool) or not isinstance(port, int) or port == 5432):
        raise ValueError("Se requiere contexto aislado externo")
    cfg = dotenv_values(run / "conexion_privada.env")
    if cfg.get("POSTGRES_HOST") not in {"127.0.0.1", "localhost"} or int(cfg["POSTGRES_PORT"]) != port:
        raise ValueError("Conexion aislada no valida")
    os.environ.update({key: value for key, value in cfg.items() if value is not None})
    os.environ["DJANGO_SETTINGS_MODULE"] = "integration_settings"
    os.environ["FRONTEND_ORIGIN"] = context["frontend_origin"]
    sys.path[:0] = [str(run), str(ROOT / "backend")]
    original_connect = socket.socket.connect

    def connect(sock, address):
        if (not isinstance(address, tuple) or address[0] not in {"localhost", "127.0.0.1", "::1"}
                or address[1] != port):
            raise RuntimeError("Red externa bloqueada durante integracion")
        return original_connect(sock, address)

    socket.socket.connect = connect
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    import django
    django.setup()
    from django.contrib.auth.hashers import make_password
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import connection, connections
    from django.test import override_settings
    from django.utils import timezone
    from rest_framework.test import APIClient
    import psycopg
    from acceso.models import Usuario
    from coordinacion.models import PrestacionServicio
    from pagos.models import HistorialEstadoPago, Pago, ReversaPago
    from profesionales.models import Profesional
    from seguimiento.entregables_multiservicio_e3 import ArchivoEntregaE3, almacenamiento
    from seguimiento.models import AvanceServicio, Entrega
    from solicitudes.models import ContactoEmpresa, EmpresaSolicitante, SolicitudServicio
    from solicitudes.referencias import crear_referencia_seguimiento

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),current_schema(),current_user,inet_server_port()")
        if cursor.fetchone() != ("skilly", "skilly", "skilly_app", port):
            raise RuntimeError("Identidad PostgreSQL inesperada")
    candidates = []
    for candidate in run.parent.glob("ensayo_aislado_*/conexion_aislada.env"):
        admin_cfg = dotenv_values(candidate)
        if int(admin_cfg.get("POSTGRES_PORT", "0")) == port:
            candidates.append((candidate, admin_cfg))
    if len(candidates) != 1:
        raise RuntimeError("No se identifica un unico cluster de ensayo")
    candidate, admin_cfg = candidates[0]
    with psycopg.connect(dbname="postgres", user=admin_cfg["POSTGRES_USER"],
                          password=admin_cfg["POSTGRES_PASSWORD"], host="127.0.0.1",
                          port=port, connect_timeout=8) as guard:
        directory = Path(guard.execute("SHOW data_directory").fetchone()[0]).resolve()
        if directory != (candidate.parent / "cluster").resolve():
            raise RuntimeError("El cluster no pertenece al respaldo de ensayo")

    output = run / ("objetos_integracion_" + uuid4().hex)
    output.mkdir(exist_ok=False)
    checks = []
    stage = "inicio"
    marker = uuid4().hex
    pdf = b"%PDF-1.7\nPrueba sintetica de permisos sin datos reales\n%%EOF\n"

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    class Actor:
        def __init__(self):
            self.client = APIClient(enforce_csrf_checks=True)
            self.client.raise_request_exception = False

        def post(self, path, data, *, csrf=True, multipart=False):
            headers = {"HTTP_ORIGIN": context["frontend_origin"]}
            if csrf:
                response = self.client.get("/api/acceso/csrf/")
                if response.status_code != 200:
                    raise RuntimeError("No se obtuvo CSRF")
                headers["HTTP_X_CSRFTOKEN"] = response.json()["csrfToken"]
            return self.client.post(path, data, format="multipart" if multipart else "json", **headers)

        def get(self, path):
            return self.client.get(path)

    def new_actor(rol):
        password = secrets.token_urlsafe(32)
        user = Usuario.objects.create(
            correo=f"objetos-{rol.lower()}-{uuid4().hex}@example.invalid", password_hash=make_password(password),
            rol=rol, estado="ACTIVO", fecha_creacion=timezone.now(), fecha_actualizacion=timezone.now(),
        )
        actor = Actor()
        check("inicio_sesion_" + rol.lower(), actor.post("/api/acceso/iniciar-sesion/", {
            "correo": user.correo, "contrasena": password,
        }).status_code == 200)
        return user, actor

    def download(name, actor, path, status=200, private_headers=False):
        response = actor.get(path)
        try:
            check(name, response.status_code == status)
            if status == 200:
                raw = b"".join(response.streaming_content)
                check(name + "_integridad", raw == pdf)
                if private_headers:
                    directives = {item.strip() for item in response["Cache-Control"].split(",")}
                    check(name + "_cabeceras", {"private", "no-store"}.issubset(directives)
                          and response["X-Content-Type-Options"] == "nosniff"
                          and response["Referrer-Policy"] == "no-referrer")
        finally:
            response.close()

    try:
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", MEDIA_ROOT=output / "media"), \
                patch("seguimiento.entregables_multiservicio_e3.RAIZ_PRIVADA", output / "entregas_privadas"):
            stage = "perfil_legado"
            owner_user, owner = new_actor("PROFESIONAL")
            other_user, other = new_actor("PROFESIONAL")
            _, admin = new_actor("ADMIN_SKILLY")
            anonymous, company = Actor(), Actor()
            profile_path = "/api/profesionales/mi-perfil/crear/"
            profile_data = {"nombres": "Persona", "apellidos": "Prueba aislada"}
            check("perfil_legado_sin_perfil", not Profesional.objects.filter(id_usuario=owner_user).exists())
            check("perfil_sin_csrf_403", owner.post(profile_path, profile_data, csrf=False).status_code == 403)
            check("perfil_admin_403", admin.post(profile_path, profile_data).status_code == 403)
            check("perfil_anonimo_403", anonymous.post(profile_path, profile_data).status_code == 403)
            check("perfil_legado_creado_201", owner.post(profile_path, profile_data).status_code == 201)
            check("perfil_otro_creado_201", other.post(profile_path, profile_data).status_code == 201)
            check("perfil_reintento_409", owner.post(profile_path, profile_data).status_code == 409)
            check("perfil_unico", Profesional.objects.filter(id_usuario=owner_user).count() == 1)
            profile = Profesional.objects.get(id_usuario=owner_user)

            stage = "documento_privado"
            upload = owner.post("/api/profesionales/mis-documentos/subir/", {
                "tipo_documento": "Titulo de prueba",
                "archivo": SimpleUploadedFile("prueba.pdf", pdf, content_type="application/pdf"),
            }, multipart=True)
            check("documento_carga_201", upload.status_code == 201)
            document_id = upload.json()["documento"]["id_documento"]
            document_path = f"/api/profesionales/mis-documentos/{document_id}/descargar/"
            download("documento_propietario_200", owner, document_path)
            download("documento_profesional_ajeno_404", other, document_path, 404)
            download("documento_anonimo_403", anonymous, document_path, 403)

            stage = "fixture_objetos"
            empresa = EmpresaSolicitante.objects.create(nombre_organizacion="Prueba objetos " + marker,
                estado="ACTIVA", fecha_registro=timezone.now())
            contacto = ContactoEmpresa.objects.create(id_empresa=empresa, nombre="Contacto sintetico",
                correo=f"contacto-{marker}@example.invalid", fecha_registro=timezone.now())

            def request_fixture():
                return SolicitudServicio.objects.create(id_empresa=empresa, id_contacto=contacto,
                    objetivo="Prueba aislada de pertenencia", descripcion_necesidad="Fixture sintetica de integracion",
                    estado="RECIBIDA", fecha_solicitud=timezone.now(), fecha_actualizacion=timezone.now())

            solicitud, privada = request_fixture(), request_fixture()
            prestacion = PrestacionServicio.objects.create(id_solicitud=solicitud, id_profesional=profile,
                condiciones_comunicadas="Fixture de condiciones", estado="CONTRATADA")
            prestacion_privada = PrestacionServicio.objects.create(id_solicitud=privada, id_profesional=profile,
                condiciones_comunicadas="Fixture de revision privada", estado="CONTRATADA")
            entrega = Entrega.objects.create(id_prestacion=prestacion, version=1, descripcion="Entrega sintetica",
                fecha_entrega=timezone.now(), estado="ACEPTADA")
            ruta = almacenamiento().save(marker + ".pdf", ContentFile(pdf))
            archivo = ArchivoEntregaE3.objects.create(id_entrega=entrega, nombre_original="entrega.pdf", ruta_privada=ruta,
                tipo_mime="application/pdf", tamanio_bytes=len(pdf), fecha_subida=timezone.now())
            comprobante = default_storage.save("comprobantes_transferencia_privados/" + marker + ".pdf", ContentFile(pdf))
            pago = Pago.objects.create(id_prestacion=prestacion, monto_total=Decimal("10000"), moneda="CLP",
                porcentaje_comision_aplicado=Decimal("10"), monto_comision=Decimal("1000"), monto_neto_profesional=Decimal("9000"),
                estado_pago="RETENIDO", metodo_pago="TRANSFERENCIA", estado_verificacion="PENDIENTE",
                comprobante_transferencia=comprobante)
            ref, ref_otra = crear_referencia_seguimiento(solicitud), crear_referencia_seguimiento(privada)

            stage = "matriz_entregables"
            pro_path = f"/api/seguimiento/profesional/entregables/archivos/{archivo.pk}/"
            adm_path = f"/api/seguimiento/administracion/entregables/archivos/{archivo.pk}/"
            emp_path = f"/api/seguimiento/empresa/{ref}/entregables/archivos/{archivo.pk}/"
            download("entrega_propietario_200", owner, pro_path, private_headers=True)
            download("entrega_profesional_ajeno_404", other, pro_path, 404)
            download("entrega_anonimo_403", anonymous, pro_path, 403)
            download("entrega_admin_200", admin, adm_path, private_headers=True)
            download("entrega_profesional_en_admin_403", owner, adm_path, 403)
            download("entrega_empresa_vinculada_200", company, emp_path, private_headers=True)
            download("entrega_otra_solicitud_404", company,
                f"/api/seguimiento/empresa/{ref_otra}/entregables/archivos/{archivo.pk}/", 404)
            download("entrega_firma_alterada_404", company,
                f"/api/seguimiento/empresa/{ref}x/entregables/archivos/{archivo.pk}/", 404)

            stage = "comprobante"
            pago_path = f"/api/pagos/administracion/{pago.pk}/"
            comprobante_path = pago_path + "comprobante/"
            download("comprobante_admin_200", admin, comprobante_path, private_headers=True)
            download("comprobante_profesional_403", owner, comprobante_path, 403)
            download("comprobante_anonimo_403", anonymous, comprobante_path, 403)

            stage = "privacidad_cancelacion"
            public_advance = AvanceServicio.objects.create(id_prestacion=prestacion_privada, estado="EN_PROGRESO",
                detalle="Avance publico sintetico", fecha_registro=timezone.now())
            aviso = owner.post(f"/api/seguimiento/profesional/prestaciones/{prestacion_privada.pk}/incidencias/", {
                "motivo": "OTRO", "descripcion": "Antecedente interno sintetico para revision administrativa.",
            })
            check("aviso_interno_registrado_201", aviso.status_code == 201)
            cancel = owner.post(f"/api/seguimiento/profesional/prestaciones/{prestacion_privada.pk}/cancelaciones/", {
                "motivo": "Impedimento sintetico", "descripcion": "Motivo privado sintetico de cancelacion pendiente de revision.",
            }, multipart=True)
            check("cancelacion_profesional_registrada_201", cancel.status_code == 201)
            follow = company.get(f"/api/seguimiento/empresa/{ref_otra}/prestacion/")
            check("empresa_sin_antecedentes_internos", follow.status_code == 200
                  and [avance["id_avance"] for avance in follow.json()["avances"]] == [public_advance.pk])
            for actor, scope in ((owner, "profesional"), (admin, "administracion")):
                own = actor.get(f"/api/seguimiento/{scope}/prestaciones/{prestacion_privada.pk}/")
                check(scope + "_conserva_antecedentes", own.status_code == 200
                      and {avance["estado"] for avance in own.json()["avances"]}
                      == {"EN_PROGRESO", "INCIDENCIA_REPORTADA", "INCIDENCIA_PROFESIONAL"})

            stage = "liberacion_y_reintentos"
            release = pago_path + "liberar/"
            release_data = {"accion": "LIBERAR_PAGO"}
            check("liberacion_profesional_403", owner.post(release, release_data).status_code == 403)
            check("liberacion_anonimo_403", anonymous.post(release, release_data).status_code == 403)
            check("liberacion_admin_sin_csrf_403", admin.post(release, release_data, csrf=False).status_code == 403)
            check("liberacion_no_verificado_409", admin.post(release, release_data).status_code == 409)
            check("reversa_no_verificado_409", admin.post(pago_path + "reversas/", {"motivo": "Prueba aislada"}).status_code == 409)
            pago.refresh_from_db()
            check("sin_movimiento_ni_historial", pago.estado_pago == "RETENIDO"
                  and not HistorialEstadoPago.objects.filter(id_pago=pago).exists()
                  and not ReversaPago.objects.filter(id_pago=pago).exists())
            pago.estado_verificacion = "VERIFICADO"
            pago.save(update_fields=["estado_verificacion"])
            check("liberacion_verificada_200", admin.post(release, release_data).status_code == 200)
            check("liberacion_reintento_200", admin.post(release, release_data).status_code == 200)
            check("historial_unico_liberacion", HistorialEstadoPago.objects.filter(id_pago=pago, estado_nuevo="LIBERADO").count() == 1)
            check("reversa_tras_liberacion_409", admin.post(pago_path + "reversas/", {"motivo": "Prueba aislada"}).status_code == 409)
            check("ninguna_reversa_creada", not ReversaPago.objects.filter(id_pago=pago).exists())
    except Exception as error:
        result = {"passed": False, "stage": stage, "error_type": type(error).__name__, "checks": checks}
    else:
        result = {"passed": True, "checks": checks}
    finally:
        connections.close_all()
        socket.socket.connect = original_connect
        logging.disable(previous_disable)
    result["scope"] = "APIClient Django/middleware, PostgreSQL y archivos reales; fixtures nuevas por ORM en copia; sin HTTP TCP/navegador ni pagos/correo externos"
    (output / "resultado.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "checks": len(checks), "stage": result.get("stage"), "evidence": str(output)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    try:
        sys.exit(ejecutar(parser.parse_args().context))
    except Exception as error:
        print(json.dumps({"passed": False, "error_type": type(error).__name__}))
        sys.exit(1)
