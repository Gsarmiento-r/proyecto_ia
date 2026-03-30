# =============================================================================
# infra/variables.tf — Variables de entrada para el módulo raíz
# =============================================================================

variable "project_id" {
  description = "ID del proyecto de Google Cloud"
  type        = string
  default     = "autos-ai"
}

variable "region" {
  description = "Región de Google Cloud"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona de Google Cloud"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Entorno de despliegue (development, staging, production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "El entorno debe ser: development, staging o production."
  }
}

variable "app_name" {
  description = "Nombre de la aplicación"
  type        = string
  default     = "autos-ai"
}

variable "container_image" {
  description = "URI de la imagen Docker en Artifact Registry"
  type        = string
  default     = "us-central1-docker.pkg.dev/autos-ai/autos-ai-repo/autos-ai-agent:latest"
}

variable "gemini_model" {
  description = "Modelo Gemini a utilizar"
  type        = string
  default     = "gemini-2.0-flash-001"
}

variable "cloud_run_min_instances" {
  description = "Número mínimo de instancias Cloud Run"
  type        = number
  default     = 1
}

variable "cloud_run_max_instances" {
  description = "Número máximo de instancias Cloud Run"
  type        = number
  default     = 10
}

variable "cloud_run_memory" {
  description = "Memoria asignada a cada instancia Cloud Run"
  type        = string
  default     = "2Gi"
}

variable "cloud_run_cpu" {
  description = "CPU asignada a cada instancia Cloud Run"
  type        = string
  default     = "2"
}

variable "firestore_location" {
  description = "Ubicación de la base de datos Firestore"
  type        = string
  default     = "us-central"
}

variable "enable_bigquery" {
  description = "Habilitar BigQuery para analítica"
  type        = bool
  default     = true
}

variable "enable_document_ai" {
  description = "Habilitar Google Document AI"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels comunes para todos los recursos"
  type        = map(string)
  default = {
    app         = "autos-ai"
    team        = "seguros-ai"
    managed-by  = "terraform"
  }
}
