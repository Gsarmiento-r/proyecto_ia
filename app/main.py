# =============================================================================
# app/main.py — Punto de entrada FastAPI para el servicio Autos-AI
# =============================================================================
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
import uvicorn
import vertexai
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from pydantic import BaseModel

from app.agent import root_agent
from app.config import settings

# ── Configuración de logging estructurado ────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger(__name__)

# ── Servicios globales ────────────────────────────────────────────────────────
session_service = InMemorySessionService()
runner: Runner | None = None

APP_NAME = settings.adk_app_name


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza al arrancar/detener la app."""
    global runner
    logger.info("Iniciando AutoFlota-AI", entorno=settings.app_env, proyecto=settings.google_cloud_project)

    # Inicializar Vertex AI
    vertexai.init(
        project=settings.vertexai_project,
        location=settings.vertexai_location,
    )

    # Inicializar ADK Runner
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    logger.info("Runner ADK inicializado", agente=root_agent.name)

    yield

    logger.info("Deteniendo AutoFlota-AI")


# ── Aplicación FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="AutoFlota-AI",
    description=(
        "API del agente de análisis de solicitudes de seguros de flotilla de autos. "
        "Procesa documentos PDF, Excel y Word en español para extraer variables clave."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class MensajeRequest(BaseModel):
    mensaje: str
    session_id: str | None = None
    user_id: str = "usuario_autos_ai"


class MensajeResponse(BaseModel):
    respuesta: str
    session_id: str
    exito: bool
    metadatos: dict = {}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health_check() -> dict:
    """Verificación de salud del servicio."""
    return {
        "estatus": "saludable",
        "servicio": "autos-ai",
        "version": "0.1.0",
        "entorno": settings.app_env,
        "agente": root_agent.name,
    }


@app.get("/", tags=["Sistema"])
async def root() -> dict:
    """Información general del servicio."""
    return {
        "servicio": "AutoFlota-AI",
        "descripcion": "Agente de análisis de solicitudes de seguros de flotilla de autos",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.post("/api/v1/analizar-documento", tags=["Análisis"])
async def analizar_documento(
    archivo: UploadFile = File(...),
    user_id: str = "usuario_autos_ai",
    session_id: str | None = None,
) -> JSONResponse:
    """
    Analiza un documento de solicitud de seguro (PDF, Excel o Word).

    Sube el archivo, lo procesa con el agente y retorna el resumen
    estructurado junto con la ruta del CSV generado.
    """
    if runner is None:
        raise HTTPException(status_code=503, detail="Runner no inicializado")

    # Validar tipo de archivo
    extensiones_permitidas = {".pdf", ".xlsx", ".xls", ".docx", ".doc"}
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in extensiones_permitidas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no soportado: {ext}. Use: {extensiones_permitidas}",
        )

    # Guardar archivo temporalmente
    ruta_temp = f"/tmp/{archivo.filename}"
    contenido = await archivo.read()
    with open(ruta_temp, "wb") as f:
        f.write(contenido)

    logger.info("Archivo recibido para análisis", nombre=archivo.filename, tamaño=len(contenido))

    # Crear o reusar sesión
    sid = session_id or f"session_{user_id}_{archivo.filename}"
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=sid
    )

    # Construir mensaje para el agente
    mensaje_usuario = (
        f"Por favor analiza el siguiente documento de solicitud de seguro de flotilla "
        f"de autos y extrae todas las variables relevantes. "
        f"El archivo se encuentra en: {ruta_temp}\n\n"
        f"Nombre del archivo: {archivo.filename}\n"
        f"Tipo: {ext.replace('.', '').upper()}"
    )

    contenido_mensaje = Content(role="user", parts=[Part(text=mensaje_usuario)])

    # Ejecutar agente
    respuesta_texto = ""
    async for evento in runner.run_async(
        user_id=user_id,
        session_id=sid,
        new_message=contenido_mensaje,
    ):
        if evento.is_final_response() and evento.content:
            for part in evento.content.parts:
                if hasattr(part, "text") and part.text:
                    respuesta_texto += part.text

    # Obtener metadatos del estado de sesión
    sesion = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=sid
    )
    estado = sesion.state if sesion else {}

    return JSONResponse(
        content={
            "exito": True,
            "respuesta": respuesta_texto,
            "session_id": sid,
            "metadatos": {
                "csv_generado": estado.get("csv_generado"),
                "id_solicitud_bd": estado.get("id_solicitud_guardada"),
                "archivo_gcs": estado.get("ultimo_archivo_gcs"),
            },
        }
    )


@app.post("/api/v1/chat", tags=["Chat"])
async def chat(request: MensajeRequest) -> MensajeResponse:
    """
    Endpoint de chat con el agente (para consultas de texto libre).
    Útil para consultar el historial de un cliente o hacer preguntas
    sobre solicitudes ya procesadas.
    """
    if runner is None:
        raise HTTPException(status_code=503, detail="Runner no inicializado")

    sid = request.session_id or f"chat_{request.user_id}"

    try:
        await session_service.create_session(
            app_name=APP_NAME, user_id=request.user_id, session_id=sid
        )
    except Exception:
        pass  # Sesión ya existe

    contenido_mensaje = Content(
        role="user", parts=[Part(text=request.mensaje)]
    )

    respuesta_texto = ""
    async for evento in runner.run_async(
        user_id=request.user_id,
        session_id=sid,
        new_message=contenido_mensaje,
    ):
        if evento.is_final_response() and evento.content:
            for part in evento.content.parts:
                if hasattr(part, "text") and part.text:
                    respuesta_texto += part.text

    return MensajeResponse(
        respuesta=respuesta_texto,
        session_id=sid,
        exito=True,
    )


@app.get("/api/v1/sesion/{session_id}", tags=["Sesiones"])
async def obtener_sesion(session_id: str, user_id: str = "usuario_autos_ai") -> dict:
    """Obtiene el estado de una sesión activa."""
    sesion = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"session_id": session_id, "estado": sesion.state}


# ── Punto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
