"""Recorrido API E2E HTTP contra un entorno SKILLY aislado ya iniciado.

Uso: python tools/e2e_api_aislado.py --context C:/ruta/contexto.json
El contexto contiene run_dir, run_id, backend_origin y database_port. run_dir
debe estar fuera del repositorio y contener fixture_privado.json del entorno.

No recorre toda la interfaz ni acredita entrevista humana, Transbank, banco o
envios reales. Usa HTTP/Django/PostgreSQL reales; reloj, entrevista y actividad
economica son simulados. Nunca imprime cuerpos, credenciales o referencias.
"""

import argparse
from datetime import datetime, timedelta, timezone
import http.cookiejar
import json
from pathlib import Path
import secrets
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Ninguna peticion puede salir del origen local verificado.
        return None


def _origen_local(valor):
    if not isinstance(valor, str):
        raise ValueError("Se requiere un origen local explicito")
    parsed = urlsplit(valor)
    if (parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or parsed.port is None):
        raise ValueError("Origen no permitido para pruebas aisladas")
    return valor.rstrip("/"), parsed.port


def _ident(body, key):
    if isinstance(body, dict):
        if key in body:
            return body[key]
        for value in body.values():
            found = _ident(value, key)
            if found is not None:
                return found
    elif isinstance(body, list):
        for value in body:
            found = _ident(value, key)
            if found is not None:
                return found
    return None


