# =============================================================================
# infra/modules/firestore/main.tf — Firestore para persistencia del agente
# =============================================================================

resource "google_firestore_database" "autos_ai_db" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"

  deletion_policy = "DELETE"
}

# Índices compuestos para consultas eficientes
resource "google_firestore_index" "idx_cliente_fecha" {
  project    = var.project_id
  database   = google_firestore_database.autos_ai_db.name
  collection = "solicitudes_seguros"

  fields {
    field_path = "nombre_cliente"
    order      = "ASCENDING"
  }
  fields {
    field_path = "timestamp_creacion"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "idx_rfc_fecha" {
  project    = var.project_id
  database   = google_firestore_database.autos_ai_db.name
  collection = "solicitudes_seguros"

  fields {
    field_path = "rfc_cliente"
    order      = "ASCENDING"
  }
  fields {
    field_path = "timestamp_creacion"
    order      = "DESCENDING"
  }
}

output "database_id" {
  value = google_firestore_database.autos_ai_db.name
}
