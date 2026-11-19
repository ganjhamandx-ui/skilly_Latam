"""Cubre permisos, transiciones y privacidad del reagendamiento bilateral."""

from contextlib import nullcontext
from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from coordinacion.agenda_segura import GestionAgendaPrestacionSeguraAdministracionView

from .models import ESTADOS_ABIERTOS, SolicitudReagendamiento
from .views import (
    AdministracionReagendamientoView,
    EvidenciaReagendamientoAdministracionView,
    OrganizacionReagendamientoView,
    POLITICA_VERSION,
    ProfesionalReagendamientoView,
    alternativas_validadas,
    evidencia_validada,
    politica_aceptada,
    serializar,
)


class RegistroFalso(SimpleNamespace):
    """Simula un modelo con guardado y actualización observables por la prueba."""

    def __init__(self, **kwargs):
        """Inicializa un registro simulado con los atributos indicados."""
        super().__init__(**kwargs)
        self.guardados = []

    def save(self, update_fields=None):
        """Simula la persistencia y registra los campos solicitados para actualización."""
        self.guardados.append(tuple(update_fields or ()))


class RelacionFalsa:
    """Simula una relación Django mínima para eventos y alternativas en memoria."""

    def __init__(self, elementos=None):
        """Inicializa una relación en memoria con elementos de prueba."""
        self.elementos = list(elementos or [])
        self.actualizaciones = []

    def all(self):
        """Devuelve la misma colección simulada sin alterar sus elementos."""
        return self.elementos

    def filter(self, **kwargs):
        """Filtra la colección simulada según las condiciones recibidas."""
        return self

    def exclude(self, **kwargs):
        """Excluye de la colección los registros que cumplen las condiciones."""
        return self

    def select_for_update(self):
        """Simula el bloqueo transaccional conservando la colección actual."""
        return self

    def update(self, **kwargs):
        """Actualiza en memoria los atributos de todos los registros simulados."""
        self.actualizaciones.append(kwargs)
        return len(self.elementos)

    def exists(self):
        """Indica si la colección simulada contiene al menos un elemento."""
        return False

    def __iter__(self):
        """Permite recorrer los registros simulados durante la prueba."""
        return iter(self.elementos)


def bloque_falso(pk=91):
    """Crea un bloque futuro disponible con identidad controlada."""

    return RegistroFalso(
        pk=pk,
        id_profesional_id=7,
        estado="DISPONIBLE",
        fecha=timezone.localdate() + timedelta(days=20),
        hora_inicio=time(10, 0),
        hora_fin=time(11, 0),
    )


def prestacion_falsa():
    """Crea una prestación contratada aislada de la base de datos."""

    return RegistroFalso(
        pk=3,
        estado="CONTRATADA",
        id_solicitud_id=13,
        id_profesional_id=7,
    )


def reserva_falsa():
    """Crea una reserva asociada al bloque original simulado."""

    return SimpleNamespace(id_disponibilidad_id=44, id_disponibilidad=bloque_falso(44))


def solicitud_falsa(**cambios):
    """Construye un expediente simulado y permite sobrescribir su estado."""

    valores = {
        "pk": 5,
        "prestacion_id": 3,
        "solicitud_id": 13,
        "profesional_id": 7,
        "bloque_original_id": 44,
        "bloque_propuesto_id": None,
        "iniciador": "ORGANIZACION",
        "motivo_organizacion": "La organización requiere coordinar una nueva fecha.",
        "motivo_profesional": "",
        "estado": "PENDIENTE_ADMIN",
        "requiere_confirmacion_organizacion": False,
        "organizacion_autorizo_cambio": True,
        "profesional_confirmo_bloque": False,
        "contrapropuesta_profesional_usada": False,
        "politica_version": POLITICA_VERSION,
        "politica_aceptada_en": timezone.now(),
        "evidencia_nombre": None,
        "evidencia_sha256": None,
        "fecha_creacion": timezone.now(),
        "fecha_actualizacion": timezone.now(),
        "alternativas": RelacionFalsa(),
        "eventos": RelacionFalsa(),
    }
    valores.update(cambios)
    return RegistroFalso(**valores)


