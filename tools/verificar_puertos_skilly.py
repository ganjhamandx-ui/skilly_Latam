"""Verificación HTTP local: sesiones, CSRF/CORS y retorno ya confirmado.

No inicia procesos, carga .env, conecta directamente a PostgreSQL ni contacta
proveedores. Las únicas escrituras son sesiones y dos callbacks idempotentes de
un checkout sintético previamente autorizado, validado antes de enviar su token.
"""
import argparse
import hashlib
from http.cookiejar import CookieJar
import importlib.util
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CSRF = "/api/acceso/csrf/"
LOGIN = "/api/acceso/iniciar-sesion/"
LOGOUT = "/api/acceso/cerrar-sesion/"
SESSION = "/api/acceso/sesion-actual/"
ADMIN = "/api/backoffice/configuracion/cuentas-bancarias/"
CALLBACK = "/api/pagos/webpay/retorno/"
APP = "/src/App.jsx"
MAX_BODY = 2_000_000


class VerificationRejected(Exception):
    pass


def require(condition):
    if not condition:
        raise VerificationRejected()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


class LocalHttp:
    def __init__(self, origins):
        self.origins = set(origins)
        self.cookies = CookieJar()
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(self.cookies), NoRedirect())

    def request(self, origin, path, *, method="GET", headers=None, body=None):
        require(origin in self.origins and method in {"GET", "POST"})
        fixed = {CSRF, LOGIN, LOGOUT, SESSION, ADMIN, CALLBACK, APP}
        require(path in fixed or re.fullmatch(r"/api/pagos/empresa/[A-Za-z0-9_.%~-]+/estado/", path))
        require(method != "POST" or path in {LOGIN, LOGOUT, CALLBACK})
        request = Request(origin + path, data=body, method=method,
                          headers={"Accept": "application/json", **(headers or {})})
        try:
            response = self.opener.open(request, timeout=10)
        except HTTPError as error:
            # 302 y rechazos se inspeccionan sin seguir el destino ni imprimirlo.
            response = error
        with response:
            content = response.read(MAX_BODY + 1)
            require(len(content) <= MAX_BODY)
            parsed = json.loads(content) if "application/json" in response.headers.get("Content-Type", "") else None
            return response.code, response.headers, parsed, content


def load_launcher():
    spec = importlib.util.spec_from_file_location("_skilly_local_verification", ROOT / "tools/entorno_local_skilly.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_json(launcher, backup, value, basename):
    file = Path(value)
    require(file.is_absolute())
    file = Path(str(launcher.native(file).resolve(strict=True)).removeprefix('\\\\?\\'))
    require(file.is_relative_to(backup) and not file.is_relative_to(ROOT)
            and file.name == basename)
    return file, launcher.read_json(file)


def product_sources_current(launcher, context):
    identity = launcher.read_json(context["source_identity_file"])
    require(identity.get("project_root") == str(ROOT)
            and identity.get("wsgi_file") == str(ROOT / "backend/config/wsgi.py")
            and identity.get("pid") == context["backend_pid"])
    sources = identity.get("product_sources")
    require(isinstance(sources, dict) and bool(sources))
    for name, digest in sources.items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts)
        source = (ROOT / name).resolve(strict=True)
        require(source.is_relative_to(ROOT / "backend") and source.suffix == ".py"
                and isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest))
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            return False
    return True


