# =============================================================================
# infra/modules/cloud_run/main.tf — Cloud Run para AutoFlota-AI
# =============================================================================

resource "google_cloud_run_v2_service" "autos_ai" {
  name     = "${var.app_name}-agent"
  location = var.region
  project  = var.project_id

  labels = var.labels

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image

      resources {
        limits = {
          memory = var.memory
          cpu    = var.cpu
        }
        cpu_idle          = false
        startup_cpu_boost = true
      }

      # Variables de entorno
      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      # Liveness probe
      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 30
        period_seconds        = 30
        failure_threshold     = 3
      }

      # Startup probe
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 10
      }

      ports {
        container_port = 8080
        name           = "http1"
      }
    }

    timeout = "300s"

    max_instance_request_concurrency = 10
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Acceso público al servicio (ajustar para producción con IAP o autenticación)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count    = var.environment == "production" ? 0 : 1
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.autos_ai.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value = google_cloud_run_v2_service.autos_ai.uri
}

output "service_name" {
  value = google_cloud_run_v2_service.autos_ai.name
}
