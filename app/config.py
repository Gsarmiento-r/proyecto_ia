# =============================================================================
# app/config.py — Configuración centralizada de la aplicación
# =============================================================================
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración central leída desde variables de entorno o archivo .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Aplicación ────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    log_level: str = "INFO"

    # ── Google Cloud ─────────────────────────────────────────────────────────
    google_cloud_project: str = Field("autos-ai", alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field("us-east1", alias="GOOGLE_CLOUD_LOCATION")
    google_application_credentials: str | None = Field(
        None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # ── Vertex AI / Gemini ────────────────────────────────────────────────────
    vertexai_project: str = Field("autos-ai", alias="VERTEXAI_PROJECT")
    vertexai_location: str = Field("us-east1", alias="VERTEXAI_LOCATION")
    gemini_model: str = Field("gemini-2.0-flash-001", alias="GEMINI_MODEL")
    gemini_model_pro: str = Field("gemini-2.0-pro-001", alias="GEMINI_MODEL_PRO")

    # ── Google Cloud Storage ──────────────────────────────────────────────────
    gcs_bucket_submissions: str = Field(
        "autos-ai-submissions", alias="GCS_BUCKET_SUBMISSIONS"
    )
    gcs_bucket_outputs: str = Field("autos-ai-outputs", alias="GCS_BUCKET_OUTPUTS")

    # ── Firestore ─────────────────────────────────────────────────────────────
    firestore_database: str = Field("(default)", alias="FIRESTORE_DATABASE")
    firestore_collection_solicitudes: str = Field(
        "solicitudes_seguros", alias="FIRESTORE_COLLECTION_SOLICITUDES"
    )
    firestore_collection_clientes: str = Field(
        "clientes", alias="FIRESTORE_COLLECTION_CLIENTES"
    )
    firestore_collection_historial: str = Field(
        "historial_cotizaciones", alias="FIRESTORE_COLLECTION_HISTORIAL"
    )

    # ── Document AI ───────────────────────────────────────────────────────────
    document_ai_processor_id: str = Field("", alias="DOCUMENT_AI_PROCESSOR_ID")
    document_ai_processor_version: str = Field("rc", alias="DOCUMENT_AI_PROCESSOR_VERSION")
    document_ai_location: str = Field("us", alias="DOCUMENT_AI_LOCATION")

    # ── BigQuery ──────────────────────────────────────────────────────────────
    bigquery_dataset: str = Field("autos_ai_analytics", alias="BIGQUERY_DATASET")
    bigquery_table_solicitudes: str = Field("solicitudes", alias="BIGQUERY_TABLE_SOLICITUDES")

    # ── ADK ───────────────────────────────────────────────────────────────────
    adk_app_name: str = Field("autos-ai-agent", alias="ADK_APP_NAME")
    adk_session_db_url: str | None = Field(None, alias="ADK_SESSION_DB_URL")

    # ── Seguridad ─────────────────────────────────────────────────────────────
    secret_key: str = Field(
        "dev-secret-key-change-in-production", alias="SECRET_KEY"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level debe ser uno de: {valid}")
        return v.upper()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def document_ai_processor_path(self) -> str:
        """Construye el path completo del procesador de Document AI."""
        return (
            f"projects/{self.google_cloud_project}/locations/"
            f"{self.document_ai_location}/processors/{self.document_ai_processor_id}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Retorna la instancia cacheada de la configuración."""
    return Settings()


# Instancia global de configuración
settings = get_settings()
