# =============================================================================
# infra/modules/storage/main.tf — Google Cloud Storage
# =============================================================================

# ── Bucket de Solicitudes (input) ─────────────────────────────────────────────
resource "google_storage_bucket" "submissions" {
  name                        = "${var.project_id}-submissions"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  labels                      = var.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action { type = "SetStorageClass"; storage_class = "NEARLINE" }
    condition { age = 90 }
  }

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

# ── Bucket de Outputs (CSV y resultados) ──────────────────────────────────────
resource "google_storage_bucket" "outputs" {
  name                        = "${var.project_id}-outputs"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  labels                      = var.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action { type = "SetStorageClass"; storage_class = "NEARLINE" }
    condition { age = 180 }
  }
}

# ── Bucket de Modelos / Estado Terraform ──────────────────────────────────────
resource "google_storage_bucket" "terraform_state" {
  name                        = "${var.project_id}-terraform-state"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  labels                      = var.labels

  versioning {
    enabled = true
  }
}

# ── Outputs ───────────────────────────────────────────────────────────────────
output "bucket_submissions_name" {
  value = google_storage_bucket.submissions.name
}

output "bucket_outputs_name" {
  value = google_storage_bucket.outputs.name
}

output "bucket_terraform_state_name" {
  value = google_storage_bucket.terraform_state.name
}
