// Skilly Latam - Datos sintéticos de prueba para MongoDB
// Información ficticia para evaluación/desarrollo. No contiene datos reales.

use("skilly_documental");

db.documentos_flexibles.insertMany([
  {
    tipo: "perfil_profesional_extendido",
    referencia_pg: { entidad: "profesional", id: NumberLong(1) },
    fecha_registro: ISODate("2026-10-10T13:00:00Z"),
    payload: {
      idiomas: [{ nombre: "Español", nivel: "Nativo" }],
      metodologias: ["Facilitación", "Gestión de proyectos"],
      disponibilidad_observada: "Flexible"
    },
    etiquetas: ["demo", "profesional"]
  },
  {
    tipo: "metadatos_documento_profesional",
    referencia_pg: { entidad: "documento_profesional", id: NumberLong(1) },
    fecha_registro: ISODate("2026-10-10T13:05:00Z"),
    payload: {
      formato: "PDF",
      origen: "carga_profesional",
      atributos_extra: { emisor: "Institución Demo", anio: 2025 }
    },
    etiquetas: ["demo", "documento"]
  }
]);

db.evidencias_entrega.insertOne({
  id_entrega_pg: NumberLong(1),
  fecha_registro: ISODate("2026-10-13T18:00:00Z"),
  evidencias: [
    { tipo: "archivo", referencia: "demo/entregas/entrega_1.pdf", descripcion: "Entregable sintético" },
    { tipo: "nota", contenido: "Evidencia de prueba para validación académica." }
  ],
  metadata_flexible: {
    checklist: { recibido: true, revisado: true },
    tags: ["demo", "entrega"]
  }
});

db.eventos_integracion.insertOne({
  tipo_integracion: "TRANSFERENCIA_BANCARIA",
  id_pago_pg: NumberLong(1),
  fecha_evento: ISODate("2026-10-12T15:30:00Z"),
  payload_sanitizado: {
    referencia: "TRX-DEMO-001",
    estado: "VERIFICADO",
    monto: 100000,
    moneda: "CLP"
  },
  resultado: "OK"
});
