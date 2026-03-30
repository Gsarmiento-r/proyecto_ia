# =============================================================================
# infra/outputs.tf — Outputs del módulo Terraform raíz
# =============================================================================

output "cloud_run_url" {
  description = "URL del servicio Cloud Run del agente"
  value       = module.cloud_run.service_url
}

output "cloud_run_service_name" {
  description = "Nombre del servicio Cloud Run"
  value       = module.cloud_run.service_name
}

output "service_account_email" {
  description = "Email de la cuenta de servicio del agente"
  value       = google_service_account.autos_ai_sa.email
}

output "artifact_registry_url" {
  description = "URL del repositorio en Artifact Registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.autos_ai_repo.repository_id}"
}

output "gcs_bucket_submissions" {
  description = "Nombre del bucket GCS para solicitudes"
  value       = module.storage.bucket_submissions_name
}

output "gcs_bucket_outputs" {
  description = "Nombre del bucket GCS para outputs"
  value       = module.storage.bucket_outputs_name
}

output "firestore_database" {
  description = "ID de la base de datos Firestore"
  value       = module.firestore.database_id
}

output "bigquery_dataset" {
  description = "ID del dataset BigQuery"
  value       = var.enable_bigquery ? module.vertex_ai.bigquery_dataset_id : null
}

output "vertex_ai_endpoint" {
  description = "Endpoint de Vertex AI para el agente"
  value       = module.vertex_ai.endpoint_id
}