def _id(body, key):
    value = _ident(body, key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AssertionError("Falta un identificador de respuesta")
    return value


def ejecutar(context_path):
    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    run_dir = Path(context["run_dir"]).resolve()
    if not run_dir.is_dir() or run_dir.is_relative_to(ROOT):
        raise ValueError("La evidencia privada debe estar fuera del repositorio")
    base, backend_port = _origen_local(context["backend_origin"])
    database_port = context["database_port"]
    if (backend_port in {8000, 5432}
            or isinstance(database_port, bool) or not isinstance(database_port, int)
            or not 1 <= database_port <= 65535 or database_port == 5432
            or backend_port == database_port):
        raise ValueError("Puertos no permitidos para el ensayo aislado")
    run_id = context["run_id"]
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("Se requiere run_id")
    private_path = (run_dir / "fixture_privado.json").resolve()
    if not private_path.is_relative_to(run_dir):
        raise ValueError("La fixture privada debe pertenecer al entorno aislado")
    fixture = json.loads(private_path.read_text(encoding="utf-8"))
    origin, _ = _origen_local(fixture["origin"])
    if not isinstance(fixture.get("control"), str) or not fixture["control"]:
        raise ValueError("Falta control privado del reloj aislado")

    output = run_dir / ("api_e2e_" + uuid4().hex)
    output.mkdir(exist_ok=False)
    checks = []
    state = {}
    stage = "guard"
    authorized = False
    clock_reset = False
    error_type = None
    transport = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedirecciones())

    def check(name, ok, **extra):
        record = {"name": name, "passed": bool(ok)}
        if "status" in extra:
            record["status"] = int(extra["status"])
        if "expected" in extra:
            record["expected"] = [int(x) for x in extra["expected"]]
        checks.append(record)
        if not ok:
            raise AssertionError(name)

    class Actor:
        def __init__(self):
            self.opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}), _SinRedirecciones(),
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            )

        def call(self, method, path, data=None, files=None, csrf=True):
            if not authorized or not path.startswith("/api/"):
                raise RuntimeError("Actor fuera del entorno API autorizado")
            headers = {"Accept": "application/json", "Origin": origin}
            if method not in {"GET", "HEAD"} and csrf:
                token_status, token = self.call("GET", "/api/acceso/csrf/")
                if token_status != 200 or not isinstance(token.get("csrfToken"), str):
                    raise RuntimeError("No se obtuvo CSRF para el ensayo")
                headers["X-CSRFToken"] = token["csrfToken"]
            payload = None
            if files:
                boundary = "skilly" + uuid4().hex
                parts = []
                for key, value in (data or {}).items():
                    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"'
                                  f'\r\n\r\n{value}\r\n').encode())
                for key, (filename, content, mime) in files.items():
                    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; '
                                  f'filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode()
                                 + content + b"\r\n")
                parts.append(f"--{boundary}--\r\n".encode())
                payload = b"".join(parts)
                headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
            elif data is not None:
                payload = json.dumps(data).encode()
                headers["Content-Type"] = "application/json"
            request = urllib.request.Request(base + path, data=payload, method=method, headers=headers)
            try:
                response = self.opener.open(request, timeout=20)
            except urllib.error.HTTPError as response_error:
                response = response_error
            with response:
                raw = response.read()
                try:
                    body = json.loads(raw)
                except (ValueError, UnicodeError):
                    body = {"non_json": True, "bytes": len(raw)}
                return response.status, body

        def expect(self, name, method, path, data=None, files=None, expected=(200,), csrf=True):
            status, body = self.call(method, path, data, files, csrf)
            check(name, status in expected, status=status, expected=expected)
            return body

        def login(self, name, account):
            return self.expect(name, "POST", "/api/acceso/iniciar-sesion/", {
                "correo": account["email"], "contrasena": account["password"],
            })

    def advance(moment):
        if not authorized:
            raise RuntimeError("Reloj aislado no autorizado")
        request = urllib.request.Request(
            base + "/__isolated/clock",
            data=json.dumps({"now": moment.isoformat() if moment else None}).encode(),
            method="POST", headers={
                "Content-Type": "application/json", "X-Isolated-Control": fixture["control"],
            },
        )
        with transport.open(request, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError("No se pudo controlar el reloj aislado")

    try:
        with transport.open(base + "/__isolated/health", timeout=5) as response:
            health = json.load(response)
        check("isolated_health_guard", health.get("isolated") is True
              and health.get("run_id") == run_id
              and health.get("database_port") == database_port)
        authorized = True
        advance(None)
        admin, professional, company, anonymous = [Actor() for _ in range(4)]
        admin.login("admin_fixture_login", fixture["admin"])
        now = datetime.now(timezone.utc)
        account = {"email": "e2e-" + uuid4().hex + "@example.invalid", "password": secrets.token_urlsafe(32)}
        # Credenciales nuevas solo en una fixture privada externa creada para esta ejecucion.
        with (output / "fixture_privado.json").open("x", encoding="utf-8") as private:
            json.dump({"professional": account}, private)
        stage = "registro_profesional"
        professional.expect("professional_registration", "POST", "/api/acceso/registro-profesional/", {
            "correo": account["email"], "contrasena": account["password"],
            "confirmar_contrasena": account["password"], "nombres": "Profesional E2E",
            "apellidos": "Prueba aislada", "titulo_profesional": "Especialista de pruebas",
            "resumen": "Perfil sintetico para recorrido completo sin datos reales.", "ubicacion": "Santiago",
        }, expected=(201,))
        professional.login("professional_login", account)
        profile = professional.expect("professional_profile", "GET", "/api/profesionales/mi-perfil/")
        pid = _id(profile, "id_profesional")
        state["professional_id"] = pid
        pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
        stage = "documentos"
        professional.expect("invalid_document_rejected", "POST", "/api/profesionales/mis-documentos/subir/", {"tipo_documento": "Titulo profesional"}, files={"archivo": ("titulo.exe", b"invalid", "application/octet-stream")}, expected=(400,))
        doc = professional.expect("private_document_upload", "POST", "/api/profesionales/mis-documentos/subir/", {"tipo_documento": "Titulo profesional"}, files={"archivo": ("titulo.pdf", pdf, "application/pdf")}, expected=(201,))
        did = _id(doc, "id_documento")
        anonymous.expect("private_document_access_denied", "GET", f"/api/profesionales/mis-documentos/{did}/descargar/", expected=(403,))
        professional.expect("private_document_owner_download", "GET", f"/api/profesionales/mis-documentos/{did}/descargar/")
        validation = professional.expect("request_professional_validation", "POST", "/api/profesionales/mi-validacion/solicitar/", {}, expected=(201,))
        vid = _id(validation, "id_validacion")
        revision = f"/api/profesionales/administracion/validaciones/{vid}/resolver/"
        admin.expect("start_document_review", "POST", revision, {"accion": "INICIAR_REVISION"})
        admin.expect("reject_document_with_reason", "POST", revision, {"accion": "REVISAR_DOCUMENTO", "id_documento": did, "decision": "RECHAZADA", "observacion": "Documento sintetico requiere correccion visible."})
        correction = professional.expect("correct_rejected_document", "POST", "/api/profesionales/mis-documentos/subir/", {"tipo_documento": "Titulo profesional", "id_documento_reemplazado": did}, files={"archivo": ("titulo_corregido.pdf", pdf, "application/pdf")}, expected=(201,))
        did2 = _id(correction, "id_documento")
        admin.expect("approve_corrected_document", "POST", revision, {"accion": "REVISAR_DOCUMENTO", "id_documento": did2, "decision": "APROBADA", "observacion": "Correccion sintetica comprobada."})
        admin.expect("finish_document_review", "POST", revision, {"accion": "FINALIZAR_REVISION", "observacion": "Todos los documentos vigentes fueron revisados."})
        stage = "entrevista"
        day = (now + timedelta(days=1)).date()
        eid = None
        for hour in range(10, 20):
            slot = admin.expect(f"create_interview_slot_{hour}", "POST", "/api/profesionales/administracion/entrevistas/bloques/", {
                "fecha": day.isoformat(), "hora_inicio": f"{hour:02}:00:00", "hora_fin": f"{hour:02}:30:00",
                "capacidad": 1, "estado": "DISPONIBLE",
            }, expected=(201, 409))
            bid = _ident(slot, "id_bloque_entrevista")
            if bid is None:
                continue
            interview = professional.expect(f"reserve_interview_{hour}", "POST", "/api/profesionales/mi-entrevista/reservar/", {"id_bloque_entrevista": bid}, expected=(200, 201, 409))
            eid = _ident(interview, "id_entrevista")
            if eid is None:
                reserved = professional.expect(f"read_reserved_interview_{hour}", "GET", "/api/profesionales/mi-entrevista/")
                eid = _ident(reserved, "id_entrevista")
            if eid is not None:
                break
        check("interview_slot_reserved_without_bypassing_guard", isinstance(eid, int) and eid > 0)
        admin.expect("confirm_simulated_interview_contact", "POST", f"/api/profesionales/administracion/entrevistas/{eid}/contacto/", {"confirmar": True})
        result_path = f"/api/profesionales/administracion/validaciones/{vid}/resultado-entrevista/"
        interview_result = {"resultado": "APROBADO", "observacion": "Entrevista academica simulada completada satisfactoriamente.", "confirmacion_realizada": True}
        admin.expect("premature_interview_result_rejected", "POST", result_path, interview_result, expected=(409,))
        advance(now + timedelta(days=2))
        admin.expect("approve_professional_after_scheduled_end", "POST", result_path, interview_result)
        profile = professional.expect("approved_professional_profile", "GET", "/api/profesionales/mi-perfil/")
        check("professional_approved_state", _ident(profile, "estado_validacion") == "APROBADO")
        state["validated_professional"] = True
        stage = "servicio"
        catalog = professional.expect("service_catalogues", "GET", "/api/marketplace/catalogos/")
        category = _id(catalog, "id_categoria")
        proposed = {
            "nombre": "Servicio E2E desarrollo web " + uuid4().hex[:8],
            "descripcion": "Desarrollo de sitio web y documentos para una organizacion de prueba.",
            "id_categoria": category, "ids_competencias": [], "modalidad": "REMOTO",
            "alcance": "Sitio web, informe y codigo fuente con una correccion.", "referencia_precio": "25000 CLP",
        }
        service = professional.expect("create_service_proposal", "POST", "/api/marketplace/mis-servicios/", proposed, expected=(201,))
        sid = _id(service, "id_servicio")
        state["service_id"] = sid
        professional.expect("submit_service_review", "POST", f"/api/marketplace/mis-servicios/{sid}/enviar-revision/", {}, expected=(200, 201))
        review = f"/api/marketplace/administracion/servicios/{sid}/revisar/"
        admin.expect("request_service_corrections", "POST", review, {"decision": "SOLICITAR_CORRECCIONES", "observacion": "Precisar el alcance de la propuesta sintetica."}, expected=(200, 201))
        proposed["alcance"] = "Sitio web, informe y codigo fuente, una correccion y manual de uso."
        professional.expect("correct_service_proposal", "PATCH", f"/api/marketplace/mis-servicios/{sid}/", {"alcance": proposed["alcance"]})
        professional.expect("resubmit_service_review", "POST", f"/api/marketplace/mis-servicios/{sid}/enviar-revision/", {}, expected=(200, 201))
        admin.expect("approve_reviewed_service_version", "POST", review, {"decision": "APROBAR_REVISION", "version_propuesta": proposed, "observacion": "Propuesta sintetica revisada y precio confirmado."}, expected=(200, 201))
        professional.expect("professional_accepts_reviewed_version", "POST", f"/api/marketplace/mis-servicios/{sid}/version-revisada/", {}, expected=(200, 201))
        professional.expect("professional_publishes_service", "POST", f"/api/marketplace/mis-servicios/{sid}/publicar/", {}, expected=(200, 201))
        public = anonymous.expect("published_service_is_public", "GET", f"/api/marketplace/servicios/{sid}/")
        check("published_service_identity", _ident(public, "id_servicio") == sid)
        state["published"] = True
        stage = "ciclos_negocio"
        sys.path.insert(0, str(ROOT))
        from tools.e2e_ciclo_aislado import ejecutar_ciclos
        state["cycles"] = ejecutar_ciclos(admin, professional, company, anonymous, sid, pid,
                                          (now + timedelta(days=10)).date(), pdf, check, _ident)
        state["complete"] = True
    except Exception as error:
        error_type = type(error).__name__
    finally:
        if authorized:
            try:
                advance(None)
                clock_reset = True
            except Exception as error:
                if error_type is None:
                    error_type = type(error).__name__
        passed = bool(state.get("complete")) and all(x["passed"] for x in checks) and clock_reset and error_type is None
        result = {
            "passed": passed, "checks": checks, "stage": stage, "state": state,
            "error_type": error_type, "clock_reset": clock_reset,
            "real_http": True, "real_postgresql": True, "clock_simulated": True,
            "interview_human_validation": False, "economic_activity_simulated": True,
            "external_payments_or_email": False, "full_ui_journey": False,
        }
        with (output / "resultado.json").open("x", encoding="utf-8") as evidence:
            json.dump(result, evidence, indent=2)
        print("API_E2E_PASSED", passed, "CHECKS", len(checks))
        print("RESULT_DIRECTORY", output)
    return passed


def main():
    parser = argparse.ArgumentParser(description="Recorrido API E2E exclusivamente aislado de SKILLY")
    parser.add_argument("--context", required=True, type=Path, help="JSON local sin credenciales impresas")
    args = parser.parse_args()
    try:
        return 0 if ejecutar(args.context) else 1
    except Exception as error:
        # No imprimir excepciones que puedan contener URL, tokens o datos de fixture.
        print("API_E2E_CONTEXT_BLOCKED", type(error).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
