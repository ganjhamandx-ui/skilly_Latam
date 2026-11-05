"""Competencias iniciales reproducibles para profesionales SKILLY.

No altera competencias ya existentes ni asigna capacidades a profesionales.
La reversa conserva los datos para evitar borrados de referencias existentes.
"""
from django.db import migrations


COMPETENCIAS = (
    ("Desarrollo web", "Creación y mantenimiento de sitios y aplicaciones web."),
    ("Python", "Desarrollo de soluciones con lenguaje Python."),
    ("Django", "Desarrollo de aplicaciones web con Django."),
    ("JavaScript", "Programación de funcionalidades web con JavaScript."),
    ("React", "Desarrollo de interfaces web con React."),
    ("PostgreSQL", "Modelado y consultas de bases de datos PostgreSQL."),
    ("Bases de datos", "Diseño, administración y consultas de bases de datos."),
    ("Análisis de requerimientos", "Levantamiento y análisis de necesidades de software."),
    ("Diseño de interfaces", "Diseño de interfaces y experiencias de usuario."),
    ("Soporte informático", "Diagnóstico y apoyo en sistemas y equipos informáticos."),
    ("Gestión de proyectos", "Planificación, coordinación y seguimiento de proyectos."),
    ("Comunicación profesional", "Comunicación de resultados, presentaciones y coordinación."),
)


def crear_catalogo(apps, schema_editor):
    Competencia = apps.get_model("profesionales", "Competencia")
    db = schema_editor.connection.alias
    for nombre, descripcion in COMPETENCIAS:
        Competencia.objects.using(db).get_or_create(
            nombre=nombre,
            defaults={"descripcion": descripcion, "estado": "ACTIVO"},
        )


class Migration(migrations.Migration):
    dependencies = [("profesionales", "0001_initial")]
    operations = [migrations.RunPython(crear_catalogo, reverse_code=migrations.RunPython.noop)]