def gestor_objetos(objeto):
    """Configura un manager simulado que devuelve el objeto indicado."""

    gestor = MagicMock()
    gestor.filter.return_value.first.return_value = objeto
    gestor.select_for_update.return_value.get.return_value = objeto
    gestor.select_for_update.return_value.filter.return_value.first.return_value = objeto
    return gestor


class ReglasEntradaTests(SimpleTestCase):
    """Cubre política, evidencia y alternativas antes de tocar persistencia."""

    def test_politica_exige_consentimiento_y_version_exacta(self):
        """Verifica el escenario: política exige consentimiento y version exacta."""
        self.assertTrue(politica_aceptada({
            "acepta_politica": True,
            "politica_version": POLITICA_VERSION,
        }))
        self.assertTrue(politica_aceptada({
            "acepta_politica": "sí",
            "politica_version": POLITICA_VERSION,
        }))
        self.assertFalse(politica_aceptada({
            "acepta_politica": False,
            "politica_version": POLITICA_VERSION,
        }))
        self.assertFalse(politica_aceptada({
            "acepta_politica": True,
            "politica_version": "anterior",
        }))

    def test_una_contrapropuesta_admite_varios_bloques(self):
        """Verifica el escenario: una contrapropuesta admite varios bloques."""
        fecha = (timezone.localdate() + timedelta(days=30)).isoformat()
        existentes, nuevos = alternativas_validadas({
            "alternativas_existentes": [10, 11],
            "alternativas_nuevas": [
                {"fecha": fecha, "hora_inicio": "09:00", "hora_fin": "10:00"},
                {"fecha": fecha, "hora_inicio": "11:00", "hora_fin": "12:00"},
            ],
        })
        self.assertEqual(existentes, [10, 11])
        self.assertEqual(len(nuevos), 2)

        with self.assertRaisesMessage(Exception, "repetidas"):
            alternativas_validadas({
                "alternativas_existentes": [10, 10],
                "alternativas_nuevas": [],
            })
        with self.assertRaisesMessage(Exception, "entre 1 y 10"):
            alternativas_validadas({
                "alternativas_existentes": [],
                "alternativas_nuevas": [],
            })

    def test_evidencia_valida_firma_tamano_y_hash_sin_escribir_archivos(self):
        """Verifica el escenario: evidencia válida firma tamaño y hash sin escribir archivos."""
        contenido = b"%PDF-1.7\njustificacion privada"
        archivo = SimpleUploadedFile(
            "respaldo.pdf",
            contenido,
            content_type="application/pdf",
        )
        resultado = evidencia_validada(archivo)
        self.assertEqual(resultado["evidencia_contenido"], contenido)
        self.assertEqual(len(resultado["evidencia_sha256"]), 64)
        self.assertEqual(resultado["evidencia_mime"], "application/pdf")

        falso = SimpleUploadedFile(
            "respaldo.pdf",
            b"no es un pdf",
            content_type="application/pdf",
        )
        with self.assertRaisesMessage(Exception, "contenido no coincide"):
            evidencia_validada(falso)

    def test_espera_controlada_sigue_sujeta_a_unicidad_abierta(self):
        """Verifica el escenario: espera controlada sigue sujeta a unicidad abierta."""
        self.assertIn("ESPERANDO_SELECCION", ESTADOS_ABIERTOS)
        restriccion = next(
            item for item in SolicitudReagendamiento._meta.constraints
            if item.name == "skilly_reag_una_abierta_prestacion"
        )
        self.assertIn("ESPERANDO_SELECCION", restriccion.condition.children[0][1])


