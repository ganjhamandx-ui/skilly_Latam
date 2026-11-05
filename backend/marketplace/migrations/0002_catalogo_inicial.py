"""Catalogo inicial reproducible para propuestas de servicios de SKILLY.

No recrea tablas ni modifica categorias preexistentes. Se ejecuta una vez
mediante `python backend/manage.py migrate` en cada instalacion nueva.
"""
from django.db import migrations


CATEGORIAS = (
    ("Tecnología e Informática", "Desarrollo de software, sitios web, sistemas y soporte tecnológico."),
    ("Diseño y Creatividad", "Diseño gráfico, identidad visual y contenido creativo."),
    ("Administración y Gestión", "Gestión administrativa y mejora de procesos empresariales."),
    ("Marketing y Comunicación", "Estrategias de comunicación, marketing y contenidos digitales."),
    ("Educación y Capacitación", "Clases, formación y capacitación especializada."),
    ("Consultoría y Asesoría", "Asesoría profesional, diagnósticos y planificación."),
)


def crear_catalogo(apps, schema_editor):
    CategoriaServicio = apps.get_model("marketplace", "CategoriaServicio")
    db = schema_editor.connection.alias
    for nombre, descripcion in CATEGORIAS:
        CategoriaServicio.objects.using(db).get_or_create(
            nombre=nombre,
            defaults={"descripcion": descripcion, "estado": "ACTIVO"},
        )


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0001_initial")]
    operations = [migrations.RunPython(crear_catalogo, reverse_code=migrations.RunPython.noop)]
