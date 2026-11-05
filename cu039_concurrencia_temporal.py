import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local

from django.conf import settings
from django.db import close_old_connections, connection, transaction
from django.db.backends.signals import connection_created
from django.test import Client, override_settings
from django.urls import reverse

from acceso.models import Usuario
from coordinacion.models import PrestacionServicio

ESQUEMA = "skilly_cu039_pruebas"
PRESTACION = 900401
SOLICITUD = 900301
DESTINO = 900502
ADMINISTRADORES = (900101, 900102)

# La marca de este hilo solo se activa dentro de los dos trabajadores.
# Django puede reabrir conexiones al procesar solicitudes del Client.
# El receptor aplica el esquema temporal a CADA conexion nueva del hilo.
_contexto = local()


def asegurar_esquema_al_conectar(sender, connection, **kwargs):
    if not getattr(_contexto, "cu039_aislado", False):
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        if cursor.fetchone()[0] != "skilly":
            raise RuntimeError("CU039: conexion a una base de datos inesperada")

        cursor.execute(f'SET SESSION search_path TO "{ESQUEMA}"')
        cursor.execute("SET SESSION lock_timeout TO '12000ms'")
        cursor.execute("SELECT current_schema()")
        if cursor.fetchone()[0] != ESQUEMA:
            raise RuntimeError("CU039: esquema de pruebas no disponible")


connection_created.connect(
    asegurar_esquema_al_conectar,
    weak=False,
    dispatch_uid="cu039_asegurar_esquema_en_cada_conexion",
)


def verificar_esquema_trabajador():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_schema()")
        return cursor.fetchone() == ("skilly", ESQUEMA)


def consultar(sql, parametros=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, parametros or [])
        return cursor.fetchall()


