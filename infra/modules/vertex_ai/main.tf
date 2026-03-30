# =============================================================================
# infra/modules/vertex_ai/main.tf — Vertex AI y servicios analíticos
# =============================================================================

# ── BigQuery Dataset para analítica ──────────────────────────────────────────
resource "google_bigquery_dataset" "autos_ai" {
  count      = var.enable_bigquery ? 1 : 0
  dataset_id = "${replace(var.app_name, "-", "_")}_analytics"
  project    = var.project_id
  location   = var.region

  friendly_name = "Autos AI Analytics"
  description   = "Dataset de analítica para solicitudes y cotizaciones de seguros de flotilla"
  labels        = var.labels

  delete_contents_on_destroy = false
}

# ── Tabla BigQuery: Solicitudes ───────────────────────────────────────────────
resource "google_bigquery_table" "solicitudes" {
  count      = var.enable_bigquery ? 1 : 0
  dataset_id = google_bigquery_dataset.autos_ai[0].dataset_id
  table_id   = "solicitudes"
  project    = var.project_id
  labels     = var.labels

  deletion_protection = true

  schema = jsonencode([
    { name = "id_solicitud", type = "STRING", mode = "REQUIRED" },
    { name = "timestamp_creacion", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "nombre_cliente", type = "STRING", mode = "NULLABLE" },
    { name = "rfc_cliente", type = "STRING", mode = "NULLABLE" },
    { name = "nombre_broker", type = "STRING", mode = "NULLABLE" },
    { name = "total_vehiculos", type = "INTEGER", mode = "NULLABLE" },
    { name = "prima_maxima", type = "FLOAT64", mode = "NULLABLE" },
    { name = "moneda", type = "STRING", mode = "NULLABLE" },
    { name = "fecha_inicio_vigencia", type = "STRING", mode = "NULLABLE" },
    { name = "fecha_fin_vigencia", type = "STRING", mode = "NULLABLE" },
    { name = "tipo_archivo_fuente", type = "STRING", mode = "NULLABLE" },
    { name = "confianza_extraccion", type = "STRING", mode = "NULLABLE" },
    { name = "estatus", type = "STRING", mode = "NULLABLE" },
  ])

  time_partitioning {
    type  = "DAY"
    field = "timestamp_creacion"
  }
}

# ── Document AI Processor ─────────────────────────────────────────────────────
resource "google_document_ai_processor" "form_parser" {
  count        = var.enable_document_ai ? 1 : 0
  location     = "us"
  display_name = "${var.app_name}-form-parser"
  type         = "FORM_PARSER_PROCESSOR"
  project      = var.project_id
}

# ── Vertex AI Feature Store (memoria del agente) ──────────────────────────────
resource "google_vertex_ai_feature_store" "autos_ai_store" {
  name    = "${replace(var.app_name, "-", "_")}_feature_store"
  region  = var.region
  project = var.project_id
  labels  = var.labels

  online_serving_config {
    fixed_node_count = 1
  }
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "bigquery_dataset_id" {
  value = var.enable_bigquery ? google_bigquery_dataset.autos_ai[0].dataset_id : null
}

output "document_ai_processor_id" {
  value = var.enable_document_ai ? google_document_ai_processor.form_parser[0].id : null
}

output "endpoint_id" {
  value = google_vertex_ai_feature_store.autos_ai_store.id
}
