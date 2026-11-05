from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('profesionales', '0002_catalogo_inicial_competencias'),
        ('pagos', '0001_initial'),
        ('acceso', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CuentaPagoProfesional',
            fields=[
                ('id_cuenta', models.BigAutoField(primary_key=True, serialize=False)),
                ('titular', models.CharField(max_length=180)),
                ('rut_titular', models.CharField(max_length=12)),
                ('banco', models.CharField(max_length=120)),
                ('tipo_cuenta', models.CharField(max_length=24)),
                ('numero_cifrado', models.TextField()),
                ('ultimos_digitos', models.CharField(max_length=4)),
                ('correo', models.EmailField(max_length=254)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('profesional', models.OneToOneField(
                    to='profesionales.profesional', on_delete=django.db.models.deletion.PROTECT,
                    db_column='id_profesional', related_name='cuenta_pago')),
            ],
            options={'db_table': 'cuenta_pago_profesional'},
        ),
        migrations.CreateModel(
            name='AbonoPagoProfesional',
            fields=[
                ('id_abono', models.BigAutoField(primary_key=True, serialize=False)),
                ('numero_destino_cifrado', models.TextField()),
                ('destino_resumen', models.CharField(max_length=255)),
                ('monto_neto', models.DecimalField(max_digits=12, decimal_places=2)),
                ('moneda', models.CharField(max_length=10)),
                ('referencia_abono', models.CharField(max_length=120)),
                ('observacion', models.TextField(blank=True)),
                ('fecha_registro', models.DateTimeField(auto_now_add=True)),
                ('pago', models.OneToOneField(
                    to='pagos.pago', on_delete=django.db.models.deletion.PROTECT,
                    db_column='id_pago', related_name='abono_bancario')),
                ('cuenta', models.ForeignKey(
                    to='profesionales.cuentapagoprofesional', on_delete=django.db.models.deletion.PROTECT,
                    db_column='id_cuenta')),
                ('registrado_por', models.ForeignKey(
                    to='acceso.usuario', on_delete=django.db.models.deletion.PROTECT,
                    db_column='id_usuario_skilly')),
            ],
            options={'db_table': 'abono_pago_profesional'},
        ),
    ]
