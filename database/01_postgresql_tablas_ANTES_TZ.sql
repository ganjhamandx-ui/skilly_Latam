-- Skilly Latam - PostgreSQL - Creación de tablas
-- Rúbrica B1: script separado de tablas.
-- Ejecutar antes de llaves primarias y foráneas.
BEGIN;
CREATE SCHEMA IF NOT EXISTS skilly;
SET search_path TO skilly;

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario BIGSERIAL,
    correo VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(30) NOT NULL,
    estado VARCHAR(20) NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_usuario_correo UNIQUE (correo)
);

CREATE TABLE IF NOT EXISTS recuperacion_acceso (
    id_recuperacion BIGSERIAL,
    id_usuario BIGINT NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    fecha_solicitud TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP NOT NULL,
    usado BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS profesional (
    id_profesional BIGSERIAL,
    id_usuario BIGINT NOT NULL,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    telefono VARCHAR(30),
    titulo_profesional VARCHAR(150),
    resumen TEXT,
    ubicacion VARCHAR(150),
    estado_validacion VARCHAR(30) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_profesional_usuario UNIQUE (id_usuario)
);

CREATE TABLE IF NOT EXISTS competencia (
    id_competencia BIGSERIAL,
    nombre VARCHAR(120) NOT NULL,
    descripcion VARCHAR(255),
    estado VARCHAR(20) NOT NULL,
    CONSTRAINT uq_competencia_nombre UNIQUE (nombre)
);

CREATE TABLE IF NOT EXISTS profesional_competencia (
    id_profesional BIGINT NOT NULL,
    id_competencia BIGINT NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documento_profesional (
    id_documento BIGSERIAL,
    id_profesional BIGINT NOT NULL,
    tipo_documento VARCHAR(60) NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    referencia_archivo VARCHAR(500) NOT NULL,
    visibilidad VARCHAR(20) NOT NULL DEFAULT 'PRIVADA',
    estado VARCHAR(30) NOT NULL,
    fecha_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS solicitud_validacion (
    id_validacion BIGSERIAL,
    id_profesional BIGINT NOT NULL,
    id_revisor_skilly BIGINT,
    estado VARCHAR(30) NOT NULL,
    fecha_solicitud TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_asignacion TIMESTAMP,
    fecha_revision TIMESTAMP,
    observacion_resultado TEXT
);

CREATE TABLE IF NOT EXISTS validacion_documento (
    id_validacion BIGINT NOT NULL,
    id_documento BIGINT NOT NULL,
    estado_revision VARCHAR(30) NOT NULL,
    observacion TEXT
);

CREATE TABLE IF NOT EXISTS bloque_entrevista_validacion (
    id_bloque_entrevista BIGSERIAL,
    id_usuario_gestor BIGINT,
    fecha DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    capacidad INTEGER NOT NULL,
    estado VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS entrevista_validacion (
    id_entrevista BIGSERIAL,
    id_validacion BIGINT NOT NULL,
    id_bloque_entrevista BIGINT NOT NULL,
    estado VARCHAR(30) NOT NULL,
    fecha_reserva TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observacion TEXT
);

CREATE TABLE IF NOT EXISTS categoria_servicio (
    id_categoria BIGSERIAL,
    nombre VARCHAR(120) NOT NULL,
    descripcion VARCHAR(255),
    estado VARCHAR(20) NOT NULL,
    CONSTRAINT uq_categoria_nombre UNIQUE (nombre)
);

CREATE TABLE IF NOT EXISTS servicio (
    id_servicio BIGSERIAL,
    id_profesional BIGINT NOT NULL,
    id_categoria BIGINT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT NOT NULL,
    modalidad VARCHAR(30),
    alcance TEXT,
    referencia_precio VARCHAR(120),
    estado_publicacion VARCHAR(30) NOT NULL,
    fecha_publicacion TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS servicio_competencia (
    id_servicio BIGINT NOT NULL,
    id_competencia BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS revision_servicio (
    id_revision_servicio BIGSERIAL,
    id_servicio BIGINT NOT NULL,
    id_usuario_skilly BIGINT,
    numero_version INTEGER NOT NULL,
    contenido_revisado TEXT NOT NULL,
    observacion TEXT,
    estado_revision VARCHAR(30) NOT NULL,
    fecha_revision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_aprobacion_profesional TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disponibilidad (
    id_disponibilidad BIGSERIAL,
    id_profesional BIGINT NOT NULL,
    fecha DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    estado VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS reserva_disponibilidad (
    id_reserva BIGSERIAL,
    id_disponibilidad BIGINT NOT NULL,
    id_solicitud BIGINT NOT NULL,
    estado VARCHAR(30) NOT NULL,
    fecha_reserva TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cambio TIMESTAMP,
    motivo_cambio TEXT
);

CREATE TABLE IF NOT EXISTS empresa_solicitante (
    id_empresa BIGSERIAL,
    nombre_organizacion VARCHAR(180) NOT NULL,
    rut VARCHAR(20),
    rubro VARCHAR(120),
    sitio_web VARCHAR(255),
    estado VARCHAR(20) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacto_empresa (
    id_contacto BIGSERIAL,
    id_empresa BIGINT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    cargo VARCHAR(120),
    correo VARCHAR(150) NOT NULL,
    telefono VARCHAR(30),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS solicitud_servicio (
    id_solicitud BIGSERIAL,
    id_empresa BIGINT NOT NULL,
    id_contacto BIGINT NOT NULL,
    id_servicio BIGINT,
    objetivo VARCHAR(250) NOT NULL,
    descripcion_necesidad TEXT NOT NULL,
    modalidad VARCHAR(30),
    fecha_preferida DATE,
    referencia_presupuesto VARCHAR(120),
    urgencia VARCHAR(20),
    estado VARCHAR(30) NOT NULL,
    fecha_solicitud TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS solicitud_competencia (
    id_solicitud BIGINT NOT NULL,
    id_competencia BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS solicitud_profesional (
    id_solicitud BIGINT NOT NULL,
    id_profesional BIGINT NOT NULL,
    tipo_asociacion VARCHAR(30),
    estado VARCHAR(30) NOT NULL,
    fecha_asociacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asignacion_solicitud (
    id_asignacion BIGSERIAL,
    id_solicitud BIGINT NOT NULL,
    id_usuario_skilly BIGINT NOT NULL,
    tipo_asignacion VARCHAR(30) NOT NULL,
    fecha_asignacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP,
    estado VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS coordinacion_solicitud (
    id_coordinacion BIGSERIAL,
    id_solicitud BIGINT NOT NULL,
    id_usuario_skilly BIGINT NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    detalle TEXT,
    estado_resultante VARCHAR(30),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reunion_solicitud (
    id_reunion BIGSERIAL,
    id_solicitud BIGINT NOT NULL,
    id_profesional BIGINT NOT NULL,
    id_usuario_skilly BIGINT,
    fecha_hora TIMESTAMP NOT NULL,
    modalidad VARCHAR(30),
    estado VARCHAR(30) NOT NULL,
    enlace_reunion VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS prestacion_servicio (
    id_prestacion BIGSERIAL,
    id_solicitud BIGINT NOT NULL,
    id_profesional BIGINT NOT NULL,
    condiciones_comunicadas TEXT,
    estado VARCHAR(30) NOT NULL,
    fecha_confirmacion TIMESTAMP,
    fecha_inicio DATE,
    fecha_fin DATE,
    fecha_cierre TIMESTAMP,
    CONSTRAINT uq_prestacion_solicitud UNIQUE (id_solicitud)
);

CREATE TABLE IF NOT EXISTS pago (
    id_pago BIGSERIAL,
    id_prestacion BIGINT NOT NULL,
    monto_total NUMERIC(12,2) NOT NULL,
    moneda VARCHAR(10) NOT NULL,
    porcentaje_comision_aplicado NUMERIC(7,4) NOT NULL,
    monto_comision NUMERIC(12,2) NOT NULL,
    monto_neto_profesional NUMERIC(12,2) NOT NULL,
    estado_pago VARCHAR(30) NOT NULL,
    metodo_pago VARCHAR(30) NOT NULL,
    proveedor_pago VARCHAR(50),
    estado_verificacion VARCHAR(30),
    comprobante_transferencia VARCHAR(255),
    fecha_pago TIMESTAMP,
    fecha_retencion TIMESTAMP,
    fecha_liberacion TIMESTAMP,
    referencia_transaccion VARCHAR(255),
    CONSTRAINT uq_pago_prestacion UNIQUE (id_prestacion)
);

CREATE TABLE IF NOT EXISTS historial_estado_pago (
    id_historial_pago BIGSERIAL,
    id_pago BIGINT NOT NULL,
    id_usuario_skilly BIGINT,
    estado_anterior VARCHAR(30),
    estado_nuevo VARCHAR(30) NOT NULL,
    fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observacion TEXT
);

CREATE TABLE IF NOT EXISTS reversa_pago (
    id_reversa BIGSERIAL,
    id_pago BIGINT NOT NULL,
    id_usuario_skilly BIGINT,
    id_resolucion_reclamo BIGINT,
    monto_reversa NUMERIC(12,2),
    estado_reversa VARCHAR(30) NOT NULL,
    motivo TEXT,
    referencia_externa VARCHAR(255),
    fecha_solicitud TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP
);

CREATE TABLE IF NOT EXISTS avance_servicio (
    id_avance BIGSERIAL,
    id_prestacion BIGINT NOT NULL,
    estado VARCHAR(30) NOT NULL,
    detalle TEXT,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entrega (
    id_entrega BIGSERIAL,
    id_prestacion BIGINT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    descripcion TEXT NOT NULL,
    referencia_entrega VARCHAR(500),
    fecha_entrega TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS observacion_entrega (
    id_observacion BIGSERIAL,
    id_entrega BIGINT NOT NULL,
    id_contacto BIGINT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detalle TEXT NOT NULL,
    estado VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS reclamo_prestacion (
    id_reclamo BIGSERIAL,
    id_prestacion BIGINT NOT NULL,
    id_contacto BIGINT NOT NULL,
    motivo VARCHAR(120) NOT NULL,
    descripcion TEXT NOT NULL,
    estado VARCHAR(30) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resolucion_reclamo (
    id_resolucion BIGSERIAL,
    id_reclamo BIGINT NOT NULL,
    id_usuario_skilly BIGINT NOT NULL,
    decision VARCHAR(40) NOT NULL,
    efecto_economico VARCHAR(40) NOT NULL,
    monto_afectado NUMERIC(12,2),
    observacion TEXT,
    fecha_resolucion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_resolucion_reclamo UNIQUE (id_reclamo)
);

CREATE TABLE IF NOT EXISTS retroalimentacion (
    id_feedback BIGSERIAL,
    id_prestacion BIGINT NOT NULL,
    id_contacto BIGINT NOT NULL,
    contenido TEXT NOT NULL,
    visibilidad VARCHAR(20) NOT NULL DEFAULT 'PRIVADA',
    estado VARCHAR(30) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recomendacion_desarrollo (
    id_recomendacion BIGSERIAL,
    id_profesional BIGINT NOT NULL,
    id_feedback BIGINT,
    id_usuario_skilly BIGINT NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT NOT NULL,
    estado VARCHAR(30) NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_comunicacion TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evento_trazabilidad (
    id_evento BIGSERIAL,
    id_usuario BIGINT,
    entidad_tipo VARCHAR(60) NOT NULL,
    entidad_id BIGINT,
    accion VARCHAR(80) NOT NULL,
    detalle_resumido VARCHAR(255),
    fecha_evento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parametro_sistema (
    id_parametro BIGSERIAL,
    clave VARCHAR(100) NOT NULL,
    valor_actual VARCHAR(500) NOT NULL,
    tipo_dato VARCHAR(30) NOT NULL,
    descripcion VARCHAR(255),
    id_usuario_actualiza BIGINT,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_parametro_clave UNIQUE (clave)
);

CREATE TABLE IF NOT EXISTS historial_parametro (
    id_historial_parametro BIGSERIAL,
    id_parametro BIGINT NOT NULL,
    valor_anterior VARCHAR(500),
    valor_nuevo VARCHAR(500) NOT NULL,
    id_usuario_skilly BIGINT,
    fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