def trabajador(id_admin, barrera, ruta):
    _contexto.cu039_aislado = True
    close_old_connections()
    connection.close()  # Fuerza una conexion nueva con el esquema aislado.
    try:
        assert verificar_esquema_trabajador(), "Esquema incorrecto al iniciar"

        usuario = Usuario.objects.get(pk=id_admin)
        assert usuario.rol == "ADMIN_SKILLY" and usuario.estado == "ACTIVO"
        assert usuario.correo.endswith("@example.invalid")

        cliente = Client(enforce_csrf_checks=True)
        assert cliente.get(reverse("csrf_token")).status_code == 200
        assert verificar_esquema_trabajador(), "Esquema incorrecto tras GET"
        token = cliente.cookies[settings.CSRF_COOKIE_NAME].value

        sesion = cliente.session
        sesion["id_usuario"] = usuario.pk
        sesion["rol"] = usuario.rol
        sesion.save()
        cliente.cookies[settings.SESSION_COOKIE_NAME] = sesion.session_key
        assert verificar_esquema_trabajador(), "Esquema incorrecto tras sesion"

        assert consultar(
            'SELECT COUNT(*) FROM "skilly_cu039_pruebas"."django_session"'
        )[0][0] >= 1
        barrera.wait(timeout=20)

        inicio = time.perf_counter()
        respuesta = cliente.post(
            ruta,
            data=json.dumps({
                "accion": "REAGENDAR",
                "motivo": f"Prueba concurrente CU039 admin {id_admin}",
                "id_disponibilidad_nueva": DESTINO,
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert verificar_esquema_trabajador(), "Esquema incorrecto tras POST"
        return {
            "admin": id_admin,
            "codigo": respuesta.status_code,
            "duracion": round(time.perf_counter() - inicio, 3),
            "respuesta": respuesta.content.decode(errors="replace")[:350],
            "sesion": sesion.session_key,
        }
    finally:
        # Evita que un hilo reutilizado conserve la ruta temporal.
        connection.close()
        _contexto.cu039_aislado = False


print("\nCU039 - CONCURRENCIA REAL EN ESQUEMA AISLADO")
base, esquema_actual, search_path = consultar(
    "SELECT current_database(), current_schema(), current_setting('search_path')"
)[0]
assert (base, esquema_actual) == ("skilly", "skilly")
assert search_path == "skilly,public"

historico_prestacion = consultar(
    'SELECT estado FROM "skilly"."prestacion_servicio" WHERE id_prestacion=1'
)
historico_pago = consultar(
    'SELECT estado_pago FROM "skilly"."pago" WHERE id_pago=1'
)

assert consultar(
    'SELECT estado FROM "skilly_cu039_pruebas"."prestacion_servicio" '
    'WHERE id_prestacion=%s', [PRESTACION]
) == [("CONTRATADA",)]
assert consultar(
    'SELECT estado_pago FROM "skilly_cu039_pruebas"."pago" WHERE id_pago=900801'
) == [("RETENIDO",)]
assert consultar(
    'SELECT id_disponibilidad, estado FROM "skilly_cu039_pruebas".'
    '"reserva_disponibilidad" WHERE id_solicitud=%s AND estado=%s',
    [SOLICITUD, "ACTIVA"]
) == [(900501, "ACTIVA")]
assert consultar(
    'SELECT id_disponibilidad, estado FROM "skilly_cu039_pruebas".'
    '"disponibilidad" WHERE id_disponibilidad IN (900501, 900502, 900503) '
    'ORDER BY id_disponibilidad'
) == [(900501, "RESERVADA"), (900502, "DISPONIBLE"), (900503, "DISPONIBLE")]
assert consultar(
    'SELECT COUNT(*) FROM "skilly_cu039_pruebas"."coordinacion_solicitud" '
    'WHERE id_solicitud=%s', [SOLICITUD]
)[0][0] == 0

ruta = reverse(
    "gestion_agenda_prestacion_administracion",
    kwargs={"id_prestacion": PRESTACION},
)
print("RUTA:", ruta)
print("DOS ADMINISTRADORES:", ADMINISTRADORES)
print("AMBOS SOLICITAN EL BLOQUE:", DESTINO)

hosts = list(settings.ALLOWED_HOSTS)
if "testserver" not in hosts:
    hosts.append("testserver")

barrera = Barrier(3)
with override_settings(ALLOWED_HOSTS=hosts):
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        # El hilo principal retiene el bloqueo mientras ambos clientes se preparan.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL search_path TO "skilly_cu039_pruebas"')
            prestacion_bloqueada = PrestacionServicio.objects.select_for_update().get(
                pk=PRESTACION
            )
            assert prestacion_bloqueada.estado == "CONTRATADA"

            futuros = [
                ejecutor.submit(trabajador, id_admin, barrera, ruta)
                for id_admin in ADMINISTRADORES
            ]
            barrera.wait(timeout=20)
            time.sleep(0.8)
            print("AMBAS SOLICITUDES INICIADAS; SE LIBERA EL BLOQUEO")

        resultados = [futuro.result(timeout=25) for futuro in futuros]

print("\nRESPUESTAS HTTP")
for resultado in resultados:
    print("ADMIN:", resultado["admin"])
    print("HTTP:", resultado["codigo"])
    print("DURACION:", resultado["duracion"], "segundos")
    print("RESPUESTA:", resultado["respuesta"])

# Las sesiones creadas por Django deben haberse escrito SOLO en pruebas.
for resultado in resultados:
    clave = resultado["sesion"]
    assert consultar(
        'SELECT COUNT(*) FROM "skilly_cu039_pruebas"."django_session" '
        'WHERE session_key=%s', [clave]
    ) == [(1,)], "Falta sesion dentro del esquema temporal"
    assert consultar(
        'SELECT COUNT(*) FROM "skilly"."django_session" '
        'WHERE session_key=%s', [clave]
    ) == [(0,)], "Una sesion de prueba alcanzo el esquema principal"
print("SESIONES AISLADAS: 2/2 OK")

codigos = sorted(resultado["codigo"] for resultado in resultados)
assert codigos in ([200, 400], [200, 409]), (
    f"Se esperaba un éxito y un conflicto: {codigos}"
)

activas = consultar(
    'SELECT id_disponibilidad FROM "skilly_cu039_pruebas".'
    '"reserva_disponibilidad" WHERE id_solicitud=%s AND estado=%s',
    [SOLICITUD, "ACTIVA"]
)
assert activas == [(DESTINO,)], f"Reservas activas incorrectas: {activas}"

bloques = consultar(
    'SELECT id_disponibilidad, estado FROM "skilly_cu039_pruebas".'
    '"disponibilidad" WHERE id_disponibilidad IN (900501, 900502, 900503) '
    'ORDER BY id_disponibilidad'
)
assert bloques == [(900501, "DISPONIBLE"), (900502, "RESERVADA"), (900503, "DISPONIBLE")]

assert consultar(
    'SELECT estado FROM "skilly_cu039_pruebas"."prestacion_servicio" '
    'WHERE id_prestacion=%s', [PRESTACION]
) == [("CONTRATADA",)]
assert consultar(
    'SELECT estado_pago FROM "skilly_cu039_pruebas"."pago" WHERE id_pago=900801'
) == [("RETENIDO",)]
assert consultar(
    'SELECT COUNT(*) FROM "skilly_cu039_pruebas"."reunion_solicitud" '
    'WHERE id_solicitud=%s AND estado=%s', [SOLICITUD, "AGENDADA"]
)[0][0] == 1
assert consultar(
    'SELECT COUNT(*) FROM "skilly_cu039_pruebas"."coordinacion_solicitud" '
    'WHERE id_solicitud=%s', [SOLICITUD]
)[0][0] == 1

assert consultar(
    'SELECT estado FROM "skilly"."prestacion_servicio" WHERE id_prestacion=1'
) == historico_prestacion
assert consultar(
    'SELECT estado_pago FROM "skilly"."pago" WHERE id_pago=1'
) == historico_pago
assert consultar("SELECT current_schema()")[0][0] == "skilly"

print("\nRESULTADOS")
print("SOLICITUDES CONCURRENTES: 2")
print("REAGENDAMIENTOS APROBADOS: 1")
print("RECHAZOS POR CONFLICTO: 1")
print("RESERVAS ACTIVAS: 1")
print("REUNION AGENDADA: 1")
print("PAGO: RETENIDO")
print("ESQUEMA PRINCIPAL: SIN CAMBIOS")
print("CU039 CONCURRENCIA REAL: OK")
