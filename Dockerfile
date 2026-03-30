# =============================================================================
# Dockerfile — Autos-AI
# Multi-stage build con UV para gestión de dependencias
# =============================================================================

# ---- Etapa 1: Builder -------------------------------------------------------
FROM python:3.12-slim AS builder

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

# Instalar dependencias del sistema necesarias para compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar UV (gestor de paquetes y entornos virtuales)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copiar archivos de dependencias primero (cache layer)
COPY pyproject.toml uv.lock* ./

# Crear entorno virtual e instalar dependencias de producción
RUN uv sync --frozen --no-dev --no-install-project

# ---- Etapa 2: Runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080 \
    APP_ENV=production

# Instalar dependencias runtime mínimas del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copiar entorno virtual del builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copiar código fuente de la aplicación
COPY --chown=appuser:appgroup app/ ./app/

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Comando de inicio
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
