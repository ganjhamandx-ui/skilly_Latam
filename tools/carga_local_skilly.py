"""Carga HTTP gradual y acotada exclusivamente sobre dos workers SKILLY aislados.

No carga .env, abre SQL, borra bloques, cambia controles ni contacta proveedores.
El plan y las métricas son públicos; los IDs/snapshots sintéticos quedan en un
checkpoint privado externo para la comprobación SQL y limpieza posterior.
"""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import hashlib
from http.cookiejar import CookieJar
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CATALOG = "/api/marketplace/servicios/"
SESSION = "/api/acceso/sesion-actual/"
CSRF = "/api/acceso/csrf/"
LOGIN = "/api/acceso/iniciar-sesion/"
LOGOUT = "/api/acceso/cerrar-sesion/"
AVAILABILITY = "/api/solicitudes/mi-disponibilidad/"
MAX_WRITES = 64
MIN_AVAILABLE_RAM = 2 * 1024 ** 3


class LoadRejected(Exception):
    def __init__(self, code):
        self.code = code


def require(condition, code="configuration_rejected"):
    if not condition:
        raise LoadRejected(code)


def percentile(values, quantile):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


class Client:
    def __init__(self, origins, frontend):
        self.origins, self.frontend = tuple(origins), frontend
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()), NoRedirect())
        self.csrf = None
        self.owned = set()

    def request(self, worker, operation, *, method="GET", payload=None, block_id=None):
        fixed = {"catalog": CATALOG, "session": SESSION, "csrf": CSRF, "login": LOGIN,
                 "logout": LOGOUT, "availability": AVAILABILITY}
        require(type(worker) is int and worker in (0, 1), "worker_rejected")
        if operation == "update_availability":
            require(type(block_id) is int and block_id in self.owned and method == "PATCH", "foreign_block_rejected")
            path = AVAILABILITY + str(block_id) + "/"
        else:
            require(operation in fixed, "operation_rejected")
            path = fixed[operation]
        require(method in {"GET", "POST", "PATCH"}, "method_rejected")
        require(method != "POST" or operation in {"login", "logout", "availability"}, "write_rejected")
        headers = {"Accept": "application/json", "Origin": self.frontend}
        body = None
        if method != "GET":
            headers["Content-Type"] = "application/json"
            require(isinstance(self.csrf, str) and bool(self.csrf), "csrf_not_initialized")
            headers["X-CSRFToken"] = self.csrf
            body = json.dumps(payload or {}).encode("utf-8")
        request = Request(self.origins[worker] + path, data=body, method=method, headers=headers)
        started = time.perf_counter()
        try:
            response = self.opener.open(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(2_000_001)
            require(len(raw) <= 2_000_000, "response_too_large")
            parsed = json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else None
            return response.code, parsed, (time.perf_counter() - started) * 1000

    def refresh_csrf(self, worker):
        status, body, _ = self.request(worker, "csrf")
        require(status == 200 and isinstance(body, dict) and isinstance(body.get("csrfToken"), str), "csrf_preflight_failed")
        self.csrf = body["csrfToken"]


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.stop_reason = None
        self.phase = "preflight"
        self.samples = []
        self.resources = []
        self.write_counts = {}
        self.last_write = {}
        self.consecutive_5xx = 0

    def halt(self, reason):
        with self.lock:
            if self.stop_reason is None:
                self.stop_reason = reason
            self.stop.set()

    def reserve_write(self, phase, client_id, now):
        with self.lock:
            key = (phase, client_id)
            if self.stop.is_set() or self.write_counts.get(phase, 0) >= MAX_WRITES:
                return False
            if now - self.last_write.get(key, -math.inf) < 1:
                return False
            self.last_write[key] = now
            self.write_counts[phase] = self.write_counts.get(phase, 0) + 1
            return True

    def record(self, phase, operation, worker, status, latency, expected):
        with self.lock:
            self.samples.append({"phase": phase, "operation": operation, "worker": worker,
                                 "status": int(status), "latency_ms": round(latency, 3)})
            phase_samples = [sample for sample in self.samples if sample["phase"] == phase]
            count_5xx = sum(sample["status"] >= 500 for sample in phase_samples)
            self.consecutive_5xx = self.consecutive_5xx + 1 if status >= 500 else 0
            reason = None
            if self.consecutive_5xx >= 5:
                reason = "five_consecutive_5xx"
            elif count_5xx / len(phase_samples) > .01:
                reason = "http_5xx_over_one_percent"
            elif percentile([sample["latency_ms"] for sample in phase_samples], .95) > 3000:
                reason = "p95_over_three_seconds"
            elif status not in expected:
                reason = "unexpected_http_status"
            if reason and self.stop_reason is None:
                self.stop_reason = reason
                self.stop.set()


def load_launcher():
    spec = importlib.util.spec_from_file_location("_skilly_load_launcher", ROOT / "tools/entorno_local_skilly.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def settings_namespace_matches(path, expected):
    """Leer el literal generado sin importar/ejecutar configuración privada."""
    try:
        file = Path(path)
        if file.stat().st_size > 1_000_000:
            return False
        tree = ast.parse(file.read_text(encoding="utf-8"))
        values = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "KEY_PREFIX" and isinstance(target.value, ast.Subscript)
                        and isinstance(target.value.value, ast.Name) and target.value.value.id == "CACHES"
                        and isinstance(target.value.slice, ast.Name) and target.value.slice.id == "ACCESO_CACHE_ALIAS"):
                    values.append(ast.literal_eval(node.value))
        return values == [expected]
    except (OSError, ValueError, TypeError, SyntaxError):
        return False


def checked_context(launcher, value):
    context = launcher.context_from(value)
    require(context.get("database_port") == 57647 and context.get("external_payments_and_mail") is False,
            "isolated_database_required")
    frontend = urlsplit(context["frontend_origin"])
    require(frontend.scheme == "http" and frontend.hostname == "127.0.0.2" and frontend.port is not None
            and 1024 <= frontend.port <= 65535 and frontend.port not in {8000, 5173, 5432, 9000, 57647}
            and frontend.username is None and frontend.password is None
            and frontend.path == "" and not (frontend.query or frontend.fragment), "frontend_origin_rejected")
    run = Path(context["run_dir"]).resolve()
    workers = context.get("backend_workers")
    require(isinstance(workers, list) and len(workers) == 2, "two_workers_required")
    origins, pids, manifests = [], [], []
    for index, worker in enumerate(workers):
        origin = worker.get("origin")
        url = urlsplit(origin)
        require(url.scheme == "http" and url.hostname == "127.0.0.2" and url.port is not None
                and 1024 <= url.port <= 65535 and url.port not in {8000, 5173, 5432, 9000, 57647}
                and url.path == "" and url.username is None and url.password is None
                and not (url.query or url.fragment), "worker_origin_rejected")
        require(type(worker.get("pid")) is int and worker["pid"] > 0, "worker_pid_rejected")
        identity_path = Path(worker["source_identity_file"]).resolve()
        require(identity_path.parent == run and identity_path.name == ("backend_ready.json" if index == 0 else "backend_ready_2.json"), "manifest_rejected")
        identity = launcher.read_json(identity_path)
        require(identity.get("pid") == worker["pid"] and identity.get("project_root") == str(ROOT)
                and identity.get("wsgi_file") == str(ROOT / "backend/config/wsgi.py"), "worker_identity_rejected")
        sources = identity.get("product_sources")
        require(isinstance(sources, dict) and bool(sources), "source_manifest_required")
        for name, digest in sources.items():
            require(not Path(name).is_absolute() and ".." not in Path(name).parts, "source_path_rejected")
            file = (ROOT / name).resolve(strict=True)
            require(file.is_relative_to(ROOT / "backend") and file.suffix == ".py"
                    and isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest)
                    and hashlib.sha256(file.read_bytes()).hexdigest() == digest, "worker_sources_outdated")
        origins.append(origin)
        pids.append(worker["pid"])
        manifests.append(sources)
    require(len(set(origins)) == 2 and len(set(pids)) == 2 and manifests[0] == manifests[1], "workers_must_match")
    cache = context.get("access_cache", {})
    require(cache.get("host") == "127.0.0.1" and type(cache.get("port")) is int
            and 1024 <= cache["port"] <= 65535 and cache.get("database") == 15
            and isinstance(cache.get("key_prefix"), str)
            and re.fullmatch(r"skilly-local-[a-f0-9]{40}", cache["key_prefix"]), "shared_isolated_cache_required")
    require(settings_namespace_matches(run / "skilly_local.py", cache["key_prefix"]), "generated_cache_namespace_mismatch")
    return context, origins


