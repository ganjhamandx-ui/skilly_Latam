from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="SolicitudReagendamiento",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("prestacion_id", models.BigIntegerField(db_index=True)),
                ("solicitud_id", models.BigIntegerField(db_index=True)),
                ("profesional_id", models.BigIntegerField(db_index=True)),
                ("bloque_original_id", models.BigIntegerField()),
                ("bloque_propuesto_id", models.BigIntegerField(blank=True, null=True)),
                ("motivo_organizacion", models.TextField()),
                ("motivo_profesional", models.TextField(blank=True)),
                ("estado", models.CharField(db_index=True, default="PENDIENTE_ADMIN", max_length=40)),
                ("requiere_confirmacion_organizacion", models.BooleanField(default=False)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "solicitud_reagendamiento"},
        ),
        migrations.CreateModel(
            name="EventoReagendamiento",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("actor", models.CharField(max_length=25)),
                ("accion", models.CharField(max_length=55)),
                ("detalle", models.TextField()),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                ("reagendamiento", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="eventos", to="reagendamientos.solicitudreagendamiento")),
            ],
            options={"db_table": "evento_reagendamiento", "ordering": ["fecha", "id"]},
        ),
        migrations.AddConstraint(
            model_name="solicitudreagendamiento",
            constraint=models.UniqueConstraint(
                fields=("prestacion_id",),
                condition=Q(estado__in=["PENDIENTE_ADMIN", "PENDIENTE_PROFESIONAL", "ESPERANDO_NUEVO_BLOQUE", "PENDIENTE_ORGANIZACION", "LISTO_CONFIRMAR"]),
                name="skilly_reag_una_abierta_prestacion",
            ),
        ),
    ]
