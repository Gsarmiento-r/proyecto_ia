# =============================================================================
# eval/eval_runner.py — Evaluación del rendimiento del agente AutoFlota-AI
# =============================================================================
"""
Ejecuta evaluaciones automatizadas del agente contra casos de prueba
predefinidos y mide precisión de extracción, completitud y tiempos.

Uso:
    uv run python eval/eval_runner.py --caso todos
    uv run python eval/eval_runner.py --caso eval/ground_truth/caso_01.json
    uv run python eval/eval_runner.py --reporte reportes/eval_$(date +%Y%m%d).json
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
import typer
import vertexai
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from rich.console import Console
from rich.table import Table

# Configurar paths
ROOT_DIR = Path(__file__).parent.parent
GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth"
REPORTES_DIR = Path(__file__).parent / "reportes"
REPORTES_DIR.mkdir(exist_ok=True)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger(__name__)
console = Console()
app_cli = typer.Typer(name="eval-runner", help="Evaluador del agente AutoFlota-AI")


# =============================================================================
# Métricas de Evaluación
# =============================================================================

CAMPOS_OBLIGATORIOS = [
    "cliente.nombre",
    "broker.nombre",
    "prima.maxima_esperada",
    "flotilla.total_vehiculos",
    "fechas.inicio_vigencia",
    "fechas.fin_vigencia",
    "fechas.devolucion_cotizacion",
    "coberturas",
    "siniestros.total_siniestros",
]


def calcular_completitud(variables_extraidas: dict, campos: list[str]) -> float:
    """
    Calcula el porcentaje de campos obligatorios extraídos correctamente.

    Args:
        variables_extraidas: Variables devueltas por el agente.
        campos: Lista de campos requeridos en notación de puntos.

    Returns:
        Porcentaje de completitud (0.0 a 1.0).
    """
    encontrados = 0
    for campo in campos:
        partes = campo.split(".")
        valor = variables_extraidas
        for parte in partes:
            if isinstance(valor, dict):
                valor = valor.get(parte)
            else:
                valor = None
                break
        if valor is not None and valor != "" and valor != "No especificado":
            encontrados += 1

    return encontrados / len(campos) if campos else 0.0


def calcular_precision(extraido: dict, esperado: dict, tolerancia: float = 0.1) -> float:
    """
    Compara las variables extraídas contra los valores esperados del ground truth.

    Args:
        extraido: Variables extraídas por el agente.
        esperado: Variables esperadas del ground truth.
        tolerancia: Tolerancia para comparación de números (fracción).

    Returns:
        Precisión (0.0 a 1.0).
    """
    coincidencias = 0
    total_campos = 0

    def comparar(val_extraido: Any, val_esperado: Any) -> bool:
        if val_esperado is None:
            return True
        if isinstance(val_esperado, (int, float)):
            try:
                v = float(str(val_extraido).replace(",", ""))
                return abs(v - val_esperado) / max(abs(val_esperado), 1) <= tolerancia
            except (ValueError, TypeError):
                return False
        return str(val_extraido).strip().lower() == str(val_esperado).strip().lower()

    for clave, val_esperado in esperado.items():
        if isinstance(val_esperado, dict):
            val_ext = extraido.get(clave, {})
            if isinstance(val_ext, dict):
                sub_prec = calcular_precision(val_ext, val_esperado, tolerancia)
                coincidencias += sub_prec
            total_campos += 1
        else:
            total_campos += 1
            if comparar(extraido.get(clave), val_esperado):
                coincidencias += 1

    return coincidencias / total_campos if total_campos > 0 else 0.0


# =============================================================================
# Runner de Evaluación
# =============================================================================

async def ejecutar_caso(
    caso: dict,
    runner: Runner,
    session_service: InMemorySessionService,
    app_name: str = "eval-autos-ai",
) -> dict:
    """Ejecuta un caso de evaluación y retorna métricas."""
    caso_id = caso.get("id", "caso_desconocido")
    archivo = caso.get("archivo_entrada")
    esperado = caso.get("salida_esperada", {})

    logger.info("Ejecutando caso de evaluación", caso_id=caso_id, archivo=archivo)

    inicio = time.monotonic()

    session_id = f"eval_{caso_id}_{int(time.time())}"
    user_id = "eval_runner"

    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    mensaje = (
        f"Analiza el documento de solicitud de seguro de flotilla en: {archivo}\n"
        f"Extrae todas las variables y genera el CSV."
    )
    contenido_msg = Content(role="user", parts=[Part(text=mensaje)])

    respuesta_texto = ""
    try:
        async for evento in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=contenido_msg,
        ):
            if evento.is_final_response() and evento.content:
                for part in evento.content.parts:
                    if hasattr(part, "text") and part.text:
                        respuesta_texto += part.text
    except Exception as exc:
        logger.error("Error al ejecutar caso", caso_id=caso_id, error=str(exc))
        return {
            "caso_id": caso_id,
            "exito": False,
            "error": str(exc),
            "tiempo_segundos": time.monotonic() - inicio,
        }

    tiempo_ejecucion = time.monotonic() - inicio

    # Obtener estado de sesión
    sesion = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    estado = sesion.state if sesion else {}
    variables_extraidas = estado.get("variables_extraidas", {})
    if isinstance(variables_extraidas, dict):
        variables_var = variables_extraidas
    else:
        variables_var = {}

    # Calcular métricas
    completitud = calcular_completitud(variables_var, CAMPOS_OBLIGATORIOS)
    precision = calcular_precision(variables_var, esperado) if esperado else None
    csv_generado = bool(estado.get("csv_generado"))
    id_guardado = estado.get("id_solicitud_guardada")

    resultado = {
        "caso_id": caso_id,
        "exito": True,
        "tiempo_segundos": round(tiempo_ejecucion, 2),
        "completitud": round(completitud, 4),
        "precision_vs_ground_truth": round(precision, 4) if precision is not None else None,
        "csv_generado": csv_generado,
        "id_base_de_datos": id_guardado,
        "variables_extraidas": variables_var,
        "respuesta_resumen_chars": len(respuesta_texto),
    }

    logger.info(
        "Caso completado",
        caso_id=caso_id,
        completitud=f"{completitud:.1%}",
        tiempo=f"{tiempo_ejecucion:.1f}s",
    )
    return resultado


async def ejecutar_todos_los_casos(
    directorio_ground_truth: Path,
    reporte_salida: Path | None = None,
) -> dict:
    """Ejecuta todos los casos de evaluación disponibles."""
    import importlib.util, sys

    # Importar configuración y agente
    sys.path.insert(0, str(ROOT_DIR))
    from app.config import settings
    from app.agent import root_agent

    vertexai.init(
        project=settings.vertexai_project,
        location=settings.vertexai_location,
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="eval-autos-ai",
        session_service=session_service,
    )

    # Cargar archivos de ground truth
    archivos_json = sorted(directorio_ground_truth.glob("*.json"))
    if not archivos_json:
        console.print(f"[yellow]No se encontraron archivos JSON en {directorio_ground_truth}[/yellow]")
        return {"casos": [], "resumen": {}}

    casos: list[dict] = []
    for archivo in archivos_json:
        with open(archivo, encoding="utf-8") as f:
            caso = json.load(f)
        casos.append(caso)

    console.print(f"[green]Ejecutando {len(casos)} casos de evaluación...[/green]\n")

    resultados: list[dict] = []
    for caso in casos:
        resultado = await ejecutar_caso(caso, runner, session_service)
        resultados.append(resultado)

    # Resumen estadístico
    exitosos = [r for r in resultados if r.get("exito")]
    resumen = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_casos": len(resultados),
        "casos_exitosos": len(exitosos),
        "tasa_exito": len(exitosos) / len(resultados) if resultados else 0,
        "completitud_promedio": (
            sum(r.get("completitud", 0) for r in exitosos) / len(exitosos)
            if exitosos else 0
        ),
        "precision_promedio": (
            sum(r.get("precision_vs_ground_truth", 0) or 0 for r in exitosos) / len(exitosos)
            if exitosos else 0
        ),
        "tiempo_promedio_segundos": (
            sum(r.get("tiempo_segundos", 0) for r in exitosos) / len(exitosos)
            if exitosos else 0
        ),
        "csv_generados": sum(1 for r in exitosos if r.get("csv_generado")),
    }

    reporte = {"resumen": resumen, "resultados": resultados}

    # Guardar reporte
    if reporte_salida:
        reporte_salida.parent.mkdir(parents=True, exist_ok=True)
        with open(reporte_salida, "w", encoding="utf-8") as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2, default=str)
        console.print(f"\n[blue]Reporte guardado en: {reporte_salida}[/blue]")

    # Mostrar tabla de resultados
    _mostrar_tabla_resultados(resultados, resumen)

    return reporte


def _mostrar_tabla_resultados(resultados: list[dict], resumen: dict) -> None:
    """Muestra una tabla Rich con los resultados de evaluación."""
    tabla = Table(title="Resultados de Evaluación — AutoFlota-AI", show_lines=True)
    tabla.add_column("Caso", style="cyan")
    tabla.add_column("Éxito", justify="center")
    tabla.add_column("Completitud", justify="right")
    tabla.add_column("Precisión", justify="right")
    tabla.add_column("Tiempo (s)", justify="right")
    tabla.add_column("CSV", justify="center")

    for r in resultados:
        tabla.add_row(
            r.get("caso_id", ""),
            "✅" if r.get("exito") else "❌",
            f"{r.get('completitud', 0):.1%}" if r.get("exito") else "—",
            f"{r.get('precision_vs_ground_truth', 0):.1%}"
            if r.get("precision_vs_ground_truth") is not None else "—",
            str(r.get("tiempo_segundos", 0)),
            "✅" if r.get("csv_generado") else "❌",
        )

    console.print(tabla)
    console.print(f"\n[bold]Resumen:[/bold]")
    console.print(f"  Tasa de éxito:       {resumen.get('tasa_exito', 0):.1%}")
    console.print(f"  Completitud media:   {resumen.get('completitud_promedio', 0):.1%}")
    console.print(f"  Precisión media:     {resumen.get('precision_promedio', 0):.1%}")
    console.print(f"  Tiempo medio:        {resumen.get('tiempo_promedio_segundos', 0):.1f}s")
    console.print(f"  CSVs generados:      {resumen.get('csv_generados', 0)}/{resumen.get('total_casos', 0)}")


# =============================================================================
# CLI
# =============================================================================

@app_cli.command()
def main(
    caso: str = typer.Option("todos", help="ID del caso o 'todos'"),
    directorio: Path = typer.Option(GROUND_TRUTH_DIR, help="Directorio con archivos JSON de ground truth"),
    reporte: Path | None = typer.Option(None, help="Ruta de salida del reporte JSON"),
):
    """Ejecuta la evaluación del agente AutoFlota-AI."""
    if reporte is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporte = REPORTES_DIR / f"eval_{ts}.json"

    asyncio.run(ejecutar_todos_los_casos(directorio, reporte))


if __name__ == "__main__":
    app_cli()
