
from pathlib import Path
import os
import sys

# ============================================================
# SKILLY - CONTROL PERMANENTE DE CODIFICACION UTF-8
# Archivos del proyecto + datos textuales de PostgreSQL.
# Este programa solo lee: no escribe archivos ni actualiza BD.
# ============================================================

RAIZ = Path(__file__).resolve().parent.parent

EXTENSIONES = {
    ".py", ".jsx", ".js", ".css", ".tsx", ".ts",
    ".html", ".sql", ".ps1", ".json",
}

EXCLUIR = {
    ".venv", "node_modules", "__pycache__", "migrations",
    "dist", ".git", "coverage", "build",
    "respaldos_backend", "respaldos_frontend",
    "respaldos_codificacion", "respaldos_credenciales",
}

CARACTERES_SOSPECHOSOS = {
    chr(0x00C3),
    chr(0x00C2),
    chr(0xFFFD),
}

PREFIJOS_DANADOS = (
    chr(0x00E2) + chr(0x20AC),
    chr(0x00E2) + chr(0x2020),
    chr(0x00E2) + chr(0x201C),
    chr(0x00E2) + chr(0x201D),
)

CAMPOS_PRIVADOS = (
    "password", "contrasena", "clave", "token",
    "secret", "secreto", "hash", "codigo",
    "otp", "salt", "credential", "credencial",
    "api_key", "apikey",
)


# Detecta posibles errores de conversion de caracteres.
# No altera ni repara automaticamente los valores.
def texto_sospechoso(texto):
    return (
        any(
            caracter in texto
            for caracter in CARACTERES_SOSPECHOSOS
        )
        or any(
            prefijo in texto
            for prefijo in PREFIJOS_DANADOS
        )
    )


def linea_sospechosa(linea):
    # Un signo ASCII '?' puede ser sintaxis valida (regex, ternarios o URLs).
    # No permite distinguir texto danado de codigo; las senales de mojibake y
    # el caracter de reemplazo se detectan aqui, y UTF-8 invalido al leer.
    return texto_sospechoso(linea)


def obtener_archivos():
    carpetas = [
        RAIZ / "backend",
        RAIZ / "frontend" / "src",
        RAIZ / "database",
        RAIZ / "tools",
    ]

    archivos = set()

    for carpeta in carpetas:
        if not carpeta.is_dir():
            continue

        for ruta in carpeta.rglob("*"):
            if not ruta.is_file():
                continue

            if ruta.suffix.lower() not in EXTENSIONES:
                continue

            if any(
                parte in EXCLUIR
                for parte in ruta.relative_to(RAIZ).parts
            ):
                continue

            archivos.add(ruta)

    adicionales = (
        RAIZ / "frontend" / "index.html",
        RAIZ / "frontend" / "vite.config.js",
    )

    for ruta in adicionales:
        if ruta.is_file():
            archivos.add(ruta)

    return sorted(archivos)


def revisar_archivos():
    print("\n===== 1. ARCHIVOS DEL PROYECTO =====")

    archivos = obtener_archivos()

    archivos_afectados = 0
    lineas_afectadas = 0
    archivos_invalidos = 0

    for ruta in archivos:
        try:
            contenido = ruta.read_text(
                encoding="utf-8-sig"
            )

        except (UnicodeError, OSError) as error:
            archivos_invalidos += 1

            print(
                "LECTURA/UTF8 INVALIDO:",
                ruta.relative_to(RAIZ)
            )
            print("MOTIVO:", type(error).__name__)
            continue

        coincidencias = [
            (numero, linea)
            for numero, linea in enumerate(
                contenido.splitlines(), 1
            )
            if linea_sospechosa(linea)
        ]

        if not coincidencias:
            continue

        archivos_afectados += 1
        lineas_afectadas += len(coincidencias)

        print(
            "\nARCHIVO:",
            ruta.relative_to(RAIZ)
        )

        for numero, linea in coincidencias[:10]:
            print(
                "LINEA",
                numero,
                ":",
                ascii(linea.strip()[:140])
            )

        if len(coincidencias) > 10:
            print(
                "OTRAS COINCIDENCIAS:",
                len(coincidencias) - 10
            )

    print("\nARCHIVOS REVISADOS:", len(archivos))
    print("ARCHIVOS SOSPECHOSOS:", archivos_afectados)
    print("LINEAS SOSPECHOSAS:", lineas_afectadas)
    print("ARCHIVOS INVALIDOS:", archivos_invalidos)

    return (
        archivos_afectados
        + lineas_afectadas
        + archivos_invalidos
    )


