from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


def conservar_flujo_historico(apps, schema_editor):
    """Adapta expedientes previos sin inventar aceptaciones de política."""
    Solicitud = apps.get_model("reagendamientos", "SolicitudReagendamiento")
    Alternativa = apps.get_model("reagendamientos", "AlternativaReagendamiento")
    Evento = apps.get_model("reagendamientos", "EventoReagendamiento")

    Solicitud.objects.filter(
        estado__in=[
            "PENDIENTE_ADMIN",
            "PENDIENTE_PROFESIONAL",
            "ESPERANDO_NUEVO_BLOQUE",
        ]
    ).update(organizacion_autorizo_cambio=True)

    for solicitud in Solicitud.objects.all().iterator():
        estado_alternativa = None
        if solicitud.estado == "PENDIENTE_PROFESIONAL":
            estado_alternativa = "PROPUESTA_ADMIN"
        elif solicitud.estado == "PENDIENTE_ORGANIZACION":
            solicitud.profesional_confirmo_bloque = True
            acepto_propuesta = Evento.objects.filter(
                reagendamiento_id=solicitud.pk,
                accion="ACEPTAR",
            ).exists()
            if acepto_propuesta:
                # Bajo la regla bilateral definitiva, la organización que inició
                # el trámite no debe volver a aceptar el bloque ya confirmado.
                solicitud.organizacion_autorizo_cambio = True
                solicitud.estado = "LISTO_CONFIRMAR"
                estado_alternativa = "SELECCIONADA"
            else:
                estado_alternativa = "HABILITADA"
            solicitud.save(update_fields=[
                "profesional_confirmo_bloque",
                "organizacion_autorizo_cambio",
                "estado",
            ])
        elif solicitud.estado in {"LISTO_CONFIRMAR", "CONFIRMADO"}:
            solicitud.organizacion_autorizo_cambio = True
            solicitud.profesional_confirmo_bloque = True
            solicitud.save(update_fields=[
                "organizacion_autorizo_cambio",
                "profesional_confirmo_bloque",
            ])
            estado_alternativa = "SELECCIONADA"

        if solicitud.bloque_propuesto_id and estado_alternativa:
            Alternativa.objects.get_or_create(
                reagendamiento_id=solicitud.pk,
                bloque_id=solicitud.bloque_propuesto_id,
                defaults={
                    "origen": "FLUJO_HISTORICO",
                    "estado": estado_alternativa,
                },
            )


def no_revertir_flujo_historico(apps, schema_editor):
    # La reversión elimina la tabla y los campos nuevos; no debe reescribir los
    # estados históricos antes de que Django retire ese esquema.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reagendamientos", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="solicitudreagendamiento",
            name="skilly_reag_una_abierta_prestacion",
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="iniciador",
            field=models.CharField(db_index=True, default="ORGANIZACION", max_length=20),
        ),
        migrations.AlterField(
            model_name="solicitudreagendamiento",
            name="motivo_organizacion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="organizacion_autorizo_cambio",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="profesional_confirmo_bloque",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="contrapropuesta_profesional_usada",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="politica_version",
            field=models.CharField(default="LEGACY_NO_REGISTRADA", max_length=40),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="politica_actor",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="politica_aceptada_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="evidencia_nombre",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="evidencia_mime",
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="evidencia_sha256",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="solicitudreagendamiento",
            name="evidencia_contenido",
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="AlternativaReagendamiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bloque_id", models.BigIntegerField()),
                ("origen", models.CharField(max_length=30)),
                ("estado", models.CharField(db_index=True, default="HABILITADA", max_length=25)),
                ("fecha", models.DateField(blank=True, null=True)),
                ("hora_inicio", models.TimeField(blank=True, null=True)),
                ("hora_fin", models.TimeField(blank=True, null=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("reagendamiento", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alternativas", to="reagendamientos.solicitudreagendamiento")),
            ],
            options={
                "db_table": "alternativa_reagendamiento",
                "ordering": ["fecha_creacion", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="alternativareagendamiento",
            constraint=models.UniqueConstraint(fields=("reagendamiento", "bloque_id"), name="skilly_reag_alternativa_unica"),
        ),
        migrations.RunPython(
            conservar_flujo_historico,
            no_revertir_flujo_historico,
        ),
        migrations.AddConstraint(
            model_name="solicitudreagendamiento",
            constraint=models.UniqueConstraint(
                fields=("prestacion_id",),
                condition=Q(estado__in=[
                    "PENDIENTE_ADMIN",
                    "PENDIENTE_PROFESIONAL",
                    "ESPERANDO_NUEVO_BLOQUE",
                    "PENDIENTE_ORGANIZACION",
                    "ESPERANDO_SELECCION",
                    "LISTO_CONFIRMAR",
                ]),
                name="skilly_reag_una_abierta_prestacion",
            ),
        ),
    ]
