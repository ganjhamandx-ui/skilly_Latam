import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


SCRIPT_MIGRACION = r'''
import json
import os

from django.conf import settings

settings.configure(
    SECRET_KEY="prueba-aislada-no-productiva",
    INSTALLED_APPS=["reagendamientos"],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ["SKILLY_REAG_DB_AISLADA"],
        }
    },
    DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    USE_TZ=True,
)

import django
django.setup()

from django.core.management import call_command
from django.db import connection

call_command("migrate", "reagendamientos", "0001", verbosity=0)

filas = [
    (1, "PENDIENTE_PROFESIONAL", 501),
    (2, "PENDIENTE_ORGANIZACION", 502),
    (3, "LISTO_CONFIRMAR", 503),
    (4, "PENDIENTE_ORGANIZACION", 504),
]
with connection.cursor() as cursor:
    for identificador, estado, bloque in filas:
        cursor.execute(
            """
            INSERT INTO solicitud_reagendamiento (
                id, prestacion_id, solicitud_id, profesional_id,
                bloque_original_id, bloque_propuesto_id,
                motivo_organizacion, motivo_profesional, estado,
                requiere_confirmacion_organizacion,
                fecha_creacion, fecha_actualizacion
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                identificador, 100 + identificador, 200 + identificador, 7,
                400 + identificador, bloque, "motivo histórico", "",
                estado, estado in {"PENDIENTE_ORGANIZACION", "LISTO_CONFIRMAR"},
                "2026-01-01T12:00:00+00:00", "2026-01-01T12:00:00+00:00",
            ],
        )
    cursor.execute(
        """
        INSERT INTO evento_reagendamiento (
            actor, accion, detalle, fecha, reagendamiento_id
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        ["PROFESIONAL", "ACEPTAR", "aceptación histórica", "2026-01-02T12:00:00+00:00", 2],
    )
    cursor.execute(
        """
        INSERT INTO evento_reagendamiento (
            actor, accion, detalle, fecha, reagendamiento_id
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        ["PROFESIONAL", "ACEPTAR", "aceptación anterior", "2026-01-01T18:00:00+00:00", 4],
    )
    cursor.execute(
        """
        INSERT INTO evento_reagendamiento (
            actor, accion, detalle, fecha, reagendamiento_id
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        ["PROFESIONAL", "CREAR_ALTERNATIVA", "alternativa histórica", "2026-01-02T12:00:00+00:00", 4],
    )

call_command("migrate", "reagendamientos", "0002", verbosity=0)

with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT id, estado, organizacion_autorizo_cambio,
               profesional_confirmo_bloque, politica_version
        FROM solicitud_reagendamiento
        ORDER BY id
        """
    )
    solicitudes = cursor.fetchall()
    cursor.execute(
        """
        SELECT reagendamiento_id, bloque_id, estado
        FROM alternativa_reagendamiento
        ORDER BY reagendamiento_id
        """
    )
    alternativas = cursor.fetchall()

print(json.dumps({"solicitudes": solicitudes, "alternativas": alternativas}))
'''


class MigracionBilateralAisladaTests(unittest.TestCase):
    def test_migracion_preserva_y_adapta_expedientes_historicos(self):
        backend = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="skilly-reagendamientos-") as temporal:
            entorno = os.environ.copy()
            entorno["SKILLY_REAG_DB_AISLADA"] = str(Path(temporal) / "reag.sqlite3")
            resultado = subprocess.run(
                [sys.executable, "-c", textwrap.dedent(SCRIPT_MIGRACION)],
                cwd=backend,
                env=entorno,
                check=True,
                capture_output=True,
                text=True,
            )

        datos = json.loads(resultado.stdout.strip().splitlines()[-1])
        self.assertEqual(datos["solicitudes"], [
            [1, "PENDIENTE_PROFESIONAL", True, False, "LEGACY_NO_REGISTRADA"],
            [2, "LISTO_CONFIRMAR", True, True, "LEGACY_NO_REGISTRADA"],
            [3, "LISTO_CONFIRMAR", True, True, "LEGACY_NO_REGISTRADA"],
            [4, "PENDIENTE_ORGANIZACION", False, True, "LEGACY_NO_REGISTRADA"],
        ])
        self.assertEqual(datos["alternativas"], [
            [1, 501, "PROPUESTA_ADMIN"],
            [2, 502, "SELECCIONADA"],
            [3, 503, "SELECCIONADA"],
            [4, 504, "HABILITADA"],
        ])
