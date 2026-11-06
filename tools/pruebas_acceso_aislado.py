"""Integración Django/PostgreSQL en copia local: acceso y transacciones.

No levanta servidores ni migra esquemas. Requiere el contexto aislado ya activo.
El cliente pasa por middleware y API reales dentro del proceso; no es navegador
ni prueba SMTP. Correo exitoso en memoria; fallo SMTP y barrera de concurrencia
inyectados únicamente durante la prueba. Nunca imprime cuerpos ni credenciales.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from pathlib import Path
import re
import secrets
import socket
import sys
import threading
from unittest.mock import patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


def ejecutar(context_path):
    from dotenv import dotenv_values

    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    run = Path(context["run_dir"]).resolve()
    if not context.get("isolated") or not run.is_dir() or run.is_relative_to(ROOT):
        raise ValueError("Se requiere contexto aislado externo")
    cfg = dotenv_values(run / "conexion_privada.env")
    if (cfg.get("POSTGRES_HOST") not in {"127.0.0.1", "localhost"}
            or int(cfg["POSTGRES_PORT"]) != context["database_port"]
            or context["database_port"] == 5432):
        raise ValueError("Conexion aislada no valida")
    os.environ.update({k: v for k, v in cfg.items() if v is not None})
    os.environ["DJANGO_SETTINGS_MODULE"] = "integration_settings"
    os.environ["FRONTEND_ORIGIN"] = context["frontend_origin"]
    sys.path[:0] = [str(run), str(ROOT / "backend")]
    original_connect = socket.socket.connect

    def connect(sock, address):
        if (not isinstance(address, tuple)
                or address[0] not in {"localhost", "127.0.0.1", "::1"}
                or address[1] != context["database_port"]):
            raise RuntimeError("Red externa bloqueada durante integracion")
        return original_connect(sock, address)

    socket.socket.connect = connect
    import django
    django.setup()
    from django.contrib.auth.hashers import make_password
    from django.core import mail
    from django.db import connection, connections
    from django.test import override_settings
    from django.utils import timezone
    from rest_framework.test import APIClient
    from acceso.models import RecuperacionAcceso, Usuario
    from acceso.serializers import RegistroProfesionalSerializer
    from profesionales.models import Profesional

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),current_schema(),current_user,inet_server_port()")
        if cursor.fetchone() != ("skilly", "skilly", "skilly_app", context["database_port"]):
            raise RuntimeError("Identidad PostgreSQL inesperada")
    # El rol de aplicación no tiene pg_read_all_settings. Consultar solamente
    # el administrador de la copia; no conceder permisos al rol ni al servidor.
    import psycopg
    candidates = []
    for candidate in run.parent.glob("ensayo_aislado_*/conexion_aislada.env"):
        admin = dotenv_values(candidate)
        if int(admin.get("POSTGRES_PORT", "0")) == context["database_port"]:
            candidates.append((candidate, admin))
    if len(candidates) != 1:
        raise RuntimeError("No se identifica un unico cluster de ensayo")
    candidate, admin = candidates[0]
    with psycopg.connect(dbname="postgres", user=admin["POSTGRES_USER"],
                          password=admin["POSTGRES_PASSWORD"], host="127.0.0.1",
                          port=context["database_port"], connect_timeout=8) as guard:
        directory = Path(guard.execute("SHOW data_directory").fetchone()[0]).resolve()
        if directory != (candidate.parent / "cluster").resolve():
            raise RuntimeError("El cluster no pertenece al respaldo de ensayo")

    output = run / ("acceso_integracion_" + uuid4().hex)
    output.mkdir(exist_ok=False)
    checks = []
    stage = "inicio"

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    class Actor:
        def __init__(self):
            self.client = APIClient(enforce_csrf_checks=True)
            self.client.raise_request_exception = False

        def post(self, path, data, csrf=True):
            headers = {"HTTP_ORIGIN": context["frontend_origin"]}
            if csrf:
                token = self.client.get("/api/acceso/csrf/").json()["csrfToken"]
                headers["HTTP_X_CSRFTOKEN"] = token
            return self.client.post(path, data, format="json", **headers)

        def login(self, correo, password):
            return self.post("/api/acceso/iniciar-sesion/", {"correo": correo, "contrasena": password})

    password = secrets.token_urlsafe(32)
    address = "acceso-" + uuid4().hex + "@example.invalid"
    payload = {"correo": address, "contrasena": password, "confirmar_contrasena": password,
               "nombres": "Prueba", "apellidos": "Concurrente"}
    try:
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            stage = "registro_concurrente"
            barrier = threading.Barrier(2, timeout=20)
            validate = RegistroProfesionalSerializer.validate_correo

            def sincronizar(serializer, value):
                value = validate(serializer, value)
                barrier.wait()
                return value

            def registrar(_):
                try:
                    return Actor().post("/api/acceso/registro-profesional/", payload).status_code
                finally:
                    connections.close_all()

            with patch.object(RegistroProfesionalSerializer, "validate_correo", sincronizar):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    statuses = sorted(pool.map(registrar, range(2)))
            check("registro_simultaneo_201_400", statuses == [201, 400])
            user = Usuario.objects.get(correo=address)
            check("una_cuenta_un_perfil", Usuario.objects.filter(correo=address).count() == 1
                  and Profesional.objects.filter(id_usuario=user).count() == 1)
            duplicate = Actor().post("/api/acceso/registro-profesional/", payload)
            check("reintento_registro_400_correo", duplicate.status_code == 400 and "correo" in duplicate.json())

            stage = "atomicidad_perfil"
            failed_address = "rollback-" + uuid4().hex + "@example.invalid"
            with patch("acceso.registro_completo.Profesional.objects.create", side_effect=RuntimeError("fallo controlado")):
                failed = Actor().post("/api/acceso/registro-profesional/", {**payload, "correo": failed_address})
            check("fallo_perfil_revierte_cuenta", failed.status_code == 500
                  and not Usuario.objects.filter(correo=failed_address).exists())

            stage = "recuperacion"
            actor, recovery = Actor(), Actor()
            check("inicio_legitimo", actor.login(address, password).status_code == 200)
            before = RecuperacionAcceso.objects.filter(id_usuario=user).count()
            captured = []

            class Capture(logging.Handler):
                def emit(self, record):
                    captured.append(record)

            logger = logging.getLogger("acceso.views")
            handler = Capture()
            logger.addHandler(handler)
            previous_level = logger.level
            logger.setLevel(logging.WARNING)
            try:
                from smtplib import SMTPAuthenticationError
                with patch("acceso.views.enviar_correo_recuperacion", side_effect=SMTPAuthenticationError(535, b"contenido-sintetico")):
                    failed = recovery.post("/api/acceso/solicitar-recuperacion/", {"correo": address})
            finally:
                logger.removeHandler(handler)
                logger.setLevel(previous_level)
            unknown = recovery.post("/api/acceso/solicitar-recuperacion/", {"correo": "ausente-" + uuid4().hex + "@example.invalid"})
            check("fallo_smtp_respuesta_generica", failed.status_code == unknown.status_code == 200
                  and failed.json() == unknown.json())
            check("fallo_smtp_revierte_token", RecuperacionAcceso.objects.filter(id_usuario=user).count() == before)
            check("log_sin_excepcion_ni_contenido", len(captured) == 1 and captured[0].exc_info is None
                  and captured[0].getMessage() == "Fallo el envio del correo de recuperacion.")
            sent = recovery.post("/api/acceso/solicitar-recuperacion/", {"correo": address})
            check("correo_solo_en_memoria", sent.status_code == 200 and len(mail.outbox) == 1)
            match = re.search(r"\n\n([A-Za-z0-9_-]{40,})\n\n", mail.outbox[0].body)
            if not match:
                raise AssertionError("Formato de correo inesperado")
            new_password = secrets.token_urlsafe(32)
            reset = {"token": match.group(1), "nueva_contrasena": new_password,
                     "confirmar_contrasena": new_password}
            check("reset_sin_csrf_rechazado", recovery.post("/api/acceso/restablecer-contrasena/", reset, csrf=False).status_code == 403)
            check("reset_legitimo", recovery.post("/api/acceso/restablecer-contrasena/", reset).status_code == 200)
            check("token_un_solo_uso", recovery.post("/api/acceso/restablecer-contrasena/", reset).status_code == 400)
            check("sesion_anterior_revocada", actor.client.get("/api/profesionales/mi-perfil/").status_code == 403)
            check("clave_anterior_rechazada", Actor().login(address, password).status_code == 400)
            check("clave_nueva_permitida", actor.login(address, new_password).status_code == 200)
            check("cierre_sin_csrf_rechazado", actor.post("/api/acceso/cerrar-sesion/", {}, csrf=False).status_code == 403)
            check("cierre_legitimo", actor.post("/api/acceso/cerrar-sesion/", {}).status_code == 200)
            check("sesion_cerrada_rechazada", actor.client.get("/api/profesionales/mi-perfil/").status_code == 403)
    except Exception as error:
        result = {"passed": False, "stage": stage, "error_type": type(error).__name__, "checks": checks}
    else:
        result = {"passed": True, "checks": checks}
    finally:
        connections.close_all()
        socket.socket.connect = original_connect
    result["scope"] = "Django middleware/API y PostgreSQL reales dentro del proceso; correo en memoria; barrera y fallo SMTP inyectados"
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
