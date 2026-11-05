from django.db import models

from acceso.models import Usuario


class Profesional(models.Model):
    id_profesional = models.BigAutoField(primary_key=True)

    id_usuario = models.OneToOneField(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario",
        related_name="profesional",
    )

    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)

    telefono = models.CharField(
        max_length=30,
        blank=True,
        null=True,
    )

    titulo_profesional = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    resumen = models.TextField(
        blank=True,
        null=True,
    )

    ubicacion = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    estado_validacion = models.CharField(max_length=30)
    fecha_registro = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "profesional"

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class Competencia(models.Model):
    id_competencia = models.BigAutoField(
        primary_key=True
    )

    nombre = models.CharField(
        max_length=120,
        unique=True,
    )

    descripcion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=20
    )

    class Meta:
        managed = False
        db_table = "competencia"

    def __str__(self):
        return self.nombre


class ProfesionalCompetencia(models.Model):
    pk = models.CompositePrimaryKey(
        "id_profesional",
        "id_competencia",
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    id_competencia = models.ForeignKey(
        Competencia,
        models.DO_NOTHING,
        db_column="id_competencia",
    )

    fecha_registro = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "profesional_competencia"


class DocumentoProfesional(models.Model):
    id_documento = models.BigAutoField(
        primary_key=True
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    tipo_documento = models.CharField(
        max_length=60
    )

    nombre_archivo = models.CharField(
        max_length=255
    )

    referencia_archivo = models.CharField(
        max_length=500
    )

    visibilidad = models.CharField(
        max_length=20
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_carga = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "documento_profesional"

    def __str__(self):
        return self.nombre_archivo


class SolicitudValidacion(models.Model):
    id_validacion = models.BigAutoField(
        primary_key=True
    )

    id_profesional = models.ForeignKey(
        Profesional,
        models.DO_NOTHING,
        db_column="id_profesional",
    )

    id_revisor_skilly = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_revisor_skilly",
        blank=True,
        null=True,
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_solicitud = models.DateTimeField()

    fecha_asignacion = models.DateTimeField(
        blank=True,
        null=True,
    )

    fecha_revision = models.DateTimeField(
        blank=True,
        null=True,
    )

    observacion_resultado = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "solicitud_validacion"


class ValidacionDocumento(models.Model):
    pk = models.CompositePrimaryKey(
        "id_validacion",
        "id_documento",
    )

    id_validacion = models.ForeignKey(
        SolicitudValidacion,
        models.DO_NOTHING,
        db_column="id_validacion",
    )

    id_documento = models.ForeignKey(
        DocumentoProfesional,
        models.DO_NOTHING,
        db_column="id_documento",
    )

    estado_revision = models.CharField(
        max_length=30
    )

    observacion = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "validacion_documento"


class BloqueEntrevistaValidacion(models.Model):
    id_bloque_entrevista = models.BigAutoField(
        primary_key=True
    )

    id_usuario_gestor = models.ForeignKey(
        Usuario,
        models.DO_NOTHING,
        db_column="id_usuario_gestor",
        blank=True,
        null=True,
    )

    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    capacidad = models.IntegerField()

    estado = models.CharField(
        max_length=20
    )

    class Meta:
        managed = False
        db_table = "bloque_entrevista_validacion"


class EntrevistaValidacion(models.Model):
    id_entrevista = models.BigAutoField(
        primary_key=True
    )

    id_validacion = models.ForeignKey(
        SolicitudValidacion,
        models.DO_NOTHING,
        db_column="id_validacion",
    )

    id_bloque_entrevista = models.ForeignKey(
        BloqueEntrevistaValidacion,
        models.DO_NOTHING,
        db_column="id_bloque_entrevista",
    )

    estado = models.CharField(
        max_length=30
    )

    fecha_reserva = models.DateTimeField()

    observacion = models.TextField(
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "entrevista_validacion"

# Gestion de cuentas de cobro y registro separado de abonos bancarios.
class CuentaPagoProfesional(models.Model):
    id_cuenta = models.BigAutoField(primary_key=True)
    profesional = models.OneToOneField(Profesional, on_delete=models.PROTECT,
        db_column='id_profesional', related_name='cuenta_pago')
    titular = models.CharField(max_length=180)
    rut_titular = models.CharField(max_length=12)
    banco = models.CharField(max_length=120)
    tipo_cuenta = models.CharField(max_length=24)
    numero_cifrado = models.TextField()
    ultimos_digitos = models.CharField(max_length=4)
    correo = models.EmailField(max_length=254)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cuenta_pago_profesional'


class AbonoPagoProfesional(models.Model):
    id_abono = models.BigAutoField(primary_key=True)
    pago = models.OneToOneField('pagos.Pago', on_delete=models.PROTECT,
        db_column='id_pago', related_name='abono_bancario')
    cuenta = models.ForeignKey(CuentaPagoProfesional, on_delete=models.PROTECT,
        db_column='id_cuenta')
    numero_destino_cifrado = models.TextField()
    destino_resumen = models.CharField(max_length=255)
    monto_neto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=10)
    referencia_abono = models.CharField(max_length=120)
    observacion = models.TextField(blank=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT,
        db_column='id_usuario_skilly')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abono_pago_profesional'