def revisar_postgresql():
    print("\n===== 2. DATOS DE POSTGRESQL =====")

    backend = RAIZ / "backend"

    if not backend.is_dir():
        print("ERROR: No se encontro la carpeta backend.")
        return False

    # Usar la configuracion real del backend de SKILLY.
    sys.path.insert(0, str(backend))

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings"
    )

    conexion = None

    try:
        import django

        django.setup()

        from django.db import connection

        conexion = connection

        with conexion.cursor() as cursor:

            # --------------------------------------------
            # Comprobar codificacion real de PostgreSQL.
            # --------------------------------------------

            cursor.execute("SHOW server_encoding")
            servidor = cursor.fetchone()[0]

            cursor.execute("SHOW client_encoding")
            cliente = cursor.fetchone()[0]

            print("SERVER_ENCODING:", servidor)
            print("CLIENT_ENCODING:", cliente)

            if (
                servidor.upper() != "UTF8"
                or cliente.upper() != "UTF8"
            ):
                print(
                    "ERROR: El servidor y la conexion "
                    "deben utilizar UTF8."
                )
                return False

            # --------------------------------------------
            # Comprobar que existe el esquema SKILLY.
            # --------------------------------------------

            esquema = "skilly"

            cursor.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name = %s
                """,
                [esquema]
            )

            if cursor.fetchone() is None:
                print(
                    "ERROR: No se encontro "
                    "el esquema skilly."
                )
                return False

            # --------------------------------------------
            # Obtener columnas de texto de todas las
            # tablas base del esquema SKILLY.
            # --------------------------------------------

            cursor.execute(
                """
                SELECT
                    c.table_name,
                    c.column_name
                FROM information_schema.columns AS c
                JOIN information_schema.tables AS t
                    ON t.table_schema = c.table_schema
                   AND t.table_name = c.table_name
                WHERE c.table_schema = %s
                  AND t.table_type = 'BASE TABLE'
                  AND c.data_type IN (
                      'character varying',
                      'character',
                      'text'
                  )
                ORDER BY
                    c.table_name,
                    c.ordinal_position
                """,
                [esquema]
            )

            columnas = cursor.fetchall()

            if not columnas:
                print(
                    "ERROR: No se encontraron "
                    "columnas de texto en SKILLY."
                )
                return False

            valores_afectados = 0
            columnas_revisadas = 0
            columnas_omitidas = 0
            tablas_revisadas = set()

            # --------------------------------------------
            # Analizar los datos ya almacenados.
            # --------------------------------------------

            for tabla, columna in columnas:

                # No mostrar campos de credenciales.
                if any(
                    palabra in columna.lower()
                    for palabra in CAMPOS_PRIVADOS
                ):
                    columnas_omitidas += 1
                    continue

                quote = conexion.ops.quote_name

                consulta = (
                    "SELECT ctid, "
                    + quote(columna)
                    + " FROM "
                    + quote(esquema)
                    + "."
                    + quote(tabla)
                    + " WHERE "
                    + quote(columna)
                    + " IS NOT NULL"
                )

                cursor.execute(consulta)

                columnas_revisadas += 1
                tablas_revisadas.add(tabla)

                # Leer por grupos para controlar memoria.
                while True:
                    filas = cursor.fetchmany(250)

                    if not filas:
                        break

                    for ubicacion, valor in filas:

                        if not isinstance(valor, str):
                            continue

                        if not texto_sospechoso(valor):
                            continue

                        valores_afectados += 1

                        print(
                            "\nSOSPECHOSO:",
                            tabla + "." + columna
                        )
                        print(
                            "FILA:",
                            str(ubicacion)
                        )
                        print(
                            "VALOR:",
                            ascii(valor[:160])
                        )

        print("\nTABLAS REVISADAS:", len(tablas_revisadas))
        print("COLUMNAS REVISADAS:", columnas_revisadas)
        print("COLUMNAS PRIVADAS OMITIDAS:", columnas_omitidas)
        print("VALORES SOSPECHOSOS:", valores_afectados)

        return valores_afectados == 0

    except Exception as error:
        print(
            "\nERROR: No se pudo completar "
            "la auditoria PostgreSQL."
        )
        print("TIPO:", type(error).__name__)
        print("DETALLE:", str(error)[:250])

        return False

    finally:
        if conexion is not None:
            conexion.close()


def main():
    print(
        "\n===== SKILLY - CONTROL PERMANENTE "
        "DE CODIFICACION ====="
    )

    problemas_archivos = revisar_archivos()

    postgres_correcto = revisar_postgresql()

    print("\n===== RESULTADO GENERAL =====")

    print(
        "ARCHIVOS CORRECTOS:",
        problemas_archivos == 0
    )

    print(
        "POSTGRESQL CORRECTO:",
        postgres_correcto
    )

    print("CAMBIOS EN ARCHIVOS: 0")
    print("CAMBIOS EN POSTGRESQL: 0")

    if (
        problemas_archivos == 0
        and postgres_correcto
    ):
        print("\nRESULTADO: CODIFICACION APROBADA")
        return 0

    print("\nRESULTADO: CODIFICACION NO APROBADA")
    return 1


if __name__ == "__main__":
    sys.exit(main())
