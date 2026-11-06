"""Cobertura Python real: unitarias offline o proceso de servidor aislado.

No instrumenta retroactivamente un servidor existente. El modo servidor exige
contexto externo, script dentro de run_dir y puerto PostgreSQL no operativo.
Los checkpoints permiten conservar datos antes de un cierre controlado.
"""
import argparse
import atexit
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT.parent / "SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b"
CONFIG = Path(__file__).with_name("python_coverage.ini")


def _destino(value, nuevo=True):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("La carpeta de evidencia debe ser absoluta")
    path = path.resolve()
    if not path.is_relative_to(BACKUP.resolve()) or path.is_relative_to(ROOT):
        raise ValueError("La evidencia debe quedar bajo el respaldo externo")
    if nuevo:
        path.mkdir(exist_ok=False)
    elif not path.is_dir():
        raise ValueError("No existe la carpeta de evidencia")
    return path


def _medidor(output):
    try:
        import coverage
    except ImportError as exc:
        raise RuntimeError("Falta coverage.py; instalar requirements-dev.txt en el entorno virtual") from exc
    return coverage.Coverage(
        config_file=str(CONFIG), data_file=str(output / ".coverage"),
    )


def _informes(cov, output):
    cov.xml_report(outfile=str(output / "coverage.xml"))
    cov.json_report(outfile=str(output / "coverage.json"))
    xml = ET.parse(output / "coverage.xml").getroot()
    files = [node.attrib["filename"] for node in xml.findall(".//class")]
    return {
        "lines_covered": int(xml.attrib["lines-covered"]),
        "lines_valid": int(xml.attrib["lines-valid"]),
        "branches_covered": int(xml.attrib["branches-covered"]),
        "branches_valid": int(xml.attrib["branches-valid"]),
        "files": len(files),
        "report": str(output / "coverage.xml"),
        "scope": "Python backend; excludes tests, migrations and uploads",
    }


def _bloqueado(*args, **kwargs):
    raise RuntimeError("Cobertura unitaria: red y conexiones de base de datos bloqueadas")


def unitarias(output):
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
    cov = _medidor(output)
    cov.start()
    salida = io.StringIO()
    resumen = {}
    secretos = []
    codigo = 1
    try:
        import django
        import psycopg
        from django.db.backends.base.base import BaseDatabaseWrapper
        with (
            patch.object(socket.socket, "connect", _bloqueado),
            patch.object(socket, "create_connection", _bloqueado),
            patch.object(psycopg, "connect", _bloqueado),
            patch.object(BaseDatabaseWrapper, "ensure_connection", _bloqueado),
            contextlib.redirect_stdout(salida),
            contextlib.redirect_stderr(salida),
        ):
            django.setup()
            from django.apps import apps
            from django.conf import settings
            from django.core.management import call_command
            from django.test import override_settings
            from django.test.runner import DiscoverRunner
            secretos = [
                settings.SECRET_KEY,
                settings.DATABASES["default"].get("PASSWORD"),
                settings.DATABASES["default"].get("USER"),
            ]

            class Runner(DiscoverRunner):
                def suite_result(self, suite, result, **kwargs):
                    resumen.update({
                        "tests": result.testsRun, "failures": len(result.failures),
                        "errors": len(result.errors), "skipped": len(result.skipped),
                    })
                    return super().suite_result(suite, result, **kwargs)

            labels = [app.name for app in apps.get_app_configs()
                      if Path(app.path).resolve().is_relative_to(ROOT / "backend")]
            labels += ["pruebas." + path.stem
                       for path in sorted((ROOT / "pruebas").glob("test*.py"))]
            call_command("check")
            with tempfile.TemporaryDirectory(prefix="skilly_coverage_media_") as media:
                with override_settings(
                    DATABASES={"default": {"ENGINE": "django.db.backends.dummy"}},
                    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                    MEDIA_ROOT=media,
                ):
                    codigo = Runner(verbosity=2, interactive=False).run_tests(labels)
    except Exception as exc:
        resumen["runner_error_type"] = type(exc).__name__
    finally:
        cov.stop()
        cov.save()
        texto = salida.getvalue()
        for secreto in secretos:
            if secreto:
                texto = texto.replace(secreto, "<redacted>")
        (output / "tests.log").write_text(texto, encoding="utf-8")
    resumen.update({"exit_code": codigo, "real_network_or_database": False})
    resumen["coverage"] = _informes(cov, output)
    (output / "resultado.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(json.dumps(resumen))
    return codigo


def servidor(output, context_path, script_path):
    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    run_dir = Path(context["run_dir"]).resolve()
    script = Path(script_path).resolve()
    origin = urlsplit(context["backend_origin"])
    port = int(context["database_port"])
    if (run_dir.is_relative_to(ROOT) or not run_dir.is_relative_to(BACKUP.resolve())
            or not script.is_relative_to(run_dir) or not script.is_file()
            or origin.hostname not in {"localhost", "127.0.0.1", "::1"}
            or origin.port in {None, 8000, 5432} or port == 5432
            or not context.get("run_id") or origin.username or origin.password):
        raise ValueError("Contexto aislado invalido")
    if (os.environ.get("POSTGRES_HOST") not in {"localhost", "127.0.0.1", "::1"}
            or os.environ.get("POSTGRES_PORT") != str(port)):
        raise ValueError("El entorno del proceso no coincide con PostgreSQL aislado")
    # El script externo sigue siendo responsable de verificar data_directory y
    # bloquear transportes de pagos/correo antes de abrir el servidor.
    cov = _medidor(output)
    cov.start()
    terminar = threading.Event()

    def checkpoint():
        while not terminar.wait(1):
            cov.save()

    def cierre():
        terminar.set()
        cov.stop()
        cov.save()

    atexit.register(cierre)
    threading.Thread(target=checkpoint, name="coverage-checkpoint", daemon=True).start()
    sys.path[:0] = [str(run_dir), str(ROOT / "backend"), str(ROOT)]
    (output / "instrumentacion.json").write_text(json.dumps({
        "run_id": context["run_id"], "backend_port": origin.port,
        "database_port": port, "checkpoint_seconds": 1,
        "scope": "This new Python server process only; not a running server",
    }, indent=2), encoding="utf-8")
    runpy.run_path(str(script), run_name="__main__")
    cierre()
    atexit.unregister(cierre)
    _informes(cov, output)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modo", choices=["unitarias", "servidor", "informes"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--context")
    parser.add_argument("--script")
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    os.chdir(ROOT)
    output = _destino(args.output, nuevo=args.modo != "informes")
    if args.modo == "unitarias":
        return unitarias(output)
    if args.modo == "servidor":
        if not args.context or not args.script:
            parser.error("servidor exige --context y --script")
        return servidor(output, args.context, args.script)
    cov = _medidor(output)
    cov.load()
    print(json.dumps(_informes(cov, output)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
