# =============================================================================
# app/agent.py — Definición e instanciación del agente AutoFlota-AI
# =============================================================================
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import structlog
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content, Part

from app.config import settings
from app.prompts import SYSTEM_PROMPT
from app.tools import TODAS_LAS_HERRAMIENTAS

logger = structlog.get_logger(__name__)

# =============================================================================
# CALLBACKS DEL AGENTE
# =============================================================================


def before_agent_callback(callback_context: CallbackContext) -> Content | None:
    """
    Callback ejecutado ANTES de que el agente procese cada turno.

    Funciones:
    - Inyectar contexto de sesión (fecha/hora, configuración, historial previo).
    - Registrar la entrada del usuario en el estado de sesión.
    - Agregar información de configuración relevante al contexto.
    - Log de auditoría de la solicitud entrante.

    Args:
        callback_context: Contexto de la sesión ADK con estado y metadatos.

    Returns:
        Content con contexto adicional, o None para no modificar la entrada.
    """
    try:
        ahora = datetime.now(timezone.utc)
        session_id = getattr(callback_context, "session_id", "desconocido")

        logger.info(
            "Agente AutoFlota-AI iniciando procesamiento",
            session_id=session_id,
            timestamp=ahora.isoformat(),
        )

        # Inicializar estado de sesión si no existe
        if not callback_context.state.get("inicializado"):
            callback_context.state.update({
                "inicializado": True,
                "session_id": str(session_id),
                "timestamp_inicio": ahora.isoformat(),
                "proyecto_gcp": settings.google_cloud_project,
                "modelo_gemini": settings.gemini_model,
                "entorno": settings.app_env,
                "solicitudes_procesadas": 0,
                "ultimo_documento_leido": None,
                "variables_extraidas": None,
                "csv_generado": None,
                "id_solicitud_guardada": None,
            })

        # Incrementar contador de solicitudes en esta sesión
        callback_context.state["solicitudes_procesadas"] = (
            callback_context.state.get("solicitudes_procesadas", 0) + 1
        )
        callback_context.state["timestamp_ultimo_procesamiento"] = ahora.isoformat()

        # Construir mensaje de contexto para inyectar
        num_solicitud = callback_context.state.get("solicitudes_procesadas", 1)
        contexto_texto = (
            f"[CONTEXTO DEL SISTEMA - {ahora.strftime('%d/%m/%Y %H:%M:%S UTC')}]\n"
            f"Sesión: {session_id} | Solicitud #{num_solicitud} en esta sesión\n"
            f"Proyecto GCP: {settings.google_cloud_project} | "
            f"Entorno: {settings.app_env} | Modelo: {settings.gemini_model}\n"
            f"Colección Firestore: {settings.firestore_collection_solicitudes}\n"
            f"Bucket GCS outputs: {settings.gcs_bucket_outputs}\n"
        )

        # Si hay un documento previo en el estado, agregar referencia
        if callback_context.state.get("ultimo_documento_leido"):
            contexto_texto += (
                f"Último documento procesado: disponible en estado de sesión.\n"
            )

        logger.debug("Contexto de sesión inicializado/actualizado", num_solicitud=num_solicitud)

        # Retornar el contexto como Content (se agrega al inicio del turno)
        return Content(
            role="user",
            parts=[Part(text=contexto_texto)],
        )

    except Exception as exc:
        logger.warning("Error en before_agent_callback (no bloqueante)", error=str(exc))
        return None  # No bloquear el agente en caso de error en callback


def after_agent_callback(callback_context: CallbackContext) -> Content | None:
    """
    Callback ejecutado DESPUÉS de que el agente genera su respuesta.

    Funciones:
    - Guardar el output del agente en el estado de sesión.
    - Actualizar métricas de sesión.
    - Log de auditoría con la respuesta generada.
    - Trigger de guardado post-procesamiento si aplica.

    Args:
        callback_context: Contexto de la sesión ADK con estado y respuesta generada.

    Returns:
        Content modificado o None para mantener la respuesta original.
    """
    try:
        ahora = datetime.now(timezone.utc)
        session_id = getattr(callback_context, "session_id", "desconocido")

        # Capturar el estado actual post-procesamiento
        estado_post = {
            "timestamp_fin": ahora.isoformat(),
            "csv_generado": callback_context.state.get("csv_generado"),
            "id_solicitud_guardada": callback_context.state.get("id_solicitud_guardada"),
            "ultimo_archivo_gcs": callback_context.state.get("ultimo_archivo_gcs"),
            "variables_extraidas": bool(callback_context.state.get("variables_extraidas")),
        }

        callback_context.state["ultimo_output_estado"] = estado_post

        logger.info(
            "Agente AutoFlota-AI finalizó procesamiento",
            session_id=session_id,
            timestamp_fin=ahora.isoformat(),
            csv_generado=bool(estado_post.get("csv_generado")),
            id_guardado=estado_post.get("id_solicitud_guardada"),
        )

        # Si se generó un CSV, agregar nota al final de la respuesta
        csv_info = estado_post.get("csv_generado")
        id_solicitud = estado_post.get("id_solicitud_guardada")

        if csv_info or id_solicitud:
            nota_footer = "\n\n---\n"
            if csv_info and isinstance(csv_info, dict):
                nota_footer += (
                    f"📊 **CSV generado:** `{csv_info.get('nombre_archivo', 'N/A')}` "
                    f"({csv_info.get('total_filas', 0)} vehículos, "
                    f"{csv_info.get('total_columnas', 0)} columnas)\n"
                )
            if id_solicitud:
                nota_footer += (
                    f"💾 **ID en base de datos:** `{id_solicitud}` "
                    f"(Firestore: {settings.firestore_collection_solicitudes})\n"
                )
            nota_footer += f"⏱️ **Procesado:** {ahora.strftime('%d/%m/%Y %H:%M:%S UTC')}\n"

            return Content(
                role="model",
                parts=[Part(text=nota_footer)],
            )

        return None

    except Exception as exc:
        logger.warning("Error en after_agent_callback (no bloqueante)", error=str(exc))
        return None


# =============================================================================
# INSTANCIACIÓN DEL AGENTE RAÍZ
# =============================================================================

root_agent = Agent(
    # ── Modelo ──────────────────────────────────────────────────────────────
    model=settings.gemini_model,

    # ── Identidad ───────────────────────────────────────────────────────────
    name="root_agent",
    description=(
        "Agente especializado en el análisis y procesamiento de solicitudes de cotización "
        "de seguros de flotilla de autos grupales. Ingiere documentos en Excel, PDF o Word "
        "en español y genera un resumen estructurado junto con un CSV de variables clave."
    ),

    # ── Instrucciones del sistema ────────────────────────────────────────────
    instruction=SYSTEM_PROMPT,

    # ── Herramientas disponibles ─────────────────────────────────────────────
    tools=TODAS_LAS_HERRAMIENTAS,

    # ── Callbacks ────────────────────────────────────────────────────────────
    before_agent_callback=before_agent_callback,
    after_agent_callback=after_agent_callback,
)


# Alias estándar que ADK espera al hacer "adk run app/" o "adk web app/"
agent = root_agent