class ProteccionesHttpTests(SimpleTestCase):
    """Comprueba CSRF, permisos y privacidad en los endpoints del flujo."""

    def setUp(self):
        """Prepara dependencias y datos aislados antes de cada escenario."""
        self.factory = APIRequestFactory(enforce_csrf_checks=True)

    def test_todos_los_post_rechazan_ausencia_de_csrf(self):
        """Verifica el escenario: todos los post rechazan ausencia de CSRF."""
        casos = [
            (OrganizacionReagendamientoView.as_view(), {"referencia": "privada"}),
            (AdministracionReagendamientoView.as_view(), {}),
            (ProfesionalReagendamientoView.as_view(), {}),
        ]
        for vista, kwargs in casos:
            with self.subTest(vista=vista):
                solicitud = self.factory.post("/api/reagendamientos/", {}, format="json")
                respuesta = vista(solicitud, **kwargs)
                self.assertEqual(respuesta.status_code, 403)

    def test_bandejas_y_evidencia_autenticadas_rechazan_anonimos(self):
        """Verifica el escenario: bandejas y evidencia autenticadas rechazan anónimos."""
        casos = [
            (AdministracionReagendamientoView.as_view(), {}),
            (ProfesionalReagendamientoView.as_view(), {}),
            (EvidenciaReagendamientoAdministracionView.as_view(), {"pk": 5}),
        ]
        for vista, kwargs in casos:
            with self.subTest(vista=vista):
                solicitud = self.factory.get("/api/reagendamientos/")
                solicitud.session = {}
                respuesta = vista(solicitud, **kwargs)
                self.assertEqual(respuesta.status_code, 403)

        self.assertEqual(
            AdministracionReagendamientoView.permission_classes[0].__name__,
            "EsAdministracionSkilly",
        )
        self.assertEqual(
            EvidenciaReagendamientoAdministracionView.permission_classes[0].__name__,
            "EsAdministracionSkilly",
        )
        self.assertEqual(
            ProfesionalReagendamientoView.permission_classes[0].__name__,
            "EsProfesional",
        )

    @patch("reagendamientos.views.PrestacionServicio.objects.filter")
    @patch("reagendamientos.views.Disponibilidad.objects.filter")
    def test_organizacion_no_recibe_metadatos_de_evidencia(self, disponibilidad, prestacion):
        """Verifica el escenario: organización no recibe metadatos de evidencia."""
        prestacion.return_value.first.return_value = None
        disponibilidad.return_value.first.return_value = None
        obj = solicitud_falsa(
            evidencia_nombre="privado.pdf",
            evidencia_sha256="a" * 64,
        )
        datos = serializar(obj, "ORGANIZACION", mostrar_eventos=False)
        self.assertNotIn("evidencia_nombre", datos)
        self.assertNotIn("evidencia_disponible", datos)
        self.assertNotIn("evidencia_url", datos)

    @patch("reagendamientos.views.transaction.atomic", side_effect=lambda: nullcontext())
    @patch("reagendamientos.views._verificar_responsable", return_value=None)
    @patch("reagendamientos.views.SolicitudReagendamiento.objects")
    def test_descarga_privada_usa_transaccion_y_cabeceras_seguras(
        self, objetos, verificar, atomicidad
    ):
        """Verifica el escenario: descarga privada usa transacción y cabeceras seguras."""
        objetos.defer.return_value.filter.return_value.first.return_value = solicitud_falsa(
            evidencia_nombre="respaldo.pdf",
            evidencia_sha256="c" * 64,
        )
        objetos.filter.return_value.values_list.return_value.first.return_value = b"%PDF-1.7\nprivado"
        respuesta = EvidenciaReagendamientoAdministracionView().get(
            SimpleNamespace(user=SimpleNamespace(pk=9)),
            5,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.content, b"%PDF-1.7\nprivado")
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        atomicidad.assert_called_once()
        verificar.assert_called_once()


