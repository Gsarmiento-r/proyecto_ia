# =============================================================================
# infra/main.tf — Infraestructura principal de Autos-AI en Google Cloud
# =============================================================================

# ── APIs de Google Cloud a habilitar ─────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "documentai.googleapis.com",
    "bigquery.googleapis.com",
    "bigquerystorage.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# ── Cuenta de servicio para el agente ────────────────────────────────────────
resource "google_service_account" "autos_ai_sa" {
  account_id   = "${var.app_name}-sa"
  display_name = "Autos AI Agent Service Account"
  project      = var.project_id
  description  = "Cuenta de servicio para el agente AutoFlota-AI"
}

# Roles necesarios para la cuenta de servicio
locals {
  sa_roles = [
    "roles/aiplatform.user",
    "roles/datastore.user",
    "roles/storage.objectAdmin",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/documentai.apiUser",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
  ]
}

resource "google_project_iam_member" "autos_ai_sa_roles" {
  for_each = toset(local.sa_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.autos_ai_sa.email}"
}

# ── Artifact Registry ─────────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "autos_ai_repo" {
  location      = var.region
  repository_id = "${var.app_name}-repo"
  description   = "Repositorio de imágenes Docker para Autos-AI"
  format        = "DOCKER"
  project       = var.project_id
  labels        = var.labels

  depends_on = [google_project_service.apis]
}

# ── Módulo: Cloud Storage ─────────────────────────────────────────────────────
module "storage" {
  source = "./modules/storage"

  project_id   = var.project_id
  region       = var.region
  app_name     = var.app_name
  environment  = var.environment
  labels       = var.labels

  depends_on = [google_project_service.apis]
}

# ── Módulo: Firestore ─────────────────────────────────────────────────────────
module "firestore" {
  source = "./modules/firestore"

  project_id         = var.project_id
  firestore_location = var.firestore_location
  app_name           = var.app_name
  environment        = var.environment

  depends_on = [google_project_service.apis]
}

# ── Módulo: Vertex AI ─────────────────────────────────────────────────────────
module "vertex_ai" {
  source = "./modules/vertex_ai"

  project_id          = var.project_id
  region              = var.region
  app_name            = var.app_name
  environment         = var.environment
  labels              = var.labels
  enable_bigquery     = var.enable_bigquery
  enable_document_ai  = var.enable_document_ai
  service_account_email = google_service_account.autos_ai_sa.email

  depends_on = [google_project_service.apis]
}

# ── Módulo: Cloud Run ─────────────────────────────────────────────────────────
module "cloud_run" {
  source = "./modules/cloud_run"

  project_id            = var.project_id
  region                = var.region
  app_name              = var.app_name
  environment           = var.environment
  container_image       = var.container_image
  service_account_email = google_service_account.autos_ai_sa.email
  min_instances         = var.cloud_run_min_instances
  max_instances         = var.cloud_run_max_instances
  memory                = var.cloud_run_memory
  cpu                   = var.cloud_run_cpu
  labels                = var.labels

  env_vars = {
    GOOGLE_CLOUD_PROJECT                = var.project_id
    GOOGLE_CLOUD_LOCATION               = var.region
    VERTEXAI_PROJECT                    = var.project_id
    VERTEXAI_LOCATION                   = var.region
    GEMINI_MODEL                        = var.gemini_model
    GCS_BUCKET_SUBMISSIONS              = module.storage.bucket_submissions_name
    GCS_BUCKET_OUTPUTS                  = module.storage.bucket_outputs_name
    FIRESTORE_DATABASE                  = "(default)"
    FIRESTORE_COLLECTION_SOLICITUDES    = "solicitudes_seguros"
    APP_ENV                             = var.environment
    LOG_LEVEL                           = var.environment == "production" ? "INFO" : "DEBUG"
  }

  depends_on = [
    module.storage,
    module.firestore,
    module.vertex_ai,
    google_artifact_registry_repository.autos_ai_repo,
  ]
}

# ── Secret Manager — Secret Key ───────────────────────────────────────────────
resource "google_secret_manager_secret" "secret_key" {
  secret_id = "${var.app_name}-secret-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels
  depends_on = [google_project_service.apis]
}