def run(args):
    launcher = load_launcher()
    context = launcher.context_from(args.contexto)
    backup, run_dir = Path(context["backup_root"]).resolve(), Path(context["run_dir"]).resolve()
    frontend, backend = context["frontend_origin"], context["backend_origin"]
    ports = []
    for origin in (frontend, backend):
        url = urlsplit(origin)
        require(url.scheme == "http" and url.hostname == "127.0.0.2" and url.port is not None
                and 1024 <= url.port <= 65535 and url.port not in {8000, 5173, 5432, 9000}
                and url.path == "" and not (url.username or url.password or url.query or url.fragment))
        ports.append(url.port)
    require(type(context["database_port"]) is int and context["database_port"] not in {8000, 5173, 5432, 9000}
            and len(set([*ports, context["database_port"]])) == 3
            and context.get("external_payments_and_mail") is False)
    output = run_dir / ("verificacion_http_" + uuid4().hex)
    output.mkdir(exist_ok=False)
    checks, errors = [], []
    stage = "fixtures"

    def check(name, condition, status=None):
        item = {"name": name, "passed": bool(condition)}
        if status is not None:
            item["status"] = int(status)
        checks.append(item)
        require(condition)

    try:
        check("backend_importa_fuentes_actuales_antes", product_sources_current(launcher, context))
        _, actors = private_json(launcher, backup, args.actores, "fixture_privado.json")
        payment_file, payment_fixture = private_json(launcher, backup, args.pago, "fixture_privado.json")
        checkout_file, checkout = private_json(launcher, backup, args.checkout, "checkout_privado.json")
        require(checkout_file.parent.parent == payment_file.parent)
        previous = launcher.read_json(checkout_file.parent / "resultado.json")
        require(previous.get("completed") is True and previous.get("authorization_verified") is True
                and previous.get("real_money") is False and previous.get("production_provider") is False
                and previous.get("provider_calls") == {"POST": 1, "PUT": 1})
        admin = actors.get("admin", {})
        require(isinstance(admin.get("email"), str) and admin["email"].endswith("@example.invalid")
                and isinstance(admin.get("password"), str) and bool(admin["password"])
                and type(admin.get("id")) is int)
        reference, prestation = payment_fixture.get("reference"), payment_fixture.get("prestacion_id")
        token = checkout.get("token")
        require(isinstance(reference, str) and bool(reference) and type(prestation) is int
                and isinstance(token, str) and re.fullmatch(r"[A-Za-z0-9_.-]{5,200}", token)
                and checkout.get("ambiente") == "TRANSBANK_INTEGRACION")
        client = LocalHttp((frontend, backend))

        def csrf_token():
            status, _, body, _ = client.request(frontend, CSRF)
            require(status == 200 and isinstance(body, dict) and isinstance(body.get("csrfToken"), str))
            return body["csrfToken"]

        stage = "csrf_login"
        csrf = csrf_token()
        credentials = json.dumps({"correo": admin["email"], "contrasena": admin["password"]}).encode("utf-8")
        unknown_origin = "http://127.0.0.3:" + str(ports[0])
        for name, origin, csrf_header in (
            ("login_sin_csrf_rechazado", frontend, None),
            ("login_csrf_incorrecto_rechazado", frontend, "x" * len(csrf)),
            ("login_origen_ajeno_rechazado", unknown_origin, csrf),
        ):
            headers = {"Content-Type": "application/json", "Origin": origin}
            if csrf_header is not None:
                headers["X-CSRFToken"] = csrf_header
            status, _, _, _ = client.request(frontend, LOGIN, method="POST", headers=headers, body=credentials)
            check(name, status == 403, status)
        status, _, body, _ = client.request(frontend, LOGIN, method="POST", body=credentials, headers={
            "Content-Type": "application/json", "Origin": frontend, "X-CSRFToken": csrf,
        })
        check("login_legitimo_proxy_y_rol", status == 200 and isinstance(body, dict)
              and body.get("usuario", {}).get("rol") == "ADMIN_SKILLY"
              and body.get("usuario", {}).get("id_usuario") == admin["id"], status)
        sessions = [cookie for cookie in client.cookies if cookie.name == "skilly_session"]
        check("cookie_sesion_http_only_samesite_host_aislado", len(sessions) == 1
              and sessions[0].domain == "127.0.0.2" and sessions[0].path == "/"
              and sessions[0].has_nonstandard_attr("HttpOnly")
              and sessions[0].get_nonstandard_attr("SameSite", "").lower() == "lax")
        status, _, body, _ = client.request(frontend, SESSION)
        check("sesion_actual_autenticada_proxy", status == 200 and isinstance(body, dict)
              and body.get("usuario", {}).get("rol") == "ADMIN_SKILLY", status)
        status, _, _, _ = client.request(frontend, ADMIN)
        check("lectura_administrativa_autenticada", status == 200, status)

        stage = "cors_y_producto"
        status, headers, _, _ = client.request(backend, CSRF, headers={"Origin": frontend})
        check("cors_solo_origen_configurado_con_credenciales", status == 200
              and headers.get("Access-Control-Allow-Origin") == frontend
              and headers.get("Access-Control-Allow-Credentials") == "true", status)
        status, headers, _, _ = client.request(backend, CSRF, headers={"Origin": unknown_origin})
        check("cors_origen_ajeno_sin_autorizacion", status == 200
              and headers.get("Access-Control-Allow-Origin") is None, status)
        status, _, _, content = client.request(frontend, APP)
        check("vite_sirve_app_actual_con_guardia_solicitud", status == 200
              and b"solicitudEnCurso" in content, status)

        stage = "callback_previamente_confirmado"
        state_path = "/api/pagos/empresa/" + quote(reference, safe="") + "/estado/"
        status, _, state_before, _ = client.request(frontend, state_path)
        check("pago_previamente_retenido_en_prestacion_correcta", status == 200 and isinstance(state_before, dict)
              and state_before.get("estado_pago") == "RETENIDO"
              and state_before.get("id_prestacion") == prestation, status)
        callback_body = urlencode({"token_ws": token}).encode("ascii")
        for attempt in (1, 2):
            status, headers, _, _ = client.request(frontend, CALLBACK, method="POST", body=callback_body,
                                                   headers={"Content-Type": "application/x-www-form-urlencoded"})
            location = urlsplit(headers.get("Location", ""))
            query = parse_qs(location.query, strict_parsing=True)
            check("callback_confirmado_idempotente_destino_configurado_" + str(attempt), status == 302
                  and location.scheme + "://" + location.netloc == frontend
                  and location.path == "/seguimiento" and not location.fragment
                  and set(query) == {"referencia", "webpay"} and query["webpay"] == ["aprobado"]
                  and len(query["referencia"]) == 1 and bool(query["referencia"][0])
                  and urlencode({name: values[0] for name, values in query.items()}) == location.query, status)
        status, _, state_after, _ = client.request(frontend, state_path)
        check("estado_pago_sin_cambios_tras_callbacks", status == 200 and state_after == state_before, status)

        stage = "logout"
        csrf = csrf_token()
        status, _, _, _ = client.request(frontend, LOGOUT, method="POST", body=b"{}", headers={
            "Content-Type": "application/json", "Origin": frontend, "X-CSRFToken": csrf,
        })
        check("logout_legitimo_proxy", status == 200, status)
        status, _, _, _ = client.request(frontend, ADMIN)
        check("administracion_rechazada_despues_logout", status == 403, status)
        status, _, _, _ = client.request(frontend, SESSION)
        check("sesion_revocada_despues_logout", status == 403, status)
        check("backend_importa_fuentes_actuales_despues", product_sources_current(launcher, context))
    except Exception as error:
        kind = type(error).__name__
        errors.append({"stage": stage, "error_type": kind if kind in {
            "VerificationRejected", "JSONDecodeError", "FileNotFoundError", "PermissionError", "ValueError",
        } else "HTTPVerificationError"})
    result = {"completed": not errors, "checks": checks, "passed": sum(item["passed"] for item in checks),
              "failed": sum(not item["passed"] for item in checks), "errors": errors,
              "frontend": frontend, "backend": backend, "isolated_database": True,
              "provider_requests_by_checker": 0, "new_checkouts": 0,
              "scope": "HTTP real contra producto local; sesiones y callback ya confirmado; sin pago nuevo ni proveedor"}
    with launcher.native(output / "resultado.json").open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
    print(json.dumps({"completed": result["completed"], "passed": result["passed"], "failed": result["failed"],
                      "errors": errors, "evidence": str(output)}), flush=True)
    return 0 if result["completed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contexto", "actores", "pago", "checkout"):
        parser.add_argument("--" + name, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # No mostrar excepciones de JSON, transporte o fixture que puedan incluir datos.
        print(json.dumps({"completed": False, "stage": "setup", "error_type": "HTTPVerificationError"}), flush=True)
        raise SystemExit(1) from None
