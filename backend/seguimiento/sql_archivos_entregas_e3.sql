BEGIN;
CREATE TABLE skilly.archivo_entrega_e3 (
  id_archivo BIGSERIAL PRIMARY KEY,
  id_entrega BIGINT NOT NULL REFERENCES skilly.entrega(id_entrega) ON DELETE RESTRICT,
  nombre_original VARCHAR(255) NOT NULL,
  ruta_privada VARCHAR(255) NOT NULL UNIQUE,
  tipo_mime VARCHAR(120) NOT NULL,
  tamanio_bytes BIGINT NOT NULL CHECK (tamanio_bytes>0 AND tamanio_bytes<=10485760),
  fecha_subida TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX archivo_entrega_e3_entrega_idx ON skilly.archivo_entrega_e3 (id_entrega);
GRANT SELECT, INSERT ON skilly.archivo_entrega_e3 TO skilly_app;
GRANT USAGE, SELECT ON SEQUENCE skilly.archivo_entrega_e3_id_archivo_seq TO skilly_app;
COMMIT;
