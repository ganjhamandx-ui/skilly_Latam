// Skilly Latam - Modelo físico MongoDB (NoSQL/documental)
// Modelo documental para evaluación/ejecución; no implica despliegue productivo.
// Se conservan referencias lógicas a PostgreSQL mediante *_pg. No existen FK entre motores.

use("skilly_documental");

db.createCollection("documentos_flexibles", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["tipo", "referencia_pg", "fecha_registro", "payload"],
      properties: {
        tipo: { bsonType: "string" },
        referencia_pg: {
          bsonType: "object",
          required: ["entidad", "id"],
          properties: {
            entidad: { bsonType: "string" },
            id: { bsonType: ["int", "long"] }
          }
        },
        fecha_registro: { bsonType: "date" },
        payload: { bsonType: "object" },
        etiquetas: { bsonType: "array", items: { bsonType: "string" } }
      }
    }
  }
});

db.createCollection("evidencias_entrega", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id_entrega_pg", "fecha_registro", "evidencias"],
      properties: {
        id_entrega_pg: { bsonType: ["int", "long"] },
        fecha_registro: { bsonType: "date" },
        evidencias: { bsonType: "array" },
        metadata_flexible: { bsonType: "object" }
      }
    }
  }
});

db.createCollection("eventos_integracion", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["tipo_integracion", "fecha_evento", "payload_sanitizado"],
      properties: {
        tipo_integracion: { bsonType: "string" },
        id_pago_pg: { bsonType: ["int", "long", "null"] },
        fecha_evento: { bsonType: "date" },
        payload_sanitizado: { bsonType: "object" },
        resultado: { bsonType: ["string", "null"] }
      }
    }
  }
});

db.documentos_flexibles.createIndex({ "referencia_pg.entidad": 1, "referencia_pg.id": 1 });
db.documentos_flexibles.createIndex({ "tipo": 1, "fecha_registro": -1 });
db.evidencias_entrega.createIndex({ "id_entrega_pg": 1 });
db.eventos_integracion.createIndex({ "tipo_integracion": 1, "fecha_evento": -1 });
db.eventos_integracion.createIndex({ "id_pago_pg": 1 });

// Nota: archivos binarios grandes no se guardan aquí por obligación.
// El proyecto puede almacenarlos en un repositorio privado/Cloud Storage y conservar en MongoDB
// únicamente metadata o payload documental flexible cuando corresponda.