def safe_fixture(launcher, context, value):
    file = Path(value)
    require(file.is_absolute(), "fixture_path_rejected")
    file = file.resolve(strict=True)
    require(file.is_relative_to(Path(context["backup_root"]).resolve()) and not file.is_relative_to(ROOT)
            and file.name == "fixture_privado.json", "fixture_path_rejected")
    fixture = launcher.read_json(file)
    actor = fixture.get("professional", {})
    require(isinstance(actor.get("email"), str) and actor["email"].endswith("@example.invalid")
            and isinstance(actor.get("password"), str) and bool(actor["password"]), "synthetic_professional_required")
    return actor, fixture.get("professional_id")


def write_json(launcher, path, data, *, exclusive=True):
    with launcher.native(path).open("x" if exclusive else "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def summarize(samples, elapsed):
    statuses, operations, workers = {}, {}, {}
    for sample in samples:
        statuses[str(sample["status"])] = statuses.get(str(sample["status"]), 0) + 1
        operations[sample["operation"]] = operations.get(sample["operation"], 0) + 1
        workers[str(sample["worker"])] = workers.get(str(sample["worker"]), 0) + 1
    durations = [sample["latency_ms"] for sample in samples]
    return {"requests": len(samples), "elapsed_seconds": round(elapsed, 3),
            "rps": round(len(samples) / elapsed, 3) if elapsed else 0,
            "p50_ms": percentile(durations, .50), "p95_ms": percentile(durations, .95),
            "p99_ms": percentile(durations, .99), "statuses": statuses,
            "operations": operations, "requests_by_worker": workers}


def resource_monitor(psutil, processes, metrics, done):
    psutil.cpu_percent(interval=None)
    for _, process in processes:
        process.cpu_percent(interval=None)
    high_cpu = 0
    while not done.wait(1):
        try:
            cpu, available = psutil.cpu_percent(interval=None), psutil.virtual_memory().available
            own = [{"role": role, "pid": process.pid, "cpu_percent": process.cpu_percent(interval=None),
                    "rss_bytes": process.memory_info().rss} for role, process in processes]
            with metrics.lock:
                metrics.resources.append({"phase": metrics.phase, "global_cpu_percent": cpu,
                                          "available_ram_bytes": available, "own_processes": own})
            high_cpu = high_cpu + 1 if cpu > 70 else 0
            if high_cpu >= 3:
                metrics.halt("global_cpu_over_70_three_samples")
            if available < MIN_AVAILABLE_RAM:
                metrics.halt("available_ram_below_two_gib")
        except Exception:
            metrics.halt("own_resource_monitor_unavailable")
            return


def run(args):
    launcher = load_launcher()
    context, origins = checked_context(launcher, args.contexto)
    actor, professional_id = safe_fixture(launcher, context, args.fixture)
    concurrency = [int(value) for value in args.concurrencias.split(",")]
    require(concurrency == sorted(set(concurrency)) and bool(concurrency)
            and all(value in {1, 2, 4, 8} for value in concurrency) and 2 <= args.segundos <= 10,
            "load_bounds_rejected")
    output = Path(args.output)
    require(output.is_absolute(), "output_path_rejected")
    output = output.resolve()
    require(output.is_relative_to(Path(context["backup_root"]).resolve()) and not output.is_relative_to(ROOT), "output_path_rejected")
    output.mkdir(exist_ok=False)
    plan = {"workers": 2, "worker_origins": origins, "concurrency": concurrency,
            "seconds_per_stage": args.segundos, "warmup_seconds": 2,
            "requests_per_client_iteration": 3, "minimum_iteration_interval_seconds": 1,
            "maximum_writes_per_stage": MAX_WRITES, "maximum_writes_per_client_per_second": 1,
            "operations": ["GET catalog", "GET authenticated session", "POST own unique availability", "PATCH same own availability"],
            "stop_limits": {"global_cpu_percent": 70, "consecutive_cpu_samples": 3, "sample_seconds": 1,
                            "minimum_available_ram_bytes": MIN_AVAILABLE_RAM, "http_5xx_ratio": .01,
                            "consecutive_5xx": 5, "p95_ms": 3000},
            "percentile_method": "linear interpolation over completed requests in each stage",
            "http_timeout_seconds": 3, "database_port": 57647, "new_payments": 0,
            "sql_integrity_verified": False, "plan_only": bool(args.plan_only)}
    write_json(launcher, output / "plan.json", plan)
    if args.plan_only:
        print(json.dumps({"planned": True, "load_executed": False, "output": str(output)}), flush=True)
        return 0
    metrics, monitor_done = Metrics(), threading.Event()
    clients, stages, created, preflight = [], [], [], []
    private_lock = threading.Lock()
    private_state = {"professional_id": professional_id, "original_availability": None,
                     "planned_slots": [], "created_blocks": created}
    monitor, stage = None, "dependency"
    started = time.perf_counter()
    try:
        try:
            import psutil
        except ImportError:
            raise LoadRejected("missing_psutil") from None
        require(psutil.virtual_memory().available >= MIN_AVAILABLE_RAM, "available_ram_below_two_gib")
        processes = []
        for index, worker in enumerate(context["backend_workers"]):
            process = psutil.Process(worker["pid"])
            require(str(Path(context["run_dir"]).resolve()).casefold() in " ".join(process.cmdline()).casefold(), "worker_pid_reused")
            processes.append(("backend_" + str(index), process))
        for field, role in (("frontend_pid", "frontend"), ("supervisor_pid", "supervisor")):
            process = psutil.Process(context[field])
            command = " ".join(process.cmdline()).replace("\\", "/").casefold()
            require((str(ROOT).replace("\\", "/").casefold() + "/") in command, "own_pid_reused")
            processes.append((role, process))
        monitor = threading.Thread(target=resource_monitor, args=(psutil, processes, metrics, monitor_done), daemon=True)
        monitor.start()
        stage = "preflight_login"
        for index in range(max(concurrency)):
            if metrics.stop.is_set():
                break
            client, worker = Client(origins, context["frontend_origin"]), index % 2
            client.refresh_csrf(worker)
            status, body, _ = client.request(worker, "login", method="POST", payload={"correo": actor["email"], "contrasena": actor["password"]})
            preflight.append({"operation": "login", "client": index, "worker": worker, "status": status})
            require(status == 200 and isinstance(body, dict) and body.get("usuario", {}).get("rol") == "PROFESIONAL", "professional_login_rejected")
            user_id = body["usuario"]["id_usuario"]
            require(type(user_id) is int and ("user_id" not in private_state or private_state["user_id"] == user_id), "actor_identity_changed")
            private_state["user_id"] = user_id
            client.refresh_csrf(1 - worker)
            clients.append(client)
        require(len(clients) == max(concurrency) and not metrics.stop.is_set(), "preflight_stopped")
        status, body, _ = clients[0].request(0, "availability")
        require(status == 200 and isinstance(body, dict) and isinstance(body.get("disponibilidad"), list), "availability_preflight_failed")
        private_state["original_availability"] = body["disponibilidad"]
        existing_dates = {block.get("fecha") for block in body["disponibilidad"]}
        slots = {}
        candidate = date.today() + timedelta(days=365)
        for count in concurrency:
            for index in range(count):
                while candidate.isoformat() in existing_dates:
                    candidate += timedelta(days=1)
                slot = {"fecha": candidate.isoformat(), "hora_inicio": "10:00:00", "hora_fin": "10:15:00"}
                slots[(count, index)] = slot
                private_state["planned_slots"].append({"concurrency": count, "client": index, **slot})
                candidate += timedelta(days=1)
        write_json(launcher, output / "fixture_carga_privado.json", private_state)

        def persist_private():
            temporary = output / (".checkpoint_" + uuid4().hex + ".tmp")
            write_json(launcher, temporary, private_state)
            os.replace(launcher.native(temporary), launcher.native(output / "fixture_carga_privado.json"))

        def stage_run(count, duration, *, warmup=False):
            label = "warmup" if warmup else "concurrency_" + str(count)
            with metrics.lock:
                metrics.phase = label
            phase_start = time.perf_counter()
            deadline = phase_start + duration

            def worker_job(index):
                client, block_id, iteration = clients[index], None, 0
                while not metrics.stop.is_set() and time.perf_counter() < deadline:
                    tick = time.perf_counter()
                    target = (index + iteration) % 2
                    for operation in ("catalog", "session"):
                        if metrics.stop.is_set():
                            break
                        request_start = time.perf_counter()
                        try:
                            status, body, latency = client.request(target, operation)
                            valid = (isinstance(body, dict) and ((operation == "catalog" and isinstance(body.get("servicios"), list))
                                     or (operation == "session" and body.get("usuario", {}).get("id_usuario") == private_state["user_id"])))
                            metrics.record(label, operation, target, status, latency, {200})
                            if status == 200 and not valid:
                                metrics.halt("response_contract_changed")
                        except Exception:
                            metrics.record(label, operation, target, 0, (time.perf_counter() - request_start) * 1000, {200})
                            metrics.halt("local_http_request_failed")
                    if not warmup and not metrics.stop.is_set() and time.perf_counter() < deadline and metrics.reserve_write(label, index, time.perf_counter()):
                        request_start, recorded = time.perf_counter(), False
                        operation = "create_own_availability" if block_id is None else "update_own_availability"
                        try:
                            if block_id is None:
                                status, body, latency = client.request(target, "availability", method="POST", payload=slots[(count, index)])
                                metrics.record(label, "create_own_availability", target, status, latency, {201})
                                recorded = True
                                require(status == 201 and isinstance(body, dict), "availability_create_failed")
                                value = body.get("disponibilidad", {})
                                require(type(value.get("id_disponibilidad")) is int, "created_block_id_missing")
                                block_id = value["id_disponibilidad"]
                                client.owned.add(block_id)
                                with private_lock:
                                    created.append({"id_disponibilidad": block_id, "concurrency": count, "client": index, **slots[(count, index)]})
                                    persist_private()
                                require(value.get("fecha") == slots[(count, index)]["fecha"]
                                        and value.get("estado") == "DISPONIBLE", "created_block_contract_changed")
                            else:
                                end = "10:16:00" if iteration % 2 else "10:15:00"
                                status, body, latency = client.request(target, "update_availability", method="PATCH", payload={"hora_fin": end}, block_id=block_id)
                                metrics.record(label, "update_own_availability", target, status, latency, {200})
                                recorded = True
                                require(status == 200 and isinstance(body, dict) and body.get("disponibilidad", {}).get("id_disponibilidad") == block_id,
                                        "updated_block_contract_changed")
                        except Exception:
                            if not recorded:
                                metrics.record(label, operation, target, 0, (time.perf_counter() - request_start) * 1000, {200, 201})
                            metrics.halt("availability_write_failed")
                    iteration += 1
                    remaining = min(deadline, tick + 1) - time.perf_counter()
                    if remaining > 0:
                        metrics.stop.wait(remaining)

            with ThreadPoolExecutor(max_workers=count) as pool:
                futures = [pool.submit(worker_job, index) for index in range(count)]
                for future in futures:
                    future.result()
            elapsed = time.perf_counter() - phase_start
            with metrics.lock:
                samples = [sample for sample in metrics.samples if sample["phase"] == label]
            summary = {"phase": label, "concurrency": count, "planned_seconds": duration,
                       "reserved_writes": metrics.write_counts.get(label, 0), **summarize(samples, elapsed)}
            stages.append(summary)

        stage = "warmup"
        stage_run(1, 2, warmup=True)
        for count in concurrency:
            if metrics.stop.is_set():
                break
            stage = "load"
            stage_run(count, args.segundos)
        if not metrics.stop.is_set():
            stage = "final_source_identity"
            checked_context(launcher, args.contexto)
    except LoadRejected as error:
        metrics.halt(error.code)
    except Exception:
        metrics.halt("load_setup_or_execution_failed")
    finally:
        for index, client in enumerate(clients):
            try:
                status, _, _ = client.request(index % 2, "logout", method="POST")
                preflight.append({"operation": "logout", "client": index, "worker": index % 2, "status": status})
                require(status == 200, "session_cleanup_failed")
            except Exception:
                metrics.halt("session_cleanup_failed")
        monitor_done.set()
        if monitor is not None:
            monitor.join(timeout=2)
    executed = [item for item in stages if item["phase"] != "warmup"]
    completed = not metrics.stop.is_set() and len(executed) == len(concurrency)
    result = {"completed": completed, "load_executed": bool(executed), "stage": stage,
              "stop_reason": metrics.stop_reason, "elapsed_seconds": round(time.perf_counter() - started, 3),
              "stages": stages, "resource_samples": len(metrics.resources), "created_blocks": len(created),
              "preflight_and_cleanup_statuses": preflight,
              "transport_or_parse_failures": sum(sample["status"] == 0 for sample in metrics.samples),
              "new_payments": 0, "external_mail": 0, "sql_integrity_verified": False,
              "limitations": ["Carga local acotada; no certifica capacidad productiva.",
                              "Solo IDs creados por este ensayo pueden retirarse tras la comprobación SQL separada."]}
    write_json(launcher, output / "requests.json", metrics.samples)
    write_json(launcher, output / "resources.json", metrics.resources)
    write_json(launcher, output / "resultado.json", result)
    print(json.dumps({"completed": completed, "load_executed": bool(executed), "stop_reason": metrics.stop_reason,
                      "created_blocks": len(created), "output": str(output)}), flush=True)
    return 0 if completed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contexto", "fixture", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--concurrencias", default="1,2,4,8")
    parser.add_argument("--segundos", type=int, default=10)
    parser.add_argument("--plan-only", action="store_true")
    return run(parser.parse_args())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({"completed": False, "stage": "arguments_or_context", "error_type": "LoadConfigurationError"}), flush=True)
        raise SystemExit(1) from None