class FlujoBilateralTests(SimpleTestCase):
    """Ejercita transiciones de ambos iniciadores con colaboradores simulados."""

    def contexto_comun(self, obj, prestacion=None, bloque=None):
        """Construye parches y objetos compartidos por los escenarios bilaterales."""
        prestacion = prestacion or prestacion_falsa()
        bloque = bloque or bloque_falso()
        return (
            patch("reagendamientos.views.transaction.atomic", side_effect=lambda: nullcontext()),
            patch("reagendamientos.views.SolicitudReagendamiento.objects", gestor_objetos(obj)),
            patch("reagendamientos.views.PrestacionServicio.objects", gestor_objetos(prestacion)),
            patch("reagendamientos.views.reserva_vigente", return_value=reserva_falsa()),
            patch("reagendamientos.views.inicio_vencido", return_value=False),
            patch("reagendamientos.views.Disponibilidad.objects", gestor_objetos(bloque)),
            patch("reagendamientos.views.disponible", return_value=True),
            patch("reagendamientos.views.evento"),
            patch("reagendamientos.views.serializar", side_effect=lambda caso, *args, **kwargs: {"estado": caso.estado}),
        )

    def test_organizacion_registra_politica_antes_de_abrir_caso_a(self):
        """Verifica el escenario: organización registra política antes de abrir caso a."""
        prestacion = prestacion_falsa()
        creado = solicitud_falsa()
        gestor_prestacion = gestor_objetos(prestacion)
        gestor_solicitud = MagicMock()
        gestor_solicitud.objects = gestor_solicitud
        gestor_solicitud.create.return_value = creado
        vista = OrganizacionReagendamientoView()
        solicitud = SimpleNamespace(data={
            "accion": "SOLICITAR",
            "motivo": "Necesitamos coordinar una nueva fecha para la reunión inicial.",
            "acepta_politica": True,
            "politica_version": POLITICA_VERSION,
        })

        with patch.object(vista, "_prestacion", return_value=prestacion), \
             patch("reagendamientos.views.transaction.atomic", side_effect=lambda: nullcontext()), \
             patch("reagendamientos.views.PrestacionServicio.objects", gestor_prestacion), \
             patch("reagendamientos.views.SolicitudReagendamiento.objects", gestor_solicitud), \
             patch("reagendamientos.views.acceso_solicitud", return_value=None), \
             patch("reagendamientos.views.reserva_vigente", return_value=reserva_falsa()), \
             patch("reagendamientos.views.evento"), \
             patch("reagendamientos.views.serializar", return_value={"estado": "PENDIENTE_ADMIN"}):
            respuesta = vista.post(solicitud, "privada")

        self.assertEqual(respuesta.status_code, 201)
        campos = gestor_solicitud.create.call_args.kwargs
        self.assertEqual(campos["iniciador"], "ORGANIZACION")
        self.assertTrue(campos["organizacion_autorizo_cambio"])
        self.assertEqual(campos["politica_version"], POLITICA_VERSION)
        self.assertIsNotNone(campos["politica_aceptada_en"])

    def test_caso_a_propuesta_y_aceptacion_profesional_sin_segunda_aceptacion(self):
        """Verifica el escenario: caso a propuesta y aceptación profesional sin segunda aceptación."""
        obj = solicitud_falsa()
        prestacion = prestacion_falsa()
        bloque = bloque_falso()
        gestor_alternativa = MagicMock()
        parches = self.contexto_comun(obj, prestacion, bloque)
        with parches[0], parches[1], parches[2], parches[3], parches[4], parches[5], \
             parches[6], parches[7], parches[8], \
             patch("reagendamientos.views._verificar_responsable", return_value=None), \
             patch("reagendamientos.views.AlternativaReagendamiento.objects", gestor_alternativa):
            respuesta_admin = AdministracionReagendamientoView().post(
                SimpleNamespace(
                    user=SimpleNamespace(pk=9),
                    data={"id": obj.pk, "accion": "PROPONER", "id_disponibilidad": bloque.pk},
                )
            )
            self.assertEqual(respuesta_admin.status_code, 200)
            self.assertEqual(obj.estado, "PENDIENTE_PROFESIONAL")
            self.assertEqual(obj.bloque_propuesto_id, bloque.pk)

            vista_profesional = ProfesionalReagendamientoView()
            with patch.object(vista_profesional, "_profesional", return_value=SimpleNamespace(pk=7)):
                respuesta_profesional = vista_profesional.post(
                    SimpleNamespace(data={"id": obj.pk, "accion": "ACEPTAR"})
                )

        self.assertEqual(respuesta_profesional.status_code, 200)
        self.assertEqual(obj.estado, "LISTO_CONFIRMAR")
        self.assertTrue(obj.profesional_confirmo_bloque)
        self.assertTrue(obj.organizacion_autorizo_cambio)

    def test_caso_a_rechazo_unico_admite_varios_bloques(self):
        """Verifica el escenario: caso a rechazo único admite varios bloques."""
        obj = solicitud_falsa(
            estado="PENDIENTE_PROFESIONAL",
            bloque_propuesto_id=90,
        )
        parches = self.contexto_comun(obj)
        vista = ProfesionalReagendamientoView()
        datos = {
            "id": obj.pk,
            "accion": "RECHAZAR_CON_ALTERNATIVAS",
            "motivo": "Ese horario se superpone con una obligación impostergable.",
            "alternativas_existentes": [91, 92],
            "alternativas_nuevas": [],
        }
        with parches[0], parches[1], parches[2], parches[3], parches[4], parches[5], \
             parches[6], parches[7], parches[8], \
             patch.object(vista, "_profesional", return_value=SimpleNamespace(pk=7)), \
             patch("reagendamientos.views.registrar_alternativas", return_value=[bloque_falso(91), bloque_falso(92)]) as registrar:
            respuesta = vista.post(SimpleNamespace(data=datos))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(obj.estado, "PENDIENTE_ORGANIZACION")
        self.assertTrue(obj.contrapropuesta_profesional_usada)
        self.assertTrue(obj.profesional_confirmo_bloque)
        self.assertEqual(len(registrar.return_value), 2)

        obj.estado = "PENDIENTE_PROFESIONAL"
        parches = self.contexto_comun(obj)
        with parches[0], parches[1], parches[2], parches[3], parches[4], parches[5], \
             parches[6], parches[7], parches[8], \
             patch.object(vista, "_profesional", return_value=SimpleNamespace(pk=7)), \
             patch("reagendamientos.views.registrar_alternativas") as segundo_registro:
            repetida = vista.post(SimpleNamespace(data=datos))
        self.assertEqual(repetida.status_code, 409)
        segundo_registro.assert_not_called()

    def test_espera_y_seleccion_posterior_conservan_el_mismo_expediente(self):
        """Verifica el escenario: espera y seleccion posterior conservan el mismo expediente."""
        obj = solicitud_falsa(
            estado="PENDIENTE_ORGANIZACION",
            profesional_confirmo_bloque=True,
            organizacion_autorizo_cambio=False,
        )
        prestacion = prestacion_falsa()
        bloque = bloque_falso(101)
        gestor_alternativas = MagicMock()
        gestor_alternativas.select_for_update.return_value.filter.return_value.first.return_value = None
        alternativa = RegistroFalso(pk=15, estado="HABILITADA")
        gestor_alternativas.update_or_create.return_value = (alternativa, True)
        parches = self.contexto_comun(obj, prestacion, bloque)
        vista = OrganizacionReagendamientoView()
        with parches[0], parches[1], parches[2], parches[3], parches[4], parches[5], \
             parches[6], parches[7], parches[8], \
             patch.object(vista, "_prestacion", return_value=prestacion), \
             patch("reagendamientos.views.AlternativaReagendamiento.objects", gestor_alternativas):
            espera = vista.post(
                SimpleNamespace(data={"id": obj.pk, "accion": "ESPERAR_SELECCION"}),
                "privada",
            )
            self.assertEqual(espera.status_code, 200)
            self.assertEqual(obj.estado, "ESPERANDO_SELECCION")

            seleccion = vista.post(
                SimpleNamespace(data={
                    "id": obj.pk,
                    "accion": "SELECCIONAR",
                    "id_disponibilidad": bloque.pk,
                }),
                "privada",
            )

        self.assertEqual(seleccion.status_code, 200)
        self.assertEqual(obj.estado, "LISTO_CONFIRMAR")
        self.assertEqual(obj.bloque_propuesto_id, bloque.pk)
        self.assertTrue(obj.organizacion_autorizo_cambio)

    def test_caso_b_exige_evidencia_y_envia_varios_bloques_a_validacion(self):
        """Verifica el escenario: caso b exige evidencia y envia varios bloques a validacion."""
        obj = solicitud_falsa(iniciador="PROFESIONAL", motivo_organizacion="")
        prestacion = prestacion_falsa()
        gestor_solicitud = MagicMock()
        gestor_solicitud.create.return_value = obj
        gestor_prestacion = gestor_objetos(prestacion)
        vista = ProfesionalReagendamientoView()
        fecha = (timezone.localdate() + timedelta(days=25)).isoformat()
        solicitud = SimpleNamespace(
            data={
                "accion": "SOLICITAR_PROFESIONAL",
                "id_prestacion": prestacion.pk,
                "motivo": "Un impedimento documentado requiere cambiar la primera reunión.",
                "acepta_politica": True,
                "politica_version": POLITICA_VERSION,
                "alternativas_existentes": [91],
                "alternativas_nuevas": [
                    {"fecha": fecha, "hora_inicio": "15:00", "hora_fin": "16:00"},
                ],
            },
            FILES={"evidencia": object()},
        )
        evidencia = {
            "evidencia_nombre": "privado.pdf",
            "evidencia_mime": "application/pdf",
            "evidencia_sha256": "b" * 64,
            "evidencia_contenido": b"%PDF-1.7\nprivado",
        }
        with patch.object(vista, "_profesional", return_value=SimpleNamespace(pk=7)), \
             patch("reagendamientos.views.transaction.atomic", side_effect=lambda: nullcontext()), \
             patch("reagendamientos.views.PrestacionServicio.objects", gestor_prestacion), \
             patch("reagendamientos.views.SolicitudReagendamiento.objects", gestor_solicitud), \
             patch("reagendamientos.views.acceso_solicitud", return_value=None), \
             patch("reagendamientos.views.reserva_vigente", return_value=reserva_falsa()), \
             patch("reagendamientos.views.evidencia_validada", return_value=evidencia), \
             patch("reagendamientos.views.registrar_alternativas", return_value=[bloque_falso(91), bloque_falso(92)]) as registrar, \
             patch("reagendamientos.views.evento"), \
             patch("reagendamientos.views.serializar", return_value={"estado": "PENDIENTE_ADMIN"}):
            respuesta = vista.post(solicitud)

        self.assertEqual(respuesta.status_code, 201)
        campos = gestor_solicitud.create.call_args.kwargs
        self.assertEqual(campos["iniciador"], "PROFESIONAL")
        self.assertTrue(campos["profesional_confirmo_bloque"])
        self.assertFalse(campos["organizacion_autorizo_cambio"])
        self.assertEqual(campos["evidencia_sha256"], "b" * 64)
        self.assertEqual(registrar.call_args.args[-1], "PENDIENTE_VALIDACION")

    def test_caso_b_validacion_habilita_solo_bloques_disponibles(self):
        """Verifica el escenario: caso b validacion habilita solo bloques disponibles."""
        alternativa_valida = RegistroFalso(bloque_id=91, estado="PENDIENTE_VALIDACION")
        alternativa_invalida = RegistroFalso(bloque_id=92, estado="PENDIENTE_VALIDACION")
        obj = solicitud_falsa(
            iniciador="PROFESIONAL",
            estado="PENDIENTE_ADMIN",
            alternativas=RelacionFalsa([alternativa_valida, alternativa_invalida]),
        )
        parches = self.contexto_comun(obj)
        gestor_disponibilidad = MagicMock()
        gestor_disponibilidad.select_for_update.return_value.filter.return_value.first.side_effect = [
            bloque_falso(91),
            bloque_falso(92),
        ]
        with parches[0], parches[1], parches[2], parches[3], parches[4], \
             patch("reagendamientos.views.Disponibilidad.objects", gestor_disponibilidad), \
             patch("reagendamientos.views.disponible", side_effect=[True, False]), \
             parches[7], parches[8], \
             patch("reagendamientos.views._verificar_responsable", return_value=None):
            respuesta = AdministracionReagendamientoView().post(
                SimpleNamespace(user=SimpleNamespace(pk=9), data={
                    "id": obj.pk,
                    "accion": "VALIDAR_ALTERNATIVAS",
                })
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(alternativa_valida.estado, "HABILITADA")
        self.assertEqual(alternativa_invalida.estado, "INVALIDA")
        self.assertEqual(obj.estado, "PENDIENTE_ORGANIZACION")
        self.assertTrue(obj.profesional_confirmo_bloque)
        self.assertFalse(obj.organizacion_autorizo_cambio)

    def test_confirmacion_es_unica_y_pasa_marcador_a_agenda_segura(self):
        """Verifica el escenario: confirmacion es única y pasa marcador a agenda segura."""
        bloque = bloque_falso(91)
        obj = solicitud_falsa(
            estado="LISTO_CONFIRMAR",
            bloque_propuesto_id=bloque.pk,
            organizacion_autorizo_cambio=True,
            profesional_confirmo_bloque=True,
        )
        parches = self.contexto_comun(obj, bloque=bloque)
        llamadas = []

        def agenda(request, prestacion_id):
            """Simula la aplicación final del bloque en la agenda segura."""
            llamadas.append((request, prestacion_id))
            return Response({"mensaje": "agenda actualizada"}, status=200)

        with parches[0], parches[1], parches[2], parches[3], parches[4], parches[5], \
             parches[6], parches[7], parches[8], \
             patch("reagendamientos.views._verificar_responsable", return_value=None), \
             patch.object(GestionAgendaPrestacionSeguraAdministracionView, "post", side_effect=agenda):
            vista = AdministracionReagendamientoView()
            request = SimpleNamespace(
                user=SimpleNamespace(pk=9),
                data={"id": obj.pk, "accion": "CONFIRMAR"},
            )
            primera = vista.post(request)
            segunda = vista.post(request)

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(obj.estado, "CONFIRMADO")
        self.assertEqual(len(llamadas), 1)
        self.assertEqual(llamadas[0][0]._solicitud_reagendamiento_id, obj.pk)

    @patch("coordinacion.agenda_segura.transaction.atomic", side_effect=lambda: nullcontext())
    @patch("coordinacion.agenda_segura.get_object_or_404")
    def test_ruta_directa_no_salta_expediente_formal(self, obtener, atomicidad):
        """Verifica el escenario: ruta directa no salta expediente formal."""
        prestacion = prestacion_falsa()
        obtener.return_value = prestacion
        formal = solicitud_falsa(estado="PENDIENTE_ORGANIZACION")
        gestor_formal = MagicMock()
        gestor_formal.select_for_update.return_value.filter.return_value.first.return_value = formal

        with patch("reagendamientos.models.SolicitudReagendamiento.objects", gestor_formal):
            respuesta = GestionAgendaPrestacionSeguraAdministracionView.post.__wrapped__(
                GestionAgendaPrestacionSeguraAdministracionView(),
                SimpleNamespace(
                    data={"accion": "REAGENDAR", "motivo": "intento directo"},
                    user=SimpleNamespace(pk=9),
                ),
                prestacion.pk,
            )

        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("solicitud formal", respuesta.data["mensaje"])
