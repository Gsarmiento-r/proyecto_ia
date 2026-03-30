# =============================================================================
# tests/test_agent.py — Tests unitarios para app/agent.py
# =============================================================================
"""
Tests para la configuración, callbacks e instanciación del agente ADK.

Ejecutar:
    uv run pytest tests/test_agent.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Tests: Configuración del agente
# =============================================================================

class TestAgentConfig:
    def test_agent_es_instancia_adk(self):
        """Verifica que root_agent es una instancia del Agent de ADK."""
        from google.adk.agents import Agent
        from app.agent import root_agent

        assert isinstance(root_agent, Agent)

    def test_agent_tiene_nombre_correcto(self):
        """Verifica que el agente tiene el nombre esperado."""
        from app.agent import root_agent, agent

        assert root_agent.name == "root_agent"
        assert agent is root_agent  # El alias debe ser el mismo objeto

    def test_agent_tiene_instrucciones(self):
        """Verifica que el agente tiene instrucciones de sistema."""
        from app.agent import root_agent

        assert root_agent.instruction is not None
        assert len(str(root_agent.instruction)) > 100

    def test_agent_tiene_herramientas(self):
        """Verifica que el agente tiene herramientas registradas."""
        from app.agent import root_agent

        assert root_agent.tools is not None
        assert len(root_agent.tools) > 0

    def test_agent_tiene_callbacks(self):
        """Verifica que el agente tiene callbacks configurados."""
        from app.agent import root_agent

        assert root_agent.before_agent_callback is not None
        assert root_agent.after_agent_callback is not None

    def test_agent_modelo_configurado(self):
        """Verifica que el agente tiene un modelo Gemini configurado."""
        from app.agent import root_agent

        assert root_agent.model is not None
        assert "gemini" in str(root_agent.model).lower()


# =============================================================================
# Tests: Callbacks
# =============================================================================

class TestCallbacks:
    def test_before_callback_retorna_content_o_none(self):
        """Verifica que before_agent_callback retorna Content o None."""
        from google.genai.types import Content
        from app.agent import before_agent_callback

        mock_context = MagicMock()
        mock_context.state = {}
        mock_context.session_id = "test-session-123"

        resultado = before_agent_callback(mock_context)

        assert resultado is None or isinstance(resultado, Content)

    def test_before_callback_inicializa_estado(self):
        """Verifica que before_agent_callback inicializa el estado de sesión."""
        from app.agent import before_agent_callback

        estado = {}
        mock_context = MagicMock()
        mock_context.state = estado
        mock_context.session_id = "test-init-session"

        before_agent_callback(mock_context)

        assert estado.get("inicializado") is True
        assert "timestamp_inicio" in estado
        assert "proyecto_gcp" in estado

    def test_before_callback_incrementa_contador(self):
        """Verifica que el contador de solicitudes se incrementa."""
        from app.agent import before_agent_callback

        estado = {"inicializado": True, "solicitudes_procesadas": 5}
        mock_context = MagicMock()
        mock_context.state = estado
        mock_context.session_id = "test-counter-session"

        before_agent_callback(mock_context)

        assert estado["solicitudes_procesadas"] == 6

    def test_before_callback_no_falla_con_error(self):
        """Verifica que before_agent_callback es resiliente a errores."""
        from app.agent import before_agent_callback

        mock_context = MagicMock()
        mock_context.state = MagicMock(side_effect=Exception("Error simulado"))

        # No debe propagar la excepción
        resultado = before_agent_callback(mock_context)
        assert resultado is None

    def test_after_callback_retorna_content_o_none(self):
        """Verifica que after_agent_callback retorna Content o None."""
        from google.genai.types import Content
        from app.agent import after_agent_callback

        mock_context = MagicMock()
        mock_context.state = {
            "csv_generado": None,
            "id_solicitud_guardada": None,
            "ultimo_archivo_gcs": None,
        }
        mock_context.session_id = "test-after-session"

        resultado = after_agent_callback(mock_context)
        assert resultado is None or isinstance(resultado, Content)

    def test_after_callback_con_csv_generado(self):
        """Verifica que after_callback agrega nota cuando hay CSV."""
        from google.genai.types import Content
        from app.agent import after_agent_callback

        mock_context = MagicMock()
        mock_context.state = {
            "csv_generado": {
                "nombre_archivo": "solicitud_test.csv",
                "total_filas": 5,
                "total_columnas": 30,
            },
            "id_solicitud_guardada": "abc-123",
            "ultimo_archivo_gcs": None,
        }
        mock_context.session_id = "test-csv-session"

        resultado = after_agent_callback(mock_context)
        assert isinstance(resultado, Content)
        texto = resultado.parts[0].text
        assert "solicitud_test.csv" in texto or "abc-123" in texto

    def test_after_callback_no_falla_con_error(self):
        """Verifica que after_agent_callback es resiliente a errores."""
        from app.agent import after_agent_callback

        mock_context = MagicMock()
        mock_context.state = MagicMock(side_effect=Exception("Error simulado"))

        resultado = after_agent_callback(mock_context)
        assert resultado is None


# =============================================================================
# Tests: Prompts
# =============================================================================

class TestPrompts:
    def test_system_prompt_existe(self):
        """Verifica que el SYSTEM_PROMPT existe y no está vacío."""
        from app.prompts import SYSTEM_PROMPT

        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 500

    def test_system_prompt_en_espanol(self):
        """Verifica que el prompt está principalmente en español."""
        from app.prompts import SYSTEM_PROMPT

        palabras_espanol = ["agente", "solicitud", "flotilla", "coberturas", "vehículos"]
        for palabra in palabras_espanol:
            assert palabra in SYSTEM_PROMPT.lower(), f"Palabra '{palabra}' no encontrada en el prompt"

    def test_extraction_prompt_tiene_placeholder(self):
        """Verifica que EXTRACTION_PROMPT tiene el placeholder correcto."""
        from app.prompts import EXTRACTION_PROMPT

        assert "{document_text}" in EXTRACTION_PROMPT

    def test_summary_prompt_tiene_placeholder(self):
        """Verifica que SUMMARY_PROMPT tiene el placeholder correcto."""
        from app.prompts import SUMMARY_PROMPT

        assert "{extracted_data}" in SUMMARY_PROMPT

    def test_extraction_prompt_menciona_json(self):
        """Verifica que el prompt de extracción menciona el formato JSON."""
        from app.prompts import EXTRACTION_PROMPT

        assert "JSON" in EXTRACTION_PROMPT or "json" in EXTRACTION_PROMPT


# =============================================================================
# Tests: Configuración
# =============================================================================

class TestConfig:
    def test_settings_carga_sin_errores(self):
        """Verifica que la configuración carga sin errores."""
        from app.config import settings

        assert settings is not None
        assert settings.google_cloud_project is not None

    def test_settings_tiene_valor_por_defecto(self):
        """Verifica que la configuración tiene valores por defecto sensatos."""
        from app.config import settings

        assert settings.google_cloud_project == "autos-ai"
        assert "gemini" in settings.gemini_model.lower()
        assert settings.app_port == 8080

    def test_document_ai_processor_path(self):
        """Verifica que el path del procesador se construye correctamente."""
        from app.config import settings

        path = settings.document_ai_processor_path
        assert settings.google_cloud_project in path
        assert "processors" in path

    def test_is_development(self):
        """Verifica la propiedad is_development."""
        from app.config import Settings

        s = Settings(app_env="development")
        assert s.is_development is True
        assert s.is_production is False
